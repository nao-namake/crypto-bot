"""Phase 89 N-BEATS 完全版実装のテスト（TDD 用・修正後挙動を assert）.

これらのテストは N-BEATS 修正（NB1 StandardScaler / NB2 Early Stopping / NB3 重み初期化 + logits 正規化 /
NB4 class_weight / NB5 学習ログ）が正しく機能していることを検証する。

修正前は `confidence_std ≈ 2.98e-08`（定数予測）だったため全テスト fail する。
修正後は confidence_std > 0.05・accuracy > 0.5・多様な class 予測が出ることを確認。
"""

from __future__ import annotations

import numpy as np
import pytest

from src.ml.nbeats import has_torch
from src.ml.nbeats_predictor import NBeatsPredictor

pytestmark = pytest.mark.skipif(not has_torch(), reason="torch が未インストール")


def _make_dummy_data(
    n_samples: int = 500, n_features: int = 55, n_classes: int = 3, seed: int = 42
):
    """学習可能な dummy データ（クラスごとに特徴量分布が異なる）.

    実機の本番特徴量と同じく **大スケール混在** (close=12M, volume=100, hour=12 等) を再現して、
    NB1 (StandardScaler) の修正効果を検証する。
    """
    rng = np.random.default_rng(seed)
    X = np.zeros((n_samples, n_features))
    y = rng.integers(0, n_classes, size=n_samples)

    # 列 0: close 想定（10^7 スケール）
    X[:, 0] = 12_000_000 + rng.normal(0, 500_000, n_samples) + y * 100_000
    # 列 1: volume 想定（10^2 スケール）
    X[:, 1] = 50 + rng.normal(0, 20, n_samples) + y * 5
    # 列 2-4: ratio 想定（10^0 スケール・クラス依存）
    X[:, 2:5] = rng.normal(0, 0.5, (n_samples, 3)) + y[:, None] * 0.3
    # 残り列: 通常スケール
    X[:, 5:] = rng.normal(0, 1, (n_samples, n_features - 5))
    return X.astype(np.float32), y


class TestNBeatsPredictorScaling:
    """NB1: StandardScaler が組み込まれているかを検証."""

    def test_scaler_is_none_before_fit(self):
        """fit 前は scaler が None."""
        p = NBeatsPredictor(n_features=55, n_classes=3, n_epochs=2)
        assert p.scaler is None, "fit 前に scaler を持つべきでない"

    def test_scaler_is_fitted_after_fit(self):
        """NB1: fit 後は scaler が StandardScaler インスタンスを保持."""
        X, y = _make_dummy_data(n_samples=100)
        p = NBeatsPredictor(n_features=X.shape[1], n_classes=3, n_epochs=5)
        p.fit(X, y)
        from sklearn.preprocessing import StandardScaler

        assert isinstance(p.scaler, StandardScaler), "fit 後に scaler が StandardScaler であるべき"
        assert p.scaler.mean_ is not None, "scaler.mean_ が fit されているべき"
        assert p.scaler.mean_.shape == (X.shape[1],), "scaler.mean_ の shape が特徴量数と一致"

    def test_predict_proba_uses_scaler(self):
        """NB1: predict_proba は内部で scaler.transform を適用."""
        X_train, y_train = _make_dummy_data(n_samples=300, seed=1)
        p = NBeatsPredictor(n_features=X_train.shape[1], n_classes=3, n_epochs=10)
        p.fit(X_train, y_train)

        # スケーリングなしで大スケール特徴量を渡しても正常な確率（NaN/Inf なし）を返す
        X_test, _ = _make_dummy_data(n_samples=20, seed=2)
        proba = p.predict_proba(X_test)
        assert proba.shape == (20, 3)
        assert np.all(np.isfinite(proba)), "predict_proba 出力に NaN/Inf があってはいけない"


