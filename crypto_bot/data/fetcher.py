# tool.py

import ccxt
import pandas as pd
import numpy as np
import talib
from typing import Optional

class MarketDataFetcher:
    def __init__(self, symbol: str = "BTC/USDT", enable_rate_limit: bool = True):
        self.symbol   = symbol
        self.exchange = ccxt.bybit({"enableRateLimit": enable_rate_limit})

    def _fetch_ohlcv_paginated(
        self,
        timeframe: str,
        since_ms: int,
        limit_per_call: int,
        max_records: int
    ) -> list:
        """
        ページングして OHLCV を集める内部メソッド。
        - since_ms        : 開始時刻（ミリ秒）
        - limit_per_call  : 1 回の fetch_ohlcv で取得するバー数
        - max_records     : 合計で欲しいバー数
        """
        all_ohlcv = []
        next_since = since_ms
        fetched = 0

        while True:
            # 1) 今回取得すべき件数
            to_fetch = min(limit_per_call, max_records - fetched)
            batch = self.exchange.fetch_ohlcv(
                self.symbol,
                timeframe=timeframe,
                since=next_since,
                limit=to_fetch
            )
            if not batch:
                break
            all_ohlcv.extend(batch)
            fetched += len(batch)
            # 次の since は、最後のタイムスタンプ ＋ 1 ミリ秒
            next_since = batch[-1][0] + 1

            # 取得完了 or API が返す件数が少ないときは終了
            if fetched >= max_records or len(batch) < to_fetch:
                break

        return all_ohlcv

    def get_price_df(
        self,
        timeframe: str = "1m",
        after: Optional[int] = None,
        limit: Optional[int] = None,
        paginate: bool = False,
        per_page: int = 500
    ) -> pd.DataFrame:
        """
        OHLCV を取得して DataFrame 化する。
        - paginate=True のとき、limit 件までページング取得。
        - per_page    : 1 回の fetch_ohlcv で読み込むバー数（Bybit は最大 500）
        """
        since_ms = None
        if isinstance(after, int):
            since_ms = after * 1000 if after < 1e12 else after

        # ページングするなら
        if paginate and limit:
            ohlcv = self._fetch_ohlcv_paginated(
                timeframe=timeframe,
                since_ms=since_ms,
                limit_per_call=per_page,
                max_records=limit
            )
        else:
            # 通常の1回取得
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