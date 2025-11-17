"""
戦略システム - Phase 52.4-B完了

6つの取引戦略を統合した戦略実行システム。
動的戦略管理基盤（Registry Pattern）によるシンプルで効率的な戦略実装を提供。

戦略構成:
1. ATRベース戦略: ボラティリティベースの逆張り戦略
2. Donchianチャネル: ブレイクアウト・反転戦略
3. ADXトレンド強度: トレンド方向性分析戦略
4. BBReversal: ボリンジャーバンド反転戦略
5. StochasticReversal: ストキャスティクス反転戦略
6. MACDEMACrossover: MACD・EMAクロスオーバー戦略

Phase 52.4-B完了: 6戦略システム・動的戦略管理基盤・市場不確実性計算統合・コード重複削減
"""

from .base.strategy_base import StrategyBase, StrategySignal
from .base.strategy_manager import StrategyManager

__all__ = [
    "StrategyBase",
    "StrategySignal",
    "StrategyManager",
    "EntryAction",
    "StrategyType",
    "SignalStrength",
]


# Phase 52.4-B完了：重複定数をutilsから再エクスポート
from .utils import EntryAction, StrategyType


# シグナル強度定義（戦略システム固有のため保持）
class SignalStrength:
    """シグナル強度定数."""

    WEAK = 0.3  # 弱いシグナル
    MEDIUM = 0.5  # 中程度のシグナル
    STRONG = 0.7  # 強いシグナル
    VERY_STRONG = 0.9  # 非常に強いシグナル
