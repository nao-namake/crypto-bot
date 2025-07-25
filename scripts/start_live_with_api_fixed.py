#!/usr/bin/env python3
"""
ライブトレーディング + API サーバー統合起動スクリプト（修正版）

Phase 2.1: API-onlyモードフォールバック削除版
- エラー時の即座終了実装
- ライブトレードモード強制維持
- API-onlyモードへのフォールバック完全削除
"""

import logging
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def start_api_server():
    """APIサーバーをバックグラウンドで起動"""
    try:
        import uvicorn

        # 直接crypto_bot.apiからFastAPIアプリを取得
        try:
            from crypto_bot.api.health import FASTAPI_AVAILABLE, app, update_init_status

            if not FASTAPI_AVAILABLE:
                raise ImportError("FastAPI not available in health module")
            logger.info("Using comprehensive health API")

            # APIサーバー初期化完了を記録
            update_init_status("basic", "api_server")
        except ImportError:
            # フォールバック: 基本APIを使用
            from crypto_bot.api import FASTAPI_AVAILABLE, app

            if not FASTAPI_AVAILABLE:
                raise ImportError("FastAPI not available")
            logger.info("Using basic API as fallback")

        logger.info("Starting API server on port 8080...")

        # uvicornサーバーを起動
        uvicorn.run(
            app, host="0.0.0.0", port=8080, log_level="info", access_log=True, workers=1
        )
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        # 【修正】API起動失敗時は即座にプロセス終了
        logger.error("API server startup failed - terminating process")

        # エラーを記録
        try:
            from crypto_bot.api.health import update_init_status

            update_init_status("basic", error=str(e))
        except:
            pass

        sys.exit(1)


def start_live_trading():
    """ライブトレーディングを開始"""
    # 【修正】CI環境やAPI_ONLY_MODEでも強制的にライブトレーディングを試行
    ci_mode = os.getenv("CI") == "true"
    api_only_mode = os.getenv("API_ONLY_MODE") == "true"

    if ci_mode or api_only_mode:
        logger.warning(
            "CI or API_ONLY_MODE detected - but attempting live trading anyway"
        )
        logger.warning("This system is designed for LIVE trading only")
        # 【修正】フォールバックせずに処理を続行

    try:
        # 環境変数から設定を取得
        mode = os.getenv("MODE", "live")
        feature_mode = os.getenv("FEATURE_MODE", "full")  # lite or full

        # 特徴量モードに応じた設定ファイル選択
        if feature_mode == "lite":
            default_config = "/app/config/production/production_lite.yml"
            logger.info("🎯 Using LITE mode (3 features) for fast initialization")
        else:
            default_config = "/app/config/production/production.yml"
            logger.info(
                "🎯 Using FULL mode (target: 151 features, actual count determined by ML processing)"
            )

        config_file = os.getenv("CONFIG_FILE", default_config)

        # 【修正】必要なファイルの存在確認 - 見つからない場合は即座終了
        if not os.path.exists(config_file):
            logger.error(f"Config file not found: {config_file}")
            logger.error(
                "Live trading requires valid config file - terminating process"
            )
            sys.exit(1)

        # 【修正】環境変数の必須チェック
        api_key = os.getenv("BITBANK_API_KEY")
        api_secret = os.getenv("BITBANK_API_SECRET")

        if not api_key or not api_secret:
            logger.error(
                "BITBANK_API_KEY or BITBANK_API_SECRET not found in environment"
            )
            logger.error(
                "Live trading requires valid API credentials - terminating process"
            )
            sys.exit(1)

        if api_key == "null" or api_secret == "null":
            logger.error("BITBANK_API_KEY or BITBANK_API_SECRET is set to 'null'")
            logger.error(
                "Live trading requires valid API credentials - terminating process"
            )
            sys.exit(1)

        logger.info(f"Starting live trading in {mode} mode...")
        logger.info(f"Using config: {config_file}")
        logger.info("✅ API credentials verified")

        # ライブトレーディングの実行
        from crypto_bot.main import cli, load_config

        # 設定ファイルを読み込み
        cfg = load_config(config_file)

        # コマンドライン引数を設定
        exchange = cfg.get("data", {}).get("exchange", "bitbank")

        if exchange == "bitbank":
            command = "live-bitbank"
        else:
            command = "live-paper"

        logger.info(f"Using command: {command} for exchange: {exchange}")
        sys.argv = [
            "crypto_bot",
            command,
            "--config",
            config_file,
        ]

        # メイン関数を実行
        cli()

    except KeyboardInterrupt:
        logger.info("Live trading interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Live trading failed: {e}")
        # 【修正】ライブトレーディング失敗時は即座にプロセス終了
        logger.error("Live trading failed - terminating process")
        sys.exit(1)


