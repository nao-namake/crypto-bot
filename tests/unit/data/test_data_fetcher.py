import pandas as pd
import pytest

from crypto_bot.data.fetcher import MarketDataFetcher


class DummyRawClient:
    """
    MarketDataFetcher._create_raw_client から返されるクライアントをモックするための
    ダミークラス。fetch_ohlcv を持ち、リスト形式のデータを返す。
    """

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since=None,
        limit: int = 1,
    ):
        # timestamp と price のみを含むシンプルなデータを返す
        return [[1234567890, 50000.0, 50100.0, 49900.0, 50000.0, 10.0]]


@pytest.fixture(autouse=True)
def patch_raw_client(monkeypatch):
    """
    全テストで MarketDataFetcher._create_raw_client を DummyRawClient に差し替える。
    """
    import crypto_bot.data.fetcher as fetcher_module

    def dummy_create_exchange_client(
        exchange_id,
        api_key=None,
        api_secret=None,
        testnet=None,
    ):
        return DummyRawClient()

    monkeypatch.setattr(
        fetcher_module,
        "create_exchange_client",
        dummy_create_exchange_client,
    )


def test_get_price_df_returns_dataframe():
    """
    get_price_df が pandas.DataFrame を返し、カラム名と値が正しいことを確認する。
    """
    fetcher = MarketDataFetcher("bybit")
    df = fetcher.get_price_df(timeframe="1m", limit=1)

    # DataFrame であること
    assert isinstance(df, pd.DataFrame)

    # カラムが正しい順序で存在すること
    expected_columns = ["open", "high", "low", "close", "volume"]
    assert list(df.columns) == expected_columns, (
        f"Expected columns {expected_columns}, " f"got {list(df.columns)}"
    )

    # 中身の値がモックと一致すること
    row = df.iloc[0]
    assert row["close"] == 50000.0
    assert row["volume"] == 10.0


def test_get_price_df_limit_zero_returns_empty():
    """
    limit=0 を指定した場合、空の DataFrame を返すことを確認する。
    """
    fetcher = MarketDataFetcher("bitbank")
    df = fetcher.get_price_df(timeframe="1m", limit=0)
    assert isinstance(df, pd.DataFrame)
    assert df.empty
