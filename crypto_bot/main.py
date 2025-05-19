import logging
import os
from pathlib import Path

import click
import pandas as pd
import yaml

# テスト用にモック差し替え可能にエクスポート
from sklearn.linear_model import LogisticRegression

from crypto_bot.backtest.engine import BacktestEngine
from crypto_bot.backtest.optimizer import (  # noqa: F401
    ParameterOptimizer,
    optimize_backtest,
)
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.ml.optimizer import _load_and_preprocess_data
from crypto_bot.ml.optimizer import optimize_ml as run_optuna
from crypto_bot.ml.optimizer import train_best_model
from crypto_bot.ml.preprocessor import prepare_ml_dataset
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.strategy.bollinger import BollingerStrategy


def deep_merge(default: dict, override: dict) -> dict:
    """
    ネストされた dict 同士を再帰的にマージする。
    override の値が優先される。
    """
    for key, val in override.items():
        if key in default and isinstance(default[key], dict) and isinstance(val, dict):
            default[key] = deep_merge(default[key], val)
        else:
            default[key] = val
    return default


def load_config(path: str) -> dict:
    """
    1) パッケージ同梱の config/default.yml を読み込む
    2) ユーザ指定の設定ファイルを読み込む
    3) deep_merge して返す
    """
    default_path = (
        Path(__file__).parent.parent / "config" / "default.yml"  # crypto_bot/
    )
    with open(default_path, "r") as f:
        default_cfg = yaml.safe_load(f) or {}

    with open(path, "r") as f:
        user_cfg = yaml.safe_load(f) or {}

    return deep_merge(default_cfg, user_cfg)


def prepare_data(cfg: dict):
    """
    データ取得 → 前処理 → 特徴量・ターゲット生成
    戻り値: X_train, y_train, X_val, y_val
    """
    dd = cfg.get("data", {})
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange"),
        symbol=dd.get("symbol"),
    )
    df = fetcher.get_price_df(
        timeframe=dd.get("timeframe"),
        since=dd.get("since"),
        limit=dd.get("limit"),
        paginate=dd.get("paginate", False),
        per_page=dd.get("per_page", 0),
    )
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # モックや一部データソースでは 'volume' 列がないことがあるので補完
    if "volume" not in df.columns:
        df["volume"] = 0

    # 前処理
    window = cfg["ml"].get("feat_period", 0)
    df = DataPreprocessor.clean(
        df, timeframe=dd.get("timeframe"), z_thresh=5.0, window=window
    )

    # 特徴量とターゲット生成
    ret = prepare_ml_dataset(df, cfg)
    # 4要素返却ならそのまま返す
    if isinstance(ret, tuple) and len(ret) == 4:
        return ret

    # 3要素返却なら全件を train/val に使う
    if isinstance(ret, tuple) and len(ret) == 3:
        X, y_reg, y_clf = ret  # type: ignore
        mode = cfg["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg
        # 全データ数をそのまま train/val に
        return X, y, X, y

    # その他: train_test_split (保険的処理)
    X, y_reg, y_clf = ret  # type: ignore
    mode = cfg["ml"].get("target_type", "classification")
    y = y_clf if mode == "classification" else y_reg
    from sklearn.model_selection import train_test_split

    return train_test_split(
        X, y, test_size=cfg["ml"].get("test_size", 0.2), random_state=42
    )


def save_model(model, path: str):
    """
    MLModel や sklearn Estimator を問わずファイルに保存
    """
    try:
        # MLModel の場合
        model.save(path)
    except AttributeError:
        # sklearn の単体モデル
        import joblib

        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(model, path)


@click.group()
def cli():
    """CryptoBot CLI entrypoint."""
    pass


@cli.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
def backtest(config_path: str):
    """Walk-forward バックテストを実行するコマンド。"""
    cfg = load_config(config_path)

    logging.basicConfig(
        level=logging.WARNING,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )

    dd = cfg.get("data", {})
    fetcher = MarketDataFetcher(exchange_id=dd.get("exchange"), symbol=dd.get("symbol"))
    df = fetcher.get_price_df(
        timeframe=dd.get("timeframe"),
        since=dd.get("since"),
        limit=dd.get("limit"),
        paginate=dd.get("paginate", False),
        per_page=dd.get("per_page", 0),
    )
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    period = cfg["strategy"]["params"]["period"]
    df = DataPreprocessor.clean(
        df, timeframe=dd.get("timeframe"), z_thresh=5.0, window=period
    )
    nbdev = cfg["strategy"]["params"].get("nbdev", 2.0)
    bb_df = IndicatorCalculator.calculate_bbands(
        df, period=period, nbdevup=nbdev, nbdevdn=nbdev
    )
    df = df.join(bb_df)

    wf = cfg["walk_forward"]
    splits = split_walk_forward(df, wf["train_window"], wf["test_window"], wf["step"])

    stats = []
    for _, test_df in splits:
        engine = BacktestEngine(
            price_df=test_df,
            strategy=BollingerStrategy(period=period, nbdevup=nbdev, nbdevdn=nbdev),
            starting_balance=cfg["backtest"]["starting_balance"],
            slippage_rate=cfg["backtest"]["slippage_rate"],
        )
        engine.run()
        stats.append(engine.statistics())

    stats_df = pd.DataFrame(stats)
    stats_df.to_csv("backtest_results.csv", index=False)
    click.echo(stats_df.to_string(index=False))


@cli.command("optimize-backtest")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--output",
    "-o",
    "output_csv",
    default=None,
    type=click.Path(),
    help="結果をCSV出力するパス",
)
def optimize_backtest_cli(config_path: str, output_csv: str):
    """バックテスト戦略のパラメータ最適化を実行するコマンド。"""
    cfg = load_config(config_path)

    click.echo(">> Starting backtest optimization …")
    df = optimize_backtest(cfg, output_csv=output_csv)
    if output_csv:
        click.echo(f">> Results saved to {output_csv!r}")
    else:
        click.echo(df.to_string(index=False))


