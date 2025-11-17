"""
統合制御システム - Phase 52.4

システム全体の統合制御・ML統合アダプター・高レベル制御機能を提供。
Application Service Layerとして高レベルフロー制御を担当。

主要コンポーネント:
- TradingOrchestrator: 統合取引システム制御（データ→特徴量→戦略→ML→リスク→取引）
- MLServiceAdapter: ML予測統合インターフェース（ProductionEnsemble統一）
- MLModelLoader: モデル読み込み管理（3段階Graceful Degradation）
- DummyModel: 最終フォールバック（ML失敗時の安全装置）
- Protocols: サービスプロトコル定義（依存性注入基盤）
"""

from .ml_adapter import MLServiceAdapter
from .orchestrator import TradingOrchestrator, create_trading_orchestrator

__all__ = ["MLServiceAdapter", "TradingOrchestrator", "create_trading_orchestrator"]
