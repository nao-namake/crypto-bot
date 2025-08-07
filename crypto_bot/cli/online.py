"""
Online learning and monitoring CLI commands
"""

import json
import logging
import sys
import threading
import time

import click
import pandas as pd

from crypto_bot.config import load_config
from crypto_bot.utils.config_state import set_current_config
from crypto_bot.utils.file import ensure_dir_for_file

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-path", "-m", default="models/online_model.pkl", help="Online model path"
)
@click.option("--learning-rate", "-lr", type=float, default=0.01)
@click.option(
    "--update-interval", "-i", type=int, default=3600, help="Update interval in seconds"
)
@click.option("--batch-size", "-b", type=int, default=32)
@click.option("--validation-split", "-v", type=float, default=0.2)
@click.option("--max-memory", type=int, default=10000, help="Maximum samples in memory")
@click.option(
    "--drift-threshold", type=float, default=0.1, help="Drift detection threshold"
)
def online_train_command(
    config_path: str,
    model_path: str,
    learning_rate: float,
    update_interval: int,
    batch_size: int,
    validation_split: float,
    max_memory: int,
    drift_threshold: float,
):
    """Start online learning system"""
    cfg = load_config(config_path)
    set_current_config(cfg)

    try:
        from crypto_bot.data.fetcher import MarketDataFetcher
        from crypto_bot.ml.online_learning import OnlineLearningSystem

        # データフェッチャー初期化
        dd = cfg.get("data", {})
        fetcher = MarketDataFetcher(
            exchange_id=dd.get("exchange", "bitbank"),
            symbol=dd.get("symbol", "BTC/JPY"),
            ccxt_options=dd.get("ccxt_options", {}),
        )

        # オンライン学習システム初期化
        online_system = OnlineLearningSystem(
            model_path=model_path,
            learning_rate=learning_rate,
            batch_size=batch_size,
            validation_split=validation_split,
            max_memory_size=max_memory,
            drift_threshold=drift_threshold,
            update_interval=update_interval,
        )

        click.echo("🚀 Starting online learning system...")
        click.echo(f"Model: {model_path}")
        click.echo(f"Update interval: {update_interval}s")
        click.echo(f"Batch size: {batch_size}")
        click.echo(f"Max memory: {max_memory} samples")

        # メインループ
        while True:
            try:
                # 最新データ取得
                since = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24)
                price_df = fetcher.get_price_df(timeframe="1h", since=since, limit=100)

                if not price_df.empty:
                    # オンライン更新
                    metrics = online_system.update(price_df)

                    if metrics:
                        click.echo(f"📊 Update completed: {metrics}")

                # 待機
                time.sleep(update_interval)

            except KeyboardInterrupt:
                click.echo("\n🛑 Shutting down online learning system...")
                break
            except Exception as e:
                logger.error(f"Error in online learning loop: {e}")
                time.sleep(60)  # エラー時は1分待機

    except ImportError as e:
        click.echo(f"Error: Online learning module not available: {e}", err=True)
        sys.exit(1)


