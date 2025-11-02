"""
戦略実装 - Phase 51.5-A完了

3つの取引戦略の具体的実装を提供。
各戦略は独立して動作し、StrategyManagerによって統合される。

実装戦略:
1. ATRBasedStrategy: ボラティリティベース逆張り戦略（range型）
2. DonchianChannelStrategy: ブレイクアウト・反転戦略（range型）
3. ADXTrendStrengthStrategy: トレンド強度・方向性分析戦略（trend型）

Phase 51.5-A完了: MochipoyAlert/MultiTimeframe削除・3戦略構成最適化
Phase 49完了: 市場不確実性計算統合・重複コード削減・保守性向上
"""

from .adx_trend import ADXTrendStrengthStrategy
from .atr_based import ATRBasedStrategy
from .donchian_channel import DonchianChannelStrategy

__all__ = [
    "ATRBasedStrategy",
    "DonchianChannelStrategy",
    "ADXTrendStrengthStrategy",
]
