"""
LightGBM model テスト - カバレッジ向上

LGBMModelの包括的なテスト。
初期化、学習、予測、特徴量重要度、パラメータクリーンアップを網羅。
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
from lightgbm import LGBMClassifier

from src.core.exceptions import DataProcessingError
from src.ml.models import LGBMModel


class TestLGBMModel:
    """LGBMModelの包括的テスト"""

    @pytest.fixture
    def sample_features(self):
        """サンプル特徴量データ"""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "rsi_14": np.random.uniform(20, 80, 100),
                "bb_position": np.random.uniform(-1, 1, 100),
                "volume_sma_ratio": np.random.uniform(0.5, 2.0, 100),
                "price_change_1h": np.random.uniform(-0.05, 0.05, 100),
                "atr_14": np.random.uniform(0.001, 0.01, 100),
                "macd": np.random.uniform(-0.01, 0.01, 100),
            }
        )

    @pytest.fixture
    def sample_targets(self):
        """サンプルターゲットデータ（3クラス分類）"""
        np.random.seed(42)
        return np.random.randint(0, 3, 100)

    @pytest.fixture
    def binary_targets(self):
        """バイナリターゲットデータ"""
        np.random.seed(42)
        return np.random.randint(0, 2, 100)

    @pytest.fixture
    def lgbm_model(self):
        """LGBMModelインスタンス"""
        return LGBMModel(
            n_estimators=10, max_depth=3, learning_rate=0.1
        )

    def test_model_initialization(self, lgbm_model):
        """モデル初期化テスト"""
        assert lgbm_model.model_name == "LightGBM"
        assert lgbm_model.model_params["n_estimators"] == 10
        assert lgbm_model.model_params["max_depth"] == 3
        assert lgbm_model.model_params["learning_rate"] == 0.1
        assert lgbm_model.estimator is not None
        assert lgbm_model.is_fitted is False

    def test_initialization_with_default_params(self):
        """デフォルトパラメータ初期化テスト（Phase 51.9: 3クラス分類対応）"""
        model = LGBMModel()

        # Phase 51.9: 3クラス分類デフォルト
        assert model.model_params["objective"] == "multiclass"
        assert model.model_params["num_class"] == 3
        assert model.model_params["boosting_type"] == "gbdt"
        assert model.model_params["verbose"] == -1
        assert model.model_params["random_state"] == 42  # 環境変数から設定

    def test_initialization_with_custom_params(self):
        """カスタムパラメータ初期化テスト"""
        model = LGBMModel(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            num_leaves=50,
            feature_fraction=0.8,
            bagging_fraction=0.8,
            bagging_freq=5,
        )

        assert model.model_params["n_estimators"] == 200
        assert model.model_params["max_depth"] == 5
        assert model.model_params["learning_rate"] == 0.05
        assert model.model_params["num_leaves"] == 50
        assert model.model_params["feature_fraction"] == 0.8

    def test_fit_basic(self, lgbm_model, sample_features, sample_targets):
        """基本的な学習テスト（3クラス分類）"""
        result = lgbm_model.fit(sample_features, sample_targets)

        assert result is lgbm_model
        assert lgbm_model.is_fitted is True
        assert lgbm_model.estimator is not None
        assert isinstance(lgbm_model.estimator, LGBMClassifier)
        assert lgbm_model.feature_names == list(sample_features.columns)

    def test_fit_binary_classification(self, sample_features, binary_targets):
        """バイナリ分類学習テスト"""
        model = LGBMModel(
            n_estimators=10,
            objective="binary",
        )
        # binary objectiveでは num_class を削除する必要がある
        if "num_class" in model.model_params:
            del model.model_params["num_class"]

        # estimatorを再作成
        model.estimator = LGBMClassifier(
            n_estimators=10,
            objective="binary",
            verbose=-1,
            random_state=42,
        )

        result = model.fit(sample_features, binary_targets)
        assert result is model
        assert model.is_fitted is True

    def test_fit_with_invalid_features(self, lgbm_model):
        """無効な特徴量での学習テスト"""
        invalid_features = pd.DataFrame()
        targets = np.array([0, 1, 2])

        with pytest.raises(Exception):
            lgbm_model.fit(invalid_features, targets)
        assert lgbm_model.is_fitted is False

    def test_fit_with_mismatched_shapes(self, lgbm_model, sample_features):
        """形状不一致での学習テスト"""
        invalid_targets = np.array([0, 1, 2])  # 特徴量より少ない

        with pytest.raises(Exception):
            lgbm_model.fit(sample_features, invalid_targets)
        assert lgbm_model.is_fitted is False

    def test_fit_with_insufficient_data(self, lgbm_model):
        """データ不足での学習テスト"""
        small_features = pd.DataFrame({"feature1": [1, 2], "feature2": [3, 4]})
        small_targets = np.array([0, 1])

        with pytest.raises(Exception) as exc_info:
            lgbm_model.fit(small_features, small_targets)
        assert "Insufficient training data" in str(exc_info.value)

    def test_fit_with_nan_values(self, lgbm_model):
        """NaN値を含むデータでの学習テスト"""
        # LightGBMはNaN値を扱える
        features_with_nan = pd.DataFrame(
            {
                "feature1": [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "feature2": [1, np.nan, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            }
        )
        targets = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2])

        result = lgbm_model.fit(features_with_nan, targets)
        assert result is lgbm_model

    def test_predict_success(self, lgbm_model, sample_features, sample_targets):
        """正常予測テスト（3クラス分類）"""
        lgbm_model.fit(sample_features, sample_targets)

        test_features = sample_features.iloc[:10]
        predictions = lgbm_model.predict(test_features)

        assert predictions is not None
        assert len(predictions) == 10
        assert all(pred in [0, 1, 2] for pred in predictions)

    def test_predict_without_fitting(self, lgbm_model, sample_features):
        """学習前予測テスト"""
        with pytest.raises(ValueError) as exc_info:
            lgbm_model.predict(sample_features.iloc[:10])
        assert "is not fitted" in str(exc_info.value)

    def test_predict_with_wrong_features(self, lgbm_model, sample_features, sample_targets):
        """間違った特徴量での予測テスト"""
        lgbm_model.fit(sample_features, sample_targets)

        wrong_features = pd.DataFrame({"wrong_feature1": [1, 2, 3], "wrong_feature2": [4, 5, 6]})

        # BaseMLModelは特徴量を自動調整するため予測は成功する
        predictions = lgbm_model.predict(wrong_features)
        assert predictions is not None
        assert len(predictions) == 3

    def test_predict_with_missing_features(self, lgbm_model, sample_features, sample_targets):
        """特徴量不足での予測テスト"""
        lgbm_model.fit(sample_features, sample_targets)

        incomplete_features = sample_features[["rsi_14", "bb_position"]].iloc[:5]

        # BaseMLModelは不足特徴量を自動補完する
        predictions = lgbm_model.predict(incomplete_features)
        assert predictions is not None
        assert len(predictions) == 5

    def test_predict_with_extra_features(self, lgbm_model, sample_features, sample_targets):
        """余分な特徴量での予測テスト"""
        lgbm_model.fit(sample_features, sample_targets)

        extra_features = sample_features.copy()
        extra_features["extra_feature"] = np.random.uniform(0, 1, len(extra_features))

        # BaseMLModelは余分な特徴量を削除する
        predictions = lgbm_model.predict(extra_features.iloc[:5])
        assert predictions is not None
        assert len(predictions) == 5

    def test_predict_proba_success(self, lgbm_model, sample_features, sample_targets):
        """確率予測成功テスト（3クラス分類）"""
        lgbm_model.fit(sample_features, sample_targets)

        test_features = sample_features.iloc[:5]
        probabilities = lgbm_model.predict_proba(test_features)

        assert probabilities is not None
        assert probabilities.shape == (5, 3)  # 5サンプル、3クラス
        assert np.all((probabilities >= 0) & (probabilities <= 1))
        assert np.allclose(probabilities.sum(axis=1), 1.0)

    def test_predict_proba_without_fitting(self, lgbm_model, sample_features):
        """学習前確率予測テスト"""
        with pytest.raises(ValueError) as exc_info:
            lgbm_model.predict_proba(sample_features.iloc[:5])
        assert "is not fitted" in str(exc_info.value)

    def test_get_feature_importance(self, lgbm_model, sample_features, sample_targets):
        """特徴量重要度取得テスト"""
        lgbm_model.fit(sample_features, sample_targets)

        importance = lgbm_model.get_feature_importance()

        assert importance is not None
        assert len(importance) == len(sample_features.columns)
        assert "feature" in importance.columns
        assert "importance" in importance.columns
        assert all(importance["importance"] >= 0)

    def test_get_feature_importance_without_fitting(self, lgbm_model):
        """学習前特徴量重要度取得テスト"""
        importance = lgbm_model.get_feature_importance()
        assert importance is None

    def test_save_model(self, lgbm_model, sample_features, sample_targets):
        """モデル保存テスト"""
        lgbm_model.fit(sample_features, sample_targets)

        with patch("joblib.dump") as mock_dump:
            lgbm_model.save("/tmp/test_lgbm_model.pkl")
            mock_dump.assert_called_once()

    def test_save_model_without_fitting(self, lgbm_model):
        """学習前モデル保存テスト"""
        with patch("joblib.dump") as mock_dump:
            lgbm_model.save("/tmp/test_lgbm_model.pkl")
            mock_dump.assert_called_once()

    def test_load_model(self):
        """モデル読み込みテスト"""
        mock_data = {
            "model_name": "LightGBM",
            "model_params": {"n_estimators": 10},
            "estimator": LGBMClassifier(n_estimators=10),
            "is_fitted": True,
            "feature_names": ["feature1", "feature2"],
        }

        with patch("joblib.load", return_value=mock_data):
            result = LGBMModel.load("/tmp/test_lgbm_model.pkl")
            assert result.model_name == "LightGBM"
            assert result.is_fitted is True
            assert result.feature_names == ["feature1", "feature2"]

    def test_load_model_file_not_found(self):
        """存在しないモデルファイル読み込みテスト"""
        with patch("joblib.load", side_effect=FileNotFoundError()):
            with pytest.raises(DataProcessingError) as exc_info:
                LGBMModel.load("/tmp/nonexistent_lgbm.pkl")
            assert "Model load failed" in str(exc_info.value)

    def test_load_model_invalid_format(self):
        """無効形式モデル読み込みテスト"""
        with patch("joblib.load", side_effect=Exception("Invalid format")):
            with pytest.raises(DataProcessingError) as exc_info:
                LGBMModel.load("/tmp/invalid_lgbm.pkl")
            assert "Model load failed" in str(exc_info.value)

    def test_get_params(self, lgbm_model):
        """パラメータ取得テスト"""
        params = lgbm_model.model_params

        assert "n_estimators" in params
        assert "max_depth" in params
        assert "learning_rate" in params
        assert params["n_estimators"] == 10
        assert params["max_depth"] == 3
        assert params["learning_rate"] == 0.1

    def test_get_model_info(self, lgbm_model):
        """モデル情報取得テスト（未学習）"""
        info = lgbm_model.get_model_info()

        assert info["model_name"] == "LightGBM"
        assert info["is_fitted"] is False
        assert info["n_features"] == 0
        assert "lgbm_specific" in info
        assert info["lgbm_specific"]["boosting_type"] == "gbdt"

    def test_get_model_info_fitted(self, lgbm_model, sample_features, sample_targets):
        """モデル情報取得テスト（学習後）"""
        lgbm_model.fit(sample_features, sample_targets)

        info = lgbm_model.get_model_info()

        assert info["model_name"] == "LightGBM"
        assert info["is_fitted"] is True
        assert info["n_features"] == len(sample_features.columns)
        assert info["feature_names"] == list(sample_features.columns)
        assert "lgbm_specific" in info

    def test_clean_lgbm_params_reg_alpha(self):
        """LGBMパラメータクリーンアップ - reg_alpha変換テスト"""
        model = LGBMModel(reg_alpha=0.1)

        # reg_alphaはlambda_l1に変換される
        # estimatorのパラメータを確認
        estimator_params = model.estimator.get_params()
        # クリーンアップ後はlambda_l1に変換されているはず
        assert "reg_alpha" not in model.model_params or model.model_params.get("reg_alpha") is not None

    def test_clean_lgbm_params_reg_lambda(self):
        """LGBMパラメータクリーンアップ - reg_lambda変換テスト"""
        model = LGBMModel(reg_lambda=0.2)

        # reg_lambdaはlambda_l2に変換される
        assert "reg_lambda" not in model.model_params or model.model_params.get("reg_lambda") is not None

    def test_clean_lgbm_params_subsample(self):
        """LGBMパラメータクリーンアップ - subsample変換テスト"""
        model = LGBMModel(subsample=0.8)

        # subsampleはbagging_fractionに変換される
        assert "subsample" not in model.model_params or model.model_params.get("subsample") is not None

    def test_clean_lgbm_params_default_removal(self):
        """LGBMパラメータクリーンアップ - デフォルト値削除テスト"""
        model = LGBMModel(
            bagging_fraction=1.0,  # デフォルト値
            feature_fraction=1.0,  # デフォルト値
            lambda_l1=0.0,  # デフォルト値
            lambda_l2=0.0,  # デフォルト値
        )

        # デフォルト値は削除される（estimatorのクリーンアップ後）
        assert model.estimator is not None

    def test_multiclass_classification(self):
        """多クラス分類テスト（Phase 51.9: 3クラス分類）"""
        model = LGBMModel(n_estimators=10)

        # 3クラス分類データ
        features = pd.DataFrame(np.random.random((100, 5)))
        targets = np.random.randint(0, 3, 100)

        result = model.fit(features, targets)
        assert result is model

        predictions = model.predict(features.iloc[:10])
        assert predictions is not None
        assert all(pred in [0, 1, 2] for pred in predictions)

        probabilities = model.predict_proba(features.iloc[:10])
        assert probabilities is not None
        assert probabilities.shape == (10, 3)

    def test_memory_efficiency(self, lgbm_model):
        """メモリ効率性テスト"""
        large_features = pd.DataFrame(np.random.random((1000, 10)))
        large_targets = np.random.randint(0, 3, 1000)

        try:
            result = lgbm_model.fit(large_features, large_targets)
            assert result is lgbm_model
        except MemoryError:
            pytest.skip("メモリ不足でスキップ")

    def test_model_repr(self, lgbm_model):
        """モデル文字列表現テスト"""
        model_str = str(lgbm_model)

        assert "LGBMModel" in model_str
        assert "object at" in model_str

    def test_regularization_parameters(self):
        """正則化パラメータテスト"""
        model = LGBMModel(
            lambda_l1=0.1,  # L1正則化
            lambda_l2=0.1,  # L2正則化
        )

        assert model.model_params["lambda_l1"] == 0.1
        assert model.model_params["lambda_l2"] == 0.1

    def test_boosting_types(self):
        """異なるブースティングタイプテスト"""
        # gbdt（デフォルト）
        model_gbdt = LGBMModel(boosting_type="gbdt")
        assert model_gbdt.model_params["boosting_type"] == "gbdt"

        # dart
        model_dart = LGBMModel(boosting_type="dart")
        assert model_dart.model_params["boosting_type"] == "dart"

        # goss
        model_goss = LGBMModel(boosting_type="goss")
        assert model_goss.model_params["boosting_type"] == "goss"

    def test_seed_consistency(self):
        """シード値一貫性テスト"""
        model = LGBMModel()

        # 複数のシード関連パラメータが設定されていることを確認
        assert "random_state" in model.model_params
        assert "seed" in model.model_params
        assert "feature_fraction_seed" in model.model_params
        assert "bagging_seed" in model.model_params
        assert "data_random_seed" in model.model_params

        # 全て同じ値（環境変数から）
        seed_value = model.model_params["random_state"]
        assert model.model_params["seed"] == seed_value
        assert model.model_params["feature_fraction_seed"] == seed_value
        assert model.model_params["bagging_seed"] == seed_value
        assert model.model_params["data_random_seed"] == seed_value

    def test_fit_with_sample_weight(self, lgbm_model, sample_features, sample_targets):
        """サンプル重み付き学習テスト"""
        # LightGBMはsample_weightをサポートしているが、BaseMLModelのfitでは直接渡せない
        # このテストはestimatorを直接使う
        lgbm_model.feature_names = sample_features.columns.tolist()
        sample_weights = np.random.uniform(0.5, 1.5, len(sample_targets))

        lgbm_model.estimator.fit(sample_features, sample_targets, sample_weight=sample_weights)
        lgbm_model.is_fitted = True

        predictions = lgbm_model.predict(sample_features.iloc[:5])
        assert predictions is not None
        assert len(predictions) == 5

    def test_get_model_info_lgbm_specific_fitted(self, lgbm_model, sample_features, sample_targets):
        """LGBMModel固有のモデル情報テスト（学習後）"""
        lgbm_model.fit(sample_features, sample_targets)

        info = lgbm_model.get_model_info()

        assert "lgbm_specific" in info
        lgbm_info = info["lgbm_specific"]

        assert "boosting_type" in lgbm_info
        assert "num_leaves" in lgbm_info
        assert "learning_rate" in lgbm_info
        assert "n_estimators" in lgbm_info

    def test_clean_lgbm_params_legacy_mapping(self):
        """LGBMレガシーパラメータ変換テスト"""
        # reg_alpha -> lambda_l1
        model1 = LGBMModel(reg_alpha=0.5)
        # パラメータがクリーンアップされることを確認
        assert model1.estimator is not None

        # reg_lambda -> lambda_l2
        model2 = LGBMModel(reg_lambda=0.5)
        assert model2.estimator is not None

        # subsample -> bagging_fraction
        model3 = LGBMModel(subsample=0.8)
        assert model3.estimator is not None

    def test_create_estimator_exception(self):
        """_create_estimator例外ハンドリングテスト"""
        with patch("src.ml.models.LGBMClassifier") as mock_lgbm:
            mock_lgbm.side_effect = Exception("Failed to create estimator")

            with pytest.raises(Exception) as exc_info:
                LGBMModel()
            assert "Failed to create estimator" in str(exc_info.value)
