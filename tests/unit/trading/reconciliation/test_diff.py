"""
diff_to_actions / is_sl_breached の純粋関数テスト（Phase 90π reconcile core）

純粋関数なのでモック不要。ActualState/DesiredState を直接組んで網羅する。
"""

from src.trading.reconciliation.actions import (
    ActionType,
    ActualState,
    DesiredSide,
    DesiredState,
    SideState,
)
from src.trading.reconciliation.diff import diff_to_actions, is_sl_breached

# テスト用の代表価格（建値10.6M・SL10.5M・TP10.7M）
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


def _types(actions, ps="long"):
    return [a.action_type for a in actions if a.position_side == ps]


class TestIsSlBreached:
    def test_long_breached_when_price_at_or_below_sl(self):
        assert is_sl_breached("long", 10_490_000, SL) is True
        assert is_sl_breached("long", SL, SL) is True

    def test_long_safe_when_price_above_sl(self):
        assert is_sl_breached("long", 10_510_000, SL) is False

    def test_short_breached_when_price_at_or_above_sl(self):
        assert is_sl_breached("short", 10_510_000, SL) is True

    def test_short_safe_when_price_below_sl(self):
        assert is_sl_breached("short", 10_490_000, SL) is False

    def test_invalid_price_returns_false(self):
        assert is_sl_breached("long", 0, SL) is False
        assert is_sl_breached("long", 10_500_000, 0) is False


class TestDiffToActions:
    def test_sl_missing_full_position_places_sl(self):
        # 建玉0.02・SL=0・TPはカバー済み・価格正常 → PLACE_SL のみ
        actual = _actual(
            long=_side("long", amount=0.02, sl_amount=0.0, tp_amount=0.02, tp_ids=("tp1",)),
            price=10_600_000,
        )
        actions = diff_to_actions(actual, _desired(long=_dside("long")))
        assert ActionType.PLACE_SL in _types(actions)
        assert ActionType.MARKET_CLOSE not in _types(actions)

    def test_price_below_sl_triggers_market_close_not_place(self):
        # 価格がSL割れ → stop再配置でなく MARKET_CLOSE
        actual = _actual(
            long=_side("long", amount=0.02, sl_amount=0.0),
            price=10_490_000,  # SL=10.5M を割っている
        )
        actions = diff_to_actions(actual, _desired(long=_dside("long")))
        assert ActionType.MARKET_CLOSE in _types(actions)
        assert ActionType.PLACE_SL not in _types(actions)

    def test_fully_covered_is_noop(self):
        # SL/TP ともカバー済み・価格正常 → NOOP
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
        actions = diff_to_actions(actual, _desired(long=_dside("long")))
        assert _types(actions) == [ActionType.NOOP]

    def test_no_position_with_orphan_sl_cancels(self):
        # 建玉なし・SL/TP残存 → 孤児 → CANCEL_ORDER
        actual = _actual(
            long=_side("long", amount=0.0, sl_amount=0.02, sl_ids=("sl1",), tp_ids=("tp1",)),
        )
        actions = diff_to_actions(actual, _desired())
        long_actions = [a for a in actions if a.position_side == "long"]
        assert all(a.action_type == ActionType.CANCEL_ORDER for a in long_actions)
        assert {a.order_id for a in long_actions} == {"sl1", "tp1"}

    def test_tp_missing_places_tp(self):
        # SLカバー済み・TP欠損 → PLACE_TP
        actual = _actual(
            long=_side("long", amount=0.02, sl_amount=0.02, sl_ids=("sl1",), tp_amount=0.0),
            price=10_600_000,
        )
        actions = diff_to_actions(actual, _desired(long=_dside("long")))
        assert ActionType.PLACE_TP in _types(actions)
        assert ActionType.PLACE_SL not in _types(actions)

    def test_partial_sl_coverage_replaces(self):
        # SL部分カバー(0.01<0.02*0.95) → 既存SL CANCEL + PLACE_SL
        actual = _actual(
            long=_side(
                "long",
                amount=0.02,
                sl_amount=0.01,
                sl_ids=("sl_old",),
                tp_amount=0.02,
                tp_ids=("tp1",),
            ),
            price=10_600_000,
        )
        actions = diff_to_actions(actual, _desired(long=_dside("long")))
        types = _types(actions)
        assert ActionType.CANCEL_ORDER in types
        assert ActionType.PLACE_SL in types
        cancel_ids = {a.order_id for a in actions if a.action_type == ActionType.CANCEL_ORDER}
        assert "sl_old" in cancel_ids

    def test_actual_not_ok_is_noop(self):
        # actual 取得失敗 → 何もしない（安全側）
        actual = _actual(
            long=_side("long", amount=0.02, sl_amount=0.0),
            ok=False,
        )
        actions = diff_to_actions(actual, _desired(long=_dside("long")))
        assert [a.action_type for a in actions] == [ActionType.NOOP]

    def test_short_position_sl_missing_places_sl(self):
        # ショート建玉でも SL欠損 → PLACE_SL
        actual = _actual(
            short=_side("short", amount=0.02, sl_amount=0.0, tp_amount=0.02, tp_ids=("tp1",)),
            price=10_600_000,
        )
        desired = _desired(short=_dside("short", tp=10_500_000, sl=10_700_000))
        actions = diff_to_actions(actual, desired)
        assert ActionType.PLACE_SL in _types(actions, ps="short")
