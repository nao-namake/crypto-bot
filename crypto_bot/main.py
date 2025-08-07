#!/usr/bin/env python3
"""
Crypto Bot - Main entry point
Phase 14: Refactored architecture
"""
import logging
import os
import signal
import sys
import threading

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import version
from crypto_bot import __version__


# Setup logging
def setup_logging():
    """LOG_LEVEL 環境変数でロガーを初期化"""
    level_name = os.getenv("CRYPTO_BOT_LOG_LEVEL", "INFO").upper()
    if hasattr(logging, level_name):
        numeric_level = getattr(logging, level_name)
    else:
        numeric_level = logging.INFO
    # より詳細なログフォーマット
    log_format = "[%(asctime)s] %(levelname)-8s %(name)-20s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        format=log_format,
        datefmt=date_format,
        level=numeric_level,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


setup_logging()
logger = logging.getLogger(__name__)

# Import CLI commands
import click

from crypto_bot.cli.backtest import backtest_command
from crypto_bot.cli.live import live_bitbank_command
from crypto_bot.cli.model import retrain_command, validate_model_command
from crypto_bot.cli.online import (
    drift_monitor_command,
    online_status_command,
    online_train_command,
    retrain_schedule_command,
)
from crypto_bot.cli.optimize import optimize_backtest_command
from crypto_bot.cli.stats import stats_command
from crypto_bot.cli.strategy import list_strategies_command, strategy_info_command
from crypto_bot.cli.train import (
    optimize_and_train_command,
    optimize_ml_command,
    train_best_command,
    train_command,
)
from crypto_bot.cli.validate import diagnose_apis_command, validate_config_command


# Create CLI group
@click.group()
@click.version_option(__version__, prog_name="crypto_bot")
def cli():
    """
    暗号通貨自動取引ボット（crypto_bot）

    97特徴量完全実装システムによる高精度取引システム。
    Phase 14リファクタリング完了版。
    """
    pass


# Add commands to CLI group
cli.add_command(backtest_command, name="backtest")
cli.add_command(live_bitbank_command, name="live-bitbank")
cli.add_command(train_command, name="train")
cli.add_command(optimize_ml_command, name="optimize-ml")
cli.add_command(optimize_and_train_command, name="optimize-and-train")
cli.add_command(train_best_command, name="train-best")
cli.add_command(online_train_command, name="online-train")
cli.add_command(online_status_command, name="online-status")
cli.add_command(drift_monitor_command, name="drift-monitor")
cli.add_command(retrain_schedule_command, name="retrain-schedule")
cli.add_command(optimize_backtest_command, name="optimize-backtest")
cli.add_command(list_strategies_command, name="list-strategies")
cli.add_command(strategy_info_command, name="strategy-info")
cli.add_command(validate_config_command, name="validate-config")
cli.add_command(diagnose_apis_command, name="diagnose-apis")
cli.add_command(validate_model_command, name="validate-model")
cli.add_command(retrain_command, name="retrain")
cli.add_command(stats_command, name="stats")


# --------------------------------------------------------------------------- #
# Signal handlers
# --------------------------------------------------------------------------- #
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"🛑 Received signal {signum}. Shutting down gracefully...")

    # Stop API server if running
    try:
        from crypto_bot.api.health import shutdown_api_server

        shutdown_api_server()
    except Exception as e:
        logger.error(f"Error shutting down API server: {e}")

    # Exit cleanly
    logger.info("👋 Shutdown complete. Goodbye!")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def main():
    """Run the main application entry point"""
    # Environment check
    if not os.getenv("BITBANK_API_KEY") or not os.getenv("BITBANK_API_SECRET"):
        logger.warning(
            "⚠️ Bitbank API credentials not found in environment variables. "
            "Some features may not work properly."
        )

    # Cloud Run environment detection
    port = os.getenv("PORT", "8080")
    if os.getenv("K_SERVICE"):
        logger.info(f"🌩️ Running in Cloud Run environment on port {port}")

        # Start API server in background for Cloud Run health checks
        from crypto_bot.api.health import start_api_server

        api_thread = threading.Thread(
            target=start_api_server,
            kwargs={"host": "0.0.0.0", "port": int(port)},
            daemon=True,
        )
        api_thread.start()
        logger.info(f"🌐 API server started on port {port}")
    else:
        logger.info("💻 Running in local environment")

    # Run CLI
    try:
        cli()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback

        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
