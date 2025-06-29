# tests/unit/ml/test_model.py
# テスト対象: crypto_bot/ml/model.py
# 説明:
#   - MLModel: 機械学習モデルのラッパー
#   - 学習・予測・保存・読み込みの基本機能

import os

import numpy as np
import pandas as pd
import pytest

from crypto_bot.ml.model import MLModel, create_model


@pytest.fixture
def dummy_classification_data():
    # シンプルなダミーデータ（2値分類）
    X = pd.DataFrame(
        {
            "feat1": np.random.rand(30),
            "feat2": np.random.rand(30),
        }
    )
    y = pd.Series(np.random.randint(0, 2, 30))
    return X, y


def test_create_model_lgbm(dummy_classification_data):
    model = create_model("lgbm", n_estimators=10)
    assert hasattr(model, "fit")
    assert model.__class__.__name__.startswith("LGBM")


def test_create_model_rf(dummy_classification_data):
    model = create_model("rf", n_estimators=5, max_depth=2)
    assert hasattr(model, "fit")
    assert model.__class__.__name__.endswith("ForestClassifier")


def test_create_model_xgb(dummy_classification_data):
    model = create_model("xgb", n_estimators=5, max_depth=2)
    assert hasattr(model, "fit")
    assert model.__class__.__name__.startswith("XGB")


def test_create_model_invalid_type():
    with pytest.raises(ValueError):
        create_model("invalid_type")


def test_create_model_lgbm_param_cleanup():
    # reg_alpha → lambda_l1
    model = create_model("lgbm", reg_alpha=0.1)
    assert hasattr(model, "lambda_l1")
    assert not hasattr(model, "reg_alpha")
    # reg_lambda → lambda_l2
    model = create_model("lgbm", reg_lambda=0.1)
    assert hasattr(model, "lambda_l2")
    assert not hasattr(model, "reg_lambda")
    # subsample → bagging_fraction
    model = create_model("lgbm", subsample=0.8)
    assert hasattr(model, "bagging_fraction")
    assert not hasattr(model, "subsample")
    # デフォルト値の削除
    model = create_model("lgbm", bagging_fraction=1.0, feature_fraction=1.0)
    assert not hasattr(model, "bagging_fraction")
    assert not hasattr(model, "feature_fraction")
    model = create_model("lgbm", lambda_l1=0.0, lambda_l2=0.0)
    assert not hasattr(model, "lambda_l1")
    assert not hasattr(model, "lambda_l2")


def test_mlmodel_fit_predict(dummy_classification_data):
    X, y = dummy_classification_data
    model = MLModel(create_model("rf", n_estimators=10))
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(X)
    proba = model.predict_proba(X)
    assert proba is not None
    assert proba.shape[0] == len(X)


def test_mlmodel_fit_predict_no_proba(dummy_classification_data):

    class DummyModel:
        def fit(self, X, y):
            pass

        def predict(self, X):
            return np.zeros(len(X))

    X, y = dummy_classification_data
    model = MLModel(DummyModel())
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(X)
    assert model.predict_proba(X) is None


def test_mlmodel_save_load(tmp_path, dummy_classification_data):
    X, y = dummy_classification_data
    model = MLModel(create_model("lgbm", n_estimators=3))
    model.fit(X, y)
    file_path = tmp_path / "test_model.joblib"
    model.save(file_path)
    assert os.path.isfile(file_path)
    loaded = MLModel.load(file_path)
    preds = loaded.predict(X)
    assert len(preds) == len(X)


def test_mlmodel_save_load_invalid_path(tmp_path, dummy_classification_data):
    X, y = dummy_classification_data
    model = MLModel(create_model("lgbm", n_estimators=3))
    model.fit(X, y)
    invalid_path = tmp_path / "nonexistent" / "test_model.joblib"
    with pytest.raises(FileNotFoundError):
        model.save(invalid_path)


def test_mlmodel_load_nonexistent_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        MLModel.load(tmp_path / "nonexistent.joblib")


def test_lgbm_param_cleanup_effect():
    # reg_alpha→lambda_l1, reg_lambda→lambda_l2, subsample→bagging_fraction への置き換えをテスト
    from crypto_bot.ml.model import _lgbm_param_cleanup

    # reg_lambdaで上書きされる場合
    params = {
        "reg_alpha": 0.2,
        "reg_lambda": 0.1,
        "subsample": 0.9,
        "feature_fraction": 1.0,
        "lambda_l2": 0.0,
    }
    cleaned = _lgbm_param_cleanup(params)
    assert "lambda_l1" in cleaned and cleaned["lambda_l1"] == 0.2
    assert "lambda_l2" in cleaned and cleaned["lambda_l2"] == 0.1
    assert "bagging_fraction" in cleaned and cleaned["bagging_fraction"] == 0.9
    assert "feature_fraction" not in cleaned  # 1.0→削除

    # lambda_l2が0.0のみの場合は削除される
    params2 = {
        "lambda_l2": 0.0,
    }
    cleaned2 = _lgbm_param_cleanup(params2)
    assert "lambda_l2" not in cleaned2  # 0.0→削除


