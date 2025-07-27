"""
VIX恐怖指数データフェッチャー
複数データソース・キャッシュ機能・品質閾値管理対応
ChatGPTアドバイス反映版：段階的・品質重視アプローチ
MultiSourceDataFetcher継承版 - Phase2統合実装
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from ..utils.api_retry import api_retry
from .multi_source_fetcher import MultiSourceDataFetcher

logger = logging.getLogger(__name__)


class VIXDataFetcher(MultiSourceDataFetcher):
    """VIX恐怖指数データ取得クラス（複数データソース・キャッシュ対応）"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        # 親クラス初期化
        super().__init__(config, data_type="vix")

        self.symbol = "^VIX"  # Yahoo Finance VIXシンボル

        logger.info("🔧 VIX Fetcher initialized with MultiSourceDataFetcher base")

    def _validate_data_quality(self, data: pd.DataFrame) -> float:
        """データ品質検証（MultiSourceDataFetcher抽象メソッド実装）"""
        if data is None or data.empty:
            return 0.0

        # 品質評価指標
        total_points = len(data)
        valid_points = len(data.dropna())

        if total_points == 0:
            return 0.0

        # VIX特有の品質検証
        vix_quality_score = 0.0
        if "vix_close" in data.columns:
            # VIX値が妥当な範囲内かチェック（通常5-80範囲）
            valid_vix_range = (
                (data["vix_close"] >= 5) & (data["vix_close"] <= 80)
            ).sum()
            vix_quality_score = valid_vix_range / total_points

        # 総合品質スコア
        quality_score = (valid_points / total_points) * 0.7 + vix_quality_score * 0.3
        logger.debug(
            "📊 VIX data quality: %.3f (valid: %d/%d, vix_range: %.3f)",
            quality_score,
            valid_points,
            total_points,
            vix_quality_score,
        )

        return quality_score

    def get_vix_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        timeframe: str = "1d",
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        VIXデータ取得（MultiSourceDataFetcher統合版）

        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            VIXデータのDataFrame
        """
        # デフォルト期間設定（過去1年間）
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        # 親クラスのget_dataメソッドを呼び出し
        return self.get_data(
            start_date=start_date, end_date=end_date, timeframe=timeframe
        )

    def _fetch_data_from_source(
        self, source_name: str, **kwargs
    ) -> Optional[pd.DataFrame]:
        """特定データソースからデータ取得（MultiSourceDataFetcher抽象メソッド実装）"""
        start_date = kwargs.get(
            "start_date", (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        )
        end_date = kwargs.get("end_date", datetime.now().strftime("%Y-%m-%d"))

        if source_name == "yahoo":
            return self._fetch_yahoo_vix(start_date, end_date)
        elif source_name == "alpha_vantage":
            return self._fetch_alpha_vantage_vix(start_date, end_date)
        else:
            logger.warning(f"Unknown VIX data source: {source_name}")
            return None

    def _generate_fallback_data(self, **kwargs) -> Optional[pd.DataFrame]:
        """フォールバックデータ生成（MultiSourceDataFetcher抽象メソッド実装）"""
        try:
            # VIX デフォルト値（通常市場レベル）
            start_date = kwargs.get(
                "start_date", (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            )
            end_date = kwargs.get("end_date", datetime.now().strftime("%Y-%m-%d"))

            # 過去30日分のデフォルトVIXデータを生成
            dates = pd.date_range(start=start_date, end=end_date, freq="D")

            # 市場通常時のVIX値（15-25範囲の軽微な変動）
            np.random.seed(42)  # 再現性のため
            base_vix = 20.0
            vix_values = []

            for _ in range(len(dates)):
                # 前日比±5%程度の変動
                variation = base_vix * 0.05 * (0.5 - np.random.random())
                vix_value = base_vix + variation
                # 10-35の範囲に制限
                vix_value = max(10, min(35, vix_value))
                vix_values.append(vix_value)
                base_vix = vix_value

            fallback_data = pd.DataFrame({"vix_close": vix_values}, index=dates)

            logger.info("📈 Generated VIX fallback data: %d days", len(fallback_data))
            return fallback_data

        except Exception as e:
            logger.error(f"❌ Failed to generate VIX fallback data: {e}")
            return None

    @api_retry(max_retries=3, base_delay=2.0, circuit_breaker=True)
    def _fetch_yahoo_vix(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """Yahoo FinanceからVIXデータ取得（Cloud Run対応）"""
        try:
            # Phase H.17: Cloud Run環境でのプロキシ設定
            import os

            # Cloud Run環境検出
            is_cloud_run = os.getenv("K_SERVICE") is not None

            if is_cloud_run:
                logger.info(
                    "🌐 Cloud Run environment detected, using optimized settings"
                )
                # Cloud Run用の設定（タイムアウト延長）
                yf.set_tz_cache_location("/tmp")  # Cloud Run用一時ディレクトリ

            vix_ticker = yf.Ticker(self.symbol)

            # Phase H.17: 複数の方法でデータ取得を試みる
            vix_data = None

            # 方法1: history()メソッド
            try:
                vix_data = vix_ticker.history(start=start_date, end=end_date)
                if not vix_data.empty:
                    logger.info(
                        f"✅ VIX data fetched via history(): {len(vix_data)} records"
                    )
            except Exception as e:
                logger.warning(f"⚠️ history() method failed: {e}")

            # 方法2: download()関数を直接使用
            if vix_data is None or vix_data.empty:
                try:
                    vix_data = yf.download(
                        self.symbol,
                        start=start_date,
                        end=end_date,
                        progress=False,
                        timeout=30,  # タイムアウト延長
                    )
                    if not vix_data.empty:
                        logger.info(
                            f"✅ VIX data fetched via download(): {len(vix_data)} records"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ download() method failed: {e}")

            if vix_data is None or vix_data.empty:
                raise ValueError("Yahoo VIX data is empty after all attempts")

            # カラム名を統一
            vix_data.columns = vix_data.columns.str.lower()
            vix_data = vix_data.rename(columns={"close": "vix_close"})

            return vix_data

        except Exception as e:
            logger.error(f"Yahoo Finance VIX fetch failed: {e}")
            logger.error(
                f"Environment: Cloud Run={is_cloud_run if 'is_cloud_run' in locals() else 'Unknown'}"
            )
            raise

    @api_retry(max_retries=3, base_delay=2.0, circuit_breaker=True)
    def _fetch_alpha_vantage_vix(
        self, start_date: str, end_date: str
    ) -> Optional[pd.DataFrame]:
        """Alpha VantageからVIXデータ取得（代替実装）"""
        try:
            # Alpha Vantage API実装（簡略版）
            # 実際の実装では、Alpha Vantage APIキーが必要
            # 現在は Yahoo Finance の代替として SPY のボラティリティを使用
            logger.info(
                "📡 Using SPY volatility as VIX alternative (Alpha Vantage placeholder)"
            )

            spy_ticker = yf.Ticker("SPY")
            spy_data = spy_ticker.history(start=start_date, end=end_date)

            if spy_data.empty:
                raise ValueError("SPY data is empty")

            # SPY のボラティリティからVIX近似値を計算
            spy_returns = spy_data["Close"].pct_change().dropna()
            rolling_vol = spy_returns.rolling(window=20).std() * (252**0.5) * 100

            # VIX形式のDataFrameを作成
            vix_data = pd.DataFrame(index=spy_data.index)
            vix_data["vix_close"] = rolling_vol * 0.8 + 15  # VIX近似値（簡略計算）

            # 欠損値処理
            vix_data = vix_data.dropna()

            if vix_data.empty:
                raise ValueError("Alpha Vantage VIX approximation failed")

            return vix_data

        except Exception as e:
            logger.error(f"Alpha Vantage VIX fetch failed: {e}")
            raise

    def calculate_vix_features(self, vix_data: pd.DataFrame) -> pd.DataFrame:
        """
        VIX特徴量計算（6特徴量）

        Args:
            vix_data: VIXデータ

        Returns:
            VIX特徴量DataFrame
        """
        try:
            if vix_data is None or vix_data.empty:
                # デフォルト値でDataFrameを作成
                default_features = self._get_default_vix_features()
                return pd.DataFrame(
                    [default_features], index=[pd.Timestamp.now(tz="UTC")]
                )

            # VIX特徴量計算（preprocessor期待形式に合わせる）
            vix_ma20 = vix_data["vix_close"].rolling(20).mean()
            vix_std = vix_data["vix_close"].rolling(20).std()

            # 各行に対してVIX特徴量を計算
            features_df = pd.DataFrame(index=vix_data.index)
            features_df["vix_level"] = vix_data["vix_close"]
            features_df["vix_change"] = vix_data["vix_close"].pct_change()
            features_df["vix_zscore"] = (vix_data["vix_close"] - vix_ma20) / vix_std
            features_df["fear_level"] = (vix_data["vix_close"] > 20).astype(int)
            features_df["vix_spike"] = (
                vix_data["vix_close"] > vix_ma20 + 2 * vix_std
            ).astype(int)

            # レジーム数値計算
            def calc_regime(vix_val):
                if vix_val > 35:
                    return 3
                elif vix_val > 25:
                    return 2
                elif vix_val > 15:
                    return 1
                else:
                    return 0

            features_df["vix_regime_numeric"] = vix_data["vix_close"].apply(calc_regime)

            # NaN値をデフォルト値で補完
            default_values = self._get_default_vix_features()
            for col in features_df.columns:
                features_df[col] = features_df[col].fillna(default_values.get(col, 0))

            logger.info(
                f"VIX features calculated: {len(features_df)} rows, "
                f"{len(features_df.columns)} columns"
            )
            return features_df

        except Exception as e:
            logger.error(f"Failed to calculate VIX features: {e}")
            # エラー時はデフォルト値でDataFrameを返す
            default_features = self._get_default_vix_features()
            return pd.DataFrame([default_features], index=[pd.Timestamp.now(tz="UTC")])

    def _get_default_vix_features(self) -> Dict[str, Any]:
        """VIX特徴量デフォルト値"""
        return {
            "vix_level": 20.0,  # 通常レベル
            "vix_change": 0.0,
            "vix_zscore": 0.0,
            "fear_level": 1,  # 通常恐怖レベル
            "vix_spike": 0,
            "vix_regime_numeric": 1,  # 通常レジーム
        }


def get_available_vix_features():
    """利用可能なVIX特徴量の名前リストを取得"""
    return [
        "vix_level",
        "vix_change",
        "vix_zscore",
        "fear_level",
        "vix_spike",
        "vix_regime_numeric",
    ]
