"""
バックテスト用データローダー - Phase 12・CI/CD統合・手動実行監視・段階的デプロイ対応

過去6ヶ月データの効率的な取得・管理・キャッシュ機能を提供。
Phase 1-11システム（DataPipeline・DataCache）と統合・GitHub Actions対応し、
高速で信頼性の高いバックテスト環境を実現。

主要機能:
- 過去6ヶ月データ自動取得・CI/CD統合
- 複数タイムフレーム対応・手動実行監視対応
- インテリジェントキャッシング・段階的デプロイ対応
- データ品質チェック・GitHub Actions対応
- 欠損データ補完・CI/CD品質ゲート対応.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..core.config import load_config
from ..core.exceptions import CryptoBotError, DataQualityError
from ..core.logger import get_logger
from ..data.data_cache import DataCache
from ..data.data_pipeline import DataPipeline


class DataLoader:
    """
    バックテスト用データローダー

    Phase 2データ層と統合し、効率的なデータ管理を実現。
    キャッシュ機能により高速なバックテスト実行をサポート。.
    """

    def __init__(self, config_path: str = "config/core/base.yaml"):
        self.logger = get_logger(__name__)

        # 設定読み込み
        try:
            self.config = load_config(config_path)
        except Exception as e:
            self.logger.warning(f"設定読み込み失敗: {e}")
            self.config = self._get_default_config()

        # Phase 2システム統合
        self.data_pipeline = DataPipeline()
        self.data_cache = DataCache()

        # バックテスト専用データディレクトリ
        self.data_dir = Path(__file__).parent / "data" / "historical"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # データ品質設定
        self.quality_thresholds = {
            "min_data_points": 1000,  # 最小データ数
            "max_gap_hours": 2,  # 最大データ欠損時間
            "volume_threshold": 1000,  # 最小出来高
            "price_change_limit": 0.2,  # 20%以上の価格変動制限
        }

        self.logger.info("DataLoader初期化完了")

    async def load_historical_data(
        self,
        symbol: str = "BTC/JPY",
        months: int = 6,
        timeframes: List[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        """
        過去データ取得（メイン機能）

        Args:
            symbol: 通貨ペア
            months: 取得月数
            timeframes: 対象タイムフレーム
            force_refresh: 強制再取得フラグ

        Returns:
            タイムフレーム別データ辞書.
        """
        if timeframes is None:
            timeframes = ["15m", "1h", "4h"]

        self.logger.info(f"過去データ取得開始: {symbol} {months}ヶ月 {timeframes}")

        # データ取得期間計算
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)

        data_dict = {}

        for timeframe in timeframes:
            try:
                # キャッシュ確認
                if not force_refresh:
                    cached_data = await self._load_from_cache(
                        symbol, timeframe, start_date, end_date
                    )
                    if cached_data is not None:
                        data_dict[timeframe] = cached_data
                        continue

                # データ取得
                raw_data = await self._fetch_timeframe_data(symbol, timeframe, start_date, end_date)

                # データ品質チェック
                cleaned_data = await self._validate_and_clean_data(raw_data, timeframe)

                # キャッシュ保存
                await self._save_to_cache(symbol, timeframe, cleaned_data, start_date, end_date)

                data_dict[timeframe] = cleaned_data

                self.logger.info(f"{timeframe}データ取得完了: {len(cleaned_data)}件")

            except Exception as e:
                self.logger.error(f"{timeframe}データ取得エラー: {e}")
                # エラー時は空のDataFrameを設定
                data_dict[timeframe] = pd.DataFrame()

        # 統合データ品質チェック
        await self._validate_integrated_data(data_dict)

        self.logger.info(f"過去データ取得完了: {len(data_dict)}タイムフレーム")
        return data_dict

    async def _fetch_timeframe_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """特定タイムフレームのデータ取得."""

        # 分割取得（API制限対応）
        all_data = []
        current_date = start_date
        chunk_days = 30  # 30日ずつ取得

        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_date)

            try:
                chunk_data = await self.data_pipeline.fetch_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_date,
                    limit=2000,  # Bitbank制限
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
                self.logger.warning(f"チャンクデータ取得エラー: {e}")

            current_date = chunk_end

        # データ統合
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=False)
            combined_data = combined_data.sort_index().drop_duplicates()
            return combined_data
        else:
            return pd.DataFrame()

    async def _validate_and_clean_data(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """データ品質チェック・クリーニング."""
        if data.empty:
            raise DataQualityError(f"{timeframe}: データが空です")

        original_length = len(data)

        # 1. 必須カラム確認
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise DataQualityError(f"必須カラム不足: {missing_columns}")

        # 2. 数値データ検証
        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

        # 3. NaN値除去
        data = data.dropna(subset=numeric_columns)

        # 4. 異常値検出・除去
        data = self._remove_outliers(data)

        # 5. 価格整合性チェック
        data = self._validate_price_consistency(data)

        # 6. 出来高フィルタリング
        data = data[data["volume"] >= self.quality_thresholds["volume_threshold"]]

        # 7. 時系列ソート・重複除去
        data = data.sort_index().drop_duplicates()

        # 8. データ十分性チェック
        final_length = len(data)
        if final_length < self.quality_thresholds["min_data_points"]:
            raise DataQualityError(
                f"{timeframe}: データ不足 {final_length}/{self.quality_thresholds['min_data_points']}"
            )

        # 9. 欠損データ補完
        data = await self._interpolate_missing_data(data, timeframe)

        self.logger.info(
            f"{timeframe}データクリーニング完了: "
            f"{original_length}→{final_length}件 ({final_length/original_length:.1%})"
        )

        return data

    def _remove_outliers(self, data: pd.DataFrame) -> pd.DataFrame:
        """異常値除去."""
        # 価格変動率による異常値検出
        price_changes = data["close"].pct_change().abs()
        change_limit = self.quality_thresholds["price_change_limit"]

        # 極端な価格変動を除去
        valid_mask = price_changes <= change_limit
        valid_mask.iloc[0] = True  # 最初の行は保持

        outlier_count = (~valid_mask).sum()
        if outlier_count > 0:
            self.logger.warning(f"異常値除去: {outlier_count}件")

        return data[valid_mask]

    def _validate_price_consistency(self, data: pd.DataFrame) -> pd.DataFrame:
        """価格整合性チェック."""
        # OHLC関係の検証
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
            self.logger.warning(f"価格整合性エラー除去: {invalid_count}件")

        return data[valid_mask]

    async def _interpolate_missing_data(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """欠損データ補完."""

        # タイムフレーム別の期待間隔
        timeframe_minutes = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
        }

        if timeframe not in timeframe_minutes:
            return data

        interval = timedelta(minutes=timeframe_minutes[timeframe])

        # 期待される時系列インデックス生成
        start_time = data.index.min()
        end_time = data.index.max()
        expected_index = pd.date_range(start=start_time, end=end_time, freq=interval)

        # 欠損期間特定
        missing_periods = expected_index.difference(data.index)

        if len(missing_periods) > 0:
            self.logger.info(f"{timeframe}: {len(missing_periods)}期間を補完")

            # リインデックス（欠損値は自動的にNaNになる）
            data = data.reindex(expected_index)

            # 前値補完（前進補完）
            data = data.fillna(method="ffill", limit=5)  # 最大5期間

            # 後値補完（後進補完）
            data = data.fillna(method="bfill", limit=5)  # 最大5期間

            # まだNaNが残っている場合は除去
            data = data.dropna()

        return data

    async def _validate_integrated_data(self, data_dict: Dict[str, pd.DataFrame]):
        """統合データ品質チェック."""

        # 各タイムフレームの期間一致チェック
        date_ranges = {}
        for timeframe, df in data_dict.items():
            if not df.empty:
                date_ranges[timeframe] = (df.index.min(), df.index.max())

        if len(date_ranges) > 1:
            # 期間の重複チェック
            min_start = max(start for start, _ in date_ranges.values())
            max_end = min(end for _, end in date_ranges.values())

            if min_start >= max_end:
                raise DataQualityError("タイムフレーム間で重複期間がありません")

            overlap_days = (max_end - min_start).days
            self.logger.info(f"統合データ重複期間: {overlap_days}日")

    async def _load_from_cache(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[pd.DataFrame]:
        """キャッシュからデータ読み込み."""

        cache_key = f"backtest_{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

        try:
            cached_data = await self.data_cache.get(cache_key)
            if cached_data is not None and not cached_data.empty:
                self.logger.info(f"{timeframe}キャッシュヒット: {len(cached_data)}件")
                return cached_data
        except Exception as e:
            self.logger.debug(f"キャッシュ読み込みエラー: {e}")

        return None

    async def _save_to_cache(
        self,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame,
        start_date: datetime,
        end_date: datetime,
    ):
        """キャッシュにデータ保存."""

        cache_key = f"backtest_{symbol}_{timeframe}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

        try:
            await self.data_cache.set(cache_key, data, ttl_hours=24 * 7)  # 1週間保持

            # ファイル保存も実行
            file_path = self.data_dir / f"{cache_key}.csv"
            data.to_csv(file_path)

            self.logger.debug(f"{timeframe}キャッシュ保存完了: {len(data)}件")

        except Exception as e:
            self.logger.warning(f"キャッシュ保存エラー: {e}")

    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定."""
        return {
            "data": {
                "timeframes": ["15m", "1h", "4h"],
                "since_hours": 24 * 30 * 6,  # 6ヶ月
                "limit": 2000,
                "cache": {
                    "enabled": True,
                    "ttl_minutes": 60,
                    "max_size": 1000,
                },
            }
        }

    async def get_data_summary(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """データサマリー生成."""

        summary = {
            "timeframes": list(data_dict.keys()),
            "data_quality": {},
            "period_info": {},
            "statistics": {},
        }

        for timeframe, df in data_dict.items():
            if df.empty:
                continue

            # 品質情報
            summary["data_quality"][timeframe] = {
                "data_points": len(df),
                "start_date": df.index.min(),
                "end_date": df.index.max(),
                "missing_values": df.isnull().sum().sum(),
                "duplicate_count": df.index.duplicated().sum(),
            }

            # 統計情報
            if "close" in df.columns:
                summary["statistics"][timeframe] = {
                    "price_range": {
                        "min": df["close"].min(),
                        "max": df["close"].max(),
                        "mean": df["close"].mean(),
                    },
                    "volume_stats": (
                        {
                            "mean": df["volume"].mean(),
                            "median": df["volume"].median(),
                        }
                        if "volume" in df.columns
                        else {}
                    ),
                }

        return summary
