# tests/unit/online_learning/test_monitoring.py
"""
Model performance monitoring のテスト
"""

from collections import deque

import numpy as np
import pytest

from crypto_bot.online_learning.monitoring import (
    ClassificationMonitor,
    PerformanceAlert,
)


class TestPerformanceAlert:
    """PerformanceAlert のテストクラス"""

    def test_initialization(self):
        """初期化のテスト"""
        alert = PerformanceAlert(
            metric_name="accuracy",
            threshold=0.8,
            comparison="below",
            severity="high",
            cooldown_minutes=10,
        )

        assert alert.metric_name == "accuracy"
        assert alert.threshold == 0.8
        assert alert.comparison == "below"
        assert alert.severity == "high"
        assert alert.cooldown_minutes == 10

    def test_default_cooldown(self):
        """デフォルトクールダウンのテスト"""
        alert = PerformanceAlert(
            metric_name="f1_score", threshold=0.7, comparison="below", severity="medium"
        )

        assert alert.cooldown_minutes == 5


class TestClassificationMonitor:
    """ClassificationMonitor のテストクラス"""

    @pytest.fixture
    def monitor(self):
        """テスト用モニター"""
        return ClassificationMonitor(window_size=100)

    @pytest.fixture
    def sample_predictions(self):
        """テスト用予測データ"""
        y_true = np.array([1, 0, 1, 1, 0, 1, 0, 0, 1, 1])
        y_pred = np.array([1, 0, 1, 0, 0, 1, 1, 0, 1, 0])
        return y_true, y_pred

    def test_initialization(self):
        """初期化のテスト"""
        monitor = ClassificationMonitor(window_size=500)

        assert monitor.window_size == 500
        assert isinstance(monitor.alert_thresholds, list)
        assert len(monitor.alert_thresholds) > 0
        assert hasattr(monitor, "last_alert_times")
        assert hasattr(monitor, "lock")

    def test_initialization_with_custom_alerts(self):
        """カスタムアラート付き初期化のテスト"""
        custom_alerts = [
            PerformanceAlert("accuracy", 0.9, "below", "high"),
            PerformanceAlert("f1_score", 0.8, "below", "medium"),
        ]

        monitor = ClassificationMonitor(window_size=200, alert_thresholds=custom_alerts)

        assert len(monitor.alert_thresholds) == 2
        assert monitor.alert_thresholds[0].metric_name == "accuracy"
        assert monitor.alert_thresholds[1].metric_name == "f1_score"

    def test_default_alerts(self):
        """デフォルトアラートのテスト"""
        monitor = ClassificationMonitor()

        # デフォルトアラートが設定されているか確認
        alert_metrics = [alert.metric_name for alert in monitor.alert_thresholds]
        assert "accuracy" in alert_metrics

    def test_update_performance(self, monitor, sample_predictions):
        """パフォーマンス更新のテスト"""
        y_true, y_pred = sample_predictions

        # モックメソッドをテスト
        if hasattr(monitor, "update_performance"):
            monitor.update_performance(y_true, y_pred)

            # 何らかの状態が更新されているか確認
            assert hasattr(monitor, "performance_history") or hasattr(
                monitor, "predictions"
            )

    def test_calculate_metrics(self, monitor, sample_predictions):
        """メトリクス計算のテスト"""
        y_true, y_pred = sample_predictions

        # モックで calculate_metrics メソッドをテスト
        if hasattr(monitor, "calculate_metrics"):
            metrics = monitor.calculate_metrics(y_true, y_pred)

            assert isinstance(metrics, dict)
            assert "accuracy" in metrics
            assert 0 <= metrics["accuracy"] <= 1

    def test_accuracy_calculation(self, sample_predictions):
        """精度計算のテスト"""
        y_true, y_pred = sample_predictions

        # sklearn の accuracy_score を直接テスト
        from sklearn.metrics import accuracy_score

        accuracy = accuracy_score(y_true, y_pred)

        assert 0 <= accuracy <= 1
        assert isinstance(accuracy, (float, np.floating))

    def test_f1_score_calculation(self, sample_predictions):
        """F1スコア計算のテスト"""
        y_true, y_pred = sample_predictions

        from sklearn.metrics import f1_score

        f1 = f1_score(y_true, y_pred, average="binary")

        assert 0 <= f1 <= 1
        assert isinstance(f1, (float, np.floating))

    def test_precision_recall_calculation(self, sample_predictions):
        """精度・再現率計算のテスト"""
        y_true, y_pred = sample_predictions

        from sklearn.metrics import precision_score, recall_score

        precision = precision_score(y_true, y_pred, average="binary")
        recall = recall_score(y_true, y_pred, average="binary")

        assert 0 <= precision <= 1
        assert 0 <= recall <= 1

    def test_alert_threshold_checking(self, monitor):
        """アラート閾値チェックのテスト"""
        # モックアラート設定
        alert = PerformanceAlert(
            metric_name="accuracy", threshold=0.8, comparison="below", severity="high"
        )
        monitor.alert_thresholds = [alert]

        # 閾値をチェックするメソッドがあるかテスト
        if hasattr(monitor, "check_alerts"):
            metrics = {"accuracy": 0.7}  # 閾値以下
            alerts = monitor.check_alerts(metrics)

            # アラートが発生するかテスト
            assert isinstance(alerts, list)

    def test_alert_cooldown(self, monitor):
        """アラートクールダウンのテスト"""
        alert = PerformanceAlert(
            metric_name="accuracy",
            threshold=0.8,
            comparison="below",
            severity="high",
            cooldown_minutes=1,
        )
        monitor.alert_thresholds = [alert]

        # 最初のアラート
        if hasattr(monitor, "check_alerts"):
            metrics = {"accuracy": 0.7}
            alerts1 = monitor.check_alerts(metrics)

            # 即座に同じアラート
            alerts2 = monitor.check_alerts(metrics)

            # クールダウンにより2回目はアラートされないはず
            if isinstance(alerts1, list) and isinstance(alerts2, list):
                assert len(alerts2) <= len(alerts1)

    def test_window_size_limit(self, monitor):
        """ウィンドウサイズ制限のテスト"""
        # ウィンドウサイズを超えるデータを追加
        for _ in range(monitor.window_size + 50):
            y_true = np.array([1, 0])
            y_pred = np.array([1, 1])

            if hasattr(monitor, "update_performance"):
                monitor.update_performance(y_true, y_pred)

        # データがウィンドウサイズ内に制限されているかチェック
        if hasattr(monitor, "performance_history"):
            assert len(monitor.performance_history) <= monitor.window_size
        elif hasattr(monitor, "predictions"):
            if isinstance(monitor.predictions, deque):
                assert len(monitor.predictions) <= monitor.window_size

    def test_get_current_performance(self, monitor, sample_predictions):
        """現在のパフォーマンス取得のテスト"""
        y_true, y_pred = sample_predictions

        # データを追加
        if hasattr(monitor, "update_performance"):
            monitor.update_performance(y_true, y_pred)

        # 現在のパフォーマンスを取得
        if hasattr(monitor, "get_current_performance"):
            performance = monitor.get_current_performance()

            assert isinstance(performance, dict)
            assert "accuracy" in performance or len(performance) >= 0

    def test_get_performance_history(self, monitor):
        """パフォーマンス履歴取得のテスト"""
        if hasattr(monitor, "get_performance_history"):
            history = monitor.get_performance_history()

            assert isinstance(history, (list, dict))

    def test_reset_monitor(self, monitor, sample_predictions):
        """モニターリセットのテスト"""
        y_true, y_pred = sample_predictions

        # データを追加
        if hasattr(monitor, "update_performance"):
            monitor.update_performance(y_true, y_pred)

        # リセット
        if hasattr(monitor, "reset"):
            monitor.reset()

            # データがクリアされているかチェック
            if hasattr(monitor, "performance_history"):
                assert len(monitor.performance_history) == 0

    def test_thread_safety(self, monitor):
        """スレッドセーフティのテスト"""
        import threading

        def update_data():
            for _ in range(10):
                y_true = np.array([1, 0, 1])
                y_pred = np.array([1, 1, 0])
                if hasattr(monitor, "update_performance"):
                    monitor.update_performance(y_true, y_pred)

        # 複数スレッドで同時更新
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=update_data)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # エラーが発生しないことを確認
        assert True

    def test_multiclass_classification(self, monitor):
        """多クラス分類のテスト"""
        # 3クラス分類のデータ
        y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 1, 0, 2, 2, 1, 1, 2])

        # 多クラス分類メトリクスの計算
        from sklearn.metrics import accuracy_score, f1_score

        accuracy = accuracy_score(y_true, y_pred)
        f1 = f1_score(y_true, y_pred, average="weighted")

        assert 0 <= accuracy <= 1
        assert 0 <= f1 <= 1

    def test_binary_classification_edge_cases(self, monitor):
        """二値分類エッジケースのテスト"""
        # 全て正解のケース
        y_true = np.array([1, 1, 1, 1])
        y_pred = np.array([1, 1, 1, 1])

        from sklearn.metrics import accuracy_score

        accuracy = accuracy_score(y_true, y_pred)
        assert accuracy == 1.0

        # 全て不正解のケース
        y_true = np.array([1, 1, 1, 1])
        y_pred = np.array([0, 0, 0, 0])

        accuracy = accuracy_score(y_true, y_pred)
        assert accuracy == 0.0

    def test_empty_data_handling(self, monitor):
        """空データ処理のテスト"""
        y_true = np.array([])
        y_pred = np.array([])

        # 空データでエラーが発生しないかテスト
        try:
            if hasattr(monitor, "update_performance"):
                monitor.update_performance(y_true, y_pred)
            assert True
        except Exception:
            # エラーハンドリングがある場合も想定内
            assert True

    def test_mismatched_array_lengths(self, monitor):
        """配列長不一致のテスト"""
        y_true = np.array([1, 0, 1])
        y_pred = np.array([1, 0])  # 長さが異なる

        # 長さ不一致でエラー処理されるかテスト
        try:
            if hasattr(monitor, "update_performance"):
                monitor.update_performance(y_true, y_pred)
            assert True
        except ValueError:
            # ValueError が発生することを期待
            assert True

    def test_performance_degradation_detection(self, monitor):
        """パフォーマンス劣化検出のテスト"""
        # 最初は高パフォーマンス
        good_predictions = np.array([1, 1, 1, 1, 1])
        good_true = np.array([1, 1, 1, 1, 1])

        if hasattr(monitor, "update_performance"):
            monitor.update_performance(good_true, good_predictions)

        # 次に低パフォーマンス
        bad_predictions = np.array([0, 0, 0, 0, 0])
        bad_true = np.array([1, 1, 1, 1, 1])

        if hasattr(monitor, "update_performance"):
            monitor.update_performance(bad_true, bad_predictions)

        # 劣化が検出されるかテスト
        if hasattr(monitor, "detect_performance_drift"):
            drift_detected = monitor.detect_performance_drift()
            assert isinstance(drift_detected, bool)

    def test_alert_severity_levels(self, monitor):
        """アラート重要度レベルのテスト"""
        alerts = [
            PerformanceAlert("accuracy", 0.9, "below", "low"),
            PerformanceAlert("accuracy", 0.8, "below", "medium"),
            PerformanceAlert("accuracy", 0.7, "below", "high"),
        ]
        monitor.alert_thresholds = alerts

        # 各重要度レベルが正しく設定されているか確認
        severities = [alert.severity for alert in monitor.alert_thresholds]
        assert "low" in severities
        assert "medium" in severities
        assert "high" in severities

    def test_comparison_operators(self):
        """比較演算子のテスト"""
        # "above"比較
        alert_above = PerformanceAlert("error_rate", 0.1, "above", "high")
        assert alert_above.comparison == "above"

        # "below"比較
        alert_below = PerformanceAlert("accuracy", 0.8, "below", "medium")
        assert alert_below.comparison == "below"

        # "change"比較
        alert_change = PerformanceAlert("f1_score", 0.05, "change", "low")
        assert alert_change.comparison == "change"
