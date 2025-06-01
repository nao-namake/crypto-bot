# =============================================================================
# ファイル名: crypto_bot/main.py
# 説明:
# Crypto-Bot 全体のCLIエントリポイント。
# - 機械学習戦略（MLStrategy）を用いたバックテスト/MLワークフロー全体の管理。
# - バックテスト、パラメータ最適化、ML訓練、モデル保存/ロードなどをカバー。
# - コマンドごとに細かく設計されており、ルールベース/ML系双方の運用が可能。
# =============================================================================
from __future__ import annotations

import logging
import os
from pathlib import Path

import click
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression

from crypto_bot.backtest.engine import BacktestEngine
from crypto_bot.backtest.analysis import export_aggregates
from crypto_bot.backtest.optimizer import (  # noqa: F401  – 他コマンドで使用
    ParameterOptimizer,
    optimize_backtest,
)
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.ml.optimizer import (
    _load_and_preprocess_data,
    optimize_ml as run_optuna,
    train_best_model,
)
from crypto_bot.ml.preprocessor import prepare_ml_dataset
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.strategy.ml_strategy import MLStrategy


# --------------------------------------------------------------------------- #
# ロギング設定
# --------------------------------------------------------------------------- #
def setup_logging():
    """
    環境変数 CRYPTO_BOT_LOG_LEVEL でログレベルを制御。デフォルトは INFO。
    DEBUG を見たい場合は CRYPTO_BOT_LOG_LEVEL=DEBUG を設定してください。
    """
    level_name = os.getenv("CRYPTO_BOT_LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
        level=numeric_level,
    )


# --------------------------------------------------------------------------- #
# ネストされた dict のマージユーティリティ
# --------------------------------------------------------------------------- #
def deep_merge(default: dict, override: dict) -> dict:
    for key, val in override.items():
        if key in default and isinstance(default[key], dict) and isinstance(val, dict):
            default[key] = deep_merge(default[key], val)
        else:
            default[key] = val
    return default


def load_config(path: str) -> dict:
    default_path = Path(__file__).parent.parent / "config" / "default.yml"
    with open(default_path, "r") as f:
        default_cfg = yaml.safe_load(f) or {}
    with open(path, "r") as f:
        user_cfg = yaml.safe_load(f) or {}
    return deep_merge(default_cfg, user_cfg)


