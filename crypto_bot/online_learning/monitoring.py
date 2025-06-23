"""
Model performance monitoring for online learning
"""

import logging
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
)

from .base import PerformanceMonitorBase

logger = logging.getLogger(__name__)


@dataclass
class PerformanceAlert:
    """Performance alert configuration"""

    metric_name: str
    threshold: float
    comparison: str  # "above", "below", "change"
    severity: str  # "low", "medium", "high"
    cooldown_minutes: int = 5


class ClassificationMonitor(PerformanceMonitorBase):
    """Performance monitor for classification models"""

    def __init__(
        self,
        window_size: int = 1000,
        alert_thresholds: Optional[List[PerformanceAlert]] = None,
    ):
        super().__init__(window_size)
        self.alert_thresholds = alert_thresholds or self._default_alerts()
        self.last_alert_times = {}
        self.lock = threading.Lock()

    def _default_alerts(self) -> List[PerformanceAlert]:
        """Get default alert thresholds for classification."""
        return [
            PerformanceAlert("accuracy", 0.1, "below", "high", 10),
            PerformanceAlert("accuracy", 0.05, "change", "medium", 5),
            PerformanceAlert("f1_score", 0.1, "below", "high", 10),
            PerformanceAlert("precision", 0.05, "below", "medium", 5),
            PerformanceAlert("recall", 0.05, "below", "medium", 5),
        ]

    def update(
        self, y_true: np.ndarray, y_pred: np.ndarray, timestamp: datetime = None
    ) -> Dict[str, float]:
        """Update."""
        with self.lock:
            if timestamp is None:
                timestamp = datetime.now()

            # Store predictions
            self.predictions.extend(y_pred.flatten())
            self.actual_values.extend(y_true.flatten())
            self.timestamps.extend([timestamp] * len(y_true))

            # Maintain window size
            while len(self.predictions) > self.window_size:
                self.predictions.popleft()
                self.actual_values.popleft()
                self.timestamps.popleft()

            # Calculate current metrics
            current_metrics = self.get_current_metrics()
            self.metrics_history.append(current_metrics.copy())

            # Check for alerts
            self._check_alerts(current_metrics)

            return current_metrics

    def get_current_metrics(self) -> Dict[str, float]:
        """Calculate current performance metrics"""
        if len(self.predictions) < 10:  # Minimum samples for reliable metrics
            return {}

        y_true = np.array(list(self.actual_values))
        y_pred = np.array(list(self.predictions))

        try:
            metrics = {
                "accuracy": accuracy_score(y_true, y_pred),
                "precision": precision_score(
                    y_true, y_pred, average="weighted", zero_division=0
                ),
                "recall": recall_score(
                    y_true, y_pred, average="weighted", zero_division=0
                ),
                "f1_score": f1_score(
                    y_true, y_pred, average="weighted", zero_division=0
                ),
                "sample_count": len(y_true),
                "timestamp": datetime.now().isoformat(),
            }

            # Add per-class metrics if binary classification
            unique_classes = np.unique(y_true)
            if len(unique_classes) == 2:
                metrics.update(
                    {
                        "precision_class_0": precision_score(
                            y_true, y_pred, pos_label=unique_classes[0], zero_division=0
                        ),
                        "precision_class_1": precision_score(
                            y_true, y_pred, pos_label=unique_classes[1], zero_division=0
                        ),
                        "recall_class_0": recall_score(
                            y_true, y_pred, pos_label=unique_classes[0], zero_division=0
                        ),
                        "recall_class_1": recall_score(
                            y_true, y_pred, pos_label=unique_classes[1], zero_division=0
                        ),
                    }
                )

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {"error": str(e), "sample_count": len(y_true)}

    def _check_alerts(self, current_metrics: Dict[str, float]):
        """Check if any alert thresholds are exceeded"""
        for alert in self.alert_thresholds:
            if self._should_skip_alert(alert):
                continue

            if alert.metric_name not in current_metrics:
                continue

            current_value = current_metrics[alert.metric_name]
            alert_triggered = False

            if alert.comparison == "below":
                alert_triggered = current_value < alert.threshold
            elif alert.comparison == "above":
                alert_triggered = current_value > alert.threshold
            elif alert.comparison == "change":
                alert_triggered = self._check_change_alert(
                    alert.metric_name, alert.threshold
                )

            if alert_triggered:
                self._trigger_alert(alert, current_value, current_metrics)

    def _should_skip_alert(self, alert: PerformanceAlert) -> bool:
        """Check if alert is in cooldown period"""
        if alert.metric_name in self.last_alert_times:
            time_since_last = datetime.now() - self.last_alert_times[alert.metric_name]
            if time_since_last < timedelta(minutes=alert.cooldown_minutes):
                return True
        return False

    def _check_change_alert(self, metric_name: str, threshold: float) -> bool:
        """Check if metric has changed significantly"""
        if len(self.metrics_history) < 5:
            return False

        recent_values = [m.get(metric_name, 0) for m in self.metrics_history[-5:]]
        if not all(v for v in recent_values):  # Skip if any values are 0/None
            return False

        current = recent_values[-1]
        baseline = np.mean(recent_values[:-1])
        change = abs(current - baseline) / max(abs(baseline), 1e-8)

        return change > threshold

    def _trigger_alert(
        self,
        alert: PerformanceAlert,
        current_value: float,
        all_metrics: Dict[str, float],
    ):
        """Trigger performance alert"""
        alert_data = {
            "alert_type": "performance_degradation",
            "metric_name": alert.metric_name,
            "current_value": current_value,
            "threshold": alert.threshold,
            "comparison": alert.comparison,
            "severity": alert.severity,
            "timestamp": datetime.now(),
            "all_metrics": all_metrics.copy(),
        }

        logger.warning(
            f"Performance alert: {alert.metric_name} = {current_value:.4f} "
            f"({alert.comparison} {alert.threshold:.4f})"
        )

        self.last_alert_times[alert.metric_name] = datetime.now()

        # Could add callback mechanism here for external alerting
        return alert_data


