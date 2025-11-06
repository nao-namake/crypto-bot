"""
戦略実装 - Phase 51.7 Day 7完了

6つの取引戦略の具体的実装を提供。
各戦略は独立して動作し、StrategyManagerによって統合される。

実装戦略:
1. ATRBasedStrategy: ボラティリティベース逆張り戦略（range型）
2. DonchianChannelStrategy: ブレイクアウト・反転戦略（range型）
3. ADXTrendStrengthStrategy: トレンド強度・方向性分析戦略（trend型）
4. BBReversalStrategy: ボリンジャーバンド反転戦略（range型）- Phase 51.7 Day 3
5. StochasticReversalStrategy: ストキャスティクス反転戦略（range型）- Phase 51.7 Day 4
6. MACDEMACrossoverStrategy: MACD/EMAクロスオーバー戦略（trend型）- Phase 51.7 Day 5

Phase 51.7 Day 7完了: 6戦略統合・54特徴量システム完成
Phase 49完了: 市場不確実性計算統合・重複コード削減・保守性向上
"""

from .adx_trend import ADXTrendStrengthStrategy
from .atr_based import ATRBasedStrategy
from .bb_reversal import BBReversalStrategy
from .donchian_channel import DonchianChannelStrategy
from .macd_ema_crossover import MACDEMACrossoverStrategy
from .stochastic_reversal import StochasticReversalStrategy

__all__ = [
    "ATRBasedStrategy",
    "DonchianChannelStrategy",
    "ADXTrendStrengthStrategy",
    "BBReversalStrategy",
    "StochasticReversalStrategy",
    "MACDEMACrossoverStrategy",
]
