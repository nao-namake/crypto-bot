"""
戦略共通ユーティリティモジュール

保守性・安定性・成績向上のため、戦略間で共通する処理を統合。
戦略固有のロジックは各戦略クラスに残し、計算処理のみ共通化。

Phase 4.1実装日: 2025年8月18日.
"""

from .constants import DEFAULT_RISK_PARAMS, EntryAction, StrategyType
from .risk_manager import RiskManager
from .signal_builder import SignalBuilder

__all__ = [
    "EntryAction",
    "StrategyType",
    "DEFAULT_RISK_PARAMS",
    "RiskManager",
    "SignalBuilder",
]
