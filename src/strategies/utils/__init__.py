"""
戦略共通ユーティリティモジュール - Phase 18統合版

Phase 18統合により、3つのファイル（constants.py, risk_manager.py, signal_builder.py）を
strategy_utils.pyに統合し、保守性を向上。

統合効果:
- ファイル数削減：3→1ファイル（66%削減）
- 関連機能の一元化：定数、リスク管理、シグナル生成を統合
- 後方互換性維持：既存のインポートパスをサポート

Phase 18統合実装日: 2025年8月30日
"""

from .strategy_utils import (
    DEFAULT_RISK_PARAMS,
    EntryAction,
    RiskManager,
    SignalBuilder,
    StrategyType,
)

__all__ = [
    "EntryAction",
    "StrategyType",
    "DEFAULT_RISK_PARAMS",
    "RiskManager",
    "SignalBuilder",
]
