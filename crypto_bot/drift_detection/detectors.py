"""
Data drift detection algorithms
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import logging
from scipy import stats
import threading

from ..online_learning.base import DriftDetectorBase

logger = logging.getLogger(__name__)


class ADWINDetector(DriftDetectorBase):
    """
    ADWIN (Adaptive Windowing) drift detector
    
    Maintains a window of recent samples and detects changes in the
    mean of the data stream using statistical hypothesis testing.
    """
    
    def __init__(self, delta: float = 0.002, max_buckets: int = 5):
        super().__init__()
        self.delta = delta  # Confidence parameter
        self.max_buckets = max_buckets
        self.buckets = []
        self.total_samples = 0
        self.total_sum = 0.0
        self.variance = 0.0
        self.width = 0
        
    def update(self, sample: float) -> bool:
        """Update detector with new sample"""
        self.total_samples += 1
        self.total_sum += sample
        
        # Update variance
        if self.total_samples > 1:
            old_mean = (self.total_sum - sample) / (self.total_samples - 1)
            new_mean = self.total_sum / self.total_samples
            self.variance = ((self.total_samples - 2) * self.variance + 
                           (sample - old_mean) * (sample - new_mean)) / (self.total_samples - 1)
        
        # Add to bucket
        self._add_to_bucket(sample)
        
        # Check for drift
        drift_detected = self._detect_change()
        
        if drift_detected:
            self.drift_detected = True
            self.last_drift_time = datetime.now()
            logger.info(f"ADWIN drift detected at sample {self.total_samples}")
            self._reset_after_drift()
        
        return drift_detected
    
    def _add_to_bucket(self, sample: float):
        """Add sample to bucket structure"""
        if not self.buckets:
            self.buckets.append({'sum': sample, 'count': 1, 'variance': 0.0})
        else:
            # Add to last bucket
            last_bucket = self.buckets[-1]
            last_bucket['sum'] += sample
            last_bucket['count'] += 1
            
            # Merge buckets if necessary
            self._compress_buckets()
    
    def _compress_buckets(self):
        """Compress buckets to maintain maximum number"""
        while len(self.buckets) > self.max_buckets:
            # Merge the two smallest buckets
            min_idx = min(range(len(self.buckets)), 
                         key=lambda i: self.buckets[i]['count'])
            
            if min_idx < len(self.buckets) - 1:
                next_bucket = self.buckets[min_idx + 1]
                self.buckets[min_idx]['sum'] += next_bucket['sum']
                self.buckets[min_idx]['count'] += next_bucket['count']
                del self.buckets[min_idx + 1]
            else:
                break
    
    def _detect_change(self) -> bool:
        """Detect if there's a significant change"""
        if len(self.buckets) < 2:
            return False
        
        # Compare different window splits
        total_count = sum(bucket['count'] for bucket in self.buckets)
        total_sum = sum(bucket['sum'] for bucket in self.buckets)
        
        for cut_point in range(1, len(self.buckets)):
            # Left window
            left_count = sum(bucket['count'] for bucket in self.buckets[:cut_point])
            left_sum = sum(bucket['sum'] for bucket in self.buckets[:cut_point])
            
            # Right window
            right_count = total_count - left_count
            right_sum = total_sum - left_sum
            
            if left_count > 0 and right_count > 0:
                left_mean = left_sum / left_count
                right_mean = right_sum / right_count
                
                # Statistical test
                if self._is_change_detected(left_mean, right_mean, left_count, right_count):
                    return True
        
        return False
    
    def _is_change_detected(self, mean1: float, mean2: float, n1: int, n2: int) -> bool:
        """Check if change is statistically significant"""
        if self.variance <= 0:
            return False
        
        # Hoeffding bound
        m = 1.0 / ((1.0 / n1) + (1.0 / n2))
        epsilon = np.sqrt((2.0 * np.log(2.0 / self.delta)) / m)
        
        return abs(mean1 - mean2) > epsilon
    
    def _reset_after_drift(self):
        """Reset detector state after drift detection"""
        # Keep only the most recent bucket
        if self.buckets:
            self.buckets = [self.buckets[-1]]
        self.total_samples = self.buckets[0]['count'] if self.buckets else 0
        self.total_sum = self.buckets[0]['sum'] if self.buckets else 0.0
    
    def reset(self):
        """Reset detector completely"""
        self.buckets = []
        self.total_samples = 0
        self.total_sum = 0.0
        self.variance = 0.0
        self.drift_detected = False
        self.last_drift_time = None


