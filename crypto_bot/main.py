# =============================================================================
# ファイル名: crypto_bot/main.py
# 説明:
# Crypto-Bot CLI エントリポイント
#   - MLStrategy を用いたバックテスト/ML ワークフローを統括
#   - バックテスト・最適化・学習・モデル保存などをカバー
# =============================================================================
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import click
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from crypto_bot.backtest.analysis import export_aggregates
from crypto_bot.backtest.engine import BacktestEngine
from crypto_bot.backtest.optimizer import (  # noqa: F401  他コマンドで使用
    ParameterOptimizer,
    optimize_backtest,
)
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.ml.optimizer import _load_and_preprocess_data
from crypto_bot.ml.optimizer import optimize_ml as run_optuna
from crypto_bot.ml.optimizer import train_best_model
from crypto_bot.ml.preprocessor import prepare_ml_dataset
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.strategy.ml_strategy import MLStrategy


# --------------------------------------------------------------------------- #
# ユーティリティ
# --------------------------------------------------------------------------- #
def ensure_dir_for_file(path: str):
    """親ディレクトリが無ければ作成する"""
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)


def setup_logging():
    """LOG_LEVEL 環境変数でロガーを初期化"""
    level_name = os.getenv("CRYPTO_BOT_LOG_LEVEL", "INFO").upper()
    numeric_level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)-5s %(name)s: %(message)s",
        level=numeric_level,
    )


def deep_merge(default: dict, override: dict) -> dict:
    """ネストされた辞書を再帰的にマージ"""
    for k, v in override.items():
        if k in default and isinstance(default[k], dict) and isinstance(v, dict):
            default[k] = deep_merge(default[k], v)
        else:
            default[k] = v
    return default


def load_config(path: str) -> dict:
    base = Path(__file__).parent.parent
    default_path = base / "config" / "default.yml"
    with open(default_path, "r") as f:
        default_cfg = yaml.safe_load(f) or {}
    with open(path, "r") as f:
        user_cfg = yaml.safe_load(f) or {}
    return deep_merge(default_cfg, user_cfg)


# --------------------------------------------------------------------------- #
# データ準備
# --------------------------------------------------------------------------- #
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

    if df.empty:
        return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series()

    # monkey-patch を尊重するため遅延 import
    from crypto_bot.ml import preprocessor as _mlprep

    ret = _mlprep.prepare_ml_dataset(df, cfg)
    if isinstance(ret, tuple) and len(ret) == 4:
        return ret

    if isinstance(ret, tuple) and len(ret) == 3:
        X, y_reg, y_clf = ret
        mode = cfg["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg
        split = train_test_split(
            X, y, test_size=cfg["ml"].get("test_size", 0.2), random_state=42
        )
        return split  # X_tr, X_val, y_tr, y_val

    return ret


def save_model(model, path: str):
    """joblib にフォールバックしてモデルを保存"""
    try:
        model.save(path)  # type: ignore[attr-defined]
    except AttributeError:
        import joblib

        ensure_dir_for_file(path)
        joblib.dump(model, path)


# --------------------------------------------------------------------------- #
# Click CLI グループ
# --------------------------------------------------------------------------- #
@click.group()
def cli():
    """Crypto-Bot CLI"""
    setup_logging()


# --------------------------------------------------------------------------- #
# 1. Backtest コマンド
# --------------------------------------------------------------------------- #
@cli.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--stats-output",
    "-s",
    "stats_output",
    default="results/backtest_results.csv",
    type=click.Path(),
    help="Statistics CSV output path",
)
@click.option(
    "--show-trades/--no-show-trades",
    "-t",
    default=True,
    help="Print trade log and aggregates after backtest",
)
def backtest(config_path: str, stats_output: str, show_trades: bool):
    """Walk-forward バックテスト（MLStrategy）"""
    cfg = load_config(config_path)
    ensure_dir_for_file(stats_output)

    # データ取得
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

    # Walk-forward split
    wf = cfg["walk_forward"]
    splits = split_walk_forward(df, wf["train_window"], wf["test_window"], wf["step"])

    # Strategy params
    sp = cfg["strategy"]["params"]
    model_path = sp.get("model_path", "model.pkl")
    threshold = sp.get("threshold", 0.0)

    metrics_list, trade_logs = [], []
    for _, test_df in splits:
        engine = BacktestEngine(
            price_df=test_df,
            strategy=MLStrategy(model_path=model_path, threshold=threshold, config=cfg),
            starting_balance=cfg["backtest"]["starting_balance"],
            slippage_rate=cfg["backtest"].get("slippage_rate", 0.0),
        )
        m_df, t_df = engine.run()
        metrics_list.append(m_df)
        trade_logs.append(t_df)

    stats_df = pd.concat(metrics_list, ignore_index=True)
    stats_df.to_csv(stats_output, index=False)
    click.echo(f"Statistics saved to {stats_output!r}")

    full_trade_df = pd.concat(trade_logs, ignore_index=True)
    trade_log_csv = cfg["backtest"].get("trade_log_csv", "results/trade_log.csv")
    ensure_dir_for_file(trade_log_csv)
    full_trade_df.to_csv(trade_log_csv, index=False)
    click.echo(f"Trade log saved to {trade_log_csv!r}")

    agg_prefix = cfg["backtest"].get("aggregate_out_prefix", "results/agg")
    ensure_dir_for_file(agg_prefix + "_dummy")
    export_aggregates(full_trade_df, agg_prefix)
    if show_trades:
        click.echo(f"Aggregates saved to {agg_prefix}_{{daily,weekly,monthly}}.csv")

    click.echo(stats_df.to_string(index=False))


