"""
Automatic retraining scheduler for online learning
"""

import logging
import pickle
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import schedule

from ..drift_detection.monitor import DriftMonitor
from .base import OnlineLearnerBase, OnlineLearningConfig
from .monitoring import OnlinePerformanceTracker

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of retraining triggers"""

    PERFORMANCE_DEGRADATION = "performance_degradation"
    DRIFT_DETECTION = "drift_detection"
    SCHEDULED_TIME = "scheduled_time"
    SAMPLE_COUNT = "sample_count"
    MANUAL = "manual"


@dataclass
class RetrainingTrigger:
    """Configuration for retraining triggers"""

    trigger_type: TriggerType
    threshold: Optional[float] = None
    schedule_cron: Optional[str] = None
    sample_interval: Optional[int] = None
    enabled: bool = True
    priority: int = 1  # Higher number = higher priority


@dataclass
class RetrainingJob:
    """Retraining job specification"""

    job_id: str
    trigger: RetrainingTrigger
    model: OnlineLearnerBase
    data_source: Callable[[], tuple]  # Function returning (X, y)
    timestamp: datetime
    priority: int
    metadata: Dict[str, Any]


class RetrainingScheduler:
    """
    Automatic retraining scheduler for online learning models

    Manages multiple trigger conditions and coordinates retraining
    across different models and data sources.
    """

    def __init__(
        self,
        config: OnlineLearningConfig,
        performance_monitor: Optional[OnlinePerformanceTracker] = None,
        drift_monitor: Optional[DriftMonitor] = None,
    ):
        """
        Initialize retraining scheduler

        Args:
            config: Online learning configuration
            performance_monitor: Performance monitoring system
            drift_monitor: Drift detection system
        """
        self.config = config
        self.performance_monitor = performance_monitor
        self.drift_monitor = drift_monitor

        # Scheduler state
        self.active = False
        self.scheduler_thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()

        # Job management
        self.pending_jobs = deque()
        self.completed_jobs = deque(maxlen=1000)
        self.failed_jobs = deque(maxlen=100)
        self.job_counter = 0

        # Registered models and triggers
        self.registered_models = {}
        self.triggers = {}
        self.data_sources = {}

        # State tracking
        self.last_retrain_times = {}
        self.retrain_counts = defaultdict(int)
        self.performance_history = defaultdict(list)

        # Default triggers
        self._setup_default_triggers()

        logger.info("RetrainingScheduler initialized")

    def _setup_default_triggers(self):
        """Setup default retraining triggers"""
        if self.config.enable_auto_retrain:
            # Performance degradation trigger
            perf_trigger = RetrainingTrigger(
                trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
                threshold=self.config.retrain_performance_threshold,
                enabled=True,
                priority=3,
            )
            self.add_trigger("performance_degradation", perf_trigger)

            # Drift detection trigger
            if self.config.enable_drift_detection:
                drift_trigger = RetrainingTrigger(
                    trigger_type=TriggerType.DRIFT_DETECTION,
                    threshold=self.config.retrain_drift_threshold,
                    enabled=True,
                    priority=2,
                )
                self.add_trigger("drift_detection", drift_trigger)

            # Sample count trigger
            sample_trigger = RetrainingTrigger(
                trigger_type=TriggerType.SAMPLE_COUNT,
                sample_interval=self.config.min_samples_for_retrain,
                enabled=True,
                priority=1,
            )
            self.add_trigger("sample_count", sample_trigger)

            # Scheduled time trigger (daily)
            time_trigger = RetrainingTrigger(
                trigger_type=TriggerType.SCHEDULED_TIME,
                schedule_cron="0 2 * * *",  # 2 AM daily
                enabled=False,  # Disabled by default
                priority=1,
            )
            self.add_trigger("daily_retrain", time_trigger)

    def register_model(
        self,
        model_id: str,
        model: OnlineLearnerBase,
        data_source: Callable[[], tuple],
        triggers: Optional[List[str]] = None,
    ):
        """
        Register a model for automatic retraining

        Args:
            model_id: Unique identifier for the model
            model: Online learning model
            data_source: Function that returns (X, y) training data
            triggers: List of trigger names to apply (None = all enabled triggers)
        """
        with self.lock:
            self.registered_models[model_id] = model
            self.data_sources[model_id] = data_source

            if triggers is None:
                triggers = [
                    name for name, trigger in self.triggers.items() if trigger.enabled
                ]

            # Initialize tracking
            self.last_retrain_times[model_id] = datetime.now()
            self.retrain_counts[model_id] = 0

            logger.info(f"Registered model '{model_id}' with triggers: {triggers}")

    def add_trigger(self, name: str, trigger: RetrainingTrigger):
        """Add a retraining trigger"""
        self.triggers[name] = trigger
        logger.info(f"Added trigger '{name}': {trigger.trigger_type.value}")

    def remove_trigger(self, name: str):
        """Remove a retraining trigger"""
        if name in self.triggers:
            del self.triggers[name]
            logger.info(f"Removed trigger '{name}'")

    def start_scheduler(self, check_interval: float = 60.0):
        """Start the automatic retraining scheduler"""
        if self.active:
            logger.warning("Scheduler already active")
            return

        self.active = True
        self.stop_event.clear()

        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop, args=(check_interval,), daemon=True
        )
        self.scheduler_thread.start()

        logger.info(f"Started retraining scheduler (check interval: {check_interval}s)")

    def stop_scheduler(self):
        """Stop the retraining scheduler"""
        if not self.active:
            return

        self.active = False
        self.stop_event.set()

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10.0)

        logger.info("Stopped retraining scheduler")

    def _scheduler_loop(self, check_interval: float):
        """Main scheduler loop"""
        while not self.stop_event.wait(check_interval):
            try:
                self._check_triggers()
                self._process_pending_jobs()
                self._cleanup_old_jobs()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")

    def _check_triggers(self):
        """Check all triggers for all registered models"""
        for model_id in self.registered_models.keys():
            for trigger_name, trigger in self.triggers.items():
                if not trigger.enabled:
                    continue

                try:
                    if self._should_trigger_retrain(model_id, trigger_name, trigger):
                        self._schedule_retrain(model_id, trigger_name, trigger)
                except Exception as e:
                    logger.error(
                        f"Error checking trigger {trigger_name} for model {model_id}: {e}"
                    )

    def _should_trigger_retrain(
        self, model_id: str, trigger_name: str, trigger: RetrainingTrigger
    ) -> bool:
        """Check if a specific trigger should fire for a model"""
        model = self.registered_models[model_id]

        # Check cooldown period
        last_retrain = self.last_retrain_times.get(model_id)
        if last_retrain:
            time_since_retrain = datetime.now() - last_retrain
            min_interval = timedelta(minutes=30)  # Minimum 30 minutes between retrains
            if time_since_retrain < min_interval:
                return False

        if trigger.trigger_type == TriggerType.PERFORMANCE_DEGRADATION:
            return self._check_performance_trigger(model_id, trigger)

        elif trigger.trigger_type == TriggerType.DRIFT_DETECTION:
            return self._check_drift_trigger(model_id, trigger)

        elif trigger.trigger_type == TriggerType.SAMPLE_COUNT:
            return self._check_sample_count_trigger(model_id, trigger)

        elif trigger.trigger_type == TriggerType.SCHEDULED_TIME:
            return self._check_schedule_trigger(model_id, trigger)

        return False

    def _check_performance_trigger(
        self, model_id: str, trigger: RetrainingTrigger
    ) -> bool:
        """Check performance degradation trigger"""
        if not self.performance_monitor:
            return False

        # Get performance degradation analysis
        degradation = self.performance_monitor.detect_performance_degradation(
            threshold=trigger.threshold or 0.05
        )

        return degradation.get("degradation_detected", False)

    def _check_drift_trigger(self, model_id: str, trigger: RetrainingTrigger) -> bool:
        """Check drift detection trigger"""
        if not self.drift_monitor:
            return False

        # Check if drift was detected recently
        monitoring_status = self.drift_monitor.get_monitoring_status()
        recent_drift = monitoring_status.get("recent_drift_events", 0)

        return recent_drift > 0

    def _check_sample_count_trigger(
        self, model_id: str, trigger: RetrainingTrigger
    ) -> bool:
        """Check sample count trigger"""
        model = self.registered_models[model_id]

        # Check if enough new samples have been processed
        last_retrain = self.last_retrain_times.get(model_id)
        if not last_retrain:
            return False

        # Estimate samples processed since last retrain
        # This is a simplified check - in practice, you'd track this more precisely
        samples_since_retrain = model.samples_seen
        threshold = trigger.sample_interval or self.config.min_samples_for_retrain

        return samples_since_retrain >= threshold

    def _check_schedule_trigger(
        self, model_id: str, trigger: RetrainingTrigger
    ) -> bool:
        """Check scheduled time trigger"""
        # Simple time-based check (in practice, would use cron-like scheduling)
        last_retrain = self.last_retrain_times.get(model_id)
        if not last_retrain:
            return True

        # Daily schedule example
        if trigger.schedule_cron == "0 2 * * *":  # Daily at 2 AM
            now = datetime.now()
            if (
                now.hour == 2
                and now.minute < 5  # Within 5 minutes of 2 AM
                and (now - last_retrain).days >= 1
            ):  # At least 1 day since last retrain
                return True

        return False

    def _schedule_retrain(
        self, model_id: str, trigger_name: str, trigger: RetrainingTrigger
    ):
        """Schedule a retraining job"""
        job_id = f"{model_id}_{trigger_name}_{self.job_counter}"
        self.job_counter += 1

        job = RetrainingJob(
            job_id=job_id,
            trigger=trigger,
            model=self.registered_models[model_id],
            data_source=self.data_sources[model_id],
            timestamp=datetime.now(),
            priority=trigger.priority,
            metadata={
                "model_id": model_id,
                "trigger_name": trigger_name,
                "trigger_type": trigger.trigger_type.value,
            },
        )

        with self.lock:
            self.pending_jobs.append(job)

        logger.info(f"Scheduled retraining job: {job_id} (trigger: {trigger_name})")

    def _process_pending_jobs(self):
        """Process pending retraining jobs"""
        if not self.pending_jobs:
            return

        # Sort by priority (higher priority first)
        with self.lock:
            sorted_jobs = sorted(
                list(self.pending_jobs), key=lambda j: j.priority, reverse=True
            )
            self.pending_jobs.clear()

        for job in sorted_jobs:
            try:
                self._execute_retrain_job(job)
            except Exception as e:
                logger.error(f"Failed to execute retraining job {job.job_id}: {e}")
                self.failed_jobs.append(
                    {"job": job, "error": str(e), "timestamp": datetime.now()}
                )

    def _execute_retrain_job(self, job: RetrainingJob):
        """Execute a retraining job"""
        start_time = time.time()
        model_id = job.metadata["model_id"]

        logger.info(f"Executing retraining job: {job.job_id}")

        try:
            # Get training data
            X, y = job.data_source()

            if len(X) < self.config.min_samples_for_retrain:
                logger.warning(f"Insufficient data for retraining: {len(X)} samples")
                return

            # Perform retraining
            old_version = job.model.model_version
            result = job.model.partial_fit(X, y)

            if result.success:
                # Update tracking
                self.last_retrain_times[model_id] = datetime.now()
                self.retrain_counts[model_id] += 1

                execution_time = time.time() - start_time

                # Record successful job
                job_result = {
                    "job": job,
                    "execution_time": execution_time,
                    "samples_processed": result.samples_processed,
                    "old_model_version": old_version,
                    "new_model_version": job.model.model_version,
                    "timestamp": datetime.now(),
                    "result": result,
                }

                self.completed_jobs.append(job_result)

                logger.info(
                    f"Retraining job {job.job_id} completed successfully "
                    f"({result.samples_processed} samples, {execution_time:.2f}s)"
                )

                # Save model if configured
                if hasattr(self.config, "save_interval_minutes"):
                    self._save_model_checkpoint(model_id, job.model)

            else:
                raise Exception(f"Retraining failed: {result.message}")

        except Exception as e:
            self.failed_jobs.append(
                {"job": job, "error": str(e), "timestamp": datetime.now()}
            )
            raise

    def _save_model_checkpoint(self, model_id: str, model: OnlineLearnerBase):
        """Save model checkpoint after retraining"""
        try:
            checkpoint_dir = Path("checkpoints") / "online_models"
            checkpoint_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_path = checkpoint_dir / f"{model_id}_{timestamp}.pkl"

            if model.save_model(str(checkpoint_path)):
                logger.info(f"Model checkpoint saved: {checkpoint_path}")

        except Exception as e:
            logger.error(f"Failed to save model checkpoint: {e}")

    def _cleanup_old_jobs(self):
        """Clean up old job records"""
        cutoff_time = datetime.now() - timedelta(days=7)

        # Clean completed jobs older than 7 days
        while self.completed_jobs and self.completed_jobs[0]["timestamp"] < cutoff_time:
            self.completed_jobs.popleft()

        # Clean failed jobs older than 7 days
        while self.failed_jobs and self.failed_jobs[0]["timestamp"] < cutoff_time:
            self.failed_jobs.popleft()

    def manual_retrain(
        self, model_id: str, data_source: Optional[Callable] = None
    ) -> bool:
        """Manually trigger retraining for a specific model"""
        if model_id not in self.registered_models:
            logger.error(f"Model {model_id} not registered")
            return False

        # Create manual trigger
        manual_trigger = RetrainingTrigger(
            trigger_type=TriggerType.MANUAL,
            enabled=True,
            priority=5,  # Highest priority
        )

        # Use provided data source or registered one
        data_source_func = data_source or self.data_sources.get(model_id)
        if not data_source_func:
            logger.error(f"No data source available for model {model_id}")
            return False

        # Create and execute job immediately
        job = RetrainingJob(
            job_id=f"{model_id}_manual_{self.job_counter}",
            trigger=manual_trigger,
            model=self.registered_models[model_id],
            data_source=data_source_func,
            timestamp=datetime.now(),
            priority=5,
            metadata={
                "model_id": model_id,
                "trigger_name": "manual",
                "trigger_type": "manual",
            },
        )

        self.job_counter += 1

        try:
            self._execute_retrain_job(job)
            logger.info(f"Manual retraining completed for model {model_id}")
            return True
        except Exception as e:
            logger.error(f"Manual retraining failed for model {model_id}: {e}")
            return False

    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        with self.lock:
            return {
                "active": self.active,
                "registered_models": list(self.registered_models.keys()),
                "enabled_triggers": [
                    name for name, trigger in self.triggers.items() if trigger.enabled
                ],
                "pending_jobs": len(self.pending_jobs),
                "completed_jobs": len(self.completed_jobs),
                "failed_jobs": len(self.failed_jobs),
                "retrain_counts": dict(self.retrain_counts),
                "last_retrain_times": {
                    k: v.isoformat() for k, v in self.last_retrain_times.items()
                },
            }

    def get_retraining_history(
        self, model_id: Optional[str] = None, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get retraining history for specified model or all models"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        history = []
        for job_record in self.completed_jobs:
            if job_record["timestamp"] > cutoff_time:
                if (
                    model_id is None
                    or job_record["job"].metadata["model_id"] == model_id
                ):
                    history.append(
                        {
                            "job_id": job_record["job"].job_id,
                            "model_id": job_record["job"].metadata["model_id"],
                            "trigger_type": job_record["job"].metadata["trigger_type"],
                            "timestamp": job_record["timestamp"].isoformat(),
                            "execution_time": job_record["execution_time"],
                            "samples_processed": job_record["samples_processed"],
                        }
                    )

        return sorted(history, key=lambda x: x["timestamp"], reverse=True)