class DDMDetector(DriftDetectorBase):
    """
    DDM (Drift Detection Method)
    
    Monitors the error rate and its standard deviation to detect drift.
    """
    
    def __init__(self, alpha_warning: float = 2.0, alpha_drift: float = 3.0):
        super().__init__()
        self.alpha_warning = alpha_warning
        self.alpha_drift = alpha_drift
        
        self.sample_count = 0
        self.error_count = 0
        self.error_rate = 0.0
        self.std_error = 0.0
        
        self.min_error_rate = float('inf')
        self.min_std_error = float('inf')
        
        self.warning_level = False
        self.drift_level = False
    
    def update(self, error: float) -> bool:
        """Update with new error (1 for error, 0 for correct)"""
        self.sample_count += 1
        self.error_count += error
        
        # Update error rate
        self.error_rate = self.error_count / self.sample_count
        
        # Update standard deviation
        self.std_error = np.sqrt(self.error_rate * (1 - self.error_rate) / self.sample_count)
        
        # Update minimum values
        if self.error_rate + self.std_error < self.min_error_rate + self.min_std_error:
            self.min_error_rate = self.error_rate
            self.min_std_error = self.std_error
        
        # Check for drift
        current_level = self.error_rate + self.std_error
        min_level = self.min_error_rate + self.min_std_error
        
        if current_level > min_level + self.alpha_drift * self.min_std_error:
            self.drift_detected = True
            self.last_drift_time = datetime.now()
            logger.info(f"DDM drift detected at sample {self.sample_count}")
            self._reset_after_drift()
            return True
        elif current_level > min_level + self.alpha_warning * self.min_std_error:
            self.warning_level = True
        else:
            self.warning_level = False
        
        return False
    
    def _reset_after_drift(self):
        """Reset after drift detection"""
        self.sample_count = 0
        self.error_count = 0
        self.error_rate = 0.0
        self.std_error = 0.0
        self.min_error_rate = float('inf')
        self.min_std_error = float('inf')
        self.warning_level = False
    
    def reset(self):
        """Reset detector completely"""
        self._reset_after_drift()
        self.drift_detected = False
        self.last_drift_time = None


class PageHinkleyDetector(DriftDetectorBase):
    """
    Page-Hinkley test for drift detection
    
    Monitors the cumulative sum of deviations from the mean.
    """
    
    def __init__(self, threshold: float = 50.0, alpha: float = 0.9999):
        super().__init__()
        self.threshold = threshold
        self.alpha = alpha
        
        self.sum_x = 0.0
        self.sample_count = 0
        self.x_mean = 0.0
        self.sum_ph = 0.0
        self.min_sum_ph = 0.0
    
    def update(self, sample: float) -> bool:
        """Update with new sample"""
        self.sample_count += 1
        self.sum_x += sample
        
        # Update mean
        old_mean = self.x_mean
        self.x_mean = self.sum_x / self.sample_count
        
        # Update Page-Hinkley sum
        if self.sample_count > 1:
            self.sum_ph += (sample - old_mean - self.alpha)
        
        # Update minimum
        if self.sum_ph < self.min_sum_ph:
            self.min_sum_ph = self.sum_ph
        
        # Check for drift
        ph_test = self.sum_ph - self.min_sum_ph
        
        if ph_test > self.threshold:
            self.drift_detected = True
            self.last_drift_time = datetime.now()
            logger.info(f"Page-Hinkley drift detected at sample {self.sample_count}")
            self._reset_after_drift()
            return True
        
        return False
    
    def _reset_after_drift(self):
        """Reset after drift detection"""
        self.sum_ph = 0.0
        self.min_sum_ph = 0.0
    
    def reset(self):
        """Reset detector completely"""
        self.sum_x = 0.0
        self.sample_count = 0
        self.x_mean = 0.0
        self._reset_after_drift()
        self.drift_detected = False
        self.last_drift_time = None


