# tests/unit/data/test_fetcher.py
# テスト対象: crypto_bot/data/fetcher.py
# 説明:
#   - HistoricalFetcher: 過去データ取得
#   - OHLCVデータの取得・整形
#   - MarketDataFetcher: OHLCVデータ取得ラッパーの正常・異常パターン
#   - DataPreprocessor: 前処理ユーティリティ（重複除去・穴埋め・外れ値除去等）

import numpy as np
import pandas as pd

from crypto_bot.data.fetcher import (
    DataPreprocessor,
    MarketDataFetcher,
)


class DummyClient:
    """fetch_ohlcv等を模倣するダミー"""

    def __init__(self):
        self.has = {}
        self._exchange = self
        self.rateLimit = 0

    def fetch_ohlcv(self, symbol, timeframe, since, limit):
        base = 1700000000000  # epoch ms
        n = limit or 5
        # OHLCV: [ts, o, h, l, c, v]
        arr = [
            [base + i * 60000, 100 + i, 101 + i, 99 + i, 100 + i, 1 + i]
            for i in range(n)
        ]
        return arr


def test_marketdatafetcher_get_price_df(monkeypatch):
    # create_exchange_clientをダミー化
    monkeypatch.setattr(
        "crypto_bot.data.fetcher.create_exchange_client", lambda **kwargs: DummyClient()
    )
    fetcher = MarketDataFetcher(exchange_id="bybit", symbol="BTC/USDT")
    df = fetcher.get_price_df(limit=3)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert len(df) == 3
    assert np.all(df["open"] == [100, 101, 102])
    # インデックスがdatetime
    assert isinstance(df.index[0], pd.Timestamp)


def test_marketdatafetcher_get_price_df_empty(monkeypatch):
    # 空リストを返すダミー
    class EmptyClient(DummyClient):
        def fetch_ohlcv(self, *a, **k):
            return []

    monkeypatch.setattr(
        "crypto_bot.data.fetcher.create_exchange_client", lambda **kwargs: EmptyClient()
    )
    fetcher = MarketDataFetcher(exchange_id="dummy", symbol="XXX/YYY")
    df = fetcher.get_price_df(limit=2)
    assert df.empty


def test_datapreprocessor_remove_duplicates():
    idx = pd.date_range("2023-01-01", periods=3, freq="h").tolist() + [
        pd.Timestamp("2023-01-01 02:00")
    ]
    df = pd.DataFrame({"close": [1, 2, 3, 3]}, index=idx)
    result = DataPreprocessor.remove_duplicates(df)
    assert len(result) == 3


def test_datapreprocessor_fill_missing_bars():
    idx = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 03:00"])
    df = pd.DataFrame(
        {
            "open": [1, 2, 4],
            "high": [2, 3, 5],
            "low": [0, 1, 3],
            "close": [1.5, 2.5, 4.5],
            "volume": [10, 12, 14],
        },
        index=idx,
    )
    filled = DataPreprocessor.fill_missing_bars(df, "1h")
    assert "2024-01-01 02:00:00" in filled.index.strftime("%Y-%m-%d %H:%M:%S")
    # 値は前値で埋まる
    assert filled.loc["2024-01-01 02:00:00"]["close"] == 2.5


def test_datapreprocessor_remove_outliers():
    idx = pd.date_range("2024-01-01", periods=20, freq="h")
    close = np.ones(20) * 100
    close[10] = 1000  # 異常値
    df = pd.DataFrame({"close": close}, index=idx)
    result = DataPreprocessor.remove_outliers(df, thresh=3, window=5)
    # 異常値が置換されていればOK
    assert result.iloc[10]["close"] != 1000
    assert abs(result.iloc[10]["close"] - 100) < 10


def test_datapreprocessor_clean_all():
    idx = pd.date_range("2024-01-01", periods=5, freq="h")
    close = [100, 101, 102, np.nan, 105]
    df = pd.DataFrame(
        {
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": [1, 2, 3, 4, 5],
        },
        index=idx,
    )
    df.iloc[2, 0] = np.nan  # openに欠損
    cleaned = DataPreprocessor.clean(df, timeframe="1h", thresh=3, window=2)
    assert not cleaned.isnull().any().any()
    assert len(cleaned) == 5
