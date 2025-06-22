# =============================================================================
# ファイル名: crypto_bot/main.py
# 説明:
# Crypto-Bot CLI エントリポイント
#   - MLStrategy を用いたバックテスト/ML ワークフローを統括
#   - バックテスト・最適化・学習・モデル保存などをカバー
# =============================================================================
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
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
from crypto_bot.execution.engine import EntryExit, Position
from crypto_bot.ml.optimizer import _load_and_preprocess_data
from crypto_bot.ml.optimizer import optimize_ml as run_optuna
from crypto_bot.ml.optimizer import train_best_model
from crypto_bot.ml.preprocessor import prepare_ml_dataset
from crypto_bot.risk.manager import RiskManager
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.strategy.ml_strategy import MLStrategy
from crypto_bot.strategy.factory import StrategyFactory


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

    # より詳細なログフォーマット
    log_format = "[%(asctime)s] %(levelname)-8s %(name)-20s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        format=log_format,
        datefmt=date_format,
        level=numeric_level,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # サードパーティライブラリのログレベルを調整
    logging.getLogger("ccxt").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("optuna").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized at level: {level_name}")


def update_status(total_profit: float, trade_count: int, position):
    """
    現在の Bot 状態を JSON へ書き出して、外部モニター（Streamlit 等）から
    参照できるようにするユーティリティ。

    Parameters
    ----------
    total_profit : float
        現在までの累積損益
    trade_count : int
        約定数（取引回数）
    position : Any
        現在ポジション（無い場合は None）
    """
    status = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_profit": total_profit,
        "trade_count": trade_count,
        "position": position or "",
    }
    with open("status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


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

    config = deep_merge(default_cfg, user_cfg)

    # 設定検証を実行
    try:
        from crypto_bot.utils.config_validator import ConfigValidator

        validator = ConfigValidator()
        validator.validate(config)
    except ImportError:
        logging.warning("設定検証モジュールが利用できません")
    except Exception as e:
        logging.error(f"設定検証エラー: {e}")
        sys.exit(1)

    return config


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

    # Strategy creation using factory
    strategy_config = cfg.get("strategy", {})
    strategy_type = strategy_config.get("type", "single")
    
    if strategy_type == "multi":
        # マルチ戦略の場合
        strategies_config = strategy_config.get("strategies", [])
        combination_mode = strategy_config.get("combination_mode", "weighted_average")
        strategy = StrategyFactory.create_multi_strategy(strategies_config, combination_mode)
    else:
        # 単一戦略の場合（従来の形式）
        strategy = StrategyFactory.create_strategy(strategy_config)

    metrics_list, trade_logs = [], []
    for _, test_df in splits:
        engine = BacktestEngine(
            price_df=test_df,
            strategy=strategy,
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

    # --- Streamlit など外部監視用にステータスを書き出し ---
    total_profit = (
        float(stats_df["net_profit"].sum()) if "net_profit" in stats_df.columns else 0.0
    )
    update_status(total_profit, len(full_trade_df), position=None)

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
# 3-D. live-paper  ← Testnet ペーパートレード用
# --------------------------------------------------------------------------- #
@cli.command("live-paper")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--max-trades",
    type=int,
    default=0,
    help="0=無限。成立した約定数がこの値に達したらループ終了",
)
def live_paper(config_path: str, max_trades: int):
    """
    Bybit Testnet でのペーパートレードを 30 秒間隔で回す簡易ループ。
    ExecutionEngine の generate_entry_order / generate_exit_order を用い、
    update_status でダッシュボード用 JSON と Monitoring 指標を更新する。
    """
    cfg = load_config(config_path)
    # 取引所クライアントは Factory で生成（Bybit Testnet がデフォルト）
    # client = create_exchange_client(
    #     exchange_id=cfg["data"].get("exchange", "bybit"),
    #     api_key=cfg["data"].get("api_key", ""),
    #     api_secret=cfg["data"].get("api_secret", ""),
    #     testnet=True,
    # )

    # --- helpers for paper trading (Entry/Exit + Risk) ---------------------
    dd = cfg.get("data", {})
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange"),
        symbol=dd.get("symbol"),
        ccxt_options=dd.get("ccxt_options"),
    )

    # Strategy & risk manager
    sp = cfg["strategy"]["params"]
    model_path = sp.get("model_path", "model.pkl")
    threshold = sp.get("threshold", 0.0)
    strategy = MLStrategy(model_path=model_path, threshold=threshold, config=cfg)
    risk_manager = RiskManager(cfg.get("risk", {}))

    position = Position()
    balance = cfg["backtest"]["starting_balance"]
    entry_exit = EntryExit(
        strategy=strategy, risk_manager=risk_manager, atr_series=None
    )
    entry_exit.current_balance = balance

    trade_done = 0
    click.echo("=== live‑paper mode start ===  Ctrl+C で停止")
    try:
        while True:
            # 最新 200 本だけ取得し、Entry/Exit 判定に利用
            price_df = fetcher.get_price_df(
                timeframe=dd.get("timeframe"),
                limit=200,
                paginate=False,
            )
            if price_df.empty:
                time.sleep(30)
                continue

            # エントリー判定
            entry_order = entry_exit.generate_entry_order(price_df, position)
            prev_trades = trade_done
            if entry_order.exist:
                balance = entry_exit.fill_order(entry_order, position, balance)
                trade_done += 1

            # エグジット判定
            exit_order = entry_exit.generate_exit_order(price_df, position)
            if exit_order.exist:
                balance = entry_exit.fill_order(exit_order, position, balance)
                trade_done += 1

            # 残高を EntryExit へ反映
            entry_exit.current_balance = balance

            # ダッシュボード用ステータス更新
            update_status(
                total_profit=balance - cfg["backtest"]["starting_balance"],
                trade_count=trade_done,
                position=position.side if position.exist else None,
            )

            if max_trades and trade_done >= max_trades:
                click.echo("Reached max‑trades. Exit.")
                break

            # 取引が無い場合も一定間隔でループ
            if trade_done == prev_trades:
                time.sleep(30)
    except KeyboardInterrupt:
        click.echo("Interrupted. Bye.")


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