class RegressionMonitor(PerformanceMonitorBase):
    """Performance monitor for regression models"""

    def __init__(
        self,
        window_size: int = 1000,
        alert_thresholds: Optional[List[PerformanceAlert]] = None,
    ):
        super().__init__(window_size)
        self.alert_thresholds = alert_thresholds or self._default_alerts()
        self.last_alert_times = {}
        self.lock = threading.Lock()

    def _default_alerts(self) -> List[PerformanceAlert]:
        """Get default alert thresholds for regression."""
        return [
            PerformanceAlert("mse", 1.0, "above", "high", 10),
            PerformanceAlert("mae", 0.5, "above", "medium", 5),
            PerformanceAlert("mse", 0.2, "change", "medium", 10),
        ]

    def update(
        self, y_true: np.ndarray, y_pred: np.ndarray, timestamp: datetime = None
    ) -> Dict[str, float]:
        """Update monitor with new predictions"""
        with self.lock:
            if timestamp is None:
                timestamp = datetime.now()

            # Store predictions
            self.predictions.extend(y_pred.flatten())
            self.actual_values.extend(y_true.flatten())
            self.timestamps.extend([timestamp] * len(y_true))

            # Maintain window size
            while len(self.predictions) > self.window_size:
                self.predictions.popleft()
                self.actual_values.popleft()
                self.timestamps.popleft()

            # Calculate current metrics
            current_metrics = self.get_current_metrics()
            self.metrics_history.append(current_metrics.copy())

            return current_metrics

    def get_current_metrics(self) -> Dict[str, float]:
        """Calculate current performance metrics for regression"""
        if len(self.predictions) < 10:
            return {}

        y_true = np.array(list(self.actual_values))
        y_pred = np.array(list(self.predictions))

        try:
            metrics = {
                "mse": mean_squared_error(y_true, y_pred),
                "mae": mean_absolute_error(y_true, y_pred),
                "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
                "sample_count": len(y_true),
                "timestamp": datetime.now().isoformat(),
            }

            # Add R² score if possible
            ss_res = np.sum((y_true - y_pred) ** 2)
            ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
            r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            metrics["r2_score"] = r2

            # Add error statistics
            errors = y_pred - y_true
            metrics.update(
                {
                    "mean_error": np.mean(errors),
                    "std_error": np.std(errors),
                    "max_error": np.max(np.abs(errors)),
                    "median_error": np.median(errors),
                }
            )

            return metrics

        except Exception as e:
            logger.error(f"Error calculating regression metrics: {e}")
            return {"error": str(e), "sample_count": len(y_true)}


