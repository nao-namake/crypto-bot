"""Phase 87 R4: confidence 計算の旧/新実装数値同一性検証 (H10 整合性基盤)

Phase 87 C2 で `confidence = float(np.max(ml_probabilities[-1]))` を
`get_predicted_class_proba()` ヘルパー経由に切り替えた。

旧実装は「最大確率」を返し、新実装は「予測クラスの確率」を返す。
正常な確率分布（要素 ≥ 0、合計 ≈ 1）ではこの2つは数学的に等価。
本テストはバックテスト履歴・ライブ運用ログとの後方互換性を保証する。
"""

import numpy as np
import pytest

from src.core.orchestration.ml_confidence import get_predicted_class_proba


def _old_max_confidence(probabilities: np.ndarray) -> float:
    """旧実装の confidence 計算（Phase 87 C2 直前まで使われていた式）"""
    last = probabilities[-1] if probabilities.ndim > 1 else probabilities
    return float(np.max(last))


class TestConfidenceBackwardCompat:
    """旧 np.max と 新 predicted_class_proba の数値同一性"""

    def test_binary_class_normal_distribution(self):
        """2クラス分類の典型的な分布で完全一致"""
        cases = [
            np.array([[0.3, 0.7]]),
            np.array([[0.9, 0.1]]),
            np.array([[0.55, 0.45]]),
            np.array([[0.01, 0.99]]),
        ]
        for probs in cases:
            old = _old_max_confidence(probs)
            _, new = get_predicted_class_proba(probs)
            assert new == pytest.approx(old), f"mismatch for {probs.tolist()}"

    def test_three_class_distribution(self):
        """3クラス分類でも完全一致"""
        cases = [
            np.array([[0.1, 0.7, 0.2]]),
            np.array([[0.6, 0.3, 0.1]]),
            np.array([[0.33, 0.34, 0.33]]),
        ]
        for probs in cases:
            old = _old_max_confidence(probs)
            _, new = get_predicted_class_proba(probs)
            assert new == pytest.approx(old)

    def test_1d_array_compatibility(self):
        """1D配列入力でも旧/新が一致"""
        probs = np.array([0.2, 0.8])
        old = _old_max_confidence(probs)
        _, new = get_predicted_class_proba(probs)
        assert new == pytest.approx(old)

    def test_multi_row_uses_last_only(self):
        """2D配列複数行でも最終行のみ使う点が共通"""
        probs = np.array(
            [
                [0.5, 0.5],  # 過去行
                [0.5, 0.5],  # 過去行
                [0.2, 0.8],  # 最終行（評価対象）
            ]
        )
        old = _old_max_confidence(probs)
        _, new = get_predicted_class_proba(probs)
        assert new == pytest.approx(old)
        assert new == pytest.approx(0.8)

    def test_edge_case_uniform_distribution(self):
        """均等分布（DummyModel が返す形）でも一致。

        argmax 先勝ちで class 0 が選ばれるが、確率値自体は np.max と同値。
        """
        probs = np.array([[0.5, 0.5]])
        old = _old_max_confidence(probs)
        cls, new = get_predicted_class_proba(probs)
        assert cls == 0  # 先勝ち
        assert new == pytest.approx(old)
        assert new == pytest.approx(0.5)

    def test_random_distributions_batch(self):
        """ランダムに生成した100件の確率分布で全件一致"""
        rng = np.random.default_rng(seed=42)
        for _ in range(100):
            raw = rng.random(size=3)
            probs = (raw / raw.sum()).reshape(1, 3)  # 正規化済み確率
            old = _old_max_confidence(probs)
            _, new = get_predicted_class_proba(probs)
            assert new == pytest.approx(old)
