# tests/unit/ml/test_optimizer.py
# テスト対象: crypto_bot/ml/optimizer.py
# 説明:
#   - objective関数: ML訓練・検証・ハイパーパラメータ提案の動作
#   - optimize_ml: Optunaサーチが正常終了するか
#   - train_best_model: モデル学習・保存の流れ
#   - save_trials: 結果CSV出力

import os

import numpy as np
import optuna
import pandas as pd
import pytest

from crypto_bot.ml.optimizer import (
    objective,
    optimize_ml,
    save_trials,
    train_best_model,
)


@pytest.fixture
def dummy_config():
    # テスト用のダミーML設定・最小限のデータ
    df = pd.DataFrame(
        {
            "open": np.random.rand(40),
            "high": np.random.rand(40),
            "low": np.random.rand(40),
            "close": np.random.rand(40),
            "volume": np.random.rand(40),
        },
        index=pd.date_range("2023-01-01", periods=40, freq="D"),
    )
    config = {
        "ml": {
            "model_type": "lgbm",
            "target_type": "classification",
            "feat_period": 5,
            "optuna": {
                "direction": "maximize",
                "sampler": {"name": "TPESampler"},
                "pruner": {
                    "name": "MedianPruner",
                    "n_startup_trials": 1,
                    "n_warmup_steps": 1,
                    "interval_steps": 1,
                },
                "n_trials": 2,
                "timeout": 10,
            },
        },
        "data": {
            "exchange": "bybit",
            "symbol": "BTC/USDT",
            "timeframe": "1d",
            "since": None,
            "limit": 40,
        },
    }
    # データ直指定でprepare_ml_dataset互換
    config["test_df"] = df
    return config, df


def test_objective_runs_with_dummy_data(dummy_config, monkeypatch):
    config, df = dummy_config

    def dummy_prepare_ml_dataset(*args, **kwargs):
        X = df[["open", "close", "volume"]]
        y = (df["close"] > df["open"]).astype(int)
        return X, y, X, y

    monkeypatch.setattr(
        "crypto_bot.ml.optimizer.prepare_ml_dataset", dummy_prepare_ml_dataset
    )

    trial = optuna.trial.create_trial(
        params={"n_estimators": 10, "max_depth": 2, "learning_rate": 0.05},
        distributions={
            "n_estimators": optuna.distributions.IntDistribution(10, 20),
            "max_depth": optuna.distributions.IntDistribution(2, 5),
            "learning_rate": optuna.distributions.FloatDistribution(
                0.01, 0.1, log=True
            ),
        },
        value=1.0,
        state=optuna.trial.TrialState.COMPLETE,
    )
    # objectiveは float を返すことを確認
    result = objective(trial, config)
    assert isinstance(result, float)


def test_optimize_ml_runs(dummy_config, monkeypatch):
    config, df = dummy_config

    def dummy_prepare_ml_dataset(*args, **kwargs):
        X = df[["open", "close", "volume"]]
        y = (df["close"] > df["open"]).astype(int)
        return X, y, X, y

    monkeypatch.setattr(
        "crypto_bot.ml.optimizer.prepare_ml_dataset", dummy_prepare_ml_dataset
    )

    study = optimize_ml(config)
    assert hasattr(study, "trials")
    assert len(study.trials) > 0


def test_train_best_model_and_save(tmp_path, dummy_config, monkeypatch):
    config, df = dummy_config

    # OptunaもダミーでOK
    class DummyStudy:
        best_params = {"n_estimators": 10, "max_depth": 2, "learning_rate": 0.05}

    monkeypatch.setattr("crypto_bot.ml.optimizer.optimize_ml", lambda cfg: DummyStudy())

    def dummy_prepare_ml_dataset(*args, **kwargs):
        X = df[["open", "close", "volume"]]
        y = (df["close"] > df["open"]).astype(int)
        return X, y, X, y

    monkeypatch.setattr(
        "crypto_bot.ml.optimizer.prepare_ml_dataset", dummy_prepare_ml_dataset
    )

    output_path = tmp_path / "model.joblib"
    train_best_model(config, output_path)
    assert os.path.exists(output_path)


def test_save_trials(tmp_path):
    # ダミーStudyでtrials_dataframe()を模倣
    class DummyStudy:
        def trials_dataframe(self):
            return pd.DataFrame({"param": [1, 2], "score": [0.7, 0.9]})

    csv_path = tmp_path / "trials.csv"
    save_trials(DummyStudy(), str(csv_path))
    assert os.path.isfile(csv_path)