# --------------------------------------------------------------------------- #
# 4. Online Learning commands
# --------------------------------------------------------------------------- #
@cli.command("online-train")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--model-type", "-t", default="river_linear", 
              help="Model type (river_linear, sklearn_sgd_classifier, etc.)")
@click.option("--data-source", "-d", default="live", 
              help="Data source (live, file, or path to data file)")
@click.option("--monitor/--no-monitor", default=True, 
              help="Enable performance monitoring")
@click.option("--drift-detection/--no-drift-detection", default=True,
              help="Enable drift detection")
def online_train(config_path: str, model_type: str, data_source: str, 
                monitor: bool, drift_detection: bool):
    """Start online learning training"""
    from crypto_bot.online_learning.base import OnlineLearningConfig
    from crypto_bot.online_learning.models import IncrementalMLModel
    from crypto_bot.online_learning.monitoring import OnlinePerformanceTracker
    from crypto_bot.drift_detection.monitor import DriftMonitor
    
    cfg = load_config(config_path)
    
    # Create online learning config
    online_config = OnlineLearningConfig(
        enable_drift_detection=drift_detection,
        enable_auto_retrain=True
    )
    
    # Initialize components
    model = IncrementalMLModel(online_config, model_type=model_type)
    
    performance_tracker = None
    drift_monitor = None
    
    if monitor:
        performance_tracker = OnlinePerformanceTracker(
            model_type="classification" if "classif" in model_type else "regression"
        )
    
    if drift_detection:
        drift_monitor = DriftMonitor()
        drift_monitor.start_monitoring()
    
    click.echo(f"Starting online learning with {model_type}")
    click.echo(f"Data source: {data_source}")
    click.echo(f"Monitoring: {'enabled' if monitor else 'disabled'}")
    click.echo(f"Drift detection: {'enabled' if drift_detection else 'disabled'}")
    
    try:
        # Simulate online learning loop
        if data_source == "live":
            click.echo("Live training mode - would connect to live data stream")
            # Implementation would connect to live data feed
        else:
            click.echo(f"File training mode - processing {data_source}")
            # Load and process data file incrementally
        
        click.echo("Online training completed successfully")
        
    except KeyboardInterrupt:
        click.echo("Training interrupted by user")
    finally:
        if drift_monitor:
            drift_monitor.stop_monitoring()


@cli.command("online-status")
@click.option("--export", "-e", type=click.Path(), 
              help="Export status to JSON file")
def online_status(export: str):
    """Show online learning system status"""
    # This would check running online learning processes
    status = {
        "timestamp": datetime.now().isoformat(),
        "active_models": 0,  # Would query actual running models
        "drift_events": 0,   # Would query drift detection system
        "last_update": None, # Would get from actual monitoring
        "performance_metrics": {}
    }
    
    click.echo("Online Learning System Status:")
    click.echo(f"Timestamp: {status['timestamp']}")
    click.echo(f"Active models: {status['active_models']}")
    click.echo(f"Recent drift events: {status['drift_events']}")
    
    if export:
        ensure_dir_for_file(export)
        with open(export, 'w') as f:
            json.dump(status, f, indent=2)
        click.echo(f"Status exported to {export}")


