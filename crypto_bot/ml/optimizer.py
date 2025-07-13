# ========================================================================
# ファイル名: crypto_bot/ml/optimizer.py
# 説明:
# 機械学習モデル（ML）のハイパパラメータ自動最適化・モデル訓練・
# Optunaによるベイズ最適化・学習済みモデル保存/ロード用モジュール。
# - ルールベース（テクニカル指標系）の最適化とは別モジュール。
# - MLStrategy等、機械学習戦略に特化。
# 主な機能:
# - objective: Optuna用評価関数（データ取得～スコア評価）
# - optimize_ml: Optunaで自動パラメータ探索
# - train_best_model: ベストモデル訓練・保存
# - save_trials: 試行履歴CSV出力
# ※ バックテストエンジンとは独立運用
# ========================================================================

import logging
import math
import os

import joblib
import optuna
import pandas as pd
from ccxt.base.errors import ExchangeError
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.ml.model import MLModel, create_ensemble_model, create_model
from crypto_bot.ml.preprocessor import prepare_ml_dataset

logger = logging.getLogger(__name__)

# xgboost が入っていれば回帰・分類器を利用可
try:
    from xgboost import XGBRegressor

    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False


def _remove_lgbm_unused_params(params):
    """
    LightGBMで値が1.0やNoneの時に警告となるパラメータを除去します。
    """
    for key in ["bagging_fraction", "feature_fraction"]:
        if key in params and (params[key] is None or params[key] == 1.0):
            params.pop(key)
    for key in ["lambda_l1", "lambda_l2"]:
        if key in params and (params[key] is None or params[key] == 0.0):
            params.pop(key)
    return params


def _load_and_preprocess_data(config: dict) -> pd.DataFrame:
    """
    設定からOHLCVデータを取得→DataPreprocessor.clean()まで実施して返す。
    """
    dd = config["data"]
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange", "bybit"),
        symbol=dd["symbol"],
    )
    try:
        df = fetcher.get_price_df(
            timeframe=dd["timeframe"],
            since=dd.get("since"),
            limit=dd.get("limit"),
            paginate=dd.get("paginate", False),
            per_page=dd.get("per_page", 0),
        )
    except ExchangeError as ex:
        logger.warning("ExchangeError while fetching OHLCV: %s", ex)
        return pd.DataFrame()
    except Exception as ex:
        logger.error("Unexpected error while fetching OHLCV: %s", ex)
        return pd.DataFrame()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    window = config["ml"]["feat_period"]
    df = DataPreprocessor.clean(
        df,
        timeframe=dd["timeframe"],
        thresh=5.0,
        window=window,
    )
    return df


def objective(trial: optuna.Trial, config: dict) -> float:
    """
    Optunaによる1 trial分の学習→検証を実施、スコア (accuracy) を返す。
    データが空やnanの場合は0.0を返す。model_type: lgbm/rf/xgb対応。
    """
    # --- データ準備 ---
    try:
        if "data" not in config:
            # 既に前処理済みDFを渡した場合
            ret = prepare_ml_dataset(config)
        else:
            df = _load_and_preprocess_data(config)
            if df.empty:
                logger.warning("Empty dataframe returned; skipping trial.")
                return 0.0
            ret = prepare_ml_dataset(df, config)
    except ExchangeError as ex:
        logger.warning("ExchangeError in objective(): %s", ex)
        return 0.0
    except Exception as ex:
        logger.error("Unexpected error in objective(): %s", ex)
        return 0.0

    # データ構造により4要素または3要素返却に対応
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

    # --- ハイパーパラメータのサジェスト ---
    search_space = config["ml"].get("model_params_search_space", {})
    params = {}
    for name, choices in search_space.items():
        params[name] = trial.suggest_categorical(name, choices)

    if not params:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 50, 200),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
            "learning_rate": trial.suggest_loguniform("learning_rate", 1e-3, 1e-1),
        }

    mode = config["ml"].get("target_type", "classification")
    mtype = config["ml"].get("model_type", "lgbm").lower()

    # --- モデル生成（分類はcreate_model、回帰は手動マッピング） ---
    if mode == "classification":
        if mtype == "rf":
            model_kwargs = {k: params[k] for k in ("n_estimators", "max_depth")}
        else:
            model_kwargs = dict(params)
            if mtype == "lgbm":
                model_kwargs["verbose"] = -1
                model_kwargs = _remove_lgbm_unused_params(model_kwargs)

        try:
            estimator = create_model(mtype, **model_kwargs)
        except ValueError as e:
            raise ValueError(f"Failed to create classification model: {e}")

    else:
        if mtype == "lgbm":
            model_kwargs = dict(params)
            model_kwargs["verbose"] = -1
            model_kwargs = _remove_lgbm_unused_params(model_kwargs)
            estimator = LGBMRegressor(**model_kwargs)
        elif mtype == "rf":
            rf_kwargs = {k: params[k] for k in ("n_estimators", "max_depth")}
            estimator = RandomForestRegressor(**rf_kwargs)
        elif mtype == "xgb" and _HAS_XGB:
            estimator = XGBRegressor(**dict(params))
        else:
            raise ValueError(f"Unknown regression model_type={mtype}")

    # --- 学習・予測・評価（早期停止対応） ---
    model = MLModel(estimator)

    # 早期停止パラメータの取得
    early_stopping_rounds = config["ml"].get("early_stopping_rounds", 50)

    # 早期停止を使った学習（LightGBM、XGBoostのみ）
    if mtype in ["lgbm", "xgb"]:
        model.fit(
            X_train,
            y_train,
            X_val=X_val,
            y_val=y_val,
            early_stopping_rounds=early_stopping_rounds,
        )
    else:
        model.fit(X_train, y_train)

    y_pred = model.predict(X_val)
    score = accuracy_score(y_val, y_pred)

    # nanや非数値は0.0を返す
    if not isinstance(score, (int, float)) or math.isnan(score):
        return 0.0

    return float(score)


