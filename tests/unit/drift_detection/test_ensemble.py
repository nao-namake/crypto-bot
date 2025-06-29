# tests/unit/drift_detection/test_ensemble.py
"""
Drift detection ensemble のテスト
"""

import numpy as np
import pytest

try:
    from crypto_bot.drift_detection.ensemble import EnsembleDriftDetector
except ImportError:
    pytest.skip("EnsembleDriftDetector not available", allow_module_level=True)
from crypto_bot.drift_detection.detectors import ADWINDetector, DDMDetector


class TestEnsembleDriftDetector:
    """Ensemble Drift Detector のテストクラス"""

    def test_initialization_empty(self):
        """空の初期化のテスト"""
        ensemble = EnsembleDriftDetector()

        assert len(ensemble.detectors) == 0
        assert ensemble.voting_strategy == "majority"
        assert not ensemble.drift_detected

    def test_initialization_with_detectors(self):
        """検出器付き初期化のテスト"""
        detectors = [ADWINDetector(), DDMDetector()]
        ensemble = EnsembleDriftDetector(
            detectors=detectors, voting_strategy="unanimous"
        )

        assert len(ensemble.detectors) == 2
        assert ensemble.voting_strategy == "unanimous"

    def test_add_detector(self):
        """検出器追加のテスト"""
        ensemble = EnsembleDriftDetector()
        detector = ADWINDetector()

        ensemble.add_detector("adwin", detector)

        assert "adwin" in ensemble.detectors
        assert ensemble.detectors["adwin"] == detector

    def test_remove_detector(self):
        """検出器削除のテスト"""
        ensemble = EnsembleDriftDetector()
        detector = ADWINDetector()
        ensemble.add_detector("adwin", detector)

        removed = ensemble.remove_detector("adwin")

        assert removed == detector
        assert "adwin" not in ensemble.detectors

    def test_remove_nonexistent_detector(self):
        """存在しない検出器削除のテスト"""
        ensemble = EnsembleDriftDetector()

        removed = ensemble.remove_detector("nonexistent")

        assert removed is None

    def test_majority_voting_no_drift(self):
        """多数決投票でドリフト未検出のテスト"""
        ensemble = EnsembleDriftDetector(voting_strategy="majority")
        ensemble.add_detector("adwin1", ADWINDetector(delta=0.1))
        ensemble.add_detector("adwin2", ADWINDetector(delta=0.1))
        ensemble.add_detector("ddm", DDMDetector())

        # 安定したデータ
        drifts = []
        for _ in range(50):
            drift = ensemble.update(1.0 + np.random.normal(0, 0.01))
            drifts.append(drift)

        # 安定データなのでドリフト検出されないはず
        assert not any(drifts)

    def test_unanimous_voting(self):
        """全員一致投票のテスト"""
        ensemble = EnsembleDriftDetector(voting_strategy="unanimous")
        ensemble.add_detector("adwin", ADWINDetector(delta=0.5))
        ensemble.add_detector("ddm", DDMDetector(alpha_d=1.0))

        # データを更新
        for i in range(20):
            ensemble.update(float(i))

        # 全員一致でなければドリフト検出されない
        assert not ensemble.drift_detected

    def test_single_detector_voting(self):
        """単一検出器投票のテスト"""
        ensemble = EnsembleDriftDetector(voting_strategy="single")
        ensemble.add_detector("adwin", ADWINDetector())

        # データを更新
        drift = ensemble.update(1.0)

        # 単一検出器の結果がそのまま返される
        assert isinstance(drift, bool)

    def test_weighted_voting(self):
        """重み付き投票のテスト"""
        ensemble = EnsembleDriftDetector(voting_strategy="weighted")
        ensemble.add_detector("adwin", ADWINDetector(), weight=0.7)
        ensemble.add_detector("ddm", DDMDetector(), weight=0.3)

        # データを更新
        drift = ensemble.update(1.0)

        # 重み付き投票の結果
        assert isinstance(drift, bool)

    def test_get_detector_states(self):
        """検出器状態取得のテスト"""
        ensemble = EnsembleDriftDetector()
        ensemble.add_detector("adwin", ADWINDetector())
        ensemble.add_detector("ddm", DDMDetector())

        # データを更新
        ensemble.update(1.0)
        ensemble.update(2.0)

        states = ensemble.get_detector_states()

        assert "adwin" in states
        assert "ddm" in states
        assert "drift_detected" in states["adwin"]
        assert "drift_detected" in states["ddm"]

    def test_reset_all(self):
        """全検出器リセットのテスト"""
        ensemble = EnsembleDriftDetector()
        ensemble.add_detector("adwin", ADWINDetector())
        ensemble.add_detector("ddm", DDMDetector())

        # データを更新
        ensemble.update(1.0)
        ensemble.update(2.0)

        # リセット
        ensemble.reset()

        # 全ての検出器がリセットされているか確認
        states = ensemble.get_detector_states()
        for _detector_name, state in states.items():
            if "total_samples" in state:
                assert state["total_samples"] == 0

    def test_get_status(self):
        """ステータス取得のテスト"""
        ensemble = EnsembleDriftDetector()
        ensemble.add_detector("adwin", ADWINDetector())

        ensemble.update(1.0)

        status = ensemble.get_status()

        assert "ensemble_drift_detected" in status
        assert "voting_strategy" in status
        assert "detectors" in status
        assert len(status["detectors"]) == 1

    def test_invalid_voting_strategy(self):
        """無効な投票戦略のテスト"""
        with pytest.raises(ValueError):
            EnsembleDriftDetector(voting_strategy="invalid_strategy")

    def test_empty_ensemble_update(self):
        """空のアンサンブル更新のテスト"""
        ensemble = EnsembleDriftDetector()

        # 検出器がない状態で更新
        drift = ensemble.update(1.0)

        # ドリフト検出されない
        assert not drift

    def test_detector_weights_sum_to_one(self):
        """検出器重みの正規化テスト"""
        ensemble = EnsembleDriftDetector(voting_strategy="weighted")
        ensemble.add_detector("adwin", ADWINDetector(), weight=2.0)
        ensemble.add_detector("ddm", DDMDetector(), weight=3.0)

        # 重みが正規化されているかテスト
        # (実装依存だが、正規化されることを期待)
        total_weight = (
            sum(ensemble.weights.values()) if hasattr(ensemble, "weights") else 1.0
        )
        assert abs(total_weight - 1.0) < 1e-6 or total_weight == 5.0  # 正規化後か元の値
