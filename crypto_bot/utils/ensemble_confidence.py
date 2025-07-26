# =============================================================================
# ファイル名: crypto_bot/utils/ensemble_confidence.py
# 説明:
# Phase C1: 2段階アンサンブル用信頼度計算ユーティリティ統合
# エントロピー・合意度・市場環境調整・リスク評価の統一化
# 既存実装（ensemble.py・multi_timeframe_ensemble.py）から抽出・改良
# =============================================================================

import logging
from typing import Any, Dict, List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


class EnsembleConfidenceCalculator:
    """
    2段階アンサンブル学習用信頼度計算統合システム

    統合機能:
    - エントロピーベース信頼度計算
    - モデル合意度計算
    - 市場環境調整
    - 動的閾値計算
    - リスク評価・ポジションサイジング
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        信頼度計算システム初期化

        Parameters:
        -----------
        config : Dict[str, Any], optional
            信頼度計算設定
        """
        self.config = config or {}

        # 基本設定
        ensemble_config = self.config.get("ml", {}).get("ensemble", {})
        self.base_confidence_threshold = ensemble_config.get(
            "confidence_threshold", 0.65
        )
        self.risk_adjustment_enabled = ensemble_config.get("risk_adjustment", True)

        # VIX調整設定
        dynamic_config = self.config.get("ml", {}).get("dynamic_threshold", {})
        self.vix_adjustment_enabled = dynamic_config.get("vix_adjustment", True)
        self.vix_levels = dynamic_config.get(
            "vix_levels",
            {
                "low_vix": {"threshold": 15, "adjustment": -0.05},
                "medium_vix": {"threshold": 25, "adjustment": 0.0},
                "high_vix": {"threshold": 35, "adjustment": 0.1},
                "extreme_vix": {"threshold": 50, "adjustment": 0.2},
            },
        )

        # 統計追跡
        self.confidence_stats = {
            "entropy_calculations": 0,
            "consensus_calculations": 0,
            "market_adjustments": 0,
            "risk_assessments": 0,
        }

        logger.info("📊 EnsembleConfidenceCalculator initialized")

    def calculate_prediction_confidence(
        self,
        probabilities: np.ndarray,
        individual_predictions: Optional[List[np.ndarray]] = None,
        market_context: Optional[Dict[str, Any]] = None,
    ) -> np.ndarray:
        """
        統合予測信頼度計算

        Parameters:
        -----------
        probabilities : np.ndarray
            アンサンブル予測確率 (shape: [n_samples, n_classes])
        individual_predictions : List[np.ndarray], optional
            個別モデル予測リスト（合意度計算用）
        market_context : Dict[str, Any], optional
            市場環境コンテキスト

        Returns:
        --------
        np.ndarray
            信頼度スコア (shape: [n_samples])
        """
        self.confidence_stats["entropy_calculations"] += 1

        try:
            # 1. エントロピーベース信頼度
            entropy_confidence = self._calculate_entropy_confidence(probabilities)

            # 2. 確率極端度ベース信頼度
            probability_confidence = self._calculate_probability_confidence(
                probabilities
            )

            # 3. モデル合意度（個別予測が提供されている場合）
            if individual_predictions is not None:
                model_agreement = self._calculate_model_agreement_score(
                    individual_predictions
                )
                self.confidence_stats["consensus_calculations"] += 1
            else:
                model_agreement = np.ones(len(probabilities))

            # 4. 市場環境調整
            if market_context is not None:
                market_adjustment = self._get_market_confidence_adjustment(
                    market_context
                )
                self.confidence_stats["market_adjustments"] += 1
            else:
                market_adjustment = 0.5

            # 総合信頼度計算（重み付き統合）
            if individual_predictions is not None:
                # 個別予測が利用可能な場合
                confidence_scores = (
                    0.3 * entropy_confidence
                    + 0.3 * probability_confidence
                    + 0.2 * model_agreement
                    + 0.2 * market_adjustment
                )
            else:
                # 個別予測が利用できない場合
                confidence_scores = (
                    0.4 * entropy_confidence
                    + 0.4 * probability_confidence
                    + 0.2 * market_adjustment
                )

            return np.clip(confidence_scores, 0.0, 1.0)

        except Exception as e:
            logger.error(f"Confidence calculation failed: {e}")
            return np.full(len(probabilities), 0.5)

    def _calculate_entropy_confidence(self, probabilities: np.ndarray) -> np.ndarray:
        """エントロピーベース信頼度計算"""
        epsilon = 1e-8
        entropy = -np.sum(probabilities * np.log(probabilities + epsilon), axis=1)

        # 2クラス分類の最大エントロピーで正規化
        max_entropy = np.log(probabilities.shape[1])
        entropy_confidence = 1 - (entropy / max_entropy)

        return np.clip(entropy_confidence, 0.0, 1.0)

    def _calculate_probability_confidence(
        self, probabilities: np.ndarray
    ) -> np.ndarray:
        """確率極端度ベース信頼度計算"""
        if probabilities.shape[1] == 2:  # 二値分類の場合
            # 0.5からの距離を信頼度とする
            probability_confidence = np.abs(probabilities[:, 1] - 0.5) * 2
        else:
            # 多クラス分類の場合は最大確率を使用
            probability_confidence = np.max(probabilities, axis=1)

        return np.clip(probability_confidence, 0.0, 1.0)

    def _calculate_model_agreement_score(
        self, individual_predictions: List[np.ndarray]
    ) -> np.ndarray:
        """モデル間合意度スコア計算"""
        if len(individual_predictions) < 2:
            return np.ones(len(individual_predictions[0]))

        # 各モデルの予測確率を結合
        pred_array = np.array(individual_predictions).T  # [n_samples, n_models]

        # 標準偏差ベースの合意度（低分散 = 高合意度）
        agreement = 1.0 - np.std(pred_array, axis=1) / 0.5  # 正規化

        return np.clip(agreement, 0.0, 1.0)

    def _get_market_confidence_adjustment(
        self, market_context: Dict[str, Any]
    ) -> float:
        """市場環境による信頼度調整"""
        # VIXベース調整
        vix_level = market_context.get("vix_level", 20.0)
        if vix_level > 35:
            vix_adj = 0.2  # 不安定な市場では信頼度低下
        elif vix_level < 15:
            vix_adj = 0.8  # 安定市場では信頼度向上
        else:
            vix_adj = 0.5

        # トレンド強度調整
        trend_strength = market_context.get("trend_strength", 0.5)
        trend_adj = trend_strength  # 強いトレンドは高信頼度

        # ボラティリティ調整
        volatility = market_context.get("volatility", 0.02)
        if volatility > 0.05:
            vol_adj = 0.3  # 高ボラティリティでは信頼度低下
        elif volatility < 0.01:
            vol_adj = 0.7  # 低ボラティリティでは信頼度向上
        else:
            vol_adj = 0.5

        return (vix_adj + trend_adj + vol_adj) / 3.0

    def calculate_consensus_score(
        self, signal_values: List[float], weights: Optional[List[float]] = None
    ) -> float:
        """
        タイムフレーム間シグナル合意度計算

        Parameters:
        -----------
        signal_values : List[float]
            各タイムフレームのシグナル値
        weights : List[float], optional
            各タイムフレームの重み

        Returns:
        --------
        float
            合意度スコア (0.0-1.0)
        """
        if len(signal_values) < 2:
            return 1.0

        # 重み付き標準偏差計算
        if weights is not None and len(weights) == len(signal_values):
            try:
                # ✅ Phase H.14修正: 形状チェック・型変換でnp.averageエラー解決
                signal_array = np.asarray(signal_values)
                weight_array = np.asarray(weights)
                if signal_array.shape[0] != weight_array.shape[0]:
                    logger.warning(
                        f"Shape mismatch: signal_values={signal_array.shape}, weights={weight_array.shape}"
                    )
                    weighted_std = np.std(signal_values)
                else:
                    # 重み付き平均
                    weighted_mean = np.average(signal_array, weights=weight_array)
                    # 重み付き分散
                    weighted_var = np.average(
                        (signal_array - weighted_mean) ** 2, weights=weight_array
                    )
                    weighted_std = np.sqrt(weighted_var)
            except Exception as e:
                logger.error(f"❌ Weighted calculation failed: {e}")
                weighted_std = np.std(signal_values)
        else:
            # 単純標準偏差
            weighted_std = np.std(signal_values)

        # 標準偏差を合意度に変換（低分散 = 高合意度）
        max_std = 0.25  # 想定される最大標準偏差
        consensus = 1.0 - min(weighted_std / max_std, 1.0)

        return consensus

    def calculate_dynamic_threshold(
        self,
        market_context: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
    ) -> float:
        """
        動的閾値計算

        Parameters:
        -----------
        market_context : Dict[str, Any], optional
            市場環境コンテキスト
        confidence_score : float, optional
            現在の信頼度スコア

        Returns:
        --------
        float
            動的閾値
        """
        base_threshold = self.base_confidence_threshold

        if market_context is None:
            return base_threshold

        # VIXベース調整
        vix_level = market_context.get("vix_level", 20.0)
        if vix_level > 35:  # 高VIX（危機時）
            threshold_adj = 0.1  # より保守的
        elif vix_level > 25:  # 中VIX（不安定）
            threshold_adj = 0.05
        elif vix_level < 15:  # 低VIX（安定）
            threshold_adj = -0.05  # より積極的
        else:
            threshold_adj = 0.0

        # ボラティリティベース調整
        volatility = market_context.get("volatility", 0.02)
        if volatility > 0.05:  # 高ボラティリティ
            threshold_adj += 0.05
        elif volatility < 0.01:  # 低ボラティリティ
            threshold_adj -= 0.02

        # 信頼度フィードバック調整
        if confidence_score is not None:
            if confidence_score > 0.8:  # 高信頼度
                threshold_adj -= 0.02  # より積極的
            elif confidence_score < 0.4:  # 低信頼度
                threshold_adj += 0.05  # より保守的

        # 最終閾値
        dynamic_threshold = base_threshold + threshold_adj
        return np.clip(dynamic_threshold, 0.3, 0.8)  # 範囲制限

    def assess_market_regime(
        self, market_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """市場レジーム評価"""
        if market_context is None:
            return "unknown"

        vix_level = market_context.get("vix_level", 20.0)
        volatility = market_context.get("volatility", 0.02)

        if vix_level > 35 or volatility > 0.06:
            return "crisis"
        elif vix_level > 25 or volatility > 0.04:
            return "volatile"
        elif vix_level < 15 and volatility < 0.02:
            return "calm"
        else:
            return "normal"

    def assess_risk_level(self, confidence_scores: Union[np.ndarray, float]) -> str:
        """リスクレベル評価"""
        if isinstance(confidence_scores, np.ndarray):
            avg_confidence = np.mean(confidence_scores)
        else:
            avg_confidence = confidence_scores

        self.confidence_stats["risk_assessments"] += 1

        if avg_confidence > 0.8:
            return "low"
        elif avg_confidence > 0.6:
            return "medium"
        elif avg_confidence > 0.4:
            return "high"
        else:
            return "very_high"

    def calculate_position_sizing(
        self,
        confidence_scores: Union[np.ndarray, float],
        market_context: Optional[Dict[str, Any]] = None,
        max_position_size: float = 0.15,
    ) -> float:
        """
        信頼度ベースポジションサイジング推奨計算

        Parameters:
        -----------
        confidence_scores : Union[np.ndarray, float]
            信頼度スコア
        market_context : Dict[str, Any], optional
            市場環境コンテキスト
        max_position_size : float
            最大ポジションサイズ

        Returns:
        --------
        float
            推奨ポジションサイズ（比率）
        """
        if isinstance(confidence_scores, np.ndarray):
            avg_confidence = np.mean(confidence_scores)
        else:
            avg_confidence = confidence_scores

        # 基本サイズ（信頼度ベース）
        base_size = avg_confidence * 0.1  # 最大10%

        # 市場環境調整
        if market_context:
            vix_level = market_context.get("vix_level", 20.0)
            if vix_level > 35:
                base_size *= 0.5  # 半分に削減
            elif vix_level < 15:
                base_size *= 1.2  # 20%増加

            # ボラティリティ調整
            volatility = market_context.get("volatility", 0.02)
            if volatility > 0.05:
                base_size *= 0.7  # 30%削減
            elif volatility < 0.01:
                base_size *= 1.1  # 10%増加

        return min(base_size, max_position_size)

    def calculate_exit_threshold(
        self,
        market_context: Optional[Dict[str, Any]] = None,
        confidence_score: Optional[float] = None,
    ) -> float:
        """動的エグジット閾値計算"""
        base_exit = 0.5

        if market_context is None:
            return base_exit

        # 市場レジームベース調整
        market_regime = self.assess_market_regime(market_context)
        if market_regime == "crisis":
            regime_adj = 0.15  # 早めのエグジット
        elif market_regime == "volatile":
            regime_adj = 0.1
        elif market_regime == "calm":
            regime_adj = -0.05  # 粘り強くホールド
        else:
            regime_adj = 0.0

        # 信頼度ベース調整
        if confidence_score is not None:
            confidence_adj = (
                1.0 - confidence_score
            ) * 0.1  # 低信頼度ほど早めにエグジット
        else:
            confidence_adj = 0.0

        return base_exit + regime_adj + confidence_adj

    def get_confidence_statistics(self) -> Dict[str, Any]:
        """信頼度計算統計取得"""
        return {
            "calculator_config": {
                "base_confidence_threshold": self.base_confidence_threshold,
                "risk_adjustment_enabled": self.risk_adjustment_enabled,
                "vix_adjustment_enabled": self.vix_adjustment_enabled,
            },
            "calculation_stats": self.confidence_stats.copy(),
            "vix_levels_config": self.vix_levels,
        }

    def reset_statistics(self):
        """統計リセット"""
        for key in self.confidence_stats:
            self.confidence_stats[key] = 0
        logger.info("📊 Confidence calculation statistics reset")


# グローバルユーティリティ関数


def calculate_ensemble_confidence(
    probabilities: np.ndarray,
    individual_predictions: Optional[List[np.ndarray]] = None,
    market_context: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """
    信頼度計算の簡易インターフェース

    Parameters:
    -----------
    probabilities : np.ndarray
        アンサンブル予測確率
    individual_predictions : List[np.ndarray], optional
        個別モデル予測リスト
    market_context : Dict[str, Any], optional
        市場環境コンテキスト
    config : Dict[str, Any], optional
        設定辞書

    Returns:
    --------
    np.ndarray
        信頼度スコア
    """
    calculator = EnsembleConfidenceCalculator(config)
    return calculator.calculate_prediction_confidence(
        probabilities, individual_predictions, market_context
    )


def calculate_timeframe_consensus(
    signal_values: List[float], weights: Optional[List[float]] = None
) -> float:
    """
    タイムフレーム合意度計算の簡易インターフェース

    Parameters:
    -----------
    signal_values : List[float]
        各タイムフレームのシグナル値
    weights : List[float], optional
        各タイムフレームの重み

    Returns:
    --------
    float
        合意度スコア
    """
    calculator = EnsembleConfidenceCalculator()
    return calculator.calculate_consensus_score(signal_values, weights)
