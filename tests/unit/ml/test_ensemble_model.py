"""
アンサンブルモデルのテスト - Phase 5-5実装

EnsembleModelクラスの主要機能をテスト。
保守性を重視したシンプルなテスト設計。.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.exceptions import DataProcessingError
from src.ml.ensemble.ensemble_model import EnsembleModel
from src.ml.models import LGBMModel, RFModel, XGBModel


class TestEnsembleModel:
    """アンサンブルモデルのテストクラス."""

    @pytest.fixture
    def sample_data(self):
        """テスト用サンプルデータ."""
        np.random.seed(42)
        n_samples = 100
        n_features = 12

        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f"feature_{i}" for i in range(n_features)],
        )
        y = pd.Series(np.random.randint(0, 2, n_samples))

        return X, y

    @pytest.fixture
    def ensemble_model(self):
        """テスト用アンサンブルモデル."""
        return EnsembleModel(confidence_threshold=0.35)

    def test_ensemble_model_initialization(self):
        """アンサンブルモデルの初期化テスト."""
        ensemble = EnsembleModel()

        assert len(ensemble.models) == 3
        assert "lgbm" in ensemble.models
        assert "xgb" in ensemble.models
        assert "rf" in ensemble.models

        assert ensemble.confidence_threshold == 0.35
        assert not ensemble.is_fitted
        assert ensemble.feature_names is None

    def test_custom_weights_initialization(self):
        """カスタム重みでの初期化テスト."""
        weights = {"lgbm": 0.5, "xgb": 0.3, "rf": 0.2}
        ensemble = EnsembleModel(weights=weights)

        # 重みが正規化されているかチェック
        total_weight = sum(ensemble.weights.values())
        assert abs(total_weight - 1.0) < 1e-6

        # 比率が保たれているかチェック
        assert ensemble.weights["lgbm"] > ensemble.weights["xgb"]
        assert ensemble.weights["xgb"] > ensemble.weights["rf"]

    def test_fit_basic(self, ensemble_model, sample_data):
        """基本的な学習テスト."""
        X, y = sample_data

        result = ensemble_model.fit(X, y)

        assert result is ensemble_model  # メソッドチェーン
        assert ensemble_model.is_fitted
        assert ensemble_model.feature_names == X.columns.tolist()
        assert len(ensemble_model.classes_) == 2
        assert len(ensemble_model.model_performance) == 3

    def test_fit_with_insufficient_data(self, ensemble_model):
        """不十分なデータでの学習エラーテスト."""
        X = pd.DataFrame(np.random.randn(10, 5))  # 50サンプル未満
        y = pd.Series(np.random.randint(0, 2, 10))

        with pytest.raises(DataProcessingError, match="Ensemble training failed"):
            ensemble_model.fit(X, y)

    def test_fit_with_mismatched_data(self, ensemble_model):
        """データサイズ不一致エラーテスト."""
        X = pd.DataFrame(np.random.randn(100, 5))
        y = pd.Series(np.random.randint(0, 2, 50))  # 異なるサイズ

        with pytest.raises(DataProcessingError, match="Ensemble training failed"):
            ensemble_model.fit(X, y)

    def test_predict_without_fit(self, ensemble_model, sample_data):
        """未学習での予測エラーテスト."""
        X, _ = sample_data

        with pytest.raises(ValueError, match="not fitted"):
            ensemble_model.predict(X)

    def test_predict_proba_without_fit(self, ensemble_model, sample_data):
        """未学習での確率予測エラーテスト."""
        X, _ = sample_data

        with pytest.raises(ValueError, match="not fitted"):
            ensemble_model.predict_proba(X)

    def test_predict_basic(self, ensemble_model, sample_data):
        """基本的な予測テスト."""
        X, y = sample_data
        ensemble_model.fit(X, y)

        predictions = ensemble_model.predict(X)

        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == len(X)
        assert all(pred in [-1, 0, 1] for pred in predictions)  # -1は低信頼度

    def test_predict_without_confidence(self, ensemble_model, sample_data):
        """信頼度閾値なしの予測テスト."""
        X, y = sample_data
        ensemble_model.fit(X, y)

        predictions = ensemble_model.predict(X, use_confidence=False)

        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == len(X)
        assert all(pred in [0, 1] for pred in predictions)  # 0または1のみ

    def test_predict_proba_basic(self, ensemble_model, sample_data):
        """基本的な確率予測テスト."""
        X, y = sample_data
        ensemble_model.fit(X, y)

        probabilities = ensemble_model.predict_proba(X)

        assert isinstance(probabilities, np.ndarray)
        assert probabilities.shape == (len(X), 2)
        assert all(0 <= prob <= 1 for row in probabilities for prob in row)

        # 各行の確率の合計が1に近いかチェック
        row_sums = np.sum(probabilities, axis=1)
        assert all(abs(sum_val - 1.0) < 1e-6 for sum_val in row_sums)

    def test_evaluate(self, ensemble_model, sample_data):
        """評価機能テスト."""
        X, y = sample_data
        ensemble_model.fit(X, y)

        metrics = ensemble_model.evaluate(X, y)

        required_metrics = ["accuracy", "precision", "recall", "f1_score"]
        for metric in required_metrics:
            assert metric in metrics
            assert 0 <= metrics[metric] <= 1

        # confidence閾値ありの場合の追加メトリクス
        assert "confidence_coverage" in metrics
        assert "confidence_accuracy" in metrics

    def test_get_feature_importance(self, ensemble_model, sample_data):
        """特徴量重要度取得テスト."""
        X, y = sample_data
        ensemble_model.fit(X, y)

        importance_df = ensemble_model.get_feature_importance()

        if importance_df is not None:
            assert isinstance(importance_df, pd.DataFrame)
            assert "feature" in importance_df.columns
            assert "importance" in importance_df.columns
            assert len(importance_df) == len(X.columns)

            # 重要度順にソートされているかチェック
            importances = importance_df["importance"].values
            assert all(importances[i] >= importances[i + 1] for i in range(len(importances) - 1))

    def test_save_and_load_model(self, ensemble_model, sample_data):
        """モデル保存・読み込みテスト."""
        X, y = sample_data
        ensemble_model.fit(X, y)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "test_ensemble"

            # 保存
            ensemble_model.save(save_path)
            assert save_path.exists()

            # 読み込み
            loaded_ensemble = EnsembleModel.load(save_path)

            assert loaded_ensemble.is_fitted
            assert loaded_ensemble.feature_names == ensemble_model.feature_names
            assert loaded_ensemble.confidence_threshold == ensemble_model.confidence_threshold

            # 予測結果の一致確認
            original_pred = ensemble_model.predict_proba(X)
            loaded_pred = loaded_ensemble.predict_proba(X)

            assert np.allclose(original_pred, loaded_pred, rtol=1e-5)

    def test_get_model_info(self, ensemble_model, sample_data):
        """モデル情報取得テスト."""
        info = ensemble_model.get_model_info()

        required_keys = [
            "ensemble_type",
            "n_models",
            "model_names",
            "weights",
            "confidence_threshold",
            "is_fitted",
        ]

        for key in required_keys:
            assert key in info

        assert info["ensemble_type"] == "soft_voting"
        assert info["n_models"] == 3
        assert info["model_names"] == ["lgbm", "xgb", "rf"]
        assert not info["is_fitted"]

        # 学習後の情報確認
        X, y = sample_data
        ensemble_model.fit(X, y)
        info_fitted = ensemble_model.get_model_info()

        assert info_fitted["is_fitted"]
        assert info_fitted["n_features"] == len(X.columns)
        assert info_fitted["feature_names"] == X.columns.tolist()

    @patch("src.ml.models.lgbm_model.LGBMModel")
    @patch("src.ml.models.xgb_model.XGBModel")
    @patch("src.ml.models.rf_model.RFModel")
    def test_model_failure_handling(self, mock_rf, mock_xgb, mock_lgbm, sample_data):
        """個別モデルの失敗処理テスト."""
        X, y = sample_data

        # 1つのモデルで例外を発生させる
        mock_lgbm_instance = Mock()
        mock_lgbm_instance.fit.side_effect = Exception("LGBM failed")
        mock_lgbm.return_value = mock_lgbm_instance

        # 正常なモデル
        mock_xgb_instance = Mock()
        mock_xgb_instance.fit.return_value = mock_xgb_instance
        mock_xgb_instance.is_fitted = True
        mock_xgb.return_value = mock_xgb_instance

        mock_rf_instance = Mock()
        mock_rf_instance.fit.return_value = mock_rf_instance
        mock_rf_instance.is_fitted = True
        mock_rf.return_value = mock_rf_instance

        models = {"lgbm": mock_lgbm_instance, "xgb": mock_xgb_instance, "rf": mock_rf_instance}

        ensemble = EnsembleModel(models=models)

        # 一部のモデルが失敗してもエラーが伝播することを確認
        with pytest.raises(DataProcessingError):
            ensemble.fit(X, y)

    def test_confidence_threshold_application(self, ensemble_model, sample_data):
        """信頼度閾値適用テスト."""
        X, y = sample_data
        ensemble_model.fit(X, y)

        # 異なる閾値での予測
        pred_low_thresh = ensemble_model.predict(X)

        ensemble_model.confidence_threshold = 0.8  # 高い閾値
        pred_high_thresh = ensemble_model.predict(X)

        # 高い閾値では-1（低信頼度）が多くなるはず
        low_confidence_count_low = np.sum(pred_low_thresh == -1)
        low_confidence_count_high = np.sum(pred_high_thresh == -1)

        assert low_confidence_count_high >= low_confidence_count_low

    def test_weights_normalization(self):
        """重み正規化テスト."""
        # 正規化が必要な重み
        weights = {"lgbm": 2.0, "xgb": 3.0, "rf": 5.0}
        ensemble = EnsembleModel(weights=weights)

        # 重みが正規化されているかチェック
        total_weight = sum(ensemble.weights.values())
        assert abs(total_weight - 1.0) < 1e-6

        # 比率が保たれているかチェック
        expected_lgbm = 2.0 / 10.0
        expected_xgb = 3.0 / 10.0
        expected_rf = 5.0 / 10.0

        assert abs(ensemble.weights["lgbm"] - expected_lgbm) < 1e-6
        assert abs(ensemble.weights["xgb"] - expected_xgb) < 1e-6
        assert abs(ensemble.weights["rf"] - expected_rf) < 1e-6
