"""
戦略実装 - Phase 52.4-B完了

6つの取引戦略の具体的実装を提供。
各戦略は独立して動作し、StrategyManagerによって統合される。

実装戦略:
1. ATRBasedStrategy: ボラティリティベース逆張り戦略（range型）
2. DonchianChannelStrategy: ブレイクアウト・反転戦略（range型）
3. ADXTrendStrengthStrategy: トレンド強度・方向性分析戦略（trend型）
4. BBReversalStrategy: ボリンジャーバンド反転戦略（range型）- Phase 52.4-B
5. StochasticReversalStrategy: ストキャスティクス反転戦略（range型）- Phase 52.4-B
6. MACDEMACrossoverStrategy: MACD/EMAクロスオーバー戦略（trend型）- Phase 52.4-B

Phase 52.4-B完了: 6戦略統合・55特徴量システム完成
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
