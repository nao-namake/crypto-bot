"""
check_invariants の純粋関数テスト（Phase 90π 裸ポジ根絶の不変条件）
"""

from src.trading.reconciliation.actions import (
    ActualState,
    DesiredSide,
    DesiredState,
    ReconcileAction,
    SideState,
)
from src.trading.reconciliation.invariants import check_invariants

AVG = 10_600_000.0
SL = 10_500_000.0
TP = 10_700_000.0


def _side(ps, amount=0.0, sl_amount=0.0, sl_ids=(), tp_amount=0.0, tp_ids=()):
    return SideState(
        position_side=ps,
        amount=amount,
        avg_price=AVG,
        sl_amount=sl_amount,
        sl_order_ids=sl_ids,
        tp_amount=tp_amount,
        tp_order_ids=tp_ids,
    )


def _actual(long=None, short=None, price=AVG, ok=True):
    return ActualState(
        long=long or _side("long"),
        short=short or _side("short"),
        current_price=price,
        ok=ok,
    )


def _desired(long=None, short=None):
    return DesiredState(long=long, short=short)


def _dside(ps, amount=0.02, tp=TP, sl=SL):
    return DesiredSide(position_side=ps, amount=amount, tp_price=tp, sl_price=sl)


class TestCheckInvariants:
    def test_naked_position_no_correction_forces_market_close(self):
        # 裸ポジ（SL欠損）で是正actionが無い → MARKET_CLOSE 強制 + 違反記録
        actual = _actual(
            long=_side("long", amount=0.02, sl_amount=0.0, tp_amount=0.02), price=10_600_000
        )
        report = check_invariants(actual, _desired(long=_dside("long")), planned_actions=[])
        assert any("naked_position_uncovered" in v for v in report.violations)
        assert any(a.is_market_close for a in report.extra_actions)

    def test_naked_but_place_sl_planned_no_extra(self):
        # 裸ポジだが PLACE_SL 計画済み → 強制追加なし
        actual = _actual(long=_side("long", amount=0.02, sl_amount=0.0), price=10_600_000)
        planned = [ReconcileAction.place_sl("long", 0.02, SL, "x")]
        report = check_invariants(actual, _desired(long=_dside("long")), planned)
        assert report.extra_actions == ()
        assert not any("naked" in v for v in report.violations)

    def test_naked_but_market_close_planned_no_extra(self):
        # 裸ポジだが MARKET_CLOSE 計画済み → 強制追加なし
        actual = _actual(long=_side("long", amount=0.02, sl_amount=0.0), price=10_600_000)
        planned = [ReconcileAction.market_close("long", 0.02, "x")]
        report = check_invariants(actual, _desired(long=_dside("long")), planned)
        assert report.extra_actions == ()

    def test_fully_covered_no_violation(self):
        actual = _actual(
            long=_side(
                "long",
                amount=0.02,
                sl_amount=0.02,
                sl_ids=("sl1",),
                tp_amount=0.02,
                tp_ids=("tp1",),
            ),
            price=10_600_000,
        )
        report = check_invariants(actual, _desired(long=_dside("long")), planned_actions=[])
        assert report.extra_actions == ()
        assert not report.has_violations

    def test_hedge_detected(self):
        actual = _actual(
            long=_side(
                "long",
                amount=0.01,
                sl_amount=0.01,
                sl_ids=("sl1",),
                tp_amount=0.01,
                tp_ids=("tp1",),
            ),
            short=_side(
                "short",
                amount=0.01,
                sl_amount=0.01,
                sl_ids=("sl2",),
                tp_amount=0.01,
                tp_ids=("tp2",),
            ),
            price=10_600_000,
        )
        desired = _desired(long=_dside("long"), short=_dside("short", tp=10_500_000, sl=10_700_000))
        report = check_invariants(actual, desired, planned_actions=[])
        assert any("hedge_detected" in v for v in report.violations)

    def test_size_exceeded(self):
        actual = _actual(
            long=_side(
                "long",
                amount=0.03,
                sl_amount=0.03,
                sl_ids=("sl1",),
                tp_amount=0.03,
                tp_ids=("tp1",),
            ),
            price=10_600_000,
        )
        report = check_invariants(
            actual,
            _desired(long=_dside("long", amount=0.03)),
            planned_actions=[],
            max_total_btc=0.02,
        )
        assert any("size_exceeded" in v for v in report.violations)

    def test_dust_position_skipped(self):
        # ダスト（min_valid_btc未満）は裸ポジ判定の対象外
        actual = _actual(long=_side("long", amount=0.0005, sl_amount=0.0), price=10_600_000)
        report = check_invariants(
            actual,
            _desired(long=_dside("long", amount=0.0005)),
            planned_actions=[],
            min_valid_btc=0.001,
        )
        assert not any("naked" in v for v in report.violations)
        assert report.extra_actions == ()

    def test_actual_not_ok_no_correction(self):
        # actual 不明時は是正しない（安全側）
        actual = _actual(long=_side("long", amount=0.02, sl_amount=0.0), ok=False)
        report = check_invariants(actual, _desired(long=_dside("long")), planned_actions=[])
        assert report.extra_actions == ()
        assert "actual_not_ok" in report.violations
