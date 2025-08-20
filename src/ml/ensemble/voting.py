"""
投票システム実装 - Phase 12実装・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応

重み付け投票とハード投票の実装。
アンサンブル学習における予測統合の核となるモジュール。

保守性を重視したシンプルで理解しやすい実装。.
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

import numpy as np

from ...core.exceptions import DataProcessingError
from ...core.logger import get_logger


class VotingMethod(Enum):
    """投票方式の列挙型."""

    SOFT = "soft"  # 確率ベースの投票
    HARD = "hard"  # クラスベースの投票
    WEIGHTED = "weighted"  # 重み付け投票


class VotingSystem:
    """
    投票システム

    複数モデルの予測を統合するための投票メカニズムを提供。
    ソフト投票とハード投票の両方に対応。.
    """

    def __init__(
        self,
        method: VotingMethod = VotingMethod.SOFT,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        投票システムの初期化

        Args:
            method: 投票方式（SOFT, HARD, WEIGHTED）
            weights: モデル重み辞書.
        """
        self.method = method
        self.weights = weights or {}
        self.logger = get_logger()

        self.logger.info(f"✅ VotingSystem initialized with method: {method.value}")

    def vote(
        self,
        predictions: Dict[str, np.ndarray],
        probabilities: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        投票の実行

        Args:
            predictions: モデル別予測クラス辞書
            probabilities: モデル別予測確率辞書（ソフト投票用）

        Returns:
            Tuple[np.ndarray, np.ndarray]: (最終予測, 信頼度スコア).
        """
        try:
            if self.method == VotingMethod.SOFT:
                return self._soft_voting(probabilities or {})
            elif self.method == VotingMethod.HARD:
                return self._hard_voting(predictions)
            elif self.method == VotingMethod.WEIGHTED:
                return self._weighted_voting(predictions, probabilities)
            else:
                raise ValueError(f"Unsupported voting method: {self.method}")

        except Exception as e:
            self.logger.error(f"Voting failed: {e}")
            raise DataProcessingError(f"Voting process failed: {e}")

    def _soft_voting(self, probabilities: Dict[str, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        ソフト投票（確率ベース）

        Args:
            probabilities: モデル別予測確率辞書

        Returns:
            Tuple[np.ndarray, np.ndarray]: (予測クラス, 信頼度).
        """
        if not probabilities:
            raise ValueError("Probabilities required for soft voting")

        # 確率の平均を計算
        avg_probabilities = self._average_probabilities(probabilities)

        # 最大確率のクラスを選択
        predictions = np.argmax(avg_probabilities, axis=1)

        # 信頼度（最大確率）を計算
        confidence = np.max(avg_probabilities, axis=1)

        self.logger.debug(f"Soft voting completed: {len(predictions)} predictions")
        return predictions, confidence

    def _hard_voting(self, predictions: Dict[str, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """
        ハード投票（多数決）

        Args:
            predictions: モデル別予測クラス辞書

        Returns:
            Tuple[np.ndarray, np.ndarray]: (予測クラス, 投票一致率).
        """
        if not predictions:
            raise ValueError("Predictions required for hard voting")

        # 予測を統合
        prediction_matrix = np.column_stack(list(predictions.values()))
        model_names = list(predictions.keys())

        final_predictions = []
        vote_agreement = []

        # 各サンプルについて多数決を実行
        for i in range(prediction_matrix.shape[0]):
            votes = prediction_matrix[i, :]

            # 重み付けありの場合
            if self.weights:
                weighted_votes = self._weighted_hard_vote(votes, model_names)
                final_pred = weighted_votes
            else:
                # 単純多数決
                final_pred = self._simple_majority_vote(votes)

            # 投票の一致率を計算
            agreement = np.sum(votes == final_pred) / len(votes)

            final_predictions.append(final_pred)
            vote_agreement.append(agreement)

        self.logger.debug(f"Hard voting completed: {len(final_predictions)} predictions")
        return np.array(final_predictions), np.array(vote_agreement)

    def _weighted_voting(
        self,
        predictions: Dict[str, np.ndarray],
        probabilities: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        重み付け投票

        Args:
            predictions: モデル別予測クラス辞書
            probabilities: モデル別予測確率辞書（利用可能な場合）

        Returns:
            Tuple[np.ndarray, np.ndarray]: (予測クラス, 重み付け信頼度).
        """
        if probabilities:
            # 確率が利用可能な場合はソフト投票を重み付け
            return self._weighted_soft_voting(probabilities)
        else:
            # 確率が利用不可能な場合はハード投票を重み付け
            return self._hard_voting(predictions)  # 重みはハード投票内で処理

    def _weighted_soft_voting(
        self, probabilities: Dict[str, np.ndarray]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        重み付けソフト投票

        Args:
            probabilities: モデル別予測確率辞書

        Returns:
            Tuple[np.ndarray, np.ndarray]: (予測クラス, 重み付け信頼度).
        """
        weighted_avg = self._average_probabilities(probabilities, use_weights=True)

        predictions = np.argmax(weighted_avg, axis=1)
        confidence = np.max(weighted_avg, axis=1)

        self.logger.debug("Weighted soft voting completed")
        return predictions, confidence

    def _average_probabilities(
        self, probabilities: Dict[str, np.ndarray], use_weights: bool = False
    ) -> np.ndarray:
        """
        確率の平均化

        Args:
            probabilities: モデル別予測確率辞書
            use_weights: 重みを使用するかどうか

        Returns:
            np.ndarray: 平均化された確率.
        """
        if not probabilities:
            raise ValueError("No probabilities provided")

        model_names = list(probabilities.keys())
        prob_arrays = list(probabilities.values())

        # 形状確認
        n_samples, n_classes = prob_arrays[0].shape
        for prob in prob_arrays[1:]:
            if prob.shape != (n_samples, n_classes):
                raise ValueError("All probability arrays must have the same shape")

        if use_weights and self.weights:
            # 重み付け平均
            weighted_sum = np.zeros((n_samples, n_classes))
            total_weight = 0.0

            for model_name, prob in probabilities.items():
                weight = self.weights.get(model_name, 1.0)
                weighted_sum += weight * prob
                total_weight += weight

            return weighted_sum / total_weight if total_weight > 0 else weighted_sum
        else:
            # 単純平均
            return np.mean(prob_arrays, axis=0)

    def _simple_majority_vote(self, votes: np.ndarray) -> int:
        """
        単純多数決

        Args:
            votes: 各モデルの投票

        Returns:
            int: 多数決の結果.
        """
        # 最頻値を取得
        unique_votes, counts = np.unique(votes, return_counts=True)
        majority_idx = np.argmax(counts)
        return unique_votes[majority_idx]

    def _weighted_hard_vote(self, votes: np.ndarray, model_names: List[str]) -> int:
        """
        重み付けハード投票

        Args:
            votes: 各モデルの投票
            model_names: モデル名リスト

        Returns:
            int: 重み付け投票の結果.
        """
        # クラス別の重み付け投票数を計算
        unique_classes = np.unique(votes)
        class_weights = {}

        for cls in unique_classes:
            total_weight = 0.0
            for i, vote in enumerate(votes):
                if vote == cls:
                    model_name = model_names[i]
                    weight = self.weights.get(model_name, 1.0)
                    total_weight += weight
            class_weights[cls] = total_weight

        # 最大重みのクラスを選択
        winning_class = max(class_weights, key=class_weights.get)
        return winning_class

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """
        重みの更新

        Args:
            new_weights: 新しい重み辞書.
        """
        old_weights = self.weights.copy()
        self.weights.update(new_weights)

        # 重みの正規化
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {name: weight / total_weight for name, weight in self.weights.items()}

        self.logger.info(f"Weights updated: {old_weights} -> {self.weights}")

    def get_voting_statistics(self, predictions: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        投票統計の取得

        Args:
            predictions: モデル別予測辞書

        Returns:
            Dict[str, float]: 投票統計.
        """
        try:
            if not predictions:
                return {}

            model_names = list(predictions.keys())
            prediction_matrix = np.column_stack(list(predictions.values()))
            n_samples, n_models = prediction_matrix.shape

            # 各ペアの一致率を計算
            agreement_rates = {}
            for i in range(n_models):
                for j in range(i + 1, n_models):
                    model_pair = f"{model_names[i]}-{model_names[j]}"
                    agreement = np.mean(prediction_matrix[:, i] == prediction_matrix[:, j])
                    agreement_rates[model_pair] = agreement

            # 全体の一致率
            unanimous_votes = np.sum(np.all(prediction_matrix == prediction_matrix[:, [0]], axis=1))
            unanimity_rate = unanimous_votes / n_samples

            # 多数決の信頼度
            majority_confidence = []
            for i in range(n_samples):
                votes = prediction_matrix[i, :]
                unique, counts = np.unique(votes, return_counts=True)
                max_count = np.max(counts)
                confidence = max_count / n_models
                majority_confidence.append(confidence)

            avg_majority_confidence = np.mean(majority_confidence)

            statistics = {
                "unanimity_rate": unanimity_rate,
                "avg_majority_confidence": avg_majority_confidence,
                "n_models": n_models,
                "n_samples": n_samples,
                **agreement_rates,
            }

            self.logger.debug(f"Voting statistics calculated: {len(statistics)} metrics")
            return statistics

        except Exception as e:
            self.logger.error(f"Failed to calculate voting statistics: {e}")
            return {}

    def analyze_disagreement(
        self,
        predictions: Dict[str, np.ndarray],
        confidence_threshold: float = 0.5,
    ) -> Dict[str, any]:
        """
        予測不一致の分析

        Args:
            predictions: モデル別予測辞書
            confidence_threshold: 信頼度閾値

        Returns:
            Dict[str, any]: 不一致分析結果.
        """
        try:
            if not predictions:
                return {}

            prediction_matrix = np.column_stack(list(predictions.values()))
            n_samples, n_models = prediction_matrix.shape

            # 不一致サンプルを特定
            disagreement_mask = ~np.all(prediction_matrix == prediction_matrix[:, [0]], axis=1)
            disagreement_indices = np.where(disagreement_mask)[0]

            # 低信頼度サンプルの特定（多数決での信頼度が低い）
            low_confidence_indices = []
            for i in range(n_samples):
                votes = prediction_matrix[i, :]
                unique, counts = np.unique(votes, return_counts=True)
                max_count = np.max(counts)
                confidence = max_count / n_models

                if confidence < confidence_threshold:
                    low_confidence_indices.append(i)

            analysis = {
                "n_disagreements": len(disagreement_indices),
                "disagreement_rate": len(disagreement_indices) / n_samples,
                "disagreement_indices": disagreement_indices.tolist(),
                "n_low_confidence": len(low_confidence_indices),
                "low_confidence_rate": len(low_confidence_indices) / n_samples,
                "low_confidence_indices": low_confidence_indices,
                "confidence_threshold": confidence_threshold,
            }

            self.logger.debug(
                f"Disagreement analysis completed: {analysis['disagreement_rate']:.3f} disagreement rate"
            )
            return analysis

        except Exception as e:
            self.logger.error(f"Failed to analyze disagreement: {e}")
            return {}

    def get_system_info(self) -> Dict[str, any]:
        """投票システム情報の取得."""
        return {
            "voting_method": self.method.value,
            "has_weights": bool(self.weights),
            "weights": self.weights.copy(),
            "n_weighted_models": len(self.weights) if self.weights else 0,
        }
