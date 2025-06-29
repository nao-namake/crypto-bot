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

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pandas.tseries.frequencies import to_offset

from crypto_bot.execution.factory import create_exchange_client

load_dotenv()


class MarketDataFetcher:
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
        if exchange_id == "bybit" and not api_key:
            self.client.has["fetchCurrencies"] = False
        self.exchange = getattr(self.client, "_exchange", self.client)

    def get_price_df(
        self,
        timeframe: str = "1m",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        paginate: bool = False,
        sleep: bool = True,
        per_page: int = 500,
    ) -> pd.DataFrame:
        import time

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
                if (
                    sleep
                    and hasattr(self.exchange, "rateLimit")
                    and self.exchange.rateLimit
                ):
                    time.sleep(self.exchange.rateLimit / 1000.0)
            data = records if limit is None else records[:limit]

        else:
            raw = self.client.fetch_ohlcv(self.symbol, timeframe, since_ms, limit)
            if (
                sleep
                and hasattr(self.exchange, "rateLimit")
                and self.exchange.rateLimit
            ):
                time.sleep(self.exchange.rateLimit / 1000.0)
            if isinstance(raw, pd.DataFrame):
                return raw
            data = raw or []

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

        if isinstance(since, datetime) or (isinstance(since, str) and since):
            df = df.iloc[1:]

        if limit is not None:
            df = df.head(limit)

        return df[["open", "high", "low", "close", "volume"]]


class DataPreprocessor:
    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        return df[~df.index.duplicated(keep="first")]

    @staticmethod
    def fill_missing_bars(df: pd.DataFrame, timeframe: str = "1h") -> pd.DataFrame:
        freq_offset = to_offset(timeframe)
        idx = pd.date_range(
            start=df.index[0],
            end=df.index[-1],
            freq=freq_offset,
            tz=df.index.tz,
        )
        df2 = df.reindex(idx)
        for col in ["open", "high", "low", "close", "volume"]:
            df2[col] = df2[col].ffill()
        return df2

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame, thresh: float = 3.5, window: int = 20
    ) -> pd.DataFrame:
        df = df.copy()
        price_cols = ["open", "high", "low", "close"]
        for col in [c for c in price_cols if c in df.columns]:
            median = (
                df[col]
                .rolling(
                    window=window,
                    center=True,
                    min_periods=1,
                )
                .median()
            )
            deviation = (df[col] - median).abs()
            mad = deviation.rolling(
                window=window,
                center=True,
                min_periods=1,
            ).median()
            mad = mad + 1e-8
            modified_zscore = 0.6745 * deviation / mad
            is_outlier = modified_zscore > thresh
            temp = df[col].copy()
            temp[is_outlier] = np.nan
            filled = temp.rolling(
                window=window,
                center=True,
                min_periods=1,
            ).mean()
            filled = filled.fillna(method="ffill").fillna(method="bfill")
            df[col] = np.where(is_outlier, filled, df[col])
        return df

    @staticmethod
    def clean(
        df: pd.DataFrame,
        timeframe: str = "1h",
        thresh: float = 3.5,
        window: int = 20,
    ) -> pd.DataFrame:
        df = DataPreprocessor.remove_duplicates(df)
        df = DataPreprocessor.fill_missing_bars(df, timeframe)
        df = DataPreprocessor.remove_outliers(df, thresh, window)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].ffill().bfill()
        return df


class OIDataFetcher:
    """OI（未決済建玉）データ取得クラス"""

    def __init__(self, market_fetcher: MarketDataFetcher):
        self.market_fetcher = market_fetcher
        self.exchange = market_fetcher.exchange
        self.symbol = market_fetcher.symbol

    def get_oi_data(
        self,
        timeframe: str = "1h",
        since: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        OI（未決済建玉）データを取得

        Returns
        -------
        pd.DataFrame
            OIデータ（index: datetime, columns: oi_amount, oi_value）
        """
        try:
            # Bybitの場合のOI取得
            if self.market_fetcher.exchange_id == "bybit":
                # 現在のOI取得を試行
                if hasattr(self.exchange, "fetch_open_interest"):
                    oi_current = self.exchange.fetch_open_interest(self.symbol)
                    if oi_current:
                        # 単一のOIデータポイントを作成
                        return pd.DataFrame(
                            [
                                {
                                    "oi_amount": oi_current.get(
                                        "openInterestAmount", 0
                                    ),
                                    "oi_value": oi_current.get("openInterestValue", 0),
                                    "timestamp": oi_current.get(
                                        "timestamp", datetime.now().timestamp() * 1000
                                    ),
                                }
                            ],
                            index=pd.to_datetime(
                                [
                                    oi_current.get(
                                        "timestamp", datetime.now().timestamp() * 1000
                                    )
                                ],
                                unit="ms",
                            ),
                        )

                # フォールバック: 空のデータフレーム
                return pd.DataFrame(columns=["oi_amount", "oi_value"])

        except Exception as e:
            print(f"Warning: Could not fetch OI data: {e}")

        # デフォルト: 空のDataFrameを返す
        return pd.DataFrame(columns=["oi_amount", "oi_value"])

    def calculate_oi_features(self, df: pd.DataFrame, window: int = 24) -> pd.DataFrame:
        """
        OI関連の特徴量を計算

        Parameters
        ----------
        df : pd.DataFrame
            OIデータ
        window : int
            移動平均の期間

        Returns
        -------
        pd.DataFrame
            OI特徴量付きDataFrame
        """
        if df.empty or "oi_amount" not in df.columns:
            return df

        # OI変化率
        df["oi_pct_change"] = df["oi_amount"].pct_change()

        # OI移動平均
        df[f"oi_ma_{window}"] = df["oi_amount"].rolling(window=window).mean()

        # OI標準化（Z-score）
        df["oi_zscore"] = (
            df["oi_amount"] - df["oi_amount"].rolling(window=window).mean()
        ) / df["oi_amount"].rolling(window=window).std()

        # OI勢い（momentum）
        df["oi_momentum"] = df["oi_amount"] / df["oi_amount"].shift(window) - 1

        # OI急激な変化検知
        df["oi_spike"] = (
            df["oi_pct_change"].abs()
            > df["oi_pct_change"].rolling(window=window).std() * 2
        ).astype(int)

        return df
