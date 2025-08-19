"""
Data Drift Detection Module

This module provides various algorithms for detecting data drift in
streaming data, which is crucial for maintaining model performance
in changing market conditions.

Supported algorithms:
- ADWIN (Adaptive Windowing)
- DDM (Drift Detection Method)
- EDDM (Early Drift Detection Method)
- Page-Hinkley Test
- Statistical tests (KS test, etc.)
"""

from .detectors import (
    ADWINDetector,
    DDMDetector,
    EDDMDetector,
    PageHinkleyDetector,
    StatisticalDriftDetector,
)
from .ensemble import DriftDetectionEnsemble
from .monitor import DriftMonitor

__all__ = [
    "ADWINDetector",
    "DDMDetector",
    "EDDMDetector",
    "PageHinkleyDetector",
    "StatisticalDriftDetector",
    "DriftDetectionEnsemble",
    "DriftMonitor",
]
