"""
状態永続化システム - Phase 38.4完了版

ドローダウン状態の永続化・管理システム。
ローカルファイルとCloud Storage両対応の統一インターフェース。
モード別（paper/live/backtest）状態分離によるデータ安全性確保。

Phase 28-29最適化: 状態永続化システム確立・モード別分離実装
Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了
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
