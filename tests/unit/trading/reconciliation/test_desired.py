"""
compute_desired_state の純粋関数テスト（Phase 90π desired 計算）

DesiredConfig を直接構築して TPSLCalculator 委譲の結果を検証する。
"""

from src.trading.reconciliation.actions import ActualState, SideState
from src.trading.reconciliation.desired import DesiredConfig, compute_desired_state

AVG = 10_600_000.0

# 既存復旧経路と同じ設定（TP1200/SL2000/floor0.7%）
CONF = DesiredConfig(
    tp_target=1200,
    sl_target=2000,
    sl_floor_ratio=0.007,
    sl_floor_enabled=True,
    min_valid_btc=0.001,
)


def _side(ps, amount=0.0, avg=AVG):
    return SideState(position_side=ps, amount=amount, avg_price=avg)


def _actual(long=None, short=None):
    return ActualState(
        long=long or _side("long"),
        short=short or _side("short"),
        current_price=AVG,
    )


class TestComputeDesiredState:
    def test_long_position_tp_above_sl_below(self):
        d = compute_desired_state(_actual(long=_side("long", amount=0.02)), CONF)
        assert d.long is not None
        assert d.long.tp_price > AVG  # long の TP は建値より上
        assert d.long.sl_price < AVG  # long の SL は建値より下
        assert d.short is None

    def test_short_position_tp_below_sl_above(self):
        d = compute_desired_state(_actual(short=_side("short", amount=0.02)), CONF)
        assert d.short is not None
        assert d.short.tp_price < AVG  # short の TP は建値より下
        assert d.short.sl_price > AVG  # short の SL は建値より上
        assert d.long is None

    def test_no_position_is_none(self):
        d = compute_desired_state(_actual(), CONF)
        assert d.long is None and d.short is None

    def test_dust_position_is_none(self):
        d = compute_desired_state(_actual(long=_side("long", amount=0.0005)), CONF)
        assert d.long is None

    def test_invalid_avg_price_is_none(self):
        d = compute_desired_state(_actual(long=_side("long", amount=0.02, avg=0.0)), CONF)
        assert d.long is None

    def test_sl_distance_at_least_floor(self):
        # floor 0.7% が下限保証: SL距離 >= avg * 0.007
        d = compute_desired_state(_actual(long=_side("long", amount=0.02)), CONF)
        sl_distance = AVG - d.long.sl_price
        assert sl_distance >= AVG * 0.007 * 0.999  # 浮動小数許容

    def test_sl_floor_enforced_with_small_target(self):
        # target を小さくすると計算距離 < floor → floor(0.7%)が効く
        conf_small = DesiredConfig(
            sl_target=1000, sl_floor_ratio=0.007, sl_floor_enabled=True, min_valid_btc=0.001
        )
        d = compute_desired_state(_actual(long=_side("long", amount=0.02)), conf_small)
        sl_distance = AVG - d.long.sl_price
        assert abs(sl_distance - AVG * 0.007) < 1.0  # floor 値 74,200円 に張り付く

    def test_floor_disabled_allows_tighter_sl(self):
        conf_nofloor = DesiredConfig(
            sl_target=1000, sl_floor_ratio=0.007, sl_floor_enabled=False, min_valid_btc=0.001
        )
        d = compute_desired_state(_actual(long=_side("long", amount=0.02)), conf_nofloor)
        sl_distance = AVG - d.long.sl_price
        assert sl_distance < AVG * 0.007  # floor無効なので狭い距離が許される

    def test_micro_position_flagged(self):
        # 0.0018 BTC → 固定SL距離が floor の5倍超 → is_micro=True（clean-up対象）
        d = compute_desired_state(_actual(long=_side("long", amount=0.0018)), CONF)
        assert d.long is not None
        assert d.long.is_micro is True

    def test_normal_position_not_micro(self):
        # 0.015 BTC（標準）→ is_micro=False
        d = compute_desired_state(_actual(long=_side("long", amount=0.015)), CONF)
        assert d.long.is_micro is False