def prepare_data(cfg: dict):
    dd = cfg.get("data", {})
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange"),
        symbol=dd.get("symbol"),
        ccxt_options=dd.get("ccxt_options"),
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
    if "volume" not in df.columns:
        df["volume"] = 0
    window = cfg["ml"].get("feat_period", 0)
    df = DataPreprocessor.clean(df, timeframe=dd.get("timeframe"), window=window)
    ret = prepare_ml_dataset(df, cfg)
    if isinstance(ret, tuple) and len(ret) == 4:
        return ret
    if isinstance(ret, tuple) and len(ret) == 3:
        X, y_reg, y_clf = ret  # type: ignore
        mode = cfg["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg
        return X, y, X, y
    from sklearn.model_selection import train_test_split
    X, y_reg, y_clf = ret  # type: ignore
    mode = cfg["ml"].get("target_type", "classification")
    y = y_clf if mode == "classification" else y_reg
    return train_test_split(
        X, y, test_size=cfg["ml"].get("test_size", 0.2), random_state=42
    )


def save_model(model, path: str):
    try:
        model.save(path)  # type: ignore[attr-defined]
    except AttributeError:
        import joblib
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(model, path)


# --------------------------------------------------------------------------- #
# Click CLI
# --------------------------------------------------------------------------- #
@click.group()
def cli():
    """Crypto-Bot CLI"""
    setup_logging()


# --------------------------------------------------------------------------- #
# 1. Backtest – MLStrategy 版
# --------------------------------------------------------------------------- #
@cli.command()
@click.option("--config", "-c", "config_path", required=True, type=click.Path(exists=True))
@click.option("--stats-output", "-s", "stats_output", default="results/backtest_results.csv", type=click.Path(), help="Statistics CSV output path")
@click.option("--show-trades/--no-show-trades", "-t", default=True, help="Print trade log and aggregates after backtest")
def backtest(config_path: str, stats_output: str, show_trades: bool):
    """Walk-forward バックテスト（MLStrategy）。CSV出力と集計を一括で実行。"""
    cfg = load_config(config_path)
    # Ensure the results directory exists for stats output
    os.makedirs(os.path.dirname(stats_output), exist_ok=True)

    # データ取得 & 前処理
    dd = cfg.get("data", {})
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange"),
        symbol=dd.get("symbol"),
        ccxt_options=dd.get("ccxt_options"),
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

    window = cfg["ml"].get("feat_period", 0)
    df = DataPreprocessor.clean(df, timeframe=dd.get("timeframe"), window=window)

    # Walk-forward 分割
    wf = cfg["walk_forward"]
    splits = split_walk_forward(df, wf["train_window"], wf["test_window"], wf["step"])

    # Strategy パラメータ
    sp = cfg["strategy"]["params"]
    model_path = sp.get("model_path", "model.pkl")
    threshold = sp.get("threshold", 0.0)

    # バックテスト実行 & 結果収集
    metrics_list: list[pd.DataFrame] = []
    trade_logs: list[pd.DataFrame] = []
    for _, test_df in splits:
        engine = BacktestEngine(
            price_df=test_df,
            strategy=MLStrategy(
                model_path=model_path,
                threshold=threshold,
                config=cfg,
            ),
            starting_balance=cfg["backtest"]["starting_balance"],
            slippage_rate=cfg["backtest"].get("slippage_rate", 0.0),
        )
        metrics_df, trade_df = engine.run()
        metrics_list.append(metrics_df)
        trade_logs.append(trade_df)

    # Statistics DataFrame 作成
    stats_df = pd.concat(metrics_list, ignore_index=True)
    stats_df.to_csv(stats_output, index=False)
    click.echo(f"Statistics saved to {stats_output!r}")

    # Trade log & ディレクトリ作成
    full_trade_df = pd.concat(trade_logs, ignore_index=True)
    click.echo(f"Trade log columns: {full_trade_df.columns.tolist()}")
    trade_log_csv = cfg["backtest"]["trade_log_csv"]
    os.makedirs(os.path.dirname(trade_log_csv), exist_ok=True)
    full_trade_df.to_csv(trade_log_csv, index=False)
    click.echo(f"Trade log saved to {trade_log_csv!r}")

    # Aggregates
    agg_prefix = cfg["backtest"]["aggregate_out_prefix"]
    os.makedirs(os.path.dirname(agg_prefix), exist_ok=True)
    export_aggregates(full_trade_df, agg_prefix)
    if show_trades:
        click.echo(f"Aggregates saved to {agg_prefix}_{{daily,weekly,monthly}}.csv")

    click.echo(stats_df.to_string(index=False))


# --------------------------------------------------------------------------- #
# 2. optimize-backtest など
# --------------------------------------------------------------------------- #
@cli.command("optimize-backtest")
@click.option("--config", "-c", "config_path", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", "output_csv", default=None, type=click.Path(), help="結果CSV出力パス")
def optimize_backtest_cli(config_path: str, output_csv: str):
    """旧バックテスト最適化コマンド（必要なら残す）。"""
    cfg = load_config(config_path)
    click.echo(">> Starting backtest optimization …")
    df = optimize_backtest(cfg, output_csv=output_csv)
    if output_csv:
        click.echo(f">> Results saved to {output_csv!r}")
    else:
        click.echo(df.to_string(index=False))


# --------------------------------------------------------------------------- #
# 3. ML まわりのコマンド（train / optimize-ml / optimize-and-train / train-best）
# --------------------------------------------------------------------------- #
@cli.command()
@click.option("--config", "-c", "config_path", required=True, type=click.Path(exists=True))
@click.option("--model-type", "-t", "model_type", default=None, help="MLモデルタイプ (lgbm/rf/xgb)")
@click.option("--output", "-o", "output_path", type=click.Path(), default=None, help="モデル保存パス")
def train(config_path: str, model_type: str, output_path: str):
    """MLモデルを学習して保存。"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()
        click.echo(f"Using model_type: {cfg['ml']['model_type']}")

    X_tr, y_tr, X_val, y_val = prepare_data(cfg)
    mode = cfg["ml"].get("target_type", "classification")
    click.echo(f"Training {mode} model on {len(X_tr)} samples")

    if model_type:
        model = train_best_model(cfg, X_tr, y_tr, X_val, y_val)
    else:
        if mode == "classification":
            model = LogisticRegression()
        else:
            from sklearn.linear_model import LinearRegression  # noqa: F401
            model = LinearRegression()
        model.fit(X_tr, y_tr)

    out_path = output_path or cfg.get("output", {}).get("model_path", "model.pkl")
    save_model(model, out_path)
    click.echo(f"Model saved to {out_path!r}")


@cli.command("optimize-ml")
@click.option("--config", "-c", "config_path", required=True, type=click.Path(exists=True))
@click.option("--model-type", "-t", "model_type", type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False), default=None)
def optimize_ml(config_path: str, model_type: str):
    """MLモデルのハイパーパラ最適化のみ実行。"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()
    study = run_optuna(cfg)
    click.echo(f"Best trial value: {study.best_value}")
    click.echo(f"Best params: {study.best_params}")


@cli.command("optimize-and-train")
@click.option("--config", "-c", "config_path", required=True, type=click.Path(exists=True))
@click.option("--trials-out", "-t", "trials_path", default=None, type=click.Path())
@click.option("--model-out", "-m", "model_path", default=None, type=click.Path())
@click.option("--model-type", "-T", "model_type", type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False), default=None)
def optimize_and_train(config_path: str, trials_path: str, model_path: str, model_type: str):
    """Optuna → トライアル保存 → 最良モデル再学習＆保存。"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    logging.basicConfig(level=logging.WARNING, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
    click.echo(">> Starting hyperparameter optimization …")
    study = run_optuna(cfg)

    # ------------------------------------------------------------------
    # モデル保存パスを決定（指定が無ければ model/best_model.pkl）
    # ------------------------------------------------------------------
    if not model_path:
        model_path = "model/best_model.pkl"
        click.echo(f">> --model-out 未指定のため {model_path!r} へ保存します")

    if trials_path:
        study.trials_dataframe().to_csv(trials_path, index=False)
        click.echo(f">> All trials saved to {trials_path!r}")

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

    estimator = create_model(mtype, **best_params) if mode == "classification" else None
    if estimator is None:
        from sklearn.linear_model import LinearRegression  # fallback
        estimator = LinearRegression(**best_params) if best_params else LinearRegression()
    estimator.fit(X, y)
    # sklearn Estimator もしくは MLModel を適切に保存
    save_model(estimator, model_path)
    click.echo(f">> Final model saved to {model_path!r}")

    click.echo(">> optimize-and-train complete.")



@cli.command("train-best")
@click.option("--config", "-c", "config_path", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", "model_path", required=True, type=click.Path())
@click.option("--model-type", "-t", "model_type", type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False), default=None)
def train_best(config_path: str, model_path: str, model_type: str):
    """最良パラメータで全データ再学習 & モデル保存。"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    click.echo(">> Running optimization and training best model …")
    train_best_model(cfg, model_path)


if __name__ == "__main__":
    cli()
