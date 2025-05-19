from unittest.mock import MagicMock

import ccxt
import pandas as pd
import pytest

from crypto_bot.data.fetcher import MarketDataFetcher


@pytest.fixture(autouse=True)
def mock_ccxt(monkeypatch):
    # 3 本だけ返すモック
    fake = MagicMock()
    fake.fetch_ohlcv.return_value = [
        [1000, 1, 2, 3, 4, 5],
        [2000, 2, 3, 4, 5, 6],
        [3000, 3, 4, 5, 6, 7],
    ]
    # ccxt.bybit(*args, **kwargs) → fake を返すように修正
    monkeypatch.setattr(ccxt, "bybit", lambda *args, **kwargs: fake)
    return fake


def test_get_price_df_iso(mock_ccxt):
    f = MarketDataFetcher(exchange_id="bybit", symbol="BTC/USDT")
    df = f.get_price_df(timeframe="1h", since="2023-01-01T00:00:00Z", limit=3)
    # モックの 3 件が返る
    assert len(df) == 3
    # インデックスは pandas.Timestamp
    assert isinstance(df.index[0], pd.Timestamp)
    # カラムは最低限揃っている
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    # fetch_ohlcv が呼ばれている
    mock_ccxt.fetch_ohlcv.assert_called()


def test_paginate(mock_ccxt):
    f = MarketDataFetcher(exchange_id="bybit", symbol="BTC/USDT")
    df = f.get_price_df(timeframe="1h", limit=5, paginate=True, per_page=3)
    # リクエストは 5 件取得を試みるが、モックは 3 件しか返さない
    assert len(df) == 3
