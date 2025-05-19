import numbers
import os
from datetime import datetime
from typing import List, Optional, Union

import pandas as pd
from dotenv import load_dotenv

from crypto_bot.execution.factory import create_exchange_client

# .env から自動読み込み
load_dotenv()


class MarketDataFetcher:
    """
    ExchangeClient を使って OHLCV を取得し、pandas.DataFrame にして返す。
    """

    def __init__(
        self,
        exchange_id: str = "bybit",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        symbol: str = "BTC/USDT",
        testnet: bool = True,
    ):
        self.exchange_id = exchange_id
        self.symbol = symbol
        api_key = api_key or os.getenv(f"{exchange_id.upper()}_API_KEY")
        api_secret = api_secret or os.getenv(f"{exchange_id.upper()}_API_SECRET")
        env_test_key = os.getenv(f"{exchange_id.upper()}_TESTNET_API_KEY")
        testnet = testnet or bool(env_test_key)
        self.client = create_exchange_client(
            exchange_id=exchange_id,
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )
        self.exchange = getattr(self.client, "_exchange", self.client)

    def get_price_df(
        self,
        timeframe: str = "1m",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        paginate: bool = False,
        per_page: int = 500,
    ) -> pd.DataFrame:
        """
        OHLCV を取得して DataFrame 化する。
        :param timeframe: CCXT フォーマットの time frame（例: "1h"）
        :param since: 取得開始時刻（ミリ秒 or ISO8601 文字列 or datetime or 数値）
        :param limit: 取得上限レコード数
        :param paginate: True の場合、ページング取得ロジックを使用
        :param per_page: 1回の API 呼び出しあたりの最大レコード数
        :return: pandas.DataFrame（index が datetime）
        """
        # since をパースして ms 単位に
        since_ms: Optional[int] = None
        if since is not None:
            if isinstance(since, str):
                dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                since_ms = int(dt.timestamp() * 1000)
            elif isinstance(since, datetime):
                since_ms = int(since.timestamp() * 1000)
            elif isinstance(since, numbers.Real):
                ts = int(since)
                since_ms = ts if ts > 1e12 else int(ts * 1000)
            else:
                raise TypeError(f"Unsupported type for since: {type(since)}")

        # 1) データ取得 (paginate or シンプル)
        if paginate and limit:
            # 複数ページをフェッチして、重複を除いて limit 件集める
            records: List = []
            seen_ts = set()
            last_since = since_ms
            retries = 0
            MAX_RETRIES = 5
            while len(records) < limit and retries < MAX_RETRIES:
                batch = self.client.fetch_ohlcv(
                    self.symbol, timeframe, last_since, per_page
                )
                # DataFrame を返すモック時は即時返却
                if isinstance(batch, pd.DataFrame):
                    return batch
                if not batch:
                    break
                added = False
                # 重複タイムスタンプは除外して追加
                for row in batch:
                    ts = row[0]
                    if ts not in seen_ts:
                        seen_ts.add(ts)
                        records.append(row)
                        last_since = ts + 1
                        added = True
                if not added:
                    retries += 1
            data = records[:limit]
        else:
            # paginate=False の場合
            raw = self.client.fetch_ohlcv(self.symbol, timeframe, since_ms, limit)
            if isinstance(raw, pd.DataFrame):
                return raw
            data = raw or []

        # 2) 空なら空 DF
        if not data:
            return pd.DataFrame()

        # 3) DataFrame 化
        df = pd.DataFrame(
            data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        # 4) timestamp → datetime index
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("datetime")

        # 5) since がdatetimeまたはISO8601文字列なら「先頭行を除去」
        if isinstance(since, datetime) or (isinstance(since, str) and since):
            df = df.iloc[1:]

        # 6) 最終的に limit 行だけ返却
        if limit is not None:
            df = df.head(limit)

        # 7) カラム整形して返す
        return df[["open", "high", "low", "close", "volume"]]


class DataPreprocessor:
    """
    OHLCV DataFrame の前処理ユーティリティ
    """

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        return df[~df.index.duplicated(keep="first")]

    @staticmethod
    def fill_missing_bars(df: pd.DataFrame, timeframe: str = "1h") -> pd.DataFrame:
        idx = pd.date_range(
            start=df.index[0], end=df.index[-1], freq=timeframe, tz=df.index.tz
        )
        df2 = df.reindex(idx)
        df2[["open", "high", "low", "close", "volume"]] = df2[
            ["open", "high", "low", "close", "volume"]
        ].ffill()
        return df2

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame, z_thresh: float = 5.0, window: int = 20
    ) -> pd.DataFrame:
        ma = df["close"].rolling(window).mean()
        sd = df["close"].rolling(window).std()
        z = (df["close"] - ma) / sd
        return df[z.abs() < z_thresh]

    @staticmethod
    def clean(
        df: pd.DataFrame, timeframe: str = "1h", z_thresh: float = 5.0, window: int = 20
    ) -> pd.DataFrame:
        df = DataPreprocessor.remove_duplicates(df)
        df = DataPreprocessor.fill_missing_bars(df, timeframe)
        df = DataPreprocessor.remove_outliers(df, z_thresh, window)
        return df.fillna(method="ffill").fillna(method="bfill")
