"""
戦略システム - Phase 4実装

4つの取引戦略を統合した戦略実行システム。
レガシーシステムの複雑さを排除し、シンプルで効率的な戦略実装を提供。

戦略構成:
1. もちぽよアラート: EMA, MACD, RCI組み合わせ戦略
2. ATRベース戦略: ボラティリティベースの逆張り戦略
3. マルチタイムフレーム戦略: 4時間足→15分足のフィルタリング
4. フィボナッチリトレースメント: 重要レベルでの反転狙い

Phase 4実装日: 2025年8月18日.
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


# Phase 18統合：重複定数をutilsから再エクスポート
from .utils import EntryAction, StrategyType


# シグナル強度定義（戦略システム固有のため保持）
class SignalStrength:
    """シグナル強度定数."""

    WEAK = 0.3  # 弱いシグナル
    MEDIUM = 0.5  # 中程度のシグナル
    STRONG = 0.7  # 強いシグナル
    VERY_STRONG = 0.9  # 非常に強いシグナル
