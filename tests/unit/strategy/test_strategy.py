from types import SimpleNamespace

import pandas as pd
import pytest

from crypto_bot.strategy.bollinger import BollingerStrategy


@pytest.fixture(autouse=True)
def dummy_bbands(monkeypatch):
    """
    talib.BBANDS をモンキーパッチし、
    upper = close + 1, middle = close, lower = close - 1 の配列を返す。
    """
    import numpy as np

    def bbands(close, timeperiod, nbdevup, nbdevdn, matype):
        arr = np.array(close, dtype=float)
        upper = arr + 1.0
        middle = arr
        lower = arr - 1.0
        return upper, middle, lower

    monkeypatch.setattr("crypto_bot.strategy.bollinger.talib.BBANDS", bbands)


def test_no_signal_when_insufficient_data():
    strat = BollingerStrategy(period=5, nbdevup=2.0, nbdevdn=2.0)
    # データ数 < period + 1 → 常に no signal
    df = pd.DataFrame(
        {
            "close": [1, 2, 3, 4],
            "high": [2, 3, 4, 5],
            "low": [0, 1, 2, 3],
        },
        index=pd.date_range("2021-01-01", periods=4),
    )
    pos = SimpleNamespace(exist=False)
    sig = strat.logic_signal(df, pos)
    assert sig.side is None
    assert sig.price is None


def test_buy_signal_generated():
    strat = BollingerStrategy(period=3, nbdevup=2.0, nbdevdn=2.0)
    # データ数 = period + 1 → BBANDS 上辺を超えた high を生成
    idx = pd.date_range("2021-01-01", periods=4)
    df = pd.DataFrame(
        {
            "close": [10, 11, 12, 13],
            "high": [11, 12, 13, 15],  # 最終 high=15 > upper(prev)=12+1=13
            "low": [9, 10, 11, 12],
        },
        index=idx,
    )
    pos = SimpleNamespace(exist=False)
    sig = strat.logic_signal(df, pos)
    assert sig.side == "BUY"
    assert sig.price == pytest.approx(13.0)


def test_sell_signal_generated():
    strat = BollingerStrategy(period=3, nbdevup=2.0, nbdevdn=2.0)
    # データ数 = period + 1 → BBANDS middle(prev)=12
    idx = pd.date_range("2021-01-01", periods=4)
    df = pd.DataFrame(
        {
            "close": [10, 12, 14, 15],
            "high": [11, 13, 15, 15],
            "low": [9, 11, 13, 11],  # 最終 low=11 < middle(prev)=14
        },
        index=idx,
    )
    pos = SimpleNamespace(exist=True)
    sig = strat.logic_signal(df, pos)
    assert sig.side == "SELL"
    assert sig.price == pytest.approx(15.0)
