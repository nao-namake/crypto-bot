# tests/unit/ml/test_preprocessor.py
# テスト対象: crypto_bot/ml/preprocessor.py
# 説明:
#   - FeatureEngineer: 特徴量生成・補完・extra_features
#   - build_ml_pipeline: sklearn互換パイプライン生成
#   - prepare_ml_dataset: X, y_reg, y_clf の一括生成

import numpy as np
import pandas as pd
import pytest

from crypto_bot.ml.preprocessor import (
    FeatureEngineer,
    build_ml_pipeline,
    prepare_ml_dataset,
)


@pytest.fixture
def dummy_config():
    return {
        "ml": {
            "feat_period": 3,
            "lags": [1, 2],
            "rolling_window": 3,
            "extra_features": ["rsi_3", "ema_3", "day_of_week"],
            "horizon": 1,
            "threshold": 0.0,
        }
    }


@pytest.fixture
def dummy_ohlcv():
    idx = pd.date_range("2023-01-01", periods=10, freq="D", tz="UTC")
    df = pd.DataFrame(
        {
            "open": np.random.rand(10),
            "high": np.random.rand(10),
            "low": np.random.rand(10),
            "close": np.random.rand(10),
            "volume": np.random.rand(10) * 10,
        },
        index=idx,
    )
    return df


def test_feature_engineer_transform(dummy_config, dummy_ohlcv):
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    # カラムが増えていること・欠損0埋め
    assert isinstance(out, pd.DataFrame)
    # 基本OHLCV + ATR + lag + rolling + extra_features で10列以上
    assert out.shape[1] > 10
    # 欠損が0で埋まる
    assert out.isnull().sum().sum() == 0


def test_feature_engineer_transform_empty_df(dummy_config):
    fe = FeatureEngineer(dummy_config)
    empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = fe.transform(empty_df)
    assert isinstance(out, pd.DataFrame)
    assert out.empty


def test_feature_engineer_transform_missing_columns(dummy_config):
    fe = FeatureEngineer(dummy_config)
    df = pd.DataFrame({"open": [1, 2, 3]})
    with pytest.raises(KeyError):
        fe.transform(df)


def test_feature_engineer_transform_with_rsi(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["rsi_14"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "rsi_14" in out.columns
    assert not out["rsi_14"].isnull().any()


def test_feature_engineer_transform_with_ema(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["ema_20"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "ema_20" in out.columns
    assert not out["ema_20"].isnull().any()


def test_feature_engineer_transform_with_sma(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["sma_20"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "sma_20" in out.columns
    assert not out["sma_20"].isnull().any()


def test_feature_engineer_transform_with_macd(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["macd"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "macd" in out.columns
    assert "macd_signal" in out.columns
    assert "macd_hist" in out.columns
    assert not out["macd"].isnull().any()


def test_feature_engineer_transform_with_rci(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["rci_14"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "rci_14" in out.columns
    assert not out["rci_14"].isnull().any()


def test_feature_engineer_transform_with_volume_zscore(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["volume_zscore_20"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "volume_zscore_20" in out.columns
    assert not out["volume_zscore_20"].isnull().any()


def test_feature_engineer_transform_with_time_features(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["day_of_week", "hour_of_day"]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "day_of_week" in out.columns
    assert "hour_of_day" in out.columns
    assert out["day_of_week"].dtype == "int8"
    assert out["hour_of_day"].dtype == "int8"


def test_feature_engineer_transform_with_mochipoyo_signals(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = [
        "mochipoyo_long_signal",
        "mochipoyo_short_signal",
    ]
    fe = FeatureEngineer(dummy_config)
    out = fe.transform(dummy_ohlcv)
    assert "mochipoyo_long_signal" in out.columns
    assert "mochipoyo_short_signal" in out.columns
    assert not out["mochipoyo_long_signal"].isnull().any()
    assert not out["mochipoyo_short_signal"].isnull().any()


def test_build_ml_pipeline_runs(dummy_config, dummy_ohlcv):
    pipeline = build_ml_pipeline(dummy_config)
    arr = pipeline.fit_transform(dummy_ohlcv)
    # 出力はndarray
    assert isinstance(arr, np.ndarray)
    # サンプル数一致
    assert arr.shape[0] == dummy_ohlcv.shape[0]


def test_build_ml_pipeline_empty_df(dummy_config):
    pipeline = build_ml_pipeline(dummy_config)
    empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    arr = pipeline.fit_transform(empty_df)
    assert isinstance(arr, np.ndarray)
    assert arr.shape[0] == 0


def test_prepare_ml_dataset(dummy_config, dummy_ohlcv):
    # 最小限のテスト：戻り値3つ/X, y_reg, y_clf
    X, y_reg, y_clf = prepare_ml_dataset(dummy_ohlcv, dummy_config)
    # X, y_reg, y_clf の行数・index一致
    assert len(X) == len(y_reg) == len(y_clf)
    # DataFrame/Series型
    assert isinstance(X, pd.DataFrame)
    assert isinstance(y_reg, pd.Series)
    assert isinstance(y_clf, pd.Series)


def test_prepare_ml_dataset_empty_df(dummy_config):
    empty_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    X, y_reg, y_clf = prepare_ml_dataset(empty_df, dummy_config)
    assert len(X) == 0
    assert len(y_reg) == 0
    assert len(y_clf) == 0


def test_prepare_ml_dataset_single_row(dummy_config):
    df = pd.DataFrame(
        {"open": [100], "high": [101], "low": [99], "close": [100], "volume": [1000]}
    )
    X, y_reg, y_clf = prepare_ml_dataset(df, dummy_config)
    assert len(X) == 0  # ウィンドウサイズ分のデータが必要なため
    assert len(y_reg) == 0
    assert len(y_clf) == 0


def test_extra_feature_unknown_raises(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["unknown_feature_999"]
    fe = FeatureEngineer(dummy_config)
    with pytest.raises(ValueError):
        fe.transform(dummy_ohlcv)


def test_extra_feature_invalid_format_raises(dummy_config, dummy_ohlcv):
    dummy_config["ml"]["extra_features"] = ["rsi"]  # パラメータなし
    fe = FeatureEngineer(dummy_config)
    with pytest.raises(ValueError):
        fe.transform(dummy_ohlcv)
