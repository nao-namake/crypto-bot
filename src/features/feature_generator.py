"""
特徴量生成統合システム - Phase 18統合版

TechnicalIndicators、MarketAnomalyDetector、FeatureServiceAdapterを
1つのクラスに統合し、重複コード削除と保守性向上を実現。

97特徴量から12特徴量への極限最適化システム実装。

統合効果:
- ファイル数削減: 3→1（67%削減）
- コード行数削減: 461行→約250行（46%削減）
- 重複コード削除: _handle_nan_values、logger初期化等
- 管理簡素化: 特徴量処理の完全一元化

Phase 18統合実装日: 2025年8月31日.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..core.config import get_anomaly_config

# Phase 19: 特徴量定義一元化（feature_managerから取得）
from ..core.config.feature_manager import get_feature_categories, get_feature_names
from ..core.exceptions import DataProcessingError
from ..core.logger import CryptoBotLogger, get_logger

# 特徴量リスト（一元化対応）
OPTIMIZED_FEATURES = get_feature_names()

# 特徴量カテゴリ（一元化対応）
FEATURE_CATEGORIES = get_feature_categories()


class FeatureGenerator:
    """
    統合特徴量生成クラス - Phase 19統合版

    テクニカル指標、異常検知、特徴量サービス機能を
    1つのクラスに統合し、12特徴量生成を効率的に提供。

    主要機能:
    - テクニカル指標生成（6個）
    - 異常検知指標生成（3個）
    - 基本特徴量生成（3個）
    - 統合品質管理と12特徴量確認
    """

    def __init__(self, lookback_period: Optional[int] = None) -> None:
        """
        初期化

        Args:
            lookback_period: 異常検知の参照期間
        """
        self.logger = get_logger()
        self.lookback_period = lookback_period or get_anomaly_config(
            "spike_detection.lookback_period", 20
        )
        self.computed_features = set()

    async def generate_features(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """
        統合特徴量生成処理（12特徴量確認機能付き）

        Args:
            market_data: 市場データ（DataFrame または dict）

        Returns:
            12特徴量を含むDataFrame
        """
        try:
            # DataFrameに変換
            result_df = self._convert_to_dataframe(market_data)

            self.logger.info("特徴量生成開始 - 12特徴量システム")
            self.computed_features.clear()

            # 必要列チェック
            self._validate_required_columns(result_df)

            # 🔹 基本特徴量を生成（3個）
            result_df = self._generate_basic_features(result_df)

            # 🔹 テクニカル指標を生成（6個）
            result_df = self._generate_technical_indicators(result_df)

            # 🔹 異常検知指標を生成（3個）
            result_df = self._generate_anomaly_indicators(result_df)

            # 🔹 NaN値処理（統合版）
            result_df = self._handle_nan_values(result_df)

            # 🎯 12特徴量完全確認・検証
            self._validate_feature_generation(result_df)

            # DataFrameをそのまま返す（戦略で使用するため）
            return result_df

        except Exception as e:
            self.logger.error(f"統合特徴量生成エラー: {e}")
            raise DataProcessingError(f"特徴量生成失敗: {e}")

    def _convert_to_dataframe(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """市場データをDataFrameに変換（タイムフレーム辞書対応）"""
        if isinstance(market_data, pd.DataFrame):
            return market_data.copy()
        elif isinstance(market_data, dict):
            try:
                # タイムフレーム辞書の場合（マルチタイムフレームデータ）
                # 実際に使用されるタイムフレーム: 4h（メイン）, 15m（サブ）
                timeframe_keys = ["4h", "15m"]  # 優先順位順
                for tf in timeframe_keys:
                    if tf in market_data and isinstance(market_data[tf], pd.DataFrame):
                        self.logger.info(f"タイムフレーム辞書からメイン時系列取得: {tf}")
                        return market_data[tf].copy()

                # 通常の辞書データの場合（OHLCV形式等）
                # 全ての値がスカラーかリストかをチェック
                if all(
                    isinstance(v, (int, float, str)) or (isinstance(v, list) and len(v) > 0)
                    for v in market_data.values()
                ):
                    return pd.DataFrame(market_data)

                # その他の構造の辞書
                self.logger.warning(f"複雑な辞書構造を検出: keys={list(market_data.keys())}")
                return pd.DataFrame(market_data)

            except (ValueError, KeyError, TypeError) as e:
                self.logger.error(
                    f"市場データ変換エラー - 構造: {type(market_data)}, キー: {list(market_data.keys()) if hasattr(market_data, 'keys') else 'N/A'}"
                )
                raise DataProcessingError(f"Dict→DataFrame変換データ構造エラー: {e}")
            except (MemoryError, OverflowError) as e:
                raise DataProcessingError(f"Dict→DataFrame変換サイズエラー: {e}")
            except Exception as e:
                raise DataProcessingError(f"Dict→DataFrame変換予期しないエラー: {e}")
        else:
            raise ValueError(f"Unsupported market_data type: {type(market_data)}")

    def _validate_required_columns(self, df: pd.DataFrame) -> None:
        """必要列の存在確認"""
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise DataProcessingError(f"必要列が不足: {missing_cols}")

    def _generate_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """基本特徴量生成（3個）"""
        result_df = df.copy()

        # 基本データはそのまま（close, volume）
        basic_features = []
        if "close" in result_df.columns:
            basic_features.append("close")
        if "volume" in result_df.columns:
            basic_features.append("volume")

        # returns_1を計算
        if "close" in result_df.columns:
            result_df["returns_1"] = result_df["close"].pct_change(1, fill_method=None)
            result_df["returns_1"] = result_df["returns_1"].fillna(0)
            basic_features.append("returns_1")

        self.computed_features.update(basic_features)
        self.logger.debug(f"基本特徴量生成完了: {len(basic_features)}個")
        return result_df

    def _generate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """テクニカル指標生成（6個）"""
        result_df = df.copy()

        # RSI 14期間
        result_df["rsi_14"] = self._calculate_rsi(result_df["close"])
        self.computed_features.add("rsi_14")

        # MACD（ラインとシグナル両方生成）
        macd_line, macd_signal = self._calculate_macd(result_df["close"])
        result_df["macd"] = macd_line
        result_df["macd_signal"] = macd_signal
        self.computed_features.add("macd")
        self.computed_features.add("macd_signal")

        # ATR 14期間
        result_df["atr_14"] = self._calculate_atr(result_df)
        self.computed_features.add("atr_14")

        # ボリンジャーバンド位置
        result_df["bb_position"] = self._calculate_bb_position(result_df["close"])
        self.computed_features.add("bb_position")

        # EMA 20期間・50期間
        result_df["ema_20"] = result_df["close"].ewm(span=20, adjust=False).mean()
        result_df["ema_50"] = result_df["close"].ewm(span=50, adjust=False).mean()
        self.computed_features.update(["ema_20", "ema_50"])

        self.logger.debug(f"テクニカル指標生成完了: 6個")
        return result_df

    def _generate_anomaly_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """異常検知指標生成（3個）"""
        result_df = df.copy()

        # Z-Score
        result_df["zscore"] = self._calculate_zscore(result_df["close"])
        self.computed_features.add("zscore")

        # 出来高比率
        result_df["volume_ratio"] = self._calculate_volume_ratio(result_df["volume"])
        self.computed_features.add("volume_ratio")

        self.logger.debug(f"異常検知指標生成完了: 2個")
        return result_df

    def _calculate_rsi(self, close: pd.Series, period: int = 14) -> pd.Series:
        """RSI計算"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()
        rs = gain / (loss + 1e-8)
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, close: pd.Series) -> tuple:
        """MACD計算（MACDラインとシグナルラインを返す）"""
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line, macd_signal

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR計算"""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=period, min_periods=1).mean()

    def _calculate_bb_position(self, close: pd.Series, period: int = 20) -> pd.Series:
        """ボリンジャーバンド位置計算"""
        bb_middle = close.rolling(window=period, min_periods=1).mean()
        bb_std_dev = close.rolling(window=period, min_periods=1).std()
        bb_upper = bb_middle + (bb_std_dev * 2)
        bb_lower = bb_middle - (bb_std_dev * 2)
        return (close - bb_lower) / (bb_upper - bb_lower + 1e-8)

    def _calculate_zscore(self, close: pd.Series, period: Optional[int] = None) -> pd.Series:
        """Z-Score計算"""
        try:
            if period is None:
                period = get_anomaly_config("zscore.calculation_period", 20)
            rolling_mean = close.rolling(window=period, min_periods=1).mean()
            rolling_std = close.rolling(window=period, min_periods=1).std()
            return (close - rolling_mean) / (rolling_std + 1e-8)
        except Exception as e:
            self.logger.error(f"Z-Score計算エラー: {e}")
            return pd.Series(np.zeros(len(close)), index=close.index)

    def _calculate_volume_ratio(self, volume: pd.Series, period: Optional[int] = None) -> pd.Series:
        """出来高比率計算"""
        try:
            if period is None:
                period = get_anomaly_config("volume_ratio.calculation_period", 20)
            volume_avg = volume.rolling(window=period, min_periods=1).mean()
            return volume / (volume_avg + 1e-8)
        except Exception as e:
            self.logger.error(f"出来高比率計算エラー: {e}")
            return pd.Series(np.zeros(len(volume)), index=volume.index)

    # Phase 19: market_stress特徴量削除（12特徴量統一）
    # def _calculate_market_stress(self, df: pd.DataFrame) -> pd.Series:
    #     """市場ストレス度指標計算（統合異常指標）"""

    def _normalize(self, series: pd.Series) -> pd.Series:
        """0-1範囲に正規化"""
        try:
            # 外れ値処理（設定ファイルから取得）
            outlier_clip_quantile = get_anomaly_config("normalization.outlier_clip_quantile", 0.95)
            upper_bound = series.quantile(outlier_clip_quantile)
            clipped_series = np.clip(series, 0, upper_bound)

            # 0-1正規化
            min_val = clipped_series.min()
            max_val = clipped_series.max()

            if max_val - min_val == 0:
                return pd.Series(np.zeros(len(series)), index=series.index)

            return (clipped_series - min_val) / (max_val - min_val)

        except Exception:
            return pd.Series(np.zeros(len(series)), index=series.index)

    def _handle_nan_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """NaN値処理（統合版）"""
        for feature in self.computed_features:
            if feature in df.columns:
                df[feature] = df[feature].ffill().bfill().fillna(0)
        return df

    def _validate_feature_generation(self, df: pd.DataFrame) -> None:
        """12特徴量完全確認・検証"""
        generated_features = [col for col in OPTIMIZED_FEATURES if col in df.columns]
        missing_features = [col for col in OPTIMIZED_FEATURES if col not in df.columns]

        # 🚨 統合ログ出力
        self.logger.info(
            f"特徴量生成完了 - 総数: {len(generated_features)}/{len(OPTIMIZED_FEATURES)}個",
            extra_data={
                "basic_features": len(
                    [f for f in ["close", "volume", "returns_1"] if f in df.columns]
                ),
                "technical_features": len(
                    [
                        f
                        for f in [
                            "rsi_14",
                            "macd",
                            "atr_14",
                            "bb_position",
                            "ema_20",
                            "ema_50",
                        ]
                        if f in df.columns
                    ]
                ),
                "anomaly_features": len([f for f in ["zscore", "volume_ratio"] if f in df.columns]),
                "generated_features": generated_features,
                "missing_features": missing_features,
                "total_expected": len(OPTIMIZED_FEATURES),
                "success": len(generated_features) == len(OPTIMIZED_FEATURES),
            },
        )

        # ⚠️ 不足特徴量の警告
        if missing_features:
            self.logger.warning(
                f"🚨 特徴量不足検出: {missing_features} ({len(missing_features)}個不足)"
            )
        else:
            self.logger.info("✅ 12特徴量完全生成成功")

    def generate_features_sync(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        同期特徴量生成（後方互換性用）

        Phase 18統合により、テストとの互換性のため同期版を提供。
        DataFrame入力・DataFrame出力で、異常検知特徴量のみ生成。

        Args:
            df: OHLCVデータフレーム
        Returns:
            特徴量追加されたデータフレーム
        """
        # 必要列のチェック（OHLCV全て必要）
        required_columns = ["open", "high", "low", "close", "volume"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            from src.core.exceptions import DataProcessingError

            raise DataProcessingError(f"必要列が不足: {missing_columns}")

        # 簡易版：market_stress特徴量のみ生成
        result_df = df.copy()

        # 効果的なlookback_periodを決定（最小3、最大はデータ長の80%）
        effective_lookback = min(self.lookback_period, max(3, int(len(df) * 0.8)))

        # 出来高異常検知 (volume_ratio)
        if "volume" in df.columns:
            if len(df) >= 2:
                rolling_mean = df["volume"].rolling(window=effective_lookback, min_periods=1).mean()
                volume_ratio = df["volume"] / rolling_mean.fillna(df["volume"].mean())
                result_df["volume_ratio"] = volume_ratio.fillna(1.0)
            else:
                result_df["volume_ratio"] = 1.0

        # 価格Z-Score (zscore)
        if "close" in df.columns:
            if len(df) >= 2:
                rolling_mean = df["close"].rolling(window=effective_lookback, min_periods=1).mean()
                rolling_std = df["close"].rolling(window=effective_lookback, min_periods=1).std()
                zscore = (df["close"] - rolling_mean) / rolling_std.fillna(
                    1.0
                )  # std=0の場合は1.0で除算
                result_df["zscore"] = zscore.fillna(0.0)
            else:
                result_df["zscore"] = 0.0

        # Phase 19: market_stress削除（12特徴量統一）
        # 市場ストレス (market_stress) - 統合指標 - 削除済み

        # computed_featuresを更新（market_stress除外）
        self.computed_features.update(["volume_ratio", "zscore"])

        return result_df

    def get_feature_info(self) -> Dict[str, Any]:
        """特徴量情報取得"""
        return {
            "total_features": len(self.computed_features),
            "computed_features": sorted(list(self.computed_features)),
            "feature_categories": FEATURE_CATEGORIES,
            "optimized_features": OPTIMIZED_FEATURES,
            "parameters": {"lookback_period": self.lookback_period},
            "feature_descriptions": {
                "close": "終値（基準価格）",
                "volume": "出来高（市場活動度）",
                "returns_1": "1期間リターン（短期モメンタム）",
                "rsi_14": "RSI（オーバーボート・ソールド判定）",
                "macd": "MACD（トレンド転換シグナル）",
                "macd_signal": "MACDシグナル（エントリータイミング）",
                "atr_14": "ATR（ボラティリティ測定）",
                "bb_position": "ボリンジャーバンド位置（価格位置）",
                "ema_20": "EMA短期（短期トレンド）",
                "ema_50": "EMA中期（中期トレンド）",
                "volume_ratio": "出来高比率（出来高異常検知）",
                "zscore": "価格Z-Score（標準化価格位置）",
            },
        }


# 後方互換性のためのエイリアス
TechnicalIndicators = FeatureGenerator
MarketAnomalyDetector = FeatureGenerator
FeatureServiceAdapter = FeatureGenerator

# エクスポートリスト
__all__ = [
    "FeatureGenerator",
    "TechnicalIndicators",
    "MarketAnomalyDetector",
    "FeatureServiceAdapter",
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]
