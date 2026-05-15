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


class TestPhase89BetaDriftDetection:
    """Phase 89-β: 特徴量ドリフト検出（KS テスト + 連続検知）"""

    @pytest.fixture
    def monitor_drift(self, persistence):
        """drift_consecutive_threshold=2、window=50 に縮小したインスタンス."""
        m = MLHealthMonitor(persistence=persistence, threshold=3, auto_load=False)
        m._drift_consecutive_threshold = 2
        m._drift_window = 50
        m._drift_ks_alpha = 0.01
        return m

    def test_first_record_initializes_reference_without_detection(self, monitor_drift):
        """初回呼び出しは reference として保存され、drift 検出は False."""
        import numpy as np
        import pandas as pd

        df = pd.DataFrame({"f1": np.random.normal(0, 1, 100)})
        detected = monitor_drift.record_feature_distribution(df)
        assert detected is False
        assert "f1" in monitor_drift._reference_distribution
        assert monitor_drift.consecutive_drift_detections == 0

    def test_similar_distribution_does_not_trigger_drift(self, monitor_drift):
        """同じ分布を再供給しても drift 検出されない."""
        import numpy as np
        import pandas as pd

        np.random.seed(42)
        df1 = pd.DataFrame({"f1": np.random.normal(0, 1, 100)})
        monitor_drift.record_feature_distribution(df1)
        for _ in range(3):
            df2 = pd.DataFrame({"f1": np.random.normal(0, 1, 100)})
            monitor_drift.record_feature_distribution(df2)
        assert monitor_drift.consecutive_drift_detections == 0

    def test_distribution_shift_triggers_drift(self, monitor_drift):
        """大きな分布シフトを与えると drift カウントが増加."""
        import numpy as np
        import pandas as pd

        np.random.seed(42)
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        monitor_drift.record_feature_distribution(ref)
        shifted = pd.DataFrame({"f1": np.random.normal(10, 1, 200)})
        detected = monitor_drift.record_feature_distribution(shifted)
        assert detected is True
        assert monitor_drift.consecutive_drift_detections == 1

    def test_consecutive_drift_triggers_emergency_stop(self, monitor_drift):
        """連続 drift_consecutive_threshold 回検知で should_emergency_stop が True."""
        import numpy as np
        import pandas as pd

        np.random.seed(42)
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        monitor_drift.record_feature_distribution(ref)
        for _ in range(2):
            shifted = pd.DataFrame({"f1": np.random.normal(10, 1, 200)})
            monitor_drift.record_feature_distribution(shifted)
        assert monitor_drift.should_emergency_stop() is True

    def test_drift_resolution_resets_count(self, monitor_drift):
        """正常分布に戻れば連続カウントが 0 にリセット."""
        import numpy as np
        import pandas as pd

        np.random.seed(42)
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        monitor_drift.record_feature_distribution(ref)
        shifted = pd.DataFrame({"f1": np.random.normal(10, 1, 200)})
        monitor_drift.record_feature_distribution(shifted)
        assert monitor_drift.consecutive_drift_detections == 1
        for _ in range(5):
            same = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
            monitor_drift.record_feature_distribution(same)
        assert monitor_drift.consecutive_drift_detections == 0

    def test_get_status_includes_drift_fields(self, monitor_drift):
        """get_status に drift 関連フィールドが含まれる."""
        status = monitor_drift.get_status()
        assert "consecutive_drift_detections" in status
        assert "drift_threshold" in status
        assert "last_drift_at" in status
        assert "reference_features_count" in status


class TestPhase89GammaAutoRetraining:
    """Phase 89-γ: Auto Retraining trigger（GitHub repository_dispatch）"""

    @pytest.fixture
    def monitor(self, persistence):
        return MLHealthMonitor(persistence=persistence, threshold=3, auto_load=False)

    def test_trigger_skips_when_github_env_missing(self, monitor, monkeypatch):
        """GITHUB_REPO_OWNER/NAME/TOKEN 未設定で False を返す."""
        monkeypatch.delenv("GITHUB_REPO_OWNER", raising=False)
        monkeypatch.delenv("GITHUB_REPO_NAME", raising=False)
        monkeypatch.delenv("GITHUB_REPO_DISPATCH_TOKEN", raising=False)
        assert monitor.trigger_retraining() is False

    def test_trigger_success_posts_to_github(self, monitor):
        """正常レスポンス時 True + Firestore に last_retrain_trigger_at 保存."""
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_resp.text = ""

        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = monitor.trigger_retraining(
                github_owner="nao-namake",
                github_repo="crypto-bot",
                github_token="fake-token",
            )
        assert result is True
        mock_post.assert_called_once()
        # last_retrain_trigger_at が保存されているか
        assert monitor._get_last_retrain_trigger() is not None

    def test_trigger_api_failure_returns_false(self, monitor):
        """HTTP 401/500 で False."""
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        with patch("requests.post", return_value=mock_resp):
            result = monitor.trigger_retraining(github_owner="o", github_repo="r", github_token="t")
        assert result is False
        assert monitor._get_last_retrain_trigger() is None

    def test_trigger_within_cooldown_skips(self, monitor):
        """cooldown 中の 2 回目呼び出しは False."""
        from unittest.mock import patch, MagicMock

        mock_resp = MagicMock()
        mock_resp.status_code = 204
        with patch("requests.post", return_value=mock_resp):
            # 1 回目: 成功
            assert (
                monitor.trigger_retraining(
                    github_owner="o", github_repo="r", github_token="t", cooldown_hours=24
                )
                is True
            )
            # 2 回目: cooldown 中
            assert (
                monitor.trigger_retraining(
                    github_owner="o", github_repo="r", github_token="t", cooldown_hours=24
                )
                is False
            )

    def test_trigger_request_exception_returns_false(self, monitor):
        """requests.exceptions.ConnectionError でも False."""
        from unittest.mock import patch

        with patch("requests.post", side_effect=ConnectionError("timeout")):
            result = monitor.trigger_retraining(github_owner="o", github_repo="r", github_token="t")
        assert result is False

    def test_trigger_uses_env_vars_when_not_passed(self, monitor, monkeypatch):
        """引数未指定なら環境変数を読む."""
        from unittest.mock import patch, MagicMock

        monkeypatch.setenv("GITHUB_REPO_OWNER", "env-owner")
        monkeypatch.setenv("GITHUB_REPO_NAME", "env-repo")
        monkeypatch.setenv("GITHUB_REPO_DISPATCH_TOKEN", "env-token")

        mock_resp = MagicMock()
        mock_resp.status_code = 204
        with patch("requests.post", return_value=mock_resp) as mock_post:
            assert monitor.trigger_retraining() is True

        # URL に env-owner/env-repo が含まれていること
        url = mock_post.call_args.args[0]
        assert "env-owner" in url and "env-repo" in url
