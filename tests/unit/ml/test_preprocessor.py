import numpy as np
import pandas as pd
import pytest

from crypto_bot.ml.preprocessor import FeatureEngineer, build_ml_pipeline


@pytest.fixture
def ohlcv_df():
    idx = pd.date_range("2023-01-01", periods=30, freq="H")
    data = {
        "open": np.random.rand(30),
        "high": np.random.rand(30),
        "low": np.random.rand(30),
        "close": np.random.rand(30),
        "volume": np.random.rand(30),
    }
    return pd.DataFrame(data, index=idx)


@pytest.fixture
def config():
    return {
        "ml": {
            "feat_period": 5,
            "lags": [1, 2],
            "rolling_window": 3,
            "horizon": 2,
            "threshold": 0.0,
        }
    }


def test_feature_engineer_basics(ohlcv_df, config):
    fe = FeatureEngineer(config)
    df_feat = fe.transform(ohlcv_df)

    # 先頭 drop_n 行が落ちているか
    expected = len(ohlcv_df) - (
        config["ml"]["rolling_window"] + max(config["ml"]["lags"])
    )
    assert df_feat.shape[0] == expected

    # ATR_<period> が含まれている
    assert f"ATR_{config['ml']['feat_period']}" in df_feat.columns


def test_pipeline_scaling(ohlcv_df, config):
    pl = build_ml_pipeline(config)
    X = pl.fit_transform(ohlcv_df)

    # numpy array らしいプロパティがあること
    assert hasattr(X, "shape")
    assert X.shape[0] > 0
