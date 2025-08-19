"""
Logging configuration and setup
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging():
    """LOG_LEVEL 環境変数でロガーを初期化"""
    level_name = os.getenv("CRYPTO_BOT_LOG_LEVEL", "INFO").upper()
    if hasattr(logging, level_name):
        level = getattr(logging, level_name)
    else:
        level = logging.INFO

    # ルートロガーの設定
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 特定のロガーのレベル調整
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # ファイルハンドラーの追加（オプション）
    log_file = os.getenv("CRYPTO_BOT_LOG_FILE")
    if log_file:
        ensure_dir_for_file(log_file)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logging.getLogger().addHandler(file_handler)


def ensure_dir_for_file(path: str):
    """親ディレクトリが無ければ作成する"""
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