@click.command()
@click.option("--export", "-e", type=click.Path(), help="Export status to JSON file")
def online_status_command(export: str):
    """Show online learning system status"""
    try:
        from crypto_bot.ml.online_learning import get_online_status

        status = get_online_status()

        if not status:
            click.echo("No online learning system is currently active.")
            return

        # ステータス表示
        click.echo("\n=== Online Learning System Status ===")
        click.echo(f"Active: {status.get('active', False)}")
        click.echo(f"Model Path: {status.get('model_path', 'N/A')}")
        click.echo(f"Last Update: {status.get('last_update', 'Never')}")
        click.echo(f"Total Updates: {status.get('total_updates', 0)}")
        click.echo(f"Memory Usage: {status.get('memory_usage', 0)} samples")

        if status.get("performance"):
            click.echo("\n📊 Performance Metrics:")
            for metric, value in status["performance"].items():
                click.echo(f"  {metric}: {value:.4f}")

        if status.get("drift_detection"):
            click.echo("\n🔍 Drift Detection:")
            click.echo(
                f"  Drift Detected: {status['drift_detection'].get('detected', False)}"
            )
            click.echo(
                f"  Drift Score: {status['drift_detection'].get('score', 0):.4f}"
            )

        # JSONエクスポート
        if export:
            ensure_dir_for_file(export)
            with open(export, "w") as f:
                json.dump(status, f, indent=2, default=str)
            click.echo(f"\n✅ Status exported to {export}")

    except ImportError:
        click.echo("Error: Online learning module not available.", err=True)
    except Exception as e:
        click.echo(f"Error retrieving status: {e}", err=True)


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--log-file", "-l", default="drift_monitor.log", help="Log file path")
@click.option(
    "--duration", "-d", type=int, default=0, help="Monitoring duration (0=infinite)"
)
def drift_monitor_command(config_path: str, log_file: str, duration: int):
    """Start drift monitoring system"""
    cfg = load_config(config_path)
    set_current_config(cfg)

    try:
        from crypto_bot.ml.drift_detection import DriftMonitor

        # ドリフトモニター初期化
        monitor = DriftMonitor(config=cfg, log_file=log_file)

        click.echo("🔍 Starting drift monitoring system...")
        click.echo(f"Log file: {log_file}")
        click.echo(f"Duration: {'infinite' if duration == 0 else f'{duration}s'}")

        # モニタリング開始
        monitor.start_monitoring()

        # 指定時間実行
        if duration > 0:
            time.sleep(duration)
            monitor.stop_monitoring()
            click.echo(f"✅ Monitoring completed after {duration}s")
        else:
            click.echo("Press Ctrl+C to stop monitoring...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                monitor.stop_monitoring()
                click.echo("\n✅ Monitoring stopped by user")

    except ImportError:
        click.echo("Error: Drift detection module not available.", err=True)
    except Exception as e:
        click.echo(f"Error in drift monitoring: {e}", err=True)


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--model-id", "-m", required=True, help="Model identifier for scheduling")
@click.option(
    "--trigger",
    "-t",
    multiple=True,
    type=click.Choice(["daily", "weekly", "monthly", "drift", "performance"]),
    default=["weekly"],
    help="Retraining triggers",
)
@click.option("--start/--stop", default=True, help="Start or stop the scheduler")
def retrain_schedule_command(
    config_path: str, model_id: str, trigger: tuple, start: bool
):
    """Manage automatic retraining scheduler"""
    cfg = load_config(config_path)
    set_current_config(cfg)

    try:
        from crypto_bot.ml.retraining_scheduler import RetrainingScheduler

        scheduler = RetrainingScheduler(config=cfg, model_id=model_id)

        if start:
            # スケジューラー開始
            click.echo(f"📅 Starting retraining scheduler for model: {model_id}")
            click.echo(f"Triggers: {', '.join(trigger)}")

            # トリガー設定
            for t in trigger:
                if t == "daily":
                    scheduler.add_daily_trigger()
                elif t == "weekly":
                    scheduler.add_weekly_trigger()
                elif t == "monthly":
                    scheduler.add_monthly_trigger()
                elif t == "drift":
                    scheduler.add_drift_trigger()
                elif t == "performance":
                    scheduler.add_performance_trigger()

            # バックグラウンドで実行
            scheduler_thread = threading.Thread(target=scheduler.run, daemon=True)
            scheduler_thread.start()

            click.echo("✅ Scheduler started successfully")
            click.echo("Press Ctrl+C to stop...")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                scheduler.stop()
                click.echo("\n✅ Scheduler stopped")
        else:
            # スケジューラー停止
            click.echo(f"🛑 Stopping retraining scheduler for model: {model_id}")
            scheduler.stop()
            click.echo("✅ Scheduler stopped successfully")

    except ImportError:
        click.echo("Error: Retraining scheduler module not available.", err=True)
    except Exception as e:
        click.echo(f"Error managing scheduler: {e}", err=True)
