#!/usr/bin/env python3
"""
Bayesian Inference Strategy for Crypto Trading Bot
Implements Bayesian updating for improved prediction accuracy
"""
import logging
from typing import Dict

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class BayesianMarketPredictor:
    """
    Bayesian predictor that updates beliefs about market direction
    based on new evidence and maintains uncertainty estimates
    """

    def __init__(
        self,
        alpha_prior: float = 1.0,
        beta_prior: float = 1.0,
        decay_factor: float = 0.95,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize Bayesian predictor
        Args:
            alpha_prior: Prior parameter for success (bullish outcomes)
            beta_prior: Prior parameter for failure (bearish outcomes)
            decay_factor: How much to weight recent vs historical data
            confidence_threshold: Minimum confidence for trading signals
        """
        self.alpha = alpha_prior
        self.beta = beta_prior
        self.decay_factor = decay_factor
        self.confidence_threshold = confidence_threshold
        # Market regime tracking
        self.current_regime = "normal"
        self.regime_history = []

        # Evidence tracking
        self.evidence_history = []
        self.prediction_history = []

        logger.info(
            f"BayesianMarketPredictor initialized with α={alpha_prior}, β={beta_prior}"
        )

    def update_belief(
        self,
        market_outcome: bool,
        prediction_confidence: float,
        feature_evidence: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Update Bayesian belief based on market outcome
        Args:
            market_outcome: True if market moved as predicted
            prediction_confidence: Confidence level of the prediction
            feature_evidence: Supporting evidence from technical indicators

        Returns:
            Updated belief statistics
        """
        # Apply decay to previous beliefs (recent data more important)
        self.alpha *= self.decay_factor
        self.beta *= self.decay_factor
        # Update based on outcome
        if market_outcome:
            # Successful prediction - increase alpha
            evidence_weight = prediction_confidence * self._calculate_evidence_strength(
                feature_evidence
            )
            self.alpha += evidence_weight
        else:
            # Failed prediction - increase beta
            evidence_weight = prediction_confidence * self._calculate_evidence_strength(
                feature_evidence
            )
            self.beta += evidence_weight

        # Calculate updated statistics
        belief_stats = self._calculate_belief_stats()

        # Store evidence
        self.evidence_history.append(
            {
                "timestamp": pd.Timestamp.now(),
                "outcome": market_outcome,
                "confidence": prediction_confidence,
                "evidence": feature_evidence.copy(),
                "alpha": self.alpha,
                "beta": self.beta,
            }
        )

        # Limit history size
        if len(self.evidence_history) > 1000:
            self.evidence_history = self.evidence_history[-500:]

        logger.debug(
            f"Belief updated: α={self.alpha:.3f}, β={self.beta:.3f}, "
            f"mean={belief_stats['mean']:.3f}, std={belief_stats['std']:.3f}"
        )

        return belief_stats

    def predict_with_uncertainty(
        self, ml_prediction: float, features: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Generate prediction with Bayesian uncertainty quantification
        Args:
            ml_prediction: Base ML model prediction (0-1)
            features: Current market features

        Returns:
            Bayesian prediction with uncertainty metrics
        """
        # Current belief about market
        belief_stats = self._calculate_belief_stats()
        # Combine ML prediction with Bayesian prior
        evidence_strength = self._calculate_evidence_strength(features)

        # Bayesian updating formula
        likelihood_weight = evidence_strength
        prior_weight = 1.0 - evidence_strength

        bayesian_prediction = (
            likelihood_weight * ml_prediction + prior_weight * belief_stats["mean"]
        )

        # Calculate prediction uncertainty
        ml_uncertainty = abs(ml_prediction - 0.5)  # Distance from neutral
        belief_uncertainty = belief_stats["std"]

        # Combined uncertainty (higher is more certain)
        combined_confidence = (ml_uncertainty + (1 - belief_uncertainty)) / 2

        # Market regime adjustment
        regime_factor = self._get_regime_adjustment()
        adjusted_prediction = bayesian_prediction * regime_factor

        prediction_result = {
            "prediction": adjusted_prediction,
            "confidence": combined_confidence,
            "ml_component": ml_prediction,
            "bayesian_component": belief_stats["mean"],
            "uncertainty": belief_uncertainty,
            "evidence_strength": evidence_strength,
            "regime": self.current_regime,
            "regime_factor": regime_factor,
            "credible_interval_95": belief_stats["ci_95"],
            "trading_signal": self._generate_trading_signal(
                adjusted_prediction, combined_confidence
            ),
        }

        self.prediction_history.append(prediction_result)

        return prediction_result

    def _calculate_evidence_strength(self, features: Dict[str, float]) -> float:
        """Calculate strength of current evidence"""
        # Technical indicator strength
        technical_signals = 0
        signal_count = 0

        # RSI evidence
        if "rsi_14" in features:
            rsi = features["rsi_14"]
            if rsi < 30 or rsi > 70:  # Strong oversold/overbought
                technical_signals += 0.8
            elif rsi < 40 or rsi > 60:  # Moderate signal
                technical_signals += 0.4
            signal_count += 1

        # MACD evidence
        if "macd" in features and "macd_signal" in features:
            macd_strength = abs(features["macd"] - features.get("macd_signal", 0))
            technical_signals += min(macd_strength / 1000, 0.8)  # Normalize
            signal_count += 1

        # Volume evidence
        if "volume_ratio" in features:
            vol_ratio = features["volume_ratio"]
            if vol_ratio > 2.0:  # High volume confirmation
                technical_signals += 0.6
            elif vol_ratio > 1.5:
                technical_signals += 0.3
            signal_count += 1

        # VIX/market sentiment evidence
        if "vix" in features:
            vix_level = features["vix"]
            if vix_level > 30:  # High fear
                technical_signals += 0.7
            elif vix_level < 15:  # Low fear
                technical_signals += 0.5
            signal_count += 1

        # Average evidence strength
        if signal_count > 0:
            evidence_strength = technical_signals / signal_count
        else:
            evidence_strength = 0.5  # Neutral if no evidence

        return min(evidence_strength, 1.0)

    def _calculate_belief_stats(self) -> Dict[str, float]:
        """Calculate current belief statistics"""
        # Beta distribution parameters
        mean = self.alpha / (self.alpha + self.beta)
        variance = (self.alpha * self.beta) / (
            (self.alpha + self.beta) ** 2 * (self.alpha + self.beta + 1)
        )
        std = np.sqrt(variance)

        # Credible intervals
        beta_dist = stats.beta(self.alpha, self.beta)
        ci_95 = beta_dist.interval(0.95)
        ci_80 = beta_dist.interval(0.80)

        return {
            "mean": mean,
            "std": std,
            "variance": variance,
            "ci_95": ci_95,
            "ci_80": ci_80,
            "alpha": self.alpha,
            "beta": self.beta,
        }

    def _get_regime_adjustment(self) -> float:
        """Adjust predictions based on market regime"""
        # Market regime detection based on recent evidence
        if len(self.evidence_history) < 10:
            return 1.0

        recent_evidence = self.evidence_history[-10:]
        success_rate = sum(1 for e in recent_evidence if e["outcome"]) / len(
            recent_evidence
        )

        if success_rate > 0.7:
            self.current_regime = "trending"
            return 1.1  # Boost signals in trending market
        elif success_rate < 0.3:
            self.current_regime = "choppy"
            return 0.8  # Reduce signals in choppy market
        else:
            self.current_regime = "normal"
            return 1.0

    def _generate_trading_signal(self, prediction: float, confidence: float) -> str:
        """Generate trading signal based on Bayesian prediction"""
        # Require both strong prediction and high confidence
        if prediction > 0.6 and confidence > self.confidence_threshold:
            return "STRONG_BUY"
        elif prediction > 0.55 and confidence > self.confidence_threshold * 0.8:
            return "BUY"
        elif prediction < 0.4 and confidence > self.confidence_threshold:
            return "STRONG_SELL"
        elif prediction < 0.45 and confidence > self.confidence_threshold * 0.8:
            return "SELL"
        else:
            return "HOLD"

    def get_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics of Bayesian predictions"""
        if len(self.evidence_history) < 5:
            return {}

        # Calculate accuracy over different time periods
        recent_evidence = (
            self.evidence_history[-20:]
            if len(self.evidence_history) >= 20
            else self.evidence_history
        )

        accuracy = sum(1 for e in recent_evidence if e["outcome"]) / len(
            recent_evidence
        )
        avg_confidence = np.mean([e["confidence"] for e in recent_evidence])

        # Calibration: how well confidence matches actual accuracy
        high_confidence_predictions = [
            e for e in recent_evidence if e["confidence"] > 0.7
        ]
        calibration = 0.0
        if high_confidence_predictions:
            calibration = sum(
                1 for e in high_confidence_predictions if e["outcome"]
            ) / len(high_confidence_predictions)

        return {
            "accuracy": accuracy,
            "avg_confidence": avg_confidence,
            "calibration": calibration,
            "total_predictions": len(self.evidence_history),
            "current_alpha": self.alpha,
            "current_beta": self.beta,
            "current_regime": self.current_regime,
        }


class BayesianEnhancedStrategy:
    """
    Enhanced trading strategy that integrates Bayesian inference
    with existing ML predictions
    """

    def __init__(self, base_strategy, bayesian_predictor: BayesianMarketPredictor):
        self.base_strategy = base_strategy
        self.bayesian_predictor = bayesian_predictor
        self.signal_history = []

    def generate_signal(
        self, features: Dict[str, float], market_data: pd.DataFrame
    ) -> Dict[str, any]:
        """
        Generate enhanced trading signal using Bayesian inference
        """
        # Get base ML prediction
        base_prediction = self.base_strategy.generate_signal(features, market_data)
        ml_probability = base_prediction.get("probability", 0.5)

        # Apply Bayesian enhancement
        bayesian_result = self.bayesian_predictor.predict_with_uncertainty(
            ml_prediction=ml_probability, features=features
        )

        # Enhanced signal decision
        enhanced_signal = {
            "action": bayesian_result["trading_signal"],
            "confidence": bayesian_result["confidence"],
            "probability": bayesian_result["prediction"],
            "base_probability": ml_probability,
            "bayesian_adjustment": bayesian_result["prediction"] - ml_probability,
            "uncertainty": bayesian_result["uncertainty"],
            "evidence_strength": bayesian_result["evidence_strength"],
            "market_regime": bayesian_result["regime"],
            "credible_interval": bayesian_result["credible_interval_95"],
            "timestamp": pd.Timestamp.now(),
        }

        self.signal_history.append(enhanced_signal)

        return enhanced_signal

    def update_performance(
        self, predicted_direction: str, actual_outcome: bool, confidence: float
    ):
        """Update Bayesian beliefs based on trading outcome"""
        # Convert direction to boolean for easier processing
        # predicted_up = predicted_direction in ["BUY", "STRONG_BUY"]

        # Get feature evidence from last signal
        last_features = {}
        if self.signal_history:
            last_signal = self.signal_history[-1]
            last_features = {
                "confidence": last_signal["confidence"],
                "evidence_strength": last_signal["evidence_strength"],
            }

        # Update beliefs
        self.bayesian_predictor.update_belief(
            market_outcome=actual_outcome,
            prediction_confidence=confidence,
            feature_evidence=last_features,
        )
