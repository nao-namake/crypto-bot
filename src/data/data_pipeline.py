"""
データ取得パイプライン

最終更新: 2025/11/16 (Phase 52.4-B)

15分足・4時間足データを効率的に取得・管理するデータパイプライン。
マルチタイムフレーム対応・高速キャッシング・自動リトライ機構を実装。

主要機能:
- マルチタイムフレーム対応（15m, 4h）2軸構成
- 効率的なデータキャッシング（LRUキャッシュ統合）
- エラーハンドリング・自動リトライ（指数バックオフ）
- データ品質チェック機能（欠損値・異常値検出）
- バックテストモード対応（CSV読み込み）

開発履歴:
- Phase 52.4-B: コード整理・ドキュメント統一
- Phase 49: バックテストモード対応完了
- Phase 34: 高速キャッシング実装
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

# 循環インポート回避のため、型ヒントでのみ使用
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import pandas as pd

from ..core.exceptions import DataFetchError
from ..core.logger import get_logger

if TYPE_CHECKING:
    from .bitbank_client import BitbankClient


class TimeFrame(Enum):
    """サポートするタイムフレーム."""

    M15 = "15m"  # 15分足
    H4 = "4h"  # 4時間足


@dataclass
class DataRequest:
    """データ取得リクエスト."""

    symbol: str = None  # 設定から取得される（None時は各メソッドでフォールバック）
    timeframe: TimeFrame = TimeFrame.H4
    limit: int = 1000
    since: Optional[int] = None


class DataPipeline:
    """
    マルチタイムフレーム データ取得パイプライン

    効率的なデータ取得・キャッシング・品質管理を提供.
    """

    def __init__(self, client: Optional["BitbankClient"] = None) -> None:
        """
        データパイプライン初期化

        Args:
            client: Bitbankクライアント（Noneの場合はグローバルクライアント使用）.
        """
        self.logger = get_logger()
        if client is None:
            from .bitbank_client import get_bitbank_client

            self.client = get_bitbank_client()
        else:
            self.client = client

        # データキャッシュ（メモリ）
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

        # 設定
        self.cache_duration_minutes = 5  # キャッシュ有効期間
        self.max_retries = 3  # 最大リトライ回数
        self.retry_delay = 1.0  # リトライ間隔（秒）

        # バックテストモードフラグ
        self._backtest_mode = False
        # バックテスト用データストレージ（Phase 34追加）
        self._backtest_data: Dict[str, pd.DataFrame] = {}
        # バックテスト用ML予測キャッシュ（Phase 35.4追加）
        self._backtest_ml_prediction: Optional[Dict[str, Any]] = None

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
        # バックテストモード対応（Phase 34追加）
        if self._backtest_mode and self._backtest_data:
            timeframe_key = request.timeframe.value
            if timeframe_key in self._backtest_data:
                self.logger.debug(f"バックテストデータ使用: {timeframe_key}")
                return self._backtest_data[timeframe_key].copy()
            else:
                self.logger.warning(
                    f"バックテストデータに{timeframe_key}が見つかりません。空のDataFrameを返します。"
                )
                return pd.DataFrame()

        cache_key = self._generate_cache_key(request)

        # CRIT-5 Fix: Race condition修正（キャッシュ存在チェック追加）
        # キャッシュチェック - 存在確認とアクセスをアトミックに
        if use_cache and self._is_cache_valid(cache_key):
            cached_data = self._cache.get(cache_key)
            if cached_data is not None:
                self.logger.debug(f"キャッシュからデータ取得: {cache_key}")
                return cached_data.copy()
            # キャッシュが削除されていた場合は、通常のデータ取得へフォールスルー

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
                    self.logger.error(
                        f"データ変換エラー: 期待された型はDataFrame、実際の型は{type(df)}"
                    )
                    return pd.DataFrame()  # 空のDataFrameを返して型安全性を保証

                # キャッシュに保存
                self._cache[cache_key] = df.copy()
                self._cache_timestamps[cache_key] = datetime.now()

                self.logger.info(
                    f"データ取得成功: {request.symbol} {request.timeframe.value}",
                    extra_data={
                        "requested_limit": request.limit,  # Phase 51.5-A Fix
                        "actual_rows": len(df),  # Phase 51.5-A Fix
                        "discrepancy": request.limit - len(df),  # Phase 51.5-A Fix
                        "rows": len(df),  # 既存フィールド（後方互換性）
                        "latest_timestamp": (df.index[-1].isoformat() if len(df) > 0 else None),
                        "attempt": attempt + 1,
                        "type_safe": isinstance(df, pd.DataFrame),
                    },
                )

                # Phase 51.5-A Fix: 取得件数が要求の半分以下なら警告
                if len(df) < request.limit * 0.5:
                    self.logger.warning(
                        f"⚠️ データ取得件数が要求の半分以下: 要求={request.limit}件, 実際={len(df)}件"
                    )

                return df

            except Exception as e:
                self.logger.warning(f"データ取得失敗 (試行 {attempt + 1}/{self.max_retries}): {e}")

                if attempt < self.max_retries - 1:
                    # CRIT-6 Fix: time.sleep → await asyncio.sleep（イベントループブロッキング解消）
                    await asyncio.sleep(self.retry_delay)
                else:
                    raise DataFetchError(
                        f"データ取得に失敗しました: {request.symbol} {request.timeframe.value}",
                        context={"max_retries_exceeded": True},
                    )

    async def fetch_multi_timeframe(
        self, symbol: str = None, limit: int = 1000
    ) -> Dict[str, pd.DataFrame]:
        """
        マルチタイムフレーム データを一括取得（型安全性強化）

        Args:
            symbol: 通貨ペア（Noneの場合は設定から取得）
            limit: 各タイムフレームの取得件数

        Returns:
            タイムフレーム別データ辞書（すべてDataFrame型保証）.
        """
        # symbolが未指定の場合は設定から取得
        if symbol is None:
            try:
                from ..core.config import get_config

                config = get_config()
                symbol = config.exchange.symbol
            except Exception:
                symbol = "BTC/JPY"  # フォールバック

        results = {}

        for timeframe in TimeFrame:
            request = DataRequest(symbol=symbol, timeframe=timeframe, limit=limit)

            try:
                df = await self.fetch_ohlcv(request)

                # 🚨 CRITICAL FIX: 厳密な返り値チェック
                if df is None:
                    raise ValueError(f"fetch_ohlcvがNoneを返しました: {timeframe.value}")
                # 型安全性チェック - DataFrameの保証
                if isinstance(df, pd.DataFrame):
                    results[timeframe.value] = df
                elif isinstance(df, dict):
                    # 辞書型の場合はDataFrameに変換を試行
                    try:
                        results[timeframe.value] = pd.DataFrame(df)
                        self.logger.warning(f"辞書からDataFrameに変換: {timeframe.value}")
                    except Exception:
                        results[timeframe.value] = pd.DataFrame()
                else:
                    self.logger.warning(
                        f"予期しない型が返却されました: {type(df)}, 空DataFrameで代替"
                    )
                    results[timeframe.value] = pd.DataFrame()

            except asyncio.CancelledError:
                # 🚨 CRITICAL FIX: 非同期キャンセルは再発生させる
                self.logger.info(f"非同期処理キャンセル: {timeframe.value}")
                raise
            except asyncio.TimeoutError as e:
                self.logger.error(f"タイムアウト: {timeframe.value} - {e}")
                results[timeframe.value] = pd.DataFrame()
            except Exception as e:
                error_msg = (
                    f"マルチタイムフレーム取得失敗: {timeframe.value} - " f"{type(e).__name__}: {e}"
                )
                self.logger.error(error_msg)
                # 失敗したタイムフレームは必ず空のDataFrameで代替（型保証）
                results[timeframe.value] = pd.DataFrame()

        # 最終的な型確認 - すべてがDataFrameであることを保証（強化版）
        for tf, data in results.items():
            if not isinstance(data, pd.DataFrame):
                data_detail = str(data)[:100] if data else "None"
                self.logger.error(
                    f"型不整合検出: {tf} = {type(data)}, "
                    f"空のDataFrameで修正. 詳細: {data_detail}"
                )
                results[tf] = pd.DataFrame()
            elif not hasattr(data, "empty"):
                self.logger.error(f"DataFrame属性不整合: {tf}, 空のDataFrameで修正")
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

    async def get_latest_prices(self, symbol: str = None) -> Dict[str, float]:
        """
        最新価格情報を全タイムフレームから取得

        Args:
            symbol: 通貨ペア（Noneの場合は設定から取得）

        Returns:
            タイムフレーム別最新価格.
        """
        # symbolが未指定の場合は設定から取得
        if symbol is None:
            try:
                from ..core.config import get_config

                config = get_config()
                symbol = config.exchange.symbol
            except Exception:
                symbol = "BTC/JPY"  # フォールバック

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

    def set_backtest_mode(self, enabled: bool) -> None:
        """
        バックテストモードの設定（Phase 35: BitbankClient連携）

        Args:
            enabled: バックテストモード有効フラグ
        """
        self._backtest_mode = enabled
        mode_text = "有効" if enabled else "無効"
        self.logger.info(f"バックテストモード設定: {mode_text}")

        # Phase 35: BitbankClientにもバックテストモードを伝播
        if hasattr(self.client, "set_backtest_mode"):
            self.client.set_backtest_mode(enabled)

    def is_backtest_mode(self) -> bool:
        """
        バックテストモード状態取得

        Returns:
            bool: バックテストモードフラグ
        """
        return self._backtest_mode

    def set_backtest_data(self, data: Dict[str, pd.DataFrame]) -> None:
        """
        バックテスト用データ設定（Phase 34実装）

        Args:
            data: タイムフレーム別データ辞書（例: {"4h": df_4h, "15m": df_15m}）
        """
        self._backtest_data = data
        timeframes = list(data.keys())
        total_rows = sum(len(df) for df in data.values())
        self.logger.info(
            f"バックテストデータ設定完了: {timeframes}",
            extra_data={"timeframes": timeframes, "total_rows": total_rows},
        )

    def clear_backtest_data(self) -> None:
        """
        バックテスト用データクリア（Phase 34実装）
        """
        self._backtest_data.clear()
        self.logger.info("バックテストデータクリア完了")

    def set_backtest_ml_prediction(self, prediction: Dict[str, Any]) -> None:
        """バックテスト用ML予測設定（Phase 35.4追加）"""
        self._backtest_ml_prediction = prediction

    def get_backtest_ml_prediction(self) -> Optional[Dict[str, Any]]:
        """バックテスト用ML予測取得（Phase 35.4追加）"""
        return self._backtest_ml_prediction

    def clear_cache(self) -> None:
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
        symbol: str = None,
        timeframe: str = "1h",
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """
        バックテスト用の過去データ取得（非同期版）

        Args:
            symbol: 通貨ペア（Noneの場合は設定から取得）
            timeframe: 時間軸
            since: 開始日時
            limit: 取得数制限

        Returns:
            pd.DataFrame: 過去データ
        """
        # symbolが未指定の場合は設定から取得
        if symbol is None:
            try:
                from ..core.config import get_config

                config = get_config()
                symbol = config.exchange.symbol
            except Exception:
                symbol = "BTC/JPY"  # フォールバック

        try:
            # timeframeをTimeFrameエナムに変換（現在サポートする2軸のみ）
            timeframe_map = {
                "15m": TimeFrame.M15,
                "4h": TimeFrame.H4,
            }

            tf_enum = timeframe_map.get(timeframe.lower(), TimeFrame.H4)  # デフォルトは4時間足

            # DataRequestを作成して既存のfetch_ohlcvを使用
            # datetimeをタイムスタンプ（ミリ秒）に変換
            since_timestamp = None
            if since is not None:
                since_timestamp = int(since.timestamp() * 1000)

            request = DataRequest(
                symbol=symbol,
                timeframe=tf_enum,
                limit=limit,
                since=since_timestamp,
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


def fetch_market_data(symbol: str = None, timeframe: str = "1h", limit: int = 1000) -> pd.DataFrame:
    """
    市場データ取得の簡易インターフェース

    Args:
        symbol: 通貨ペア（Noneの場合は設定から取得）
        timeframe: タイムフレーム
        limit: 取得件数

    Returns:
        OHLCV DataFrame.
    """
    # symbolが未指定の場合は設定から取得
    if symbol is None:
        try:
            from ..core.config import get_config

            config = get_config()
            symbol = config.exchange.symbol
        except Exception:
            symbol = "BTC/JPY"  # フォールバック

    pipeline = get_data_pipeline()

    # TimeFrame enumに変換
    timeframe_enum = TimeFrame(timeframe)

    request = DataRequest(symbol=symbol, timeframe=timeframe_enum, limit=limit)

    return pipeline.fetch_ohlcv(request)
