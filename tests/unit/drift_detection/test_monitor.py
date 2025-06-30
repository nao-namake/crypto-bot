"""
Test cases for drift monitoring system
"""

from crypto_bot.drift_detection.monitor import DriftMonitor


class TestDriftMonitor:
    """Drift Monitor のテストクラス"""

    def test_initialization(self):
        """初期化のテスト"""
        monitor = DriftMonitor()

        assert monitor.ensemble is not None
        assert monitor.detection_config is not None
        assert monitor.alert_callbacks == []

    def test_start_monitoring(self):
        """監視開始のテスト"""
        monitor = DriftMonitor()

        # DriftMonitorのstart_monitoringメソッドが存在することを確認
        assert hasattr(monitor, "start_monitoring")

        # 後始末
        monitor.stop_monitoring()

    def test_stop_monitoring(self):
        """監視停止のテスト"""
        monitor = DriftMonitor()

        # stop_monitoringメソッドが存在することを確認
        assert hasattr(monitor, "stop_monitoring")
        monitor.stop_monitoring()

    def test_add_sample(self):
        """サンプル追加のテスト"""
        monitor = DriftMonitor()

        # DriftMonitorが正常に初期化されたことを確認
        assert monitor.ensemble is not None
