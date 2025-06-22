"""
Drift monitoring and alerting system
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import logging
import threading
import time
from collections import deque, defaultdict
import json
from pathlib import Path

from .ensemble import DriftDetectionEnsemble
from .detectors import (
    ADWINDetector,
    DDMDetector,
    StatisticalDriftDetector
)

logger = logging.getLogger(__name__)


class DriftMonitor:
    """
    Comprehensive drift monitoring system
    
    Combines multiple drift detection algorithms with alerting,
    logging, and automatic response capabilities.
    """
    
    def __init__(self,
                 detection_config: Optional[Dict[str, Any]] = None,
                 alert_callbacks: Optional[List[Callable]] = None,
                 log_file: Optional[str] = None):
        """
        Initialize drift monitor
        
        Args:
            detection_config: Configuration for drift detectors
            alert_callbacks: Functions to call when drift is detected
            log_file: File to log drift events
        """
        self.detection_config = detection_config or self._default_config()
        self.alert_callbacks = alert_callbacks or []
        self.log_file = log_file
        
        # Initialize ensemble detector
        self.ensemble = DriftDetectionEnsemble(
            detectors=self.detection_config.get("detectors", ["adwin", "ddm", "statistical"]),
            voting_method=self.detection_config.get("voting_method", "majority"),
            confidence_threshold=self.detection_config.get("confidence_threshold", 0.7)
        )
        
        # Monitoring state
        self.monitoring_active = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        # Event tracking
        self.drift_events = deque(maxlen=1000)
        self.alert_history = deque(maxlen=500)
        self.performance_metrics = deque(maxlen=10000)
        
        # Alert configuration
        self.alert_cooldown = timedelta(minutes=self.detection_config.get("alert_cooldown_minutes", 5))
        self.last_alert_time = None
        
        # Data buffers
        self.sample_buffer = deque(maxlen=self.detection_config.get("buffer_size", 1000))
        self.error_buffer = deque(maxlen=self.detection_config.get("error_buffer_size", 1000))
        
        logger.info("DriftMonitor initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for drift detection"""
        return {
            "detectors": ["adwin", "ddm", "statistical"],
            "voting_method": "majority",
            "confidence_threshold": 0.7,
            "alert_cooldown_minutes": 5,
            "buffer_size": 1000,
            "error_buffer_size": 1000,
            "log_drift_events": True,
            "auto_reset_after_drift": False,
            "performance_threshold": 0.1,
            "min_samples_for_detection": 100
        }
    
    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback function for drift alerts"""
        self.alert_callbacks.append(callback)
        logger.info(f"Added alert callback: {callback.__name__}")
    
    def start_monitoring(self, monitoring_interval: float = 1.0):
        """Start continuous drift monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(monitoring_interval,),
            daemon=True
        )
        self.monitor_thread.start()
        
        logger.info(f"Started drift monitoring (interval: {monitoring_interval}s)")
    
    def stop_monitoring(self):
        """Stop drift monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        
        logger.info("Stopped drift monitoring")
    
    def _monitoring_loop(self, interval: float):
        """Main monitoring loop"""
        while not self.stop_event.wait(interval):
            try:
                self._check_drift_status()
                self._update_performance_metrics()
                self._cleanup_old_data()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def update_sample(self, sample: Any, error: Optional[float] = None, 
                     performance_metrics: Optional[Dict[str, float]] = None):
        """
        Update monitor with new sample
        
        Args:
            sample: Data sample for drift detection
            error: Error value (0/1 for correct/incorrect)
            performance_metrics: Current model performance metrics
        """
        with self.lock:
            # Add to buffers
            self.sample_buffer.append({
                "data": sample,
                "timestamp": datetime.now(),
                "error": error
            })
            
            if error is not None:
                self.error_buffer.append({
                    "error": error,
                    "timestamp": datetime.now()
                })
            
            if performance_metrics:
                self.performance_metrics.append({
                    "metrics": performance_metrics,
                    "timestamp": datetime.now()
                })
            
            # Check for drift
            if len(self.sample_buffer) >= self.detection_config.get("min_samples_for_detection", 100):
                drift_detected = self.ensemble.update(sample, error)
                
                if drift_detected:
                    self._handle_drift_detection(sample, error, performance_metrics)
    
    def _handle_drift_detection(self, sample: Any, error: Optional[float], 
                               performance_metrics: Optional[Dict[str, float]]):
        """Handle drift detection event"""
        drift_event = {
            "timestamp": datetime.now(),
            "sample": sample,
            "error": error,
            "performance_metrics": performance_metrics,
            "detector_results": self.ensemble.get_detector_status(),
            "ensemble_info": self.ensemble.get_ensemble_info()
        }
        
        self.drift_events.append(drift_event)
        
        # Log event
        if self.detection_config.get("log_drift_events", True):
            self._log_drift_event(drift_event)
        
        # Send alerts
        self._send_drift_alerts(drift_event)
        
        # Auto-reset if enabled
        if self.detection_config.get("auto_reset_after_drift", False):
            self.ensemble.reset()
            logger.info("Auto-reset ensemble after drift detection")
    
    def _send_drift_alerts(self, drift_event: Dict[str, Any]):
        """Send drift alerts to registered callbacks"""
        # Check cooldown
        if (self.last_alert_time and 
            datetime.now() - self.last_alert_time < self.alert_cooldown):
            logger.debug("Alert in cooldown period, skipping")
            return
        
        alert_data = {
            "event_type": "data_drift",
            "timestamp": drift_event["timestamp"],
            "severity": "high",
            "message": "Data drift detected by ensemble",
            "details": {
                "detector_results": drift_event["detector_results"],
                "ensemble_voting": drift_event["ensemble_info"]["voting_method"],
                "performance_impact": drift_event.get("performance_metrics", {})
            }
        }
        
        # Send to callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback {callback.__name__}: {e}")
        
        self.alert_history.append(alert_data)
        self.last_alert_time = datetime.now()
        
        logger.info("Drift alerts sent")
    
    def _log_drift_event(self, drift_event: Dict[str, Any]):
        """Log drift event to file"""
        if not self.log_file:
            return
        
        try:
            log_entry = {
                "timestamp": drift_event["timestamp"].isoformat(),
                "event_type": "drift_detection",
                "detector_results": drift_event["detector_results"],
                "ensemble_info": drift_event["ensemble_info"],
                "performance_metrics": drift_event.get("performance_metrics", {})
            }
            
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to log drift event: {e}")
    
    def _check_drift_status(self):
        """Check current drift status and detector health"""
        if not self.sample_buffer:
            return
        
        # Check for stuck detectors
        detector_status = self.ensemble.get_detector_status()
        active_detectors = sum(detector_status.values())
        
        if active_detectors == len(detector_status):
            logger.warning("All detectors reporting drift - possible system issue")
        
        # Check performance degradation
        self._check_performance_degradation()
    
    def _check_performance_degradation(self):
        """Check for performance degradation trends"""
        if len(self.performance_metrics) < 10:
            return
        
        recent_metrics = list(self.performance_metrics)[-10:]
        
        # Look for declining performance trends
        for metric_name in ["accuracy", "precision", "recall", "f1"]:
            values = [m["metrics"].get(metric_name) for m in recent_metrics 
                     if metric_name in m["metrics"]]
            
            if len(values) >= 5:
                trend = np.polyfit(range(len(values)), values, 1)[0]
                if trend < -self.detection_config.get("performance_threshold", 0.1):
                    logger.warning(f"Declining {metric_name} trend detected: {trend:.4f}")
    
    def _update_performance_metrics(self):
        """Update aggregated performance metrics"""
        if not self.error_buffer:
            return
        
        # Calculate recent error rate
        recent_errors = [e["error"] for e in list(self.error_buffer)[-100:]]
        if recent_errors:
            error_rate = np.mean(recent_errors)
            
            # Log significant changes
            if len(self.performance_metrics) > 0:
                last_error_rate = self.performance_metrics[-1]["metrics"].get("error_rate", 0)
                if abs(error_rate - last_error_rate) > 0.05:
                    logger.info(f"Error rate change: {last_error_rate:.3f} -> {error_rate:.3f}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Clean drift events older than 24 hours
        while (self.drift_events and 
               self.drift_events[0]["timestamp"] < cutoff_time):
            self.drift_events.popleft()
        
        # Clean alert history
        while (self.alert_history and 
               self.alert_history[0]["timestamp"] < cutoff_time):
            self.alert_history.popleft()
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status"""
        with self.lock:
            return {
                "monitoring_active": self.monitoring_active,
                "ensemble_status": self.ensemble.get_ensemble_info(),
                "recent_drift_events": len([e for e in self.drift_events 
                                          if e["timestamp"] > datetime.now() - timedelta(hours=1)]),
                "total_drift_events": len(self.drift_events),
                "alert_callbacks_count": len(self.alert_callbacks),
                "sample_buffer_size": len(self.sample_buffer),
                "performance_metrics_count": len(self.performance_metrics),
                "last_alert_time": self.last_alert_time.isoformat() if self.last_alert_time else None
            }
    
    def get_drift_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get drift detection summary for specified time period"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_events = [e for e in self.drift_events if e["timestamp"] > cutoff_time]
        
        if not recent_events:
            return {"no_drift_events": True, "time_period_hours": hours}
        
        # Analyze detector contributions
        detector_contributions = defaultdict(int)
        for event in recent_events:
            for detector, detected in event["detector_results"].items():
                if detected:
                    detector_contributions[detector] += 1
        
        return {
            "time_period_hours": hours,
            "total_drift_events": len(recent_events),
            "events_per_hour": len(recent_events) / hours,
            "detector_contributions": dict(detector_contributions),
            "most_active_detector": max(detector_contributions.items(), 
                                      key=lambda x: x[1])[0] if detector_contributions else None,
            "first_event": recent_events[0]["timestamp"].isoformat(),
            "last_event": recent_events[-1]["timestamp"].isoformat(),
            "ensemble_voting_method": self.ensemble.voting_method
        }
    
    def reset_all_detectors(self):
        """Reset all drift detectors"""
        with self.lock:
            self.ensemble.reset()
            self.drift_events.clear()
            self.sample_buffer.clear()
            self.error_buffer.clear()
            logger.info("All drift detectors reset")
    
    def export_drift_data(self, filepath: str, hours: int = 24) -> bool:
        """Export drift detection data to file"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_events = [e for e in self.drift_events if e["timestamp"] > cutoff_time]
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "time_period_hours": hours,
                "monitoring_config": self.detection_config,
                "drift_events": [
                    {
                        "timestamp": e["timestamp"].isoformat(),
                        "detector_results": e["detector_results"],
                        "ensemble_info": e["ensemble_info"]
                    } for e in recent_events
                ],
                "summary": self.get_drift_summary(hours)
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Drift data exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export drift data: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_monitoring()


# Convenience functions for common alerting scenarios

def console_alert_callback(alert_data: Dict[str, Any]):
    """Simple console alert callback"""
    timestamp = alert_data["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    print(f"[DRIFT ALERT {timestamp}] {alert_data['message']}")
    if alert_data.get("details"):
        print(f"Details: {alert_data['details']}")


def file_alert_callback(log_file: str):
    """Create file-based alert callback"""
    def callback(alert_data: Dict[str, Any]):
        try:
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - DRIFT ALERT: {alert_data}\n")
        except Exception as e:
            logger.error(f"Failed to write alert to file {log_file}: {e}")
    
    return callback


def email_alert_callback(smtp_config: Dict[str, Any]):
    """Create email-based alert callback (requires additional setup)"""
    def callback(alert_data: Dict[str, Any]):
        # Placeholder for email implementation
        logger.info(f"Email alert would be sent: {alert_data['message']}")
        # Implementation would use smtplib to send actual emails
    
    return callback