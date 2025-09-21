"""
Graceful Shutdown管理モジュール

main.py軽量化方針に従い、shutdown処理を専用モジュールとして分離。
"""

from .graceful_shutdown_manager import GracefulShutdownManager

__all__ = ["GracefulShutdownManager"]
