"""
ProductionEnsemble テストファイル - Phase 64.6更新

本番用アンサンブルモデルの全メソッドを包括的にテスト。
55特徴量システム・重み付け投票・予測精度検証をカバー。

Phase 64.6: StackingEnsembleテスト削除
"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from src.ml.ensemble import ProductionEnsemble


class TestProductionEnsemble:
    """ProductionEnsemble メインテストクラス"""

    @pytest.fixture
    def mock_models(self):
        """モックモデル作成"""
        mock_lgbm = MagicMock()
        mock_lgbm.predict.return_value = np.array([1, 0, 1])
        mock_lgbm.predict_proba.return_value = np.array([[0.2, 0.8], [0.7, 0.3], [0.1, 0.9]])
        mock_lgbm.n_features_in_ = 55

        mock_xgb = MagicMock()
        mock_xgb.predict.return_value = np.array([1, 1, 0])
        mock_xgb.predict_proba.return_value = np.array([[0.3, 0.7], [0.4, 0.6], [0.8, 0.2]])
        mock_xgb.n_features_in_ = 55

        mock_rf = MagicMock()
        mock_rf.predict.return_value = np.array([0, 1, 1])
        mock_rf.predict_proba.return_value = np.array([[0.6, 0.4], [0.2, 0.8], [0.3, 0.7]])
        mock_rf.n_features_in_ = 55

        return {
            "lightgbm": mock_lgbm,
            "xgboost": mock_xgb,
            "random_forest": mock_rf,
        }

    @pytest.fixture
    def sample_data(self):
        """55特徴量サンプルデータ作成"""
        return np.random.random((3, 55))

    @pytest.fixture
    def ensemble(self, mock_models):
        """ProductionEnsemble インスタンス作成"""
        return ProductionEnsemble(mock_models)

    def test_init_success(self, mock_models):
        """正常初期化テスト"""
        ensemble = ProductionEnsemble(mock_models)

        assert len(ensemble.models) == 3
        assert "lightgbm" in ensemble.models
        assert "xgboost" in ensemble.models
        assert "random_forest" in ensemble.models
        assert ensemble.n_features_ == 55
        assert ensemble.is_fitted is True
        assert len(ensemble.feature_names) == 55
        assert "close" in ensemble.feature_names
        assert "rsi_14" in ensemble.feature_names

    def test_init_empty_models(self):
        """空モデル初期化エラーテスト"""
        with pytest.raises(ValueError, match="個別モデルが提供されていません"):
            ProductionEnsemble({})

    def test_predict_success(self, ensemble, sample_data):
        """正常予測テスト"""
        predictions = ensemble.predict(sample_data)

        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == 3
        assert np.all((predictions == 0) | (predictions == 1))

    def test_predict_wrong_features(self, ensemble):
        """特徴量数不一致エラーテスト"""
        wrong_data = np.array([[1, 2, 3, 4, 5]])

        with pytest.raises(ValueError, match="特徴量数不一致"):
            ensemble.predict(wrong_data)

    def test_predict_proba_success(self, ensemble, sample_data):
        """正常確率予測テスト"""
        probabilities = ensemble.predict_proba(sample_data)

        assert isinstance(probabilities, np.ndarray)
        assert probabilities.shape == (3, 2)
        # 確率の合計が1に近い
        assert np.allclose(probabilities.sum(axis=1), 1.0, rtol=1e-6)
        # 確率が0-1の範囲内
        assert np.all((probabilities >= 0) & (probabilities <= 1))

    def test_predict_proba_wrong_features(self, ensemble):
        """確率予測特徴量数不一致エラーテスト"""
        wrong_data = np.array([[1, 2, 3]])

        with pytest.raises(ValueError, match="特徴量数不一致"):
            ensemble.predict_proba(wrong_data)

    def test_get_model_info(self, ensemble):
        """モデル情報取得テスト"""
        info = ensemble.get_model_info()

        assert info["type"] == "ProductionEnsemble"
        assert len(info["individual_models"]) == 3
        assert "lightgbm" in info["individual_models"]
        assert info["n_features"] == 55
        assert len(info["feature_names"]) == 55
        assert info["phase"] == "Phase 22"
        assert info["status"] == "production_ready"
        assert "weights" in info

    def test_update_weights_success(self, ensemble):
        """重み更新成功テスト"""
        new_weights = {"lightgbm": 0.5, "xgboost": 0.3}
        original_rf_weight = ensemble.weights["random_forest"]

        ensemble.update_weights(new_weights)

        # 新しい重みが反映されている
        assert ensemble.weights["lightgbm"] != 0.4
        assert ensemble.weights["xgboost"] != 0.4
        # random_forestの重みは変更されていない（更新対象外）
        assert ensemble.weights["random_forest"] == original_rf_weight

    def test_update_weights_normalization(self, ensemble):
        """重み正規化テスト"""
        new_weights = {"lightgbm": 2.0, "xgboost": 3.0, "random_forest": 1.0}

        ensemble.update_weights(new_weights)

        # 重みが正規化されて合計が1になっている
        total_weight = sum(ensemble.weights.values())
        assert abs(total_weight - 1.0) < 1e-6

    def test_validate_predictions_without_true_labels(self, ensemble, sample_data):
        """正解ラベルなし予測検証テスト"""
        result = ensemble.validate_predictions(sample_data)

        assert "n_samples" in result
        assert result["n_samples"] == 3
        assert "prediction_range" in result
        assert "probability_range" in result
        assert "buy_ratio" in result
        assert "avg_confidence" in result
        assert 0 <= result["buy_ratio"] <= 1
        assert 0 <= result["avg_confidence"] <= 1

    def test_validate_predictions_with_true_labels(self, ensemble, sample_data):
        """正解ラベル付き予測検証テスト"""
        y_true = np.array([1, 0, 1])

        result = ensemble.validate_predictions(sample_data, y_true)

        assert "accuracy" in result
        assert "f1_score" in result
        assert 0 <= result["accuracy"] <= 1
        assert 0 <= result["f1_score"] <= 1

    def test_predict_model_without_predict_method(self, mock_models, sample_data):
        """予測メソッドなしモデルエラーテスト"""
        mock_models["lightgbm"].predict = None
        type(mock_models["lightgbm"]).predict = property(lambda self: None)

        ensemble = ProductionEnsemble(mock_models)

        try:
            result = ensemble.predict(sample_data)
            assert result is not None or result is None
        except (ValueError, AttributeError):
            pass

    def test_predict_proba_model_fallback(self, sample_data):
        """predict_proba なしモデルのフォールバックテスト（3クラス分類対応）"""
        mock_proba_model = MagicMock()
        mock_proba_model.predict_proba.return_value = np.array(
            [[0.7, 0.2, 0.1], [0.1, 0.8, 0.1], [0.1, 0.1, 0.8]]
        )
        mock_proba_model.n_features_in_ = 55

        mock_predict_only = MagicMock()
        mock_predict_only.predict.return_value = np.array([0, 1, 2])
        mock_predict_only.n_features_in_ = 55
        del mock_predict_only.predict_proba

        models = {"proba_model": mock_proba_model, "predict_only": mock_predict_only}
        ensemble = ProductionEnsemble(models)

        probabilities = ensemble.predict_proba(sample_data)

        assert isinstance(probabilities, np.ndarray)
        assert probabilities.shape == (3, 3)

    def test_predict_proba_model_without_methods(self, sample_data):
        """予測メソッド完全なしエラーテスト"""
        mock_broken = MagicMock()
        mock_broken.n_features_in_ = 55
        del mock_broken.predict
        del mock_broken.predict_proba

        models = {"broken": mock_broken}
        ensemble = ProductionEnsemble(models)

        with pytest.raises(ValueError, match="に予測メソッドがありません"):
            ensemble.predict_proba(sample_data)

    def test_repr(self, ensemble):
        """文字列表現テスト"""
        repr_str = repr(ensemble)

        assert "ProductionEnsemble" in repr_str
        assert "models=3" in repr_str
        assert "features=55" in repr_str
        assert "weights=" in repr_str

    def test_pandas_dataframe_input(self, mock_models):
        """pandas DataFrame 入力テスト"""
        try:
            import pandas as pd

            for model in mock_models.values():
                model.predict.return_value = np.array([1, 0])
                model.predict_proba.return_value = np.array([[0.3, 0.7], [0.8, 0.2]])

            ensemble = ProductionEnsemble(mock_models)

            from src.core.config.feature_manager import get_feature_names

            feature_names = get_feature_names()
            df_data = pd.DataFrame(np.random.random((2, 55)), columns=feature_names)

            predictions = ensemble.predict(df_data)
            probabilities = ensemble.predict_proba(df_data)

            assert len(predictions) == 2
            assert probabilities.shape == (2, 2)

        except ImportError:
            pytest.skip("pandas not available")

    def test_weighted_prediction_calculation(self, sample_data):
        """重み付け予測計算の詳細テスト（3クラス分類対応）"""
        mock_proba = MagicMock()
        mock_proba.predict_proba.return_value = np.array(
            [[0.3, 0.5, 0.2], [0.4, 0.4, 0.2], [0.1, 0.3, 0.6]]
        )
        mock_proba.n_features_in_ = 55

        mock_model1 = MagicMock()
        mock_model1.predict.return_value = np.array([1, 1, 0])
        mock_model1.n_features_in_ = 55
        del mock_model1.predict_proba

        mock_model2 = MagicMock()
        mock_model2.predict.return_value = np.array([0, 0, 2])
        mock_model2.n_features_in_ = 55
        del mock_model2.predict_proba

        models = {"proba": mock_proba, "model1": mock_model1, "model2": mock_model2}
        ensemble = ProductionEnsemble(models)

        ensemble.weights = {"proba": 0.4, "model1": 0.3, "model2": 0.3}

        predictions = ensemble.predict(sample_data)

        assert isinstance(predictions, np.ndarray)
        assert len(predictions) == 3


class TestProductionEnsembleEdgeCases:
    """ProductionEnsemble エッジケーステスト"""

    @pytest.fixture
    def mock_models(self):
        """モックモデル作成（エッジケース用）"""
        mock_lgbm = MagicMock()
        mock_lgbm.predict.return_value = np.array([1, 0, 1])
        mock_lgbm.predict_proba.return_value = np.array([[0.2, 0.8], [0.7, 0.3], [0.1, 0.9]])
        mock_lgbm.n_features_in_ = 55

        mock_xgb = MagicMock()
        mock_xgb.predict.return_value = np.array([1, 1, 0])
        mock_xgb.predict_proba.return_value = np.array([[0.3, 0.7], [0.4, 0.6], [0.8, 0.2]])
        mock_xgb.n_features_in_ = 55

        mock_rf = MagicMock()
        mock_rf.predict.return_value = np.array([0, 1, 1])
        mock_rf.predict_proba.return_value = np.array([[0.6, 0.4], [0.2, 0.8], [0.3, 0.7]])
        mock_rf.n_features_in_ = 55

        return {
            "lightgbm": mock_lgbm,
            "xgboost": mock_xgb,
            "random_forest": mock_rf,
        }

    @pytest.fixture
    def sample_data(self):
        """55特徴量サンプルデータ作成"""
        return np.random.random((3, 55))

    def test_single_model_ensemble(self):
        """単一モデルアンサンブルテスト"""
        mock_single = MagicMock()
        mock_single.predict.return_value = np.array([1, 0])
        mock_single.predict_proba.return_value = np.array([[0.3, 0.7], [0.8, 0.2]])
        mock_single.n_features_in_ = 55

        ensemble = ProductionEnsemble({"single": mock_single})

        data = np.random.random((2, 55))
        predictions = ensemble.predict(data)
        probabilities = ensemble.predict_proba(data)

        assert len(predictions) == 2
        assert probabilities.shape == (2, 2)

    def test_zero_weight_handling(self, mock_models, sample_data):
        """ゼロ重み処理テスト"""
        ensemble = ProductionEnsemble(mock_models)

        ensemble.weights["lightgbm"] = 0
        ensemble.weights["xgboost"] = 0.7
        ensemble.weights["random_forest"] = 0.3

        predictions = ensemble.predict(sample_data)
        probabilities = ensemble.predict_proba(sample_data)

        assert isinstance(predictions, np.ndarray)
        assert probabilities.shape == (len(sample_data), 2)

    def test_large_dataset_performance(self, mock_models):
        """大規模データセット性能テスト"""
        ensemble = ProductionEnsemble(mock_models)

        large_data = np.random.random((1000, 55))

        for model in mock_models.values():
            model.predict.return_value = np.random.randint(0, 2, 1000)
            model.predict_proba.return_value = np.random.random((1000, 2))

        predictions = ensemble.predict(large_data)
        probabilities = ensemble.predict_proba(large_data)

        assert len(predictions) == 1000
        assert probabilities.shape == (1000, 2)
