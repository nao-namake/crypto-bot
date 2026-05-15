"""
Phase 89-γ: HMMRegimeClassifier テスト 8 件
"""

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("hmmlearn")

from src.core.services.hmm_regime_classifier import HMMRegimeClassifier, has_hmmlearn


@pytest.fixture
def training_data():
    """3 つのレジームを混合した学習データ（500 サンプル）."""
    rng = np.random.default_rng(42)
    n_per_regime = 167
    # bear: 負のリターン + 高 ATR
    bear = pd.DataFrame(
        {
            "returns_1": rng.normal(-0.005, 0.01, n_per_regime),
            "atr_14": rng.normal(0.02, 0.005, n_per_regime),
            "volume_ratio": rng.normal(1.5, 0.3, n_per_regime),
        }
    )
    # sideways: ニュートラル + 低 ATR
    sideways = pd.DataFrame(
        {
            "returns_1": rng.normal(0.0, 0.002, n_per_regime),
            "atr_14": rng.normal(0.005, 0.001, n_per_regime),
            "volume_ratio": rng.normal(1.0, 0.1, n_per_regime),
        }
    )
    # bull: 正のリターン + 中 ATR
    bull = pd.DataFrame(
        {
            "returns_1": rng.normal(0.005, 0.01, n_per_regime),
            "atr_14": rng.normal(0.015, 0.003, n_per_regime),
            "volume_ratio": rng.normal(1.3, 0.25, n_per_regime),
        }
    )
    return pd.concat([bear, sideways, bull], ignore_index=True)


def test_has_hmmlearn_when_installed():
    assert has_hmmlearn() is True


def test_fit_offline_learns_three_states(training_data):
    clf = HMMRegimeClassifier(n_states=3, random_state=42, n_iter=50)
    clf.fit_offline(training_data, min_samples=100)
    assert clf.is_fitted is True
    assert clf.model is not None


def test_predict_proba_shape_and_sum_to_one(training_data):
    """predict_proba は (n_samples, n_states) で各行 sum=1.0."""
    clf = HMMRegimeClassifier(n_states=3, n_iter=30)
    clf.fit_offline(training_data, min_samples=100)
    probas = clf.predict_proba(training_data.iloc[:50])
    assert probas.shape == (50, 3)
    assert np.allclose(probas.sum(axis=1), 1.0, atol=1e-6)


def test_predict_proba_before_fit_returns_uniform():
    """fit 前は uniform 確率を返す（fail-open）."""
    clf = HMMRegimeClassifier(n_states=3)
    df = pd.DataFrame(
        {
            "returns_1": [0.001, 0.002, 0.003],
            "atr_14": [0.01, 0.01, 0.01],
            "volume_ratio": [1.0, 1.1, 1.2],
        }
    )
    probas = clf.predict_proba(df)
    assert probas.shape == (3, 3)
    assert np.allclose(probas, 1.0 / 3)


def test_fit_offline_raises_on_insufficient_samples():
    """min_samples 未満で fit_offline は ValueError."""
    clf = HMMRegimeClassifier(n_states=3)
    df = pd.DataFrame(
        {"returns_1": [0.01] * 50, "atr_14": [0.01] * 50, "volume_ratio": [1.0] * 50}
    )
    with pytest.raises(ValueError, match="HMM 学習には最低"):
        clf.fit_offline(df, min_samples=100)


def test_missing_features_raise(training_data):
    """入力 DF に必要列が無いと ValueError."""
    clf = HMMRegimeClassifier(n_states=3)
    df_missing = training_data.drop(columns=["volume_ratio"])
    with pytest.raises(ValueError, match="HMM 入力特徴量不足"):
        clf._extract_features(df_missing)


def test_save_and_load_roundtrip(training_data, tmp_path):
    """save → load で予測が一致する."""
    clf = HMMRegimeClassifier(n_states=3, n_iter=30)
    clf.fit_offline(training_data, min_samples=100)
    test_df = training_data.iloc[:20]
    original = clf.predict_proba(test_df)

    path = tmp_path / "hmm.pkl"
    clf.save(str(path))

    clf2 = HMMRegimeClassifier(n_states=3)
    clf2.load(str(path))
    loaded = clf2.predict_proba(test_df)

    assert np.allclose(original, loaded, atol=1e-6)


def test_nan_inputs_handled_via_zero_fill(training_data):
    """NaN 含む入力でもエラーなく予測（nan_to_num で 0 fill）."""
    clf = HMMRegimeClassifier(n_states=3, n_iter=30)
    clf.fit_offline(training_data, min_samples=100)
    df_with_nan = pd.DataFrame(
        {
            "returns_1": [0.001, np.nan, 0.003],
            "atr_14": [0.01, 0.01, np.nan],
            "volume_ratio": [1.0, 1.1, 1.2],
        }
    )
    probas = clf.predict_proba(df_with_nan)
    assert probas.shape == (3, 3)
    assert not np.any(np.isnan(probas))
