"""
Actual State 取得・正規化 — 取引所スナップショットを ActualState に変換

唯一の真実源は bitbank の実建玉（fetch_margin_positions）。それに有効な SL/TP 注文
（fetch_active_orders）と現在価格（fetch_ticker）を重ねて、サイド別の ActualState を作る。

失効 SL の扱い（今回の裸ポジの核心）:
- bitbank の fetch_active_orders は *有効な注文のみ* 返す。CANCELED_UNFILLED/EXPIRED で
  失効した SL は返らないため、自動的に「実効 SL なし」となり裸ポジ検知に繋がる。
- 念のため、万一 status に失効値が乗っていても `_is_effective` で除外する（二重防御）。
- SL の判別は注文 *ステータス* ではなく、最終的に diff/invariants が *実建玉* を基準に
  判断する（CANCELED_UNFILLED が「約定進行中」か「真の失効」かはステータスでは決まらない）。

取得失敗時は ok=False を返し、reconcile 側は ABORT（何もしない・安全側）。
"""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional, Tuple

from ...core.logger import get_logger
from .actions import ActualState, SideState, exit_side_of

# SL とみなす注文タイプ
_SL_TYPES = ("stop", "stop_limit", "stop_loss")
# 実効でない（失効・約定済み）とみなす ccxt status / bitbank info.status
_INVALID_STATUSES = ("canceled", "closed", "expired", "rejected")
_INVALID_INFO_STATUSES = ("CANCELED_UNFILLED", "EXPIRED", "REJECTED")


def _is_effective(order: dict) -> bool:
    """注文が「今まさに有効（建玉を保護できる）」か。失効・約定済みは False。"""
    status = str(order.get("status", "")).lower()
    if status in _INVALID_STATUSES:
        return False
    info_status = str((order.get("info") or {}).get("status", "")).upper()
    if info_status in _INVALID_INFO_STATUSES:
        return False
    return True


def _position_of(positions: List[dict], position_side: str) -> Tuple[float, float]:
    """margin positions から指定サイドの (amount, avg_price) を取り出す。"""
    for p in positions or []:
        if p.get("side") == position_side:
            amt = abs(float(p.get("amount") or 0))
            avg = float(p.get("average_price") or 0)
            return amt, avg
    return 0.0, 0.0


def _build_side(
    position_side: str, amount: float, avg_price: float, active_orders: List[dict]
) -> SideState:
    """建玉サイドの SideState を、有効な SL/TP 注文を集計して構築する。"""
    exit_side = exit_side_of(position_side)  # long→sell / short→buy
    sl_amount = 0.0
    sl_ids: List[str] = []
    sl_status = ""
    tp_amount = 0.0
    tp_ids: List[str] = []

    for o in active_orders or []:
        if o.get("side") != exit_side:
            continue
        otype = str(o.get("type", "")).lower()
        oid = str(o.get("id", ""))
        if otype in _SL_TYPES:
            if _is_effective(o):
                sl_amount += abs(float(o.get("amount") or 0))
                sl_ids.append(oid)
            else:
                # 失効 SL（診断用にステータスを記録・実効には数えない）
                sl_status = str((o.get("info") or {}).get("status", "")) or str(o.get("status", ""))
        elif otype == "limit":
            # 決済方向の limit = TP（エントリーの逆方向 limit は exit_side でないので除外される）
            if _is_effective(o):
                tp_amount += abs(float(o.get("amount") or 0))
                tp_ids.append(oid)

    return SideState(
        position_side=position_side,
        amount=amount,
        avg_price=avg_price,
        sl_amount=sl_amount,
        sl_order_ids=tuple(sl_ids),
        sl_status=sl_status,
        tp_amount=tp_amount,
        tp_order_ids=tuple(tp_ids),
    )


async def build_actual_state(
    bitbank_client: Any, symbol: str = "BTC/JPY", logger: Optional[Any] = None
) -> ActualState:
    """取引所スナップショットから ActualState を構築する。

    fetch_margin_positions は async、fetch_active_orders / fetch_ticker は sync のため
    後者は asyncio.to_thread でラップする。いずれかが失敗したら ok=False（reconcile は ABORT）。
    """
    logger = logger or get_logger()
    try:
        positions = await bitbank_client.fetch_margin_positions(symbol)
        active_orders = await asyncio.to_thread(bitbank_client.fetch_active_orders, symbol, 100)
        ticker = await asyncio.to_thread(bitbank_client.fetch_ticker, symbol)
        current_price = float(ticker.get("last") or 0)
    except Exception as e:
        logger.warning(f"⚠️ Phase 90π reconcile: actual 取得失敗 → ABORT（安全側）: {e}")
        return ActualState(
            long=SideState("long"), short=SideState("short"), current_price=0.0, ok=False
        )

    long_amt, long_avg = _position_of(positions, "long")
    short_amt, short_avg = _position_of(positions, "short")
    return ActualState(
        long=_build_side("long", long_amt, long_avg, active_orders),
        short=_build_side("short", short_amt, short_avg, active_orders),
        current_price=current_price,
        ok=True,
    )
