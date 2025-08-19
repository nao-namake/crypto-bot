# =============================================================================
# ファイル名: crypto_bot/data/timeframe_synchronizer.py
# 説明:
# マルチタイムフレームデータ同期・統合システム
# ・時刻アライメント・欠損データ補完・整合性チェック
# ・リアルタイム同期・クロスタイムフレーム検証
# ・Phase 2.2: データ同期・統合システム実装
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


class TimeframeSynchronizer:
    """マルチタイムフレームデータ同期・統合システム"""

    def __init__(
        self,
        timeframes: List[str] = None,
        base_timeframe: str = "1h",
        sync_tolerance: timedelta = None,
        missing_data_threshold: float = 0.1,
        consistency_check_enabled: bool = True,
    ):
        """
        初期化

        Args:
            timeframes: 対象タイムフレーム
            base_timeframe: ベースタイムフレーム
            sync_tolerance: 同期許容誤差
            missing_data_threshold: 欠損データ許容率
            consistency_check_enabled: 整合性チェック有効化
        """
        self.timeframes = timeframes or ["15m", "1h", "4h"]
        self.base_timeframe = base_timeframe
        self.sync_tolerance = sync_tolerance or timedelta(minutes=1)
        self.missing_data_threshold = missing_data_threshold
        self.consistency_check_enabled = consistency_check_enabled

        # 同期統計
        self.sync_stats = {
            "sync_operations": 0,
            "alignment_corrections": 0,
            "missing_data_filled": 0,
            "consistency_violations": 0,
            "quality_improvements": 0,
        }

        # タイムフレーム期間マッピング
        self.timeframe_periods = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "30m": timedelta(minutes=30),
            "1h": timedelta(hours=1),
            "2h": timedelta(hours=2),
            "4h": timedelta(hours=4),
            "8h": timedelta(hours=8),
            "12h": timedelta(hours=12),
            "1d": timedelta(days=1),
        }

        logger.info("🔄 TimeframeSynchronizer initialized")
        logger.info(f"  - Timeframes: {self.timeframes}")
        logger.info(f"  - Base timeframe: {self.base_timeframe}")
        logger.info(f"  - Sync tolerance: {self.sync_tolerance}")

    def synchronize_multi_timeframe_data(
        self, multi_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        マルチタイムフレームデータの同期・統合

        Args:
            multi_data: タイムフレーム別データ辞書

        Returns:
            Dict[str, pd.DataFrame]: 同期済みデータ
        """
        try:
            logger.info("🔄 Starting multi-timeframe synchronization")
            self.sync_stats["sync_operations"] += 1

            if not multi_data:
                logger.warning("⚠️ No data to synchronize")
                return {}

            # 1. 時刻アライメント
            aligned_data = self._align_timeframes(multi_data)

            # 2. 欠損データ補完
            filled_data = self._fill_missing_data(aligned_data)

            # 3. 整合性チェック・修正
            if self.consistency_check_enabled:
                consistent_data = self._ensure_consistency(filled_data)
            else:
                consistent_data = filled_data

            # 4. 品質向上
            improved_data = self._improve_data_quality(consistent_data)

            logger.info("✅ Multi-timeframe synchronization complete")
            logger.info(f"  - Processed {len(improved_data)} timeframes")

            return improved_data

        except Exception as e:
            logger.error(f"❌ Multi-timeframe synchronization failed: {e}")
            return multi_data

    def _align_timeframes(
        self, multi_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """タイムフレーム時刻アライメント"""
        try:
            logger.debug("🔄 Aligning timeframes")
            aligned_data = {}

            # ベースタイムフレームの時刻範囲を取得
            base_data = multi_data.get(self.base_timeframe)
            if base_data is None or base_data.empty:
                logger.warning(f"⚠️ Base timeframe {self.base_timeframe} not available")
                return multi_data

            base_start = base_data.index.min()
            base_end = base_data.index.max()

            for timeframe, data in multi_data.items():
                if data.empty:
                    aligned_data[timeframe] = data
                    continue

                try:
                    # タイムフレーム期間を取得
                    period = self.timeframe_periods.get(timeframe)
                    if period is None:
                        logger.warning(f"⚠️ Unknown timeframe period: {timeframe}")
                        aligned_data[timeframe] = data
                        continue

                    # 標準的な時刻グリッドを生成
                    aligned_index = self._generate_aligned_index(
                        base_start, base_end, period, timeframe
                    )

                    # データを標準グリッドにアライメント
                    aligned_data[timeframe] = self._align_to_index(
                        data, aligned_index, timeframe
                    )

                    logger.debug(
                        f"✅ Aligned {timeframe}: {len(data)} -> {len(aligned_data[timeframe])} records"
                    )

                except Exception as e:
                    logger.error(f"❌ Failed to align {timeframe}: {e}")
                    aligned_data[timeframe] = data

            self.sync_stats["alignment_corrections"] += len(multi_data)
            return aligned_data

        except Exception as e:
            logger.error(f"❌ Timeframe alignment failed: {e}")
            return multi_data

    def _generate_aligned_index(
        self,
        start_time: datetime,
        end_time: datetime,
        period: timedelta,
        timeframe: str,
    ) -> pd.DatetimeIndex:
        """標準時刻グリッド生成"""
        try:
            # タイムフレームに応じた開始時刻調整
            if timeframe in ["4h", "8h", "12h"]:
                # 4時間・8時間・12時間足は00:00UTCから開始
                # ✅ Phase H.14修正: period.total_seconds()をint()で明示的型変換
                hours_per_period = int(period.total_seconds() // 3600)
                aligned_hour = (start_time.hour // hours_per_period) * hours_per_period
                aligned_start = start_time.replace(
                    hour=aligned_hour,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            elif timeframe in ["1d"]:
                # 日足は00:00UTCから開始
                aligned_start = start_time.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
            else:
                # 分足・時間足は適切な境界に調整
                if period.total_seconds() >= 3600:  # 1時間以上
                    aligned_start = start_time.replace(
                        minute=0, second=0, microsecond=0
                    )
                else:  # 1時間未満
                    minute_period = int(period.total_seconds() // 60)
                    aligned_minute = (
                        start_time.minute // minute_period
                    ) * minute_period
                    aligned_start = start_time.replace(
                        minute=aligned_minute, second=0, microsecond=0
                    )

            # 標準グリッド生成
            freq_str = self._period_to_freq_string(period, timeframe)
            return pd.date_range(start=aligned_start, end=end_time, freq=freq_str)

        except Exception as e:
            logger.error(f"❌ Failed to generate aligned index: {e}")
            return pd.date_range(start=start_time, end=end_time, freq="1h")

    def _period_to_freq_string(self, period: timedelta, timeframe: str) -> str:
        """timedelta を pandas frequency string に変換"""
        total_seconds = period.total_seconds()

        if total_seconds < 3600:  # 1時間未満
            minutes = int(total_seconds // 60)
            return f"{minutes}T"
        elif total_seconds < 86400:  # 1日未満
            hours = int(total_seconds // 3600)
            return f"{hours}h"
        else:  # 1日以上
            days = int(total_seconds // 86400)
            return f"{days}D"

    def _align_to_index(
        self, data: pd.DataFrame, target_index: pd.DatetimeIndex, timeframe: str
    ) -> pd.DataFrame:
        """データを指定インデックスにアライメント"""
        try:
            # 最近傍時刻マッピング
            aligned_data = pd.DataFrame(index=target_index, columns=data.columns)

            for target_time in target_index:
                # 許容誤差内の最近傍データを検索
                time_diff = np.abs(data.index - target_time)
                # ✅ Phase H.14修正: TimedeltaIndexエラー完全解決・argmin()でint取得・直接インデックス使用
                min_diff_argmin = time_diff.argmin()
                min_diff_idx = data.index[min_diff_argmin]
                min_diff = time_diff[
                    min_diff_argmin
                ]  # TimedeltaIndexは直接インデックスアクセス

                if min_diff <= self.sync_tolerance:
                    aligned_data.loc[target_time] = data.loc[min_diff_idx]

            # 欠損データのマーク
            missing_count = aligned_data.isnull().all(axis=1).sum()
            if missing_count > 0:
                logger.debug(
                    f"📊 {timeframe}: {missing_count} missing records after alignment"
                )

            return aligned_data

        except Exception as e:
            logger.error(f"❌ Failed to align data to index: {e}")
            return data

    def _fill_missing_data(
        self, multi_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """欠損データ補完"""
        try:
            logger.debug("🔄 Filling missing data")
            filled_data = {}

            for timeframe, data in multi_data.items():
                if data.empty:
                    filled_data[timeframe] = data
                    continue

                try:
                    # 欠損率チェック
                    missing_ratio = data.isnull().all(axis=1).mean()
                    if missing_ratio > self.missing_data_threshold:
                        logger.warning(
                            f"⚠️ {timeframe}: High missing ratio " f"{missing_ratio:.2f}"
                        )

                    # 欠損データ補完
                    filled = self._intelligent_fill_missing(data, timeframe)
                    filled_data[timeframe] = filled

                    fill_count = data.isnull().sum().sum() - filled.isnull().sum().sum()
                    if fill_count > 0:
                        logger.debug(
                            f"✅ {timeframe}: Filled {fill_count} missing values"
                        )
                        self.sync_stats["missing_data_filled"] += fill_count

                except Exception as e:
                    logger.error(f"❌ Failed to fill missing data for {timeframe}: {e}")
                    filled_data[timeframe] = data

            return filled_data

        except Exception as e:
            logger.error(f"❌ Missing data filling failed: {e}")
            return multi_data

    def _intelligent_fill_missing(
        self, data: pd.DataFrame, timeframe: str
    ) -> pd.DataFrame:
        """高度な欠損データ補完"""
        try:
            filled = data.copy()

            # OHLCVの各列に対して適切な補完を実行
            for col in data.columns:
                if col in ["open", "high", "low", "close"]:
                    # 価格データ: 時間加重補間
                    filled[col] = self._time_weighted_interpolation(data[col])
                elif col == "volume":
                    # ボリューム: ゼロ埋め後に移動平均補間
                    filled[col] = self._volume_interpolation(data[col])
                else:
                    # その他: 線形補間
                    filled[col] = data[col].interpolate(method="linear")

            # OHLC整合性の確保
            if all(col in filled.columns for col in ["open", "high", "low", "close"]):
                filled = self._ensure_ohlc_consistency(filled)

            return filled

        except Exception as e:
            logger.error(f"❌ Intelligent fill failed: {e}")
            return data

    def _time_weighted_interpolation(self, series: pd.Series) -> pd.Series:
        """時間加重補間"""
        try:
            # 基本線形補間
            interpolated = series.interpolate(method="linear")

            # 長期間の欠損に対してはトレンド考慮補間
            missing_mask = series.isnull()
            if missing_mask.any():
                # 前後の有効データポイントを使用してトレンド補間
                interpolated = series.interpolate(method="cubic")

            return interpolated

        except Exception:
            # フォールバック: 線形補間
            return series.interpolate(method="linear")

    def _volume_interpolation(self, volume_series: pd.Series) -> pd.Series:
        """ボリューム補間"""
        try:
            filled = volume_series.copy()

            # ボリュームのゼロ値を一時的に欠損として扱う
            zero_mask = filled == 0
            filled[zero_mask] = np.nan

            # 移動平均ベースの補間
            ma_7 = filled.rolling(window=7, min_periods=3).mean()
            ma_24 = filled.rolling(window=24, min_periods=12).mean()

            # 欠損箇所を移動平均で埋める
            filled = filled.fillna(ma_7).fillna(ma_24)

            # 元のゼロ値は保持
            filled[zero_mask] = 0

            # 負値の除去
            filled = np.maximum(filled, 0)

            return filled

        except Exception:
            # フォールバック: 線形補間
            return volume_series.interpolate(method="linear").fillna(0)

    def _ensure_consistency(
        self, multi_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """クロスタイムフレーム整合性確保"""
        try:
            logger.debug("🔄 Ensuring cross-timeframe consistency")
            consistent_data = multi_data.copy()

            # ベースタイムフレームを基準とした整合性チェック
            base_data = consistent_data.get(self.base_timeframe)
            if base_data is None or base_data.empty:
                return consistent_data

            for timeframe, data in consistent_data.items():
                if timeframe == self.base_timeframe or data.empty:
                    continue

                try:
                    # 整合性チェック・修正
                    corrected = self._cross_timeframe_validation(
                        data, base_data, timeframe
                    )
                    consistent_data[timeframe] = corrected

                except Exception as e:
                    logger.error(f"❌ Consistency check failed for {timeframe}: {e}")

            return consistent_data

        except Exception as e:
            logger.error(f"❌ Consistency ensuring failed: {e}")
            return multi_data

    def _cross_timeframe_validation(
        self, data: pd.DataFrame, base_data: pd.DataFrame, timeframe: str
    ) -> pd.DataFrame:
        """クロスタイムフレーム検証・修正"""
        try:
            corrected = data.copy()
            period = self.timeframe_periods.get(timeframe)

            if period is None or "close" not in data.columns:
                return corrected

            # 価格の妥当性チェック
            violations = 0
            for timestamp, row in data.iterrows():
                if pd.isnull(row["close"]):
                    continue

                # 対応するベース期間のデータを取得
                base_period_data = self._get_base_period_data(
                    base_data, timestamp, period
                )

                if base_period_data.empty:
                    continue

                # 価格範囲チェック
                base_min = base_period_data["low"].min()
                base_max = base_period_data["high"].max()

                # 異常値検出・修正
                if row["close"] < base_min * 0.95 or row["close"] > base_max * 1.05:
                    # 5%を超える乖離は異常値として修正
                    corrected.loc[timestamp, "close"] = base_period_data["close"].iloc[
                        -1
                    ]
                    violations += 1

            if violations > 0:
                logger.debug(
                    f"🔧 {timeframe}: Corrected {violations} consistency violations"
                )
                self.sync_stats["consistency_violations"] += violations

            return corrected

        except Exception as e:
            logger.error(f"❌ Cross-timeframe validation failed: {e}")
            return data

    def _get_base_period_data(
        self, base_data: pd.DataFrame, timestamp: datetime, period: timedelta
    ) -> pd.DataFrame:
        """指定期間のベースデータ取得"""
        try:
            start_time = timestamp - period
            end_time = timestamp

            return base_data.loc[
                (base_data.index >= start_time) & (base_data.index <= end_time)
            ]

        except Exception:
            return pd.DataFrame()

    def _improve_data_quality(
        self, multi_data: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """データ品質向上"""
        try:
            logger.debug("🔄 Improving data quality")
            improved_data = {}

            for timeframe, data in multi_data.items():
                if data.empty:
                    improved_data[timeframe] = data
                    continue

                try:
                    improved = data.copy()

                    # OHLC整合性確保
                    if all(
                        col in improved.columns
                        for col in ["open", "high", "low", "close"]
                    ):
                        improved = self._ensure_ohlc_consistency(improved)

                    # 外れ値のスムージング
                    improved = self._smooth_outliers(improved, timeframe)

                    # ボリュームの正規化
                    if "volume" in improved.columns:
                        improved["volume"] = np.maximum(improved["volume"], 0)

                    improved_data[timeframe] = improved
                    self.sync_stats["quality_improvements"] += 1

                except Exception as e:
                    logger.error(f"❌ Quality improvement failed for {timeframe}: {e}")
                    improved_data[timeframe] = data

            return improved_data

        except Exception as e:
            logger.error(f"❌ Data quality improvement failed: {e}")
            return multi_data

    def _ensure_ohlc_consistency(self, data: pd.DataFrame) -> pd.DataFrame:
        """OHLC整合性確保"""
        try:
            corrected = data.copy()

            # High >= max(Open, Close), Low <= min(Open, Close)
            corrected["high"] = np.maximum(
                corrected["high"], np.maximum(corrected["open"], corrected["close"])
            )
            corrected["low"] = np.minimum(
                corrected["low"], np.minimum(corrected["open"], corrected["close"])
            )

            # High >= Low
            corrected["high"] = np.maximum(corrected["high"], corrected["low"])

            return corrected

        except Exception as e:
            logger.error(f"❌ OHLC consistency ensuring failed: {e}")
            return data

    def _smooth_outliers(
        self, data: pd.DataFrame, timeframe: str, threshold: float = 3.0
    ) -> pd.DataFrame:
        """外れ値のスムージング"""
        try:
            smoothed = data.copy()

            for col in ["open", "high", "low", "close"]:
                if col not in data.columns:
                    continue

                try:
                    # Phase H.16.2: numpy/pandas互換性修復・データ型安全性確保
                    col_data = data[col].dropna()

                    # 数値データの確認と変換
                    if len(col_data) == 0:
                        continue

                    # float64に明示的変換（numpy互換性確保）
                    col_data = pd.to_numeric(col_data, errors="coerce").astype(
                        np.float64
                    )

                    # NaN削除後の最終チェック
                    col_data = col_data.dropna()
                    if len(col_data) < 3:  # 最小データ要件
                        continue

                    # Z-score計算（型安全）
                    z_scores = np.abs(stats.zscore(col_data.values))
                    outliers_mask = z_scores > threshold

                    if np.any(outliers_mask):
                        # 外れ値インデックス取得
                        outlier_indices = col_data.index[outliers_mask]

                        # 移動平均で置換
                        window = 5 if timeframe in ["15m", "1h"] else 3
                        ma = data[col].rolling(window=window, center=True).mean()
                        smoothed.loc[outlier_indices, col] = ma.loc[outlier_indices]

                except Exception as e:
                    logger.debug(f"⚠️ Outlier smoothing failed for {col}: {e}")
                    continue

            return smoothed

        except Exception as e:
            logger.error(f"❌ Outlier smoothing failed: {e}")
            return data

    def get_synchronization_stats(self) -> Dict:
        """同期統計情報取得"""
        return {
            "sync_stats": self.sync_stats.copy(),
            "timeframes": self.timeframes,
            "base_timeframe": self.base_timeframe,
            "sync_tolerance_seconds": self.sync_tolerance.total_seconds(),
            "missing_data_threshold": self.missing_data_threshold,
            "consistency_check_enabled": self.consistency_check_enabled,
        }

    def reset_stats(self) -> None:
        """統計リセット"""
        self.sync_stats = {
            "sync_operations": 0,
            "alignment_corrections": 0,
            "missing_data_filled": 0,
            "consistency_violations": 0,
            "quality_improvements": 0,
        }
        logger.info("🔄 Synchronization stats reset")
