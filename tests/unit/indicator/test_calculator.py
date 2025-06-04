# tests/unit/indicator/test_calculator.py
# テスト対象: crypto_bot/indicator/calculator.py
# 説明:
#   - IndicatorCalculator クラスの各種テクニカル指標計算メソッドの動作確認

import numpy as np
import pandas as pd
import pytest

from crypto_bot.indicator.calculator import IndicatorCalculator


@pytest.fixture
def dummy_ohlcv():
    # シンプルなダミーOHLCV DataFrameを作成
    idx = pd.date_range("2024-01-01", periods=30, freq="1D")
    data = {
        "open": np.linspace(100, 130, 30),
        "high": np.linspace(101, 131, 30),
        "low": np.linspace(99, 129, 30),
        "close": np.linspace(100, 130, 30),
        "volume": np.random.rand(30) * 100,
    }
    return pd.DataFrame(data, index=idx)


def test_calculate_atr(dummy_ohlcv):
    result = IndicatorCalculator.calculate_atr(dummy_ohlcv, period=14)
    assert isinstance(result, pd.Series)
    assert len(result) == 30


def test_sma(dummy_ohlcv):
    calc = IndicatorCalculator()
    sma = calc.sma(dummy_ohlcv["close"], window=5)
    assert isinstance(sma, pd.Series)
    assert sma.isnull().sum() > 0  # 最初はNaN


def test_ema(dummy_ohlcv):
    calc = IndicatorCalculator()
    ema = calc.ema(dummy_ohlcv["close"], window=5)
    assert isinstance(ema, pd.Series)
    assert ema.isnull().sum() > 0  # 最初はNaN


def test_rsi(dummy_ohlcv):
    calc = IndicatorCalculator()
    rsi = calc.rsi(dummy_ohlcv["close"], window=14)
    assert isinstance(rsi, pd.Series)
    assert len(rsi) == len(dummy_ohlcv)


def test_macd(dummy_ohlcv):
    calc = IndicatorCalculator()
    macd = calc.macd(dummy_ohlcv["close"], fast=12, slow=26, signal=9)
    assert isinstance(macd, pd.DataFrame)
    assert macd.shape[1] == 3


def test_rci(dummy_ohlcv):
    calc = IndicatorCalculator()
    rci = calc.rci(dummy_ohlcv["close"], window=9)
    assert isinstance(rci, pd.Series)
    assert len(rci) == len(dummy_ohlcv)


def test_atr_wrapper(dummy_ohlcv):
    calc = IndicatorCalculator()
    atr = calc.atr(dummy_ohlcv, window=14)
    assert isinstance(atr, pd.Series)
    assert len(atr) == len(dummy_ohlcv)


def test_mochipoyo_signals(dummy_ohlcv):
    calc = IndicatorCalculator()
    sig = calc.mochipoyo_signals(
        dummy_ohlcv, rci_window=9, macd_fast=12, macd_slow=26, macd_signal=9
    )
    assert isinstance(sig, pd.DataFrame)
    assert set(sig.columns) == {"mochipoyo_long_signal", "mochipoyo_short_signal"}
