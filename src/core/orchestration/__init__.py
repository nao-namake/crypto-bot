"""
統合制御システム - Phase 38.4完了版

システム全体の統合制御・ML統合アダプター・高レベル制御機能を提供。
orchestrator.pyから分離した統合制御機能の集約。

Phase 28-29最適化: 統合制御システム分離・Application Service Pattern確立
Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了
"""

from .ml_adapter import MLServiceAdapter
from .orchestrator import TradingOrchestrator, create_trading_orchestrator

__all__ = ["MLServiceAdapter", "TradingOrchestrator", "create_trading_orchestrator"]
