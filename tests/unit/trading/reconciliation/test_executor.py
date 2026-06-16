"""
ReconcileExecutor のテスト（Phase 90π 発注層・shadow_mode・bitbankエラー冪等処理）
"""

import pytest

from src.trading.reconciliation.actions import ActionType, ReconcileAction
from src.trading.reconciliation.executor import ReconcileExecutor

from .fakes import FakeBitbankClient, make_order


@pytest.mark.asyncio
async def test_shadow_mode_places_no_orders():
    # R0 の肝: shadow_mode では一切発注しない
    client = FakeBitbankClient()
    ex = ReconcileExecutor(client, shadow_mode=True)
    actions = [
        ReconcileAction.place_sl("long", 0.02, 10_500_000, "x"),
        ReconcileAction.market_close("long", 0.02, "naked"),
    ]
    report = await ex.apply(actions)
    assert client.created_orders == []
    assert client.canceled_orders == []
    assert all(r.status == "shadow" for r in report.results)
    assert report.shadow_mode is True


@pytest.mark.asyncio
async def test_place_sl_creates_stop_order():
    client = FakeBitbankClient()
    ex = ReconcileExecutor(client, shadow_mode=False)
    await ex.apply([ReconcileAction.place_sl("long", 0.02, 10_500_000, "x")])
    assert len(client.created_orders) == 1
    o = client.created_orders[0]
    assert o["order_type"] == "stop"
    assert o["side"] == "sell"  # long の SL は sell stop
    assert o["trigger_price"] == 10_500_000
    assert o["is_closing_order"] is True
    assert o["entry_position_side"] == "long"


@pytest.mark.asyncio
async def test_place_tp_creates_postonly_limit():
    client = FakeBitbankClient()
    ex = ReconcileExecutor(client, shadow_mode=False)
    await ex.apply([ReconcileAction.place_tp("long", 0.02, 10_700_000, "x")])
    o = client.created_orders[0]
    assert o["order_type"] == "limit"
    assert o["side"] == "sell"
    assert o["price"] == 10_700_000
    assert o["post_only"] is True


@pytest.mark.asyncio
async def test_market_close_cancels_existing_then_closes():
    client = FakeBitbankClient(active_orders=[make_order("tp1", "limit", "sell", 0.02)])
    ex = ReconcileExecutor(client, shadow_mode=False)
    await ex.apply([ReconcileAction.market_close("long", 0.02, "naked")])
    assert "tp1" in client.canceled_orders  # 二重決済防止のため既存注文を消す
    markets = [o for o in client.created_orders if o["order_type"] == "market"]
    assert len(markets) == 1
    assert markets[0]["side"] == "sell"
    assert markets[0]["is_closing_order"] is True


@pytest.mark.asyncio
async def test_cancel_50026_is_idempotent_ok():
    client = FakeBitbankClient(cancel_error=RuntimeError("bitbank error 50026 該当注文なし"))
    ex = ReconcileExecutor(client, shadow_mode=False)
    report = await ex.apply([ReconcileAction.cancel_order("x", "orphan")])
    assert report.results[0].status == "idempotent_ok"


@pytest.mark.asyncio
async def test_place_sl_50062_is_idempotent_ok():
    client = FakeBitbankClient(create_error=RuntimeError("bitbank error 50062 建玉数量超過"))
    ex = ReconcileExecutor(client, shadow_mode=False)
    report = await ex.apply([ReconcileAction.place_sl("long", 0.02, 10_500_000, "x")])
    assert report.results[0].status == "idempotent_ok"


@pytest.mark.asyncio
async def test_70004_is_retry():
    client = FakeBitbankClient(create_error=RuntimeError("bitbank error 70004 取引一時停止"))
    ex = ReconcileExecutor(client, shadow_mode=False)
    report = await ex.apply([ReconcileAction.place_sl("long", 0.02, 10_500_000, "x")])
    assert report.results[0].status == "retry"


@pytest.mark.asyncio
async def test_30101_is_abort():
    client = FakeBitbankClient(create_error=RuntimeError("bitbank error 30101 trigger未指定"))
    ex = ReconcileExecutor(client, shadow_mode=False)
    report = await ex.apply([ReconcileAction.place_sl("long", 0.02, 10_500_000, "x")])
    assert report.results[0].status == "abort"


@pytest.mark.asyncio
async def test_action_order_cancel_before_place():
    client = FakeBitbankClient()
    ex = ReconcileExecutor(client, shadow_mode=False)
    actions = [
        ReconcileAction.place_sl("long", 0.02, 10_500_000, "x"),
        ReconcileAction.cancel_order("old_sl", "replace"),
    ]
    report = await ex.apply(actions)
    # CANCEL が PLACE より先に実行される
    assert report.results[0].action.action_type == ActionType.CANCEL_ORDER


@pytest.mark.asyncio
async def test_noop_does_nothing():
    client = FakeBitbankClient()
    ex = ReconcileExecutor(client, shadow_mode=False)
    report = await ex.apply([ReconcileAction.noop("covered", "long")])
    assert client.created_orders == []
    assert report.results[0].status == "noop"
