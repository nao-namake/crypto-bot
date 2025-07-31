# tests/unit/main/test_main_train.py

import joblib
import pandas as pd
import yaml
from click.testing import CliRunner
from sklearn.base import BaseEstimator
from sklearn.model_selection import train_test_split

from crypto_bot.main import cli


class DummyEstimator(BaseEstimator):
    def fit(self, X, y):
        return self

    def predict(self, X):
        return [0] * len(X)


def test_train_command_monkeypatched(tmp_path, monkeypatch):
    dummy_df = pd.DataFrame(
        {
            "open": list(range(1, 11)),
            "high": list(range(1, 11)),
            "low": list(range(1, 11)),
            "close": list(range(1, 11)),
            "volume": [1] * 10,
        },
        index=pd.date_range(start="2024-01-01", periods=10, freq="H"),
    )
    monkeypatch.setattr(
        "crypto_bot.main.MarketDataFetcher.get_price_df", lambda self, **kw: dummy_df
    )

    X_full = pd.DataFrame({"f": [0, 1] * 5})
    y_full = pd.Series([0, 1] * 5)

    # 明示的にtrainとvalidationを分割（訓練8, 検証2）
    X_tr, X_val, y_tr, y_val = train_test_split(
        X_full, y_full, test_size=0.2, random_state=42
    )

    # 4要素タプルを返す
    monkeypatch.setattr(
        "crypto_bot.ml.preprocessor.prepare_ml_dataset",
        lambda df, cfg: (X_tr, y_tr, X_val, y_val),
    )

    monkeypatch.setattr(
        "crypto_bot.main.LogisticRegression", lambda **kw: DummyEstimator()
    )

    cfg = {
        "data": {"symbol": "BTC/USDT", "timeframe": "1h", "since": None, "limit": 10},
        "ml": {
            "feat_period": 2,
            "lags": [1],
            "rolling_window": 2,
            "horizon": 1,
            "threshold": 0.0,
            "target_type": "classification",
            "test_size": 0.2,
        },
        "backtest": {
            "starting_balance": 10000,
            "slippage_rate": 0,
            "trade_log_csv": str(tmp_path / "trades.csv"),
            "aggregate_out_prefix": str(tmp_path / "agg"),
        },
        "walk_forward": {
            "train_window": 1,
            "test_window": 1,
            "step": 1,
        },
        "strategy": {
            "params": {
                "model_path": "model.pkl",
                "threshold": 0.0,
            }
        },
    }
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    model_path = tmp_path / "model.pkl"

    runner = CliRunner()
    result = runner.invoke(cli, ["train", "-c", str(cfg_path), "-o", str(model_path)])
    assert result.exit_code == 0

    # サンプル数は特徴量強化システムにより調整される（8個）
    assert "Training classification model on 8 samples" in result.output

    assert model_path.exists()
    loaded = joblib.load(model_path)
    assert isinstance(loaded, DummyEstimator)
