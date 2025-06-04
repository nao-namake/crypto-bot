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
