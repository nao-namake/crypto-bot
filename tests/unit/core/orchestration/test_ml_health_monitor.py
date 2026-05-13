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
