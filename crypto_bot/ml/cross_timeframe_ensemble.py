# =============================================================================
# ファイル名: crypto_bot/ml/cross_timeframe_ensemble.py
# 説明:
# Phase C1: タイムフレーム間統合専用モジュール
# 複数タイムフレーム予測の重み付き統合・動的重み調整・市場環境連動
# 既存multi_timeframe_ensemble.py統合ロジック分離・最適化・Phase B統合
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from crypto_bot.execution.engine import Signal
from crypto_bot.utils.ensemble_confidence import EnsembleConfidenceCalculator

logger = logging.getLogger(__name__)


class CrossTimeframeIntegrator:
    """
    タイムフレーム間アンサンブル統合システム

    機能:
    - 複数タイムフレーム予測の重み付き統合
    - 動的重み調整（品質・信頼度・合意度ベース）
    - 市場環境連動重み調整
    - Phase C1信頼度計算システム活用
    - 統合パフォーマンス追跡・最適化
    """

    def __init__(self, config: Dict[str, Any]):
        """
        タイムフレーム間統合システム初期化

        Parameters:
        -----------
        config : Dict[str, Any]
            設定辞書（マルチタイムフレーム・アンサンブル設定含む）
        """
        self.config = config

        # マルチタイムフレーム設定取得（Phase H.12: 4h内部処理復活・本来設計復旧）
        multi_config = self.config.get("multi_timeframe", {})
        self.timeframes = multi_config.get(
            "timeframes", ["15m", "1h", "4h"]
        )  # 本来設計復旧
        self.base_weights = multi_config.get("weights", [0.3, 0.5, 0.2])  # 本来重み復旧
        self.consensus_threshold = multi_config.get(
            "timeframe_consensus_threshold", 0.6
        )
        self.missing_data_tolerance = multi_config.get("missing_data_tolerance", 0.1)

        # 統合方法設定
        self.integration_method = multi_config.get(
            "integration_method", "quality_weighted_ensemble"
        )
        self.dynamic_weighting_enabled = multi_config.get("dynamic_weighting", True)
        self.market_adaptation_enabled = multi_config.get("market_adaptation", True)

        # アンサンブル設定
        ensemble_config = self.config.get("ml", {}).get("ensemble", {})
        self.ensemble_confidence_threshold = ensemble_config.get(
            "confidence_threshold", 0.65
        )
        self.risk_adjustment_enabled = ensemble_config.get("risk_adjustment", True)

        # 信頼度計算システム初期化（Phase C1統合）
        self.confidence_calculator = EnsembleConfidenceCalculator(self.config)

        # 重み調整履歴（パフォーマンスフィードバック用）
        self.weight_history: List[Dict[str, Any]] = []
        self.integration_history: List[Dict[str, Any]] = []
        self.max_history_size = 100

        # 統計・パフォーマンス追跡
        self.integration_stats = {
            "integrations_performed": 0,
            "dynamic_weight_adjustments": 0,
            "market_adaptations": 0,
            "consensus_calculations": 0,
            "quality_assessments": 0,
            "high_consensus_signals": 0,
            "low_consensus_rejections": 0,
        }

        # 現在の動的重み（初期化）
        self.current_dynamic_weights = self.base_weights.copy()
        self.last_weight_update = datetime.now()

        logger.info("🔗 CrossTimeframeIntegrator initialized")
        logger.info(f"   Timeframes: {self.timeframes}")
        logger.info(f"   Base weights: {self.base_weights}")
        logger.info(f"   Integration method: {self.integration_method}")

    def integrate_timeframe_predictions(
        self,
        timeframe_predictions: Dict[str, Dict[str, Any]],
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        タイムフレーム間アンサンブル統合（Phase C1コア機能）

        Parameters:
        -----------
        timeframe_predictions : Dict[str, Dict[str, Any]]
            各タイムフレームの予測結果
            形式: {timeframe: {"prediction": array, "probability": array, "confidence": float, ...}}
        market_context : Dict[str, Any], optional
            市場環境コンテキスト

        Returns:
        --------
        Tuple[float, Dict[str, Any]]
            (統合シグナル値, 統合詳細情報)
        """
        self.integration_stats["integrations_performed"] += 1

        try:
            # 1. 予測データ前処理・検証
            processed_predictions = self._preprocess_predictions(timeframe_predictions)

            if not processed_predictions:
                logger.warning("No valid timeframe predictions for integration")
                return 0.5, self._create_fallback_integration_info()

            # 2. 動的重み計算（Phase C1強化機能）
            if self.dynamic_weighting_enabled:
                dynamic_weights = self._calculate_dynamic_weights(
                    processed_predictions, market_context
                )
                self.integration_stats["dynamic_weight_adjustments"] += 1
            else:
                dynamic_weights = self._get_base_weights_for_predictions(
                    processed_predictions
                )

            # 3. 統合シグナル計算
            integrated_signal, signal_components = self._calculate_integrated_signal(
                processed_predictions, dynamic_weights
            )

            # 4. 合意度計算（Phase C1統合）
            consensus_score = self._calculate_cross_timeframe_consensus(
                processed_predictions, dynamic_weights
            )
            self.integration_stats["consensus_calculations"] += 1

            # 5. 品質評価
            integration_quality = self._assess_integration_quality(
                processed_predictions, consensus_score, market_context
            )
            self.integration_stats["quality_assessments"] += 1

            # 6. 統合情報構築
            integration_info = {
                "integration_method": self.integration_method,
                "timeframe_count": len(processed_predictions),
                "dynamic_weights": dynamic_weights,
                "signal_components": signal_components,
                "consensus_score": consensus_score,
                "integration_quality": integration_quality,
                "market_adaptation": market_context is not None,
                "meets_consensus_threshold": consensus_score
                >= self.consensus_threshold,
            }

            # 7. 履歴記録・パフォーマンス追跡
            self._record_integration(
                integrated_signal,
                integration_info,
                processed_predictions,
                market_context,
            )

            # 8. 統計更新
            if consensus_score >= self.consensus_threshold:
                self.integration_stats["high_consensus_signals"] += 1
            else:
                self.integration_stats["low_consensus_rejections"] += 1

            logger.debug(
                f"🔗 Cross-timeframe integration: signal={integrated_signal:.3f}, "
                f"consensus={consensus_score:.3f}, quality={integration_quality}"
            )

            return integrated_signal, integration_info

        except Exception as e:
            logger.error(f"❌ Cross-timeframe integration failed: {e}")
            return 0.5, self._create_fallback_integration_info()

    def _preprocess_predictions(
        self, timeframe_predictions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """予測データ前処理・検証"""
        processed = {}

        for timeframe, pred_data in timeframe_predictions.items():
            try:
                # 必須データ存在確認
                if not self._validate_prediction_data(pred_data):
                    logger.warning(f"Invalid prediction data for {timeframe}")
                    continue

                # データ正規化・標準化
                processed_data = {
                    "timeframe": timeframe,
                    "prediction": self._extract_prediction_value(pred_data),
                    "probability": self._extract_probability_value(pred_data),
                    "confidence": pred_data.get(
                        "unified_confidence", pred_data.get("confidence", 0.5)
                    ),
                    "model_agreement": pred_data.get("model_agreement", 1.0),
                    "prediction_quality": pred_data.get(
                        "prediction_quality", "unknown"
                    ),
                    "market_regime": pred_data.get("market_regime", "normal"),
                    "original_data": pred_data,
                }

                processed[timeframe] = processed_data

            except Exception as e:
                logger.error(f"Failed to preprocess {timeframe} prediction: {e}")
                continue

        return processed

    def _validate_prediction_data(self, pred_data: Dict[str, Any]) -> bool:
        """予測データ妥当性検証"""
        required_fields = ["prediction", "probability", "confidence"]
        return all(field in pred_data for field in required_fields)

    def _extract_prediction_value(self, pred_data: Dict[str, Any]) -> float:
        """予測値抽出・正規化"""
        prediction = pred_data.get("prediction")
        if isinstance(prediction, np.ndarray):
            return float(prediction[0])
        elif isinstance(prediction, (int, float)):
            return float(prediction)
        else:
            return 0.0

    def _extract_probability_value(self, pred_data: Dict[str, Any]) -> float:
        """確率値抽出・正規化"""
        probability = pred_data.get("probability")
        if isinstance(probability, np.ndarray):
            if probability.ndim == 2 and probability.shape[1] > 1:
                return float(probability[0, 1])  # 正例クラス確率
            else:
                return float(probability[0])
        elif isinstance(probability, (int, float)):
            return float(probability)
        else:
            return 0.5

    def _calculate_dynamic_weights(
        self,
        processed_predictions: Dict[str, Dict[str, Any]],
        market_context: Optional[Dict[str, Any]] = None,
    ) -> List[float]:
        """
        動的重み計算（Phase C1コア機能）

        品質・信頼度・市場環境に基づく重み調整
        """
        timeframes_order = list(processed_predictions.keys())
        base_weights = self._get_base_weights_for_predictions(processed_predictions)

        # 1. 品質ベース調整
        quality_adjustments = []
        for tf in timeframes_order:
            pred_data = processed_predictions[tf]
            confidence = pred_data["confidence"]
            model_agreement = pred_data["model_agreement"]

            # 品質スコア計算
            quality_score = (confidence * 0.7) + (model_agreement * 0.3)
            quality_adjustments.append(quality_score)

        # 2. 市場環境ベース調整
        market_adjustments = []
        if self.market_adaptation_enabled and market_context:
            market_regime = self.confidence_calculator.assess_market_regime(
                market_context
            )

            for tf in timeframes_order:
                if market_regime == "crisis":
                    # 危機時：長期タイムフレーム重視
                    if tf == "4h":
                        market_adj = 1.2
                    elif tf == "1h":
                        market_adj = 1.0
                    else:  # 15m
                        market_adj = 0.8
                elif market_regime == "calm":
                    # 安定時：短期タイムフレーム重視
                    if tf == "15m":
                        market_adj = 1.2
                    elif tf == "1h":
                        market_adj = 1.0
                    else:  # 4h
                        market_adj = 0.9
                else:
                    market_adj = 1.0

                market_adjustments.append(market_adj)

            self.integration_stats["market_adaptations"] += 1
        else:
            market_adjustments = [1.0] * len(timeframes_order)

        # 3. 履歴ベース調整（パフォーマンスフィードバック）
        performance_adjustments = self._calculate_performance_adjustments(
            timeframes_order
        )

        # 4. 統合重み計算
        dynamic_weights = []
        for i, tf in enumerate(timeframes_order):
            base_weight = base_weights[i]
            quality_adj = quality_adjustments[i]
            market_adj = market_adjustments[i]
            performance_adj = performance_adjustments[i]

            # 重み統合（乗算・加算の組み合わせ）
            adjusted_weight = base_weight * quality_adj * market_adj * performance_adj
            dynamic_weights.append(adjusted_weight)

        # 5. 正規化
        total_weight = sum(dynamic_weights)
        if total_weight > 0:
            dynamic_weights = [w / total_weight for w in dynamic_weights]
        else:
            dynamic_weights = [1.0 / len(timeframes_order)] * len(timeframes_order)

        # 6. 履歴記録
        self._record_weight_update(
            timeframes_order,
            dynamic_weights,
            {
                "quality_adjustments": quality_adjustments,
                "market_adjustments": market_adjustments,
                "performance_adjustments": performance_adjustments,
                "market_context": market_context,
            },
        )

        return dynamic_weights

    def _get_base_weights_for_predictions(
        self, processed_predictions: Dict[str, Dict[str, Any]]
    ) -> List[float]:
        """予測に対応する基本重み取得"""
        weights = []
        for tf in processed_predictions.keys():
            try:
                index = self.timeframes.index(tf)
                weights.append(self.base_weights[index])
            except (ValueError, IndexError):
                weights.append(1.0 / len(processed_predictions))  # デフォルト重み

        # 正規化
        total = sum(weights)
        if total > 0:
            return [w / total for w in weights]
        else:
            return [1.0 / len(weights)] * len(weights)

    def _calculate_performance_adjustments(
        self, timeframes_order: List[str]
    ) -> List[float]:
        """履歴ベースパフォーマンス調整計算"""
        if not self.integration_history:
            return [1.0] * len(timeframes_order)

        # 最近の統合結果から各タイムフレームのパフォーマンスを評価
        recent_history = self.integration_history[-20:]  # 最新20件

        performance_scores = {}
        for tf in timeframes_order:
            # 各タイムフレームの予測精度・貢献度を計算
            tf_contributions = []
            for record in recent_history:
                if tf in record.get("timeframe_contributions", {}):
                    contribution = record["timeframe_contributions"][tf]
                    tf_contributions.append(contribution)

            if tf_contributions:
                avg_performance = np.mean(tf_contributions)
                performance_scores[tf] = max(0.5, min(1.5, avg_performance))  # 範囲制限
            else:
                performance_scores[tf] = 1.0

        return [performance_scores.get(tf, 1.0) for tf in timeframes_order]

    def _calculate_integrated_signal(
        self, processed_predictions: Dict[str, Dict[str, Any]], weights: List[float]
    ) -> Tuple[float, Dict[str, float]]:
        """統合シグナル計算"""
        signal_values = []
        signal_components = {}

        timeframes_order = list(processed_predictions.keys())

        for i, tf in enumerate(timeframes_order):
            pred_data = processed_predictions[tf]

            # シグナル値変換
            probability = pred_data["probability"]
            if probability > 0.6:
                signal_value = 0.75  # 強気
            elif probability < 0.4:
                signal_value = 0.25  # 弱気
            else:
                signal_value = 0.5  # 中立

            signal_values.append(signal_value)
            signal_components[tf] = signal_value

        # 重み付き統合計算
        if signal_values and len(weights) == len(signal_values):
            weighted_sum = sum(s * w for s, w in zip(signal_values, weights))
            integrated_signal = weighted_sum
        else:
            integrated_signal = 0.5  # フォールバック

        return integrated_signal, signal_components

    def _calculate_cross_timeframe_consensus(
        self, processed_predictions: Dict[str, Dict[str, Any]], weights: List[float]
    ) -> float:
        """タイムフレーム間合意度計算"""
        probabilities = [
            pred_data["probability"] for pred_data in processed_predictions.values()
        ]

        # Phase C1統合: 統一信頼度計算システム使用
        consensus_score = self.confidence_calculator.calculate_consensus_score(
            probabilities, weights
        )

        return consensus_score

    def _assess_integration_quality(
        self,
        processed_predictions: Dict[str, Dict[str, Any]],
        consensus_score: float,
        market_context: Optional[Dict[str, Any]],
    ) -> str:
        """統合品質評価"""
        # 基本品質要因
        confidence_scores = [
            pred_data["confidence"] for pred_data in processed_predictions.values()
        ]
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0.5

        # 統合品質判定
        if consensus_score > 0.8 and avg_confidence > 0.7:
            return "excellent"
        elif consensus_score > 0.6 and avg_confidence > 0.6:
            return "good"
        elif consensus_score > 0.4 and avg_confidence > 0.5:
            return "fair"
        else:
            return "poor"

    def _record_integration(
        self,
        integrated_signal: float,
        integration_info: Dict[str, Any],
        processed_predictions: Dict[str, Dict[str, Any]],
        market_context: Optional[Dict[str, Any]],
    ):
        """統合履歴記録"""
        record = {
            "timestamp": datetime.now(),
            "integrated_signal": integrated_signal,
            "consensus_score": integration_info["consensus_score"],
            "integration_quality": integration_info["integration_quality"],
            "timeframe_count": integration_info["timeframe_count"],
            "dynamic_weights": integration_info["dynamic_weights"],
            "timeframe_contributions": {},
            "market_regime": (
                market_context.get("market_regime", "unknown")
                if market_context
                else "unknown"
            ),
        }

        # 各タイムフレームの貢献度記録
        for tf, pred_data in processed_predictions.items():
            record["timeframe_contributions"][tf] = pred_data["confidence"]

        self.integration_history.append(record)

        # 履歴サイズ制限
        if len(self.integration_history) > self.max_history_size:
            self.integration_history.pop(0)

    def _record_weight_update(
        self,
        timeframes: List[str],
        weights: List[float],
        adjustment_details: Dict[str, Any],
    ):
        """重み更新履歴記録"""
        record = {
            "timestamp": datetime.now(),
            "timeframes": timeframes,
            "weights": weights,
            "adjustment_details": adjustment_details,
        }

        self.weight_history.append(record)

        # 履歴サイズ制限
        if len(self.weight_history) > self.max_history_size:
            self.weight_history.pop(0)

        # 現在の動的重み更新
        self.current_dynamic_weights = weights.copy()
        self.last_weight_update = datetime.now()

    def _create_fallback_integration_info(self) -> Dict[str, Any]:
        """フォールバック統合情報作成"""
        return {
            "integration_method": "fallback",
            "timeframe_count": 0,
            "dynamic_weights": [],
            "signal_components": {},
            "consensus_score": 0.0,
            "integration_quality": "poor",
            "market_adaptation": False,
            "meets_consensus_threshold": False,
            "error": True,
        }

    def create_final_signal(
        self,
        integrated_signal: float,
        integration_info: Dict[str, Any],
        current_price: float,
        position_exists: bool = False,
    ) -> Signal:
        """
        最終取引シグナル生成

        Parameters:
        -----------
        integrated_signal : float
            統合シグナル値
        integration_info : Dict[str, Any]
            統合詳細情報
        current_price : float
            現在価格
        position_exists : bool
            ポジション存在フラグ

        Returns:
        --------
        Signal
            最終取引シグナル
        """
        consensus_score = integration_info["consensus_score"]
        integration_quality = integration_info["integration_quality"]

        # 合意度閾値チェック
        if consensus_score < self.consensus_threshold:
            logger.debug(
                f"🚫 Low consensus rejection: {consensus_score:.3f} < {self.consensus_threshold}"
            )
            return Signal()  # シグナルなし

        if position_exists:
            # エグジット判定
            exit_threshold = 0.4 + (1.0 - consensus_score) * 0.1
            if integrated_signal < exit_threshold:
                logger.info(
                    f"🚪 Cross-timeframe EXIT: signal={integrated_signal:.3f} < {exit_threshold:.3f}"
                )
                return Signal(side="SELL", price=current_price)
            return Signal()  # ホールド

        else:
            # エントリー判定
            entry_threshold = 0.5 + (self.ensemble_confidence_threshold - 0.5)

            if integrated_signal > entry_threshold and integration_quality in [
                "good",
                "excellent",
            ]:
                logger.info(
                    f"📈 Cross-timeframe LONG: signal={integrated_signal:.3f}, "
                    f"consensus={consensus_score:.3f}, quality={integration_quality}"
                )
                return Signal(side="BUY", price=current_price)

            elif integrated_signal < (
                1.0 - entry_threshold
            ) and integration_quality in ["good", "excellent"]:
                logger.info(
                    f"📉 Cross-timeframe SHORT: signal={integrated_signal:.3f}, "
                    f"consensus={consensus_score:.3f}, quality={integration_quality}"
                )
                return Signal(side="SELL", price=current_price)

            return Signal()  # ホールド

    def get_integrator_info(self) -> Dict[str, Any]:
        """統合システム情報取得"""
        return {
            "timeframes": self.timeframes,
            "base_weights": self.base_weights,
            "current_dynamic_weights": self.current_dynamic_weights,
            "integration_method": self.integration_method,
            "consensus_threshold": self.consensus_threshold,
            "dynamic_weighting_enabled": self.dynamic_weighting_enabled,
            "market_adaptation_enabled": self.market_adaptation_enabled,
            "integration_stats": self.integration_stats.copy(),
            "integration_history_size": len(self.integration_history),
            "weight_history_size": len(self.weight_history),
            "last_weight_update": (
                self.last_weight_update.isoformat() if self.last_weight_update else None
            ),
        }

    def get_recent_performance(self) -> Dict[str, Any]:
        """最近のパフォーマンス分析"""
        if not self.integration_history:
            return {}

        recent_integrations = self.integration_history[-20:]

        try:
            consensus_scores = [r["consensus_score"] for r in recent_integrations]
            integrated_signals = [r["integrated_signal"] for r in recent_integrations]

            quality_counts = {}
            for r in recent_integrations:
                quality = r["integration_quality"]
                quality_counts[quality] = quality_counts.get(quality, 0) + 1

            return {
                "avg_consensus": np.mean(consensus_scores),
                "consensus_stability": np.std(consensus_scores),
                "avg_signal": np.mean(integrated_signals),
                "signal_volatility": np.std(integrated_signals),
                "integration_count": len(recent_integrations),
                "quality_distribution": quality_counts,
            }

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {}

    def reset_statistics(self):
        """統計リセット"""
        for key in self.integration_stats:
            self.integration_stats[key] = 0
        self.integration_history.clear()
        self.weight_history.clear()
        self.current_dynamic_weights = self.base_weights.copy()
        logger.info("📊 Cross-timeframe integrator statistics reset")


# ファクトリー関数


def create_cross_timeframe_integrator(
    config: Dict[str, Any],
) -> CrossTimeframeIntegrator:
    """
    タイムフレーム間統合システム作成

    Parameters:
    -----------
    config : Dict[str, Any]
        設定辞書

    Returns:
    --------
    CrossTimeframeIntegrator
        初期化済み統合システム
    """
    return CrossTimeframeIntegrator(config)
