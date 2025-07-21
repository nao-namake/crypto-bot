"""
TechnicalFeatureEngine - Phase B2.2 テクニカル指標バッチ処理

現状問題解決:
- RSI・SMA・EMA等の個別計算 → 同一指標の複数期間一括計算
- 151回のdf[column] = value → バッチ化・一括統合
- 処理時間・メモリ効率大幅改善

改善例:
Before: df["rsi_7"] = calc_rsi(7); df["rsi_14"] = calc_rsi(14); ... (3回計算)
After:  rsi_batch = calc_rsi_batch([7, 14, 21]) → 1回計算で3特徴量生成
"""

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .batch_calculator import BatchFeatureCalculator, FeatureBatch

logger = logging.getLogger(__name__)


class TechnicalFeatureEngine:
    """
    テクニカル指標バッチ処理エンジン - Phase B2.2

    効率化ポイント:
    - 同一指標・複数期間の一括計算
    - NumPy vectorized処理活用
    - メモリ使用量最適化
    """

    def __init__(
        self, config: Dict[str, Any], batch_calculator: BatchFeatureCalculator
    ):
        self.config = config
        self.batch_calc = batch_calculator
        self.ml_config = config.get("ml", {})

        # IndicatorCalculator互換性確保
        try:
            from crypto_bot.indicator.calculator import IndicatorCalculator

            self.ind_calc = IndicatorCalculator()
            self.indicator_available = True
        except ImportError:
            logger.warning(
                "⚠️ IndicatorCalculator not available, using built-in methods"
            )
            self.ind_calc = None
            self.indicator_available = False

        # テクニカル指標設定
        self.technical_configs = self._parse_technical_features()

        logger.info("🔧 TechnicalFeatureEngine initialized for batch processing")

    def _parse_technical_features(self) -> Dict[str, Dict]:
        """設定からテクニカル指標設定を解析"""
        extra_features = self.ml_config.get("extra_features", [])
        configs = {
            "rsi": {"periods": [], "single_calls": []},
            "sma": {"periods": [], "single_calls": []},
            "ema": {"periods": [], "single_calls": []},
            "atr": {"periods": [], "single_calls": []},
            "volume_zscore": {"periods": [], "single_calls": []},
            "macd": {"enabled": False},
            "stoch": {"enabled": False},
            "adx": {"enabled": False},
        }

        for feat in extra_features:
            feat_lc = feat.lower()

            # アンダースコア分割で期間抽出
            if "_" in feat_lc:
                base, _, param = feat_lc.partition("_")

                # 数値期間の場合
                if param.isdigit():
                    period = int(param)
                    if base in configs:
                        configs[base]["periods"].append(period)
                # 複合パラメータの場合
                elif base == "volume" and "zscore" in param:
                    period_str = param.split("_")[-1] if "_" in param else "14"
                    period = int(period_str) if period_str.isdigit() else 14
                    configs["volume_zscore"]["periods"].append(period)
            else:
                # 期間指定なしの場合（デフォルト期間群を使用）
                if feat_lc == "rsi":
                    configs["rsi"]["periods"].extend([7, 14, 21])
                elif feat_lc == "sma":
                    configs["sma"]["periods"].extend([10, 20, 50, 100, 200])
                elif feat_lc == "ema":
                    configs["ema"]["periods"].extend([10, 12, 26, 50, 100])
                elif feat_lc in ["macd", "stoch", "adx"]:
                    configs[feat_lc]["enabled"] = True

        # 重複除去・ソート
        for indicator in ["rsi", "sma", "ema", "atr", "volume_zscore"]:
            if configs[indicator]["periods"]:
                configs[indicator]["periods"] = sorted(
                    list(set(configs[indicator]["periods"]))
                )

        return configs

    def calculate_rsi_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """RSI指標バッチ計算"""
        periods = self.technical_configs["rsi"]["periods"]
        if not periods:
            return FeatureBatch("rsi_batch", {})

        try:
            rsi_features = {}
            close_series = df["close"]

            # 各期間のRSI計算
            for period in periods:
                if self.indicator_available and self.ind_calc:
                    # IndicatorCalculator使用
                    rsi_values = self.ind_calc.rsi(close_series, window=period)
                else:
                    # 内蔵RSI計算
                    rsi_values = self._calculate_rsi_builtin(close_series, period)

                rsi_features[f"rsi_{period}"] = rsi_values

            logger.debug(f"✅ RSI batch: {len(rsi_features)} indicators ({periods})")
            return self.batch_calc.create_feature_batch(
                "rsi_batch", rsi_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ RSI batch calculation failed: {e}")
            return FeatureBatch("rsi_batch", {})

    def calculate_sma_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """SMA指標バッチ計算"""
        periods = self.technical_configs["sma"]["periods"]
        if not periods:
            return FeatureBatch("sma_batch", {})

        try:
            sma_features = {}
            close_series = df["close"]

            # 各期間のSMA計算（vectorized処理）
            for period in periods:
                if self.indicator_available and self.ind_calc:
                    sma_values = self.ind_calc.sma(close_series, window=period)
                else:
                    sma_values = close_series.rolling(window=period).mean()

                sma_features[f"sma_{period}"] = sma_values

            logger.debug(f"✅ SMA batch: {len(sma_features)} indicators ({periods})")
            return self.batch_calc.create_feature_batch(
                "sma_batch", sma_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ SMA batch calculation failed: {e}")
            return FeatureBatch("sma_batch", {})

    def calculate_ema_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """EMA指標バッチ計算"""
        periods = self.technical_configs["ema"]["periods"]
        if not periods:
            return FeatureBatch("ema_batch", {})

        try:
            ema_features = {}
            close_series = df["close"]

            # 各期間のEMA計算
            for period in periods:
                if self.indicator_available and self.ind_calc:
                    ema_values = self.ind_calc.ema(close_series, window=period)
                else:
                    ema_values = close_series.ewm(span=period, adjust=False).mean()

                ema_features[f"ema_{period}"] = ema_values

            logger.debug(f"✅ EMA batch: {len(ema_features)} indicators ({periods})")
            return self.batch_calc.create_feature_batch(
                "ema_batch", ema_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ EMA batch calculation failed: {e}")
            return FeatureBatch("ema_batch", {})

    def calculate_atr_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """ATR指標バッチ計算"""
        periods = self.technical_configs["atr"]["periods"]

        # 基本ATR (feat_period)
        base_period = self.ml_config.get("feat_period", 14)
        all_periods = list(set(periods + [base_period]))

        try:
            atr_features = {}

            # 各期間のATR計算
            for period in all_periods:
                if self.indicator_available and self.ind_calc:
                    atr_values = self.ind_calc.atr(df, window=period)
                    if isinstance(atr_values, pd.DataFrame):
                        atr_values = atr_values.iloc[:, 0]  # 最初の列を使用
                else:
                    atr_values = self._calculate_atr_builtin(df, period)

                # 基本ATRは特別な名前
                if period == base_period:
                    atr_features[f"ATR_{period}"] = atr_values
                atr_features[f"atr_{period}"] = atr_values

            logger.debug(
                f"✅ ATR batch: {len(atr_features)} indicators ({all_periods})"
            )
            return self.batch_calc.create_feature_batch(
                "atr_batch", atr_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ ATR batch calculation failed: {e}")
            return FeatureBatch("atr_batch", {})

    def calculate_volume_zscore_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """Volume Z-Score バッチ計算"""
        periods = self.technical_configs["volume_zscore"]["periods"]
        if not periods:
            return FeatureBatch("volume_zscore_batch", {})

        try:
            zscore_features = {}
            volume_series = df["volume"]

            # 各期間のVolume Z-Score計算
            for period in periods:
                vol_mean = volume_series.rolling(window=period).mean()
                vol_std = volume_series.rolling(window=period).std()
                zscore = ((volume_series - vol_mean) / vol_std).fillna(0)

                zscore_features[f"volume_zscore_{period}"] = zscore

            logger.debug(
                f"✅ Volume Z-Score batch: {len(zscore_features)} indicators ({periods})"
            )
            return self.batch_calc.create_feature_batch(
                "volume_zscore_batch", zscore_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ Volume Z-Score batch calculation failed: {e}")
            return FeatureBatch("volume_zscore_batch", {})

    def calculate_complex_indicators_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """複合指標バッチ計算 (MACD, Stochastic, ADX)"""
        complex_features = {}

        try:
            # MACD計算
            if self.technical_configs["macd"]["enabled"]:
                if self.indicator_available and self.ind_calc:
                    macd_df = self.ind_calc.macd(df["close"])
                    if isinstance(macd_df, pd.DataFrame):
                        # MACD列名を標準化
                        macd_cols = macd_df.columns
                        if "MACD_12_26_9" in macd_cols:
                            complex_features["macd"] = macd_df["MACD_12_26_9"]
                        if "MACDs_12_26_9" in macd_cols:
                            complex_features["macd_signal"] = macd_df["MACDs_12_26_9"]
                        if "MACDh_12_26_9" in macd_cols:
                            complex_features["macd_hist"] = macd_df["MACDh_12_26_9"]
                else:
                    # 内蔵MACD計算
                    macd_line, macd_signal, macd_hist = self._calculate_macd_builtin(
                        df["close"]
                    )
                    complex_features.update(
                        {
                            "macd": macd_line,
                            "macd_signal": macd_signal,
                            "macd_hist": macd_hist,
                        }
                    )

            # Stochastic計算
            if self.technical_configs["stoch"]["enabled"]:
                if self.indicator_available and self.ind_calc:
                    # IndicatorCalculatorのstochastic使用
                    try:
                        stoch_result = self.ind_calc.stochastic(df)

                        # 型安全性チェック・変換
                        if isinstance(stoch_result, tuple) and len(stoch_result) == 2:
                            stoch_k, stoch_d = stoch_result
                        elif (
                            hasattr(stoch_result, "__iter__")
                            and len(list(stoch_result)) == 2
                        ):
                            stoch_k, stoch_d = list(stoch_result)
                        else:
                            # フォールバック: 内蔵計算使用
                            stoch_k, stoch_d = self._calculate_stochastic_builtin(df)

                        # Series型に変換・検証
                        if not isinstance(stoch_k, pd.Series):
                            if hasattr(stoch_k, "squeeze"):
                                stoch_k = stoch_k.squeeze()
                            else:
                                stoch_k, stoch_d = self._calculate_stochastic_builtin(
                                    df
                                )

                        if not isinstance(stoch_d, pd.Series):
                            if hasattr(stoch_d, "squeeze"):
                                stoch_d = stoch_d.squeeze()
                            else:
                                stoch_k, stoch_d = self._calculate_stochastic_builtin(
                                    df
                                )

                        complex_features.update(
                            {"stoch_k": stoch_k, "stoch_d": stoch_d}
                        )

                    except (AttributeError, TypeError, ValueError) as e:
                        logger.warning(
                            f"⚠️ IndicatorCalculator stochastic failed: {e}, using builtin"
                        )
                        # stochasticメソッドが存在しない場合は内蔵計算
                        stoch_k, stoch_d = self._calculate_stochastic_builtin(df)
                        complex_features.update(
                            {"stoch_k": stoch_k, "stoch_d": stoch_d}
                        )
                else:
                    stoch_k, stoch_d = self._calculate_stochastic_builtin(df)
                    complex_features.update({"stoch_k": stoch_k, "stoch_d": stoch_d})

            # ADX計算
            if self.technical_configs["adx"]["enabled"]:
                if self.indicator_available and self.ind_calc:
                    try:
                        adx_result = self.ind_calc.adx(df)

                        # 型安全性チェック・変換
                        if isinstance(adx_result, pd.DataFrame):
                            # DataFrameの場合、ADXカラムを探す
                            if "ADX_14" in adx_result.columns:
                                adx = adx_result["ADX_14"]
                            elif "ADX" in adx_result.columns:
                                adx = adx_result["ADX"]
                            else:
                                # 最初の列を使用
                                adx = adx_result.iloc[:, 0]
                        elif isinstance(adx_result, pd.Series):
                            adx = adx_result
                        else:
                            # その他の型の場合はフォールバック
                            adx = self._calculate_adx_builtin(df)

                        # Series型確認
                        if not isinstance(adx, pd.Series):
                            if hasattr(adx, "squeeze"):
                                adx = adx.squeeze()
                            else:
                                adx = self._calculate_adx_builtin(df)

                        complex_features["adx"] = adx

                    except (AttributeError, TypeError, ValueError) as e:
                        logger.warning(
                            f"⚠️ IndicatorCalculator ADX failed: {e}, using builtin"
                        )
                        adx = self._calculate_adx_builtin(df)
                        complex_features["adx"] = adx
                else:
                    adx = self._calculate_adx_builtin(df)
                    complex_features["adx"] = adx

            logger.debug(
                f"✅ Complex indicators batch: {len(complex_features)} indicators"
            )
            return self.batch_calc.create_feature_batch(
                "complex_batch", complex_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ Complex indicators batch calculation failed: {e}")
            return FeatureBatch("complex_batch", {})

    def calculate_lag_rolling_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """Lag・Rolling統計バッチ計算"""
        try:
            lag_roll_features = {}

            # Lag特徴量
            lags = self.ml_config.get("lags", [1, 2, 3])
            close_series = df["close"]

            for lag in lags:
                lag_roll_features[f"close_lag_{lag}"] = close_series.shift(lag)

            # Rolling統計
            rolling_window = self.ml_config.get("rolling_window", 14)
            lag_roll_features[f"close_mean_{rolling_window}"] = close_series.rolling(
                rolling_window
            ).mean()
            lag_roll_features[f"close_std_{rolling_window}"] = close_series.rolling(
                rolling_window
            ).std()

            logger.debug(f"✅ Lag/Rolling batch: {len(lag_roll_features)} features")
            return self.batch_calc.create_feature_batch(
                "lag_roll_batch", lag_roll_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ Lag/Rolling batch calculation failed: {e}")
            return FeatureBatch("lag_roll_batch", {})

    def calculate_all_technical_batches(self, df: pd.DataFrame) -> List[FeatureBatch]:
        """全テクニカル指標バッチ計算"""
        batches = []

        # 各バッチ計算
        batches.append(self.calculate_lag_rolling_batch(df))  # 基本統計
        batches.append(self.calculate_rsi_batch(df))  # RSI
        batches.append(self.calculate_sma_batch(df))  # SMA
        batches.append(self.calculate_ema_batch(df))  # EMA
        batches.append(self.calculate_atr_batch(df))  # ATR
        batches.append(self.calculate_volume_zscore_batch(df))  # Volume指標
        batches.append(self.calculate_complex_indicators_batch(df))  # 複合指標

        # 空でないバッチのみを返す
        non_empty_batches = [batch for batch in batches if len(batch) > 0]

        total_features = sum(len(batch) for batch in non_empty_batches)
        logger.info(
            f"🔄 Technical batches completed: {len(non_empty_batches)} batches, {total_features} features"
        )

        return non_empty_batches

    # 内蔵計算メソッド（IndicatorCalculator不使用時のフォールバック）

    def _calculate_rsi_builtin(self, series: pd.Series, period: int) -> pd.Series:
        """内蔵RSI計算"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)  # デフォルト中立値

    def _calculate_atr_builtin(self, df: pd.DataFrame, period: int) -> pd.Series:
        """内蔵ATR計算"""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())

        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = pd.Series(true_range).rolling(window=period).mean()
        return atr.fillna(0)

    def _calculate_macd_builtin(
        self, series: pd.Series
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """内蔵MACD計算"""
        ema12 = series.ewm(span=12, adjust=False).mean()
        ema26 = series.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def _calculate_stochastic_builtin(
        self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3
    ) -> Tuple[pd.Series, pd.Series]:
        """内蔵Stochastic計算"""
        high_max = df["high"].rolling(window=k_period).max()
        low_min = df["low"].rolling(window=k_period).min()
        k_percent = ((df["close"] - low_min) / (high_max - low_min)) * 100
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent.fillna(50), d_percent.fillna(50)

    def _calculate_adx_builtin(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """内蔵ADX計算（簡略版）"""
        # 簡略ADX（DX基準）
        high_diff = df["high"].diff()
        low_diff = -df["low"].diff()

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        tr = self._calculate_atr_builtin(df, 1)
        plus_di = 100 * (
            pd.Series(plus_dm).rolling(window=period).sum()
            / tr.rolling(window=period).sum()
        )
        minus_di = 100 * (
            pd.Series(minus_dm).rolling(window=period).sum()
            / tr.rolling(window=period).sum()
        )

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        return adx.fillna(25)  # デフォルト中立値


def create_technical_engine(
    config: Dict[str, Any], batch_calculator: BatchFeatureCalculator
) -> TechnicalFeatureEngine:
    """TechnicalFeatureEngine ファクトリー関数"""
    return TechnicalFeatureEngine(config, batch_calculator)
