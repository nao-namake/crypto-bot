"""
戦略実装 - Phase 64.5

6つの取引戦略の具体的実装を提供。
各戦略は独立して動作し、StrategyManagerによって統合される。

レンジ型（4戦略）:
1. ATRBasedStrategy: ATR消尽率ベース逆張り
2. BBReversalStrategy: ボリンジャーバンド位置主導の平均回帰
3. StochasticReversalStrategy: ストキャスティクス乖離検出
4. DonchianChannelStrategy: チャネル端部反転

トレンド型（2戦略）:
5. MACDEMACrossoverStrategy: MACD/EMAクロスオーバー
6. ADXTrendStrengthStrategy: ADX≥25 + DIクロスによるトレンドフォロー
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