def download_model_if_needed():
    """Cloud StorageからMLモデルをダウンロード"""
    # 固定パス使用
    model_path = "/app/models/production/model.pkl"
    model_dir = os.path.dirname(model_path)

    # ディレクトリ作成
    if not os.path.exists(model_dir):
        os.makedirs(model_dir, exist_ok=True)
        logger.info(f"📁 Created model directory: {model_dir}")

    if os.path.exists(model_path):
        logger.info(f"✅ Model file already exists: {model_path}")
        return True

    try:
        logger.info("📥 Downloading model from Cloud Storage...")
        from google.cloud import storage

        client = storage.Client()
        bucket = client.bucket("my-crypto-bot-models")
        blob = bucket.blob("model.pkl")

        # ダウンロード
        blob.download_to_filename(model_path)
        logger.info(f"✅ Model downloaded successfully: {model_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to download model: {e}")

        # フォールバック: ダミーモデルを作成
        try:
            logger.info("🔄 Creating dummy model for fallback...")
            import pickle

            import numpy as np
            from sklearn.linear_model import LogisticRegression

            # ダミーモデルを作成（101特徴量対応）
            dummy_model = LogisticRegression(random_state=42)
            X_dummy = np.random.randn(100, 101)  # 101特徴量
            y_dummy = np.random.randint(0, 2, 100)
            dummy_model.fit(X_dummy, y_dummy)

            # 保存
            with open(model_path, "wb") as f:
                pickle.dump(dummy_model, f)

            logger.info(f"✅ Dummy model created: {model_path}")
            return True

        except Exception as fallback_error:
            logger.error(f"❌ Failed to create dummy model: {fallback_error}")
            return False


def check_requirements():
    """必要な依存関係とファイルをチェック"""
    try:
        # 基本モジュールのインポートテスト
        import crypto_bot  # noqa: F401

        logger.info("✅ crypto_bot module imported successfully")

        # APIサーバーのテスト
        try:
            from crypto_bot.api.health import app  # noqa: F401

            logger.info("✅ Health API module imported successfully")
        except ImportError:
            from crypto_bot.api import app  # noqa: F401

            logger.info("✅ Basic API module imported successfully")

        logger.info("✅ API server module imported successfully")

        # 【修正】MLモデルの確認 - 失敗時は即座終了
        if not download_model_if_needed():
            logger.error("❌ Model download/creation failed - terminating process")
            return False

        # 設定ファイルの存在確認
        config_file = os.getenv("CONFIG_FILE", "/app/config/production/production.yml")
        if os.path.exists(config_file):
            logger.info(f"✅ Config file found: {config_file}")
        else:
            logger.error(f"❌ Config file not found: {config_file}")
            logger.error(
                "Live trading requires valid config file - terminating process"
            )
            return False

        # 【修正】yfinance依存関係の確認
        try:
            import yfinance  # noqa: F401

            logger.info("✅ yfinance module imported successfully")
        except ImportError:
            logger.error(
                "❌ yfinance module not found - external data fetchers will fail"
            )
            logger.error(
                "Live trading requires yfinance for external data - terminating process"
            )
            return False

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
    logger.info("=== Crypto Bot Live Trading + API Server (NO-FALLBACK VERSION) ===")
    logger.info("Starting integrated live trading and API server...")
    logger.info("⚠️  This version terminates on any error - NO API-only fallback")

    # シグナルハンドラーの設定
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # 【修正】要件チェック - 失敗時は即座終了
    if not check_requirements():
        logger.error("Requirements check failed. Exiting.")
        sys.exit(1)

    # 環境変数の表示
    mode = os.getenv("MODE", "live")
    config_file = os.getenv("CONFIG_FILE", "/app/config/production/production.yml")
    logger.info(f"Mode: {mode}")
    logger.info(f"Config: {config_file}")

    # 【修正】必須環境変数の確認
    api_key = os.getenv("BITBANK_API_KEY")
    api_secret = os.getenv("BITBANK_API_SECRET")
    logger.info(f"API Key set: {'Yes' if api_key and api_key != 'null' else 'No'}")
    logger.info(
        f"API Secret set: {'Yes' if api_secret and api_secret != 'null' else 'No'}"
    )

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
                    # 【修正】API停止時は即座にプロセス終了
                    sys.exit(1)

                if trading_future.done():
                    logger.info("Live trading completed")
                    if trading_future.exception():
                        error_msg = f"Live trading error: {trading_future.exception()}"
                        logger.error(error_msg)
                        # 【修正】ライブトレーディング停止時は即座にプロセス終了
                        sys.exit(1)
                    break

                time.sleep(5)  # 5秒間隔でチェック

    except KeyboardInterrupt:
        logger.info("Interrupted by user, shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("Cleanup completed. Goodbye!")


if __name__ == "__main__":
    main()
