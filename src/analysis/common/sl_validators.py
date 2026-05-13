"""Phase 87 Stage 3: SL未設置検出（live/backtest 共通ロジック）

Phase 86 で live/standard_analysis.py に金額ベースの missing_sl_detected が実装されていたが、
backtest 側は未実装で、コード重複と非対称性があった。本モジュールで統一する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MissingSLResult:
    """SL未設置検出の結果

    Attributes:
        detected: True なら SL未設置あり
        position_amount: ポジション合計数量 (BTC)
        sl_order_amount: SL注文合計数量 (BTC)
        coverage_ratio: SL カバレッジ比率 (sl_order_amount / position_amount)、ポジション0時は1.0
        threshold_pct: しきい値（デフォルト 0.95）
        sides: サイド別詳細（"long" / "short" の数量、SL有無）
        reason: 検出理由・ログ用文字列
    """

    detected: bool
    position_amount: float = 0.0
    sl_order_amount: float = 0.0
    coverage_ratio: float = 1.0
    threshold_pct: float = 0.95
    sides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    reason: str = ""


def detect_missing_sl(
    positions: List[Dict[str, Any]],
    orders: List[Dict[str, Any]],
    threshold_pct: float = 0.95,
    symbol: str = "BTC/JPY",
) -> MissingSLResult:
    """ポジション合計と SL注文合計を比較し、SL未設置を検出する。

    Args:
        positions: bitbank fetch_margin_positions の結果（各 dict は side / amount を持つ）
        orders: bitbank fetch_active_orders の結果（各 dict は type / side / amount を持つ）
        threshold_pct: SL カバレッジしきい値（デフォルト 0.95、5% 端数誤差許容）
        symbol: 通貨ペア（将来の複数ペア対応のため）

    Returns:
        MissingSLResult: 検出結果
    """
    long_total = 0.0
    short_total = 0.0
    for p in positions or []:
        try:
            amount = float(p.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0.0
        side = (p.get("side") or "").lower()
        if side == "long":
            long_total += amount
        elif side == "short":
            short_total += amount

    # SL注文は type=stop / stop_limit
    # long ポジション (買い) の SL は sell 側、short ポジション (売り) の SL は buy 側
    sl_sell_total = 0.0
    sl_buy_total = 0.0
    for o in orders or []:
        try:
            order_amount = float(o.get("amount") or 0)
        except (TypeError, ValueError):
            order_amount = 0.0
        order_type = (o.get("type") or "").lower()
        order_side = (o.get("side") or "").lower()
        if order_type not in ("stop", "stop_limit"):
            continue
        if order_side == "sell":
            sl_sell_total += order_amount
        elif order_side == "buy":
            sl_buy_total += order_amount

    long_covered = long_total <= 0 or sl_sell_total >= long_total * threshold_pct
    short_covered = short_total <= 0 or sl_buy_total >= short_total * threshold_pct
    detected = (not long_covered) or (not short_covered)

    total_pos = long_total + short_total
    total_sl = sl_sell_total + sl_buy_total
    coverage = total_sl / total_pos if total_pos > 0 else 1.0

    sides = {
        "long": {
            "position": long_total,
            "sl_order": sl_sell_total,
            "covered": long_covered,
        },
        "short": {
            "position": short_total,
            "sl_order": sl_buy_total,
            "covered": short_covered,
        },
    }

    reason = ""
    if detected:
        missing_sides = [
            name for name, info in sides.items() if not info["covered"] and info["position"] > 0
        ]
        reason = (
            f"SL未設置検出 (sides={missing_sides}, "
            f"long {long_total:.4f}/{sl_sell_total:.4f} BTC, "
            f"short {short_total:.4f}/{sl_buy_total:.4f} BTC, "
            f"threshold={threshold_pct * 100:.0f}%)"
        )

    return MissingSLResult(
        detected=detected,
        position_amount=total_pos,
        sl_order_amount=total_sl,
        coverage_ratio=coverage,
        threshold_pct=threshold_pct,
        sides=sides,
        reason=reason,
    )