# --------------------------------------------------------------------------- #
# 2. optimize-backtest
# --------------------------------------------------------------------------- #
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
    help="結果 CSV 出力パス",
)
def optimize_backtest_cli(config_path: str, output_csv: str):
    """バックテスト最適化"""
    cfg = load_config(config_path)
    click.echo(">> Starting backtest optimization …")
    df = optimize_backtest(cfg, output_csv=output_csv)
    if output_csv:
        click.echo(f">> Results saved to {output_csv!r}")
    else:
        click.echo(df.to_string(index=False))


# --------------------------------------------------------------------------- #
# 3-A. train コマンド
# --------------------------------------------------------------------------- #
@cli.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type", "-t", default=None, help="ML モデルタイプ (lgbm / rf / xgb)"
)
@click.option(
    "--output",
    "-o",
    "output_path",
    default=None,
    type=click.Path(),
    help="モデル保存パス",
)
def train(config_path: str, model_type: str, output_path: str):
    """ML モデルを学習して保存"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()
        click.echo(f"Using model_type: {cfg['ml']['model_type']}")

    ret = prepare_data(cfg)

    if isinstance(ret, tuple) and len(ret) == 4:
        X_tr, y_tr, X_val, y_val = ret
        train_samples = len(X_tr)
    else:
        X, y_reg, y_clf = ret  # type: ignore
        mode = cfg["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg
        if len(X) < 2:
            click.echo("データ数が 2 未満です。学習をスキップします。")
            sys.exit(0)
        X_tr, X_val, y_tr, y_val = train_test_split(
            X, y, test_size=cfg["ml"].get("test_size", 0.2), random_state=42
        )
        train_samples = len(X_tr)

    mode = cfg["ml"].get("target_type", "classification")
    click.echo(f"Training {mode} model on {train_samples} samples")

    if train_samples <= 1:
        click.echo("訓練データが 1 サンプル以下のため学習を中止します。")
        sys.exit(0)

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


# --------------------------------------------------------------------------- #
# 3-B. optimize-ml
# --------------------------------------------------------------------------- #
@cli.command("optimize-ml")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type",
    "-t",
    type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False),
    default=None,
)
def optimize_ml(config_path: str, model_type: str):
    """ハイパーパラ最適化のみ実行"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()
    study = run_optuna(cfg)
    click.echo(f"Best trial value: {study.best_value}")
    click.echo(f"Best params: {study.best_params}")


# --------------------------------------------------------------------------- #
# 3-C. optimize-and-train
# --------------------------------------------------------------------------- #
@cli.command("optimize-and-train")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--trials-out", "-t", "trials_path", default=None, type=click.Path())
@click.option("--model-out", "-m", "model_path", default=None, type=click.Path())
@click.option(
    "--model-type",
    "-T",
    type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False),
    default=None,
)
def optimize_and_train(
    config_path: str, trials_path: str, model_path: str, model_type: str
):
    """Optuna → 再学習 → モデル保存"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    logging.basicConfig(
        level=logging.WARNING,
        format=("[%(asctime)s] " "%(levelname)s " "%(name)s: " "%(message)s"),
    )
    click.echo(">> Starting hyperparameter optimization …")
    study = run_optuna(cfg)

    if not model_path:
        model_path = "model/best_model.pkl"
        click.echo(f">> --model-out 未指定のため {model_path!r} へ保存します")

    if trials_path:
        ensure_dir_for_file(trials_path)
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

        if best_params:
            estimator = LinearRegression(**best_params)
        else:
            estimator = LinearRegression()
    estimator.fit(X, y)
    save_model(estimator, model_path)
    click.echo(f">> Final model saved to {model_path!r}")
    click.echo(">> optimize-and-train complete.")


# --------------------------------------------------------------------------- #
# 3-D. train-best
# --------------------------------------------------------------------------- #
@cli.command("train-best")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--output", "-o", "model_path", required=True, type=click.Path())
@click.option(
    "--model-type",
    "-t",
    type=click.Choice(["lgbm", "rf", "xgb"], case_sensitive=False),
    default=None,
)
def train_best(config_path: str, model_path: str, model_type: str):
    """ベストパラメータで全データ再学習 & 保存"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    click.echo(">> Running optimization and training best model …")
    train_best_model(cfg, model_path)


if __name__ == "__main__":
    cli()
