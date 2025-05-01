# tool.py

import ccxt
import pandas as pd
import numpy as np
import talib
from typing import Optional

class MarketDataFetcher:
    """
    Bybit などの取引所から OHLCV を取得して DataFrame 化する。
    """
    def __init__(self, symbol: str = "BTC/USDT", enable_rate_limit: bool = True):
        self.symbol = symbol
        self.exchange = ccxt.bybit({"enableRateLimit": enable_rate_limit})

    def get_price_df(
        self,
        timeframe: str = "1m",
        after: Optional[int] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        after : Unix秒 or ミリ秒。戻り値は datetime を index に持つ OHLCV DataFrame。
        """
        since_ms = None
        if isinstance(after, int):
            since_ms = after * 1000 if after < 1e12 else after

        ohlcv = self.exchange.fetch_ohlcv(
            self.symbol,
            timeframe=timeframe,
            since=since_ms,
            limit=limit
        )
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("datetime", inplace=True)
        return df[["open", "high", "low", "close", "volume"]]


class IndicatorCalculator:
    """
    talib をラップして指標を計算し、Series/DataFrame を返す。
    """
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        arr = talib.ATR(
            df["high"].values,
            df["low"].values,
            df["close"].values,
            timeperiod=period
        )
        return pd.Series(arr, index=df.index, name=f"ATR_{period}")

    @staticmethod
    def calculate_bbands(
        df: pd.DataFrame,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0
    ) -> pd.DataFrame:
        upper, middle, lower = talib.BBANDS(
            df["close"].values,
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=0
        )
        return pd.DataFrame(
            {"BB_upper": upper, "BB_middle": middle, "BB_lower": lower},
            index=df.index
        )


class DataPreprocessor:
    """
    OHLCV DataFrame の前処理ユーティリティ
    - 重複行の除去
    - 欠損バーの検出＆補完
    - 異常値（飛び値）の除去
    - 欠損値の補完
    """

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        # 同一 timestamp の重複を除去（最初の行を残す）
        return df[~df.index.duplicated(keep="first")]

    @staticmethod
    def fill_missing_bars(
        df: pd.DataFrame,
        timeframe: str = "1h"
    ) -> pd.DataFrame:
        # インデックスを指定の時間間隔で再構築し、欠損バーを補完
        idx = pd.date_range(
            start=df.index[0],
            end=df.index[-1],
            freq=timeframe,
            tz=df.index.tz
        )
        df2 = df.reindex(idx)
        # OHLCV は前の値で埋める
        df2[["open", "high", "low", "close", "volume"]] = (
            df2[["open", "high", "low", "close", "volume"]].ffill()
        )
        return df2

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame,
        z_thresh: float = 5.0,
        window: int = 20
    ) -> pd.DataFrame:
        # close の移動平均・標準偏差を計算し、Zスコアで閾値を超える飛び値を除外
        ma = df["close"].rolling(window).mean()
        sd = df["close"].rolling(window).std()
        z = (df["close"] - ma) / sd
        return df[z.abs() < z_thresh]

    @staticmethod
    def clean(
        df: pd.DataFrame,
        timeframe: str = "1h",
        z_thresh: float = 5.0,
        window: int = 20
    ) -> pd.DataFrame:
        # 1) 重複除去
        df = DataPreprocessor.remove_duplicates(df)
        # 2) 欠損バー補完
        df = DataPreprocessor.fill_missing_bars(df, timeframe)
        # 3) 飛び値除去
        df = DataPreprocessor.remove_outliers(df, z_thresh, window)
        # 4) 残った欠損値を前後で埋める
        df = df.fillna(method="ffill").fillna(method="bfill")
        return df