@cli.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type",
    "-t",
    "model_type",
    default=None,
    help="MLモデルタイプ (lgbm/rf/xgb)",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(),
    default=None,
    help="モデル保存パス (config の output.model_path を上書き)",
)
def train(config_path: str, model_type: str, output_path: str):
    """
    MLモデルを学習して保存するコマンド。
    --model-type が指定された場合は train_best_model を呼び出します。
    """
    cfg = load_config(config_path)

    # CLI override: 設定上の model_type を更新
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()
        click.echo(f"Using model_type: {cfg['ml']['model_type']}")

    # データ準備
    X_tr, y_tr, X_val, y_val = prepare_data(cfg)

    # サンプル数を出力
    mode = cfg["ml"].get("target_type", "classification")
    click.echo(f"Training {mode} model on {len(X_tr)} samples")

    # モデル構築・学習
    if model_type:
        model = train_best_model(cfg, X_tr, y_tr, X_val, y_val)
    else:
        if mode == "classification":
            model = LogisticRegression()
        else:
            from sklearn.linear_model import LinearRegression  # noqa: F401

            model = LinearRegression()
        model.fit(X_tr, y_tr)

    # モデル保存
    out_path = output_path or cfg.get("output", {}).get("model_path", "model.pkl")
    save_model(model, out_path)
    click.echo(f"Model saved to {out_path!r}")


@cli.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type",
    "-t",
    "model_type",
    type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False),
    default=None,
    help="MLモデルタイプ (lgbm/rf/xgb)",
)
def optimize_ml(config_path: str, model_type: str):
    """MLモデルのハイパーパラ最適化を実行 (最適化のみ)。"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    study = run_optuna(cfg)
    click.echo(f"Best trial value: {study.best_value}")
    click.echo(f"Best params: {study.best_params}")


@cli.command("optimize-and-train")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--trials-out",
    "-t",
    "trials_path",
    default=None,
    type=click.Path(),
    help="全トライアル結果をCSV出力するパス",
)
@click.option(
    "--model-out",
    "-m",
    "model_path",
    default=None,
    type=click.Path(),
    help="最良パラメータで再学習モデル出力パス",
)
@click.option(
    "--model-type",
    "-T",
    "model_type",
    type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False),
    default=None,
    help="MLモデルタイプ (lgbm/rf/xgb)",
)
def optimize_and_train(
    config_path: str, trials_path: str, model_path: str, model_type: str
):
    """
    1) Optuna 最適化
    2) (--trials-out) トライアル結果をCSV保存
    3) (--model-out) 最良パラメータで再学習＆モデル保存
    """
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    logging.basicConfig(
        level=logging.WARNING,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    )
    click.echo(">> Starting hyperparameter optimization …")
    study = run_optuna(cfg)

    if trials_path:
        df_trials = study.trials_dataframe()
        df_trials.to_csv(trials_path, index=False)
        click.echo(f">> All trials saved to {trials_path!r}")

    if model_path:
        click.echo(">> Training final model on full dataset …")
        full_df = _load_and_preprocess_data(cfg)
        X, y_reg, y_clf = prepare_ml_dataset(full_df, cfg)
        mode = cfg["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg

        mtype = cfg["ml"]["model_type"].lower()
        best_params = study.best_params.copy()
        if mtype == "rf":
            best_params.pop("learning_rate", None)

        from crypto_bot.ml.model import create_model

        estimator = (
            create_model(mtype, **best_params) if mode == "classification" else None
        )
        ml_model = estimator
        ml_model.fit(X, y)
        ml_model.save(model_path)
        click.echo(f">> Final model saved to {model_path!r}")

    click.echo(">> optimize-and-train complete.")


@cli.command("train-best")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--output",
    "-o",
    "model_path",
    required=True,
    type=click.Path(),
    help="最良モデル出力パス",
)
@click.option(
    "--model-type",
    "-t",
    "model_type",
    type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False),
    default=None,
    help="MLモデルタイプ (lgbm/rf/xgb)",
)
def train_best(config_path: str, model_path: str, model_type: str):
    """Optuna で最適化 → 最良パラメータで全データ再学習 & モデル保存"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    click.echo(">> Running optimization and training best model …")
    train_best_model(cfg, model_path)


if __name__ == "__main__":
    cli()
