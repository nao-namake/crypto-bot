"""
状態永続化システム - Phase 28完了・Phase 29最適化版

ドローダウン状態の永続化・管理システム。
ローカルファイルとCloud Storage両対応の統一インターフェース。
モード別（paper/live/backtest）状態分離によるデータ安全性確保。
"""

from .drawdown_persistence import (
    CloudStoragePersistence,
    DrawdownPersistence,
    LocalFilePersistence,
    create_persistence,
)

__all__ = [
    "DrawdownPersistence",
    "LocalFilePersistence",
    "CloudStoragePersistence",
    "create_persistence",
]
