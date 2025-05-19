import math
import os

import joblib
import optuna
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.ml.model import MLModel, create_model
from crypto_bot.ml.preprocessor import prepare_ml_dataset

# xgboost が入っていれば回帰・分類器を利用可（分類器は create_model で扱う）
try:
    from xgboost import XGBClassifier, XGBRegressor  # noqa: F401

    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False

from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor


def _load_and_preprocess_data(config: dict) -> pd.DataFrame:
    """
    設定から OHLCV データを取得し、DataPreprocessor.clean() まで通して返す。
    """
    dd = config["data"]
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange", "bybit"),
        symbol=dd["symbol"],
    )
    df = fetcher.get_price_df(
        timeframe=dd["timeframe"],
        since=dd.get("since"),
        limit=dd.get("limit"),
        paginate=dd.get("paginate", False),
        per_page=dd.get("per_page", 0),
    )
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    window = config["ml"]["feat_period"]
    df = DataPreprocessor.clean(
        df,
        timeframe=dd["timeframe"],
        z_thresh=5.0,
        window=window,
    )
    return df


def objective(trial: optuna.Trial, config: dict) -> float:
    """
    1 trial 分の学習→検証を行い、スコア (accuracy) を返す。
    データが空／nan の場合は 0.0 を返す。
    model_type: lgbm/rf/xgb に対応。
    """
    # --- データ準備 ---
    if "data" not in config:
        # 既に前処理済み DF を渡した場合
        ret = prepare_ml_dataset(config)
    else:
        df = _load_and_preprocess_data(config)
        ret = prepare_ml_dataset(df, config)

    # 4要素 or 3要素返り値に対応
    if isinstance(ret, tuple) and len(ret) == 4:
        X_train, y_train, X_val, y_val = ret
    else:
        X, y_reg, y_clf = ret  # type: ignore
        mode = config["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg
        test_size = config["ml"].get("test_size", 0.2)
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

    # 空データチェック
    try:
        if len(X_train) == 0 or len(y_train) == 0 or len(X_val) == 0 or len(y_val) == 0:
            return 0.0
    except Exception:
        return 0.0

    # --- ハイパーパラサジェスト ---
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 50, 200),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "learning_rate": trial.suggest_loguniform("learning_rate", 1e-3, 1e-1),
    }

    mode = config["ml"].get("target_type", "classification")
    mtype = config["ml"].get("model_type", "lgbm").lower()

    # --- モデル生成（分類は create_model、回帰は手動マッピング） ---
    if mode == "classification":
        # RandomForest は learning_rate を受け取らないので絞り込む
        if mtype == "rf":
            model_kwargs = {k: params[k] for k in ("n_estimators", "max_depth")}
        else:
            model_kwargs = dict(params)
            if mtype == "lgbm":
                model_kwargs["verbose"] = -1

        try:
            estimator = create_model(mtype, **model_kwargs)
        except ValueError as e:
            raise ValueError(f"Failed to create classification model: {e}")

    else:
        # 回帰モデルは手動マッピング
        if mtype == "lgbm":
            model_kwargs = dict(params)
            model_kwargs["verbose"] = -1
            estimator = LGBMRegressor(**model_kwargs)
        elif mtype == "rf":
            rf_kwargs = {k: params[k] for k in ("n_estimators", "max_depth")}
            estimator = RandomForestRegressor(**rf_kwargs)
        elif mtype == "xgb" and _HAS_XGB:
            estimator = XGBRegressor(**dict(params))
        else:
            raise ValueError(f"Unknown regression model_type={mtype}")

    # --- 学習 & 予測 & 評価 ---
    model = MLModel(estimator)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_val)
    score = accuracy_score(y_val, y_pred)

    # nan／非数値チェック
    if not isinstance(score, (int, float)) or math.isnan(score):
        return 0.0

    return float(score)


def optimize_ml(config: dict) -> optuna.Study:
    """
    config['ml']['optuna'] を読み込み、Optuna 最適化を実行。
    Study オブジェクトを返却。
    """
    opt_cfg = config["ml"]["optuna"]
    sampler = getattr(optuna.samplers, opt_cfg["sampler"]["name"])()
    pruner = getattr(optuna.pruners, opt_cfg["pruner"]["name"])(
        n_startup_trials=opt_cfg["pruner"]["n_startup_trials"],
        n_warmup_steps=opt_cfg["pruner"]["n_warmup_steps"],
        interval_steps=opt_cfg["pruner"]["interval_steps"],
    )
    study = optuna.create_study(
        direction=opt_cfg["direction"],
        sampler=sampler,
        pruner=pruner,
    )
    study.optimize(
        lambda trial: objective(trial, config),
        n_trials=opt_cfg["n_trials"],
        timeout=opt_cfg["timeout"],
    )
    return study


def save_trials(study: optuna.Study, path: str = "trials.csv"):
    """
    Optuna の全トライアル結果を CSV 保存。
    """
    df = study.trials_dataframe()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Trials saved to {path!r}")


# ----------------------------------------------------------------
# train_best_model: 2つの呼び出しスタイルに対応
#   * train_best_model(cfg, X_tr, y_tr, X_te, y_te) → Estimator を返す
#   * train_best_model(cfg, output_path)         → study 最適化＋モデル保存
# ----------------------------------------------------------------
def train_best_model(config: dict, *args):
    # (cfg, X_tr, y_tr, X_te, y_te) の場合
    if len(args) == 4:
        X_train, y_train, X_val, y_val = args
        mtype = config["ml"].get("model_type", "lgbm").lower()
        # シンプルに分類用モデルを作り、学習して返す
        estimator = create_model(mtype)
        estimator.fit(X_train, y_train)
        return estimator

    # (cfg, output_path) の場合
    if len(args) == 1 and isinstance(args[0], (str, os.PathLike)):
        output_path = args[0]

        # 1) 最適化
        study = optimize_ml(config)

        # 2) 全データ取得＆前処理
        df = _load_and_preprocess_data(config)
        ret = prepare_ml_dataset(df, config)
        if isinstance(ret, tuple) and len(ret) == 4:
            X_train, y_train, _, _ = ret
        else:
            X_train, _, y_clf = ret  # type: ignore
            mode = config["ml"].get("target_type", "classification")
            y_train = y_clf if mode == "classification" else y_clf

        # 3) 推定器生成
        mode = config["ml"].get("target_type", "classification")
        mtype = config["ml"].get("model_type", "lgbm").lower()
        best_params = study.best_params.copy()

        if mode == "classification":
            if mtype == "rf":
                best_params.pop("learning_rate", None)
            if mtype == "lgbm":
                best_params["verbose"] = -1
            estimator = create_model(mtype, **best_params)
        else:
            if mtype == "lgbm":
                best_params["verbose"] = -1
                estimator = LGBMRegressor(**best_params)
            elif mtype == "rf":
                # 必要パラメタだけ抜き出し
                tmp = {k: best_params[k] for k in ("n_estimators", "max_depth")}
                estimator = RandomForestRegressor(**tmp)
            elif mtype == "xgb" and _HAS_XGB:
                estimator = XGBRegressor(**best_params)
            else:
                raise ValueError(f"Unknown regression model_type={mtype}")

        # 4) 学習＋保存
        model = MLModel(estimator).fit(X_train, y_train)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        joblib.dump(model, output_path)
        print(f"Best model saved to {output_path!r}")
        return

    raise TypeError(
        "train_best_model: 引数は "
        "(config, X_tr, y_tr, X_te, y_te) か "
        "(config, output_path) のいずれかで呼び出してください"
    )


# エイリアス: main.py から run_optuna として利用できるように
run_optuna = optimize_ml
