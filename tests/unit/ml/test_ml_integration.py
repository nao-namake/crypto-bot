"""
ML層統合テスト - Phase 64.6更新

ProductionEnsembleの統合テスト。
実際の使用パターンに近い統合テスト。
"""

import numpy as np
import pandas as pd
import pytest

from src.ml import ProductionEnsemble
from src.ml.models import LGBMModel, RFModel, XGBModel


class TestMLIntegration:
    """ML層統合テストクラス."""

    @pytest.fixture
    def sample_dataset(self):
        """テスト用データセット."""
        np.random.seed(42)
        n_samples = 200
        n_features = 12

        feature_names = [
            "close",
            "volume",
            "returns_1",
            "rsi_14",
            "macd",
            "macd_signal",
            "atr_14",
            "bb_position",
            "ema_20",
            "ema_50",
            "zscore",
            "volume_ratio",
        ]

        X = pd.DataFrame(np.random.randn(n_samples, n_features), columns=feature_names)

        # 3クラス分類対応 - クラス不均衡を模擬
        y = pd.Series(np.random.choice([0, 1, 2], n_samples, p=[0.2, 0.6, 0.2]))

        return X, y

    def test_individual_models_train_and_predict(self, sample_dataset):
        """個別モデルの学習・予測テスト."""
        X, y = sample_dataset

        for ModelClass in [LGBMModel, XGBModel, RFModel]:
            model = ModelClass()
            model.fit(X, y)

            assert model.is_fitted

            predictions = model.predict(X)
            probabilities = model.predict_proba(X)

            assert len(predictions) == len(X)
            assert probabilities.shape == (len(X), 3)

    def test_production_ensemble_with_trained_models(self, sample_dataset):
        """ProductionEnsembleでの学習済みモデル統合テスト."""
        X, y = sample_dataset

        # 個別モデルを学習
        lgbm = LGBMModel()
        lgbm.fit(X, y)

        xgb = XGBModel()
        xgb.fit(X, y)

        rf = RFModel()
        rf.fit(X, y)

        # ProductionEnsembleに統合
        models = {
            "lightgbm": lgbm.estimator,
            "xgboost": xgb.estimator,
            "random_forest": rf.estimator,
        }
        ensemble = ProductionEnsemble(models)

        # 予測実行
        predictions = ensemble.predict(X)
        probabilities = ensemble.predict_proba(X)

        assert len(predictions) == len(X)
        assert probabilities.shape == (len(X), 3)

        # 確率の合計が1に近い
        assert np.allclose(probabilities.sum(axis=1), 1.0, rtol=1e-6)

    def test_feature_importance_analysis(self, sample_dataset):
        """特徴量重要度分析テスト."""
        X, y = sample_dataset

        lgbm = LGBMModel()
        lgbm.fit(X, y)

        importance = lgbm.get_feature_importance()
        assert importance is not None
        assert len(importance) == len(X.columns)
