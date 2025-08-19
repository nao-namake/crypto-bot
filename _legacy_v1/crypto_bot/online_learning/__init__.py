"""
Online Learning Module for Crypto Trading Bot

This module provides incremental learning capabilities for adapting to
changing market conditions in real-time without full model retraining.

Key Features:
- Incremental model updates with new data
- Data drift detection and monitoring
- Model performance tracking
- Automatic retraining triggers
- Memory-efficient streaming learning
"""

try:
    from .base import (
        ModelUpdateResult,
        OnlineLearnerBase,
        OnlineLearningConfig,
        PredictionResult,
    )
    from .models import IncrementalMLModel
    from .monitoring import ClassificationMonitor, PerformanceAlert
    from .scheduler import (
        RetrainingJob,
        RetrainingScheduler,
        RetrainingTrigger,
        TriggerType,
    )
except ImportError:
    # Handle missing dependencies gracefully
    pass

__all__ = [
    "IncrementalMLModel",
    "RetrainingScheduler",
    "TriggerType",
    "RetrainingTrigger",
    "RetrainingJob",
    "OnlineLearningConfig",
    "PredictionResult",
    "ModelUpdateResult",
    "OnlineLearnerBase",
    "PerformanceAlert",
    "ClassificationMonitor",
]
