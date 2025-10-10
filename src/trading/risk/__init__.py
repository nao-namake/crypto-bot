"""
trading/risk層 - 統合リスク管理システム

Phase 38リファクタリング
"""

from .anomaly import AnomalyAlert, AnomalyLevel, TradingAnomalyDetector
from .drawdown import DrawdownManager, TradeRecord, TradingStatus
from .kelly import KellyCalculationResult, KellyCriterion, TradeResult
from .sizer import PositionSizeIntegrator

# TODO: manager.pyを作成後、以下のインポートを有効化
# from .manager import IntegratedRiskManager, RiskDecision, RiskMetrics

__all__ = [
    # Kelly基準
    "KellyCriterion",
    "TradeResult",
    "KellyCalculationResult",
    # ポジションサイジング
    "PositionSizeIntegrator",
    # 異常検出
    "TradingAnomalyDetector",
    "AnomalyAlert",
    "AnomalyLevel",
    # ドローダウン管理
    "DrawdownManager",
    "TradeRecord",
    "TradingStatus",
    # TODO: manager.py作成後、以下を有効化
    # "IntegratedRiskManager",
    # "RiskDecision",
    # "RiskMetrics",
]