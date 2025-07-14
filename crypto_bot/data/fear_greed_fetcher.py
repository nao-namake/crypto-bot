"""
Fear&Greed指数データフェッチャー
Alternative.me APIからCrypto Fear & Greed Indexを取得し、101特徴量システムに統合
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class FearGreedDataFetcher:
    """Fear&Greed指数データ取得クラス"""

    def __init__(self):
        self.api_url = "https://api.alternative.me/fng/"

    def get_fear_greed_data(
        self, limit: int = 30, days_back: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fear&Greedデータ取得

        Args:
            limit: 取得するデータ数
            days_back: 過去何日分のデータを取得するか（limitと同等）

        Returns:
            Fear&GreedデータのDataFrame
        """
        try:
            # days_backが指定されている場合はlimitとして使用
            if days_back is not None:
                limit = days_back

            # Alternative.me APIからデータ取得
            params = {"limit": limit}
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if "data" not in data:
                logger.warning("No Fear&Greed data in response")
                return None

            # DataFrameに変換
            fg_data = pd.DataFrame(data["data"])
            fg_data["timestamp"] = pd.to_datetime(fg_data["timestamp"], unit="s")
            fg_data["value"] = pd.to_numeric(fg_data["value"])
            fg_data = fg_data.sort_values("timestamp").set_index("timestamp")

            logger.info(f"Fear&Greed data retrieved: {len(fg_data)} records")
            return fg_data

        except Exception as e:
            logger.error(f"Failed to fetch Fear&Greed data: {e}")
            return None

    def calculate_fear_greed_features(self, fg_data: pd.DataFrame) -> pd.DataFrame:
        """
        Fear&Greed特徴量計算（13特徴量）

        Args:
            fg_data: Fear&Greedデータ

        Returns:
            Fear&Greed特徴量DataFrame
        """
        try:
            if fg_data is None or fg_data.empty:
                # デフォルト値でDataFrameを作成
                default_features = self._get_default_fear_greed_features()
                return pd.DataFrame(
                    [default_features], index=[pd.Timestamp.now(tz="UTC")]
                )

            # 各行に対してFear&Greed特徴量を計算
            features_df = pd.DataFrame(index=fg_data.index)

            # 基本指標
            features_df["fg_index"] = fg_data["value"]
            features_df["fg_change_1d"] = fg_data["value"].pct_change()
            features_df["fg_change_7d"] = fg_data["value"].pct_change(7)
            features_df["fg_ma_7"] = fg_data["value"].rolling(7).mean()
            features_df["fg_ma_30"] = fg_data["value"].rolling(30).mean()

            # 感情状態分類
            features_df["fg_extreme_fear"] = (fg_data["value"] < 25).astype(int)
            features_df["fg_fear"] = (
                (fg_data["value"] >= 25) & (fg_data["value"] < 45)
            ).astype(int)
            features_df["fg_neutral"] = (
                (fg_data["value"] >= 45) & (fg_data["value"] < 55)
            ).astype(int)
            features_df["fg_greed"] = (
                (fg_data["value"] >= 55) & (fg_data["value"] < 75)
            ).astype(int)
            features_df["fg_extreme_greed"] = (fg_data["value"] >= 75).astype(int)

            # 統計指標
            features_df["fg_volatility"] = fg_data["value"].rolling(7).std()
            features_df["fg_momentum"] = (
                fg_data["value"] - fg_data["value"].rolling(7).mean()
            )
            features_df["fg_reversal_signal"] = (
                (fg_data["value"] < 25) | (fg_data["value"] > 75)
            ).astype(int)

            # NaN値をデフォルト値で補完
            default_values = self._get_default_fear_greed_features()
            for col in features_df.columns:
                features_df[col] = features_df[col].fillna(default_values.get(col, 0))

            logger.info(
                f"Fear&Greed features calculated: {len(features_df)} rows, "
                f"{len(features_df.columns)} columns"
            )
            return features_df

        except Exception as e:
            logger.error(f"Failed to calculate Fear&Greed features: {e}")
            # エラー時はデフォルト値でDataFrameを返す
            default_features = self._get_default_fear_greed_features()
            return pd.DataFrame([default_features], index=[pd.Timestamp.now(tz="UTC")])

    def _get_default_fear_greed_features(self) -> Dict[str, Any]:
        """Fear&Greed特徴量デフォルト値"""
        return {
            "fg_index": 50.0,  # 中立
            "fg_change_1d": 0.0,
            "fg_change_7d": 0.0,
            "fg_ma_7": 50.0,
            "fg_ma_30": 50.0,
            "fg_extreme_fear": 0,
            "fg_fear": 0,
            "fg_neutral": 1,
            "fg_greed": 0,
            "fg_extreme_greed": 0,
            "fg_volatility": 10.0,
            "fg_momentum": 0.0,
            "fg_reversal_signal": 0,
        }


def get_available_fear_greed_features():
    """利用可能なFear&Greed特徴量の名前リストを取得"""
    return [
        "fg_index",
        "fg_change_1d",
        "fg_change_7d",
        "fg_ma_7",
        "fg_ma_30",
        "fg_extreme_fear",
        "fg_fear",
        "fg_neutral",
        "fg_greed",
        "fg_extreme_greed",
        "fg_volatility",
        "fg_momentum",
        "fg_reversal_signal",
    ]
