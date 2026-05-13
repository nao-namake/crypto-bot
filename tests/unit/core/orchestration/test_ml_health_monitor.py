"""Phase 87 C4: MLHealthMonitor テスト（サーキットブレーカー）"""

import pytest

from src.core.orchestration.ml_health_monitor import MLHealthMonitor
from src.core.persistence.firestore_state import FirestoreStateClient


@pytest.fixture
def persistence(tmp_path):
    return FirestoreStateClient(
        instance_id="mlhealth-test",
        local_fallback_dir=str(tmp_path),
        force_local=True,
    )


@pytest.fixture
def monitor(persistence):
    return MLHealthMonitor(persistence=persistence, threshold=3, auto_load=False)


class TestMLHealthMonitor:
    def test_initial_state(self, monitor):
        assert monitor.consecutive_failures == 0
        assert monitor.should_emergency_stop() is False

    def test_record_failure_increments(self, monitor):
        monitor.record_failure("predict_error: X")
        assert monitor.consecutive_failures == 1
        assert monitor.last_reason == "predict_error: X"
        assert monitor.should_emergency_stop() is False

    def test_emergency_stop_at_threshold(self, monitor):
        monitor.record_failure("a")
        monitor.record_failure("b")
        assert monitor.should_emergency_stop() is False
        monitor.record_failure("c")
        assert monitor.should_emergency_stop() is True

    def test_emergency_stop_beyond_threshold(self, monitor):
        for i in range(5):
            monitor.record_failure(f"err{i}")
        assert monitor.consecutive_failures == 5
        assert monitor.should_emergency_stop() is True

    def test_reset_on_success_clears(self, monitor):
        monitor.record_failure("x")
        monitor.record_failure("y")
        assert monitor.consecutive_failures == 2
        monitor.reset_on_success()
        assert monitor.consecutive_failures == 0
        assert monitor.last_reason is None
        assert monitor.should_emergency_stop() is False

    def test_reset_on_success_noop_when_zero(self, monitor):
        """カウント0で reset_on_success してもクラッシュしない"""
        monitor.reset_on_success()
        assert monitor.consecutive_failures == 0

    def test_get_status(self, monitor):
        monitor.record_failure("oops")
        status = monitor.get_status()
        assert status["consecutive_failures"] == 1
        assert status["threshold"] == 3
        assert status["last_reason"] == "oops"
        assert status["should_emergency_stop"] is False

    def test_state_persists_across_instances(self, persistence):
        """state が Firestore（ローカル fallback）に保存され、別インスタンスで復元される"""
        m1 = MLHealthMonitor(persistence=persistence, threshold=5, auto_load=False)
        m1.record_failure("first")
        m1.record_failure("second")

        # 新インスタンスを auto_load=True で
        m2 = MLHealthMonitor(persistence=persistence, threshold=5)
        assert m2.consecutive_failures == 2
        assert m2.last_reason == "second"

    def test_custom_threshold(self, persistence):
        m = MLHealthMonitor(persistence=persistence, threshold=1, auto_load=False)
        m.record_failure("once")
        assert m.should_emergency_stop() is True

    def test_no_persistence_works_inmemory(self):
        """persistence=None でもクラッシュしない（インメモリ動作）"""
        m = MLHealthMonitor(persistence=None, threshold=2, auto_load=False)
        m.record_failure("x")
        assert m.consecutive_failures == 1
        m.record_failure("y")
        assert m.should_emergency_stop() is True


class TestPhase87Stage2R4ThresholdConfig:
    """Phase 87 Stage 2-R4: threshold が config 経由で読まれる"""

    def test_threshold_from_config_when_none(self, persistence, monkeypatch):
        """threshold=None なら get_threshold("ml.health.consecutive_failure_threshold", 3) が使われる"""

        def fake_get_threshold(key, default=None):
            if key == "ml.health.consecutive_failure_threshold":
                return 7
            return default

        monkeypatch.setattr("src.core.config.get_threshold", fake_get_threshold, raising=False)
        m = MLHealthMonitor(persistence=persistence, threshold=None, auto_load=False)
        assert m.threshold == 7

    def test_explicit_threshold_overrides_config(self, persistence):
        """明示的 threshold 引数が config より優先される"""
        m = MLHealthMonitor(persistence=persistence, threshold=10, auto_load=False)
        assert m.threshold == 10

    def test_fallback_to_default_on_config_error(self, persistence, monkeypatch):
        """get_threshold が例外を投げても DEFAULT_THRESHOLD にフォールバック"""

        def broken_get_threshold(*args, **kwargs):
            raise RuntimeError("config load error")

        monkeypatch.setattr("src.core.config.get_threshold", broken_get_threshold, raising=False)
        m = MLHealthMonitor(persistence=persistence, threshold=None, auto_load=False)
        assert m.threshold == MLHealthMonitor.DEFAULT_THRESHOLD
