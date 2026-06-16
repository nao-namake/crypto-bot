"""
build_actual_state のテスト（Phase 90π Actual State 取得）

FakeBitbankClient で取引所スナップショットを与え、ActualState への正規化を検証する。
特に「失効SL（CANCELED_UNFILLED）が実効SLに数えられない」を確認（裸ポジ検知の要）。
"""

import pytest

from src.trading.reconciliation.state import build_actual_state

from .fakes import FakeBitbankClient, make_order, make_position


@pytest.mark.asyncio
async def test_position_with_sl_and_tp():
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[
            make_order("sl1", "stop", "sell", 0.02),
            make_order("tp1", "limit", "sell", 0.02, price=10_700_000),
        ],
        price=10_600_000,
    )
    actual = await build_actual_state(client)
    assert actual.ok
    assert actual.long.amount == 0.02
    assert actual.long.sl_amount == 0.02
    assert "sl1" in actual.long.sl_order_ids
    assert actual.long.tp_amount == 0.02
    assert "tp1" in actual.long.tp_order_ids
    assert actual.current_price == 10_600_000


@pytest.mark.asyncio
async def test_naked_position_no_sl():
    # SLなし・TPのみ → sl_amount=0（裸ポジ検知へ）
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[make_order("tp1", "limit", "sell", 0.02)],
    )
    actual = await build_actual_state(client)
    assert actual.long.amount == 0.02
    assert actual.long.sl_amount == 0.0


@pytest.mark.asyncio
async def test_canceled_unfilled_sl_excluded():
    # CANCELED_UNFILLED の SL は実効SLに数えない（今回の裸ポジの核心）
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[
            make_order(
                "sl1", "stop", "sell", 0.02, status="canceled", info_status="CANCELED_UNFILLED"
            )
        ],
    )
    actual = await build_actual_state(client)
    assert actual.long.sl_amount == 0.0
    assert actual.long.sl_order_ids == ()


@pytest.mark.asyncio
async def test_short_position_uses_buy_side_orders():
    # short 建玉の SL/TP は buy 方向
    client = FakeBitbankClient(
        positions=[make_position("short", 0.02, 10_600_000)],
        active_orders=[
            make_order("sl1", "stop", "buy", 0.02),
            make_order("tp1", "limit", "buy", 0.02),
        ],
    )
    actual = await build_actual_state(client)
    assert actual.short.amount == 0.02
    assert actual.short.sl_amount == 0.02
    assert actual.short.tp_amount == 0.02
    # long 側には何も無い
    assert actual.long.amount == 0.0


@pytest.mark.asyncio
async def test_no_position():
    client = FakeBitbankClient(positions=[], active_orders=[])
    actual = await build_actual_state(client)
    assert actual.ok
    assert actual.long.amount == 0.0
    assert actual.short.amount == 0.0


@pytest.mark.asyncio
async def test_fetch_failure_returns_not_ok():
    client = FakeBitbankClient(raise_on_fetch=True)
    actual = await build_actual_state(client)
    assert actual.ok is False


@pytest.mark.asyncio
async def test_entry_limit_not_counted_as_tp():
    # long エントリーの buy limit は exit_side(sell) でないので TP に数えない
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[
            make_order("entry1", "limit", "buy", 0.02),  # エントリー側 limit
            make_order("sl1", "stop", "sell", 0.02),
        ],
    )
    actual = await build_actual_state(client)
    assert actual.long.tp_amount == 0.0  # buy limit は long TP に数えない
    assert actual.long.sl_amount == 0.02
