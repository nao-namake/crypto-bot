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
]


# 戦略タイプ定義
class StrategyType:
    """戦略タイプ定数."""

    MOCHIPOY_ALERT = "mochipoy_alert"  # もちぽよアラート戦略
    ATR_BASED = "atr_based"  # ATRベース戦略
    MULTI_TIMEFRAME = "multi_timeframe"  # マルチタイムフレーム戦略
    FIBONACCI_RETRACEMENT = "fibonacci"  # フィボナッチリトレースメント戦略


# シグナル強度定義
class SignalStrength:
    """シグナル強度定数."""

    WEAK = 0.3  # 弱いシグナル
    MEDIUM = 0.5  # 中程度のシグナル
    STRONG = 0.7  # 強いシグナル
    VERY_STRONG = 0.9  # 非常に強いシグナル


# エントリーアクション定義
class EntryAction:
    """エントリーアクション定数."""

    BUY = "buy"  # 買いエントリー
    SELL = "sell"  # 売りエントリー
    HOLD = "hold"  # ホールド（エントリーなし）
    CLOSE = "close"  # ポジションクローズ
