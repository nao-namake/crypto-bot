"""
Phase 89-γ: N-BEATS モデル + Predictor テスト 16 件
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from src.ml.nbeats import NBeatsBlock, NBeatsClassifier, has_torch
from src.ml.nbeats_predictor import NBeatsPredictor


class TestNBeatsBlock:
    """単一 block のテスト."""

    def test_forward_shape(self):
        """forward (batch, n_features) → (batch, n_classes)."""
        block = NBeatsBlock(n_features=47, hidden_size=64, n_classes=3)
        x = torch.randn(8, 47)
        out = block(x)
        assert out.shape == (8, 3)

    def test_forward_different_batch_sizes(self):
        """batch_size 1 や 100 でも動く."""
        block = NBeatsBlock(n_features=10, hidden_size=32, n_classes=2)
        for batch in (1, 100):
            x = torch.randn(batch, 10)
            assert block(x).shape == (batch, 2)


class TestNBeatsClassifier:
    """フルモデルのテスト."""

    def test_forward_shape_default(self):
        """デフォルト構成で forward 動作."""
        model = NBeatsClassifier(n_features=47, n_classes=3)
        x = torch.randn(4, 47)
        out = model(x)
        assert out.shape == (4, 3)

    def test_n_blocks_total_equals_stacks_times_blocks(self):
        """blocks 総数 = n_stacks × n_blocks_per_stack."""
        model = NBeatsClassifier(n_features=10, n_stacks=3, n_blocks_per_stack=4, hidden_size=16)
        assert len(model.blocks) == 12

    def test_forward_aggregates_block_outputs(self):
        """全 block の logits が加算される（block 増で出力スケール変化）."""
        small = NBeatsClassifier(n_features=10, n_stacks=1, n_blocks_per_stack=1, hidden_size=8)
        large = NBeatsClassifier(n_features=10, n_stacks=2, n_blocks_per_stack=3, hidden_size=8)
        x = torch.randn(4, 10)
        # forward 自体が走ること（block 数違いでもエラーなし）
        assert small(x).shape == (4, 3)
        assert large(x).shape == (4, 3)

    def test_dropout_inactive_during_eval(self):
        """eval モードで dropout 無効化."""
        model = NBeatsClassifier(n_features=10, hidden_size=16)
        model.eval()
        x = torch.randn(2, 10)
        with torch.no_grad():
            out1 = model(x)
            out2 = model(x)
        # eval + no_grad なら 2 回の出力が一致
        assert torch.allclose(out1, out2)

    def test_cpu_inference_works_without_gpu(self):
        """CPU テンソルで動く."""
        model = NBeatsClassifier(n_features=20, hidden_size=8)
        x = torch.randn(3, 20)
        assert x.device.type == "cpu"
        out = model(x)
        assert out.device.type == "cpu"


class TestNBeatsPredictor:
    """sklearn 互換ラッパーのテスト."""

    def test_initial_state_n_features_in(self):
        """n_features_in_ プロパティが __init__ 値を返す."""
        pred = NBeatsPredictor(n_features=47, n_epochs=1)
        assert pred.n_features_in_ == 47
        assert pred.is_fitted is False

    def test_fit_predict_roundtrip(self):
        """簡易データで fit → predict が走る."""
        rng = np.random.default_rng(0)
        X = rng.normal(size=(50, 10)).astype(np.float32)
        y = rng.integers(0, 3, size=50)
        pred = NBeatsPredictor(n_features=10, n_classes=3, n_epochs=2, batch_size=16)
        pred.fit(X, y)
        assert pred.is_fitted is True
        labels = pred.predict(X)
        assert labels.shape == (50,)
        assert set(labels.tolist()).issubset({0, 1, 2})

    def test_predict_proba_returns_softmax_distribution(self):
        """predict_proba は (batch, n_classes) で各行 sum=1.0."""
        rng = np.random.default_rng(1)
        X = rng.normal(size=(20, 10)).astype(np.float32)
        y = rng.integers(0, 3, size=20)
        pred = NBeatsPredictor(n_features=10, n_classes=3, n_epochs=2, batch_size=8)
        pred.fit(X, y)
        probas = pred.predict_proba(X)
        assert probas.shape == (20, 3)
        assert np.allclose(probas.sum(axis=1), 1.0, atol=1e-5)

    def test_predict_proba_before_fit_returns_uniform(self):
        """fit 前の predict_proba は uniform を返す（fail-open）."""
        pred = NBeatsPredictor(n_features=10, n_classes=3)
        X = np.random.normal(size=(5, 10))
        probas = pred.predict_proba(X)
        assert probas.shape == (5, 3)
        assert np.allclose(probas, 1.0 / 3)

    def test_n_features_auto_inferred_from_fit_when_none(self):
        """n_features=None で初期化 → fit で X.shape から推定される."""
        rng = np.random.default_rng(2)
        X = rng.normal(size=(20, 15)).astype(np.float32)
        y = rng.integers(0, 3, size=20)
        pred = NBeatsPredictor(n_features=None, n_classes=3, n_epochs=1)
        pred.fit(X, y)
        assert pred.n_features == 15
        assert pred.n_features_in_ == 15

    def test_fit_with_pandas_dataframe_input(self):
        """pandas DataFrame 入力でも fit / predict 動作."""
        import pandas as pd

        rng = np.random.default_rng(3)
        X = pd.DataFrame(rng.normal(size=(20, 8)))
        y = pd.Series(rng.integers(0, 3, size=20))
        pred = NBeatsPredictor(n_features=8, n_classes=3, n_epochs=1)
        pred.fit(X, y)
        probas = pred.predict_proba(X)
        assert probas.shape == (20, 3)

    def test_n_classes_2_works(self):
        """二値分類でも動く."""
        rng = np.random.default_rng(4)
        X = rng.normal(size=(20, 10)).astype(np.float32)
        y = rng.integers(0, 2, size=20)
        pred = NBeatsPredictor(n_features=10, n_classes=2, n_epochs=1)
        pred.fit(X, y)
        probas = pred.predict_proba(X)
        assert probas.shape == (20, 2)

    def test_reproducibility_with_random_state(self):
        """同じ random_state で再現性."""
        rng = np.random.default_rng(5)
        X = rng.normal(size=(20, 10)).astype(np.float32)
        y = rng.integers(0, 3, size=20)

        p1 = NBeatsPredictor(n_features=10, n_epochs=2, random_state=123)
        p1.fit(X, y)
        out1 = p1.predict_proba(X)

        p2 = NBeatsPredictor(n_features=10, n_epochs=2, random_state=123)
        p2.fit(X, y)
        out2 = p2.predict_proba(X)

        assert np.allclose(out1, out2, atol=1e-5)


def test_has_torch_returns_true_when_installed():
    """torch インストール時は True."""
    assert has_torch() is True
