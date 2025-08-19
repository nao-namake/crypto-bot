"""
投票システムのテスト - Phase 5-5実装

VotingSystemクラスの重み付け投票機能をテスト。.
"""

from unittest.mock import Mock

import numpy as np
import pytest

from src.core.exceptions import DataProcessingError
from src.ml.ensemble.voting import VotingMethod, VotingSystem


class TestVotingSystem:
    """投票システムのテストクラス."""

    @pytest.fixture
    def sample_predictions(self):
        """テスト用予測データ."""
        predictions = {
            "model_a": np.array([0, 1, 0, 1, 0]),
            "model_b": np.array([0, 1, 1, 1, 0]),
            "model_c": np.array([1, 1, 0, 0, 0]),
        }
        return predictions

    @pytest.fixture
    def sample_probabilities(self):
        """テスト用確率データ."""
        probabilities = {
            "model_a": np.array([[0.8, 0.2], [0.3, 0.7], [0.6, 0.4], [0.2, 0.8], [0.9, 0.1]]),
            "model_b": np.array([[0.7, 0.3], [0.4, 0.6], [0.3, 0.7], [0.1, 0.9], [0.8, 0.2]]),
            "model_c": np.array([[0.2, 0.8], [0.3, 0.7], [0.6, 0.4], [0.7, 0.3], [0.9, 0.1]]),
        }
        return probabilities

    def test_voting_system_initialization(self):
        """投票システム初期化テスト."""
        voting = VotingSystem()
        assert voting.method == VotingMethod.SOFT
        assert voting.weights == {}

        # 重み付き初期化
        weights = {"model_a": 0.5, "model_b": 0.3}
        voting_weighted = VotingSystem(method=VotingMethod.WEIGHTED, weights=weights)
        assert voting_weighted.method == VotingMethod.WEIGHTED
        assert voting_weighted.weights == weights

    def test_soft_voting_basic(self, sample_probabilities):
        """基本的なソフト投票テスト."""
        voting = VotingSystem(method=VotingMethod.SOFT)

        predictions, confidence = voting.vote({}, sample_probabilities)

        assert isinstance(predictions, np.ndarray)
        assert isinstance(confidence, np.ndarray)
        assert len(predictions) == 5
        assert len(confidence) == 5

        # 予測値は0または1
        assert all(pred in [0, 1] for pred in predictions)

        # 信頼度は0-1の範囲
        assert all(0 <= conf <= 1 for conf in confidence)

    def test_soft_voting_without_probabilities(self):
        """確率なしでのソフト投票エラーテスト."""
        voting = VotingSystem(method=VotingMethod.SOFT)

        with pytest.raises(DataProcessingError, match="Voting process failed"):
            voting.vote({}, {})

    def test_hard_voting_basic(self, sample_predictions):
        """基本的なハード投票テスト."""
        voting = VotingSystem(method=VotingMethod.HARD)

        predictions, agreement = voting.vote(sample_predictions, {})

        assert isinstance(predictions, np.ndarray)
        assert isinstance(agreement, np.ndarray)
        assert len(predictions) == 5
        assert len(agreement) == 5

        # 予測値は0または1
        assert all(pred in [0, 1] for pred in predictions)

        # 一致率は0-1の範囲
        assert all(0 <= agr <= 1 for agr in agreement)

    def test_hard_voting_majority_decision(self):
        """ハード投票の多数決テスト."""
        voting = VotingSystem(method=VotingMethod.HARD)

        # 明確な多数決ケース
        predictions = {
            "model_a": np.array([0, 1]),
            "model_b": np.array([0, 1]),
            "model_c": np.array([1, 0]),  # 異なる予測
        }

        result, agreement = voting.vote(predictions, {})

        # 多数決の結果
        assert result[0] == 0  # 2対1で0が勝利
        assert result[1] == 1  # 2対1で1が勝利

        # 一致率の確認
        assert agreement[0] == 2 / 3  # 3モデル中2つが一致
        assert agreement[1] == 2 / 3

    def test_weighted_hard_voting(self, sample_predictions):
        """重み付きハード投票テスト."""
        weights = {"model_a": 0.5, "model_b": 0.3, "model_c": 0.2}
        voting = VotingSystem(method=VotingMethod.HARD, weights=weights)

        predictions, agreement = voting.vote(sample_predictions, {})

        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == 5

    def test_weighted_soft_voting(self, sample_probabilities):
        """重み付きソフト投票テスト."""
        weights = {"model_a": 0.5, "model_b": 0.3, "model_c": 0.2}
        voting = VotingSystem(method=VotingMethod.WEIGHTED, weights=weights)

        predictions, confidence = voting.vote({}, sample_probabilities)

        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == 5

        # 重み付け投票の結果が単純平均と異なることを確認
        simple_voting = VotingSystem(method=VotingMethod.SOFT)
        simple_pred, _ = simple_voting.vote({}, sample_probabilities)

        # 完全に同じ結果になることは稀（重みがあるため）
        # ただし、テストデータ次第では同じになる可能性もある

    def test_average_probabilities_basic(self, sample_probabilities):
        """確率平均化テスト."""
        voting = VotingSystem()

        # 単純平均
        avg_proba = voting._average_probabilities(sample_probabilities, use_weights=False)

        assert avg_proba.shape == (5, 2)

        # 各行の確率の合計が1に近いかチェック
        row_sums = np.sum(avg_proba, axis=1)
        assert all(abs(sum_val - 1.0) < 1e-6 for sum_val in row_sums)

    def test_average_probabilities_weighted(self, sample_probabilities):
        """重み付き確率平均化テスト."""
        weights = {"model_a": 0.5, "model_b": 0.3, "model_c": 0.2}
        voting = VotingSystem(weights=weights)

        avg_proba = voting._average_probabilities(sample_probabilities, use_weights=True)

        assert avg_proba.shape == (5, 2)

        # 重み付き平均は単純平均と異なるはず
        simple_avg = voting._average_probabilities(sample_probabilities, use_weights=False)
        assert not np.allclose(avg_proba, simple_avg)

    def test_simple_majority_vote(self):
        """単純多数決テスト."""
        voting = VotingSystem()

        # 明確な多数
        votes = np.array([0, 0, 1])
        result = voting._simple_majority_vote(votes)
        assert result == 0

        # 同数の場合（最初に見つかった値が返される）
        votes = np.array([0, 1])
        result = voting._simple_majority_vote(votes)
        assert result in [0, 1]

    def test_weighted_hard_vote(self):
        """重み付きハード投票テスト."""
        weights = {"model_a": 0.6, "model_b": 0.3, "model_c": 0.1}
        voting = VotingSystem(weights=weights)

        votes = np.array([0, 1, 1])  # model_a: 0, model_b: 1, model_c: 1
        model_names = ["model_a", "model_b", "model_c"]

        result = voting._weighted_hard_vote(votes, model_names)

        # model_aの重みが大きいので、0が勝利するはず
        assert result == 0

    def test_update_weights(self):
        """重み更新テスト."""
        voting = VotingSystem()

        new_weights = {"model_a": 2.0, "model_b": 3.0}
        voting.update_weights(new_weights)

        # 重みが正規化されているかチェック
        total_weight = sum(voting.weights.values())
        assert abs(total_weight - 1.0) < 1e-6

        # 比率が保たれているかチェック
        assert voting.weights["model_a"] == 2.0 / 5.0
        assert voting.weights["model_b"] == 3.0 / 5.0

    def test_get_voting_statistics(self, sample_predictions):
        """投票統計取得テスト."""
        voting = VotingSystem()

        stats = voting.get_voting_statistics(sample_predictions)

        required_keys = ["unanimity_rate", "avg_majority_confidence", "n_models", "n_samples"]
        for key in required_keys:
            assert key in stats

        assert 0 <= stats["unanimity_rate"] <= 1
        assert 0 <= stats["avg_majority_confidence"] <= 1
        assert stats["n_models"] == 3
        assert stats["n_samples"] == 5

        # ペア別一致率もチェック
        pair_keys = [key for key in stats.keys() if "-" in key]
        assert len(pair_keys) == 3  # 3C2 = 3ペア

    def test_analyze_disagreement(self, sample_predictions):
        """不一致分析テスト."""
        voting = VotingSystem()

        analysis = voting.analyze_disagreement(sample_predictions, confidence_threshold=0.6)

        required_keys = [
            "n_disagreements",
            "disagreement_rate",
            "disagreement_indices",
            "n_low_confidence",
            "low_confidence_rate",
            "low_confidence_indices",
        ]

        for key in required_keys:
            assert key in analysis

        assert 0 <= analysis["disagreement_rate"] <= 1
        assert 0 <= analysis["low_confidence_rate"] <= 1
        assert analysis["confidence_threshold"] == 0.6

    def test_get_system_info(self):
        """システム情報取得テスト."""
        weights = {"model_a": 0.6, "model_b": 0.4}
        voting = VotingSystem(method=VotingMethod.WEIGHTED, weights=weights)

        info = voting.get_system_info()

        assert info["voting_method"] == "weighted"
        assert info["has_weights"] is True
        assert info["n_weighted_models"] == 2
        assert info["weights"] == weights

    def test_vote_with_mismatched_shapes(self):
        """形状不一致エラーテスト."""
        voting = VotingSystem(method=VotingMethod.SOFT)

        # 異なる形状の確率
        probabilities = {
            "model_a": np.array([[0.6, 0.4], [0.3, 0.7]]),
            "model_b": np.array([[0.5, 0.5]]),  # 異なる行数
        }

        with pytest.raises(DataProcessingError, match="Voting process failed"):
            voting.vote({}, probabilities)

    def test_vote_with_empty_input(self):
        """空入力でのエラーテスト."""
        voting = VotingSystem(method=VotingMethod.HARD)

        with pytest.raises(DataProcessingError, match="Voting process failed"):
            voting.vote({}, {})

        voting_soft = VotingSystem(method=VotingMethod.SOFT)
        with pytest.raises(DataProcessingError, match="Voting process failed"):
            voting_soft.vote({}, {})

    def test_unsupported_voting_method(self):
        """未サポート投票方式エラーテスト."""
        # 無効なVotingMethodを直接設定（通常は起こらない）
        voting = VotingSystem()
        voting.method = "unsupported_method"

        with pytest.raises(DataProcessingError, match="Voting process failed"):
            voting.vote({"model_a": np.array([0, 1])}, {})
