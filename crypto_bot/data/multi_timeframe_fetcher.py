# =============================================================================
# ファイル名: crypto_bot/data/multi_timeframe_fetcher.py
# 説明:
# マルチタイムフレーム対応データフェッチャー
# ・複数タイムフレーム（15m/1h/4h）の効率的な取得・変換
# ・1時間足ベースデータから他タイムフレームへの補間・集約
# ・データ同期・品質管理・キャッシュ機能統合
# ・Phase 2.1: マルチタイムフレーム基盤実装
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd
from scipy import interpolate

from .fetcher import MarketDataFetcher
from .timeframe_synchronizer import TimeframeSynchronizer

logger = logging.getLogger(__name__)


class MultiTimeframeDataFetcher:
    """マルチタイムフレーム対応データフェッチャー"""

    def __init__(
        self,
        base_fetcher: MarketDataFetcher = None,
        config: dict = None,
        timeframes: List[str] = None,
        base_timeframe: str = "1h",
        cache_enabled: bool = True,
        data_quality_threshold: float = 0.9,
        synchronization_enabled: bool = True,
        sync_tolerance_minutes: int = 1,
    ):
        """
        初期化

        Args:
            base_fetcher: ベースとなるMarketDataFetcher
            config: 設定辞書（base_fetcherがNoneの場合使用）
            timeframes: 対象タイムフレーム（例: ["15m", "1h", "4h"]）
            base_timeframe: ベースタイムフレーム（データ取得用）
            cache_enabled: キャッシュ有効化
            data_quality_threshold: データ品質閾値
            synchronization_enabled: 同期機能有効化
            sync_tolerance_minutes: 同期許容誤差（分）
        """
        # configからの設定読み取り（Phase H.2.2: 4h復活対応）
        if config and "multi_timeframe" in config:
            mtf_config = config["multi_timeframe"]
            timeframes = timeframes or mtf_config.get("timeframes", ["15m", "1h", "4h"])
            synchronization_enabled = mtf_config.get(
                "data_sync_enabled", synchronization_enabled
            )
            # データ品質閾値も設定から読み取る
            data_quality_threshold = mtf_config.get(
                "data_quality_threshold", data_quality_threshold
            )
            
        # multi_timeframe_data設定も読み取り（Phase H.2.2: target_timeframes対応）
        if config and "data" in config and "multi_timeframe_data" in config["data"]:
            mtf_data_config = config["data"]["multi_timeframe_data"]
            # base_timeframeの確認
            config_base_timeframe = mtf_data_config.get("base_timeframe", "1h")
            if config_base_timeframe != base_timeframe:
                logger.info(f"Using config base_timeframe: {config_base_timeframe}")
                base_timeframe = config_base_timeframe
            
            # target_timeframesがある場合はそれを使用
            target_timeframes_config = mtf_data_config.get("target_timeframes", {})
            if target_timeframes_config:
                # 設定されたタイムフレームのみを使用
                configured_timeframes = list(target_timeframes_config.keys())
                if configured_timeframes:
                    timeframes = configured_timeframes
                    logger.info(f"Using configured target timeframes: {timeframes}")

        self.base_fetcher = base_fetcher
        self.config = config
        self.timeframes = timeframes or ["15m", "1h", "4h"]
        self.base_timeframe = base_timeframe
        self.cache_enabled = cache_enabled
        self.data_quality_threshold = data_quality_threshold
        self.synchronization_enabled = synchronization_enabled

        # TimeframeSynchronizer初期化（エラーハンドリング強化）
        if self.synchronization_enabled:
            try:
                self.synchronizer = TimeframeSynchronizer(
                    timeframes=self.timeframes,
                    base_timeframe=self.base_timeframe,
                    sync_tolerance=timedelta(minutes=sync_tolerance_minutes),
                    missing_data_threshold=min(1.0 - self.data_quality_threshold, 0.5),
                    consistency_check_enabled=True,
                )
                logger.info(
                    f"  - Synchronizer initialized: {self.synchronizer is not None}"
                )
            except Exception as e:
                logger.warning(f"⚠️ TimeframeSynchronizer initialization failed: {e}")
                logger.info("  - Falling back to basic synchronizer")
                self.synchronizer = TimeframeSynchronizer()
        else:
            self.synchronizer = None

        # データキャッシュ
        self.data_cache: Dict[str, pd.DataFrame] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_ttl = timedelta(minutes=5)  # 5分間キャッシュ

        # データ品質統計
        self.quality_stats = {
            "fetch_count": 0,
            "cache_hits": 0,
            "interpolation_count": 0,
            "aggregation_count": 0,
            "quality_failures": 0,
            "synchronization_count": 0,
        }

        logger.info("🔄 MultiTimeframeDataFetcher initialized")
        logger.info(f"  - Timeframes: {self.timeframes}")
        logger.info(f"  - Base timeframe: {self.base_timeframe}")
        logger.info(f"  - Cache enabled: {self.cache_enabled}")
        logger.info(f"  - Data quality threshold: {self.data_quality_threshold}")
        logger.info(f"  - Synchronization enabled: {self.synchronization_enabled}")

    def get_multi_timeframe_data(
        self,
        since: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
        force_refresh: bool = False,
    ) -> Dict[str, pd.DataFrame]:
        """
        複数タイムフレームのデータを同時取得

        Args:
            since: 開始時刻
            limit: 取得件数
            force_refresh: キャッシュ強制更新

        Returns:
            Dict[timeframe, DataFrame]: タイムフレーム別データ
        """
        try:
            logger.info(f"🔄 Fetching multi-timeframe data: {self.timeframes}")
            self.quality_stats["fetch_count"] += 1

            # ベースデータ取得
            base_data = self._get_base_data(since, limit, force_refresh)
            if base_data.empty:
                logger.error("❌ Failed to fetch base data")
                return {}

            # 各タイムフレーム変換
            multi_data = {}
            for timeframe in self.timeframes:
                try:
                    data = self._convert_to_timeframe(base_data, timeframe)
                    if not data.empty:
                        quality_score = self._assess_data_quality(data, timeframe)
                        if quality_score >= self.data_quality_threshold:
                            multi_data[timeframe] = data
                            logger.info(
                                f"✅ {timeframe}: {len(data)} records "
                                f"(quality: {quality_score:.3f})"
                            )
                        else:
                            logger.warning(
                                f"⚠️ {timeframe}: Quality too low "
                                f"({quality_score:.3f} < {self.data_quality_threshold})"
                            )
                            self.quality_stats["quality_failures"] += 1
                    else:
                        logger.warning(f"⚠️ {timeframe}: No data after conversion")

                except Exception as e:
                    logger.error(f"❌ Failed to convert to {timeframe}: {e}")
                    continue

            # Phase 2.2: データ同期・統合システム適用
            if self.synchronization_enabled and self.synchronizer and multi_data:
                logger.info("🔄 Applying timeframe synchronization")
                synchronized_data = self.synchronizer.synchronize_multi_timeframe_data(
                    multi_data
                )
                self.quality_stats["synchronization_count"] += 1

                logger.info(
                    f"✅ Multi-timeframe fetch + synchronization complete: "
                    f"{len(synchronized_data)} timeframes"
                )
                return synchronized_data
            else:
                logger.info(
                    f"✅ Multi-timeframe fetch complete: {len(multi_data)} timeframes"
                )
                return multi_data

        except Exception as e:
            logger.error(f"❌ Multi-timeframe data fetch failed: {e}")
            return {}

    def _get_base_data(
        self,
        since: Optional[Union[str, datetime]],
        limit: Optional[int],
        force_refresh: bool,
    ) -> pd.DataFrame:
        """ベースタイムフレームデータ取得（キャッシュ対応・テスト用ダミーデータ対応）"""
        cache_key = f"{self.base_timeframe}_base"
        current_time = datetime.now()

        # キャッシュチェック
        if (
            not force_refresh
            and self.cache_enabled
            and cache_key in self.data_cache
            and cache_key in self.cache_timestamps
            and current_time - self.cache_timestamps[cache_key] < self.cache_ttl
        ):
            logger.info(f"📋 Using cached base data: {self.base_timeframe}")
            self.quality_stats["cache_hits"] += 1
            return self.data_cache[cache_key]

        # base_fetcherがNoneの場合（テスト用）
        if self.base_fetcher is None:
            logger.info(
                f"🧪 Generating test data for {self.base_timeframe} (no base_fetcher)"
            )
            data = self._generate_test_data(limit or 100)

            if not data.empty:
                # キャッシュ更新
                if self.cache_enabled:
                    self.data_cache[cache_key] = data
                    self.cache_timestamps[cache_key] = current_time
                logger.info(f"✅ Test base data generated: {len(data)} records")
                return data
            else:
                logger.error("❌ Failed to generate test data")
                return pd.DataFrame()

        # 新規データ取得
        try:
            logger.info(f"🔄 Fetching base data: {self.base_timeframe}")
            data = self.base_fetcher.get_price_df(
                timeframe=self.base_timeframe,
                since=since,
                limit=limit,
                paginate=True,
            )

            if not data.empty:
                # データ前処理
                data = self._preprocess_data(data)

                # キャッシュ更新
                if self.cache_enabled:
                    self.data_cache[cache_key] = data
                    self.cache_timestamps[cache_key] = current_time

                logger.info(f"✅ Base data fetched: {len(data)} records")
                return data
            else:
                logger.error("❌ No base data received")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ Base data fetch failed: {e}")
            return pd.DataFrame()

    def _convert_to_timeframe(
        self, base_data: pd.DataFrame, target_timeframe: str
    ) -> pd.DataFrame:
        """タイムフレーム変換（Phase H.2.2: 設定ベース強化・4h復活対応）"""
        if target_timeframe == self.base_timeframe:
            return base_data.copy()

        try:
            # 設定ファイルから変換方法を取得
            conversion_method = self._get_conversion_method(target_timeframe)
            
            logger.debug(f"Converting {self.base_timeframe} → {target_timeframe} using method: {conversion_method}")

            if conversion_method == "interpolation" and target_timeframe == "15m":
                return self._interpolate_to_15m(base_data)
            elif conversion_method == "aggregation" and target_timeframe == "4h":
                return self._aggregate_to_4h(base_data)
            elif conversion_method == "direct":
                return base_data.copy()
            else:
                # フォールバック: 従来の方式
                if target_timeframe == "15m" and self.base_timeframe == "1h":
                    return self._interpolate_to_15m(base_data)
                elif target_timeframe == "4h" and self.base_timeframe == "1h":
                    return self._aggregate_to_4h(base_data)
                else:
                    logger.warning(
                        f"⚠️ Unsupported conversion: "
                        f"{self.base_timeframe} → {target_timeframe}"
                    )
                    return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ Timeframe conversion failed: {e}")
            return pd.DataFrame()
    
    def _get_conversion_method(self, target_timeframe: str) -> str:
        """設定から変換方法を取得（Phase H.2.2）"""
        try:
            if (self.config and 
                "data" in self.config and 
                "multi_timeframe_data" in self.config["data"]):
                
                target_config = self.config["data"]["multi_timeframe_data"].get("target_timeframes", {})
                tf_config = target_config.get(target_timeframe, {})
                method = tf_config.get("method", "auto")
                
                if method != "auto":
                    return method
            
            # デフォルト方式
            if target_timeframe == "15m":
                return "interpolation"
            elif target_timeframe == "4h":
                return "aggregation"
            else:
                return "direct"
                
        except Exception as e:
            logger.warning(f"Failed to get conversion method for {target_timeframe}: {e}")
            return "auto"

    def _interpolate_to_15m(self, hourly_data: pd.DataFrame) -> pd.DataFrame:
        """1時間足→15分足補間"""
        try:
            logger.debug("🔄 Interpolating 1h → 15m")
            self.quality_stats["interpolation_count"] += 1

            if hourly_data.empty or len(hourly_data) < 2:
                return pd.DataFrame()

            # 15分間隔のタイムインデックス作成
            start_time = hourly_data.index[0]
            end_time = hourly_data.index[-1]
            minute_15_index = pd.date_range(start=start_time, end=end_time, freq="15T")

            interpolated_data = pd.DataFrame(index=minute_15_index)

            # 各列を補間
            for col in ["open", "high", "low", "close", "volume"]:
                if col in hourly_data.columns:
                    if col == "volume":
                        # ボリュームは線形分割
                        interpolated_data[col] = (
                            hourly_data[col].reindex(minute_15_index, method="ffill")
                            / 4.0
                        )
                    elif col in ["high", "low"]:
                        # 高値・安値は特別処理
                        interpolated_data[col] = self._interpolate_high_low(
                            hourly_data, col, minute_15_index
                        )
                    else:
                        # 価格データはスプライン補間
                        if len(hourly_data) >= 4:
                            f = interpolate.interp1d(
                                hourly_data.index.astype(np.int64),
                                hourly_data[col].values,
                                kind="cubic",
                                bounds_error=False,
                                fill_value="extrapolate",
                            )
                            interpolated_data[col] = f(minute_15_index.astype(np.int64))
                        else:
                            # データ不足時は線形補間
                            interpolated_data[col] = (
                                hourly_data[col]
                                .reindex(minute_15_index)
                                .interpolate(method="linear")
                            )

            # データ品質改善
            interpolated_data = self._improve_interpolated_data(interpolated_data)

            logger.debug(f"✅ 15m interpolation: {len(interpolated_data)} records")
            return interpolated_data

        except Exception as e:
            logger.error(f"❌ 15m interpolation failed: {e}")
            return pd.DataFrame()

    def _interpolate_high_low(
        self, hourly_data: pd.DataFrame, col: str, target_index: pd.DatetimeIndex
    ) -> pd.Series:
        """高値・安値の特別補間処理"""
        try:
            # 基本補間
            base_series = (
                hourly_data[col].reindex(target_index).interpolate(method="linear")
            )

            # 高値・安値の現実性調整
            close_series = (
                hourly_data["close"].reindex(target_index).interpolate(method="linear")
            )

            if col == "high":
                # 高値は終値より低くならないよう調整
                return np.maximum(base_series, close_series * 1.001)
            else:  # low
                # 安値は終値より高くならないよう調整
                return np.minimum(base_series, close_series * 0.999)

        except Exception:
            # エラー時は基本補間
            return hourly_data[col].reindex(target_index).interpolate(method="linear")

    def _aggregate_to_4h(self, hourly_data: pd.DataFrame) -> pd.DataFrame:
        """1時間足→4時間足集約"""
        try:
            logger.debug("🔄 Aggregating 1h → 4h")
            self.quality_stats["aggregation_count"] += 1

            if hourly_data.empty:
                return pd.DataFrame()

            # 4時間単位でリサンプリング
            aggregated = hourly_data.resample("4h").agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )

            # 欠損データ除去
            aggregated = aggregated.dropna()

            logger.debug(f"✅ 4h aggregation: {len(aggregated)} records")
            return aggregated

        except Exception as e:
            logger.error(f"❌ 4h aggregation failed: {e}")
            return pd.DataFrame()

    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """データ前処理"""
        try:
            # インデックスがDatetimeでない場合は変換
            if not isinstance(data.index, pd.DatetimeIndex):
                if "timestamp" in data.columns:
                    data["timestamp"] = pd.to_datetime(data["timestamp"])
                    data = data.set_index("timestamp")
                elif "datetime" in data.columns:
                    data["datetime"] = pd.to_datetime(data["datetime"])
                    data = data.set_index("datetime")

            # 重複削除
            data = data[~data.index.duplicated(keep="last")]

            # ソート
            data = data.sort_index()

            # 基本的な外れ値除去（価格の異常値）
            for col in ["open", "high", "low", "close"]:
                if col in data.columns:
                    # 前日比±50%を超える変化を異常値として除去
                    pct_change = data[col].pct_change().abs()
                    outliers = pct_change > 0.5
                    if outliers.any():
                        logger.warning(
                            f"⚠️ Removed {outliers.sum()} outliers from {col}"
                        )
                        data.loc[outliers, col] = np.nan
                        data[col] = data[col].interpolate(method="linear")

            return data

        except Exception as e:
            logger.error(f"❌ Data preprocessing failed: {e}")
            return data

    def _improve_interpolated_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """補間データの品質改善"""
        try:
            # OHLC関係の整合性確保
            if all(col in data.columns for col in ["open", "high", "low", "close"]):
                # High >= max(Open, Close), Low <= min(Open, Close)
                data["high"] = np.maximum(
                    data["high"], np.maximum(data["open"], data["close"])
                )
                data["low"] = np.minimum(
                    data["low"], np.minimum(data["open"], data["close"])
                )

            # ボリュームの負値除去
            if "volume" in data.columns:
                data["volume"] = np.maximum(data["volume"], 0)

            return data

        except Exception as e:
            logger.error(f"❌ Data improvement failed: {e}")
            return data

    def _assess_data_quality(self, data: pd.DataFrame, timeframe: str) -> float:
        """データ品質評価"""
        if data.empty:
            return 0.0

        try:
            quality_factors = []

            # 1. データ完全性（欠損率）
            total_cells = len(data) * len(data.columns)
            missing_cells = data.isnull().sum().sum()
            completeness = 1.0 - (missing_cells / total_cells)
            quality_factors.append(completeness * 0.3)

            # 2. データ量充足性
            min_required = {"15m": 50, "1h": 100, "4h": 25}
            min_req = min_required.get(timeframe, 50)
            data_sufficiency = min(len(data) / min_req, 1.0)
            quality_factors.append(data_sufficiency * 0.3)

            # 3. OHLC整合性
            if all(col in data.columns for col in ["open", "high", "low", "close"]):
                ohlc_valid = (
                    (data["high"] >= data["open"])
                    & (data["high"] >= data["close"])
                    & (data["low"] <= data["open"])
                    & (data["low"] <= data["close"])
                    & (data["high"] >= data["low"])
                ).mean()
                quality_factors.append(ohlc_valid * 0.2)

            # 4. 価格変動の妥当性
            if "close" in data.columns and len(data) > 1:
                price_changes = data["close"].pct_change().abs()
                reasonable_changes = (price_changes <= 0.1).mean()  # 10%以下の変化率
                quality_factors.append(reasonable_changes * 0.2)

            overall_quality = sum(quality_factors)
            return min(1.0, max(0.0, overall_quality))

        except Exception as e:
            logger.error(f"❌ Quality assessment failed: {e}")
            return 0.5

    def get_cache_info(self) -> Dict:
        """キャッシュ・統計情報取得"""
        info = {
            "cache_enabled": self.cache_enabled,
            "cached_timeframes": list(self.data_cache.keys()),
            "cache_timestamps": {
                tf: ts.isoformat() for tf, ts in self.cache_timestamps.items()
            },
            "quality_stats": self.quality_stats.copy(),
            "synchronization_enabled": self.synchronization_enabled,
        }

        # 同期統計情報追加
        if self.synchronizer:
            info["synchronization_stats"] = (
                self.synchronizer.get_synchronization_stats()
            )

        return info

    def clear_cache(self, timeframe: Optional[str] = None) -> None:
        """キャッシュクリア"""
        if timeframe:
            self.data_cache.pop(timeframe, None)
            self.cache_timestamps.pop(timeframe, None)
            logger.info(f"🗑️ Cleared cache for {timeframe}")
        else:
            self.data_cache.clear()
            self.cache_timestamps.clear()
            logger.info("🗑️ Cleared all cache")

    def _generate_test_data(self, n_records: int = 100) -> pd.DataFrame:
        """テスト用ダミーデータ生成"""
        try:
            import random
            from datetime import timedelta

            # 時系列インデックス生成
            end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
            timestamps = [end_time - timedelta(hours=i) for i in range(n_records)]
            timestamps.reverse()

            # ランダムなOHLCVデータ生成
            base_price = 5000000  # BTC/JPY想定
            ohlcv_data = []

            for _ts in timestamps:
                # 価格変動生成
                price_change = random.gauss(0, 0.01) * 0.02
                base_price *= 1 + price_change

                # OHLC生成
                volatility = abs(random.gauss(0.005, 0.002))
                high = base_price * (1 + volatility)
                low = base_price * (1 - volatility)
                open_price = base_price + random.gauss(0, volatility * 0.5) * base_price
                close_price = base_price
                volume = abs(random.gauss(50, 20))

                ohlcv_data.append(
                    {
                        "open": open_price,
                        "high": high,
                        "low": low,
                        "close": close_price,
                        "volume": volume,
                    }
                )

            df = pd.DataFrame(ohlcv_data, index=timestamps)
            logger.info(f"🧪 Generated test data: {len(df)} records")
            return df

        except Exception as e:
            logger.error(f"❌ Test data generation failed: {e}")
            return pd.DataFrame()

    def get_data_for_timeframe(
        self,
        timeframe: str,
        since: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        """単一タイムフレームデータ取得"""
        multi_data = self.get_multi_timeframe_data(since, limit, force_refresh)
        return multi_data.get(timeframe, pd.DataFrame())
