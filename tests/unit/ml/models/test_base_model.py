"""
BaseMLModel テスト - カバレッジ向上

BaseMLModelの抽象クラスと共通機能のテスト。
エッジケース、エラーハンドリング、ユーティリティ関数を網羅。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from src.core.exceptions import DataProcessingError
from src.ml.models import BaseMLModel, LGBMModel, RFModel, XGBModel


class ConcreteMLModel(BaseMLModel):
    """テスト用の具象クラス"""

    def _create_estimator(self, **kwargs):
        """テスト用のestimatorを作成"""
        return LogisticRegression(max_iter=100, random_state=42)


class TestBaseMLModel:
    """BaseMLModelの包括的テスト"""

    @pytest.fixture
    def sample_features(self):
        """サンプル特徴量データ"""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "feature1": np.random.uniform(0, 1, 100),
                "feature2": np.random.uniform(0, 1, 100),
                "feature3": np.random.uniform(0, 1, 100),
                "feature4": np.random.uniform(0, 1, 100),
                "feature5": np.random.uniform(0, 1, 100),
            }
        )

    @pytest.fixture
    def sample_targets(self):
        """サンプルターゲットデータ"""
        np.random.seed(42)
        return pd.Series(np.random.randint(0, 3, 100))

    @pytest.fixture
    def binary_targets(self):
        """バイナリターゲットデータ"""
        np.random.seed(42)
        return pd.Series(np.random.randint(0, 2, 100))

    @pytest.fixture
    def base_model(self):
        """ConcreteMLModelインスタンス"""
        return ConcreteMLModel(model_name="TestModel")

    def test_model_initialization(self, base_model):
        """モデル初期化テスト"""
        assert base_model.model_name == "TestModel"
        assert base_model.estimator is not None
        assert base_model.is_fitted is False
        assert base_model.feature_names is None

    def test_fit_basic(self, base_model, sample_features, binary_targets):
        """基本的な学習テスト"""
        result = base_model.fit(sample_features, binary_targets)

        assert result is base_model
        assert base_model.is_fitted is True
        assert base_model.feature_names == list(sample_features.columns)

    def test_fit_with_numpy_arrays(self, base_model):
        """NumPy配列での学習テスト"""
        np.random.seed(42)
        X = np.random.random((100, 5))
        y = np.random.randint(0, 2, 100)

        # NumPy配列はDataFrameに変換して渡す
        X_df = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(5)])
        y_series = pd.Series(y)

        result = base_model.fit(X_df, y_series)
        assert result is base_model
        assert base_model.is_fitted is True

    def test_fit_with_empty_data(self, base_model):
        """空データでの学習テスト"""
        empty_features = pd.DataFrame()
        empty_targets = pd.Series(dtype=int)

        with pytest.raises(DataProcessingError) as exc_info:
            base_model.fit(empty_features, empty_targets)
        assert "Training data is empty" in str(exc_info.value)

    def test_fit_with_length_mismatch(self, base_model, sample_features):
        """長さ不一致での学習テスト"""
        short_targets = pd.Series(np.random.randint(0, 2, 50))

        with pytest.raises(DataProcessingError) as exc_info:
            base_model.fit(sample_features, short_targets)
        assert "length mismatch" in str(exc_info.value)

    def test_fit_with_insufficient_samples(self, base_model):
        """サンプル数不足での学習テスト"""
        small_features = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})
        small_targets = pd.Series([0, 1, 0])

        with pytest.raises(DataProcessingError) as exc_info:
            base_model.fit(small_features, small_targets)
        assert "Insufficient training data" in str(exc_info.value)

    def test_fit_with_high_nan_ratio_features(self, base_model):
        """特徴量のNaN比率が高い場合のテスト"""
        # 60%以上のNaN値を含む特徴量
        features = pd.DataFrame(
            {
                "feature1": [np.nan] * 70 + [1.0] * 30,
                "feature2": [np.nan] * 70 + [2.0] * 30,
            }
        )
        targets = pd.Series(np.random.randint(0, 2, 100))

        with pytest.raises(DataProcessingError) as exc_info:
            base_model.fit(features, targets)
        assert "Too many NaN values in features" in str(exc_info.value)

    def test_fit_with_high_nan_ratio_target(self, base_model, sample_features):
        """ターゲットのNaN比率が高い場合のテスト"""
        # 40%以上のNaN値を含むターゲット
        targets = pd.Series([np.nan] * 50 + [0, 1] * 25)

        with pytest.raises(DataProcessingError) as exc_info:
            base_model.fit(sample_features, targets)
        assert "Too many NaN values in target" in str(exc_info.value)

    def test_predict_success(self, base_model, sample_features, binary_targets):
        """正常予測テスト"""
        base_model.fit(sample_features, binary_targets)

        predictions = base_model.predict(sample_features.iloc[:10])

        assert predictions is not None
        assert len(predictions) == 10

    def test_predict_without_fitting(self, base_model, sample_features):
        """学習前予測テスト"""
        with pytest.raises(ValueError) as exc_info:
            base_model.predict(sample_features)
        assert "is not fitted" in str(exc_info.value)

    def test_predict_proba_success(self, base_model, sample_features, binary_targets):
        """確率予測成功テスト"""
        base_model.fit(sample_features, binary_targets)

        probabilities = base_model.predict_proba(sample_features.iloc[:10])

        assert probabilities is not None
        assert probabilities.shape[0] == 10
        assert np.all((probabilities >= 0) & (probabilities <= 1))

    def test_predict_proba_without_fitting(self, base_model, sample_features):
        """学習前確率予測テスト"""
        with pytest.raises(ValueError) as exc_info:
            base_model.predict_proba(sample_features)
        assert "is not fitted" in str(exc_info.value)

    def test_align_features_missing(self, base_model, sample_features, binary_targets):
        """不足特徴量の自動補完テスト"""
        base_model.fit(sample_features, binary_targets)

        # 一部の特徴量のみ
        incomplete_features = sample_features[["feature1", "feature2"]].iloc[:5]

        predictions = base_model.predict(incomplete_features)
        assert predictions is not None
        assert len(predictions) == 5

    def test_align_features_extra(self, base_model, sample_features, binary_targets):
        """余分な特徴量の削除テスト"""
        base_model.fit(sample_features, binary_targets)

        extra_features = sample_features.copy()
        extra_features["extra_feature"] = np.random.uniform(0, 1, len(extra_features))

        predictions = base_model.predict(extra_features.iloc[:5])
        assert predictions is not None
        assert len(predictions) == 5

    def test_align_features_reorder(self, base_model, sample_features, binary_targets):
        """特徴量順序の調整テスト"""
        base_model.fit(sample_features, binary_targets)

        # 列順序を逆にする
        reordered_features = sample_features[sample_features.columns[::-1]].iloc[:5]

        predictions = base_model.predict(reordered_features)
        assert predictions is not None
        assert len(predictions) == 5

    def test_get_feature_importance(self, base_model, sample_features, binary_targets):
        """特徴量重要度取得テスト"""
        base_model.fit(sample_features, binary_targets)

        importance = base_model.get_feature_importance()

        # LogisticRegressionはcoef_を持つ
        assert importance is not None
        assert len(importance) == len(sample_features.columns)
        assert "feature" in importance.columns
        assert "importance" in importance.columns

    def test_get_feature_importance_without_fitting(self, base_model):
        """学習前特徴量重要度取得テスト"""
        importance = base_model.get_feature_importance()
        assert importance is None

    def test_get_model_info(self, base_model):
        """モデル情報取得テスト（未学習）"""
        info = base_model.get_model_info()

        assert info["model_name"] == "TestModel"
        assert info["model_type"] == "LogisticRegression"
        assert info["is_fitted"] is False
        assert info["n_features"] == 0

    def test_get_model_info_fitted(self, base_model, sample_features, binary_targets):
        """モデル情報取得テスト（学習後）"""
        base_model.fit(sample_features, binary_targets)

        info = base_model.get_model_info()

        assert info["model_name"] == "TestModel"
        assert info["is_fitted"] is True
        assert info["n_features"] == len(sample_features.columns)
        assert info["feature_names"] == list(sample_features.columns)

    def test_save_model(self, base_model, sample_features, binary_targets):
        """モデル保存テスト"""
        base_model.fit(sample_features, binary_targets)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "test_model.pkl"
            base_model.save(save_path)
            assert save_path.exists()

    def test_save_creates_directory(self, base_model, sample_features, binary_targets):
        """保存時のディレクトリ作成テスト"""
        base_model.fit(sample_features, binary_targets)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "subdir" / "test_model.pkl"
            base_model.save(save_path)
            assert save_path.exists()
            assert save_path.parent.exists()

    def test_save_model_error(self, base_model, sample_features, binary_targets):
        """モデル保存エラーテスト"""
        base_model.fit(sample_features, binary_targets)

        with patch("joblib.dump", side_effect=Exception("Save failed")):
            with pytest.raises(DataProcessingError) as exc_info:
                base_model.save("/tmp/test_model.pkl")
            assert "Model save failed" in str(exc_info.value)

    def test_load_model(self, base_model, sample_features, binary_targets):
        """モデル読み込みテスト"""
        base_model.fit(sample_features, binary_targets)

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "test_model.pkl"
            base_model.save(save_path)

            loaded_model = ConcreteMLModel.load(save_path)

            assert loaded_model.model_name == base_model.model_name
            assert loaded_model.is_fitted == base_model.is_fitted
            assert loaded_model.feature_names == base_model.feature_names

    def test_load_model_file_not_found(self):
        """存在しないモデルファイル読み込みテスト"""
        with pytest.raises(DataProcessingError) as exc_info:
            ConcreteMLModel.load("/nonexistent/path/model.pkl")
        assert "Model load failed" in str(exc_info.value)

    def test_load_model_invalid_format(self):
        """無効形式モデル読み込みテスト"""
        with patch("joblib.load", side_effect=Exception("Invalid format")):
            with pytest.raises(DataProcessingError) as exc_info:
                ConcreteMLModel.load("/tmp/invalid_model.pkl")
            assert "Model load failed" in str(exc_info.value)


class TestValidateTrainingData:
    """_validate_training_dataメソッドの詳細テスト"""

    @pytest.fixture
    def model(self):
        return ConcreteMLModel(model_name="TestModel")

    def test_validate_numpy_arrays(self, model):
        """NumPy配列のバリデーションテスト"""
        X = np.random.random((100, 5))
        y = np.random.randint(0, 2, 100)

        # 正常なデータ
        model._validate_training_data(X, y)  # 例外が発生しなければOK

    def test_validate_pandas_dataframe(self, model):
        """Pandas DataFrameのバリデーションテスト"""
        X = pd.DataFrame(np.random.random((100, 5)))
        y = pd.Series(np.random.randint(0, 2, 100))

        model._validate_training_data(X, y)  # 例外が発生しなければOK

    def test_validate_empty_numpy(self, model):
        """空NumPy配列のバリデーションテスト"""
        X = np.array([]).reshape(0, 5)
        y = np.array([])

        with pytest.raises(ValueError) as exc_info:
            model._validate_training_data(X, y)
        assert "Training data is empty" in str(exc_info.value)

    def test_validate_nan_ratio_numpy(self, model):
        """NumPy配列のNaN比率バリデーションテスト"""
        X = np.full((100, 5), np.nan)  # 100% NaN
        y = np.random.randint(0, 2, 100)

        with pytest.raises(ValueError) as exc_info:
            model._validate_training_data(X, y)
        assert "Too many NaN values" in str(exc_info.value)


class TestAlignFeatures:
    """_align_featuresメソッドの詳細テスト"""

    @pytest.fixture
    def model(self):
        model = ConcreteMLModel(model_name="TestModel")
        model.feature_names = ["feature1", "feature2", "feature3"]
        return model

    def test_align_no_changes_needed(self, model):
        """変更不要の場合のテスト"""
        X = pd.DataFrame(
            {
                "feature1": [1, 2, 3],
                "feature2": [4, 5, 6],
                "feature3": [7, 8, 9],
            }
        )

        aligned = model._align_features(X)

        assert list(aligned.columns) == model.feature_names

    def test_align_with_missing_features(self, model):
        """不足特徴量の補完テスト"""
        X = pd.DataFrame(
            {
                "feature1": [1, 2, 3],
            }
        )

        aligned = model._align_features(X)

        assert list(aligned.columns) == model.feature_names
        assert (aligned["feature2"] == 0.0).all()
        assert (aligned["feature3"] == 0.0).all()

    def test_align_with_extra_features(self, model):
        """余分な特徴量の削除テスト"""
        X = pd.DataFrame(
            {
                "feature1": [1, 2, 3],
                "feature2": [4, 5, 6],
                "feature3": [7, 8, 9],
                "extra": [10, 11, 12],
            }
        )

        aligned = model._align_features(X)

        assert list(aligned.columns) == model.feature_names
        assert "extra" not in aligned.columns

    def test_align_with_reordering(self, model):
        """特徴量順序の調整テスト"""
        X = pd.DataFrame(
            {
                "feature3": [7, 8, 9],
                "feature1": [1, 2, 3],
                "feature2": [4, 5, 6],
            }
        )

        aligned = model._align_features(X)

        assert list(aligned.columns) == model.feature_names

    def test_align_with_no_feature_names(self):
        """feature_namesがない場合のテスト"""
        model = ConcreteMLModel(model_name="TestModel")
        model.feature_names = None

        X = pd.DataFrame({"any_feature": [1, 2, 3]})

        aligned = model._align_features(X)

        # feature_namesがない場合は入力をそのまま返す
        assert "any_feature" in aligned.columns


class TestGetModelImportance:
    """_get_model_importanceメソッドの詳細テスト"""

    def test_importance_from_feature_importances(self):
        """feature_importances_属性からの重要度取得テスト"""
        model = RFModel(n_estimators=10, random_state=42)

        X = pd.DataFrame(np.random.random((100, 5)))
        y = pd.Series(np.random.randint(0, 2, 100))
        model.fit(X, y)

        importance = model._get_model_importance()

        assert importance is not None
        assert len(importance) == 5

    def test_importance_from_coef(self):
        """coef_属性からの重要度取得テスト"""
        model = ConcreteMLModel(model_name="TestModel")

        X = pd.DataFrame(np.random.random((100, 5)))
        y = pd.Series(np.random.randint(0, 2, 100))
        model.fit(X, y)

        importance = model._get_model_importance()

        assert importance is not None
        assert len(importance) == 5


class TestPredictProbaWithoutProba:
    """predict_probaがないモデルのテスト"""

    def test_predict_proba_fallback(self):
        """predict_probaがない場合のフォールバックテスト"""

        class NoProbaModel(BaseMLModel):
            """predict_probaを持たないモデル"""

            def _create_estimator(self, **kwargs):
                estimator = Mock()
                estimator.predict = Mock(return_value=np.array([0, 1, 2, 1, 0]))
                # predict_probaを持たない
                del estimator.predict_proba
                return estimator

        model = NoProbaModel(model_name="NoProbaModel")
        model.is_fitted = True
        model.feature_names = ["feature1", "feature2"]

        X = pd.DataFrame(
            {
                "feature1": [1, 2, 3, 4, 5],
                "feature2": [6, 7, 8, 9, 10],
            }
        )

        probabilities = model.predict_proba(X)

        assert probabilities is not None
        assert probabilities.shape[0] == 5
        # 各行で予測クラスの確率が1.0
        for i, pred in enumerate([0, 1, 2, 1, 0]):
            assert probabilities[i, pred] == 1.0


class TestPredictProbaEdgeCases:
    """predict_probaのエッジケーステスト"""

    def test_predict_proba_single_class_prediction(self):
        """単一クラスのみ予測される場合のテスト（n_classes < 2）"""

        class SingleClassModel(BaseMLModel):
            def _create_estimator(self, **kwargs):
                estimator = Mock()
                # 全て同じクラスを予測
                estimator.predict = Mock(return_value=np.array([0, 0, 0, 0, 0]))
                del estimator.predict_proba
                return estimator

        model = SingleClassModel(model_name="SingleClassModel")
        model.is_fitted = True
        model.feature_names = ["feature1", "feature2"]

        X = pd.DataFrame({"feature1": [1, 2, 3, 4, 5], "feature2": [6, 7, 8, 9, 10]})

        probabilities = model.predict_proba(X)

        assert probabilities is not None
        # n_classes < 2 なので 2 に調整される
        assert probabilities.shape == (5, 2)

    def test_predict_proba_two_class_warning(self):
        """2クラスが検出された場合の警告テスト（n_classes != 3）"""

        class TwoClassModel(BaseMLModel):
            def _create_estimator(self, **kwargs):
                estimator = Mock()
                # 2クラスのみ予測
                estimator.predict = Mock(return_value=np.array([0, 1, 0, 1, 0]))
                del estimator.predict_proba
                return estimator

        model = TwoClassModel(model_name="TwoClassModel")
        model.is_fitted = True
        model.feature_names = ["feature1", "feature2"]

        X = pd.DataFrame({"feature1": [1, 2, 3, 4, 5], "feature2": [6, 7, 8, 9, 10]})

        # 警告が出るがエラーにはならない
        probabilities = model.predict_proba(X)

        assert probabilities is not None
        assert probabilities.shape == (5, 2)


class TestGetFeatureImportanceNone:
    """特徴量重要度がNoneになる場合のテスト"""

    def test_importance_returns_none(self):
        """_get_model_importanceがNoneを返す場合のテスト"""

        class NoImportanceModel(BaseMLModel):
            def _create_estimator(self, **kwargs):
                estimator = Mock()
                estimator.fit = Mock(return_value=None)
                # feature_importances_もcoef_も持たない
                if hasattr(estimator, "feature_importances_"):
                    del estimator.feature_importances_
                if hasattr(estimator, "coef_"):
                    del estimator.coef_
                return estimator

        model = NoImportanceModel(model_name="NoImportanceModel")
        model.is_fitted = True
        model.feature_names = ["feature1", "feature2"]

        importance = model.get_feature_importance()
        assert importance is None


class TestModelErrorHandling:
    """モデルエラーハンドリングテスト"""

    def test_fit_exception_handling(self):
        """学習時の例外ハンドリングテスト"""

        class FailingModel(BaseMLModel):
            def _create_estimator(self, **kwargs):
                estimator = Mock()
                estimator.fit = Mock(side_effect=Exception("Fit failed"))
                return estimator

        model = FailingModel(model_name="FailingModel")

        X = pd.DataFrame(np.random.random((100, 5)))
        y = pd.Series(np.random.randint(0, 2, 100))

        with pytest.raises(DataProcessingError) as exc_info:
            model.fit(X, y)
        assert "Model training failed" in str(exc_info.value)

    def test_predict_exception_handling(self):
        """予測時の例外ハンドリングテスト"""

        class FailingPredictModel(BaseMLModel):
            def _create_estimator(self, **kwargs):
                estimator = Mock()
                estimator.fit = Mock(return_value=None)
                estimator.predict = Mock(side_effect=Exception("Predict failed"))
                return estimator

        model = FailingPredictModel(model_name="FailingPredictModel")
        model.is_fitted = True
        model.feature_names = ["feature1", "feature2"]

        X = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})

        with pytest.raises(DataProcessingError) as exc_info:
            model.predict(X)
        assert "Prediction failed" in str(exc_info.value)

    def test_predict_proba_exception_handling(self):
        """確率予測時の例外ハンドリングテスト"""

        class FailingProbaModel(BaseMLModel):
            def _create_estimator(self, **kwargs):
                estimator = Mock()
                estimator.fit = Mock(return_value=None)
                estimator.predict_proba = Mock(side_effect=Exception("Proba failed"))
                return estimator

        model = FailingProbaModel(model_name="FailingProbaModel")
        model.is_fitted = True
        model.feature_names = ["feature1", "feature2"]

        X = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})

        with pytest.raises(DataProcessingError) as exc_info:
            model.predict_proba(X)
        assert "Probability prediction failed" in str(exc_info.value)

    def test_get_feature_importance_exception_handling(self):
        """特徴量重要度取得時の例外ハンドリングテスト"""

        class FailingImportanceModel(BaseMLModel):
            def _create_estimator(self, **kwargs):
                estimator = Mock()
                estimator.fit = Mock(return_value=None)
                # feature_importances_アクセス時に例外
                type(estimator).feature_importances_ = property(
                    lambda self: (_ for _ in ()).throw(Exception("Importance failed"))
                )
                return estimator

        model = FailingImportanceModel(model_name="FailingImportanceModel")
        model.is_fitted = True
        model.feature_names = ["feature1", "feature2"]

        # 例外が発生してもNoneを返す（エラーログは出力される）
        importance = model.get_feature_importance()
        assert importance is None
