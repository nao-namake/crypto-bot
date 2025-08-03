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
        self, config: Dict[str, Any], batch_calculator: BatchFeatureCalculator = None
    ):
        self.config = config

        # BatchFeatureCalculatorが提供されていない場合は自動作成
        if batch_calculator is None:
            logger.info(
                "🔧 TechnicalFeatureEngine: BatchFeatureCalculator auto-created"
            )
            batch_calculator = BatchFeatureCalculator(config)

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
        """設定からテクニカル指標設定を解析 - production.yml完全対応版"""
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

        # 🔍 設定読み込み詳細デバッグ（97特徴量問題解決版）
        logger.info("🔧 TechnicalFeatureEngine config received:")
        logger.info(f"🔧   Config keys: {list(self.config.keys())}")
        logger.info(f"🔧   ML config keys: {list(self.ml_config.keys())}")
        logger.info(f"🔧   Extra features raw content: {extra_features}")
        logger.info(f"🔧   Extra features type: {type(extra_features)}")
        logger.info(f"🔧   Total extra features count: {len(extra_features)}")

        # 特徴量リストの詳細確認
        if len(extra_features) > 0:
            logger.info(f"🔧   First 10 features: {extra_features[:10]}")
            logger.info(
                f"🔧   EMA features in list: {[f for f in extra_features if 'ema_' in f.lower()]}"
            )
            logger.info(
                f"🔧   ATR features in list: {[f for f in extra_features if 'atr_' in f.lower()]}"
            )
        else:
            logger.warning("⚠️   WARNING: No extra features found in configuration!")

        logger.info(
            f"🔧 Parsing {len(extra_features)} extra features from configuration"
        )

        # 設定ファイル読み込みの検証
        import yaml

        try:
            with open(
                "/Users/nao/Desktop/bot/config/production/production.yml",
                "r",
                encoding="utf-8",
            ) as f:
                raw_config = yaml.safe_load(f)
            raw_extra_features = raw_config.get("ml", {}).get("extra_features", [])
            logger.info(
                f"🔍 RAW production.yml extra_features count: {len(raw_extra_features)}"
            )
            logger.info(
                f"🔍 RAW EMA features: {[f for f in raw_extra_features if 'ema_' in f.lower()]}"
            )
            logger.info(
                f"🔍 RAW ATR features: {[f for f in raw_extra_features if 'atr_' in f.lower()]}"
            )

            if len(raw_extra_features) != len(extra_features):
                logger.error("❌ CRITICAL: Configuration mismatch detected!")
                logger.error(f"   RAW file: {len(raw_extra_features)} features")
                logger.error(f"   Loaded config: {len(extra_features)} features")
                logger.error(f"   First 10 RAW features: {raw_extra_features[:10]}")
        except Exception as e:
            logger.error(f"❌ Failed to read raw production.yml: {e}")

        # Production.ymlからEMA系特徴量を直接検索
        if hasattr(self, "config") and "ml" in self.config:
            ml_section = self.config["ml"]
            prod_extra_features = ml_section.get("extra_features", [])
            logger.info(
                f"🔍 Object config extra_features count: {len(prod_extra_features)}"
            )
            logger.info(
                f"🔍 Object config EMA features: {[f for f in prod_extra_features if 'ema_' in f.lower()]}"
            )
            logger.info(
                f"🔍 Object config ATR features: {[f for f in prod_extra_features if 'atr_' in f.lower()]}"
            )
        else:
            logger.warning("❌ Cannot access config directly")

        for feat in extra_features:
            feat_lc = feat.lower()
            logger.info(f"  🔍 Processing feature: '{feat}' -> '{feat_lc}'")

            # EMA期間抽出 (ema_5, ema_10, ema_20, ema_50, ema_100, ema_200)
            if feat_lc.startswith("ema_"):
                logger.info(f"    ✅ EMA feature detected: {feat_lc}")
                parts = feat_lc.split("_")
                logger.info(f"    🔍 EMA parts: {parts}")
                if len(parts) >= 2 and parts[1].isdigit():
                    period = int(parts[1])
                    configs["ema"]["periods"].append(period)
                    logger.info(f"    ✅ EMA period added: {period}")
                else:
                    logger.warning(f"    ❌ EMA parsing failed for {feat_lc}")

            # ATR期間抽出 (atr_14)
            elif feat_lc.startswith("atr_"):
                logger.info(f"    ✅ ATR feature detected: {feat_lc}")
                parts = feat_lc.split("_")
                logger.info(f"    🔍 ATR parts: {parts}")
                if len(parts) >= 2 and parts[1].isdigit():
                    period = int(parts[1])
                    configs["atr"]["periods"].append(period)
                    logger.info(f"    ✅ ATR period added: {period}")
                else:
                    logger.warning(f"    ❌ ATR parsing failed for {feat_lc}")

            # RSI期間抽出 (rsi_14)
            elif feat_lc.startswith("rsi_") and not feat_lc.endswith(
                ("oversold", "overbought")
            ):
                logger.info(f"    ✅ RSI feature detected: {feat_lc}")
                parts = feat_lc.split("_")
                if len(parts) >= 2 and parts[1].isdigit():
                    period = int(parts[1])
                    configs["rsi"]["periods"].append(period)
                    logger.info(f"    ✅ RSI period added: {period}")
                else:
                    logger.warning(f"    ❌ RSI parsing failed for {feat_lc}")

            # SMA期間抽出
            elif feat_lc.startswith("sma_"):
                parts = feat_lc.split("_")
                if len(parts) >= 2 and parts[1].isdigit():
                    period = int(parts[1])
                    configs["sma"]["periods"].append(period)
                    logger.debug(f"  ✅ SMA period: {period}")

            # アンダースコア分割で期間抽出（従来ロジック保持）
            elif "_" in feat_lc:
                base, _, param = feat_lc.partition("_")

                # 数値期間の場合
                if param.isdigit():
                    period = int(param)
                    if base in configs and "periods" in configs[base]:
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
                elif "stoch" in feat_lc:
                    configs["stoch"]["enabled"] = True
                elif "adx" in feat_lc:
                    configs["adx"]["enabled"] = True

        # 重複除去・ソート
        for indicator in ["rsi", "sma", "ema", "atr", "volume_zscore"]:
            if configs[indicator]["periods"]:
                configs[indicator]["periods"] = sorted(
                    list(set(configs[indicator]["periods"]))
                )

        # Production.yml特徴量から親指標を有効化
        # stoch_k, stoch_d などが含まれていればstochを有効化
        if any("stoch" in feat.lower() for feat in extra_features):
            configs["stoch"]["enabled"] = True
            logger.debug("  ✅ Stochastic enabled")

        # adx_14などが含まれていればadxを有効化
        if any("adx" in feat.lower() for feat in extra_features):
            configs["adx"]["enabled"] = True
            logger.debug("  ✅ ADX enabled")

        # macd関連も同様に
        if any("macd" in feat.lower() for feat in extra_features):
            configs["macd"]["enabled"] = True
            logger.debug("  ✅ MACD enabled")

        # Production.yml対応結果ログ
        logger.info("🎯 Technical features parsing completed:")
        logger.info(f"  EMA periods: {configs['ema']['periods']}")
        logger.info(f"  ATR periods: {configs['atr']['periods']}")
        logger.info(f"  RSI periods: {configs['rsi']['periods']}")
        logger.info(f"  MACD enabled: {configs['macd']['enabled']}")
        logger.info(f"  Stochastic enabled: {configs['stoch']['enabled']}")
        logger.info(f"  ADX enabled: {configs['adx']['enabled']}")

        return configs

    def calculate_rsi_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """RSI指標バッチ計算"""
        periods = self.technical_configs["rsi"]["periods"]
        logger.info(f"🔍 RSI batch calculation: periods={periods}")
        if not periods:
            logger.warning("⚠️ No RSI periods configured")
            return FeatureBatch("rsi_batch", {})

        try:
            rsi_features = {}
            close_series = df["close"]
            logger.info(f"🔍 RSI calculation: close_series length={len(close_series)}")

            # 各期間のRSI計算
            for period in periods:
                try:
                    if len(close_series) < period + 1:
                        logger.warning(
                            f"  ⚠️ Insufficient data for RSI_{period}: {len(close_series)} < {period + 1}"
                        )
                        continue

                    if self.indicator_available and self.ind_calc:
                        # IndicatorCalculator使用
                        logger.debug(f"  Using IndicatorCalculator for RSI_{period}")
                        rsi_values = self.ind_calc.rsi(close_series, window=period)
                    else:
                        # 内蔵RSI計算
                        logger.debug(f"  Using builtin calculation for RSI_{period}")
                        rsi_values = self._calculate_rsi_builtin(close_series, period)

                    # None または 空の結果チェック
                    if rsi_values is None:
                        logger.warning(
                            f"  ⚠️ RSI_{period} returned None, using builtin fallback"
                        )
                        rsi_values = self._calculate_rsi_builtin(close_series, period)

                    # Series型確認とNaN値処理
                    if rsi_values is not None and isinstance(rsi_values, pd.Series):
                        rsi_features[f"rsi_{period}"] = rsi_values
                        logger.debug(f"  ✅ RSI_{period} calculated successfully")
                    else:
                        logger.warning(
                            f"  ⚠️ RSI_{period} invalid result: {type(rsi_values)}"
                        )

                except Exception as e:
                    logger.error(f"  ❌ RSI_{period} calculation failed: {e}")
                    import traceback

                    traceback.print_exc()

            # RSI oversold/overbought特徴量を追加
            if "rsi_14" in rsi_features and rsi_features["rsi_14"] is not None:
                rsi_14 = rsi_features["rsi_14"]
                # Series型チェックとNaN値処理
                if isinstance(rsi_14, pd.Series):
                    rsi_features["rsi_oversold"] = (rsi_14 < 30).astype(int)
                    rsi_features["rsi_overbought"] = (rsi_14 > 70).astype(int)
                    logger.debug("  ✅ RSI oversold/overbought features added")
                else:
                    logger.warning(f"  ⚠️ RSI_14 is not a Series: {type(rsi_14)}")

            logger.info(
                f"✅ RSI batch: {len(rsi_features)} indicators ({list(rsi_features.keys())})"
            )
            return self.batch_calc.create_feature_batch(
                "rsi_batch", rsi_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ RSI batch calculation failed: {e}")
            import traceback

            traceback.print_exc()
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

                # 小文字のatr_期間のみを使用（重複を避ける）
                atr_features[f"atr_{period}"] = atr_values

            logger.debug(
                f"✅ ATR batch: {len(atr_features)} indicators ({all_periods})"
            )
            return self.batch_calc.create_feature_batch(
                "atr_batch", atr_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ ATR batch calculation failed: {e}")
            # Phase H.23.6: エラー時でも緊急ATR値を提供
            emergency_features = {}
            try:
                # 緊急フォールバック: 全期間に対して価格の2%を設定
                logger.info("🚨 Generating emergency ATR values (2% of price)")
                emergency_atr = df["close"] * 0.02

                for period in all_periods:
                    if period == self.ml_config.get("feat_period", 14):
                        emergency_features[f"ATR_{period}"] = emergency_atr
                    emergency_features[f"atr_{period}"] = emergency_atr

                logger.warning(
                    f"⚠️ Using emergency ATR for {len(emergency_features)} features"
                )
                return FeatureBatch("atr_batch", emergency_features, df.index)
            except Exception as emergency_error:
                logger.error(f"❌ Emergency ATR generation failed: {emergency_error}")
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

                # MACD cross特徴量を追加
                if "macd" in complex_features and "macd_signal" in complex_features:
                    macd = complex_features["macd"]
                    signal = complex_features["macd_signal"]
                    # クロスの検出
                    macd_above = macd > signal
                    macd_below = macd < signal
                    complex_features["macd_cross_up"] = (
                        macd_above & macd_below.shift(1)
                    ).astype(int)
                    complex_features["macd_cross_down"] = (
                        macd_below & macd_above.shift(1)
                    ).astype(int)

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

            # Stochastic oversold/overbought特徴量を追加
            if "stoch_k" in complex_features:
                stoch_k = complex_features["stoch_k"]
                complex_features["stoch_oversold"] = (stoch_k < 20).astype(int)
                complex_features["stoch_overbought"] = (stoch_k > 80).astype(int)

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

                        complex_features["adx_14"] = adx

                    except (AttributeError, TypeError, ValueError) as e:
                        logger.warning(
                            f"⚠️ IndicatorCalculator ADX failed: {e}, using builtin"
                        )
                        adx = self._calculate_adx_builtin(df)
                        complex_features["adx_14"] = adx
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

    def calculate_missing_features_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """Phase 2: 不足している97特徴量を計算"""
        try:
            missing_features = {}

            # データフレームの列をチェック
            has_high = "high" in df.columns
            has_low = "low" in df.columns
            has_volume = "volume" in df.columns
            has_open = "open" in df.columns

            # 基本OHLCV特徴量（存在する場合のみ）
            if has_open:
                missing_features["open"] = df["open"]
            if has_high:
                missing_features["high"] = df["high"]
            if has_low:
                missing_features["low"] = df["low"]
            if has_volume:
                missing_features["volume"] = df["volume"]

            # ボリンジャーバンド
            if self.indicator_available and self.ind_calc:
                bb_result = self.ind_calc.bollinger_bands(df["close"])
                if isinstance(bb_result, pd.DataFrame):
                    # BBL_20_2.0 -> bb_lower のようにマッピング
                    if "BBL_20_2.0" in bb_result.columns:
                        missing_features["bb_lower"] = bb_result["BBL_20_2.0"]
                    if "BBM_20_2.0" in bb_result.columns:
                        missing_features["bb_middle"] = bb_result["BBM_20_2.0"]
                    if "BBU_20_2.0" in bb_result.columns:
                        missing_features["bb_upper"] = bb_result["BBU_20_2.0"]
                    if "BBB_20_2.0" in bb_result.columns:
                        missing_features["bb_position"] = bb_result["BBB_20_2.0"]
                    if "BBW_20_2.0" in bb_result.columns:
                        missing_features["bb_width"] = bb_result["BBW_20_2.0"]
                    else:
                        # BBWが無い場合は計算する
                        if (
                            "BBU_20_2.0" in bb_result.columns
                            and "BBL_20_2.0" in bb_result.columns
                            and "BBM_20_2.0" in bb_result.columns
                        ):
                            missing_features["bb_width"] = (
                                bb_result["BBU_20_2.0"] - bb_result["BBL_20_2.0"]
                            ) / bb_result["BBM_20_2.0"]
            else:
                # 内蔵計算
                sma_20 = df["close"].rolling(window=20).mean()
                std_20 = df["close"].rolling(window=20).std()
                missing_features["bb_upper"] = sma_20 + (std_20 * 2)
                missing_features["bb_middle"] = sma_20
                missing_features["bb_lower"] = sma_20 - (std_20 * 2)
                missing_features["bb_width"] = (
                    missing_features["bb_upper"] - missing_features["bb_lower"]
                ) / sma_20
                missing_features["bb_position"] = (
                    df["close"] - missing_features["bb_lower"]
                ) / (missing_features["bb_upper"] - missing_features["bb_lower"] + 1e-8)

            # SMA変数を確実に定義
            if "sma_20" not in locals():
                sma_20 = df["close"].rolling(window=20).mean()
            if "std_20" not in locals():
                std_20 = df["close"].rolling(window=20).std()

            # ボリンジャーバンドスクイーズ
            missing_features["bb_squeeze"] = (
                missing_features.get("bb_width", std_20 * 4 / sma_20) < 0.1
            ).astype(int)

            # 価格位置特徴量
            missing_features["price_position_20"] = (
                df["close"] - df["close"].rolling(20).min()
            ) / (df["close"].rolling(20).max() - df["close"].rolling(20).min() + 1e-8)
            missing_features["price_position_50"] = (
                df["close"] - df["close"].rolling(50).min()
            ) / (df["close"].rolling(50).max() - df["close"].rolling(50).min() + 1e-8)
            missing_features["price_vs_sma20"] = (df["close"] - sma_20) / sma_20
            # intraday_position（high, lowが必要）
            if has_high and has_low:
                missing_features["intraday_position"] = (df["close"] - df["low"]) / (
                    df["high"] - df["low"] + 1e-8
                )

            # リターン特徴量
            for period in [1, 2, 3, 5, 10]:
                missing_features[f"returns_{period}"] = df["close"].pct_change(period)
                missing_features[f"log_returns_{period}"] = np.log(
                    df["close"] / df["close"].shift(period)
                )

            # ボリュームラグ特徴量
            for lag in [1, 2, 3, 4, 5]:
                missing_features[f"volume_lag_{lag}"] = df["volume"].shift(lag)

            # 追加のラグ特徴量
            missing_features["close_lag_4"] = df["close"].shift(4)
            missing_features["close_lag_5"] = df["close"].shift(5)

            # ボラティリティ特徴量
            missing_features["volatility_20"] = (
                df["close"].pct_change().rolling(20).std()
            )
            missing_features["volatility_50"] = (
                df["close"].pct_change().rolling(50).std()
            )
            missing_features["volatility_ratio"] = missing_features["volatility_20"] / (
                missing_features["volatility_50"] + 1e-8
            )

            # high/lowが必要な特徴量
            if "high" in df.columns and "low" in df.columns:
                missing_features["high_low_ratio"] = df["high"] / df["low"]
                missing_features["true_range"] = np.maximum(
                    df["high"] - df["low"],
                    np.maximum(
                        np.abs(df["high"] - df["close"].shift()),
                        np.abs(df["low"] - df["close"].shift()),
                    ),
                )

            # ボリューム関連特徴量（volumeがある場合のみ）
            if "volume" in df.columns:
                missing_features["volume_sma_20"] = df["volume"].rolling(20).mean()
                missing_features["volume_ratio"] = df["volume"] / (
                    missing_features["volume_sma_20"] + 1e-8
                )
                missing_features["volume_trend"] = missing_features[
                    "volume_sma_20"
                ].pct_change(5)

            # VWAP（high, low, volumeがある場合のみ）
            if all(col in df.columns for col in ["high", "low", "volume"]):
                typical_price = (df["high"] + df["low"] + df["close"]) / 3
                missing_features["vwap"] = (typical_price * df["volume"]).cumsum() / df[
                    "volume"
                ].cumsum()
                missing_features["vwap_distance"] = (
                    df["close"] - missing_features["vwap"]
                ) / missing_features["vwap"]

            # その他のテクニカル指標
            if self.indicator_available and self.ind_calc:
                # Williams %R
                try:
                    missing_features["williams_r"] = self.ind_calc.williams_r(df)
                except Exception:
                    # フォールバック
                    highest_high = df["high"].rolling(14).max()
                    lowest_low = df["low"].rolling(14).min()
                    missing_features["williams_r"] = (
                        -100
                        * (highest_high - df["close"])
                        / (highest_high - lowest_low + 1e-8)
                    )

                # CCI
                try:
                    cci = self.ind_calc.cci(df, window=20)
                    if isinstance(cci, pd.Series):
                        missing_features["cci_20"] = cci
                except Exception:
                    # フォールバック
                    typical_price = (df["high"] + df["low"] + df["close"]) / 3
                    sma_tp = typical_price.rolling(20).mean()
                    mad = typical_price.rolling(20).apply(
                        lambda x: np.abs(x - x.mean()).mean()
                    )
                    missing_features["cci_20"] = (typical_price - sma_tp) / (
                        0.015 * mad + 1e-8
                    )
            else:
                # 内蔵計算
                # Williams %R（high, lowが必要）
                if "high" in df.columns and "low" in df.columns:
                    highest_high = df["high"].rolling(14).max()
                    lowest_low = df["low"].rolling(14).min()
                    missing_features["williams_r"] = (
                        -100
                        * (highest_high - df["close"])
                        / (highest_high - lowest_low + 1e-8)
                    )

                # CCI（high, lowが必要）
                if "high" in df.columns and "low" in df.columns:
                    typical_price = (df["high"] + df["low"] + df["close"]) / 3
                    sma_tp = typical_price.rolling(20).mean()
                    mad = typical_price.rolling(20).apply(
                        lambda x: np.abs(x - x.mean()).mean()
                    )
                    missing_features["cci_20"] = (typical_price - sma_tp) / (
                        0.015 * mad + 1e-8
                    )

            # OBV（On Balance Volume）（volumeがある場合のみ）
            if "volume" in df.columns:
                obv = (np.sign(df["close"].diff()) * df["volume"]).cumsum()
                missing_features["obv"] = obv
                missing_features["obv_sma"] = obv.rolling(20).mean()

            # AD Line（high, low, volumeがある場合のみ）
            if all(col in df.columns for col in ["high", "low", "volume"]):
                clv = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (
                    df["high"] - df["low"] + 1e-8
                )
                missing_features["ad_line"] = (clv * df["volume"]).cumsum()

                # CMF（Chaikin Money Flow）
                mf_multiplier = clv
                mf_volume = mf_multiplier * df["volume"]
                missing_features["cmf"] = (
                    mf_volume.rolling(20).sum() / df["volume"].rolling(20).sum()
                )

            # MFI（Money Flow Index）（high, low, volumeがある場合のみ）
            if all(col in df.columns for col in ["high", "low", "volume"]):
                typical_price = (df["high"] + df["low"] + df["close"]) / 3
                raw_money_flow = typical_price * df["volume"]
                positive_flow = (
                    raw_money_flow.where(typical_price > typical_price.shift(), 0)
                    .rolling(14)
                    .sum()
                )
                negative_flow = (
                    raw_money_flow.where(typical_price <= typical_price.shift(), 0)
                    .rolling(14)
                    .sum()
                )
                mfi_ratio = positive_flow / (negative_flow + 1e-8)
                missing_features["mfi"] = 100 - (100 / (1 + mfi_ratio))

            # ADXの要素（Plus/Minus DI）
            high_diff = df["high"].diff()
            low_diff = -df["low"].diff()
            plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
            minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
            tr = missing_features.get("true_range", self._calculate_atr_builtin(df, 1))
            missing_features["plus_di"] = 100 * (
                pd.Series(plus_dm).rolling(14).sum() / tr.rolling(14).sum()
            )
            missing_features["minus_di"] = 100 * (
                pd.Series(minus_dm).rolling(14).sum() / tr.rolling(14).sum()
            )

            # ADX（既に計算されているが、adx_14として保存）
            if "adx" in missing_features:
                missing_features["adx_14"] = missing_features.pop("adx")

            # トレンド関連特徴量
            missing_features["trend_strength"] = abs(
                missing_features.get("price_vs_sma20", 0)
            )
            missing_features["trend_direction"] = np.sign(df["close"] - sma_20)

            # Ultimate Oscillator（簡易版）
            bp = df["close"] - np.minimum(df["low"], df["close"].shift())
            tr = missing_features.get("true_range", self._calculate_atr_builtin(df, 1))
            avg7 = bp.rolling(7).sum() / tr.rolling(7).sum()
            avg14 = bp.rolling(14).sum() / tr.rolling(14).sum()
            avg28 = bp.rolling(28).sum() / tr.rolling(28).sum()
            missing_features["ultimate_oscillator"] = (
                100 * ((4 * avg7) + (2 * avg14) + avg28) / 7
            )

            # サポート・レジスタンス距離（簡易版）
            support = df["low"].rolling(20).min()
            resistance = df["high"].rolling(20).max()
            missing_features["support_distance"] = (df["close"] - support) / df["close"]
            missing_features["resistance_distance"] = (resistance - df["close"]) / df[
                "close"
            ]
            missing_features["support_strength"] = (df["close"] - support) / (
                resistance - support + 1e-8
            )

            # ブレイクアウト関連
            missing_features["volume_breakout"] = (
                df["volume"] > df["volume"].rolling(20).mean() * 2
            ).astype(int)
            missing_features["price_breakout_up"] = (
                df["close"] > df["high"].shift(1).rolling(20).max()
            ).astype(int)
            missing_features["price_breakout_down"] = (
                df["close"] < df["low"].shift(1).rolling(20).min()
            ).astype(int)

            # キャンドルパターン（簡易版）
            body = df["close"] - df["open"]
            upper_shadow = df["high"] - np.maximum(df["open"], df["close"])
            lower_shadow = np.minimum(df["open"], df["close"]) - df["low"]
            body_size = abs(body)

            missing_features["doji"] = (
                body_size < (df["high"] - df["low"]) * 0.1
            ).astype(int)
            missing_features["hammer"] = (
                (lower_shadow > body_size * 2) & (upper_shadow < body_size * 0.5)
            ).astype(int)
            missing_features["engulfing"] = (
                (body > 0) & (body.shift() < 0) & (abs(body) > abs(body.shift()))
            ).astype(int)
            missing_features["pinbar"] = (
                (upper_shadow > body_size * 2) | (lower_shadow > body_size * 2)
            ).astype(int)

            # 統計的特徴量
            missing_features["skewness_20"] = (
                df["close"].pct_change().rolling(20).apply(lambda x: x.skew())
            )
            missing_features["kurtosis_20"] = (
                df["close"].pct_change().rolling(20).apply(lambda x: x.kurt())
            )
            missing_features["zscore"] = (
                df["close"] - df["close"].rolling(20).mean()
            ) / df["close"].rolling(20).std()
            missing_features["mean_reversion_20"] = -missing_features["zscore"]
            missing_features["mean_reversion_50"] = (
                -(df["close"] - df["close"].rolling(50).mean())
                / df["close"].rolling(50).std()
            )

            # 時間関連特徴量（Phase H.29.7: index使用で常に生成）
            try:
                dt_index = None
                # timestamp列またはindexから時間情報取得
                if "timestamp" in df.columns:
                    dt_index = pd.to_datetime(df["timestamp"])
                elif df.index.name == "timestamp":
                    dt_index = pd.to_datetime(df.index)
                elif hasattr(df.index, "hour"):
                    dt_index = df.index
                else:
                    # デフォルト: 現在時刻ベースのダミー時間データを生成
                    base_time = pd.Timestamp("2024-01-01 00:00:00")
                    dt_index = pd.date_range(
                        start=base_time, periods=len(df), freq="1H"
                    )

                # dt_indexがSeriesの場合はDateTimeIndexに変換
                if isinstance(dt_index, pd.Series):
                    dt_index = pd.DatetimeIndex(dt_index)

                # 時間特徴量生成（安全にアクセス）
                if dt_index is not None and hasattr(dt_index, "hour"):
                    missing_features["hour"] = pd.Series(
                        dt_index.hour, index=df.index, name="hour"
                    )
                    missing_features["day_of_week"] = pd.Series(
                        dt_index.dayofweek, index=df.index, name="day_of_week"
                    )
                    missing_features["is_weekend"] = (dt_index.dayofweek >= 5).astype(
                        int
                    )
                    missing_features["is_asian_session"] = (
                        (dt_index.hour >= 0) & (dt_index.hour < 8)
                    ).astype(int)
                    missing_features["is_european_session"] = (
                        (dt_index.hour >= 8) & (dt_index.hour < 16)
                    ).astype(int)
                    missing_features["is_us_session"] = (
                        (dt_index.hour >= 16) & (dt_index.hour < 24)
                    ).astype(int)
                else:
                    # フォールバック: ダミー時間特徴量
                    logger.warning("⚠️ Creating dummy time features")
                    missing_features["hour"] = pd.Series(
                        12, index=df.index, name="hour"
                    )  # 正午固定
                    missing_features["day_of_week"] = pd.Series(
                        2, index=df.index, name="day_of_week"
                    )  # 火曜日固定
                    missing_features["is_weekend"] = pd.Series(
                        0, index=df.index
                    ).astype(int)
                    missing_features["is_asian_session"] = pd.Series(
                        0, index=df.index
                    ).astype(int)
                    missing_features["is_european_session"] = pd.Series(
                        1, index=df.index
                    ).astype(int)
                    missing_features["is_us_session"] = pd.Series(
                        0, index=df.index
                    ).astype(int)
            except Exception as time_error:
                logger.warning(
                    f"⚠️ Time features failed: {time_error}, using dummy values"
                )
                # 緊急フォールバック: ダミー時間特徴量
                missing_features["hour"] = pd.Series(12, index=df.index, name="hour")
                missing_features["day_of_week"] = pd.Series(
                    2, index=df.index, name="day_of_week"
                )
                missing_features["is_weekend"] = pd.Series(0, index=df.index).astype(
                    int
                )
                missing_features["is_asian_session"] = pd.Series(
                    0, index=df.index
                ).astype(int)
                missing_features["is_european_session"] = pd.Series(
                    1, index=df.index
                ).astype(int)
                missing_features["is_us_session"] = pd.Series(0, index=df.index).astype(
                    int
                )

            # 追加の指標
            missing_features["roc_10"] = df["close"].pct_change(10) * 100
            missing_features["roc_20"] = df["close"].pct_change(20) * 100

            # TRIX（簡易版）
            ema1 = df["close"].ewm(span=14, adjust=False).mean()
            ema2 = ema1.ewm(span=14, adjust=False).mean()
            ema3 = ema2.ewm(span=14, adjust=False).mean()
            missing_features["trix"] = ema3.pct_change() * 10000

            # Mass Index（簡易版）
            ema_hl = (df["high"] - df["low"]).ewm(span=9, adjust=False).mean()
            ema_ema_hl = ema_hl.ewm(span=9, adjust=False).mean()
            missing_features["mass_index"] = (ema_hl / ema_ema_hl).rolling(25).sum()

            # Keltner Channels
            kc_ema = df["close"].ewm(span=20, adjust=False).mean()
            kc_atr = missing_features.get("atr_14", self._calculate_atr_builtin(df, 14))
            missing_features["keltner_upper"] = kc_ema + (kc_atr * 2)
            missing_features["keltner_lower"] = kc_ema - (kc_atr * 2)

            # Donchian Channels
            missing_features["donchian_upper"] = df["high"].rolling(20).max()
            missing_features["donchian_lower"] = df["low"].rolling(20).min()

            # Ichimoku（簡易版）
            high_9 = df["high"].rolling(9).max()
            low_9 = df["low"].rolling(9).min()
            missing_features["ichimoku_conv"] = (high_9 + low_9) / 2

            high_26 = df["high"].rolling(26).max()
            low_26 = df["low"].rolling(26).min()
            missing_features["ichimoku_base"] = (high_26 + low_26) / 2

            # 効率性・品質指標
            missing_features["price_efficiency"] = abs(
                df["close"] - df["close"].shift(20)
            ) / (df["high"].rolling(20).max() - df["low"].rolling(20).min() + 1e-8)
            missing_features["trend_consistency"] = (
                df["close"].diff().rolling(20).apply(lambda x: (x > 0).sum() / len(x))
            )
            missing_features["volume_price_correlation"] = (
                df["close"].pct_change().rolling(20).corr(df["volume"].pct_change())
            )

            # レジーム判定（修正版）
            vol_20 = missing_features.get(
                "volatility_20", df["close"].pct_change().rolling(20).std()
            )
            # より適切な閾値とウィンドウサイズを使用
            if len(vol_20.dropna()) > 50:
                # 50期間の移動平均を基準に、より感度の高い閾値（1.2倍）を使用
                vol_avg = vol_20.rolling(50, min_periods=10).mean()
                missing_features["volatility_regime"] = (vol_20 > vol_avg * 1.2).astype(
                    int
                )
            else:
                # データが少ない場合は全データの75%パーセンタイルを基準に
                vol_threshold = vol_20.quantile(0.75)
                missing_features["volatility_regime"] = (vol_20 > vol_threshold).astype(
                    int
                )

            # モメンタム品質
            returns = df["close"].pct_change()
            missing_features["momentum_quality"] = returns.rolling(20).mean() / (
                returns.rolling(20).std() + 1e-8
            )

            # マーケットフェーズ
            sma_50 = df["close"].rolling(50).mean()
            sma_200 = df["close"].rolling(200).mean()
            phase = np.where(
                (df["close"] > sma_50) & (sma_50 > sma_200),
                1,  # 上昇トレンド
                np.where(
                    (df["close"] < sma_50) & (sma_50 < sma_200),
                    -1,  # 下降トレンド
                    0,  # レンジ
                ),
            )
            missing_features["market_phase"] = pd.Series(phase, index=df.index)

            # momentum_14（最後に追加）
            missing_features["momentum_14"] = df["close"] - df["close"].shift(14)

            # 97特徴量統一: close_std_10を追加（close_mean_10は削除）
            missing_features["close_mean_10"] = df["close"].rolling(10).mean()
            missing_features["close_std_10"] = df["close"].rolling(10).std()

            # Production.yml完全対応保証ロジック
            required_features = self.ml_config.get("extra_features", [])
            logger.info(
                f"🔍 Production.yml compliance check: {len(required_features)} required features"
            )

            guaranteed_count = 0
            for req_feat in required_features:
                if req_feat not in missing_features:
                    # 不足特徴量のフォールバック生成
                    if req_feat.startswith(("ema_", "sma_")):
                        # EMA/SMA系: 単純移動平均で代替
                        try:
                            period = int(req_feat.split("_")[1])
                            if req_feat.startswith("ema_"):
                                missing_features[req_feat] = (
                                    df["close"].ewm(span=period, adjust=False).mean()
                                )
                            else:
                                missing_features[req_feat] = (
                                    df["close"].rolling(period).mean()
                                )
                            guaranteed_count += 1
                            logger.debug(f"  ✅ Generated {req_feat}")
                        except Exception:
                            missing_features[req_feat] = df["close"].rolling(20).mean()
                            guaranteed_count += 1

                    elif req_feat.startswith("atr_"):
                        # ATR系
                        try:
                            period = int(req_feat.split("_")[1])
                            missing_features[req_feat] = self._calculate_atr_builtin(
                                df, period
                            )
                            guaranteed_count += 1
                            logger.debug(f"  ✅ Generated {req_feat}")
                        except Exception:
                            missing_features[req_feat] = df["close"] * 0.02  # 2%固定
                            guaranteed_count += 1

                    elif req_feat in ["rsi_oversold", "rsi_overbought"]:
                        # RSI派生特徴量
                        rsi_14 = missing_features.get(
                            "rsi_14", df["close"] * 0 + 50
                        )  # デフォルト50
                        if req_feat == "rsi_oversold":
                            missing_features[req_feat] = (rsi_14 < 30).astype(int)
                        else:
                            missing_features[req_feat] = (rsi_14 > 70).astype(int)
                        guaranteed_count += 1
                        logger.debug(f"  ✅ Generated {req_feat}")

                    elif req_feat in ["stoch_oversold", "stoch_overbought"]:
                        # Stochastic派生特徴量
                        stoch_k = missing_features.get(
                            "stoch_k", df["close"] * 0 + 50
                        )  # デフォルト50
                        if req_feat == "stoch_oversold":
                            missing_features[req_feat] = (stoch_k < 20).astype(int)
                        else:
                            missing_features[req_feat] = (stoch_k > 80).astype(int)
                        guaranteed_count += 1
                        logger.debug(f"  ✅ Generated {req_feat}")

                    else:
                        # その他の特徴量: 既に計算済みのはず
                        logger.debug(f"  ⚠️ {req_feat} should be calculated elsewhere")

            logger.info(
                f"🎯 Production.yml compliance: {guaranteed_count} features guaranteed"
            )
            logger.info(
                f"✅ Missing features batch: {len(missing_features)} features calculated"
            )
            return self.batch_calc.create_feature_batch(
                "missing_features_batch", missing_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ Missing features batch calculation failed: {e}")
            import traceback

            traceback.print_exc()
            return FeatureBatch("missing_features_batch", {})

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
        batches.append(
            self.calculate_missing_features_batch(df)
        )  # Phase H.25: 不足特徴量

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
        """Phase H.23.6: 強化版内蔵ATR計算 - NaN値防止・多段階フォールバック"""
        try:
            # Phase H.29: データ不足チェック緩和（実データ優先）
            min_required = max(2, period // 5)  # より少ないデータでも実計算を試みる
            if len(df) < min_required:
                logger.warning(
                    f"⚠️ ATR: Insufficient data ({len(df)} < {min_required}), using price-based fallback"
                )
                # Phase H.29: 価格の0.02%をATR代替値として使用（BTCJPYスケーリング対応）
                price_based_atr = df["close"] * 0.0002
                return pd.Series(price_based_atr, index=df.index, name=f"atr_{period}")

            # 動的period調整
            effective_period = min(period, len(df) - 1)
            if effective_period != period:
                logger.warning(f"⚠️ ATR period adjusted: {period} → {effective_period}")

            # True Range計算（強化版）
            high_low = df["high"] - df["low"]
            high_close = np.abs(df["high"] - df["close"].shift())
            low_close = np.abs(df["low"] - df["close"].shift())

            # NaN値処理強化
            high_low = high_low.fillna(0)
            high_close = high_close.fillna(
                high_low
            )  # 前日終値データがない場合はhigh-lowを使用
            low_close = low_close.fillna(high_low)

            true_range = np.maximum(high_low, np.maximum(high_close, low_close))

            # Phase H.29: ATR計算（min_periods緩和で実データ優先）
            atr = (
                pd.Series(true_range, index=df.index)
                .rolling(
                    window=effective_period,
                    min_periods=max(
                        1, effective_period // 5
                    ),  # より少ないデータでも計算
                )
                .mean()
            )

            # Phase H.23.6: 現実的なNaN値フォールバック
            if atr.isnull().any():
                # フォールバック1: 価格変動率ベース（現実的）
                price_volatility = (
                    df["close"]
                    .pct_change()
                    .abs()
                    .rolling(window=effective_period, min_periods=1)
                    .mean()
                    * df["close"]
                )

                # フォールバック2: 価格の0.02%（最終手段）Phase H.29対応
                emergency_atr = df["close"] * 0.0002

                # 階層的フォールバック適用
                atr = atr.fillna(price_volatility).fillna(emergency_atr)

            logger.debug(
                f"✅ ATR calculated: period={effective_period}, nan_count={atr.isnull().sum()}"
            )
            return atr.rename(f"atr_{period}")

        except Exception as e:
            logger.error(f"❌ ATR builtin calculation failed: {e}")
            # 緊急フォールバック: 価格の0.02% Phase H.29対応
            emergency_atr = df["close"] * 0.0002
            return pd.Series(emergency_atr, index=df.index, name=f"atr_{period}")

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