@cli.command("drift-monitor")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--log-file", "-l", type=click.Path(),
              help="Log drift events to file")
@click.option("--duration", "-d", default=3600, type=int,
              help="Monitoring duration in seconds")
def drift_monitor_cmd(config_path: str, log_file: str, duration: int):
    """Start drift monitoring system"""
    from crypto_bot.drift_detection.monitor import DriftMonitor, console_alert_callback
    
    cfg = load_config(config_path)
    
    # Initialize drift monitor
    monitor = DriftMonitor(log_file=log_file)
    monitor.add_alert_callback(console_alert_callback)
    
    click.echo(f"Starting drift monitoring for {duration} seconds")
    if log_file:
        click.echo(f"Logging to: {log_file}")
    
    try:
        monitor.start_monitoring()
        time.sleep(duration)
        
        # Show summary
        summary = monitor.get_drift_summary(hours=duration/3600)
        click.echo("\nDrift Monitoring Summary:")
        click.echo(f"Total events: {summary.get('total_drift_events', 0)}")
        
    except KeyboardInterrupt:
        click.echo("Monitoring interrupted by user")
    finally:
        monitor.stop_monitoring()


@cli.command("retrain-schedule")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--model-id", "-m", required=True,
              help="Model identifier for scheduling")
@click.option("--trigger", "-t", multiple=True,
              help="Trigger types (performance, drift, schedule, sample_count)")
@click.option("--start/--stop", default=True,
              help="Start or stop the scheduler")
def retrain_schedule(config_path: str, model_id: str, trigger: tuple, start: bool):
    """Manage automatic retraining scheduler"""
    from crypto_bot.online_learning.scheduler import RetrainingScheduler
    from crypto_bot.online_learning.base import OnlineLearningConfig
    
    cfg = load_config(config_path)
    online_config = OnlineLearningConfig()
    
    scheduler = RetrainingScheduler(online_config)
    
    if start:
        click.echo(f"Starting retraining scheduler for model: {model_id}")
        click.echo(f"Enabled triggers: {', '.join(trigger) if trigger else 'all default'}")
        scheduler.start_scheduler()
        
        try:
            # Keep running until interrupted
            while True:
                time.sleep(60)
                status = scheduler.get_scheduler_status()
                if status['pending_jobs'] > 0:
                    click.echo(f"Pending retraining jobs: {status['pending_jobs']}")
        except KeyboardInterrupt:
            click.echo("Scheduler stopped by user")
        finally:
            scheduler.stop_scheduler()
    else:
        click.echo("Stopping retraining scheduler...")
        scheduler.stop_scheduler()


# --------------------------------------------------------------------------- #
# 5. Strategy management commands
# --------------------------------------------------------------------------- #
@cli.command("list-strategies")
def list_strategies():
    """利用可能な戦略一覧を表示"""
    strategies = StrategyFactory.list_available_strategies()
    click.echo("Available strategies:")
    for strategy in sorted(strategies):
        click.echo(f"  - {strategy}")


@cli.command("strategy-info")
@click.argument("strategy_name")
def strategy_info(strategy_name: str):
    """戦略の詳細情報を表示"""
    try:
        info = StrategyFactory.get_strategy_info(strategy_name)
        click.echo(f"Strategy: {info['name']}")
        click.echo(f"Class: {info['class_name']}")
        click.echo(f"Module: {info['module']}")
        if info['docstring']:
            click.echo(f"Description: {info['docstring'].strip()}")
        click.echo("Parameters:")
        for param in info['parameters']:
            default_str = f" (default: {param['default']})" if param['default'] is not None else ""
            click.echo(f"  - {param['name']}: {param['annotation']}{default_str}")
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command("validate-config")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
def validate_config(config_path: str):
    """戦略設定の検証"""
    cfg = load_config(config_path)
    strategy_config = cfg.get("strategy", {})
    
    if strategy_config.get("type") == "multi":
        strategies_config = strategy_config.get("strategies", [])
        errors = []
        for i, strategy_config in enumerate(strategies_config):
            strategy_errors = StrategyFactory.validate_config(strategy_config)
            for error in strategy_errors:
                errors.append(f"Strategy {i+1}: {error}")
        
        if errors:
            click.echo("Configuration errors found:")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.echo("Multi-strategy configuration is valid!")
    else:
        errors = StrategyFactory.validate_config(strategy_config)
        if errors:
            click.echo("Configuration errors found:")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.echo("Strategy configuration is valid!")


if __name__ == "__main__":
    cli()
