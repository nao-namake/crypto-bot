# crypto_bot/api/__init__.py
# API関連モジュールのパッケージ初期化

try:
    from .health import app, health_checker

    __all__ = ["app", "health_checker"]
except ImportError:
    # FastAPI not available, provide dummy objects
    app = None
    health_checker = None
    __all__ = ["app", "health_checker"]
