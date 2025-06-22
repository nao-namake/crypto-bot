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

from .engine import OnlineLearningEngine
from .models import IncrementalMLModel, OnlineClassifier, OnlineRegressor
from .monitor import ModelPerformanceMonitor
from .scheduler import RetrainingScheduler

__all__ = [
    "OnlineLearningEngine",
    "IncrementalMLModel",
    "OnlineClassifier",
    "OnlineRegressor",
    "RetrainingScheduler",
    "ModelPerformanceMonitor",
]
