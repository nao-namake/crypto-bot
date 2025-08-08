"""
Technical Indicators - Phase 16.3-B Split

統合前: crypto_bot/ml/feature_master_implementation.py（1,801行）
分割後: crypto_bot/ml/features/master/technical_indicators.py

機能:
- RSI、MACD、統計系、ATR/ボラティリティ、ボリンジャーバンド
- ストキャス、ボリューム、オシレーター、ADXトレンド系特徴量
- テクニカル指標の詳細実装メソッド群

Phase 16.3-B実装日: 2025年8月8日
"""

import logging

import numpy as np
import pandas as pd

# typing imports removed - not currently used


logger = logging.getLogger(__name__)


class TechnicalIndicatorsMixin:
    """テクニカル指標生成メソッド群（Mixinクラス）"""

    def _generate_rsi_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """RSI系: 3個 (rsi_14, rsi_oversold, rsi_overbought)"""
        logger.debug("🔧 RSI系特徴量生成中...")

        try:
            if "close" in df.columns:
                # RSI計算
                delta = df["close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()

                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))

                df["rsi_14"] = rsi
                self.implemented_features.add("rsi_14")

                # RSI条件特徴量
                df["rsi_oversold"] = (rsi < 30).astype(int)
                self.implemented_features.add("rsi_oversold")

                df["rsi_overbought"] = (rsi > 70).astype(int)
                self.implemented_features.add("rsi_overbought")

                logger.debug("✅ RSI系特徴量: 3/3個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ RSI系特徴量生成エラー: {e}")

        return df

    def _generate_macd_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """MACD系: 5個 (macd, macd_signal, macd_hist, macd_cross_up, macd_cross_down)"""
        logger.debug("🔧 MACD系特徴量生成中...")

        try:
            if "close" in df.columns:
                # MACD計算
                exp1 = df["close"].ewm(span=12, adjust=False).mean()
                exp2 = df["close"].ewm(span=26, adjust=False).mean()

                macd = exp1 - exp2
                signal = macd.ewm(span=9, adjust=False).mean()
                hist = macd - signal

                df["macd"] = macd
                self.implemented_features.add("macd")

                df["macd_signal"] = signal
                self.implemented_features.add("macd_signal")

                df["macd_hist"] = hist
                self.implemented_features.add("macd_hist")

                # MACDクロス特徴量
                macd_prev = macd.shift(1)
                signal_prev = signal.shift(1)

                df["macd_cross_up"] = (
                    (macd > signal) & (macd_prev <= signal_prev)
                ).astype(int)
                self.implemented_features.add("macd_cross_up")

                df["macd_cross_down"] = (
                    (macd < signal) & (macd_prev >= signal_prev)
                ).astype(int)
                self.implemented_features.add("macd_cross_down")

                logger.debug("✅ MACD系特徴量: 5/5個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ MACD系特徴量生成エラー: {e}")

        return df

    def _generate_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """統計系: 2個 (zscore, close_std_10)"""
        logger.debug("🔧 統計系特徴量生成中...")

        try:
            if "close" in df.columns:
                # Z-Score計算
                rolling_mean = df["close"].rolling(window=20).mean()
                rolling_std = df["close"].rolling(window=20).std()
                df["zscore"] = (df["close"] - rolling_mean) / rolling_std
                self.implemented_features.add("zscore")

                # 10期間標準偏差
                df["close_std_10"] = df["close"].rolling(window=10).std()
                self.implemented_features.add("close_std_10")

                logger.debug("✅ 統計系特徴量: 2/2個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ 統計系特徴量生成エラー: {e}")

        return df

    def _generate_atr_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ATR・ボラティリティ系: 2個 (atr_14, volatility_20)"""
        logger.debug("🔧 ATR・ボラティリティ系特徴量生成中...")

        try:
            required_cols = ["high", "low", "close"]
            if all(col in df.columns for col in required_cols):
                # ATR計算
                high_low = df["high"] - df["low"]
                high_close = np.abs(df["high"] - df["close"].shift())
                low_close = np.abs(df["low"] - df["close"].shift())

                true_range = np.maximum(high_low, np.maximum(high_close, low_close))
                df["atr_14"] = true_range.rolling(window=14).mean()
                self.implemented_features.add("atr_14")

                # ボラティリティ計算（20期間リターンの標準偏差）
                returns = df["close"].pct_change()
                df["volatility_20"] = returns.rolling(window=20).std() * np.sqrt(20)
                self.implemented_features.add("volatility_20")

                logger.debug("✅ ATR・ボラティリティ系特徴量: 2/2個実装完了")
            else:
                logger.warning(f"⚠️ 必要列が不足: {required_cols}")

        except Exception as e:
            logger.error(f"❌ ATR・ボラティリティ系特徴量生成エラー: {e}")

        return df

    def _generate_price_position_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """価格ポジション系: 4個 (price_position_20, price_position_50, price_vs_sma20, intraday_position)"""
        logger.debug("🔧 価格ポジション系特徴量生成中...")

        try:
            if "close" in df.columns:
                # 価格ポジション計算
                sma_20 = df["close"].rolling(window=20).mean()
                sma_50 = df["close"].rolling(window=50).mean()

                # 20期間SMAに対する相対位置
                df["price_position_20"] = (df["close"] - sma_20) / sma_20 * 100
                self.implemented_features.add("price_position_20")

                # 50期間SMAに対する相対位置
                df["price_position_50"] = (df["close"] - sma_50) / sma_50 * 100
                self.implemented_features.add("price_position_50")

                # SMA20との価格比較
                df["price_vs_sma20"] = (df["close"] > sma_20).astype(int)
                self.implemented_features.add("price_vs_sma20")

                # 日内ポジション（高値・安値に対する位置）
                if all(col in df.columns for col in ["high", "low"]):
                    df["intraday_position"] = (df["close"] - df["low"]) / (
                        df["high"] - df["low"]
                    )
                    df["intraday_position"] = df["intraday_position"].fillna(
                        0.5
                    )  # レンジがない場合は中央値
                    self.implemented_features.add("intraday_position")

                logger.debug("✅ 価格ポジション系特徴量: 4/4個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ 価格ポジション系特徴量生成エラー: {e}")

        return df

    def _generate_bollinger_band_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ボリンジャーバンド系: 6個 (bb_position, bb_upper, bb_middle, bb_lower, bb_width, bb_squeeze)"""
        logger.debug("🔧 ボリンジャーバンド系特徴量生成中...")

        try:
            if "close" in df.columns:
                # ボリンジャーバンド計算
                bb_period = 20
                bb_std_mult = 2

                bb_middle = df["close"].rolling(window=bb_period).mean()
                bb_std = df["close"].rolling(window=bb_period).std()

                bb_upper = bb_middle + (bb_std * bb_std_mult)
                bb_lower = bb_middle - (bb_std * bb_std_mult)

                df["bb_upper"] = bb_upper
                self.implemented_features.add("bb_upper")

                df["bb_middle"] = bb_middle
                self.implemented_features.add("bb_middle")

                df["bb_lower"] = bb_lower
                self.implemented_features.add("bb_lower")

                # BBポジション（バンド内での位置）
                df["bb_position"] = (df["close"] - bb_lower) / (bb_upper - bb_lower)
                df["bb_position"] = df["bb_position"].fillna(0.5)
                self.implemented_features.add("bb_position")

                # BBバンド幅
                df["bb_width"] = (bb_upper - bb_lower) / bb_middle
                self.implemented_features.add("bb_width")

                # BBスクイーズ（バンド幅が狭い状態）
                bb_width_sma = df["bb_width"].rolling(window=20).mean()
                df["bb_squeeze"] = (df["bb_width"] < bb_width_sma * 0.8).astype(int)
                self.implemented_features.add("bb_squeeze")

                logger.debug("✅ ボリンジャーバンド系特徴量: 6/6個実装完了")
            else:
                logger.warning("⚠️ close列が見つかりません")

        except Exception as e:
            logger.error(f"❌ ボリンジャーバンド系特徴量生成エラー: {e}")

        return df

    def _generate_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """時間特徴量系: 5個 (hour, day_of_week, is_weekend, is_asian_session, is_us_session)"""
        logger.debug("🔧 時間特徴量系生成中...")

        try:
            if isinstance(df.index, pd.DatetimeIndex):
                # 時間特徴量
                df["hour"] = df.index.hour
                self.implemented_features.add("hour")

                df["day_of_week"] = df.index.dayofweek
                self.implemented_features.add("day_of_week")

                df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)
                self.implemented_features.add("is_weekend")

                # セッション判定（UTC時間基準）
                df["is_asian_session"] = (
                    (df.index.hour >= 0) & (df.index.hour < 9)
                ).astype(int)
                self.implemented_features.add("is_asian_session")

                df["is_us_session"] = (
                    (df.index.hour >= 13) & (df.index.hour < 21)
                ).astype(int)
                self.implemented_features.add("is_us_session")

                logger.debug("✅ 時間特徴量系: 5/5個実装完了")
            else:
                logger.warning("⚠️ DatetimeIndexが必要です")

        except Exception as e:
            logger.error(f"❌ 時間特徴量系生成エラー: {e}")

        return df

    def _generate_stochastic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ストキャスティクス系: 4個 (stoch_k, stoch_d, stoch_oversold, stoch_overbought)"""
        logger.debug("🔧 ストキャスティクス系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["high", "low", "close"]):
                # ストキャスティクス期間設定（標準14期間）
                period = 14
                k_period = 3  # %D計算用の移動平均期間

                # %K値計算：(現在価格 - n期間最安値) / (n期間最高値 - n期間最安値) * 100
                lowest_low = df["low"].rolling(window=period).min()
                highest_high = df["high"].rolling(window=period).max()

                # ゼロ除算回避
                denominator = highest_high - lowest_low
                stoch_k = np.where(
                    denominator != 0,
                    ((df["close"] - lowest_low) / denominator * 100),
                    50.0,  # デフォルト値（中立）
                )

                df["stoch_k"] = stoch_k
                self.implemented_features.add("stoch_k")

                # %D値計算：%Kの移動平均（Slow Stochastic）
                df["stoch_d"] = (
                    pd.Series(stoch_k, index=df.index).rolling(window=k_period).mean()
                )
                self.implemented_features.add("stoch_d")

                # 売られすぎ判定：%K < 20
                df["stoch_oversold"] = (stoch_k < 20).astype(int)
                self.implemented_features.add("stoch_oversold")

                # 買われすぎ判定：%K > 80
                df["stoch_overbought"] = (stoch_k > 80).astype(int)
                self.implemented_features.add("stoch_overbought")

                logger.debug("✅ ストキャスティクス系特徴量: 4/4個実装完了")
            else:
                logger.warning("⚠️ high, low, close列が必要です")

        except Exception as e:
            logger.error(f"❌ ストキャスティクス系特徴量生成エラー: {e}")

        return df

    def _generate_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """出来高系: 14個 (volume_lag_*, volume_sma_20, volume_ratio, vwap, etc.)"""
        logger.debug("🔧 出来高系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["volume", "high", "low", "close"]):
                # 1. ボリュームラグ特徴量: 3個
                df["volume_lag_1"] = df["volume"].shift(1)
                self.implemented_features.add("volume_lag_1")

                df["volume_lag_4"] = df["volume"].shift(4)
                self.implemented_features.add("volume_lag_4")

                df["volume_lag_5"] = df["volume"].shift(5)
                self.implemented_features.add("volume_lag_5")

                # 2. ボリューム単純移動平均: 1個
                df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
                self.implemented_features.add("volume_sma_20")

                # 3. ボリューム比率（現在ボリューム / 20期間平均）: 1個
                volume_ma = df["volume"].rolling(window=20).mean()
                df["volume_ratio"] = np.where(
                    volume_ma > 0, df["volume"] / volume_ma, 1.0  # デフォルト値
                )
                self.implemented_features.add("volume_ratio")

                # 4. ボリュームトレンド（5期間のボリューム変化）: 1個
                df["volume_trend"] = df["volume"].pct_change(5) * 100
                self.implemented_features.add("volume_trend")

                # 5. VWAP (Volume Weighted Average Price): 1個
                typical_price = (df["high"] + df["low"] + df["close"]) / 3
                vwap_num = (typical_price * df["volume"]).rolling(window=20).sum()
                vwap_den = df["volume"].rolling(window=20).sum()
                df["vwap"] = np.where(vwap_den > 0, vwap_num / vwap_den, df["close"])
                self.implemented_features.add("vwap")

                # 6. VWAPからの距離: 1個
                df["vwap_distance"] = ((df["close"] - df["vwap"]) / df["vwap"]) * 100
                self.implemented_features.add("vwap_distance")

                # 7. OBV (On-Balance Volume): 1個
                price_change = df["close"].diff()
                obv_direction = np.where(
                    price_change > 0, 1, np.where(price_change < 0, -1, 0)
                )
                df["obv"] = (df["volume"] * obv_direction).cumsum()
                self.implemented_features.add("obv")

                # 8. OBV単純移動平均: 1個
                df["obv_sma"] = df["obv"].rolling(window=20).mean()
                self.implemented_features.add("obv_sma")

                # 9. CMF (Chaikin Money Flow): 1個
                money_flow_multiplier = (
                    (df["close"] - df["low"]) - (df["high"] - df["close"])
                ) / (df["high"] - df["low"])
                money_flow_multiplier = money_flow_multiplier.fillna(0)  # ゼロ除算対策
                money_flow_volume = money_flow_multiplier * df["volume"]
                cmf_num = money_flow_volume.rolling(window=20).sum()
                cmf_den = df["volume"].rolling(window=20).sum()
                df["cmf"] = np.where(cmf_den > 0, cmf_num / cmf_den, 0.0)
                self.implemented_features.add("cmf")

                # 10. MFI (Money Flow Index): 1個
                raw_money_flow = typical_price * df["volume"]
                positive_flow = np.where(typical_price.diff() > 0, raw_money_flow, 0)
                negative_flow = np.where(typical_price.diff() < 0, raw_money_flow, 0)

                pos_flow_sum = pd.Series(positive_flow).rolling(window=14).sum()
                neg_flow_sum = pd.Series(negative_flow).rolling(window=14).sum()

                money_ratio = np.where(
                    neg_flow_sum > 0, pos_flow_sum / neg_flow_sum, 1.0
                )
                df["mfi"] = 100 - (100 / (1 + money_ratio))
                self.implemented_features.add("mfi")

                # 11. A/D Line (Accumulation/Distribution Line): 1個
                ad_multiplier = money_flow_multiplier  # CMFと同じ計算
                df["ad_line"] = (ad_multiplier * df["volume"]).cumsum()
                self.implemented_features.add("ad_line")

                # 12. ボリュームブレイクアウト: 1個
                volume_threshold = df["volume"].rolling(window=20).mean() * 1.5
                df["volume_breakout"] = (df["volume"] > volume_threshold).astype(int)
                self.implemented_features.add("volume_breakout")

                # 13. ボリューム・価格相関: 1個
                price_returns = df["close"].pct_change()
                volume_returns = df["volume"].pct_change()
                df["volume_price_correlation"] = price_returns.rolling(window=20).corr(
                    volume_returns
                )
                df["volume_price_correlation"] = df["volume_price_correlation"].fillna(
                    0.0
                )  # NaN対策
                self.implemented_features.add("volume_price_correlation")

                logger.debug("✅ 出来高系特徴量: 13/13個実装完了")
            else:
                logger.warning("⚠️ volume, high, low, close列が必要です")

        except Exception as e:
            logger.error(f"❌ 出来高系特徴量生成エラー: {e}")

        return df

    def _generate_oscillator_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """オシレーター系: 4個 (cci_20, williams_r, ultimate_oscillator, momentum_14)"""
        logger.debug("🔧 オシレーター系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["high", "low", "close"]):
                # 1. CCI (Commodity Channel Index): 1個
                typical_price = (df["high"] + df["low"] + df["close"]) / 3
                tp_sma = typical_price.rolling(window=20).mean()
                mean_deviation = typical_price.rolling(window=20).apply(
                    lambda x: np.mean(np.abs(x - x.mean())), raw=True
                )
                df["cci_20"] = np.where(
                    mean_deviation > 0,
                    (typical_price - tp_sma)
                    / (0.015 * mean_deviation),  # 0.015は標準的な定数
                    0.0,
                )
                self.implemented_features.add("cci_20")

                # 2. Williams %R: 1個
                period = 14
                highest_high = df["high"].rolling(window=period).max()
                lowest_low = df["low"].rolling(window=period).min()
                denominator = highest_high - lowest_low
                williams_r = np.where(
                    denominator > 0,
                    -100 * (highest_high - df["close"]) / denominator,
                    -50.0,  # デフォルト値（中立）
                )
                df["williams_r"] = williams_r
                self.implemented_features.add("williams_r")

                # 3. Ultimate Oscillator: 1個
                # True Range計算
                prev_close = df["close"].shift(1)
                tr1 = df["high"] - df["low"]
                tr2 = np.abs(df["high"] - prev_close)
                tr3 = np.abs(df["low"] - prev_close)
                true_range = np.maximum(tr1, np.maximum(tr2, tr3))

                # Buying Pressure計算
                buying_pressure = df["close"] - np.minimum(df["low"], prev_close)

                # 3つの期間での計算
                bp7 = buying_pressure.rolling(window=7).sum()
                tr7 = true_range.rolling(window=7).sum()
                bp14 = buying_pressure.rolling(window=14).sum()
                tr14 = true_range.rolling(window=14).sum()
                bp28 = buying_pressure.rolling(window=28).sum()
                tr28 = true_range.rolling(window=28).sum()

                # Ultimate Oscillator計算
                raw7 = np.where(tr7 > 0, bp7 / tr7, 0.5)
                raw14 = np.where(tr14 > 0, bp14 / tr14, 0.5)
                raw28 = np.where(tr28 > 0, bp28 / tr28, 0.5)

                df["ultimate_oscillator"] = 100 * (4 * raw7 + 2 * raw14 + raw28) / 7
                self.implemented_features.add("ultimate_oscillator")

                # 4. Momentum: 1個
                df["momentum_14"] = df["close"] - df["close"].shift(14)
                self.implemented_features.add("momentum_14")

                logger.debug("✅ オシレーター系特徴量: 4/4個実装完了")
            else:
                logger.warning("⚠️ high, low, close列が必要です")

        except Exception as e:
            logger.error(f"❌ オシレーター系特徴量生成エラー: {e}")

        return df

    def _generate_adx_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """ADX・トレンド系: 5個 (adx_14, plus_di, minus_di, trend_strength, trend_direction)"""
        logger.debug("🔧 ADX・トレンド系特徴量生成中...")

        try:
            if all(col in df.columns for col in ["high", "low", "close"]):
                period = 14

                # True Range計算
                prev_close = df["close"].shift(1)
                tr1 = df["high"] - df["low"]
                tr2 = (df["high"] - prev_close).abs()
                tr3 = (df["low"] - prev_close).abs()
                true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

                # Directional Movement計算
                high_diff = df["high"].diff()
                low_diff = df["low"].diff() * -1  # 下降時は正の値

                plus_dm = pd.Series(
                    np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0),
                    index=df.index,
                )
                minus_dm = pd.Series(
                    np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0),
                    index=df.index,
                )

                # 移動平均計算
                atr_smooth = true_range.rolling(window=period).mean()
                plus_dm_smooth = plus_dm.rolling(window=period).mean()
                minus_dm_smooth = minus_dm.rolling(window=period).mean()

                # Directional Indicators計算
                plus_di = 100 * plus_dm_smooth / atr_smooth
                minus_di = 100 * minus_dm_smooth / atr_smooth

                # NaN値を0で置換
                plus_di = plus_di.fillna(0)
                minus_di = minus_di.fillna(0)

                df["plus_di"] = plus_di
                self.implemented_features.add("plus_di")

                df["minus_di"] = minus_di
                self.implemented_features.add("minus_di")

                # DX (Directional Index)計算
                di_sum = plus_di + minus_di
                di_diff = (plus_di - minus_di).abs()
                dx = 100 * di_diff / di_sum
                dx = dx.fillna(0)

                # ADX計算（DXの移動平均）
                adx = dx.rolling(window=period).mean().fillna(0)
                df["adx_14"] = adx
                self.implemented_features.add("adx_14")

                # トレンド強度（ADXベース）: 1個
                trend_strength = pd.Series(
                    np.where(
                        adx > 25,
                        3,  # 強トレンド
                        np.where(
                            adx > 20, 2, np.where(adx > 15, 1, 0)  # 中トレンド
                        ),  # 弱・無トレンド
                    ),
                    index=df.index,
                )
                df["trend_strength"] = trend_strength
                self.implemented_features.add("trend_strength")

                # トレンド方向（+DI vs -DI）: 1個
                trend_direction = pd.Series(
                    np.where(
                        plus_di > minus_di + 2,
                        1,  # 上昇トレンド（バッファ付き）
                        np.where(minus_di > plus_di + 2, -1, 0),  # 下降トレンド・横ばい
                    ),
                    index=df.index,
                )
                df["trend_direction"] = trend_direction
                self.implemented_features.add("trend_direction")

                logger.debug("✅ ADX・トレンド系特徴量: 5/5個実装完了")
            else:
                logger.warning("⚠️ high, low, close列が必要です")

        except Exception as e:
            logger.error(f"❌ ADX・トレンド系特徴量生成エラー: {e}")

        return df
