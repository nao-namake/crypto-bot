"""
Base classes for online learning components
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class OnlineLearningConfig:
    """Configuration for online learning system"""

    # Model update settings
    update_frequency: str = "batch"  # "sample", "batch", "time"
    batch_size: int = 100
    update_interval_minutes: int = 60

    # Memory management
    memory_window: int = 10000  # Number of samples to keep in memory
    forgetting_factor: float = 0.95  # Exponential forgetting for older samples

    # Performance monitoring
    performance_window: int = 1000  # Window for performance calculation
    performance_threshold: float = 0.1  # Minimum accuracy drop to trigger retrain

    # Drift detection
    enable_drift_detection: bool = True
    drift_detection_window: int = 500
    drift_threshold: float = 0.01

    # Retraining triggers
    enable_auto_retrain: bool = True
    retrain_performance_threshold: float = 0.15
    retrain_drift_threshold: float = 0.05
    min_samples_for_retrain: int = 1000

    # Model persistence
    save_interval_minutes: int = 30
    max_model_versions: int = 10


@dataclass
class PredictionResult:
    """Result of online prediction"""

    prediction: Union[float, int, np.ndarray]
    confidence: float
    model_version: str
    timestamp: datetime
    features_used: List[str]
    metadata: Dict[str, Any]


@dataclass
class ModelUpdateResult:
    """Result of model update"""

    success: bool
    samples_processed: int
    performance_change: float
    drift_detected: bool
    model_version: str
    update_time_ms: float
    memory_usage_mb: float
    message: str


class OnlineLearnerBase(ABC):
    """Base class for online learning models"""

    def __init__(self, config: OnlineLearningConfig):
        self.config = config
        self.model_version = "1.0.0"
        self.samples_seen = 0
        self.last_update = datetime.now()
        self.performance_history = []
        self.is_fitted = False

    @abstractmethod
    def partial_fit(self, X: np.ndarray, y: np.ndarray) -> ModelUpdateResult:
        """Update model with new data samples"""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> PredictionResult:
        """Make prediction with confidence estimate"""
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities (for classifiers)"""
        pass

    @abstractmethod
    def get_feature_importance(self) -> Dict[str, float]:
        """Get current feature importance scores"""
        pass

    @abstractmethod
    def save_model(self, path: str) -> bool:
        """Save current model state"""
        pass

    @abstractmethod
    def load_model(self, path: str) -> bool:
        """Load model from saved state"""
        pass

    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        return {
            "model_version": self.model_version,
            "samples_seen": self.samples_seen,
            "last_update": self.last_update.isoformat(),
            "is_fitted": self.is_fitted,
            "performance_history_length": len(self.performance_history),
            "config": self.config.__dict__,
        }


class DriftDetectorBase(ABC):
    """Base class for drift detection algorithms"""

    def __init__(self, window_size: int = 500, threshold: float = 0.01):
        self.window_size = window_size
        self.threshold = threshold
        self.reference_data = []
        self.current_data = []
        self.drift_detected = False
        self.last_drift_time = None

    @abstractmethod
    def update(self, sample: np.ndarray) -> bool:
        """Update detector with new sample, return True if drift detected"""
        pass

    @abstractmethod
    def reset(self):
        """Reset detector state"""
        pass

    def get_drift_info(self) -> Dict[str, Any]:
        """Get drift detection information"""
        return {
            "drift_detected": self.drift_detected,
            "last_drift_time": (
                self.last_drift_time.isoformat() if self.last_drift_time else None
            ),
            "reference_samples": len(self.reference_data),
            "current_samples": len(self.current_data),
            "threshold": self.threshold,
            "window_size": self.window_size,
        }


class PerformanceMonitorBase(ABC):
    """Base class for model performance monitoring"""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.predictions = []
        self.actual_values = []
        self.timestamps = []
        self.metrics_history = []

    @abstractmethod
    def update(
        self, y_true: np.ndarray, y_pred: np.ndarray, timestamp: datetime = None
    ) -> Dict[str, float]:
        """Update monitor with new predictions and actual values"""
        pass

    @abstractmethod
    def get_current_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        pass

    def get_performance_trend(self, metric: str, periods: int = 10) -> List[float]:
        """Get trend for specific metric over time periods"""
        if not self.metrics_history:
            return []

        recent_metrics = self.metrics_history[-periods:]
        return [m.get(metric, 0.0) for m in recent_metrics]

    def is_performance_degraded(self, metric: str, threshold: float) -> bool:
        """Check if performance has degraded beyond threshold"""
        trend = self.get_performance_trend(metric, periods=5)
        if len(trend) < 2:
            return False

        current = trend[-1]
        baseline = np.mean(trend[:-1]) if len(trend) > 1 else trend[0]
        degradation = abs(current - baseline) / max(abs(baseline), 1e-8)

        return degradation > threshold
