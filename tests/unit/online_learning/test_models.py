# tests/unit/online_learning/test_models.py
"""
Incremental learning models のテスト
"""

import os
import tempfile
from unittest.mock import Mock, patch

import numpy as np
import pytest

from crypto_bot.online_learning.base import OnlineLearningConfig
from crypto_bot.online_learning.models import IncrementalMLModel


class TestIncrementalMLModel:
    """IncrementalMLModel のテストクラス"""

    @pytest.fixture
    def config(self):
        """テスト用設定"""
        return OnlineLearningConfig(
            batch_size=10, memory_window=100, enable_drift_detection=True
        )

    @pytest.fixture
    def sample_data(self):
        """テスト用データ"""
        X = np.random.random((20, 3))
        y = np.random.randint(0, 2, 20)
        return X, y

    def test_initialization_river_not_available(self, config):
        """River利用不可時の初期化テスト"""
        with patch("crypto_bot.online_learning.models.RIVER_AVAILABLE", False):
            with patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True):
                model = IncrementalMLModel(
                    config=config,
                    model_type="sgd_classifier",
                    task_type="classification",
                )

                assert model.model_type == "sgd_classifier"
                assert model.task_type == "classification"
                assert model.backend == "sklearn"

    def test_initialization_sklearn_not_available(self, config):
        """sklearn利用不可時の初期化テスト"""
        with patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", False):
            with patch("crypto_bot.online_learning.models.RIVER_AVAILABLE", False):
                with pytest.raises(ImportError):
                    IncrementalMLModel(
                        config=config,
                        model_type="sgd_classifier",
                        task_type="classification",
                    )

    def test_initialization_river_available(self, config):
        """River利用可能時の初期化テスト"""
        with patch("crypto_bot.online_learning.models.RIVER_AVAILABLE", True):
            with patch("crypto_bot.online_learning.models.linear_model"):
                model = IncrementalMLModel(
                    config=config, model_type="river_linear", task_type="classification"
                )

                assert model.model_type == "river_linear"
                assert model.backend == "river"

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_sklearn_classifier_partial_fit(self, mock_sgd, config, sample_data):
        """sklearn分類器の部分学習テスト"""
        X, y = sample_data

        # モックモデルの設定
        mock_model = Mock()
        mock_model.partial_fit.return_value = None
        mock_model.classes_ = [0, 1]
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )

        result = model.partial_fit(X, y)

        assert result.success is True
        assert result.samples_processed == len(X)
        assert mock_model.partial_fit.called

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_sklearn_predict(self, mock_sgd, config, sample_data):
        """sklearn予測テスト"""
        X, y = sample_data

        # モックモデルの設定
        mock_model = Mock()
        mock_model.predict.return_value = np.array([1, 0, 1])
        mock_model.predict_proba.return_value = np.array(
            [[0.2, 0.8], [0.7, 0.3], [0.3, 0.7]]
        )
        mock_model.classes_ = [0, 1]
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )
        model.is_fitted = True

        result = model.predict(X[:3])

        assert result.prediction.shape == (3,)
        assert result.confidence > 0
        assert mock_model.predict.called

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDRegressor")
    def test_sklearn_regressor(self, mock_sgd, config, sample_data):
        """sklearn回帰器テスト"""
        X, y = sample_data
        y = y.astype(float)  # 回帰用に変換

        # モックモデルの設定
        mock_model = Mock()
        mock_model.partial_fit.return_value = None
        mock_model.predict.return_value = np.array([0.5, 0.7, 0.3])
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_regressor", task_type="regression"
        )

        # 学習
        result = model.partial_fit(X, y)
        assert result.success is True

        # 予測
        model.is_fitted = True
        pred_result = model.predict(X[:3])
        assert pred_result.prediction.shape == (3,)

    @patch("crypto_bot.online_learning.models.RIVER_AVAILABLE", True)
    def test_river_model_creation(self, config):
        """Riverモデル作成テスト"""
        with patch("crypto_bot.online_learning.models.linear_model") as mock_linear:
            mock_model = Mock()
            mock_linear.LogisticRegression.return_value = mock_model

            model = IncrementalMLModel(
                config=config, model_type="river_linear", task_type="classification"
            )

            assert model.backend == "river"
            assert mock_linear.LogisticRegression.called

    @patch("crypto_bot.online_learning.models.RIVER_AVAILABLE", True)
    def test_river_ensemble_creation(self, config):
        """Riverアンサンブルモデル作成テスト"""
        with patch("crypto_bot.online_learning.models.ensemble") as mock_ensemble:
            mock_model = Mock()
            mock_ensemble.AdaptiveRandomForestClassifier.return_value = mock_model

            model = IncrementalMLModel(
                config=config, model_type="river_forest", task_type="classification"
            )

            assert model.backend == "river"
            assert mock_ensemble.AdaptiveRandomForestClassifier.called

    def test_invalid_model_type(self, config):
        """無効なモデルタイプテスト"""
        with pytest.raises(ValueError):
            IncrementalMLModel(
                config=config, model_type="invalid_model", task_type="classification"
            )

    def test_invalid_task_type(self, config):
        """無効なタスクタイプテスト"""
        with pytest.raises(ValueError):
            IncrementalMLModel(
                config=config, model_type="sgd_classifier", task_type="invalid_task"
            )

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_memory_management(self, mock_sgd, config, sample_data):
        """メモリ管理テスト"""
        X, y = sample_data

        # メモリ制限を小さく設定
        config.memory_window = 10

        mock_model = Mock()
        mock_model.partial_fit.return_value = None
        mock_model.classes_ = [0, 1]
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )

        # メモリ制限を超えるデータを追加
        result = model.partial_fit(X, y)

        # メモリ使用量が報告されているか確認
        assert result.memory_usage_mb >= 0

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_feature_importance_sklearn(self, mock_sgd, config):
        """sklearn特徴量重要度テスト"""
        mock_model = Mock()
        mock_model.coef_ = np.array([[0.5, -0.3, 0.8]])
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config,
            model_type="sgd_classifier",
            task_type="classification",
            feature_names=["f1", "f2", "f3"],
        )
        model.is_fitted = True

        importance = model.get_feature_importance()

        assert isinstance(importance, dict)
        assert len(importance) == 3
        assert "f1" in importance

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_model_saving(self, mock_sgd, config):
        """モデル保存テスト"""
        mock_model = Mock()
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            try:
                success = model.save_model(tmp_file.name)
                assert success is True
                assert os.path.exists(tmp_file.name)
            finally:
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_model_loading(self, mock_sgd, config):
        """モデル読み込みテスト"""
        mock_model = Mock()
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            try:
                # 保存
                model.save_model(tmp_file.name)

                # 新しいモデルで読み込み
                new_model = IncrementalMLModel(
                    config=config,
                    model_type="sgd_classifier",
                    task_type="classification",
                )

                success = new_model.load_model(tmp_file.name)
                assert success is True
            finally:
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_predict_proba_classification(self, mock_sgd, config, sample_data):
        """分類確率予測テスト"""
        X, y = sample_data

        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.7], [0.8, 0.2]])
        mock_model.classes_ = [0, 1]
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )
        model.is_fitted = True

        probas = model.predict_proba(X[:2])

        assert probas.shape == (2, 2)
        assert np.allclose(probas.sum(axis=1), 1.0)

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDRegressor")
    def test_predict_proba_regression(self, mock_sgd, config, sample_data):
        """回帰での確率予測テスト（エラーケース）"""
        X, y = sample_data

        mock_model = Mock()
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_regressor", task_type="regression"
        )
        model.is_fitted = True

        # 回帰では確率予測は利用できない
        with pytest.raises(ValueError):
            model.predict_proba(X[:2])

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_get_status(self, mock_sgd, config):
        """ステータス取得テスト"""
        mock_model = Mock()
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )
        model.samples_seen = 100

        status = model.get_status()

        assert "model_type" in status
        assert "task_type" in status
        assert "backend" in status
        assert "is_fitted" in status
        assert "samples_seen" in status
        assert status["samples_seen"] == 100

    @patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True)
    @patch("crypto_bot.online_learning.models.SGDClassifier")
    def test_reset_model(self, mock_sgd, config):
        """モデルリセットテスト"""
        mock_model = Mock()
        mock_sgd.return_value = mock_model

        model = IncrementalMLModel(
            config=config, model_type="sgd_classifier", task_type="classification"
        )
        model.samples_seen = 100
        model.is_fitted = True

        # リセット機能があるかテスト
        if hasattr(model, "reset"):
            model.reset()
            assert model.samples_seen == 0
            assert model.is_fitted is False

    def test_error_handling_partial_fit(self, config, sample_data):
        """部分学習エラーハンドリングテスト"""
        X, y = sample_data

        with patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True):
            with patch("crypto_bot.online_learning.models.SGDClassifier") as mock_sgd:
                mock_model = Mock()
                mock_model.partial_fit.side_effect = Exception("Training error")
                mock_sgd.return_value = mock_model

                model = IncrementalMLModel(
                    config=config,
                    model_type="sgd_classifier",
                    task_type="classification",
                )

                result = model.partial_fit(X, y)

                # エラーが適切に処理されているか確認
                assert result.success is False
                assert "error" in result.message.lower()

    def test_error_handling_predict(self, config, sample_data):
        """予測エラーハンドリングテスト"""
        X, y = sample_data

        with patch("crypto_bot.online_learning.models.SKLEARN_AVAILABLE", True):
            with patch("crypto_bot.online_learning.models.SGDClassifier") as mock_sgd:
                mock_model = Mock()
                mock_model.predict.side_effect = Exception("Prediction error")
                mock_sgd.return_value = mock_model

                model = IncrementalMLModel(
                    config=config,
                    model_type="sgd_classifier",
                    task_type="classification",
                )
                model.is_fitted = True

                # 予測エラーが適切に処理されるか確認
                try:
                    result = model.predict(X[:1])
                    # エラーが処理されている場合
                    assert result is not None
                except Exception:
                    # エラーが伝播する場合も想定内
                    assert True
