"""
特徴量生成統合システム - Phase 21統合版

TechnicalIndicators、MarketAnomalyDetector、FeatureServiceAdapterを
1つのクラスに統合し、重複コード削除と保守性向上を実現。

97特徴量から15特徴量への最適化システム実装（5戦略対応）。

統合効果:
- ファイル数削減: 3→1（67%削減）
- コード行数削減: 461行→約250行（46%削減）
- 重複コード削除: _handle_nan_values、logger初期化等
- 管理簡素化: 特徴量処理の完全一元化

Phase 21統合実装日: 2025年9月12日.
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..core.config import get_anomaly_config

# Phase 21: 特徴量定義一元化（feature_managerから取得）
from ..core.config.feature_manager import get_feature_categories, get_feature_names
from ..core.exceptions import DataProcessingError
from ..core.logger import CryptoBotLogger, get_logger

# 特徴量リスト（一元化対応）
OPTIMIZED_FEATURES = get_feature_names()

# 特徴量カテゴリ（一元化対応）
FEATURE_CATEGORIES = get_feature_categories()


class FeatureGenerator:
    """
    統合特徴量生成クラス - Phase 21統合版

    テクニカル指標、異常検知、特徴量サービス機能を
    1つのクラスに統合し、15特徴量生成を効率的に提供。

    主要機能:
    - テクニカル指標生成（9個）
    - 異常検知指標生成（1個）
    - 基本特徴量生成（2個）
    - ブレイクアウト指標生成（3個）
    - レジーム指標生成（3個）
    - 統合品質管理と15特徴量確認
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
        統合特徴量生成処理（15特徴量確認機能付き）

        Args:
            market_data: 市場データ（DataFrame または dict）

        Returns:
            15特徴量を含むDataFrame
        """
        try:
            # DataFrameに変換
            result_df = self._convert_to_dataframe(market_data)

            self.logger.info("特徴量生成開始 - 15特徴量システム")
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

            # 🎯 15特徴量完全確認・検証
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
                # 設定から優先順位付きタイムフレームを取得
                from ..core.config import get_data_config

                timeframe_keys = get_data_config("timeframes", ["4h", "15m"])  # 設定化対応
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

        self.computed_features.update(basic_features)
        self.logger.debug(f"基本特徴量生成完了: {len(basic_features)}個")
        return result_df

    def _generate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """テクニカル指標生成（6個）"""
        result_df = df.copy()

        # RSI 14期間
        result_df["rsi_14"] = self._calculate_rsi(result_df["close"])
        self.computed_features.add("rsi_14")

        # MACD（ラインのみ生成）
        macd_line, _ = self._calculate_macd(result_df["close"])
        result_df["macd"] = macd_line
        self.computed_features.add("macd")

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

        # Donchian Channel指標（3個）
        donchian_high, donchian_low, channel_position = self._calculate_donchian_channel(result_df)
        result_df["donchian_high_20"] = donchian_high
        result_df["donchian_low_20"] = donchian_low
        result_df["channel_position"] = channel_position
        self.computed_features.update(["donchian_high_20", "donchian_low_20", "channel_position"])

        # ADX指標（3個）
        adx, plus_di, minus_di = self._calculate_adx_indicators(result_df)
        result_df["adx_14"] = adx
        result_df["plus_di_14"] = plus_di
        result_df["minus_di_14"] = minus_di
        self.computed_features.update(["adx_14", "plus_di_14", "minus_di_14"])

        self.logger.debug("テクニカル指標生成完了: 11個")
        return result_df

    def _generate_anomaly_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """異常検知指標生成（1個）"""
        result_df = df.copy()

        # 出来高比率
        result_df["volume_ratio"] = self._calculate_volume_ratio(result_df["volume"])
        self.computed_features.add("volume_ratio")

        self.logger.debug("異常検知指標生成完了: 2個")
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

    # Phase 22: market_stress特徴量削除（15特徴量統一）
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

    def _calculate_donchian_channel(self, df: pd.DataFrame, period: int = 20) -> tuple:
        """
        Donchian Channel計算

        Args:
            df: OHLCV DataFrame
            period: 計算期間（デフォルト: 20）

        Returns:
            (donchian_high, donchian_low, channel_position)
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # 20期間の最高値・最安値
            donchian_high = high.rolling(window=period, min_periods=1).max()
            donchian_low = low.rolling(window=period, min_periods=1).min()

            # チャネル内位置計算（0-1）
            channel_width = donchian_high - donchian_low
            channel_position = (close - donchian_low) / (channel_width + 1e-8)

            # NaN値を適切な値で補完
            donchian_high = donchian_high.bfill().fillna(high.iloc[0])
            donchian_low = donchian_low.bfill().fillna(low.iloc[0])
            channel_position = channel_position.fillna(0.5)  # 中央値で補完

            return donchian_high, donchian_low, channel_position

        except Exception as e:
            self.logger.error(f"Donchian Channel計算エラー: {e}")
            # エラー時のフォールバック
            zeros = pd.Series(np.zeros(len(df)), index=df.index)
            half_ones = pd.Series(np.full(len(df), 0.5), index=df.index)
            return zeros, zeros, half_ones

    def _calculate_adx_indicators(self, df: pd.DataFrame, period: int = 14) -> tuple:
        """
        ADX指標計算（ADX、+DI、-DI）

        Args:
            df: OHLCV DataFrame
            period: 計算期間（デフォルト: 14）

        Returns:
            (adx, plus_di, minus_di)
        """
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            # True Range計算
            tr1 = high - low
            tr2 = np.abs(high - close.shift(1))
            tr3 = np.abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Directional Movement計算
            plus_dm = (high - high.shift(1)).where((high - high.shift(1)) > (low.shift(1) - low), 0)
            minus_dm = (low.shift(1) - low).where((low.shift(1) - low) > (high - high.shift(1)), 0)
            plus_dm = plus_dm.where(plus_dm > 0, 0)
            minus_dm = minus_dm.where(minus_dm > 0, 0)

            # Smoothed True Range と Directional Movement
            atr = tr.rolling(window=period, min_periods=1).mean()
            plus_dm_smooth = plus_dm.rolling(window=period, min_periods=1).mean()
            minus_dm_smooth = minus_dm.rolling(window=period, min_periods=1).mean()

            # Directional Indicators
            plus_di = 100 * plus_dm_smooth / (atr + 1e-8)
            minus_di = 100 * minus_dm_smooth / (atr + 1e-8)

            # Directional Index
            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-8)

            # ADX (Average Directional Index)
            adx = dx.rolling(window=period, min_periods=1).mean()

            # NaN値補完
            adx = adx.bfill().fillna(0)
            plus_di = plus_di.bfill().fillna(0)
            minus_di = minus_di.bfill().fillna(0)

            return adx, plus_di, minus_di

        except Exception as e:
            self.logger.error(f"ADX指標計算エラー: {e}")
            # エラー時のフォールバック
            zeros = pd.Series(np.zeros(len(df)), index=df.index)
            return zeros, zeros, zeros

    def _handle_nan_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """NaN値処理（統合版）"""
        for feature in self.computed_features:
            if feature in df.columns:
                df[feature] = df[feature].ffill().bfill().fillna(0)
        return df

    def _validate_feature_generation(self, df: pd.DataFrame) -> None:
        """15特徴量完全確認・検証"""
        generated_features = [col for col in OPTIMIZED_FEATURES if col in df.columns]
        missing_features = [col for col in OPTIMIZED_FEATURES if col not in df.columns]

        # 🚨 統合ログ出力
        self.logger.info(
            f"特徴量生成完了 - 総数: {len(generated_features)}/{len(OPTIMIZED_FEATURES)}個",
            extra_data={
                "basic_features": len([f for f in ["close", "volume"] if f in df.columns]),
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
                "anomaly_features": len([f for f in ["volume_ratio"] if f in df.columns]),
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
            self.logger.info("✅ 15特徴量完全生成成功")

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
                "rsi_14": "RSI（オーバーボート・ソールド判定）",
                "macd": "MACD（トレンド転換シグナル）",
                "atr_14": "ATR（ボラティリティ測定）",
                "bb_position": "ボリンジャーバンド位置（価格位置）",
                "ema_20": "EMA短期（短期トレンド）",
                "ema_50": "EMA中期（中期トレンド）",
                "donchian_high_20": "Donchian Channel上限（20期間最高値）",
                "donchian_low_20": "Donchian Channel下限（20期間最安値）",
                "channel_position": "チャネル内位置（0-1正規化位置）",
                "adx_14": "ADX（トレンド強度指標）",
                "plus_di_14": "+DI（上昇トレンド方向性）",
                "minus_di_14": "-DI（下降トレンド方向性）",
                "volume_ratio": "出来高比率（出来高異常検知）",
            },
        }


# エクスポートリスト
__all__ = [
    "FeatureGenerator",
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]
