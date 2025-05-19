# tests/unit/test_ml_optimizer.py

import numpy as np
import optuna
import pytest

from crypto_bot.ml.optimizer import objective, optimize_ml


@pytest.fixture
def small_ohlcv():
    """
    10 行だけのダミー OHLCV DataFrame を返す。
    prepare_ml_dataset のモックで使います。
    """
    # 本来は pandas.DataFrame ですが、objective 内では配列しか使わないので numpy だけでも OK
    close = np.arange(100, 110)
    # ダミーデータとして numpy 配列そのまま返すように準備
    return close


def test_objective_monkeypatch(monkeypatch, small_ohlcv):
    # prepare_ml_dataset をモックして X_train, y_train, X_val, y_val を返す
    def fake_prepare_ml_dataset(cfg):
        # X: (n_samples, n_features), y: (n_samples,)
        X = small_ohlcv.reshape(-1, 1)
        y = np.zeros(len(X), dtype=int)
        return X, y, X, y

    monkeypatch.setattr(
        "crypto_bot.ml.optimizer.prepare_ml_dataset",
        fake_prepare_ml_dataset,
    )

    # DummyTrial で suggest_* 系は最低値を返す
    class DummyTrial:
        def suggest_int(self, name, a, b):
            return a

        def suggest_loguniform(self, name, low, high):
            return low

    # コンフィグは objective に渡る最低限だけ指定しておく
    dummy_config = {"ml": {}}
    score = objective(DummyTrial(), dummy_config)

    # 全て 0 ラベルなので accuracy は必ず 1.0
    assert score == 1.0


def test_optimize_ml_runs_one_trial(monkeypatch):
    # prepare_ml_dataset をモック
    monkeypatch.setattr(
        "crypto_bot.ml.optimizer.prepare_ml_dataset",
        lambda cfg: ([], [], [], []),
    )

    # MLModel をモックして学習時間をゼロに
    class DummyModel:
        def __init__(self, params):
            pass

        def fit(self, X, y):
            return self

        def predict(self, X):
            return []

    monkeypatch.setattr("crypto_bot.ml.optimizer.MLModel", DummyModel)

    # 1トライアルだけ回るようにコンフィグを設定
    cfg = {
        "ml": {
            "optuna": {
                "n_trials": 1,
                "timeout": 1,
                "direction": "maximize",
                "sampler": {"name": "RandomSampler"},
                "pruner": {
                    "name": "MedianPruner",
                    "n_startup_trials": 1,
                    "n_warmup_steps": 1,
                    "interval_steps": 1,
                },
            }
        }
    }

    study = optimize_ml(cfg)
    # ちゃんと最良トライアルが返ってきていること
    assert isinstance(study, optuna.Study)
    assert study.best_trial is not None
