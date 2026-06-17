"""
Reconciler 統合テスト + 回帰テスト（Phase 90π）

全層（state→desired→diff→invariant→executor）を通し、特に:
- マルチサイクル冪等性（裸ポジ→PLACE_SL→次サイクルNOOP）
- 今回の裸ポジ事例の回帰（0.02 long・SLなし・価格SL割れ → MARKET_CLOSE）
- shadow_mode の安全性（同じ裸ポジでも発注しない）
を検証する。
"""

import pytest

from src.trading.reconciliation.actions import ActionType
from src.trading.reconciliation.desired import DesiredConfig
from src.trading.reconciliation.reconciler import Reconciler

from .fakes import FakeBitbankClient, make_order, make_position

# 既存復旧経路と同じ設定（実configに依存させない）
CONF = DesiredConfig(
    tp_target=1200,
    sl_target=2000,
    sl_floor_ratio=0.007,
    sl_floor_enabled=True,
    min_valid_btc=0.001,
)


def _reconciler(client, shadow=True):
    return Reconciler(
        client,
        shadow_mode=shadow,
        desired_config=CONF,
        coverage_ratio=0.95,
        min_valid_btc=0.001,
        max_total_btc=0.02,
    )


def _action_types(report):
    return [r.action.action_type for r in report.results]


@pytest.mark.asyncio
async def test_naked_position_shadow_proposes_sl_but_no_order():
    # 裸ポジ・価格正常 → SHADOW で PLACE_SL 提案するが発注なし
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[],
        price=10_600_000,
    )
    report = await _reconciler(client, shadow=True).reconcile_once()
    assert client.created_orders == []
    assert ActionType.PLACE_SL in _action_types(report)


@pytest.mark.asyncio
async def test_naked_position_live_places_sl():
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[],
        price=10_600_000,
    )
    await _reconciler(client, shadow=False).reconcile_once()
    stops = [o for o in client.created_orders if o["order_type"] == "stop"]
    assert len(stops) == 1
    assert stops[0]["side"] == "sell"


@pytest.mark.asyncio
async def test_covered_position_is_noop():
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[
            make_order("sl1", "stop", "sell", 0.02),
            make_order("tp1", "limit", "sell", 0.02),
        ],
        price=10_600_000,
    )
    report = await _reconciler(client, shadow=False).reconcile_once()
    assert client.created_orders == []
    assert client.canceled_orders == []
    assert all(r.status in ("noop",) for r in report.results)


@pytest.mark.asyncio
async def test_idempotent_naked_then_covered():
    # 1サイクル目で SL/TP を配置 → 2サイクル目は NOOP（冪等）
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_600_000)],
        active_orders=[],
        price=10_600_000,
    )
    r = _reconciler(client, shadow=False)
    await r.reconcile_once()
    after_first = len(client.created_orders)
    assert after_first >= 1  # SL（とTP）を配置
    await r.reconcile_once()
    assert len(client.created_orders) == after_first  # 増えない＝冪等


@pytest.mark.asyncio
async def test_actual_fetch_failure_aborts():
    client = FakeBitbankClient(raise_on_fetch=True)
    await _reconciler(client, shadow=False).reconcile_once()
    assert client.created_orders == []
    assert client.canceled_orders == []


@pytest.mark.asyncio
async def test_regression_naked_price_below_sl_market_closes():
    # 今回の裸ポジ事例の回帰: long 0.02 @10,612,785・SLなし・価格10,529,413（SL割れ）
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_612_785)],
        active_orders=[],
        price=10_529_413,
    )
    await _reconciler(client, shadow=False).reconcile_once()
    markets = [o for o in client.created_orders if o["order_type"] == "market"]
    assert len(markets) == 1  # 価格割れ裸ポジ → 成行決済
    assert markets[0]["side"] == "sell"
    assert markets[0]["is_closing_order"] is True


@pytest.mark.asyncio
async def test_regression_shadow_does_not_close():
    # 同じ裸ポジでも shadow_mode なら一切発注しない（R0 安全性）
    client = FakeBitbankClient(
        positions=[make_position("long", 0.02, 10_612_785)],
        active_orders=[],
        price=10_529_413,
    )
    await _reconciler(client, shadow=True).reconcile_once()
    assert client.created_orders == []


@pytest.mark.asyncio
async def test_regression_micro_position_cleanup():
    # 今回の 0.0018 微小ポジ（固定SL距離が破綻）→ micro判定 → 成行clean-up（残さない）
    client = FakeBitbankClient(
        positions=[make_position("short", 0.0018, 10_537_098)],
        active_orders=[],
        price=10_400_000,
    )
    await _reconciler(client, shadow=False).reconcile_once()
    markets = [o for o in client.created_orders if o["order_type"] == "market"]
    assert len(markets) == 1  # 微小端数 → 成行決済で残さない
    assert markets[0]["side"] == "buy"  # short の決済 = buy
