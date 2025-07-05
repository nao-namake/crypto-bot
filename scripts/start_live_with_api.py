#!/usr/bin/env python3
"""
ライブトレーディング + API サーバー統合起動スクリプト

Docker環境でライブトレーディングとAPIサーバーを同時に起動します。
- APIサーバー: バックグラウンドでヘルスチェック・監視機能を提供
- ライブトレード: メインプロセスで取引を実行
"""

import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def start_api_server():
    """APIサーバーをバックグラウンドで起動"""
    try:
        import uvicorn

        from crypto_bot.api.server import app

        logger.info("Starting API server on port 8080...")

        # uvicornサーバーを起動
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8080,
            log_level="info",
            access_log=True,
            workers=1
        )
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        sys.exit(1)


def start_live_trading():
    """ライブトレーディングを開始"""
    # CI環境またはAPI_ONLY_MODEの場合はライブトレーディングをスキップ
    if os.getenv("CI") == "true" or os.getenv("API_ONLY_MODE") == "true":
        logger.info("CI or API_ONLY_MODE detected - skipping live trading")
        logger.info("Running in API-only mode...")

        # APIサーバーのみで無限ループ
        try:
            while True:
                time.sleep(60)
                logger.info("API-only mode: heartbeat")
        except KeyboardInterrupt:
            logger.info("API server interrupted")
        return

    try:
        # 環境変数から設定を取得
        mode = os.getenv("MODE", "paper")
        config_file = os.getenv("CONFIG_FILE", "config/default.yml")

        # 必要なファイルの存在確認
        if not os.path.exists(config_file):
            logger.warning(
                f"Config file not found: {config_file}, running API-only mode"
            )
            # APIサーバーのみで継続
            try:
                while True:
                    time.sleep(60)
                    logger.info("API-only mode: heartbeat (missing config)")
            except KeyboardInterrupt:
                logger.info("API server interrupted")
            return

        logger.info(f"Starting live trading in {mode} mode...")
        logger.info(f"Using config: {config_file}")

        # ライブトレーディングの実行
        from crypto_bot.main import main

        # コマンドライン引数を設定
        sys.argv = [
            "crypto_bot",
            "live-paper" if mode == "paper" else "live-real",
            "--config", config_file
        ]

        # メイン関数を実行
        main()

    except KeyboardInterrupt:
        logger.info("Live trading interrupted by user")
    except Exception as e:
        logger.error(f"Live trading failed: {e}")
        # ライブトレーディングが失敗してもAPIサーバーは継続
        logger.info("Continuing with API server only...")

        # APIサーバーのみで無限ループ
        try:
            while True:
                time.sleep(60)
                logger.info("API-only mode: heartbeat")
        except KeyboardInterrupt:
            logger.info("API server interrupted")


def check_requirements():
    """必要な依存関係とファイルをチェック"""
    try:
        # 基本モジュールのインポートテスト
        import crypto_bot  # noqa: F401
        logger.info("✅ crypto_bot module imported successfully")

        # APIサーバーのテスト
        from crypto_bot.api.server import app  # noqa: F401
        logger.info("✅ API server module imported successfully")

        # 設定ファイルの存在確認
        config_file = os.getenv("CONFIG_FILE", "config/default.yml")
        if os.path.exists(config_file):
            logger.info(f"✅ Config file found: {config_file}")
        else:
            logger.warning(f"⚠️ Config file not found: {config_file}")

        return True

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Requirement check failed: {e}")
        return False


def signal_handler(signum, frame):
    """シグナルハンドラー（優雅な終了）"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """メイン実行関数"""
    logger.info("=== Crypto Bot Live Trading + API Server ===")
    logger.info("Starting integrated live trading and API server...")

    # シグナルハンドラーの設定
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # 要件チェック
    if not check_requirements():
        logger.error("Requirements check failed. Exiting.")
        sys.exit(1)

    # 環境変数の表示
    mode = os.getenv("MODE", "paper")
    config_file = os.getenv("CONFIG_FILE", "config/default.yml")
    logger.info(f"Mode: {mode}")
    logger.info(f"Config: {config_file}")

    try:
        # ThreadPoolExecutorを使用してAPIサーバーとライブトレードを並行実行
        with ThreadPoolExecutor(max_workers=2) as executor:
            logger.info("Starting API server in background thread...")
            api_future = executor.submit(start_api_server)

            # APIサーバーの起動を待つ
            time.sleep(3)
            logger.info("API server startup grace period completed")

            logger.info("Starting live trading in main thread...")
            trading_future = executor.submit(start_live_trading)

            # メインループ：どちらかが終了するまで待機
            while True:
                if api_future.done():
                    logger.error("API server stopped unexpectedly")
                    if api_future.exception():
                        logger.error(f"API server error: {api_future.exception()}")
                    break

                if trading_future.done():
                    logger.info("Live trading completed")
                    if trading_future.exception():
                        error_msg = f"Live trading error: {trading_future.exception()}"
                        logger.error(error_msg)
                    break

                time.sleep(5)  # 5秒間隔でチェック

    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Cleanup completed. Goodbye!")


if __name__ == "__main__":
    main()
