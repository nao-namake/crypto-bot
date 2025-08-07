"""
Model utilities for saving and loading ML models
"""

import logging
import pickle
from typing import Any

logger = logging.getLogger(__name__)

# joblib条件付きimport
JOBLIB_AVAILABLE = False
try:
    import joblib

    JOBLIB_AVAILABLE = True
except ImportError:
    pass


def save_model(model: Any, path: str):
    """joblib にフォールバックしてモデルを保存"""
    from crypto_bot.utils.file import ensure_dir_for_file

    ensure_dir_for_file(path)

    if JOBLIB_AVAILABLE:
        joblib.dump(model, path)
        logger.info(f"Model saved to {path} using joblib")
    else:
        # joblib がなければ pickle
        with open(path, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"Model saved to {path} using pickle")


def load_model(path: str) -> Any:
    """モデルを読み込む（joblib/pickleフォールバック付き）"""
    try:
        if JOBLIB_AVAILABLE:
            model = joblib.load(path)
            logger.info(f"Model loaded from {path} using joblib")
        else:
            with open(path, "rb") as f:
                model = pickle.load(f)
            logger.info(f"Model loaded from {path} using pickle")
        return model
    except Exception as e:
        logger.error(f"Failed to load model from {path}: {e}")
        raise
