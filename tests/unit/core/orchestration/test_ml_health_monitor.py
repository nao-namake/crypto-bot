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
        """drift_consecutive_threshold=2、window=50 に縮小したインスタンス.

        Phase 89 H4: 本番では significant_feature_min=3 だが、テストは単一特徴量で実施するため 1 に上書き.
        Phase 89 H10: auto_retraining も無効化（テストで requests.post を mock しない場合の干渉防止）.
        """
        m = MLHealthMonitor(persistence=persistence, threshold=3, auto_load=False)
        m._drift_consecutive_threshold = 2
        m._drift_window = 50
        m._drift_ks_alpha = 0.01
        m._drift_significant_feature_min = 1  # H4: テストは 1 特徴量で drift 判定
        m._drift_auto_retraining = False  # H10: テスト中の自動 trigger を抑制
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
        from unittest.mock import MagicMock, patch

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
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        with patch("requests.post", return_value=mock_resp):
            result = monitor.trigger_retraining(github_owner="o", github_repo="r", github_token="t")
        assert result is False
        assert monitor._get_last_retrain_trigger() is None

    def test_trigger_within_cooldown_skips(self, monitor):
        """cooldown 中の 2 回目呼び出しは False."""
        from unittest.mock import MagicMock, patch

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
        from unittest.mock import MagicMock, patch

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


