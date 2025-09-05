"""
データ取得パイプライン - マルチタイムフレーム対応

15分足と4時間足のデータを効率的に取得・管理する
シンプルで高速なデータパイプライン実装。

主な特徴:
- マルチタイムフレーム対応（15m, 4h）2軸構成
- 効率的なデータキャッシング
- エラーハンドリングと自動リトライ
- データ品質チェック機能

Phase 13改善実装日: 2025年8月24日.
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
    from .bitbank_client import BitbankClient, get_bitbank_client


class TimeFrame(Enum):
    """サポートするタイムフレーム."""

    M15 = "15m"  # 15分足
    H4 = "4h"  # 4時間足


@dataclass
class DataRequest:
    """データ取得リクエスト."""

    symbol: str = "BTC/JPY"
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

        self.logger.info("データパイプライン初期化完了")

        # Phase 18統合: バックテスト機能統合
        self.backtest_data_dir = Path(__file__).parent / "historical"
        self.backtest_data_dir.mkdir(parents=True, exist_ok=True)

        # バックテスト用データ品質設定
        self.backtest_quality_thresholds = {
            "min_data_points": 1000,  # 最小データ数
            "max_gap_hours": 2,  # 最大データ欠損時間
            "volume_threshold": 1000,  # 最小出来高
            "price_change_limit": 0.2,  # 20%以上の価格変動制限
        }

        # バックテスト用長期キャッシュ設定
        self.backtest_cache_duration_hours = 24 * 7  # 1週間

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
        symbol: str = "BTC/JPY",
        timeframe: str = "1h",
        since: Optional[datetime] = None,
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


# Phase 18統合: DataLoader機能統合（バックテスト専用）


class BacktestDataLoader:
    """
    バックテスト用データローダー（Phase 18統合版）

    DataLoaderからの統合機能。DataPipelineを基盤として、
    バックテスト専用の長期データ取得・高品質データ管理を提供。
    """

    def __init__(self, data_pipeline: Optional[DataPipeline] = None):
        """バックテストデータローダー初期化"""
        self.logger = get_logger(__name__)
        self.data_pipeline = data_pipeline or get_data_pipeline()

        # バックテスト専用データディレクトリ
        self.data_dir = Path(__file__).parent / "historical"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # データ品質設定（DataLoaderから統合）
        self.quality_thresholds = {
            "min_data_points": 1000,  # 最小データ数
            "max_gap_hours": 2,  # 最大データ欠損時間
            "volume_threshold": 1000,  # 最小出来高
            "price_change_limit": 0.2,  # 20%以上の価格変動制限
        }

        self.logger.info("BacktestDataLoader初期化完了（Phase 18統合版）")

    async def load_historical_data(
        self,
        symbol: str = "BTC/JPY",
        months: int = 6,
        timeframes: List[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        """
        過去データ取得（DataLoaderから統合）

        Args:
            symbol: 通貨ペア
            months: 取得月数
            timeframes: 対象タイムフレーム
            force_refresh: 強制再取得フラグ

        Returns:
            タイムフレーム別データ辞書
        """
        if timeframes is None:
            timeframes = ["15m", "1h", "4h"]

        self.logger.info(f"過去データ取得開始（統合版）: {symbol} {months}ヶ月 {timeframes}")

        # データ取得期間計算
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)

        data_dict = {}

        for timeframe in timeframes:
            try:
                # キャッシュ確認（長期キャッシュ）
                if not force_refresh:
                    cached_data = await self._load_from_backtest_cache(
                        symbol, timeframe, start_date, end_date
                    )
                    if cached_data is not None:
                        data_dict[timeframe] = cached_data
                        continue

                # データ取得（DataPipelineを使用）
                raw_data = await self._fetch_timeframe_data_integrated(
                    symbol, timeframe, start_date, end_date
                )

                # データ品質チェック（統合版）
                cleaned_data = await self._validate_and_clean_data_integrated(raw_data, timeframe)

                # バックテスト専用キャッシュ保存
                await self._save_to_backtest_cache(
                    symbol, timeframe, cleaned_data, start_date, end_date
                )

                data_dict[timeframe] = cleaned_data

                self.logger.info(f"{timeframe}データ取得完了（統合版）: {len(cleaned_data)}件")

            except Exception as e:
                self.logger.error(f"{timeframe}データ取得エラー（統合版）: {e}")
                data_dict[timeframe] = pd.DataFrame()

        # 統合データ品質チェック
        await self._validate_integrated_data(data_dict)

        self.logger.info(f"過去データ取得完了（統合版）: {len(data_dict)}タイムフレーム")
        return data_dict

    async def _fetch_timeframe_data_integrated(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """DataPipeline統合データ取得"""
        all_data = []
        current_date = start_date
        chunk_days = 30

        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_date)

            try:
                # DataPipelineを使用してデータ取得
                chunk_data = await self.data_pipeline.fetch_historical_data(
                    symbol=symbol, timeframe=timeframe, since=current_date, limit=2000
                )

                if not chunk_data.empty:
                    # 期間フィルタリング
                    chunk_data = chunk_data[
                        (chunk_data.index >= current_date) & (chunk_data.index < chunk_end)
                    ]
                    all_data.append(chunk_data)

                # レート制限対応
                await asyncio.sleep(1.0)

            except Exception as e:
                self.logger.warning(f"チャンクデータ取得エラー（統合版）: {e}")

            current_date = chunk_end

        # データ統合
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=False)
            combined_data = combined_data.sort_index().drop_duplicates()
            return combined_data
        else:
            return pd.DataFrame()

    async def _validate_and_clean_data_integrated(
        self, data: pd.DataFrame, timeframe: str
    ) -> pd.DataFrame:
        """データ品質チェック・クリーニング（統合版）"""
        if data.empty:
            from ..core.exceptions import DataQualityError

            raise DataQualityError(f"{timeframe}: データが空です（統合版）")

        original_length = len(data)

        # 基本的なデータクリーニング（DataLoaderから統合）
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            from ..core.exceptions import DataQualityError

            raise DataQualityError(f"必須カラム不足（統合版）: {missing_columns}")

        # 数値データ検証
        for col in required_columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

        # NaN値除去
        data = data.dropna(subset=required_columns)

        # 異常値検出・除去
        data = self._remove_outliers_integrated(data)

        # 価格整合性チェック
        data = self._validate_price_consistency_integrated(data)

        # 出来高フィルタリング
        data = data[data["volume"] >= self.quality_thresholds["volume_threshold"]]

        # データ十分性チェック
        final_length = len(data)
        if final_length < self.quality_thresholds["min_data_points"]:
            from ..core.exceptions import DataQualityError

            raise DataQualityError(
                f"{timeframe}: データ不足（統合版） {final_length}/{self.quality_thresholds['min_data_points']}"
            )

        self.logger.info(
            f"{timeframe}データクリーニング完了（統合版）: "
            f"{original_length}→{final_length}件 ({final_length / original_length:.1%})"
        )

        return data

    def _remove_outliers_integrated(self, data: pd.DataFrame) -> pd.DataFrame:
        """異常値除去（統合版）"""
        price_changes = data["close"].pct_change().abs()
        change_limit = self.quality_thresholds["price_change_limit"]

        valid_mask = price_changes <= change_limit
        valid_mask.iloc[0] = True  # 最初の行は保持

        outlier_count = (~valid_mask).sum()
        if outlier_count > 0:
            self.logger.warning(f"異常値除去（統合版）: {outlier_count}件")

        return data[valid_mask]

    def _validate_price_consistency_integrated(self, data: pd.DataFrame) -> pd.DataFrame:
        """価格整合性チェック（統合版）"""
        valid_mask = (
            (data["high"] >= data["low"])
            & (data["high"] >= data["open"])
            & (data["high"] >= data["close"])
            & (data["low"] <= data["open"])
            & (data["low"] <= data["close"])
            & (data["open"] > 0)
            & (data["high"] > 0)
            & (data["low"] > 0)
            & (data["close"] > 0)
        )

        invalid_count = (~valid_mask).sum()
        if invalid_count > 0:
            self.logger.warning(f"価格整合性エラー除去（統合版）: {invalid_count}件")

        return data[valid_mask]

    async def _load_from_backtest_cache(
        self, symbol: str, timeframe: str, start_date: datetime, end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """バックテスト用長期キャッシュ読み込み"""
        cache_key = f"backtest_{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        file_path = self.data_dir / f"{cache_key}.csv"

        try:
            if file_path.exists():
                # ファイル更新時刻チェック（1週間キャッシュ）
                import os

                file_age_hours = (datetime.now().timestamp() - os.path.getmtime(file_path)) / 3600

                if file_age_hours < 24 * 7:  # 1週間以内
                    cached_data = pd.read_csv(file_path, index_col=0, parse_dates=True)
                    self.logger.info(
                        f"{timeframe}バックテストキャッシュヒット: {len(cached_data)}件"
                    )
                    return cached_data

        except Exception as e:
            self.logger.debug(f"バックテストキャッシュ読み込みエラー: {e}")

        return None

    async def _save_to_backtest_cache(
        self,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime,
    ):
        """バックテスト用長期キャッシュ保存"""
        cache_key = f"backtest_{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        file_path = self.data_dir / f"{cache_key}.csv"

        try:
            data.to_csv(file_path)
            self.logger.debug(f"{timeframe}バックテストキャッシュ保存完了: {len(data)}件")
        except Exception as e:
            self.logger.warning(f"バックテストキャッシュ保存エラー: {e}")

    async def _validate_integrated_data(self, data_dict: Dict[str, pd.DataFrame]):
        """統合データ品質チェック（統合版）"""
        date_ranges = {}
        for timeframe, df in data_dict.items():
            if not df.empty:
                date_ranges[timeframe] = (df.index.min(), df.index.max())

        if len(date_ranges) > 1:
            min_start = max(start for start, _ in date_ranges.values())
            max_end = min(end for _, end in date_ranges.values())

            if min_start >= max_end:
                from ..core.exceptions import DataQualityError

                raise DataQualityError("タイムフレーム間で重複期間がありません（統合版）")

            overlap_days = (max_end - min_start).days
            self.logger.info(f"統合データ重複期間（統合版）: {overlap_days}日")


# バックテストデータローダー取得用グローバル関数
_backtest_data_loader: Optional[BacktestDataLoader] = None


def get_backtest_data_loader() -> BacktestDataLoader:
    """グローバルバックテストデータローダー取得"""
    global _backtest_data_loader

    if _backtest_data_loader is None:
        _backtest_data_loader = BacktestDataLoader()

    return _backtest_data_loader
