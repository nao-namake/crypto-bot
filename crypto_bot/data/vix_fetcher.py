"""
VIX恐怖指数データフェッチャー
Yahoo Financeから米国VIX指数データを取得し、101特徴量システムに統合
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class VIXDataFetcher:
    """VIX恐怖指数データ取得クラス"""

    def __init__(self):
        self.symbol = "^VIX"  # Yahoo Finance VIXシンボル

    def get_vix_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        timeframe: str = "1d",
        limit: Optional[int] = None,
        since: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        VIXデータ取得

        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            VIXデータのDataFrame
        """
        try:
            # デフォルト期間設定（過去1年間）
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            # Yahoo Financeからデータ取得
            vix_ticker = yf.Ticker(self.symbol)
            vix_data = vix_ticker.history(start=start_date, end=end_date)

            if vix_data.empty:
                logger.warning("No VIX data retrieved")
                return None

            # カラム名を統一
            vix_data.columns = vix_data.columns.str.lower()
            vix_data = vix_data.rename(columns={"close": "vix_close"})

            logger.info(f"VIX data retrieved: {len(vix_data)} records")
            return vix_data

        except Exception as e:
            logger.error(f"Failed to fetch VIX data: {e}")
            return None

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