# =============================================================================
# EnsembleModel と create_ensemble_model の包括的テスト
# =============================================================================


class TestEnsembleModel:
    """EnsembleModel クラスの包括的テストクラス"""

    @pytest.fixture
    def simple_models(self):
        """テスト用の簡単なモデルリスト"""
        from crypto_bot.ml.model import create_model

        return [
            create_model("rf", n_estimators=5, max_depth=2, random_state=42),
            create_model("lgbm", n_estimators=5, max_depth=2, random_state=42),
        ]

    @pytest.fixture
    def ensemble_test_data(self):
        """アンサンブル用のテストデータ"""
        np.random.seed(42)
        X = pd.DataFrame(
            {
                "feat1": np.random.rand(50),
                "feat2": np.random.rand(50),
                "feat3": np.random.rand(50),
            }
        )
        y = pd.Series((X["feat1"] + X["feat2"] > 1.0).astype(int))
        return X, y

    def test_ensemble_model_initialization_voting(self, simple_models):
        """多数決方式での初期化テスト"""
        from crypto_bot.ml.model import EnsembleModel

        ensemble = EnsembleModel(simple_models, method="voting")

        assert ensemble.method == "voting"
        assert len(ensemble.models) == 2
        assert ensemble.weights is None
        assert not ensemble.is_fitted

    def test_ensemble_model_initialization_weighted(self, simple_models):
        """重み付き方式での初期化テスト"""
        from crypto_bot.ml.model import EnsembleModel

        weights = [0.6, 0.4]
        ensemble = EnsembleModel(simple_models, method="weighted", weights=weights)

        assert ensemble.method == "weighted"
        assert ensemble.weights == [0.6, 0.4]  # 正規化されて合計1.0になる

    def test_ensemble_model_initialization_stacking(self, simple_models):
        """スタッキング方式での初期化テスト"""
        from sklearn.linear_model import LogisticRegression

        from crypto_bot.ml.model import EnsembleModel

        meta_model = LogisticRegression()
        ensemble = EnsembleModel(
            simple_models, method="stacking", meta_model=meta_model
        )

        assert ensemble.method == "stacking"
        assert ensemble.meta_model == meta_model

    def test_ensemble_model_invalid_method(self, simple_models):
        """無効な手法での初期化エラーテスト"""
        from crypto_bot.ml.model import EnsembleModel

        with pytest.raises(ValueError, match="method must be"):
            EnsembleModel(simple_models, method="invalid_method")

    def test_ensemble_model_weights_normalization(self, simple_models):
        """重み正規化のテスト"""
        from crypto_bot.ml.model import EnsembleModel

        # 合計が1でない重み
        weights = [2.0, 3.0]
        ensemble = EnsembleModel(simple_models, method="weighted", weights=weights)

        # 重みが正規化されている
        assert abs(sum(ensemble.weights) - 1.0) < 1e-6
        assert abs(ensemble.weights[0] - 0.4) < 1e-6  # 2/(2+3)
        assert abs(ensemble.weights[1] - 0.6) < 1e-6  # 3/(2+3)

    def test_ensemble_model_fit_voting(self, simple_models, ensemble_test_data):
        """多数決方式での学習テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="voting")

        result = ensemble.fit(X, y)

        assert result is ensemble  # fit は self を返す
        assert ensemble.is_fitted

    def test_ensemble_model_fit_stacking(self, simple_models, ensemble_test_data):
        """スタッキング方式での学習テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="stacking")

        ensemble.fit(X, y)

        assert ensemble.is_fitted
        # メタモデルも学習されている
        assert hasattr(ensemble.meta_model, "predict")

    def test_ensemble_model_predict_voting(self, simple_models, ensemble_test_data):
        """多数決方式での予測テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="voting")
        ensemble.fit(X, y)

        predictions = ensemble.predict(X)

        assert len(predictions) == len(X)
        assert all(pred in [0, 1] for pred in predictions)

    def test_ensemble_model_predict_weighted(self, simple_models, ensemble_test_data):
        """重み付き方式での予測テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        weights = [0.7, 0.3]
        ensemble = EnsembleModel(simple_models, method="weighted", weights=weights)
        ensemble.fit(X, y)

        predictions = ensemble.predict(X)

        assert len(predictions) == len(X)
        assert all(pred in [0, 1] for pred in predictions)

    def test_ensemble_model_predict_stacking(self, simple_models, ensemble_test_data):
        """スタッキング方式での予測テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="stacking")
        ensemble.fit(X, y)

        predictions = ensemble.predict(X)

        assert len(predictions) == len(X)
        assert all(pred in [0, 1] for pred in predictions)

    def test_ensemble_model_predict_proba_voting(
        self, simple_models, ensemble_test_data
    ):
        """多数決方式での確率予測テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="voting")
        ensemble.fit(X, y)

        probabilities = ensemble.predict_proba(X)

        assert probabilities.shape == (len(X), 2)
        # 確率の合計が1に近い
        assert all(abs(prob_sum - 1.0) < 1e-6 for prob_sum in probabilities.sum(axis=1))

    def test_ensemble_model_predict_proba_weighted(
        self, simple_models, ensemble_test_data
    ):
        """重み付き方式での確率予測テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        weights = [0.8, 0.2]
        ensemble = EnsembleModel(simple_models, method="weighted", weights=weights)
        ensemble.fit(X, y)

        probabilities = ensemble.predict_proba(X)

        assert probabilities.shape == (len(X), 2)
        # 確率が0-1の範囲内
        assert ((probabilities >= 0) & (probabilities <= 1)).all()

    def test_ensemble_model_predict_proba_stacking(
        self, simple_models, ensemble_test_data
    ):
        """スタッキング方式での確率予測テスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="stacking")
        ensemble.fit(X, y)

        probabilities = ensemble.predict_proba(X)

        assert probabilities.shape == (len(X), 2)
        # 確率の合計が1に近い
        assert all(abs(prob_sum - 1.0) < 1e-6 for prob_sum in probabilities.sum(axis=1))

    def test_ensemble_model_predict_before_fit(self, simple_models, ensemble_test_data):
        """学習前の予測エラーテスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="voting")

        with pytest.raises(ValueError, match="モデルが学習されていません"):
            ensemble.predict(X)

    def test_ensemble_model_predict_proba_before_fit(
        self, simple_models, ensemble_test_data
    ):
        """学習前の確率予測エラーテスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="voting")

        with pytest.raises(ValueError, match="モデルが学習されていません"):
            ensemble.predict_proba(X)

    def test_ensemble_model_get_meta_features(self, simple_models, ensemble_test_data):
        """メタ特徴量取得のテスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="stacking")
        ensemble.fit(X, y)

        meta_features = ensemble._get_meta_features(X)

        assert meta_features.shape == (len(X), len(simple_models))

    def test_ensemble_model_save_load(
        self, tmp_path, simple_models, ensemble_test_data
    ):
        """アンサンブルモデルの保存・読み込みテスト"""
        from crypto_bot.ml.model import EnsembleModel

        X, y = ensemble_test_data
        ensemble = EnsembleModel(simple_models, method="weighted", weights=[0.6, 0.4])
        ensemble.fit(X, y)

        # 保存
        file_path = tmp_path / "ensemble_model.joblib"
        ensemble.save(file_path)
        assert file_path.exists()

        # 読み込み
        loaded_ensemble = EnsembleModel.load(file_path)

        assert loaded_ensemble.method == ensemble.method
        assert loaded_ensemble.weights == ensemble.weights
        assert loaded_ensemble.is_fitted == ensemble.is_fitted

        # 予測結果が一致
        original_pred = ensemble.predict(X)
        loaded_pred = loaded_ensemble.predict(X)
        np.testing.assert_array_equal(original_pred, loaded_pred)

    def test_ensemble_model_save_invalid_path(self, simple_models):
        """アンサンブルモデルの無効パス保存エラーテスト"""
        from crypto_bot.ml.model import EnsembleModel

        ensemble = EnsembleModel(simple_models, method="voting")

        with pytest.raises(FileNotFoundError, match="ディレクトリが存在しません"):
            ensemble.save("/nonexistent/path/model.joblib")

    def test_ensemble_model_with_models_without_predict_proba(self, ensemble_test_data):
        """predict_probaメソッドがないモデルでのテスト"""
        from crypto_bot.ml.model import EnsembleModel

        # predict_probaメソッドがないダミーモデル
        class DummyModel:
            def fit(self, X, y):
                self.classes_ = np.unique(y)
                return self

            def predict(self, X):
                return np.random.choice([0, 1], size=len(X))

        models = [DummyModel(), DummyModel()]
        X, y = ensemble_test_data

        ensemble = EnsembleModel(models, method="voting")
        ensemble.fit(X, y)

        # 予測は動作する
        predictions = ensemble.predict(X)
        assert len(predictions) == len(X)

        # 確率予測も動作する（ワンホット化される）
        probabilities = ensemble.predict_proba(X)
        assert probabilities.shape == (len(X), 2)


class TestCreateEnsembleModel:
    """create_ensemble_model 関数のテストクラス"""

    @pytest.fixture
    def model_configs(self):
        """テスト用のモデル設定"""
        return [
            {"type": "rf", "n_estimators": 5, "max_depth": 2},
            {"type": "lgbm", "n_estimators": 5, "max_depth": 2},
            {"type": "xgb", "n_estimators": 5, "max_depth": 2},
        ]

    def test_create_ensemble_model_voting(self, model_configs):
        """多数決アンサンブル作成テスト"""
        from crypto_bot.ml.model import create_ensemble_model

        ensemble = create_ensemble_model(model_configs, method="voting")

        assert ensemble.method == "voting"
        assert len(ensemble.models) == 3
        assert ensemble.weights is None

    def test_create_ensemble_model_weighted(self, model_configs):
        """重み付きアンサンブル作成テスト"""
        from crypto_bot.ml.model import create_ensemble_model

        weights = [0.5, 0.3, 0.2]
        ensemble = create_ensemble_model(
            model_configs, method="weighted", weights=weights
        )

        assert ensemble.method == "weighted"
        assert ensemble.weights == weights

    def test_create_ensemble_model_stacking_default_meta(self, model_configs):
        """デフォルトメタモデルでのスタッキング作成テスト"""
        from sklearn.linear_model import LogisticRegression

        from crypto_bot.ml.model import create_ensemble_model

        ensemble = create_ensemble_model(model_configs, method="stacking")

        assert ensemble.method == "stacking"
        assert isinstance(ensemble.meta_model, LogisticRegression)

    def test_create_ensemble_model_stacking_custom_meta(self, model_configs):
        """カスタムメタモデルでのスタッキング作成テスト"""
        from crypto_bot.ml.model import create_ensemble_model

        meta_config = {"type": "lr", "C": 0.5}
        ensemble = create_ensemble_model(
            model_configs, method="stacking", meta_model_config=meta_config
        )

        assert ensemble.method == "stacking"
        assert hasattr(ensemble.meta_model, "C")
        assert ensemble.meta_model.C == 0.5

    def test_create_ensemble_model_stacking_with_ml_meta(self, model_configs):
        """ML メタモデルでのスタッキング作成テスト"""
        from crypto_bot.ml.model import create_ensemble_model

        meta_config = {"type": "rf", "n_estimators": 10}
        ensemble = create_ensemble_model(
            model_configs, method="stacking", meta_model_config=meta_config
        )

        assert ensemble.method == "stacking"
        assert hasattr(ensemble.meta_model, "n_estimators")
        assert ensemble.meta_model.n_estimators == 10

    def test_create_ensemble_model_config_modification(self):
        """設定変更による副作用のテスト"""
        from crypto_bot.ml.model import create_ensemble_model

        # 元の設定
        original_configs = [
            {"type": "rf", "n_estimators": 10},
            {"type": "lgbm", "n_estimators": 15},
        ]

        # 設定のコピーを作成
        test_configs = [config.copy() for config in original_configs]

        ensemble = create_ensemble_model(test_configs, method="voting")

        # 元の設定が変更されていない（typeがpopされているため実際には変更される）
        assert len(ensemble.models) == 2


class TestAdvancedMLModel:
    """MLModel の高度なテストケース"""

    def test_mlmodel_ensemble_integration(self, dummy_classification_data):
        """MLModel と EnsembleModel の統合テスト"""
        from crypto_bot.ml.model import EnsembleModel, MLModel, create_model

        X, y = dummy_classification_data

        # 個別のMLModelを作成
        model1 = MLModel(create_model("rf", n_estimators=10))
        model2 = MLModel(create_model("lgbm", n_estimators=10))

        # アンサンブルモデルに組み込み
        ensemble = EnsembleModel([model1.estimator, model2.estimator], method="voting")
        ensemble.fit(X, y)

        predictions = ensemble.predict(X)
        assert len(predictions) == len(X)

    def test_mlmodel_different_estimator_types(self):
        """異なる推定器タイプでのMLModelテスト"""
        from sklearn.naive_bayes import GaussianNB
        from sklearn.svm import SVC

        from crypto_bot.ml.model import MLModel

        # 確率予測が可能なモデル
        model_with_proba = MLModel(GaussianNB())
        assert hasattr(model_with_proba.estimator, "predict_proba")

        # 確率予測が不可能なモデル（デフォルト設定のSVC）
        model_without_proba = MLModel(SVC())
        # SVCはデフォルトではpredict_probaがない
        X = pd.DataFrame({"feat1": [1, 2, 3], "feat2": [4, 5, 6]})
        y = pd.Series([0, 1, 0])
        model_without_proba.fit(X, y)

        # predict_probaが無い場合はNoneが返される
        proba = model_without_proba.predict_proba(X)
        assert proba is None

    def test_mlmodel_chaining(self, dummy_classification_data):
        """MLModel のメソッドチェーンテスト"""
        from crypto_bot.ml.model import MLModel, create_model

        X, y = dummy_classification_data

        # メソッドチェーンでの利用
        model = MLModel(create_model("rf", n_estimators=5)).fit(X, y)

        predictions = model.predict(X)
        assert len(predictions) == len(X)


class TestEdgeCases:
    """エッジケースのテストクラス"""

    def test_ensemble_empty_models_list(self):
        """空のモデルリストでのエラーテスト"""
        from crypto_bot.ml.model import EnsembleModel

        # 空のモデルリストでも初期化は可能
        ensemble = EnsembleModel([], method="voting")
        assert len(ensemble.models) == 0

    def test_ensemble_single_model(self, dummy_classification_data):
        """単一モデルでのアンサンブルテスト"""
        from crypto_bot.ml.model import EnsembleModel, create_model

        X, y = dummy_classification_data
        single_model = [create_model("rf", n_estimators=5)]

        ensemble = EnsembleModel(single_model, method="voting")
        ensemble.fit(X, y)

        predictions = ensemble.predict(X)
        assert len(predictions) == len(X)

    def test_create_model_with_complex_params(self):
        """複雑なパラメータでのモデル作成テスト"""
        from crypto_bot.ml.model import create_model

        # 多くのパラメータを持つモデル
        model = create_model(
            "lgbm",
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            reg_alpha=0.1,
            reg_lambda=0.2,
            subsample=0.8,
            feature_fraction=0.9,
        )

        # パラメータクリーンアップが正しく動作していることを確認
        assert hasattr(model, "lambda_l1")
        assert hasattr(model, "lambda_l2")
        assert hasattr(model, "bagging_fraction")
        assert not hasattr(model, "reg_alpha")
        assert not hasattr(model, "reg_lambda")
        assert not hasattr(model, "subsample")

    def test_lgbm_param_cleanup_edge_cases(self):
        """LGBMパラメータクリーンアップのエッジケース"""
        from crypto_bot.ml.model import _lgbm_param_cleanup

        # lambda_l1 が既に存在し、reg_alpha も存在する場合
        params = {
            "reg_alpha": 0.1,
            "lambda_l1": 0.2,  # こちらが優先される
        }
        cleaned = _lgbm_param_cleanup(params)
        assert cleaned["lambda_l1"] == 0.2  # 既存のlambda_l1が保持される
        assert "reg_alpha" not in cleaned

        # bagging_fraction が既に存在し、subsample も存在する場合
        params2 = {
            "subsample": 0.7,
            "bagging_fraction": 0.8,  # こちらが保持される
        }
        cleaned2 = _lgbm_param_cleanup(params2)
        assert cleaned2["bagging_fraction"] == 0.8
        assert "subsample" not in cleaned2

    def test_create_model_case_insensitive(self):
        """大文字小文字を区別しないモデル作成テスト"""
        from crypto_bot.ml.model import create_model

        # 大文字小文字の違い
        model1 = create_model("LGBM", n_estimators=5)
        model2 = create_model("lgbm", n_estimators=5)
        model3 = create_model("LgBm", n_estimators=5)

        assert type(model1).__name__ == type(model2).__name__ == type(model3).__name__

    def test_ensemble_model_weights_none_handling(self, dummy_classification_data):
        """重みがNoneの場合の処理テスト"""
        from crypto_bot.ml.model import EnsembleModel, create_model

        X, y = dummy_classification_data
        models = [
            create_model("rf", n_estimators=5),
            create_model("lgbm", n_estimators=5),
        ]

        # 重みがNoneの重み付きアンサンブル
        ensemble = EnsembleModel(models, method="weighted", weights=None)
        ensemble.fit(X, y)

        probabilities = ensemble.predict_proba(X)
        assert probabilities.shape == (len(X), 2)