class StatisticalDriftDetector(DriftDetectorBase):
    """
    Statistical drift detector using Kolmogorov-Smirnov test
    """
    
    def __init__(self, window_size: int = 500, threshold: float = 0.01):
        super().__init__(window_size, threshold)
        self.reference_window = deque(maxlen=window_size)
        self.current_window = deque(maxlen=window_size)
        self.is_reference_ready = False
        self.lock = threading.Lock()
    
    def update(self, sample: np.ndarray) -> bool:
        """Update with new sample (can be multi-dimensional)"""
        with self.lock:
            if isinstance(sample, (list, np.ndarray)):
                sample = np.array(sample).flatten()
            else:
                sample = np.array([sample])
            
            if not self.is_reference_ready:
                # Fill reference window first
                self.reference_window.append(sample)
                if len(self.reference_window) == self.window_size:
                    self.is_reference_ready = True
                    logger.info("Reference window ready for drift detection")
                return False
            else:
                # Add to current window and check for drift
                self.current_window.append(sample)
                
                if len(self.current_window) == self.window_size:
                    drift_detected = self._detect_drift()
                    
                    if drift_detected:
                        self.drift_detected = True
                        self.last_drift_time = datetime.now()
                        logger.info("Statistical drift detected")
                        self._update_reference()
                        return True
                    
                    # Slide window
                    if len(self.current_window) > self.window_size // 2:
                        # Remove oldest half
                        for _ in range(self.window_size // 2):
                            if self.current_window:
                                self.current_window.popleft()
                
                return False
    
    def _detect_drift(self) -> bool:
        """Detect drift using statistical tests"""
        if len(self.current_window) < self.window_size // 2:
            return False
        
        # Convert to arrays
        reference_data = np.array(list(self.reference_window))
        current_data = np.array(list(self.current_window))
        
        # Handle multi-dimensional data
        if len(reference_data.shape) > 1:
            # Apply test to each dimension
            p_values = []
            for dim in range(reference_data.shape[1]):
                ref_dim = reference_data[:, dim]
                cur_dim = current_data[:, dim]
                
                # Kolmogorov-Smirnov test
                statistic, p_value = stats.ks_2samp(ref_dim, cur_dim)
                p_values.append(p_value)
            
            # Use minimum p-value (most conservative)
            min_p_value = min(p_values)
        else:
            # 1D data
            statistic, min_p_value = stats.ks_2samp(reference_data.flatten(), 
                                                   current_data.flatten())
        
        return min_p_value < self.threshold
    
    def _update_reference(self):
        """Update reference window after drift detection"""
        # Move current window to reference
        self.reference_window = self.current_window.copy()
        self.current_window.clear()
    
    def reset(self):
        """Reset detector completely"""
        with self.lock:
            self.reference_window.clear()
            self.current_window.clear()
            self.is_reference_ready = False
            self.drift_detected = False
            self.last_drift_time = None


class EDDMDetector(DDMDetector):
    """
    EDDM (Early Drift Detection Method)
    
    Extension of DDM that considers the distance between classification errors.
    """
    
    def __init__(self, alpha_warning: float = 0.95, alpha_drift: float = 0.9):
        super().__init__(alpha_warning, alpha_drift)
        self.error_positions = []
        self.mean_distance = 0.0
        self.std_distance = 0.0
        self.min_mean_distance = float('inf')
        self.min_std_distance = float('inf')
    
    def update(self, error: float) -> bool:
        """Update with new error"""
        self.sample_count += 1
        
        if error == 1:  # Error occurred
            self.error_positions.append(self.sample_count)
            
            # Calculate distances between errors
            if len(self.error_positions) >= 2:
                distances = []
                for i in range(1, len(self.error_positions)):
                    distances.append(self.error_positions[i] - self.error_positions[i-1])
                
                if distances:
                    self.mean_distance = np.mean(distances)
                    self.std_distance = np.std(distances) if len(distances) > 1 else 0
                    
                    # Update minimum values
                    if (self.mean_distance + self.std_distance < 
                        self.min_mean_distance + self.min_std_distance):
                        self.min_mean_distance = self.mean_distance
                        self.min_std_distance = self.std_distance
                    
                    # Check for drift
                    current_level = self.mean_distance + self.std_distance
                    min_level = self.min_mean_distance + self.min_std_distance
                    
                    if min_level > 0 and current_level / min_level < self.alpha_drift:
                        self.drift_detected = True
                        self.last_drift_time = datetime.now()
                        logger.info(f"EDDM drift detected at sample {self.sample_count}")
                        self._reset_after_drift()
                        return True
                    elif min_level > 0 and current_level / min_level < self.alpha_warning:
                        self.warning_level = True
                    else:
                        self.warning_level = False
        
        return False
    
    def _reset_after_drift(self):
        """Reset after drift detection"""
        super()._reset_after_drift()
        self.error_positions = []
        self.mean_distance = 0.0
        self.std_distance = 0.0
        self.min_mean_distance = float('inf')
        self.min_std_distance = float('inf')
    
    def reset(self):
        """Reset detector completely"""
        super().reset()
        self._reset_after_drift()