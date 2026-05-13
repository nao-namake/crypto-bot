"""Phase 87 Stage 3: TP/SL距離算出ヘルパー（Phase 86 単一実装の再利用）"""

from __future__ import annotations

from typing import Tuple

from ...trading.execution.tpsl_calculator import TPSLCalculator


def calculate_tp_sl_distances(
    action: str,
    entry_price: float,
    amount: float,
    target_profit: float = 1500.0,
    target_max_loss: float = 2000.0,
    entry_fee_rate: float = 0.001,
    exit_fee_rate_tp: float = 0.0,
    exit_fee_rate_sl: float = 0.001,
    min_distance_ratio: float = 0.007,
    enable_floor: bool = True,
) -> Tuple[float, float, float, float]:
    """TP/SL 価格と距離を計算する（Phase 86 TPSLCalculator 経由）。

    Args:
        action: "buy" or "sell"
        entry_price: エントリー価格
        amount: 数量 (BTC)
        target_profit: 目標利益 (円)
        target_max_loss: 目標損失上限 (円)
        entry_fee_rate: エントリー手数料率
        exit_fee_rate_tp: TP決済手数料率 (Maker=0想定)
        exit_fee_rate_sl: SL決済手数料率 (Taker=0.001想定)
        min_distance_ratio: SL最低距離比率 (Phase 85 floor 0.007)
        enable_floor: SL floor 有効化

    Returns:
        (tp_price, sl_price, tp_distance_pct, sl_distance_pct)
    """
    tp_price = TPSLCalculator.calculate_tp(
        action=action,
        entry_price=entry_price,
        amount=amount,
        target_net_profit=target_profit,
        entry_fee_rate=entry_fee_rate,
        exit_fee_rate=exit_fee_rate_tp,
    )
    sl_price = TPSLCalculator.calculate_sl(
        action=action,
        entry_price=entry_price,
        amount=amount,
        target_max_loss=target_max_loss,
        entry_fee_rate=entry_fee_rate,
        exit_fee_rate=exit_fee_rate_sl,
        min_distance_ratio=min_distance_ratio,
        enable_floor=enable_floor,
    )
    tp_distance_pct = abs(tp_price - entry_price) / entry_price * 100
    sl_distance_pct = abs(entry_price - sl_price) / entry_price * 100
    return tp_price, sl_price, tp_distance_pct, sl_distance_pct