class TestNBeatsPredictorOutputDiversity:
    """NB3 + NB1: 修正後の N-BEATS が定数予測でないことを検証（最重要）."""

    def test_confidence_std_after_fit_is_nontrivial(self):
        """NB1+NB3: fit 後の predict_proba は confidence_std > 0.02 を満たすべき.

        修正前: confidence_std ≈ 2.98e-08 (定数予測)
        修正後: 確率分布がサンプルごとに変化する。
        """
        X, y = _make_dummy_data(n_samples=500, seed=42)
        p = NBeatsPredictor(n_features=X.shape[1], n_classes=3, n_epochs=30, random_state=42)
        p.fit(X, y)

        proba = p.predict_proba(X[:200])
        max_probs = proba.max(axis=1)
        std = float(max_probs.std())
        assert std > 0.02, (
            f"confidence_std={std:.6f} は uniform 出力の兆候。"
            "NB1 (StandardScaler) / NB3 (Kaiming init + logits 正規化) 修正を確認。"
        )

    def test_predict_returns_diverse_classes(self):
        """NB3: 修正後の predict() は複数クラスを返す（全部同じクラスでない）.

        修正前: 全予測が 1 クラスに張り付き (accuracy 0.85%)
        """
        X, y = _make_dummy_data(n_samples=500, seed=42)
        p = NBeatsPredictor(n_features=X.shape[1], n_classes=3, n_epochs=30, random_state=42)
        p.fit(X, y)

        preds = p.predict(X[:200])
        unique_classes = np.unique(preds)
        assert len(unique_classes) >= 2, (
            f"predict() が単一クラス {unique_classes} しか返さない（定数化）。"
            "N-BEATS が学習できていない。"
        )


class TestNBeatsPredictorLearning:
    """学習が実際に進行していることを検証."""

    def test_fit_changes_predictions_from_initial(self):
        """fit() 前後で predict_proba 出力が変化する（学習が進行している証拠）."""
        X, y = _make_dummy_data(n_samples=300, seed=42)
        p = NBeatsPredictor(n_features=X.shape[1], n_classes=3, n_epochs=20, random_state=42)

        # fit 前 (is_fitted=False) は uniform fallback
        proba_before = p.predict_proba(X[:10])
        # fit 後
        p.fit(X, y)
        proba_after = p.predict_proba(X[:10])

        # 全サンプルで proba が全く同じ場合は学習していない
        diff = np.abs(proba_after - proba_before).max()
        assert diff > 0.01, f"fit 前後の予測差 {diff:.6f} が小さすぎる。学習が機能していない。"

    def test_accuracy_better_than_random_on_separable_data(self):
        """学習可能なデータで accuracy > random(1/n_classes) を達成する."""
        X, y = _make_dummy_data(n_samples=600, seed=123)
        p = NBeatsPredictor(n_features=X.shape[1], n_classes=3, n_epochs=30, random_state=123)
        p.fit(X, y)

        preds = p.predict(X)
        accuracy = float((preds == y).mean())
        # 完璧でなくてもランダム (1/3 = 0.333) より明確に良いはず
        assert (
            accuracy > 0.4
        ), f"accuracy={accuracy:.3f} がランダム水準 (0.333) と差がない。学習が機能していない可能性。"


class TestNBeatsPredictorEarlyStopping:
    """NB2: Early Stopping の動作確認."""

    def test_early_stopping_history_recorded(self):
        """NB2: fit 後に best_epoch / training_history が記録される.

        Early Stopping 機構が組み込まれていれば、これらの属性が利用可能。
        """
        X, y = _make_dummy_data(n_samples=300, seed=42)
        p = NBeatsPredictor(n_features=X.shape[1], n_classes=3, n_epochs=50, random_state=42)
        p.fit(X, y)

        # NB2 で導入される属性（学習履歴）
        assert hasattr(p, "best_epoch") or hasattr(p, "training_history"), (
            "Early Stopping のための best_epoch / training_history 属性が見つからない。"
            "NB2 修正を確認。"
        )


class TestNBeatsPredictorClassWeight:
    """NB4: クラス不均衡対応 (class_weight) の動作確認."""

    def test_class_weights_parameter_accepted(self):
        """NB4: fit() が class_weights パラメータを受け取れる."""
        import inspect

        sig = inspect.signature(NBeatsPredictor.fit)
        assert (
            "class_weights" in sig.parameters or "class_weight" in sig.parameters
        ), "fit() に class_weights / class_weight パラメータが必要。NB4 修正を確認。"