class OnlinePerformanceTracker:
    """
    Comprehensive performance tracking system for online learning

    Manages both classification and regression monitoring,
    with alerting and trend analysis capabilities.
    """

    def __init__(
        self,
        model_type: str = "classification",
        window_size: int = 1000,
        trend_analysis_periods: int = 10,
    ):
        """
        Initialize performance tracker

        Args:
            model_type: "classification" or "regression"
            window_size: Number of samples to keep for metrics calculation
            trend_analysis_periods: Number of periods for trend analysis
        """
        self.model_type = model_type
        self.window_size = window_size
        self.trend_analysis_periods = trend_analysis_periods

        # Initialize appropriate monitor
        if model_type == "classification":
            self.monitor = ClassificationMonitor(window_size)
        elif model_type == "regression":
            self.monitor = RegressionMonitor(window_size)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        # Performance tracking
        self.performance_log = deque(maxlen=10000)
        self.alert_callbacks = []
        self.lock = threading.Lock()

        logger.info(f"OnlinePerformanceTracker initialized for {model_type}")

    def update(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, float]:
        """Update performance tracking with new predictions"""
        with self.lock:
            timestamp = datetime.now()

            # Update monitor
            metrics = self.monitor.update(y_true, y_pred, timestamp)

            # Add to performance log
            log_entry = {
                "timestamp": timestamp,
                "metrics": metrics.copy(),
                "sample_count": len(y_true),
                "metadata": metadata or {},
            }
            self.performance_log.append(log_entry)

            return metrics

    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_logs = [
            log for log in self.performance_log if log["timestamp"] > cutoff_time
        ]

        if not recent_logs:
            return {"no_data": True, "time_period_hours": hours}

        # Aggregate metrics
        all_metrics = defaultdict(list)
        total_samples = 0

        for log in recent_logs:
            total_samples += log["sample_count"]
            for metric, value in log["metrics"].items():
                if isinstance(value, (int, float)) and metric != "sample_count":
                    all_metrics[metric].append(value)

        # Calculate summary statistics
        summary = {
            "time_period_hours": hours,
            "total_samples": total_samples,
            "log_entries": len(recent_logs),
            "metrics_summary": {},
        }

        for metric, values in all_metrics.items():
            if values:
                summary["metrics_summary"][metric] = {
                    "current": values[-1],
                    "mean": np.mean(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "trend": self._calculate_trend(values),
                }

        return summary

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for metric values"""
        if len(values) < 3:
            return "insufficient_data"

        # Simple trend calculation using linear regression slope
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]

        if abs(slope) < 1e-6:
            return "stable"
        elif slope > 0:
            return "improving" if self.model_type == "classification" else "degrading"
        else:
            return "degrading" if self.model_type == "classification" else "improving"

    def detect_performance_degradation(
        self, metric: str = "accuracy", threshold: float = 0.05, periods: int = 5
    ) -> Dict[str, Any]:
        """Detect significant performance degradation"""
        trend_values = self.monitor.get_performance_trend(metric, periods)

        if len(trend_values) < periods:
            return {"insufficient_data": True, "required_periods": periods}

        current = trend_values[-1]
        baseline = np.mean(trend_values[:-1])

        if baseline == 0:
            return {"invalid_baseline": True}

        change = (current - baseline) / abs(baseline)
        degraded = abs(change) > threshold

        if self.model_type == "regression":
            # For regression, lower error metrics are better
            if metric in ["mse", "mae", "rmse"]:
                degraded = change > threshold  # Increase is bad
            else:
                degraded = change < -threshold  # Decrease is bad for r2_score
        else:
            # For classification, higher accuracy/f1 is better
            degraded = change < -threshold  # Decrease is bad

        return {
            "degradation_detected": degraded,
            "current_value": current,
            "baseline_value": baseline,
            "change_percentage": change * 100,
            "threshold_percentage": threshold * 100,
            "metric": metric,
            "periods_analyzed": periods,
        }

    def add_alert_callback(self, callback):
        """Add callback for performance alerts"""
        self.alert_callbacks.append(callback)

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed current metrics and diagnostics"""
        current_metrics = self.monitor.get_current_metrics()

        return {
            "current_metrics": current_metrics,
            "sample_count": len(self.monitor.predictions),
            "window_utilization": len(self.monitor.predictions) / self.window_size,
            "metrics_history_length": len(self.monitor.metrics_history),
            "model_type": self.model_type,
            "last_update": datetime.now().isoformat(),
        }

    def reset(self):
        """Reset all performance tracking"""
        with self.lock:
            self.monitor.predictions.clear()
            self.monitor.actual_values.clear()
            self.monitor.timestamps.clear()
            self.monitor.metrics_history.clear()
            self.performance_log.clear()
            logger.info("Performance tracker reset")

    def export_performance_data(self, filepath: str, hours: int = 24) -> bool:
        """Export performance data to file"""
        try:
            summary = self.get_performance_summary(hours)
            detailed_metrics = self.get_detailed_metrics()

            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "model_type": self.model_type,
                "summary": summary,
                "current_state": detailed_metrics,
                "configuration": {
                    "window_size": self.window_size,
                    "trend_analysis_periods": self.trend_analysis_periods,
                },
            }

            import json

            with open(filepath, "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"Performance data exported to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to export performance data: {e}")
            return False