def optimize_ml(config: dict) -> optuna.Study:
    """
    config['ml']['optuna']を読み込み、Optuna最適化を実行。
    Studyオブジェクトを返却。
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
    Optuna の全トライアル結果をCSV保存。
    """
    df = study.trials_dataframe()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Trials saved to {path!r}")


def train_best_model(config: dict, *args):
    """
    train_best_model:
    (cfg, X_tr, y_tr, X_te, y_te) または (cfg, output_path)の2形式に対応。
    """
    # (cfg, X_tr, y_tr, X_te, y_te)
    if len(args) == 4:
        X_train, y_train, X_val, y_val = args
        mtype = config["ml"].get("model_type", "lgbm").lower()
        estimator = create_model(mtype)
        estimator.fit(X_train, y_train)
        return estimator

    # (cfg, output_path)
    if len(args) == 1 and isinstance(args[0], (str, os.PathLike)):
        output_path = args[0]

        # 1) Optunaによる最適化
        study = optimize_ml(config)

        # 2) 全データ取得・前処理
        df = _load_and_preprocess_data(config)
        ret = prepare_ml_dataset(df, config)
        if isinstance(ret, tuple) and len(ret) == 4:
            X_train, y_train, _, _ = ret
        else:
            X_train, _, y_clf = ret  # type: ignore
            mode = config["ml"].get("target_type", "classification")
            y_train = y_clf if mode == "classification" else y_clf

        # 3) 最良推定器生成
        mode = config["ml"].get("target_type", "classification")
        mtype = config["ml"].get("model_type", "lgbm").lower()

        # アンサンブルモデルの場合
        if mtype == "ensemble":
            ensemble_config = config["ml"].get("ensemble", {})
            if ensemble_config.get("enabled", False):
                logger.info("Creating ensemble model")

                # ベースモデル設定を取得
                base_models_config = ensemble_config.get("base_models", [])
                method = ensemble_config.get("method", "voting")
                weights = ensemble_config.get("weights")
                meta_model_config = ensemble_config.get("meta_model", {})

                # アンサンブルモデルを作成
                ensemble_model = create_ensemble_model(
                    model_configs=base_models_config,
                    method=method,
                    weights=weights,
                    meta_model_config=meta_model_config,
                )

                # 学習・保存
                model = ensemble_model.fit(X_train, y_train)
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                ensemble_model.save(output_path)
                print(f"Best ensemble model saved to {output_path!r}")
                return
            else:
                logger.warning(
                    "Ensemble model requested but not enabled in config. "
                    "Using default lgbm."
                )
                mtype = "lgbm"

        best_params = study.best_params.copy()

        if mode == "classification":
            if mtype == "rf":
                best_params.pop("learning_rate", None)
            if mtype == "lgbm":
                best_params["verbose"] = -1
                best_params = _remove_lgbm_unused_params(best_params)
            estimator = create_model(mtype, **best_params)
        else:
            if mtype == "lgbm":
                best_params["verbose"] = -1
                best_params = _remove_lgbm_unused_params(best_params)
                estimator = LGBMRegressor(**best_params)
            elif mtype == "rf":
                tmp = {k: best_params[k] for k in ("n_estimators", "max_depth")}
                estimator = RandomForestRegressor(**tmp)
            elif mtype == "xgb" and _HAS_XGB:
                estimator = XGBRegressor(**best_params)
            else:
                raise ValueError(f"Unknown regression model_type={mtype}")

        # 4) 学習・保存
        model = MLModel(estimator).fit(X_train, y_train)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        joblib.dump(model, output_path)
        print(f"Best model saved to {output_path!r}")

        # 5) 特徴量重要度分析・出力
        importance_df = model.get_feature_importance(X_train.columns.tolist())
        if importance_df is not None:
            importance_path = output_path.replace(".pkl", "_feature_importance.csv")
            importance_df.to_csv(importance_path, index=False)
            print(f"Feature importance saved to {importance_path!r}")

            # 上位20特徴量をログ出力
            logger.info("Top 20 Important Features:")
            for _, row in importance_df.head(20).iterrows():
                logger.info(f"  {row['feature']}: {row['importance']:.4f}")

            # 特徴量選択推奨（101 → 80特徴量）
            selected_features = model.select_features_by_importance(
                X_train, threshold=0.005, max_features=80
            )
            print(
                f"Recommended feature selection: "
                f"{len(X_train.columns)} → {len(selected_features)} features"
            )
            logger.info(
                f"Selected features for optimization: {selected_features[:10]}..."
            )

        return

    raise TypeError(
        "train_best_model: 引数は (config, X_tr, y_tr, X_te, y_te) か "
        "(config, output_path) で呼び出してください"
    )


# エイリアス: main.py から run_optunaとして利用可
run_optuna = optimize_ml
