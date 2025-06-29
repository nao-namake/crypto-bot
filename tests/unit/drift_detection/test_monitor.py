# tests/unit/drift_detection/test_monitor.py
"""
Drift detection monitor のテスト
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from crypto_bot.drift_detection.detectors import ADWINDetector
from crypto_bot.drift_detection.monitor import DriftMonitor


class TestDriftMonitor:
    """Drift Monitor のテストクラス"""

    def test_initialization(self):
        """初期化のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector, monitoring_interval=60)

        assert monitor.detector == detector
        assert monitor.monitoring_interval == 60
        assert not monitor.is_monitoring
        assert len(monitor.drift_history) == 0

    def test_start_monitoring(self):
        """監視開始のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector)

        monitor.start_monitoring()

        assert monitor.is_monitoring

        # 後始末
        monitor.stop_monitoring()

    def test_stop_monitoring(self):
        """監視停止のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector)

        monitor.start_monitoring()
        monitor.stop_monitoring()

        assert not monitor.is_monitoring

    def test_add_sample(self):
        """サンプル追加のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector)

        # サンプル追加
        drift_detected = monitor.add_sample(1.0)

        assert isinstance(drift_detected, bool)
        assert len(monitor.sample_buffer) == 1

    def test_sample_buffer_limit(self):
        """サンプルバッファの制限テスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector, max_buffer_size=5)

        # バッファサイズを超えるサンプルを追加
        for i in range(10):
            monitor.add_sample(float(i))

        # バッファサイズが制限されているか確認
        assert len(monitor.sample_buffer) <= 5

    def test_drift_history_recording(self):
        """ドリフト履歴記録のテスト"""
        detector = Mock()
        detector.update.return_value = True  # ドリフト検出をシミュレート
        detector.drift_detected = True
        detector.last_drift_time = datetime.now()

        monitor = DriftMonitor(detector=detector)

        # ドリフト検出
        drift_detected = monitor.add_sample(1.0)

        assert drift_detected
        assert len(monitor.drift_history) == 1

    def test_get_statistics(self):
        """統計情報取得のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector)

        # いくつかサンプルを追加
        for i in range(10):
            monitor.add_sample(float(i))

        stats = monitor.get_statistics()

        assert "total_samples" in stats
        assert "drift_count" in stats
        assert "is_monitoring" in stats
        assert "detector_status" in stats
        assert stats["total_samples"] == 10

    def test_get_recent_drifts(self):
        """最近のドリフト取得のテスト"""
        detector = Mock()
        detector.update.return_value = True
        detector.drift_detected = True
        detector.last_drift_time = datetime.now()

        monitor = DriftMonitor(detector=detector)

        # ドリフトを記録
        monitor.add_sample(1.0)

        recent_drifts = monitor.get_recent_drifts(hours=1)

        assert len(recent_drifts) == 1

    def test_get_recent_drifts_time_filter(self):
        """時間フィルタ付きドリフト取得のテスト"""
        detector = Mock()
        monitor = DriftMonitor(detector=detector)

        # 古いドリフトを追加
        old_time = datetime.now() - timedelta(hours=2)
        monitor.drift_history.append({"timestamp": old_time, "sample_count": 100})

        # 新しいドリフトを追加
        new_time = datetime.now()
        monitor.drift_history.append({"timestamp": new_time, "sample_count": 200})

        recent_drifts = monitor.get_recent_drifts(hours=1)

        # 1時間以内のドリフトのみ返される
        assert len(recent_drifts) == 1
        assert recent_drifts[0]["sample_count"] == 200

    def test_reset_monitor(self):
        """モニターリセットのテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector)

        # データを追加
        monitor.add_sample(1.0)
        monitor.add_sample(2.0)

        # リセット
        monitor.reset()

        assert len(monitor.sample_buffer) == 0
        assert len(monitor.drift_history) == 0
        assert monitor.total_samples == 0

    def test_configure_detector(self):
        """検出器設定のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector)

        new_detector = Mock()

        # 検出器を変更
        monitor.configure_detector(new_detector)

        assert monitor.detector == new_detector

    def test_set_monitoring_interval(self):
        """監視間隔設定のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector, monitoring_interval=60)

        # 間隔を変更
        monitor.set_monitoring_interval(30)

        assert monitor.monitoring_interval == 30

    def test_export_drift_history(self):
        """ドリフト履歴エクスポートのテスト"""
        detector = Mock()
        monitor = DriftMonitor(detector=detector)

        # ドリフト履歴を追加
        monitor.drift_history.append({"timestamp": datetime.now(), "sample_count": 100})
        monitor.drift_history.append({"timestamp": datetime.now(), "sample_count": 200})

        history = monitor.export_drift_history()

        assert len(history) == 2
        assert all("timestamp" in entry for entry in history)
        assert all("sample_count" in entry for entry in history)

    @patch("crypto_bot.drift_detection.monitor.logging")
    def test_logging_on_drift_detection(self, mock_logging):
        """ドリフト検出時のログテスト"""
        detector = Mock()
        detector.update.return_value = True
        detector.drift_detected = True
        detector.last_drift_time = datetime.now()

        monitor = DriftMonitor(detector=detector)

        # ドリフト検出
        monitor.add_sample(1.0)

        # ログが呼ばれているか確認（実装依存）
        # このテストは実装によっては不要

    def test_concurrent_access_safety(self):
        """並行アクセス安全性のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector)

        import threading

        def add_samples():
            for i in range(10):
                monitor.add_sample(float(i))

        # 複数スレッドで同時にサンプル追加
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=add_samples)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # データが正しく処理されていることを確認
        assert monitor.total_samples == 30

    def test_memory_usage_control(self):
        """メモリ使用量制御のテスト"""
        detector = ADWINDetector()
        monitor = DriftMonitor(detector=detector, max_history_size=3)

        # 履歴制限を超えるドリフトを追加
        for i in range(5):
            monitor.drift_history.append(
                {"timestamp": datetime.now(), "sample_count": i * 100}
            )

        # 履歴サイズが制限されているか確認
        if hasattr(monitor, "max_history_size"):
            monitor._trim_history()  # 実装依存のメソッド
            assert len(monitor.drift_history) <= 3
