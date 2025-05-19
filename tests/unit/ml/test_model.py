# tests/unit/test_model.py
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from crypto_bot.ml.model import MLModel


@pytest.fixture
def simple_data():
    # 2クラス問題のダミー
    X = pd.DataFrame({"f1": [0, 1, 0, 1], "f2": [1, 1, 0, 0]})
    y = pd.Series([0, 1, 0, 1])
    return X, y


def test_fit_predict(simple_data, tmp_path):
    X, y = simple_data
    base = LogisticRegression()
    m = MLModel(base)
    m.fit(X, y)
    preds = m.predict(X)
    # 学習データは完璧に分けられる
    assert np.array_equal(preds, y.values)

    # 保存→読み込みで同一の振る舞い
    p = tmp_path / "mdl.pkl"
    m.save(p)
    m2 = MLModel.load(p)
    preds2 = m2.predict(X)
    assert np.array_equal(preds2, preds)
