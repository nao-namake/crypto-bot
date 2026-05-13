"""Phase 87 Stage 3 H10/H6: QualityFilter モジュール単体テスト"""

from unittest.mock import patch

import pytest

from src.core.orchestration.quality_filter import (
    QualityFilter,
    QualityFilterResult,
    apply_to_signal,
)
from src.strategies.base.strategy_base import StrategySignal


def _signal(action="buy", confidence=0.7):
    return StrategySignal(
        strategy_name="TestStrategy",
        timestamp=None,
        action=action,
        confidence=confidence,
        strength=0.5,
        current_price=14000000.0,
        entry_price=14000000.0,
    )


# ============================================================
# evaluate() 純粋判定
# ============================================================


def _make_thresholds_mock(
    accept=0.58, reject=0.42, uncertain=0.5, high_fail=0.65, regime_overrides=None
):
    """global + 任意 regime override の get_threshold mock を返す"""
    base = {
        "ml.quality_filter.accept_threshold": accept,
        "ml.quality_filter.reject_threshold": reject,
        "ml.quality_filter.uncertain_penalty": uncertain,
        "ml.quality_filter.high_confidence_failure_threshold": high_fail,
    }
    if regime_overrides:
        for regime, vals in regime_overrides.items():
            for k, v in vals.items():
                base[f"ml.quality_filter.regime_thresholds.{regime}.{k}"] = v

    def get(key, default=None):
        return base.get(key, default)

    return get


class TestEvaluate:
    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_accept_path(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(accept=0.58)
        qf = QualityFilter()
        r = qf.evaluate(ml_prediction=1, ml_confidence=0.70)
        assert r.verdict == "accept"
        assert r.adjusted_confidence_factor == 1.0
        assert r.thresholds_used["accept_threshold"] == 0.58

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_reject_by_high_confidence_failure(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(high_fail=0.65)
        qf = QualityFilter()
        # ml_pred=0 + conf=0.70 >= high_fail=0.65 → reject
        r = qf.evaluate(0, 0.70)
        assert r.verdict == "reject"
        assert r.adjusted_confidence_factor == 0.1

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_reject_by_low_confidence(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(reject=0.42)
        qf = QualityFilter()
        # conf < reject_threshold (0.42) → reject
        r = qf.evaluate(1, 0.35)
        assert r.verdict == "reject"

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_uncertain_middle(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(
            accept=0.58, reject=0.42, high_fail=0.65, uncertain=0.5
        )
        qf = QualityFilter()
        # ml_pred=1, conf=0.50: accept(>=0.58)未達、reject(>=high_fail=0.65かつml=0)該当せず、reject(<0.42)未満達せず → uncertain
        r = qf.evaluate(1, 0.50)
        assert r.verdict == "uncertain"
        assert r.adjusted_confidence_factor == 0.5

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_regime_specific_threshold_used(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(
            accept=0.58,
            regime_overrides={"tight_range": {"accept_threshold": 0.55}},
        )
        qf = QualityFilter()
        # tight_range の accept_threshold=0.55 が適用される
        r = qf.evaluate(1, 0.56, regime="tight_range")
        assert r.verdict == "accept"
        assert r.thresholds_used["accept_threshold"] == 0.55

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_regime_unknown_uses_global(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(accept=0.58)
        qf = QualityFilter()
        r = qf.evaluate(1, 0.59, regime="unknown")
        assert r.verdict == "accept"
        assert r.thresholds_used["accept_threshold"] == 0.58

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_regime_unmapped_falls_back_to_global(self, mock_get):
        # high_volatility は regime_overrides に含まれない → global へ fallback
        mock_get.side_effect = _make_thresholds_mock(
            accept=0.58,
            regime_overrides={"tight_range": {"accept_threshold": 0.55}},
        )
        qf = QualityFilter()
        r = qf.evaluate(1, 0.58, regime="high_volatility")
        assert r.thresholds_used["accept_threshold"] == 0.58

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_regime_aware_disabled(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(
            accept=0.58,
            regime_overrides={"tight_range": {"accept_threshold": 0.55}},
        )
        qf = QualityFilter(regime_aware=False)
        r = qf.evaluate(1, 0.58, regime="tight_range")
        # regime_aware=False なら tight_range が無視される
        assert r.thresholds_used["accept_threshold"] == 0.58


# ============================================================
# apply_to_signal()
# ============================================================


class TestApplyToSignal:
    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_hold_signal_passes_through(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock()
        qf = QualityFilter()
        result = qf.evaluate(1, 0.70)
        hold_signal = _signal(action="hold")
        out = apply_to_signal(result, hold_signal)
        assert out.action == "hold"
        assert out is hold_signal  # 同一オブジェクト

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_accept_returns_original_signal(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(accept=0.58)
        qf = QualityFilter()
        result = qf.evaluate(1, 0.70)
        signal = _signal(action="buy", confidence=0.8)
        out = apply_to_signal(result, signal)
        assert out is signal  # accept はそのまま

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_reject_converts_to_hold(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(high_fail=0.65)
        qf = QualityFilter()
        result = qf.evaluate(0, 0.70)  # reject
        signal = _signal(action="buy", confidence=0.8)
        out = apply_to_signal(result, signal)
        assert out.action == "hold"
        assert out.confidence == pytest.approx(0.8 * 0.1)
        assert out.metadata.get("quality_filtered") is True

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_uncertain_keeps_action_but_scales_confidence(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock(accept=0.58, reject=0.42, uncertain=0.5)
        qf = QualityFilter()
        result = qf.evaluate(1, 0.50)  # uncertain
        signal = _signal(action="buy", confidence=0.8)
        out = apply_to_signal(result, signal)
        assert out.action == "buy"
        assert out.confidence == pytest.approx(0.8 * 0.5)
        assert out.metadata.get("quality_uncertain") is True


# ============================================================
# 戻り値型
# ============================================================


class TestResultType:
    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_qfresult_dataclass_fields(self, mock_get):
        mock_get.side_effect = _make_thresholds_mock()
        qf = QualityFilter()
        r = qf.evaluate(1, 0.7, regime="tight_range")
        assert isinstance(r, QualityFilterResult)
        assert isinstance(r.verdict, str)
        assert isinstance(r.adjusted_confidence_factor, float)
        assert isinstance(r.thresholds_used, dict)
        assert isinstance(r.reason, str)
        assert r.regime == "tight_range"
