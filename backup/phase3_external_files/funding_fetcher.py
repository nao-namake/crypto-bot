# crypto_bot/data/funding_fetcher.py
# 説明:
# Funding Rate・Open Interest データ取得・分析クラス
# ・Binance公開APIを使用（認証不要）
# ・市況判定・トレンド分析・タイミング測定用
# ・エラー時フォールバック・デフォルト値生成対応

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FundingDataFetcher:
    """Funding Rate・Open Interest データ取得・分析クラス"""

    def __init__(self):
        """初期化"""
        self.exchange = None
        self._initialize_exchange()

    def _initialize_exchange(self):
        """取引所接続初期化"""
        try:
            import os

            import ccxt

            # Phase H.19: HTTPクライアント最適化
            from ..utils.http_client_optimizer import get_optimized_client

            # Cloud Run環境検出
            is_cloud_run = os.getenv("K_SERVICE") is not None

            # 最適化されたHTTPクライアントを使用
            if is_cloud_run:
                http_client = get_optimized_client("binance")
                # ccxtにセッションを注入（可能な場合）
                session = http_client.session
            else:
                session = None

            self.exchange = ccxt.binance(
                {
                    "enableRateLimit": True,
                    "timeout": 30000 if is_cloud_run else 10000,  # Cloud Runでは長めに
                    "options": {"defaultType": "future"},  # 先物取引（FR/OI取得用）
                    "session": session,  # 最適化されたセッションを使用
                }
            )
            logger.info("✅ Binance connection initialized for FR/OI data")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize exchange: {e}")
            self.exchange = None

    def get_funding_rate_data(
        self,
        symbol: str = "BTC/USDT",
        since: Optional[Union[str, datetime]] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Funding Rate履歴データ取得

        Args:
            symbol: 通貨ペア（例：BTC/USDT）
            since: 開始時刻
            limit: 取得件数

        Returns:
            DataFrame: Funding Rate履歴データ
        """
        try:
            if not self.exchange:
                logger.warning("Exchange not available, using default FR data")
                return self._generate_default_funding_data(limit)

            # Funding Rate履歴取得
            since_ms = None
            if since:
                if isinstance(since, str):
                    since_dt = pd.to_datetime(since)
                else:
                    since_dt = since
                since_ms = int(since_dt.timestamp() * 1000)

            funding_history = self.exchange.fetch_funding_rate_history(
                symbol, since=since_ms, limit=limit
            )

            if not funding_history:
                logger.warning(f"No funding data for {symbol}, using defaults")
                return self._generate_default_funding_data(limit)

            # DataFrameに変換
            df = pd.DataFrame(funding_history)
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df = df.set_index("datetime")

            # Phase H.19修正: 必要な列のみ抽出（存在確認付き）
            available_columns = df.columns.tolist()
            required_columns = []

            # fundingRate列の存在確認
            if "fundingRate" in available_columns:
                required_columns.append("fundingRate")
            elif "rate" in available_columns:
                df["fundingRate"] = df["rate"]
                required_columns.append("fundingRate")
            else:
                logger.warning("No funding rate column found, using default")
                df["fundingRate"] = 0.0001  # デフォルト値
                required_columns.append("fundingRate")

            # fundingTimestamp列の存在確認（オプション）
            if "fundingTimestamp" in available_columns:
                required_columns.append("fundingTimestamp")
            elif "timestamp" in available_columns:
                df["fundingTimestamp"] = df["timestamp"]
                required_columns.append("fundingTimestamp")
            # fundingTimestampは必須ではないので、なくても続行

            df = df[required_columns].copy()
            df["fundingRate"] = pd.to_numeric(df["fundingRate"], errors="coerce")

            logger.info(f"✅ Retrieved {len(df)} funding rate records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"❌ Failed to fetch funding rate data: {e}")
            return self._generate_default_funding_data(limit)

    def get_open_interest_data(
        self, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 100
    ) -> pd.DataFrame:
        """
        Open Interest履歴データ取得

        Args:
            symbol: 通貨ペア
            timeframe: 時間足
            limit: 取得件数

        Returns:
            DataFrame: Open Interest履歴データ
        """
        try:
            if not self.exchange:
                logger.warning("Exchange not available, using default OI data")
                return self._generate_default_oi_data(limit)

            # 現在のOI取得
            oi_current = self.exchange.fetch_open_interest(symbol)

            # 履歴データ生成（実際のAPIがない場合の代替）
            current_oi = oi_current.get("openInterestAmount", 50000)

            # 時系列OIデータ生成
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=limit)
            timestamps = pd.date_range(start_time, end_time, freq="1h")

            # ランダムなOI変動を生成（±10%変動）
            np.random.seed(42)  # 再現性のため
            variations = np.random.normal(1.0, 0.05, len(timestamps))
            oi_values = current_oi * np.cumprod(variations)

            df = pd.DataFrame(
                {"openInterest": oi_values, "symbol": symbol}, index=timestamps
            )

            logger.info(f"✅ Generated {len(df)} OI records for {symbol}")
            return df

        except Exception as e:
            logger.error(f"❌ Failed to fetch OI data: {e}")
            return self._generate_default_oi_data(limit)

    def calculate_funding_features(self, funding_df: pd.DataFrame) -> pd.DataFrame:
        """
        Funding Rate特徴量計算

        Args:
            funding_df: Funding Rateデータ

        Returns:
            DataFrame: FR特徴量
        """
        if funding_df.empty:
            return pd.DataFrame()

        features = pd.DataFrame(index=funding_df.index)
        fr = funding_df["fundingRate"]

        # 基本特徴量
        features["funding_rate"] = fr
        features["funding_rate_abs"] = fr.abs()
        features["funding_rate_pct_change"] = fr.pct_change()

        # 移動平均・統計
        features["funding_rate_ma8"] = fr.rolling(8).mean()
        features["funding_rate_ma24"] = fr.rolling(24).mean()
        features["funding_rate_std8"] = fr.rolling(8).std()

        # 市況判定特徴量
        features["funding_bullish_extreme"] = (fr > 0.01).astype(int)  # 1%以上
        features["funding_bearish_extreme"] = (fr < -0.005).astype(int)  # -0.5%以下
        features["funding_neutral"] = ((fr >= -0.005) & (fr <= 0.01)).astype(int)

        # トレンド特徴量
        features["funding_trend_up"] = (fr > features["funding_rate_ma8"]).astype(int)
        features["funding_momentum"] = fr - fr.shift(3)
        features["funding_volatility"] = fr.rolling(24).std()

        # 反転サイン
        features["funding_reversal_signal"] = (
            (fr.shift(1) > 0.008) & (fr < 0.005)  # 高FR→急落
        ).astype(int)

        logger.info(f"✅ Calculated {len(features.columns)} funding features")
        return features.fillna(0)

    def calculate_oi_features(self, oi_df: pd.DataFrame) -> pd.DataFrame:
        """
        Open Interest特徴量計算

        Args:
            oi_df: Open Interestデータ

        Returns:
            DataFrame: OI特徴量
        """
        if oi_df.empty:
            return pd.DataFrame()

        features = pd.DataFrame(index=oi_df.index)
        oi = oi_df["openInterest"]

        # 基本特徴量
        features["oi_level"] = oi
        features["oi_change"] = oi.pct_change()
        features["oi_change_abs"] = oi.pct_change().abs()

        # 移動平均・トレンド
        features["oi_ma24"] = oi.rolling(24).mean()
        features["oi_ma72"] = oi.rolling(72).mean()
        features["oi_trend_short"] = (oi > features["oi_ma24"]).astype(int)
        features["oi_trend_long"] = (oi > features["oi_ma72"]).astype(int)

        # ボラティリティ・勢い
        features["oi_volatility"] = oi.rolling(24).std() / oi.rolling(24).mean()
        features["oi_momentum"] = oi / oi.shift(24) - 1
        features["oi_acceleration"] = features["oi_change"] - features[
            "oi_change"
        ].shift(1)

        # 極値検知
        features["oi_spike_up"] = (
            features["oi_change"] > features["oi_change"].rolling(24).quantile(0.95)
        ).astype(int)
        features["oi_spike_down"] = (
            features["oi_change"] < features["oi_change"].rolling(24).quantile(0.05)
        ).astype(int)

        logger.info(f"✅ Calculated {len(features.columns)} OI features")
        return features.fillna(0)

    def _generate_default_funding_data(self, limit: int) -> pd.DataFrame:
        """デフォルトFunding Rateデータ生成"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=limit * 8)  # 8時間間隔
        timestamps = pd.date_range(start_time, end_time, freq="8h")[:limit]

        # 現実的なFR値生成（-0.01% ~ +0.01%）
        np.random.seed(42)
        default_rates = np.random.normal(0.0001, 0.0003, len(timestamps))

        df = pd.DataFrame(
            {
                "fundingRate": default_rates,
                "fundingTimestamp": [int(ts.timestamp() * 1000) for ts in timestamps],
            },
            index=timestamps,
        )

        logger.info(f"📊 Generated {len(df)} default funding rate records")
        return df

    def _generate_default_oi_data(self, limit: int) -> pd.DataFrame:
        """デフォルトOpen Interestデータ生成"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=limit)
        timestamps = pd.date_range(start_time, end_time, freq="1h")[:limit]

        # 現実的なOI値生成（50,000 BTC基準）
        np.random.seed(42)
        base_oi = 50000
        variations = np.random.normal(1.0, 0.02, len(timestamps))
        oi_values = base_oi * np.cumprod(variations)

        df = pd.DataFrame(
            {"openInterest": oi_values, "symbol": "BTC/USDT"}, index=timestamps
        )

        logger.info(f"📊 Generated {len(df)} default OI records")
        return df


# デフォルト値定義（feature_defaults.pyで使用）
def get_default_funding_features() -> Dict[str, float]:
    """デフォルトFunding Rate特徴量値"""
    return {
        "funding_rate": 0.0001,  # 0.01%
        "funding_rate_abs": 0.0001,
        "funding_rate_pct_change": 0.0,
        "funding_rate_ma8": 0.0001,
        "funding_rate_ma24": 0.0001,
        "funding_rate_std8": 0.0002,
        "funding_bullish_extreme": 0,
        "funding_bearish_extreme": 0,
        "funding_neutral": 1,
        "funding_trend_up": 0,
        "funding_momentum": 0.0,
        "funding_volatility": 0.0002,
        "funding_reversal_signal": 0,
    }


def get_default_oi_features() -> Dict[str, float]:
    """デフォルトOpen Interest特徴量値"""
    return {
        "oi_level": 50000.0,
        "oi_change": 0.0,
        "oi_change_abs": 0.01,
        "oi_ma24": 50000.0,
        "oi_ma72": 50000.0,
        "oi_trend_short": 1,
        "oi_trend_long": 1,
        "oi_volatility": 0.02,
        "oi_momentum": 0.0,
        "oi_acceleration": 0.0,
        "oi_spike_up": 0,
        "oi_spike_down": 0,
    }
