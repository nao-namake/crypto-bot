#!/usr/bin/env python3
"""
ライブトレードとAPIサーバーを同時実行するスクリプト
Dockerコンテナ内で背景でAPIサーバーを起動し、フォアグラウンドでライブトレードを実行
"""

import logging
import signal
import subprocess
import sys
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class LiveTradingWithAPI:
    def __init__(self):
        self.api_process: Optional[subprocess.Popen] = None
        self.live_trade_process: Optional[subprocess.Popen] = None
        self.shutdown_event = threading.Event()

    def start_api_server(self):
        """バックグラウンドでAPIサーバーを起動"""
        try:
            logger.info("Starting API server in background...")
            self.api_process = subprocess.Popen(
                [
                    "python",
                    "-m",
                    "uvicorn",
                    "crypto_bot.api.server:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "8080",
                    "--log-level",
                    "warning",  # ログレベルを下げてノイズ削減
                ]
            )

            # APIサーバー起動待機
            time.sleep(5)

            if self.api_process.poll() is None:
                logger.info("API server started successfully")
                return True
            else:
                logger.error("API server failed to start")
                return False

        except Exception as e:
            logger.error(f"Failed to start API server: {e}")
            return False

    def download_model_if_needed(self):
        """必要に応じてCloud StorageからMLモデルをダウンロード"""
        import os
        
        model_path = "model/calibrated_model.pkl"
        gcs_path = os.getenv("MODEL_GCS_PATH")
        
        if gcs_path and not os.path.exists(model_path):
            logger.info(f"Downloading ML model from {gcs_path}...")
            try:
                os.makedirs("model", exist_ok=True)
                
                # Parse GCS path: gs://bucket/path
                if gcs_path.startswith("gs://"):
                    parts = gcs_path[5:].split("/", 1)
                    bucket_name = parts[0]
                    blob_name = parts[1]
                    
                    # Use Google Cloud Storage client
                    from google.cloud import storage
                    client = storage.Client()
                    bucket = client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    blob.download_to_filename(model_path)
                    logger.info("ML model downloaded successfully")
                    return True
                else:
                    logger.error(f"Invalid GCS path format: {gcs_path}")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to download model: {e}")
                return False
        elif os.path.exists(model_path):
            logger.info("ML model already exists locally")
            return True
        else:
            logger.warning("No ML model available (neither local nor GCS)")
            return False

    def start_live_trading(self):
        """フォアグラウンドでライブトレードを開始"""
        try:
            # MLモデルをダウンロード
            if not self.download_model_if_needed():
                logger.error("Cannot start live trading without ML model")
                return 1
                
            logger.info("Starting live trading...")
            self.live_trade_process = subprocess.Popen(
                [
                    "python",
                    "-m",
                    "crypto_bot.main",
                    "live-paper",
                    "--config",
                    "config/default.yml",
                ]
            )

            # ライブトレード完了まで待機
            return_code = self.live_trade_process.wait()
            logger.info(f"Live trading finished with return code: {return_code}")
            return return_code

        except Exception as e:
            logger.error(f"Live trading failed: {e}")
            return 1

    def signal_handler(self, signum, frame):
        """シグナルハンドラー（graceful shutdown）"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """プロセス終了処理"""
        logger.info("Cleaning up processes...")

        if self.live_trade_process and self.live_trade_process.poll() is None:
            logger.info("Terminating live trading process...")
            self.live_trade_process.terminate()
            try:
                self.live_trade_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Force killing live trading process...")
                self.live_trade_process.kill()

        if self.api_process and self.api_process.poll() is None:
            logger.info("Terminating API server process...")
            self.api_process.terminate()
            try:
                self.api_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Force killing API server process...")
                self.api_process.kill()

    def run(self):
        """メイン実行"""
        # シグナルハンドラー設定
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

        try:
            # 1. APIサーバー起動
            if not self.start_api_server():
                logger.error("Failed to start API server, exiting...")
                return 1

            # 2. ライブトレード開始
            return_code = self.start_live_trading()

            return return_code

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return 1
        finally:
            self.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    trader = LiveTradingWithAPI()
    exit_code = trader.run()
    sys.exit(exit_code)
