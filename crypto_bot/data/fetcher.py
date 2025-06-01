# =============================================================================
# ファイル名: crypto_bot/data/fetcher.py
# 説明:
# ・MarketDataFetcher：取引所（Bybit等）からOHLCVデータをDataFrame形式で取得するユーティリティ
# ・DataPreprocessor：取得した価格データ（OHLCV）の重複除去、欠損補完、外れ値除去などの前処理を一括で行う
# ・.envファイルやAPIキー自動読込、Bybit専用の細かい工夫もあり
# ・バックテストや学習データ用のデータ取得・整形の中心的な役割
# =============================================================================

import numbers
import os
from datetime import datetime
from typing import List, Optional, Union

import pandas as pd
from dotenv import load_dotenv
from pandas.tseries.frequencies import to_offset

from crypto_bot.execution.factory import create_exchange_client

# .env から自動読み込み（APIキーなど）
load_dotenv()


class MarketDataFetcher:
    """
    ExchangeClient を使って OHLCV を取得し、pandas.DataFrame にして返す。

    引数:
        - exchange_id: 取引所名（例: "bybit"）
        - api_key, api_secret: 各種APIキー（.envがあれば省略可）
        - symbol: 取引ペア
        - testnet: テストネット利用可否
        - ccxt_options: CCXT拡張オプション（APIエンドポイント指定など）

    主要メソッド:
        - get_price_df(): OHLCVをDataFrameで返す（自動ページング等あり）
    """

    def __init__(
        self,
        exchange_id: str = "bybit",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        symbol: str = "BTC/USDT",
        testnet: bool = True,
        ccxt_options: Optional[dict] = None,
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
            ccxt_options=ccxt_options or {},
        )
        # Bybitの場合、APIキー未設定だとfetchCurrenciesエラーを避ける
        if exchange_id == "bybit" and not api_key:
            self.client.has["fetchCurrencies"] = False
        self.exchange = getattr(self.client, "_exchange", self.client)

    # --------------------------------------------------------------------- #
    # データ取得
    # --------------------------------------------------------------------- #
    def get_price_df(
        self,
        timeframe: str = "1m",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        paginate: bool = False,
        sleep: bool = True,
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
        import time
        # since をミリ秒に変換
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

        max_records = limit if limit is not None else float("inf")

        if paginate and limit:
            # ------------------- ページング取得 ------------------------- #
            records: List = []
            seen_ts = set()
            last_since = since_ms
            retries = 0
            MAX_RETRIES = 5
            while len(records) < max_records and retries < MAX_RETRIES:
                batch = self.client.fetch_ohlcv(
                    self.symbol, timeframe, last_since, per_page
                )
                if isinstance(batch, pd.DataFrame):
                    return batch
                if not batch:
                    break

                added = False
                for row in batch:
                    ts = row[0]
                    if ts not in seen_ts:
                        seen_ts.add(ts)
                        records.append(row)
                        last_since = ts + 1
                        added = True
                if not added:
                    retries += 1
                if sleep and hasattr(self.exchange, "rateLimit") and self.exchange.rateLimit:
                    time.sleep(self.exchange.rateLimit / 1000.0)
            data = records if limit is None else records[:limit]

        else:
            # ------------------- 単発取得 ------------------------------- #
            raw = self.client.fetch_ohlcv(self.symbol, timeframe, since_ms, limit)
            if sleep and hasattr(self.exchange, "rateLimit") and self.exchange.rateLimit:
                time.sleep(self.exchange.rateLimit / 1000.0)
            if isinstance(raw, pd.DataFrame):
                return raw
            data = raw or []

            # Bybit linear契約で":USDT" サフィックスが必要な場合の自動リトライ
            if (
                not data
                and self.exchange_id == "bybit"
                and "/USDT" in self.symbol
                and ":USDT" not in self.symbol
            ):
                retry_symbol = f"{self.symbol}:USDT"
                try:
                    raw = self.client.fetch_ohlcv(
                        retry_symbol, timeframe, since_ms, limit
                    )
                    if raw:
                        self.symbol = retry_symbol
                        data = raw
                except Exception:
                    pass

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(
            data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("datetime")

        # sinceがdatetime/ISOなら先頭行を除外（重複分）
        if isinstance(since, datetime) or (isinstance(since, str) and since):
            df = df.iloc[1:]

        if limit is not None:
            df = df.head(limit)

        return df[["open", "high", "low", "close", "volume"]]


# ===================================================================== #
# 前処理ユーティリティ
# ===================================================================== #
class DataPreprocessor:
    """OHLCV DataFrame の前処理ユーティリティ

    1. 重複除去
    2. 欠損バー補完（全期間を生成）
    3. 外れ値（z-score）除去
    4. 欠損のffill/bfill
    """

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        return df[~df.index.duplicated(keep="first")]

    @staticmethod
    def fill_missing_bars(df: pd.DataFrame, timeframe: str = "1h") -> pd.DataFrame:
        freq_offset = to_offset(timeframe)
        idx = pd.date_range(start=df.index[0], end=df.index[-1], freq=freq_offset, tz=df.index.tz)
        df2 = df.reindex(idx)
        for col in ["open", "high", "low", "close", "volume"]:
            df2[col] = df2[col].ffill()
        return df2

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame, z_thresh: float = 5.0, window: int = 20
    ) -> pd.DataFrame:
        ma = df["close"].rolling(window).mean()
        sd = df["close"].rolling(window).std()
        z = (df["close"] - ma) / sd
        mask = z.abs() < z_thresh
        df = df.copy()
        df.loc[~mask, "close"] = ma[~mask]
        return df

    @staticmethod
    def clean(
        df: pd.DataFrame, timeframe: str = "1h", z_thresh: float = 5.0, window: int = 20
    ) -> pd.DataFrame:
        df = DataPreprocessor.remove_duplicates(df)
        df = DataPreprocessor.fill_missing_bars(df, timeframe)
        df = DataPreprocessor.remove_outliers(df, z_thresh, window)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].ffill().bfill()
        return df
