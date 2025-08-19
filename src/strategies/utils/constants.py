"""
戦略共通定数定義

4つの戦略で重複していた定数をここに統合。
各戦略固有のパラメータは戦略クラスに残す。.
"""

from typing import Any, Dict


class EntryAction:
    """エントリーアクション定数."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class StrategyType:
    """戦略タイプ定数."""

    MOCHIPOY_ALERT = "mochipoy_alert"
    ATR_BASED = "atr_based"
    FIBONACCI_RETRACEMENT = "fibonacci"
    MULTI_TIMEFRAME = "multi_timeframe"


# 基本リスク管理パラメータ（戦略で上書き可能）
DEFAULT_RISK_PARAMS: Dict[str, Any] = {
    # ストップロス・テイクプロフィット
    "stop_loss_atr_multiplier": 2.0,  # 一般的な設定
    "take_profit_ratio": 2.5,  # リワード・リスク比
    # ポジションサイズ
    "position_size_base": 0.02,  # 2%の基本設定
    # 計算設定
    "min_atr_threshold": 0.001,  # ATRの最小値（ゼロ除算回避）
    "max_position_size": 0.05,  # 最大ポジションサイズ（5%）
}
