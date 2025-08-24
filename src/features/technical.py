"""
テクニカル指標実装 - 6個の厳選指標

レガシーシステムの97特徴量から、実用性重視で
6個の高効果テクニカル指標を実装。

実装指標:
- Momentum系（2個）: rsi_14, macd
- Volatility系（2個）: atr_14, bb_position
- トレンド系（2個）: ema_20, ema_50

Phase 13改善実装日: 2025年8月24日.
"""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from ..core.exceptions import DataProcessingError
from ..core.logger import get_logger


class TechnicalIndicators:
    """
    テクニカル指標計算クラス

    シンプルで効率的な実装により、必要最小限の
    特徴量生成を提供。.
    """

    def __init__(self):
        """初期化."""
        self.logger = get_logger()
        self.computed_features = set()

    def generate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        全テクニカル指標を生成

        Args:
            df: OHLCV データフレーム

        Returns:
            特徴量追加済みデータフレーム.
        """
        try:
            self.logger.info("テクニカル指標生成開始")
            self.computed_features.clear()

            # 必要列チェック
            required_cols = ["close", "volume", "high", "low"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise DataProcessingError(f"必要列が不足: {missing_cols}")

            result_df = df.copy()

            # 各指標生成（6個の技術指標のみ）
            result_df["rsi_14"] = self._calculate_rsi(result_df["close"])
            self.computed_features.add("rsi_14")

            macd_line, _ = self._calculate_macd(result_df["close"])
            result_df["macd"] = macd_line
            self.computed_features.add("macd")

            result_df["atr_14"] = self._calculate_atr(result_df)
            self.computed_features.add("atr_14")

            result_df["bb_position"] = self._calculate_bb_position(result_df["close"])
            self.computed_features.add("bb_position")

            result_df["ema_20"] = result_df["close"].ewm(span=20, adjust=False).mean()
            result_df["ema_50"] = result_df["close"].ewm(span=50, adjust=False).mean()
            self.computed_features.update(["ema_20", "ema_50"])

            # NaN値処理
            for feature in self.computed_features:
                if feature in result_df.columns:
                    result_df[feature] = result_df[feature].ffill().bfill().fillna(0)

            self.logger.info(f"テクニカル指標生成完了: {len(self.computed_features)}個")
            return result_df

        except Exception as e:
            self.logger.error(f"テクニカル指標生成エラー: {e}")
            raise DataProcessingError(f"特徴量生成失敗: {e}")

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """RSI計算."""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        rs = gain / (loss + 1e-8)
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, close: pd.Series) -> tuple:
        """MACD計算（MACDラインとシグナルラインを返す）."""
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line, macd_signal

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR計算."""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=period, min_periods=1).mean()

    def _calculate_bb_position(self, close: pd.Series, period: int = 20) -> pd.Series:
        """ボリンジャーバンド位置計算."""
        bb_middle = close.rolling(window=period, min_periods=1).mean()
        bb_std_dev = close.rolling(window=period, min_periods=1).std()
        bb_upper = bb_middle + (bb_std_dev * 2)
        bb_lower = bb_middle - (bb_std_dev * 2)
        return (close - bb_lower) / (bb_upper - bb_lower + 1e-8)


    def get_feature_info(self) -> Dict[str, Any]:
        """特徴量情報取得."""
        return {
            "total_features": len(self.computed_features),
            "computed_features": sorted(list(self.computed_features)),
            "categories": {
                "momentum": ["rsi_14", "macd"],
                "volatility": ["atr_14", "bb_position"],
                "trend": ["ema_20", "ema_50"],
            },
        }
