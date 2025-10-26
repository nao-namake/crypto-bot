"""
戦略実装 - Phase 49完了

5つの取引戦略の具体的実装を提供。
各戦略は独立して動作し、StrategyManagerによって統合される。

実装戦略:
1. MochipoyAlertStrategy: EMA, MACD, RCI組み合わせ戦略
2. ATRBasedStrategy: ボラティリティベース逆張り戦略
3. MultiTimeframeStrategy: 4時間足→15分足フィルタリング戦略
4. DonchianChannelStrategy: ブレイクアウト・反転戦略
5. ADXTrendStrengthStrategy: トレンド強度・方向性分析戦略

Phase 49完了: 市場不確実性計算統合・重複コード削減・保守性向上
"""

from .adx_trend import ADXTrendStrengthStrategy
from .atr_based import ATRBasedStrategy
from .donchian_channel import DonchianChannelStrategy
from .mochipoy_alert import MochipoyAlertStrategy
from .multi_timeframe import MultiTimeframeStrategy

__all__ = [
    "MochipoyAlertStrategy",
    "ATRBasedStrategy",
    "MultiTimeframeStrategy",
    "DonchianChannelStrategy",
    "ADXTrendStrengthStrategy",
]
