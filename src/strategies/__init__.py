"""
戦略システム - Phase 64.5

6つの取引戦略を統合した戦略実行システム。
Registry Pattern + Decoratorによる自動登録・動的ロード機構。

戦略構成（レンジ型4 + トレンド型2）:
1. BBReversal: BB位置主導 + RSIボーナス → 平均回帰
2. StochasticDivergence: 価格とStochasticの乖離検出 → 反転
3. ATRBased: ATR消尽率70%以上 → 反転期待
4. DonchianChannel: チャネル端部反転 + RSIボーナス
5. MACDEMACrossover: MACDクロス + EMAトレンド確認
6. ADXTrendStrength: ADX≥25 + DIクロス → トレンドフォロー
"""

from .base.strategy_base import StrategyBase, StrategySignal
from .base.strategy_manager import StrategyManager
from .utils import EntryAction, StrategyType

__all__ = [
    "StrategyBase",
    "StrategySignal",
    "StrategyManager",
    "EntryAction",
    "StrategyType",
]
