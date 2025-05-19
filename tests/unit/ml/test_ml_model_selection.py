import pytest
from lightgbm import LGBMClassifier
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from crypto_bot.ml.model import create_model
from crypto_bot.ml.optimizer import train_best_model


# 3-1: model.create_model の単体テスト
@pytest.mark.parametrize(
    ("mt", "expected_cls"),
    [("lgbm", LGBMClassifier), ("rf", RandomForestClassifier), ("xgb", XGBClassifier)],
)
def test_create_model_registry(mt, expected_cls):
    model = create_model(mt, random_state=42)
    assert isinstance(model, expected_cls)


def test_create_model_bad_type():
    with pytest.raises(ValueError):
        create_model("hogehoge")


# 3-2: train_best_model が model_type を尊重して返すか
def test_train_best_model_respects_model_type(tmp_path):
    # ダミーデータ
    X, y = make_classification(n_samples=200, n_features=5, random_state=0)
    X_tr, X_te = X[:160], X[160:]
    y_tr, y_te = y[:160], y[160:]

    # cfg を組み立て
    cfg = {
        "ml": {
            "model_type": "rf",
            "optuna": {"n_trials": 1, "timeout": 10},  # 小 trial で終わるように
        },
        "output": {"model_path": str(tmp_path / "mdl.pkl")},
    }
    model = train_best_model(cfg, X_tr, y_tr, X_te, y_te)
    assert isinstance(model, RandomForestClassifier)
