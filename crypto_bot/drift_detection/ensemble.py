"""
Ensemble drift detection combining multiple algorithms
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from .detectors import (
    ADWINDetector,
    DDMDetector,
    EDDMDetector,
    PageHinkleyDetector,
    StatisticalDriftDetector,
)

logger = logging.getLogger(__name__)


class DriftDetectionEnsemble:
    """
    Ensemble of multiple drift detection algorithms

    Combines predictions from multiple detectors using voting or
    confidence-based methods to improve robustness.
    """

    def __init__(
        self,
        detectors: Optional[List[str]] = None,
        voting_method: str = "majority",
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize ensemble drift detector

        Args:
            detectors: List of detector names to include
            voting_method: "majority", "unanimous", or "confidence"
            confidence_threshold: Threshold for confidence-based voting
        """
        self.voting_method = voting_method
        self.confidence_threshold = confidence_threshold

        # Initialize detectors
        if detectors is None:
            detectors = ["adwin", "ddm", "statistical"]

        self.detectors = {}
        self._initialize_detectors(detectors)

        # Tracking
        self.detection_history = []
        self.detector_votes = defaultdict(int)
        self.last_detection_time = None
        self.ensemble_drift_detected = False

    def _initialize_detectors(self, detector_names: List[str]):
        """Initialize individual detectors"""
        detector_map = {
            "adwin": ADWINDetector,
            "ddm": DDMDetector,
            "eddm": EDDMDetector,
            "page_hinkley": PageHinkleyDetector,
            "statistical": StatisticalDriftDetector,
        }

        for name in detector_names:
            if name in detector_map:
                self.detectors[name] = detector_map[name]()
                logger.info(f"Initialized {name} drift detector")
            else:
                logger.warning(f"Unknown detector: {name}")

    def update(self, sample: Any, error: Optional[float] = None) -> bool:
        """
        Update all detectors and check for ensemble drift

        Args:
            sample: Data sample (for distribution-based detectors)
            error: Error value (for error-based detectors like DDM)

        Returns:
            True if ensemble detects drift
        """
        detector_results = {}

        # Update each detector
        for name, detector in self.detectors.items():
            try:
                if name in ["ddm", "eddm"] and error is not None:
                    # Error-based detectors
                    result = detector.update(error)
                elif name == "adwin" and isinstance(sample, (int, float)):
                    # ADWIN expects scalar values
                    result = detector.update(float(sample))
                elif name == "page_hinkley" and isinstance(sample, (int, float)):
                    # Page-Hinkley expects scalar values
                    result = detector.update(float(sample))
                elif name == "statistical":
                    # Statistical detector expects arrays
                    result = detector.update(sample)
                else:
                    # Skip if incompatible input
                    continue

                detector_results[name] = result

                if result:
                    self.detector_votes[name] += 1
                    logger.info(f"Drift detected by {name} detector")

            except Exception as e:
                logger.error(f"Error updating {name} detector: {e}")
                detector_results[name] = False

        # Ensemble decision
        ensemble_drift = self._make_ensemble_decision(detector_results)

        if ensemble_drift:
            self.ensemble_drift_detected = True
            self.last_detection_time = datetime.now()
            logger.info("Ensemble drift detection triggered")

            # Record detection event
            self.detection_history.append(
                {
                    "timestamp": datetime.now(),
                    "detector_results": detector_results.copy(),
                    "voting_method": self.voting_method,
                }
            )

        return ensemble_drift

    def _make_ensemble_decision(self, detector_results: Dict[str, bool]) -> bool:
        """Make ensemble drift decision based on individual results"""
        if not detector_results:
            return False

        detections = list(detector_results.values())
        num_detections = sum(detections)
        total_detectors = len(detections)

        if self.voting_method == "majority":
            return num_detections > total_detectors / 2
        elif self.voting_method == "unanimous":
            return num_detections == total_detectors
        elif self.voting_method == "confidence":
            # Use confidence threshold
            confidence = num_detections / total_detectors
            return confidence >= self.confidence_threshold
        else:
            # Default to majority
            return num_detections > total_detectors / 2

    def reset(self):
        """Reset all detectors and ensemble state"""
        for detector in self.detectors.values():
            detector.reset()

        self.detection_history.clear()
        self.detector_votes.clear()
        self.last_detection_time = None
        self.ensemble_drift_detected = False

        logger.info("Ensemble drift detector reset")

    def get_ensemble_info(self) -> Dict[str, Any]:
        """Get comprehensive ensemble information"""
        detector_info = {}
        for name, detector in self.detectors.items():
            detector_info[name] = detector.get_drift_info()

        return {
            "ensemble_drift_detected": self.ensemble_drift_detected,
            "last_detection_time": (
                self.last_detection_time.isoformat()
                if self.last_detection_time
                else None
            ),
            "voting_method": self.voting_method,
            "confidence_threshold": self.confidence_threshold,
            "detector_votes": dict(self.detector_votes),
            "detection_history_length": len(self.detection_history),
            "individual_detectors": detector_info,
        }

    def get_detection_summary(self) -> Dict[str, Any]:
        """Get summary of recent detections"""
        if not self.detection_history:
            return {"no_detections": True}

        recent_detections = self.detection_history[-10:]  # Last 10 detections

        # Count detector contributions
        detector_contributions = defaultdict(int)
        for detection in recent_detections:
            for detector, result in detection["detector_results"].items():
                if result:
                    detector_contributions[detector] += 1

        return {
            "total_detections": len(self.detection_history),
            "recent_detections": len(recent_detections),
            "detector_contributions": dict(detector_contributions),
            "most_active_detector": (
                max(detector_contributions.items(), key=lambda x: x[1])[0]
                if detector_contributions
                else None
            ),
            "last_detection": (
                self.detection_history[-1] if self.detection_history else None
            ),
        }

    def is_any_detector_active(self) -> bool:
        """Check if any detector has detected drift recently"""
        return any(detector.drift_detected for detector in self.detectors.values())

    def get_detector_status(self) -> Dict[str, bool]:
        """Get current status of all detectors"""
        return {
            name: detector.drift_detected for name, detector in self.detectors.items()
        }

    def add_detector(self, name: str, detector_class, **kwargs):
        """Add a new detector to the ensemble"""
        if name in self.detectors:
            logger.warning(f"Detector {name} already exists, replacing...")

        self.detectors[name] = detector_class(**kwargs)
        logger.info(f"Added {name} detector to ensemble")

    def remove_detector(self, name: str):
        """Remove a detector from the ensemble"""
        if name in self.detectors:
            del self.detectors[name]
            logger.info(f"Removed {name} detector from ensemble")
        else:
            logger.warning(f"Detector {name} not found in ensemble")

    def set_voting_method(self, method: str, threshold: Optional[float] = None):
        """Change the voting method"""
        valid_methods = ["majority", "unanimous", "confidence"]
        if method not in valid_methods:
            raise ValueError(f"Invalid voting method. Choose from: {valid_methods}")

        self.voting_method = method
        if threshold is not None:
            self.confidence_threshold = threshold

        logger.info(f"Ensemble voting method changed to: {method}")
        if threshold is not None:
            logger.info(f"Confidence threshold set to: {threshold}")
