"""
OI Fetcher - Phase 16.3-C Split

統合前: crypto_bot/data/fetcher.py（1,456行）
分割後: crypto_bot/data/fetching/oi_fetcher.py

機能:
- OIDataFetcher: OI（未決済建玉）データ取得クラス
- 未決済建玉データ取得・特徴量計算
- Bitbank現物取引向けOI近似機能
- 特殊用途データ取得（使用頻度低）

Phase 16.3-C実装日: 2025年8月8日
"""

import logging
from datetime import datetime
from typing import Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class OIDataFetcher:
    """
    OI（未決済建玉）データ取得クラス

    - 未決済建玉データの取得・処理
    - 各種OI関連特徴量の計算
    - Bitbank現物取引対応（OI近似機能）
    - 特殊用途データ取得機能
    """

    def __init__(self, market_fetcher):
        """
        OIデータ取得クラス初期化

        Parameters
        ----------
        market_fetcher : MarketDataFetcher
            市場データ取得クライアント
        """
        self.market_fetcher = market_fetcher
        self.exchange = market_fetcher.exchange
        self.symbol = market_fetcher.symbol
        self.exchange_id = market_fetcher.exchange_id

    def get_oi_data(
        self,
        timeframe: str = "1h",
        since: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        OI（未決済建玉）データを取得

        Parameters
        ----------
        timeframe : str
            時間枠（"1h", "4h"等）
        since : Optional[Union[str, datetime]]
            開始時刻
        limit : Optional[int]
            取得件数制限

        Returns
        -------
        pd.DataFrame
            OIデータ（index: datetime, columns: oi_amount, oi_value）
        """
        try:
            # Bitbankの場合のOI取得（現物・信用取引対応）
            if self.exchange_id == "bitbank":
                logger.info("Generating OI approximation for Bitbank")
                return self._generate_bitbank_oi_approximation(timeframe, since, limit)

            # その他の取引所の場合（将来の拡張用）
            else:
                logger.warning(
                    f"OI data not supported for exchange: {self.exchange_id}"
                )
                return self._create_empty_oi_dataframe()

        except Exception as e:
            logger.warning(f"Could not fetch OI data: {e}")
            return self._create_empty_oi_dataframe()

    def _generate_bitbank_oi_approximation(
        self,
        timeframe: str,
        since: Optional[Union[str, datetime]],
        limit: Optional[int],
    ) -> pd.DataFrame:
        """
        Bitbank向けOI近似データ生成

        現物取引にはOIが存在しないため、取引量×価格でポジション規模を推定
        """
        try:
            # 価格データを取得してOI近似値を計算
            from .data_processor import DataProcessor

            processor = DataProcessor(self.market_fetcher)
            price_data = processor.get_price_df(
                timeframe=timeframe, since=since, limit=limit
            )

            if price_data.empty:
                logger.warning("No price data available for OI approximation")
                return self._create_empty_oi_dataframe()

            logger.info(
                f"Generating OI approximation from {len(price_data)} price records"
            )

            result = pd.DataFrame(index=price_data.index)

            # OI近似計算: 取引量ベースのポジション推定
            volume_ma = price_data["volume"].rolling(window=24, min_periods=1).mean()
            volatility = (
                price_data["close"].pct_change().rolling(window=24, min_periods=1).std()
            )

            # ポジションサイズ推定（経験的な計算式）
            # 取引量が多く、ボラティリティが高いほど大きなポジションが推定される
            position_size = volume_ma * (1 + volatility * 10)
            position_size = position_size.fillna(0)

            # OI近似値を設定
            result["oi_amount"] = position_size
            result["oi_value"] = position_size * price_data["close"]

            logger.info(f"Generated OI approximation: {len(result)} records")
            return result

        except Exception as e:
            logger.error(f"Failed to generate Bitbank OI approximation: {e}")
            return self._create_empty_oi_dataframe()

    def _create_empty_oi_dataframe(self) -> pd.DataFrame:
        """空のOIDataFrameを作成"""
        return pd.DataFrame(columns=["oi_amount", "oi_value"])

    def calculate_oi_features(self, df: pd.DataFrame, window: int = 24) -> pd.DataFrame:
        """
        OI関連の特徴量を計算

        Parameters
        ----------
        df : pd.DataFrame
            OIデータ（oi_amount, oi_value列を含む）
        window : int
            移動平均の期間（デフォルト24）

        Returns
        -------
        pd.DataFrame
            OI特徴量付きDataFrame
        """
        if df.empty or "oi_amount" not in df.columns:
            logger.warning("No valid OI data for feature calculation")
            return df

        try:
            logger.info(f"Calculating OI features with window={window}")
            result_df = df.copy()

            # 1. OI変化率
            result_df["oi_pct_change"] = result_df["oi_amount"].pct_change()

            # 2. OI移動平均
            result_df[f"oi_ma_{window}"] = (
                result_df["oi_amount"].rolling(window=window, min_periods=1).mean()
            )

            # 3. OI標準化（Z-score）
            oi_rolling_mean = (
                result_df["oi_amount"].rolling(window=window, min_periods=1).mean()
            )
            oi_rolling_std = (
                result_df["oi_amount"].rolling(window=window, min_periods=1).std()
            )

            result_df["oi_zscore"] = (
                (result_df["oi_amount"] - oi_rolling_mean)
                / (oi_rolling_std + 1e-8)  # ゼロ除算防止
            ).fillna(0)

            # 4. OI勢い（momentum）
            result_df["oi_momentum"] = (
                result_df["oi_amount"] / result_df["oi_amount"].shift(window) - 1
            ).fillna(0)

            # 5. OI急激な変化検知（スパイク検出）
            oi_pct_rolling_std = (
                result_df["oi_pct_change"].rolling(window=window, min_periods=1).std()
            )
            spike_threshold = oi_pct_rolling_std * 2  # 2シグマを閾値とする

            result_df["oi_spike"] = (
                result_df["oi_pct_change"].abs() > spike_threshold
            ).astype(int)

            # 6. OIトレンド（上昇・下降・横ばい）
            oi_trend_signal = result_df[f"oi_ma_{window}"].diff()
            result_df["oi_trend"] = (
                pd.cut(
                    oi_trend_signal,
                    bins=[-float("inf"), -0.001, 0.001, float("inf")],
                    labels=[-1, 0, 1],  # -1:下降, 0:横ばい, 1:上昇
                )
                .astype(float)
                .fillna(0)
            )

            # 7. OI相対強度（現在値 / 期間最大値）
            oi_rolling_max = (
                result_df["oi_amount"].rolling(window=window, min_periods=1).max()
            )
            result_df["oi_relative_strength"] = (
                (result_df["oi_amount"] / (oi_rolling_max + 1e-8))  # ゼロ除算防止
                .fillna(0)
                .clip(0, 1)
            )

            # NaN値の最終処理
            numeric_columns = [
                "oi_pct_change",
                f"oi_ma_{window}",
                "oi_zscore",
                "oi_momentum",
                "oi_spike",
                "oi_trend",
                "oi_relative_strength",
            ]

            for col in numeric_columns:
                if col in result_df.columns:
                    result_df[col] = result_df[col].fillna(0)

            logger.info(f"Successfully calculated {len(numeric_columns)} OI features")
            return result_df

        except Exception as e:
            logger.error(f"Failed to calculate OI features: {e}")
            return df  # エラー時は元のDataFrameを返す
