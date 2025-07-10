"""
外部データキャッシュシステム
バックテスト時の特徴量数一致を保証するために、全期間の外部データを事前にキャッシュ
"""

import logging
from typing import Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExternalDataCache:
    """
    バックテスト用外部データキャッシュ

    全期間の外部データ（VIX、DXY、Fear&Greed、Funding Rate）を事前取得し、
    ウォークフォワード各期間で該当データを高速抽出する
    """

    def __init__(self, start_date: str = "2024-01-01", end_date: str = "2024-12-31"):
        self.start_date = start_date
        self.end_date = end_date
        self.cache = {}
        self.is_initialized = False

    def initialize_cache(self):
        """全期間の外部データをキャッシュ"""
        try:
            logger.info(f"Initializing cache: {self.start_date} to {self.end_date}")

            # VIXデータキャッシュ
            self._cache_vix_data()

            # DXY・マクロデータキャッシュ
            self._cache_macro_data()

            # Fear&Greedデータキャッシュ
            self._cache_fear_greed_data()

            # Funding Rateデータキャッシュ
            self._cache_funding_data()

            self.is_initialized = True
            logger.info("External data cache initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize external data cache: {e}")
            self.is_initialized = False

    def _cache_vix_data(self):
        """VIXデータをキャッシュ"""
        try:
            from crypto_bot.data.vix_fetcher import VIXDataFetcher

            vix_fetcher = VIXDataFetcher()
            vix_data = vix_fetcher.get_vix_data(
                start_date=self.start_date, end_date=self.end_date, timeframe="1d"
            )

            if not vix_data.empty:
                vix_features = vix_fetcher.calculate_vix_features(vix_data)
                # 日次→時間足変換
                vix_hourly = vix_features.resample("1h").ffill()
                self.cache["vix"] = vix_hourly
                logger.info(f"Cached VIX data: {len(vix_hourly)} hourly records")
            else:
                self.cache["vix"] = pd.DataFrame()
                logger.warning("No VIX data available for caching")

        except Exception as e:
            logger.warning(f"Failed to cache VIX data: {e}")
            self.cache["vix"] = pd.DataFrame()

    def _cache_macro_data(self):
        """DXY・マクロデータをキャッシュ"""
        try:
            from crypto_bot.data.macro_fetcher import MacroDataFetcher

            macro_fetcher = MacroDataFetcher()
            start_dt = pd.to_datetime(self.start_date)
            end_dt = pd.to_datetime(self.end_date)

            macro_data = macro_fetcher.get_macro_data(start_dt, end_dt)

            if not macro_data.empty:
                macro_features = macro_fetcher.calculate_macro_features(macro_data)
                # 日次→時間足変換
                macro_hourly = macro_features.resample("1h").ffill()
                self.cache["macro"] = macro_hourly
                logger.info(f"Cached macro data: {len(macro_hourly)} hourly records")
            else:
                self.cache["macro"] = pd.DataFrame()
                logger.warning("No macro data available for caching")

        except Exception as e:
            logger.warning(f"Failed to cache macro data: {e}")
            self.cache["macro"] = pd.DataFrame()

    def _cache_fear_greed_data(self):
        """Fear&Greedデータをキャッシュ"""
        try:
            from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher

            fg_fetcher = FearGreedDataFetcher()
            fg_data = fg_fetcher.get_fear_greed_data(days_back=365)

            if not fg_data.empty:
                fg_features = fg_fetcher.calculate_fear_greed_features(fg_data)
                # 日次→時間足変換
                fg_hourly = fg_features.resample("1h").ffill()
                self.cache["fear_greed"] = fg_hourly
                logger.info(f"Cached Fear&Greed data: {len(fg_hourly)} hourly records")
            else:
                self.cache["fear_greed"] = pd.DataFrame()
                logger.warning("No Fear&Greed data available for caching")

        except Exception as e:
            logger.warning(f"Failed to cache Fear&Greed data: {e}")
            self.cache["fear_greed"] = pd.DataFrame()

    def _cache_funding_data(self):
        """Funding Rateデータをキャッシュ"""
        try:
            from crypto_bot.data.funding_fetcher import FundingDataFetcher

            funding_fetcher = FundingDataFetcher()
            funding_data = funding_fetcher.get_funding_rate_data(
                symbol="BTC/USDT", since=self.start_date, limit=8760  # 1年分
            )

            if not funding_data.empty:
                funding_features = funding_fetcher.calculate_funding_features(
                    funding_data
                )
                # 8時間足→時間足変換
                funding_hourly = funding_features.resample("1h").ffill()
                self.cache["funding"] = funding_hourly
                logger.info(
                    f"Cached funding data: {len(funding_hourly)} hourly records"
                )
            else:
                # デフォルト特徴量を生成
                from crypto_bot.data.funding_fetcher import (
                    get_available_funding_features,
                )

                funding_feature_names = get_available_funding_features()

                # 全期間の時間インデックス生成
                hourly_index = pd.date_range(
                    start=self.start_date, end=self.end_date, freq="1h", tz="UTC"
                )

                default_funding = pd.DataFrame(
                    index=hourly_index, columns=funding_feature_names
                ).fillna(0)

                self.cache["funding"] = default_funding
                logger.info(
                    f"Created default funding data: {len(default_funding)} items"
                )

        except Exception as e:
            logger.warning(f"Failed to cache funding data: {e}")
            # エラー時もデフォルト特徴量を生成
            try:
                from crypto_bot.data.funding_fetcher import (
                    get_available_funding_features,
                )

                funding_feature_names = get_available_funding_features()

                hourly_index = pd.date_range(
                    start=self.start_date, end=self.end_date, freq="1h", tz="UTC"
                )

                default_funding = pd.DataFrame(
                    index=hourly_index, columns=funding_feature_names
                ).fillna(0)

                self.cache["funding"] = default_funding
                logger.info(
                    f"Created default funding after error: {len(default_funding)} items"
                )
            except Exception as inner_e:
                logger.error(f"Failed to create default funding data: {inner_e}")
                self.cache["funding"] = pd.DataFrame()

    def get_period_data(
        self, data_type: str, start_time: pd.Timestamp, end_time: pd.Timestamp
    ) -> pd.DataFrame:
        """
        指定期間のデータを取得

        Parameters
        ----------
        data_type : str
            データタイプ ('vix', 'macro', 'fear_greed', 'funding')
        start_time : pd.Timestamp
            開始時刻
        end_time : pd.Timestamp
            終了時刻

        Returns
        -------
        pd.DataFrame
            指定期間のデータ
        """
        if not self.is_initialized:
            logger.warning("External data cache not initialized")
            return pd.DataFrame()

        if data_type not in self.cache:
            logger.warning(f"Data type {data_type} not found in cache")
            return pd.DataFrame()

        cached_data = self.cache[data_type]
        if cached_data.empty:
            return pd.DataFrame()

        # 期間抽出
        try:
            period_data = cached_data.loc[start_time:end_time]
            return period_data
        except Exception as e:
            logger.warning(f"Failed to extract period data for {data_type}: {e}")
            return pd.DataFrame()

    def get_cache_info(self) -> Dict[str, int]:
        """キャッシュ情報を取得"""
        info = {}
        for data_type, data in self.cache.items():
            info[data_type] = len(data) if not data.empty else 0
        return info


# グローバルキャッシュインスタンス
_global_cache: Optional[ExternalDataCache] = None


def get_global_cache() -> ExternalDataCache:
    """グローバルキャッシュインスタンスを取得"""
    global _global_cache
    if _global_cache is None:
        _global_cache = ExternalDataCache()
    return _global_cache


def initialize_global_cache(
    start_date: str = "2024-01-01", end_date: str = "2024-12-31"
):
    """グローバルキャッシュを初期化"""
    global _global_cache
    _global_cache = ExternalDataCache(start_date, end_date)
    _global_cache.initialize_cache()
    return _global_cache
