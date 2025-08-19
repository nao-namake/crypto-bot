#!/usr/bin/env python3
"""
Docker専用APIサーバーエントリポイント
確実にFastAPIアプリケーションを起動するためのモジュール
"""

import logging
import sys

logger = logging.getLogger(__name__)


def get_app():
    """FastAPIアプリケーションを取得"""
    try:
        from crypto_bot.api.health import FASTAPI_AVAILABLE, app

        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI not available")
        logger.info("Loading comprehensive health API")
        return app
    except ImportError:
        # フォールバック: シンプルなAPI
        try:
            from crypto_bot.api.legacy import FASTAPI_AVAILABLE
            from crypto_bot.api.legacy import app as simple_app

            if not FASTAPI_AVAILABLE or simple_app is None:
                raise ImportError("FastAPI not available in simple API")
            logger.info("Loading simple API as fallback")
            return simple_app
        except ImportError:
            logger.error("FastAPI not available - check if api extras are installed")
            sys.exit(1)


# アプリケーション取得
app = get_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
