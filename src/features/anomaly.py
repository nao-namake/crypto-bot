"""
異常検知指標実装 - 3個の統合指標

市場異常・価格効率性・異常値検出による
高精度な取引シグナル補強機能。

実装指標:
- zscore: 価格Z-Score（標準化価格位置）
- volume_ratio: 出来高比率（平均出来高対比）
- market_stress: 市場ストレス度（統合指標）

Phase 13改善実装日: 2025年8月24日.
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from ..core.exceptions import DataProcessingError
from ..core.logger import get_logger


class MarketAnomalyDetector:
    """
    異常検知指標計算クラス

    統計的手法により市場の異常状態を検出し、
    取引戦略の精度向上をサポート。.
    """

    def __init__(self, lookback_period: int = 20):
        """
        初期化

        Args:
            lookback_period: 異常検知の参照期間.
        """
        self.logger = get_logger()
        self.lookback_period = lookback_period
        self.computed_features = set()

    def generate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        全異常検知指標を生成

        Args:
            df: OHLCV データフレーム

        Returns:
            異常検知指標追加済みデータフレーム.
        """
        try:
            self.logger.info("異常検知指標生成開始")
            self.computed_features.clear()

            # 必要列チェック
            required_cols = ["open", "high", "low", "close", "volume"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise DataProcessingError(f"必要列が不足: {missing_cols}")

            result_df = df.copy()

            # 3つの異常検知指標を生成
            result_df["zscore"] = self._calculate_zscore(result_df["close"])
            self.computed_features.add("zscore")

            result_df["volume_ratio"] = self._calculate_volume_ratio(result_df["volume"])
            self.computed_features.add("volume_ratio")

            result_df["market_stress"] = self._calculate_market_stress(result_df)
            self.computed_features.add("market_stress")

            # NaN値処理
            for feature in self.computed_features:
                if feature in result_df.columns:
                    result_df[feature] = result_df[feature].ffill().bfill().fillna(0)

            self.logger.info(f"異常検知指標生成完了: {len(self.computed_features)}個")
            return result_df

        except Exception as e:
            self.logger.error(f"異常検知指標生成エラー: {e}")
            raise DataProcessingError(f"異常検知特徴量生成失敗: {e}")

    def _calculate_market_stress(self, df: pd.DataFrame) -> pd.Series:
        """市場ストレス度指標計算."""
        try:
            # 価格ギャップ（前日比で大きな価格変動）
            price_gap = np.abs(df["open"] - df["close"].shift(1)) / df["close"].shift(1)

            # 日中変動率（High-Low range）
            intraday_range = (df["high"] - df["low"]) / df["close"]

            # 出来高スパイク（平均の何倍か）
            volume_avg = df["volume"].rolling(window=self.lookback_period, min_periods=1).mean()
            volume_spike = df["volume"] / (volume_avg + 1e-8)

            # 重み付け合成（価格変動重視）
            market_stress = (
                0.4 * self._normalize(price_gap)
                + 0.3 * self._normalize(intraday_range)
                + 0.3 * self._normalize(volume_spike)
            )

            return market_stress

        except Exception as e:
            self.logger.error(f"市場ストレス度指標エラー: {e}")
            return pd.Series(np.zeros(len(df)), index=df.index)

    def _normalize(self, series: pd.Series) -> pd.Series:
        """0-1範囲に正規化."""
        try:
            # 外れ値処理（上位5%をクリップ）
            upper_bound = series.quantile(0.95)
            clipped_series = np.clip(series, 0, upper_bound)

            # 0-1正規化
            min_val = clipped_series.min()
            max_val = clipped_series.max()

            if max_val - min_val == 0:
                return pd.Series(np.zeros(len(series)), index=series.index)

            return (clipped_series - min_val) / (max_val - min_val)

        except Exception:
            return pd.Series(np.zeros(len(series)), index=series.index)

    def _calculate_zscore(self, close: pd.Series, period: int = 20) -> pd.Series:
        """Z-Score計算."""
        try:
            rolling_mean = close.rolling(window=period, min_periods=1).mean()
            rolling_std = close.rolling(window=period, min_periods=1).std()
            return (close - rolling_mean) / (rolling_std + 1e-8)
        except Exception as e:
            self.logger.error(f"Z-Score計算エラー: {e}")
            return pd.Series(np.zeros(len(close)), index=close.index)

    def _calculate_volume_ratio(self, volume: pd.Series, period: int = 20) -> pd.Series:
        """出来高比率計算."""
        try:
            volume_avg = volume.rolling(window=period, min_periods=1).mean()
            return volume / (volume_avg + 1e-8)
        except Exception as e:
            self.logger.error(f"出来高比率計算エラー: {e}")
            return pd.Series(np.zeros(len(volume)), index=volume.index)

    def get_feature_info(self) -> Dict[str, Any]:
        """特徴量情報取得."""
        return {
            "total_features": len(self.computed_features),
            "computed_features": sorted(list(self.computed_features)),
            "parameters": {"lookback_period": self.lookback_period},
            "feature_descriptions": {
                "zscore": "価格Z-Score（標準化価格位置）",
                "volume_ratio": "出来高比率（平均出来高対比）",
                "market_stress": "市場ストレス度（複合指標）"
            },
        }
