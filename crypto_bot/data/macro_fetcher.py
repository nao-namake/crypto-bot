"""
マクロ経済データフェッチャー
Yahoo Financeから米ドル指数(DXY)・金利データを取得し、101特徴量システムに統合
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MacroDataFetcher:
    """マクロ経済データ取得クラス"""

    def __init__(self):
        self.symbols = {
            "dxy": "DX-Y.NYB",  # ドル指数
            "us10y": "^TNX",  # 米10年債利回り
            "us2y": "^IRX",  # 米2年債利回り
        }

    def get_macro_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        マクロ経済データ取得

        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            マクロデータの辞書
        """
        try:
            # デフォルト期間設定（過去1年間）
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            macro_data = {}

            for name, symbol in self.symbols.items():
                try:
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(start=start_date, end=end_date)

                    if not data.empty:
                        data.columns = data.columns.str.lower()
                        macro_data[name] = data
                        logger.info(f"{name} data retrieved: {len(data)} records")
                    else:
                        logger.warning(f"No data retrieved for {name}")

                except Exception as e:
                    logger.error(f"Failed to fetch {name} data: {e}")

            return macro_data

        except Exception as e:
            logger.error(f"Failed to fetch macro data: {e}")
            return {}

    def calculate_macro_features(
        self, macro_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        マクロ経済特徴量計算（10特徴量）

        Args:
            macro_data: マクロデータ辞書

        Returns:
            マクロ特徴量DataFrame
        """
        try:
            if not macro_data or all(df.empty for df in macro_data.values()):
                # データがない場合はデフォルト値でDataFrameを作成
                default_features = self._get_default_macro_features()
                return pd.DataFrame(
                    [default_features], index=[pd.Timestamp.now(tz="UTC")]
                )

            # 共通のインデックスを決定（最も長いデータセットを基準）
            max_data = max(macro_data.values(), key=len, default=pd.DataFrame())
            if max_data.empty:
                default_features = self._get_default_macro_features()
                return pd.DataFrame(
                    [default_features], index=[pd.Timestamp.now(tz="UTC")]
                )

            features_df = pd.DataFrame(index=max_data.index)

            # DXY（ドル指数）特徴量（preprocessor期待形式）
            if "dxy" in macro_data and not macro_data["dxy"].empty:
                dxy_data = macro_data["dxy"]
                dxy_aligned = dxy_data.reindex(features_df.index, method="ffill")

                dxy_ma20 = dxy_aligned["close"].rolling(20).mean()
                dxy_std = dxy_aligned["close"].rolling(20).std()

                features_df["dxy_level"] = dxy_aligned["close"]
                features_df["dxy_change"] = dxy_aligned["close"].pct_change()
                features_df["dxy_zscore"] = (dxy_aligned["close"] - dxy_ma20) / dxy_std
                features_df["dxy_strength"] = (dxy_aligned["close"] > dxy_ma20).astype(
                    int
                )
            else:
                defaults = self._get_default_dxy_features()
                for key, value in defaults.items():
                    features_df[key] = value

            # 米10年債利回り特徴量（preprocessor期待形式）
            if "us10y" in macro_data and not macro_data["us10y"].empty:
                us10y_data = macro_data["us10y"]
                us10y_aligned = us10y_data.reindex(features_df.index, method="ffill")

                us10y_ma20 = us10y_aligned["close"].rolling(20).mean()
                us10y_std = us10y_aligned["close"].rolling(20).std()

                features_df["treasury_10y_level"] = us10y_aligned["close"]
                features_df["treasury_10y_change"] = us10y_aligned["close"].diff()
                features_df["treasury_10y_zscore"] = (
                    us10y_aligned["close"] - us10y_ma20
                ) / us10y_std
                features_df["treasury_regime"] = (
                    us10y_aligned["close"] > us10y_ma20
                ).astype(int)
            else:
                defaults = self._get_default_10y_features()
                for key, value in defaults.items():
                    features_df[key] = value

            # 米2年債利回り特徴量とイールドカーブ
            if "us2y" in macro_data and not macro_data["us2y"].empty:
                us2y_data = macro_data["us2y"]
                us2y_aligned = us2y_data.reindex(features_df.index, method="ffill")

                # イールドカーブとリスクセンチメント
                treasury_10y = features_df.get("treasury_10y_level", 4.0)
                if isinstance(treasury_10y, pd.Series):
                    yield_spread = treasury_10y - us2y_aligned["close"]
                    features_df["yield_curve_spread"] = yield_spread
                    features_df["risk_sentiment"] = (yield_spread > 0).astype(int)
                else:
                    features_df["yield_curve_spread"] = (
                        treasury_10y - us2y_aligned["close"]
                    )
                    features_df["risk_sentiment"] = (
                        features_df["yield_curve_spread"] > 0
                    ).astype(int)
            else:
                defaults = self._get_default_2y_features()
                for key, value in defaults.items():
                    features_df[key] = value

            # NaN値を適切にデフォルト値で補完
            default_values = self._get_default_macro_features()
            for col in features_df.columns:
                features_df[col] = features_df[col].fillna(default_values.get(col, 0))
                # 無限大値も補完
                features_df[col] = features_df[col].replace(
                    [float("inf"), float("-inf")], default_values.get(col, 0)
                )

            logger.info(
                f"Macro features calculated: {len(features_df)} rows, "
                f"{len(features_df.columns)} columns"
            )
            return features_df

        except Exception as e:
            logger.error(f"Failed to calculate macro features: {e}")
            # エラー時はデフォルト値でDataFrameを返す
            default_features = self._get_default_macro_features()
            return pd.DataFrame([default_features], index=[pd.Timestamp.now(tz="UTC")])

    def _get_default_dxy_features(self) -> Dict[str, Any]:
        """DXY特徴量デフォルト値"""
        return {
            "dxy_level": 103.0,  # 典型的なDXYレベル
            "dxy_change": 0.0,
            "dxy_zscore": 0.0,
            "dxy_strength": 0,
        }

    def _get_default_10y_features(self) -> Dict[str, Any]:
        """10年債特徴量デフォルト値"""
        return {
            "treasury_10y_level": 4.0,  # 典型的な10年債利回り
            "treasury_10y_change": 0.0,
            "treasury_10y_zscore": 0.0,
            "treasury_regime": 0,
        }

    def _get_default_2y_features(self) -> Dict[str, Any]:
        """2年債特徴量デフォルト値"""
        return {
            "yield_curve_spread": -0.5,  # 逆イールド状態
            "risk_sentiment": 0,
        }

    def _get_default_macro_features(self) -> Dict[str, Any]:
        """マクロ特徴量デフォルト値（10特徴量）"""
        features = {}
        features.update(self._get_default_dxy_features())
        features.update(self._get_default_10y_features())
        features.update(self._get_default_2y_features())
        return features
