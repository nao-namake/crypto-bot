# =============================================================================
# ファイル名: crypto_bot/ml/timeframe_ensemble.py
# 説明:
# Phase C1: タイムフレーム内アンサンブル学習専用モジュール
# 単一タイムフレーム内での複数モデルアンサンブル処理最適化
# EnsembleMLStrategy機能分離・Phase B基盤統合・パフォーマンス向上
# =============================================================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.ml.ensemble import TradingEnsembleClassifier, create_trading_ensemble
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.utils.ensemble_confidence import EnsembleConfidenceCalculator

logger = logging.getLogger(__name__)


class TimeframeEnsembleProcessor:
    """
    単一タイムフレーム内アンサンブル学習処理システム

    機能:
    - 単一タイムフレーム用の複数モデルアンサンブル
    - Phase B基盤（BatchFeatureCalculator等）統合
    - 統一信頼度計算システム活用
    - メモリ効率・パフォーマンス最適化
    - 統一インターフェース提供
    """

    def __init__(
        self,
        timeframe: str,
        config: Dict[str, Any],
        feature_engineer: Optional[FeatureEngineer] = None,
    ):
        """
        タイムフレーム内アンサンブル処理初期化

        Parameters:
        -----------
        timeframe : str
            処理対象タイムフレーム（例: "15m", "1h", "4h"）
        config : Dict[str, Any]
            設定辞書（アンサンブル・特徴量設定含む）
        feature_engineer : FeatureEngineer, optional
            特徴量エンジニアリングインスタンス
        """
        self.timeframe = timeframe
        self.config = config

        # アンサンブル設定取得
        ensemble_config = self.config.get("ml", {}).get("ensemble", {})
        self.ensemble_enabled = ensemble_config.get("enabled", True)
        self.ensemble_method = ensemble_config.get("method", "trading_stacking")
        self.base_confidence_threshold = ensemble_config.get(
            "confidence_threshold", 0.65
        )

        # 特徴量エンジニアリング初期化
        if feature_engineer is not None:
            self.feature_engineer = feature_engineer
        else:
            self.feature_engineer = FeatureEngineer(self.config)

        # その他コンポーネント初期化
        self.scaler = StandardScaler()
        self.indicator_calc = IndicatorCalculator()

        # 信頼度計算システム初期化（新Phase C1機能）
        self.confidence_calculator = EnsembleConfidenceCalculator(self.config)

        # アンサンブルモデル初期化
        self.ensemble_model: Optional[TradingEnsembleClassifier] = None
        self.is_fitted = False

        if self.ensemble_enabled:
            try:
                self.ensemble_model = create_trading_ensemble(self.config)
                logger.info(
                    f"✅ {timeframe} ensemble model created: {self.ensemble_method}"
                )
            except Exception as e:
                logger.error(f"❌ Failed to create {timeframe} ensemble model: {e}")
                self.ensemble_enabled = False

        # パフォーマンス統計
        self.processing_stats = {
            "predictions_made": 0,
            "feature_engineering_calls": 0,
            "confidence_calculations": 0,
            "ensemble_predictions": 0,
            "fallback_predictions": 0,
        }

        # 予測履歴（最新パフォーマンス追跡用）
        self.prediction_history: List[Dict[str, Any]] = []
        self.max_history_size = 50

        logger.info(f"🔄 TimeframeEnsembleProcessor initialized for {timeframe}")

    def fit(self, price_df: pd.DataFrame, y: pd.Series) -> TimeframeEnsembleProcessor:
        """
        タイムフレーム特化アンサンブルモデル学習

        Parameters:
        -----------
        price_df : pd.DataFrame
            価格データ
        y : pd.Series
            ターゲットデータ

        Returns:
        --------
        TimeframeEnsembleProcessor
            学習済みプロセッサー
        """
        if not self.ensemble_enabled or self.ensemble_model is None:
            logger.warning(
                f"Ensemble not enabled for {self.timeframe}, skipping training"
            )
            return self

        logger.info(f"🎯 Training {self.timeframe} timeframe ensemble model")

        try:
            # 特徴量エンジニアリング
            feat_df = self.feature_engineer.transform(price_df)
            self.processing_stats["feature_engineering_calls"] += 1

            if feat_df.empty:
                logger.error(f"Empty features for {self.timeframe} training")
                return self

            # スケーリング
            scaled_features = self.scaler.fit_transform(feat_df.values)
            X_scaled = pd.DataFrame(
                scaled_features, index=feat_df.index, columns=feat_df.columns
            )

            # アンサンブルモデル学習
            self.ensemble_model.fit(X_scaled, y)
            self.is_fitted = True

            # 学習結果情報取得
            ensemble_info = self.ensemble_model.get_trading_ensemble_info()
            logger.info(f"✅ {self.timeframe} ensemble training completed")
            logger.info(f"   Models: {ensemble_info.get('num_base_models', 'N/A')}")
            logger.info(f"   Method: {ensemble_info.get('ensemble_method', 'N/A')}")

        except Exception as e:
            logger.error(f"❌ {self.timeframe} ensemble training failed: {e}")
            self.ensemble_enabled = False
            self.is_fitted = False

        return self

    def predict_with_confidence(
        self, price_df: pd.DataFrame, market_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]:
        """
        信頼度付きアンサンブル予測（Phase C1統合機能）

        Parameters:
        -----------
        price_df : pd.DataFrame
            価格データ
        market_context : Dict[str, Any], optional
            市場環境コンテキスト

        Returns:
        --------
        Tuple[np.ndarray, np.ndarray, np.ndarray, Dict[str, Any]]
            (予測クラス, 予測確率, 信頼度スコア, 予測情報)
        """
        self.processing_stats["predictions_made"] += 1

        # フォールバック処理（改善版：簡易テクニカル分析）
        def create_fallback_result():
            self.processing_stats["fallback_predictions"] += 1
            logger.info(
                f"🔄 [{self.timeframe}] Using fallback prediction with simple technical analysis"
            )

            # 簡易テクニカル分析を試みる
            try:
                if len(price_df) >= 20:
                    close_prices = price_df["close"].values
                    sma20 = np.mean(close_prices[-20:])
                    current_price = close_prices[-1]

                    # 価格とSMA20の関係から簡易的な予測
                    if current_price > sma20 * 1.01:  # 1%以上上
                        prediction = 1
                        probability = 0.6
                        confidence = 0.55
                        logger.info(
                            f"📈 [{self.timeframe}] Fallback: Bullish signal (price > SMA20)"
                        )
                    elif current_price < sma20 * 0.99:  # 1%以上下
                        prediction = 0
                        probability = 0.4
                        confidence = 0.55
                        logger.info(
                            f"📉 [{self.timeframe}] Fallback: Bearish signal (price < SMA20)"
                        )
                    else:
                        prediction = 0
                        probability = 0.5
                        confidence = 0.4
                        logger.info(f"➡️ [{self.timeframe}] Fallback: Neutral signal")
                else:
                    # データ不足の場合
                    prediction = 0
                    probability = 0.5
                    confidence = 0.3
                    logger.warning(
                        f"⚠️ [{self.timeframe}] Fallback: Insufficient data for technical analysis"
                    )
            except Exception as e:
                logger.error(
                    f"❌ [{self.timeframe}] Fallback technical analysis failed: {e}"
                )
                prediction = 0
                probability = 0.5
                confidence = 0.3

            return (
                np.array([prediction]),
                np.array([[1 - probability, probability]]),
                np.array([confidence]),
                {
                    "timeframe": self.timeframe,
                    "method": "fallback_technical",
                    "ensemble_enabled": False,
                    "dynamic_threshold": 0.5,
                    "risk_level": "medium",
                    "fallback_reason": (
                        "model_not_fitted"
                        if not self.is_fitted
                        else "ensemble_disabled"
                    ),
                },
            )

        if (
            not self.ensemble_enabled
            or not self.is_fitted
            or self.ensemble_model is None
        ):
            logger.warning(f"Ensemble not available for {self.timeframe}")
            return create_fallback_result()

        try:
            # 特徴量エンジニアリング
            feat_df = self.feature_engineer.transform(price_df)
            self.processing_stats["feature_engineering_calls"] += 1

            if feat_df.empty:
                logger.warning(f"Empty features for {self.timeframe} prediction")
                return create_fallback_result()

            # スケーリング
            scaled_features = self.scaler.transform(feat_df.values)
            X_scaled = pd.DataFrame(
                scaled_features, index=feat_df.index, columns=feat_df.columns
            )

            # 最新データ取得
            last_X = X_scaled.iloc[[-1]]

            # アンサンブル予測実行
            predictions, probabilities, ensemble_confidence, trading_info = (
                self.ensemble_model.predict_with_trading_confidence(
                    last_X, market_context
                )
            )
            self.processing_stats["ensemble_predictions"] += 1

            # Phase C1統合: 新信頼度計算システム使用
            # 個別モデル予測取得（合意度計算用）
            individual_predictions = self._get_individual_model_predictions(last_X)

            # 統合信頼度計算
            unified_confidence = (
                self.confidence_calculator.calculate_prediction_confidence(
                    probabilities, individual_predictions, market_context
                )
            )
            self.processing_stats["confidence_calculations"] += 1

            # 予測情報統合
            prediction_info = {
                "timeframe": self.timeframe,
                "method": self.ensemble_method,
                "ensemble_enabled": True,
                "ensemble_confidence": ensemble_confidence[0],
                "unified_confidence": unified_confidence[0],
                "dynamic_threshold": trading_info.get("dynamic_threshold", 0.5),
                "market_regime": trading_info.get("market_regime", "normal"),
                "risk_level": trading_info.get("risk_level", "medium"),
                "model_agreement": self._calculate_model_agreement(
                    individual_predictions
                ),
                "prediction_quality": self._assess_prediction_quality(
                    probabilities, unified_confidence[0]
                ),
            }

            # 予測履歴記録
            self._record_prediction(prediction_info, probabilities[0], market_context)

            return predictions, probabilities, unified_confidence, prediction_info

        except Exception as e:
            logger.error(f"❌ {self.timeframe} prediction failed: {e}")
            return create_fallback_result()

    def _get_individual_model_predictions(
        self, X: pd.DataFrame
    ) -> Optional[List[np.ndarray]]:
        """個別モデル予測取得（合意度計算用）"""
        if not hasattr(self.ensemble_model, "fitted_base_models"):
            return None

        try:
            individual_predictions = []
            for model in self.ensemble_model.fitted_base_models:
                proba = model.predict_proba(X)
                individual_predictions.append(proba[:, 1])  # 正例クラス確率
            return individual_predictions
        except Exception as e:
            logger.error(
                f"Failed to get individual predictions for {self.timeframe}: {e}"
            )
            return None

    def _calculate_model_agreement(
        self, individual_predictions: Optional[List[np.ndarray]]
    ) -> float:
        """モデル合意度計算"""
        if individual_predictions is None or len(individual_predictions) < 2:
            return 1.0

        try:
            # 標準偏差ベース合意度計算
            pred_array = np.array(individual_predictions)
            agreement = 1.0 - np.std(pred_array) / 0.5  # 正規化
            return max(0.0, min(1.0, agreement))
        except Exception:
            return 0.5

    def _assess_prediction_quality(
        self, probabilities: np.ndarray, confidence: float
    ) -> str:
        """予測品質評価"""
        prob_max = np.max(probabilities[0])

        if confidence > 0.8 and prob_max > 0.7:
            return "excellent"
        elif confidence > 0.6 and prob_max > 0.6:
            return "good"
        elif confidence > 0.4 and prob_max > 0.55:
            return "fair"
        else:
            return "poor"

    def _record_prediction(
        self,
        prediction_info: Dict[str, Any],
        probabilities: np.ndarray,
        market_context: Optional[Dict[str, Any]],
    ):
        """予測履歴記録"""
        record = {
            "timestamp": pd.Timestamp.now(),
            "timeframe": self.timeframe,
            "probabilities": probabilities.tolist(),
            "confidence": prediction_info.get("unified_confidence", 0.5),
            "market_regime": prediction_info.get("market_regime", "normal"),
            "prediction_quality": prediction_info.get("prediction_quality", "unknown"),
        }

        if market_context:
            record["vix_level"] = market_context.get("vix_level", 20.0)
            record["volatility"] = market_context.get("volatility", 0.02)

        self.prediction_history.append(record)

        # 履歴サイズ制限
        if len(self.prediction_history) > self.max_history_size:
            self.prediction_history.pop(0)

    def generate_trading_signal(
        self,
        price_df: pd.DataFrame,
        position: Optional[Position] = None,
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Signal:
        """
        取引シグナル生成（タイムフレーム特化）

        Parameters:
        -----------
        price_df : pd.DataFrame
            価格データ
        position : Position, optional
            現在のポジション
        market_context : Dict[str, Any], optional
            市場環境コンテキスト

        Returns:
        --------
        Signal
            取引シグナル
        """
        try:
            # アンサンブル予測実行
            predictions, probabilities, confidence_scores, prediction_info = (
                self.predict_with_confidence(price_df, market_context)
            )

            current_price = float(price_df["close"].iloc[-1])
            prediction = predictions[0]
            probability = probabilities[0, 1]  # 正例クラス確率
            confidence = confidence_scores[0]

            # 動的閾値取得
            dynamic_threshold = self.confidence_calculator.calculate_dynamic_threshold(
                market_context, confidence
            )

            # ポジション状況確認
            position_exists = position is not None and position.exist

            if position_exists:
                # エグジット判定（リスク調整型）
                exit_threshold = self.confidence_calculator.calculate_exit_threshold(
                    market_context, confidence
                )

                if probability < exit_threshold:
                    logger.info(
                        f"🚪 {self.timeframe} EXIT signal: "
                        f"prob={probability:.4f} < {exit_threshold:.4f}"
                    )
                    return Signal(side="SELL", price=current_price)

                return Signal()  # ホールド

            else:
                # エントリー判定（信頼度ベース）
                min_confidence = max(dynamic_threshold, 0.5)

                if prediction == 1 and confidence >= min_confidence:
                    logger.info(
                        f"📈 {self.timeframe} LONG signal: "
                        f"prob={probability:.4f}, confidence={confidence:.4f}"
                    )
                    return Signal(side="BUY", price=current_price)

                elif (
                    probability < (1.0 - dynamic_threshold)
                    and confidence >= min_confidence
                ):
                    logger.info(
                        f"📉 {self.timeframe} SHORT signal: "
                        f"prob={probability:.4f}, confidence={confidence:.4f}"
                    )
                    return Signal(side="SELL", price=current_price)

                return Signal()  # ホールド

        except Exception as e:
            logger.error(f"❌ {self.timeframe} signal generation failed: {e}")
            return Signal()

    def get_processor_info(self) -> Dict[str, Any]:
        """プロセッサー情報取得"""
        info = {
            "timeframe": self.timeframe,
            "ensemble_enabled": self.ensemble_enabled,
            "ensemble_method": self.ensemble_method,
            "is_fitted": self.is_fitted,
            "base_confidence_threshold": self.base_confidence_threshold,
            "processing_stats": self.processing_stats.copy(),
            "prediction_history_size": len(self.prediction_history),
        }

        # アンサンブルモデル情報
        if self.ensemble_model and self.is_fitted:
            try:
                ensemble_info = self.ensemble_model.get_trading_ensemble_info()
                info["ensemble_details"] = ensemble_info
            except Exception as e:
                info["ensemble_details"] = {"error": str(e)}

        # 最近のパフォーマンス分析
        if self.prediction_history:
            recent_predictions = self.prediction_history[-10:]
            info["recent_performance"] = self._analyze_recent_performance(
                recent_predictions
            )

        return info

    def _analyze_recent_performance(
        self, recent_predictions: List[Dict]
    ) -> Dict[str, Any]:
        """最近のパフォーマンス分析"""
        try:
            confidences = [p["confidence"] for p in recent_predictions]
            vix_levels = [p.get("vix_level", 20.0) for p in recent_predictions]

            quality_counts = {}
            for p in recent_predictions:
                quality = p.get("prediction_quality", "unknown")
                quality_counts[quality] = quality_counts.get(quality, 0) + 1

            return {
                "avg_confidence": np.mean(confidences) if confidences else 0.0,
                "confidence_stability": np.std(confidences) if confidences else 0.0,
                "avg_vix_level": np.mean(vix_levels) if vix_levels else 20.0,
                "prediction_count": len(recent_predictions),
                "quality_distribution": quality_counts,
            }

        except Exception as e:
            logger.error(f"Performance analysis failed for {self.timeframe}: {e}")
            return {}

    def reset_statistics(self):
        """統計リセット"""
        for key in self.processing_stats:
            self.processing_stats[key] = 0
        self.prediction_history.clear()
        if self.confidence_calculator:
            self.confidence_calculator.reset_statistics()
        logger.info(f"📊 {self.timeframe} processor statistics reset")


# ファクトリー関数


def create_timeframe_ensemble_processor(
    timeframe: str,
    config: Dict[str, Any],
    feature_engineer: Optional[FeatureEngineer] = None,
) -> TimeframeEnsembleProcessor:
    """
    タイムフレーム内アンサンブルプロセッサー作成

    Parameters:
    -----------
    timeframe : str
        対象タイムフレーム
    config : Dict[str, Any]
        設定辞書
    feature_engineer : FeatureEngineer, optional
        特徴量エンジニアリングインスタンス

    Returns:
    --------
    TimeframeEnsembleProcessor
        初期化済みプロセッサー
    """
    return TimeframeEnsembleProcessor(timeframe, config, feature_engineer)
