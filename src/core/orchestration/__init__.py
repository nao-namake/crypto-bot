"""
統合制御システム - Phase 49完了

システム全体の統合制御・ML統合アダプター・高レベル制御機能を提供。
orchestrator.pyから分離した統合制御機能の集約。

Phase 49完了:
- TradingOrchestrator: Application Service Layer高レベル統合制御
- MLServiceAdapter: ProductionEnsemble統一インターフェース・ML予測統合
- ml_loader: モデル読み込み専門（ProductionEnsemble・個別モデル再構築）
- ml_fallback: DummyModel安全装置（hold信頼度0.5フォールバック）
Phase 35: バックテスト最適化（ログレベル動的変更・Discord無効化）
Phase 28-29: Application Service Pattern確立・責任分離・依存性注入基盤
"""

from .ml_adapter import MLServiceAdapter
from .orchestrator import TradingOrchestrator, create_trading_orchestrator

__all__ = ["MLServiceAdapter", "TradingOrchestrator", "create_trading_orchestrator"]
