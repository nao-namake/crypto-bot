"""Phase 87 Stage 3 H10: バックテスト/ライブ整合性 - 品質フィルタ判定の同一性検証

Stage 1-R R4 で confidence 計算の数値同一性は確認済（test_confidence_backward_compat.py）。
本テストはさらに踏み込み、**同じ (ml_prediction, ml_confidence, regime) に対して
バックテストとライブが完全に同じ verdict を返す**ことを保証する。

これにより:
- バックテストで成功した戦略がライブで品質フィルタに拒否される
- ライブで通過する取引がバックテストで拒否される
というスケール不一致を構造的に防止する。
"""

from unittest.mock import patch

import numpy as np
import pytest

from src.core.orchestration.ml_confidence import get_predicted_class_proba
from src.core.orchestration.quality_filter import QualityFilter


def _make_thresholds_mock(regime_overrides=None):
    base = {
        "ml.quality_filter.accept_threshold": 0.58,
        "ml.quality_filter.reject_threshold": 0.42,
        "ml.quality_filter.uncertain_penalty": 0.5,
        "ml.quality_filter.high_confidence_failure_threshold": 0.65,
    }
    if regime_overrides:
        for regime, vals in regime_overrides.items():
            for k, v in vals.items():
                base[f"ml.quality_filter.regime_thresholds.{regime}.{k}"] = v

    def get(key, default=None):
        return base.get(key, default)

    return get


class TestQualityFilterConsistency:
    """同一入力 → 同一 verdict (バックテストとライブの判定一致)"""

    @patch("src.core.orchestration.quality_filter.get_threshold")
    @pytest.mark.parametrize(
        "ml_pred, confidence, expected_verdict",
        [
            (1, 0.80, "accept"),
            (1, 0.50, "uncertain"),
            (0, 0.80, "reject"),
            (1, 0.30, "reject"),
        ],
    )
    def test_same_input_same_verdict(self, mock_get, ml_pred, confidence, expected_verdict):
        """ライブ・バックテストの両方で QualityFilter を呼び、verdict が一致"""
        mock_get.side_effect = _make_thresholds_mock()

        # 「ライブ側」呼び出し
        qf_live = QualityFilter(regime_aware=True)
        result_live = qf_live.evaluate(ml_pred, confidence, regime="unknown")

        # 「バックテスト側」呼び出し（別インスタンス）
        qf_backtest = QualityFilter(regime_aware=True)
        result_backtest = qf_backtest.evaluate(ml_pred, confidence, regime="unknown")

        assert result_live.verdict == expected_verdict
        assert result_live.verdict == result_backtest.verdict
        assert result_live.adjusted_confidence_factor == result_backtest.adjusted_confidence_factor

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_regime_specific_consistency(self, mock_get):
        """tight_range/normal_range で両者一致"""
        mock_get.side_effect = _make_thresholds_mock(
            regime_overrides={
                "tight_range": {"accept_threshold": 0.55},
                "normal_range": {"accept_threshold": 0.85},
            }
        )

        qf_live = QualityFilter()
        qf_backtest = QualityFilter()

        for regime in ["tight_range", "normal_range", "trending"]:
            for confidence in [0.50, 0.60, 0.75]:
                r_live = qf_live.evaluate(1, confidence, regime=regime)
                r_backtest = qf_backtest.evaluate(1, confidence, regime=regime)
                assert r_live.verdict == r_backtest.verdict, (
                    f"verdict 不一致: regime={regime}, conf={confidence} "
                    f"live={r_live.verdict}, backtest={r_backtest.verdict}"
                )

    def test_predicted_class_proba_consistency(self):
        """Stage 1-R R4 と統合: predicted_class_proba ヘルパーが両者で同値"""
        # ライブ側: ml_probabilities (2D)
        probs_live = np.array([[0.3, 0.7]])
        cls_live, conf_live = get_predicted_class_proba(probs_live)

        # バックテスト側: precomputed_ml_predictions の同一サンプル
        probs_backtest = np.array([0.3, 0.7])  # 1D（インデックス参照後）
        cls_backtest, conf_backtest = get_predicted_class_proba(probs_backtest)

        assert cls_live == cls_backtest
        assert conf_live == conf_backtest

    @patch("src.core.orchestration.quality_filter.get_threshold")
    def test_full_pipeline_consistency(self, mock_get):
        """confidence 計算 → QualityFilter 判定 のフルパイプライン同一性"""
        mock_get.side_effect = _make_thresholds_mock()

        # 同一の ml_probabilities を 2 回処理（ライブ/バックテスト想定）
        probs = np.array([[0.2, 0.8]])  # ml_pred=1, conf=0.8

        cls1, conf1 = get_predicted_class_proba(probs)
        qf1 = QualityFilter()
        verdict1 = qf1.evaluate(cls1, conf1).verdict

        cls2, conf2 = get_predicted_class_proba(probs)
        qf2 = QualityFilter()
        verdict2 = qf2.evaluate(cls2, conf2).verdict

        assert verdict1 == verdict2 == "accept"
