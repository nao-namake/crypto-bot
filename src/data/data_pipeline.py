"""
データ取得パイプライン - マルチタイムフレーム対応

1時間足、15分足、4時間足のデータを効率的に取得・管理する
シンプルで高速なデータパイプライン実装。

主な特徴:
- マルチタイムフレーム対応（15m, 1h, 4h）
- 効率的なデータキャッシング
- エラーハンドリングと自動リトライ
- データ品質チェック機能.
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd

from ..core.exceptions import DataFetchError
from ..core.logger import get_logger
from .bitbank_client import BitbankClient, get_bitbank_client


class TimeFrame(Enum):
    """サポートするタイムフレーム."""

    M15 = "15m"  # 15分足
    H1 = "1h"  # 1時間足
    H4 = "4h"  # 4時間足


@dataclass
class DataRequest:
    """データ取得リクエスト."""

    symbol: str = "BTC/JPY"
    timeframe: TimeFrame = TimeFrame.H1
    limit: int = 1000
    since: Optional[int] = None


class DataPipeline:
    """
    マルチタイムフレーム データ取得パイプライン

    効率的なデータ取得・キャッシング・品質管理を提供.
    """

    def __init__(self, client: Optional[BitbankClient] = None):
        """
        データパイプライン初期化

        Args:
            client: Bitbankクライアント（Noneの場合はグローバルクライアント使用）.
        """
        self.logger = get_logger()
        self.client = client or get_bitbank_client()

        # データキャッシュ（メモリ）
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

        # 設定
        self.cache_duration_minutes = 5  # キャッシュ有効期間
        self.max_retries = 3  # 最大リトライ回数
        self.retry_delay = 1.0  # リトライ間隔（秒）

        self.logger.info("データパイプライン初期化完了")

    def _generate_cache_key(self, request: DataRequest) -> str:
        """キャッシュキー生成."""
        return f"{request.symbol}_{request.timeframe.value}_{request.limit}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """キャッシュの有効性チェック."""
        if cache_key not in self._cache_timestamps:
            return False

        cache_time = self._cache_timestamps[cache_key]
        now = datetime.now()

        return (now - cache_time).total_seconds() < (self.cache_duration_minutes * 60)

    def _validate_ohlcv_data(self, data: List[List[Union[int, float]]]) -> bool:
        """OHLCV データの品質チェック."""
        if not data:
            return False

        for row in data:
            if len(row) != 6:  # [timestamp, open, high, low, close, volume]
                return False

            timestamp, open_price, high, low, close, volume = row

            # 基本的な価格検証
            if not all(isinstance(x, (int, float)) for x in row):
                return False

            if high < low or high < open_price or high < close:
                return False

            if low > open_price or low > close:
                return False

            if volume < 0:
                return False

        return True

    def _convert_to_dataframe(self, ohlcv_data: List[List[Union[int, float]]]) -> pd.DataFrame:
        """OHLCV データをDataFrameに変換."""
        columns = ["timestamp", "open", "high", "low", "close", "volume"]

        df = pd.DataFrame(ohlcv_data, columns=columns)

        # タイムスタンプを日時に変換
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        # 数値型に変換
        numeric_columns = ["open", "high", "low", "close", "volume"]
        df[numeric_columns] = df[numeric_columns].astype(float)

        # ソート
        df.sort_index(inplace=True)

        return df

    async def fetch_ohlcv(self, request: DataRequest, use_cache: bool = True) -> pd.DataFrame:
        """
        OHLCV データを取得

        Args:
            request: データ取得リクエスト
            use_cache: キャッシュ使用フラグ

        Returns:
            OHLCV DataFrameOHLCV データ（pandas DataFrame）.
        """
        cache_key = self._generate_cache_key(request)

        # キャッシュチェック
        if use_cache and self._is_cache_valid(cache_key):
            self.logger.debug(f"キャッシュからデータ取得: {cache_key}")
            return self._cache[cache_key].copy()

        # データ取得（リトライ機能付き）
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(
                    f"データ取得開始: {request.symbol} {request.timeframe.value} "
                    f"(試行: {attempt + 1}/{self.max_retries})"
                )

                # APIからデータ取得
                ohlcv_data = await self.client.fetch_ohlcv(
                    symbol=request.symbol,
                    timeframe=request.timeframe.value,
                    since=request.since,
                    limit=request.limit,
                )

                # データ品質チェック
                if not self._validate_ohlcv_data(ohlcv_data):
                    raise DataFetchError(
                        f"データ品質チェック失敗: {request.symbol} {request.timeframe.value}",
                        context={"attempt": attempt + 1},
                    )

                # DataFrameに変換
                df = self._convert_to_dataframe(ohlcv_data)

                # 型安全性チェック - DataFrameの保証
                if not isinstance(df, pd.DataFrame):
                    self.logger.error(f"データ変換エラー: 期待された型はDataFrame、実際の型は{type(df)}")
                    return pd.DataFrame()  # 空のDataFrameを返して型安全性を保証

                # キャッシュに保存
                self._cache[cache_key] = df.copy()
                self._cache_timestamps[cache_key] = datetime.now()

                self.logger.info(
                    f"データ取得成功: {request.symbol} {request.timeframe.value}",
                    extra_data={
                        "rows": len(df),
                        "latest_timestamp": (df.index[-1].isoformat() if len(df) > 0 else None),
                        "attempt": attempt + 1,
                        "type_safe": isinstance(df, pd.DataFrame),
                    },
                )

                return df

            except Exception as e:
                self.logger.warning(f"データ取得失敗 (試行 {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise DataFetchError(
                        f"データ取得に失敗しました: {request.symbol} {request.timeframe.value}",
                        context={"max_retries_exceeded": True},
                    )

    async def fetch_multi_timeframe(
        self, symbol: str = "BTC/JPY", limit: int = 1000
    ) -> Dict[str, pd.DataFrame]:
        """
        マルチタイムフレーム データを一括取得（型安全性強化）

        Args:
            symbol: 通貨ペア
            limit: 各タイムフレームの取得件数

        Returns:
            タイムフレーム別データ辞書（すべてDataFrame型保証）.
        """
        results = {}

        for timeframe in TimeFrame:
            request = DataRequest(symbol=symbol, timeframe=timeframe, limit=limit)

            try:
                df = await self.fetch_ohlcv(request)
                
                # 型安全性チェック - DataFrameの保証
                if isinstance(df, pd.DataFrame):
                    results[timeframe.value] = df
                else:
                    self.logger.warning(
                        f"予期しない型が返却されました: {type(df)}, DataFrameに変換します"
                    )
                    # dictやその他の型の場合は空のDataFrameに変換
                    results[timeframe.value] = pd.DataFrame()

            except Exception as e:
                self.logger.error(f"マルチタイムフレーム取得失敗: {timeframe.value}", error=e)
                # 失敗したタイムフレームは必ず空のDataFrameで代替（型保証）
                results[timeframe.value] = pd.DataFrame()

        # 最終的な型確認 - すべてがDataFrameであることを保証
        for tf, data in results.items():
            if not isinstance(data, pd.DataFrame):
                self.logger.error(f"型不整合検出: {tf} = {type(data)}, 空のDataFrameで修正")
                results[tf] = pd.DataFrame()

        self.logger.info(
            f"マルチタイムフレーム取得完了: {symbol}",
            extra_data={
                "timeframes": list(results.keys()),
                "total_rows": sum(len(df) for df in results.values()),
                "all_dataframes": all(isinstance(df, pd.DataFrame) for df in results.values()),
            },
        )

        return results

    async def get_latest_prices(self, symbol: str = "BTC/JPY") -> Dict[str, float]:
        """
        最新価格情報を全タイムフレームから取得

        Args:
            symbol: 通貨ペア

        Returns:
            タイムフレーム別最新価格.
        """
        latest_prices = {}

        for timeframe in TimeFrame:
            try:
                request = DataRequest(symbol=symbol, timeframe=timeframe, limit=1)
                df = await self.fetch_ohlcv(request)

                if len(df) > 0:
                    latest_prices[timeframe.value] = float(df["close"].iloc[-1])

            except Exception as e:
                self.logger.warning(f"最新価格取得失敗: {timeframe.value} - {e}")

        return latest_prices

    def clear_cache(self):
        """キャッシュクリア."""
        self._cache.clear()
        self._cache_timestamps.clear()
        self.logger.info("データキャッシュをクリアしました")

    def get_cache_info(self) -> Dict[str, Any]:
        """キャッシュ情報取得."""
        now = datetime.now()

        cache_info = {
            "total_cached_items": len(self._cache),
            "cache_size_mb": sum(df.memory_usage(deep=True).sum() for df in self._cache.values())
            / 1024
            / 1024,
            "items": [],
        }

        for key, timestamp in self._cache_timestamps.items():
            age_minutes = (now - timestamp).total_seconds() / 60
            is_valid = age_minutes < self.cache_duration_minutes

            cache_info["items"].append(
                {
                    "key": key,
                    "age_minutes": round(age_minutes, 2),
                    "is_valid": is_valid,
                    "rows": len(self._cache[key]),
                }
            )

        return cache_info

    async def fetch_historical_data(
        self,
        symbol: str = "BTC/JPY",
        timeframe: str = "1h",
        since: datetime = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        バックテスト用の過去データ取得（非同期版）

        Args:
            symbol: 通貨ペア
            timeframe: 時間軸
            since: 開始日時
            limit: 取得数制限

        Returns:
            pd.DataFrame: 過去データ
        """
        try:
            # timeframeをTimeFrameエナムに変換
            timeframe_map = {
                "1m": TimeFrame.M1,
                "5m": TimeFrame.M5,
                "15m": TimeFrame.M15,
                "1h": TimeFrame.H1,
                "4h": TimeFrame.H4,
                "1d": TimeFrame.D1,
            }

            tf_enum = timeframe_map.get(timeframe.lower(), TimeFrame.H1)

            # DataRequestを作成して既存のfetch_ohlcvを使用
            request = DataRequest(
                symbol=symbol,
                timeframe=tf_enum,
                limit=limit,
                since=since,
            )

            # 非同期メソッドを実行
            data = await self.fetch_ohlcv(request, use_cache=True)

            self.logger.info(f"Historical data fetched: {len(data)} rows for {symbol} {timeframe}")
            return data

        except Exception as e:
            self.logger.error(f"Historical data fetch error: {e}")
            # 空のDataFrameを返す（エラー対応）
            return pd.DataFrame()


# グローバルパイプラインインスタンス
_data_pipeline: Optional[DataPipeline] = None


def get_data_pipeline() -> DataPipeline:
    """グローバルデータパイプライン取得."""
    global _data_pipeline

    if _data_pipeline is None:
        _data_pipeline = DataPipeline()

    return _data_pipeline


def fetch_market_data(
    symbol: str = "BTC/JPY", timeframe: str = "1h", limit: int = 1000
) -> pd.DataFrame:
    """
    市場データ取得の簡易インターフェース

    Args:
        symbol: 通貨ペア
        timeframe: タイムフレーム
        limit: 取得件数

    Returns:
        OHLCV DataFrame.
    """
    pipeline = get_data_pipeline()

    # TimeFrame enumに変換
    timeframe_enum = TimeFrame(timeframe)

    request = DataRequest(symbol=symbol, timeframe=timeframe_enum, limit=limit)

    return pipeline.fetch_ohlcv(request)
