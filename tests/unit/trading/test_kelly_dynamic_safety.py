"""
Phase 89-β: Fractional Kelly 動的安全係数テスト

KellyCriterion._get_dynamic_safety_factor の連敗段階別 multiplier 適用と、
calculate_from_history への consecutive_losses 引数の伝播を検証する。
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.trading.risk.kelly import KellyCriterion


@pytest.fixture
def kelly():
    """base safety_factor=0.7, min_trades=3 の KellyCriterion インスタンス."""
    return KellyCriterion(max_position_ratio=0.03, safety_factor=0.7, min_trades_for_kelly=3)


def _add_winning_history(kelly: KellyCriterion, n_wins: int = 5, n_losses: int = 3) -> None:
    """勝率高め（67%）の取引履歴を構築（Kelly>0 になる条件）."""
    now = datetime.now()
    for i in range(n_wins):
        kelly.add_trade_result(
            profit_loss=1500.0,
            strategy="test",
            confidence=0.8,
            timestamp=now - timedelta(hours=i + 1),
        )
    for i in range(n_losses):
        kelly.add_trade_result(
            profit_loss=-1000.0,
            strategy="test",
            confidence=0.6,
            timestamp=now - timedelta(hours=10 + i),
        )


def test_zero_losses_uses_base_safety_factor(kelly):
    """0 連敗時は base safety_factor (0.7) × multiplier 1.0 = 0.7."""
    factor = kelly._get_dynamic_safety_factor(consecutive_losses=0)
    assert factor == pytest.approx(0.7 * 1.0, abs=0.001)


def test_three_losses_applies_first_tier_multiplier(kelly):
    """3 連敗で multiplier=0.7 適用 → 0.7 × 0.7 = 0.49."""
    factor = kelly._get_dynamic_safety_factor(consecutive_losses=3)
    assert factor == pytest.approx(0.7 * 0.7, abs=0.001)


def test_five_losses_applies_strong_shrink(kelly):
    """5 連敗で multiplier=0.4 適用 → 0.7 × 0.4 = 0.28."""
    factor = kelly._get_dynamic_safety_factor(consecutive_losses=5)
    assert factor == pytest.approx(0.7 * 0.4, abs=0.001)


def test_seven_losses_applies_extreme_shrink(kelly):
    """7 連敗で multiplier=0.2 適用 → 0.7 × 0.2 = 0.14."""
    factor = kelly._get_dynamic_safety_factor(consecutive_losses=7)
    assert factor == pytest.approx(0.7 * 0.2, abs=0.001)


def test_eight_or_more_losses_returns_zero(kelly):
    """8 連敗以上で取引停止（safety_factor=0）."""
    assert kelly._get_dynamic_safety_factor(consecutive_losses=8) == 0.0
    assert kelly._get_dynamic_safety_factor(consecutive_losses=15) == 0.0


def test_dynamic_factor_reflected_in_calculate_from_history(kelly):
    """calculate_from_history に consecutive_losses を渡すと safety_adjusted_fraction に反映される."""
    _add_winning_history(kelly)

    result_no_loss = kelly.calculate_from_history(consecutive_losses=0)
    result_five_loss = kelly.calculate_from_history(consecutive_losses=5)

    assert result_no_loss is not None
    assert result_five_loss is not None
    # 同じ Kelly fraction だが、5 連敗時の safety_adjusted は 0連敗時より小さい
    assert result_no_loss.kelly_fraction == pytest.approx(
        result_five_loss.kelly_fraction, abs=1e-6
    )
    assert result_five_loss.safety_adjusted_fraction < result_no_loss.safety_adjusted_fraction
    # 0連敗: × 0.7 / 5連敗: × 0.28 → 比率は 0.4
    ratio = result_five_loss.safety_adjusted_fraction / result_no_loss.safety_adjusted_fraction
    assert ratio == pytest.approx(0.4, abs=0.01)


def test_calculate_optimal_size_passes_consecutive_losses(kelly):
    """calculate_optimal_size 経由でも consecutive_losses が calculate_from_history に伝播する."""
    _add_winning_history(kelly)

    with patch.object(
        kelly, "calculate_from_history", wraps=kelly.calculate_from_history
    ) as spy:
        kelly.calculate_optimal_size(
            ml_confidence=0.7,
            strategy_name="test",
            consecutive_losses=5,
        )
        # consecutive_losses が伝播していることを確認
        call_args = spy.call_args
        assert call_args.kwargs.get("consecutive_losses") == 5


def test_dynamic_multiplier_table_overridable_via_config():
    """thresholds.yaml の dynamic_safety_multiplier を上書きすれば挙動が変わる."""
    kelly = KellyCriterion(safety_factor=1.0)
    custom_table = {"loss_0": 0.5, "loss_3": 0.4, "loss_5": 0.3, "loss_7": 0.2, "loss_8": 0.0}
    with patch(
        "src.trading.risk.kelly.get_threshold",
        side_effect=lambda key, default=None: custom_table
        if key == "risk.kelly_criterion.dynamic_safety_multiplier"
        else default,
    ):
        # base safety_factor=1.0 × custom multiplier
        assert kelly._get_dynamic_safety_factor(0) == pytest.approx(0.5)
        assert kelly._get_dynamic_safety_factor(3) == pytest.approx(0.4)
        assert kelly._get_dynamic_safety_factor(5) == pytest.approx(0.3)
        assert kelly._get_dynamic_safety_factor(7) == pytest.approx(0.2)
        assert kelly._get_dynamic_safety_factor(8) == 0.0
