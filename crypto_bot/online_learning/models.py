"""
Incremental learning models for online training
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import pickle
import logging
from pathlib import Path
import threading
import time

try:
    from river import linear_model, tree, ensemble, metrics
    from river import preprocessing as river_preprocessing
    RIVER_AVAILABLE = True
except ImportError:
    RIVER_AVAILABLE = False
    logging.warning("River not available. Install with: pip install river")

try:
    from sklearn.linear_model import SGDClassifier, SGDRegressor
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from .base import (
    OnlineLearnerBase, 
    OnlineLearningConfig,
    PredictionResult,
    ModelUpdateResult
)

logger = logging.getLogger(__name__)


class IncrementalMLModel(OnlineLearnerBase):
    """
    Wrapper for incremental machine learning models
    Supports both River and scikit-learn incremental learners
    """
    
    def __init__(self, 
                 config: OnlineLearningConfig,
                 model_type: str = "river_linear",
                 model_params: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        self.model_type = model_type
        self.model_params = model_params or {}
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.feature_buffer = []
        self.target_buffer = []
        self.lock = threading.Lock()
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the underlying ML model"""
        if self.model_type.startswith("river_") and RIVER_AVAILABLE:
            self._initialize_river_model()
        elif self.model_type.startswith("sklearn_") and SKLEARN_AVAILABLE:
            self._initialize_sklearn_model()
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def _initialize_river_model(self):
        """Initialize River-based model"""
        model_name = self.model_type.replace("river_", "")
        
        if model_name == "linear":
            self.model = linear_model.LogisticRegression(**self.model_params)
        elif model_name == "linear_reg":
            self.model = linear_model.LinearRegression(**self.model_params)
        elif model_name == "tree":
            self.model = tree.HoeffdingTreeClassifier(**self.model_params)
        elif model_name == "adaptive_tree":
            self.model = tree.HoeffdingAdaptiveTreeClassifier(**self.model_params)
        elif model_name == "bagging":
            base_model = tree.HoeffdingTreeClassifier()
            self.model = ensemble.BaggingClassifier(
                model=base_model,
                n_models=self.model_params.get("n_estimators", 10)
            )
        else:
            raise ValueError(f"Unknown River model: {model_name}")
        
        # River models don't need separate scaling
        self.scaler = None
    
    def _initialize_sklearn_model(self):
        """Initialize scikit-learn incremental model"""
        model_name = self.model_type.replace("sklearn_", "")
        
        if model_name == "sgd_classifier":
            self.model = SGDClassifier(**self.model_params)
        elif model_name == "sgd_regressor":
            self.model = SGDRegressor(**self.model_params)
        else:
            raise ValueError(f"Unknown sklearn incremental model: {model_name}")
        
        # Initialize scaler for sklearn models
        self.scaler = StandardScaler()
    
    def partial_fit(self, X: np.ndarray, y: np.ndarray) -> ModelUpdateResult:
        """Update model with new data samples"""
        start_time = time.time()
        
        try:
            with self.lock:
                if isinstance(X, pd.DataFrame):
                    self.feature_names = list(X.columns)
                    X = X.values
                
                if len(X.shape) == 1:
                    X = X.reshape(1, -1)
                
                if self.model_type.startswith("river_"):
                    result = self._partial_fit_river(X, y)
                else:
                    result = self._partial_fit_sklearn(X, y)
                
                self.samples_seen += len(X)
                self.last_update = datetime.now()
                self.is_fitted = True
                
                # Update performance tracking
                if hasattr(self, 'performance_monitor'):
                    y_pred = self.predict(X).prediction
                    self.performance_monitor.update(y, y_pred)
                
                update_time = (time.time() - start_time) * 1000
                result.update_time_ms = update_time
                result.model_version = self.model_version
                
                return result
                
        except Exception as e:
            logger.error(f"Error in partial_fit: {e}")
            return ModelUpdateResult(
                success=False,
                samples_processed=0,
                performance_change=0.0,
                drift_detected=False,
                model_version=self.model_version,
                update_time_ms=0.0,
                memory_usage_mb=0.0,
                message=f"Update failed: {str(e)}"
            )
    
    def _partial_fit_river(self, X: np.ndarray, y: np.ndarray) -> ModelUpdateResult:
        """Update River model"""
        samples_processed = 0
        
        for i in range(len(X)):
            # Convert to dictionary format for River
            sample = {f"feature_{j}": X[i, j] for j in range(X.shape[1])}
            target = y[i] if hasattr(y[i], 'item') else y[i]
            
            # Update model
            self.model.learn_one(sample, target)
            samples_processed += 1
        
        return ModelUpdateResult(
            success=True,
            samples_processed=samples_processed,
            performance_change=0.0,  # Would need separate calculation
            drift_detected=False,
            model_version=self.model_version,
            update_time_ms=0.0,
            memory_usage_mb=0.0,
            message=f"River model updated with {samples_processed} samples"
        )
    
    def _partial_fit_sklearn(self, X: np.ndarray, y: np.ndarray) -> ModelUpdateResult:
        """Update scikit-learn model"""
        # Scale features if scaler is available
        if self.scaler is not None:
            if not hasattr(self.scaler, 'n_features_in_'):
                # First time - fit scaler
                X_scaled = self.scaler.fit_transform(X)
            else:
                # Update scaler incrementally (approximate)
                X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X
        
        # Update model
        if hasattr(self.model, 'partial_fit'):
            if not self.is_fitted:
                # First fit - need to specify classes for classification
                if hasattr(self.model, 'classes_'):
                    unique_classes = np.unique(y)
                    self.model.partial_fit(X_scaled, y, classes=unique_classes)
                else:
                    self.model.partial_fit(X_scaled, y)
            else:
                self.model.partial_fit(X_scaled, y)
        else:
            # For models without partial_fit, accumulate data and retrain
            self.feature_buffer.extend(X_scaled)
            self.target_buffer.extend(y)
            
            if len(self.feature_buffer) >= self.config.batch_size:
                X_batch = np.array(self.feature_buffer)
                y_batch = np.array(self.target_buffer)
                self.model.fit(X_batch, y_batch)
                
                # Clear buffer
                self.feature_buffer = []
                self.target_buffer = []
        
        return ModelUpdateResult(
            success=True,
            samples_processed=len(X),
            performance_change=0.0,
            drift_detected=False,
            model_version=self.model_version,
            update_time_ms=0.0,
            memory_usage_mb=0.0,
            message=f"Sklearn model updated with {len(X)} samples"
        )
    
    def predict(self, X: np.ndarray) -> PredictionResult:
        """Make prediction with confidence estimate"""
        try:
            with self.lock:
                if not self.is_fitted:
                    raise ValueError("Model not fitted yet")
                
                if isinstance(X, pd.DataFrame):
                    X = X.values
                
                if len(X.shape) == 1:
                    X = X.reshape(1, -1)
                
                if self.model_type.startswith("river_"):
                    prediction, confidence = self._predict_river(X)
                else:
                    prediction, confidence = self._predict_sklearn(X)
                
                return PredictionResult(
                    prediction=prediction,
                    confidence=confidence,
                    model_version=self.model_version,
                    timestamp=datetime.now(),
                    features_used=self.feature_names,
                    metadata={"samples_seen": self.samples_seen}
                )
                
        except Exception as e:
            logger.error(f"Error in predict: {e}")
            return PredictionResult(
                prediction=0.0,
                confidence=0.0,
                model_version=self.model_version,
                timestamp=datetime.now(),
                features_used=[],
                metadata={"error": str(e)}
            )
    
    def _predict_river(self, X: np.ndarray) -> tuple:
        """Make prediction using River model"""
        predictions = []
        confidences = []
        
        for i in range(len(X)):
            sample = {f"feature_{j}": X[i, j] for j in range(X.shape[1])}
            
            if hasattr(self.model, 'predict_proba_one'):
                proba = self.model.predict_proba_one(sample)
                if proba:
                    prediction = max(proba, key=proba.get)
                    confidence = max(proba.values())
                else:
                    prediction = 0
                    confidence = 0.5
            else:
                prediction = self.model.predict_one(sample)
                confidence = 0.8  # Default confidence for deterministic models
            
            predictions.append(prediction)
            confidences.append(confidence)
        
        return np.array(predictions), np.mean(confidences)
    
    def _predict_sklearn(self, X: np.ndarray) -> tuple:
        """Make prediction using scikit-learn model"""
        # Scale features if scaler is available
        if self.scaler is not None:
            X_scaled = self.scaler.transform(X)
        else:
            X_scaled = X
        
        prediction = self.model.predict(X_scaled)
        
        # Get confidence estimate
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(X_scaled)
            confidence = np.max(proba, axis=1).mean()
        elif hasattr(self.model, 'decision_function'):
            decision = self.model.decision_function(X_scaled)
            confidence = np.abs(decision).mean()
        else:
            confidence = 0.8  # Default confidence
        
        return prediction, confidence
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities"""
        if not self.is_fitted:
            raise ValueError("Model not fitted yet")
        
        if isinstance(X, pd.DataFrame):
            X = X.values
        
        if len(X.shape) == 1:
            X = X.reshape(1, -1)
        
        if self.model_type.startswith("river_"):
            probabilities = []
            for i in range(len(X)):
                sample = {f"feature_{j}": X[i, j] for j in range(X.shape[1])}
                if hasattr(self.model, 'predict_proba_one'):
                    proba = self.model.predict_proba_one(sample)
                    # Convert to array format
                    prob_array = [proba.get(0, 0.0), proba.get(1, 0.0)]
                    probabilities.append(prob_array)
                else:
                    # Binary classification default
                    probabilities.append([0.5, 0.5])
            return np.array(probabilities)
        else:
            if self.scaler is not None:
                X = self.scaler.transform(X)
            
            if hasattr(self.model, 'predict_proba'):
                return self.model.predict_proba(X)
            else:
                # For regressors or models without proba
                predictions = self.model.predict(X)
                # Convert to binary probabilities
                proba = np.column_stack([1 - predictions, predictions])
                return proba
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get current feature importance scores"""
        importance = {}
        
        if self.model_type.startswith("sklearn_"):
            if hasattr(self.model, 'coef_'):
                # Linear models
                coef = self.model.coef_
                if len(coef.shape) > 1:
                    coef = coef[0]  # Take first class for multi-class
                
                for i, name in enumerate(self.feature_names):
                    importance[name] = abs(coef[i]) if i < len(coef) else 0.0
            elif hasattr(self.model, 'feature_importances_'):
                # Tree-based models
                importances = self.model.feature_importances_
                for i, name in enumerate(self.feature_names):
                    importance[name] = importances[i] if i < len(importances) else 0.0
        
        # River models don't typically expose feature importance directly
        # Could implement custom importance calculation here
        
        return importance
    
    def save_model(self, path: str) -> bool:
        """Save current model state"""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'model_type': self.model_type,
                'model_params': self.model_params,
                'model_version': self.model_version,
                'samples_seen': self.samples_seen,
                'feature_names': self.feature_names,
                'is_fitted': self.is_fitted,
                'config': self.config
            }
            
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            return False
    
    def load_model(self, path: str) -> bool:
        """Load model from saved state"""
        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data.get('scaler')
            self.model_type = model_data['model_type']
            self.model_params = model_data['model_params']
            self.model_version = model_data['model_version']
            self.samples_seen = model_data['samples_seen']
            self.feature_names = model_data['feature_names']
            self.is_fitted = model_data['is_fitted']
            self.config = model_data.get('config', self.config)
            
            logger.info(f"Model loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False


class OnlineClassifier(IncrementalMLModel):
    """Specialized online classifier"""
    
    def __init__(self, config: OnlineLearningConfig, **kwargs):
        # Default to River logistic regression for classification
        kwargs.setdefault('model_type', 'river_linear')
        super().__init__(config, **kwargs)


class OnlineRegressor(IncrementalMLModel):
    """Specialized online regressor"""
    
    def __init__(self, config: OnlineLearningConfig, **kwargs):
        # Default to River linear regression
        kwargs.setdefault('model_type', 'river_linear_reg')
        super().__init__(config, **kwargs)