class TestPhase90GammaDriftFix:
    """Phase 90γ-①: Drift 検出の構造的バグ修正

    背景: 旧実装は (a) reference 分布が初回固定で永久に更新されず、
    (b) 価格絶対値 (OHLCV/MA/BB) を比較対象に含むため、市場の自然変動を
    drift と誤検知し続ける構造的欠陥があった。本テストは修正後の挙動を保証する。
    """

    @pytest.fixture
    def monitor_drift(self, persistence):
        m = MLHealthMonitor(persistence=persistence, threshold=3, auto_load=False)
        m._drift_consecutive_threshold = 2
        m._drift_window = 50
        m._drift_ks_alpha = 0.01
        m._drift_significant_feature_min = 1
        m._drift_auto_retraining = False
        return m

    def test_exclude_features_filtered_out(self, monitor_drift):
        """exclude_features に指定された特徴量は _extract_feature_values の出力から除外."""
        import pandas as pd

        monitor_drift._drift_exclude_features = {"open", "close"}
        df = pd.DataFrame(
            {"open": [1.0, 2.0, 3.0], "close": [4.0, 5.0, 6.0], "rsi_14": [50.0, 55.0, 60.0]}
        )
        values = monitor_drift._extract_feature_values(df)
        assert "open" not in values
        assert "close" not in values
        assert "rsi_14" in values

    def test_price_shift_with_exclusion_does_not_trigger_drift(self, monitor_drift):
        """OHLCV を除外している状態で価格大幅シフトしても drift 検出されない."""
        import numpy as np
        import pandas as pd

        monitor_drift._drift_exclude_features = {"close"}
        monitor_drift._drift_significant_feature_min = 1
        np.random.seed(42)
        # close は除外・rsi は変動なし → drift 対象が無いので検出されない
        ref = pd.DataFrame(
            {
                "close": np.random.normal(12_000_000, 10_000, 200),
                "rsi_14": np.random.normal(50, 5, 200),
            }
        )
        monitor_drift.record_feature_distribution(ref)
        shifted = pd.DataFrame(
            {
                "close": np.random.normal(13_000_000, 10_000, 200),  # +8% 価格シフト
                "rsi_14": np.random.normal(50, 5, 200),  # 変動なし
            }
        )
        # rsi 同一分布なので drift 判定されないはず（close は除外で比較対象外）
        for _ in range(3):
            detected = monitor_drift.record_feature_distribution(shifted)
            assert detected is False

    def test_reference_reset_after_expiry(self, monitor_drift):
        """reference_reset_hours 経過後に reference が reset され、新分布で再初期化される."""
        from datetime import timedelta

        import numpy as np
        import pandas as pd

        monitor_drift._drift_reference_reset_hours = 168.0
        np.random.seed(42)
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        monitor_drift.record_feature_distribution(ref)
        first_ref_at = monitor_drift._reference_initialized_at
        assert first_ref_at is not None

        # 期限切れシミュレーション（200h 前にずらす = 168h より古い）
        monitor_drift._reference_initialized_at = first_ref_at - timedelta(hours=200)

        # 大きく異なる分布を供給 → reset され新 reference として保存（drift 検出されない）
        shifted = pd.DataFrame({"f1": np.random.normal(10, 1, 200)})
        detected = monitor_drift.record_feature_distribution(shifted)
        assert detected is False
        # reference 初期化時刻が更新されている
        assert monitor_drift._reference_initialized_at is not None
        assert monitor_drift._reference_initialized_at > first_ref_at - timedelta(hours=200)

    def test_reference_not_reset_within_expiry(self, monitor_drift):
        """期限内であれば reference は reset されず、初期化時刻も変わらない（既存挙動保持）."""
        import numpy as np
        import pandas as pd

        monitor_drift._drift_reference_reset_hours = 168.0
        np.random.seed(42)
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        monitor_drift.record_feature_distribution(ref)
        first_ref_at = monitor_drift._reference_initialized_at

        # 数回呼び出し（期限内）
        for _ in range(3):
            same = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
            monitor_drift.record_feature_distribution(same)

        # reference 初期化時刻は変わらない
        assert monitor_drift._reference_initialized_at == first_ref_at

    def test_significant_feature_min_strict_blocks_minor_drift(self, monitor_drift):
        """significant_feature_min=10 で 9 個の特徴量が drift しても判定されない."""
        import numpy as np
        import pandas as pd

        monitor_drift._drift_significant_feature_min = 10
        np.random.seed(42)
        ref_data = {f"f{i}": np.random.normal(0, 1, 200) for i in range(15)}
        ref = pd.DataFrame(ref_data)
        monitor_drift.record_feature_distribution(ref)

        # 9 特徴量のみシフト・残り 6 は同分布
        shift_data = {
            f"f{i}": (np.random.normal(10, 1, 200) if i < 9 else np.random.normal(0, 1, 200))
            for i in range(15)
        }
        shifted = pd.DataFrame(shift_data)
        detected = monitor_drift.record_feature_distribution(shifted)
        assert detected is False  # 9 < 10 で drift 未判定

    def test_reset_disabled_with_zero_hours(self, monitor_drift):
        """reference_reset_hours=0 で reset 無効化（旧挙動相当）."""
        from datetime import timedelta

        import numpy as np
        import pandas as pd

        monitor_drift._drift_reference_reset_hours = 0  # reset 無効
        np.random.seed(42)
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        monitor_drift.record_feature_distribution(ref)
        first_ref_at = monitor_drift._reference_initialized_at

        # 大幅に時刻をずらしても reset されない
        monitor_drift._reference_initialized_at = first_ref_at - timedelta(days=365)
        shifted = pd.DataFrame({"f1": np.random.normal(10, 1, 200)})
        detected = monitor_drift.record_feature_distribution(shifted)
        # reset されないので分布シフトが drift として正しく検出される
        assert detected is True

    def test_status_includes_phase90_fields(self, monitor_drift):
        """get_status に Phase 90γ-① の新規フィールドが含まれる."""
        status = monitor_drift.get_status()
        assert "reference_initialized_at" in status
        assert "drift_exclude_features_count" in status
        assert "drift_reference_reset_hours" in status

    def test_reference_initialized_at_persists(self, persistence):
        """reference_initialized_at が Firestore に永続化され、別インスタンスで復元される."""
        import numpy as np
        import pandas as pd

        m1 = MLHealthMonitor(persistence=persistence, threshold=3, auto_load=False)
        m1._drift_window = 50
        m1._drift_significant_feature_min = 1
        m1._drift_auto_retraining = False
        np.random.seed(42)
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        m1.record_feature_distribution(ref)
        first_ref_at = m1._reference_initialized_at
        assert first_ref_at is not None

        # 別インスタンスを auto_load=True で生成
        m2 = MLHealthMonitor(persistence=persistence, threshold=3, auto_load=True)
        assert m2._reference_initialized_at is not None
        # ISO フォーマット変換による微小誤差を許容
        assert abs((m2._reference_initialized_at - first_ref_at).total_seconds()) < 1.0

    def test_reset_clears_drift_counter(self, monitor_drift):
        """reset 時に consecutive_drift_detections と last_drift_at がクリアされる.

        旧実装では reset 後も古いカウンタが残っており、reset 直後にも
        should_emergency_stop() が True を返し続ける危険があった。
        Phase 90γ-① fix: reset 時は drift カウンタを仕切り直す。
        """
        from datetime import timedelta

        import numpy as np
        import pandas as pd

        monitor_drift._drift_reference_reset_hours = 168.0
        np.random.seed(42)

        # 1. reference 初期化
        ref = pd.DataFrame({"f1": np.random.normal(0, 1, 200)})
        monitor_drift.record_feature_distribution(ref)
        assert monitor_drift.consecutive_drift_detections == 0

        # 2. drift を発生させて consecutive > 0 にする
        shifted = pd.DataFrame({"f1": np.random.normal(10, 1, 200)})
        monitor_drift.record_feature_distribution(shifted)
        assert monitor_drift.consecutive_drift_detections == 1
        assert monitor_drift.last_drift_at is not None

        # 3. reset 期限切れシミュレーション（200h 前にずらす = 168h より古い）
        monitor_drift._reference_initialized_at = (
            monitor_drift._reference_initialized_at - timedelta(hours=200)
        )

        # 4. 再度呼び出して reset 発火 + drift カウンタクリア
        new_ref = pd.DataFrame({"f1": np.random.normal(20, 1, 200)})
        detected = monitor_drift.record_feature_distribution(new_ref)

        # 5. drift カウンタが仕切り直されていることを検証
        assert detected is False  # reset 直後の戻り値は False
        assert monitor_drift.consecutive_drift_detections == 0
        assert monitor_drift.last_drift_at is None
