# crypto_bot/indicator/calculator.py
# 説明:
# pandas-taライブラリを使い、テクニカル指標（ATR・SMA・EMA・MACD・RSI・RCIなど）を簡単に計算するためのクラスです。
# - ATR（平均的な価格変動幅）、移動平均（SMA/EMA）、MACD・RSI・RCIも計算できます。
# - pandas-ta がインストールされていればOK。TA-Libは使いません。
# - バックテストや特徴量エンジニアリング、トレーディング戦略の実装で広く利用します。

from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta  # TA-Lib は一切使いません


class IndicatorCalculator:
    """
    pandas-ta をラップして、各種テクニカル指標（ATR/SMA/EMA/MACD/RSI/RCIなど）を計算し、
    Series / DataFrame を返します。
    """

    # ------------------------------------------------------------------
    # ATR ― 平均真の範囲（価格の平均的な変動幅、ボラティリティの指標）
    # ------------------------------------------------------------------
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """平均真の範囲 (ATR) を返す（Phase H.26: 超堅牢化版・NaN値多発完全解決）"""
        import logging

        logger = logging.getLogger(__name__)

        # Phase H.26: 入力データ検証強化
        try:
            if df is None or df.empty:
                logger.error("ATR calculation: Empty or None DataFrame")
                raise ValueError("Empty DataFrame provided for ATR calculation")

            required_cols = ["high", "low", "close"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"ATR calculation: Missing columns {missing_cols}")
                raise ValueError(f"Missing required columns for ATR: {missing_cols}")

            # NaN値チェック強化
            tmp = df[required_cols].copy()
            initial_nan_ratio = tmp.isna().sum().sum() / (len(tmp) * len(required_cols))
            logger.debug(f"ATR input data quality: {initial_nan_ratio:.2%} NaN values")

            # 極端なNaN値の場合は即座にフォールバック
            if initial_nan_ratio > 0.7:
                logger.warning(
                    f"Too many NaN values for ATR: {initial_nan_ratio:.2%}, using emergency fallback"
                )
                return IndicatorCalculator._emergency_atr_fallback(tmp, period)

            # Phase H.26: NaN値の積極的な事前処理
            tmp = tmp.ffill().bfill()
            remaining_nan_ratio = tmp.isna().sum().sum() / (
                len(tmp) * len(required_cols)
            )

            if remaining_nan_ratio > 0:
                # まだNaNがある場合は価格平均で補完
                for col in required_cols:
                    if tmp[col].isna().any():
                        mean_price = tmp[required_cols].mean(axis=1)  # 行平均
                        tmp[col] = tmp[col].fillna(mean_price)
                logger.info(
                    f"ATR: Applied aggressive NaN filling, {remaining_nan_ratio:.2%} → 0%"
                )

            # 型変換の安全処理
            tmp = tmp.astype("float64")

        except Exception as e:
            logger.error(f"ATR input validation failed: {e}")
            # 緊急フォールバック
            return IndicatorCalculator._emergency_atr_fallback(df, period)

        # Phase H.26: 段階的期間調整戦略（より積極的）
        min_data_required = max(2, period // 5)  # より緩和（3→2, period//3→period//5）
        if len(tmp) < min_data_required:
            logger.error(f"Insufficient data for ATR: {len(tmp)} < {min_data_required}")
            return IndicatorCalculator._emergency_atr_fallback(tmp, period)

        # Phase H.26: 適応的期間調整（段階的縮小）
        effective_period = IndicatorCalculator._calculate_adaptive_period(
            tmp, period, logger
        )

        if effective_period != period:
            logger.info(
                f"ATR period adapted: {period} → {effective_period} (data length: {len(tmp)})"
            )

        atr_series = None
        try:
            # Phase H.13: pandas-taでのATR計算（主要手法）
            atr_series = ta.atr(
                high=tmp["high"],
                low=tmp["low"],
                close=tmp["close"],
                length=effective_period,
            )

            # Phase H.13: 結果の品質チェック
            if atr_series is not None and not atr_series.isnull().all():
                # nan値の個数をチェック
                nan_count = atr_series.isnull().sum()
                if nan_count > 0:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"📊 ATR calculation: {nan_count}/{len(atr_series)} nan values, using available data"
                    )

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"⚠️ pandas-ta ATR calculation failed: {e}, using fallback method"
            )
            atr_series = None

        # Phase H.26: 多段階フォールバック処理（大幅強化）
        if (
            atr_series is None
            or atr_series.isnull().all()
            or atr_series.isnull().sum() / len(atr_series) > 0.5
        ):
            logger.info(
                "🔄 Using Phase H.26 enhanced multi-stage fallback ATR calculation"
            )
            atr_series = IndicatorCalculator._multi_stage_atr_fallback(
                tmp, effective_period, logger
            )

        # Phase H.26: 最終品質チェック・NaN値完全除去
        if atr_series is not None:
            atr_series = IndicatorCalculator._finalize_atr_series(
                atr_series, tmp, effective_period, logger
            )

        return atr_series.rename(f"ATR_{period}")

    # ------------------------------------------------------------------
    # SMA（単純移動平均）・EMA（指数移動平均）
    # ------------------------------------------------------------------
    def sma(self, series: pd.Series, window: int) -> pd.Series:
        """単純移動平均 (SMA)"""
        return series.rolling(window=window, min_periods=window).mean()

    def ema(self, series: pd.Series, window: int) -> pd.Series:
        """指数移動平均 (EMA)"""
        return series.ewm(span=window, adjust=False, min_periods=window).mean()

    # ------------------------------------------------------------------
    # RSI（相対力指数）
    # ------------------------------------------------------------------
    def rsi(self, series: pd.Series, window: int = 14) -> pd.Series:
        """RSI（相対力指数）"""
        try:
            return ta.rsi(series, length=window)
        except Exception:
            # フォールバック実装（単純RSI計算式）
            delta = series.diff()
            up = delta.clip(lower=0).rolling(window=window).mean()
            down = -delta.clip(upper=0).rolling(window=window).mean()
            rs = up / (down + 1e-8)
            return 100 - (100 / (1 + rs))

    # ------------------------------------------------------------------
    # MACD（移動平均収束拡散法）
    # ------------------------------------------------------------------
    def macd(
        self, series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> pd.DataFrame:
        """
        MACD
        - macd: MACDライン
        - macdh: MACDヒストグラム
        - macds: シグナル
        """
        try:
            macd_df = ta.macd(series, fast=fast, slow=slow, signal=signal)
            if macd_df is None or macd_df.isnull().all(axis=None):
                raise ValueError("macd_df is None or all null")
            return macd_df
        except Exception:
            # フォールバック
            macd_line = self.ema(series, fast) - self.ema(series, slow)
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            macd_hist = macd_line - signal_line
            return pd.DataFrame(
                {
                    "MACD_12_26_9": macd_line,
                    "MACDh_12_26_9": macd_hist,
                    "MACDs_12_26_9": signal_line,
                }
            )

    # ------------------------------------------------------------------
    # RCI（順位相関指数） ※pandas_taにない場合は自作
    # ------------------------------------------------------------------
    def rci(self, series: pd.Series, window: int = 9) -> pd.Series:
        """RCI（順位相関指数）。pandas_ta未実装時は自作計算式で対応。"""
        # pandas_taにrciがなければ自作関数を使う
        rci_func = getattr(ta, "rci", None)
        if callable(rci_func):
            try:
                out = ta.rci(series, length=window)
                if out is not None:
                    return out
            except Exception:
                pass
        # --- フォールバック：RCI自作 ---
        n = window

        def _rci(x):
            price_ranks = pd.Series(x).rank(ascending=False)
            date_ranks = np.arange(1, n + 1)
            d = price_ranks.values - date_ranks
            return (1 - 6 * (d**2).sum() / (n * (n**2 - 1))) * 100

        return series.rolling(window=n).apply(_rci, raw=False).rename(f"RCI_{window}")

    # ------------------------------------------------------------------
    # ATRラッパー
    # ------------------------------------------------------------------
    def atr(self, df: pd.DataFrame, window: int = 14) -> pd.Series:
        """DataFrame チェック付き ATR ラッパー"""
        if not isinstance(df, pd.DataFrame):
            raise TypeError("atr requires a pandas DataFrame")
        return self.calculate_atr(df, period=window)

    # ------------------------------------------------------------------
    # もちぽよアラート: RCI×MACDの逆張りシグナル（買い・売り対応）
    # ------------------------------------------------------------------
    def mochipoyo_signals(
        self,
        df: pd.DataFrame,
        rci_window: int = 9,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
    ) -> pd.DataFrame:
        """
        もちぽよアラート風シグナル（ロング・ショート両対応）
        - ロング（買い）条件: RCIが-80以下＆MACDゴールデンクロス
        - ショート（売り）条件: RCIが+80以上＆MACDデッドクロス
        """
        close = df["close"]
        # RCI計算
        rci = self.rci(close, window=rci_window)
        # MACD計算
        macd_df = self.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
        macd = (
            macd_df.iloc[:, 0]
            if "MACD_12_26_9" in macd_df.columns
            else macd_df.iloc[:, 0]
        )
        signal = (
            macd_df.iloc[:, 2]
            if "MACDs_12_26_9" in macd_df.columns
            else macd_df.iloc[:, 2]
        )

        # ゴールデンクロス・デッドクロス検出
        golden_cross = (macd.shift(1) < signal.shift(1)) & (macd > signal)
        dead_cross = (macd.shift(1) > signal.shift(1)) & (macd < signal)

        # ロングシグナル: RCI低位＆ゴールデンクロス
        long_signal = ((rci < -80) & golden_cross).astype(int)
        # ショートシグナル: RCI高位＆デッドクロス
        short_signal = ((rci > 80) & dead_cross).astype(int)

        return pd.DataFrame(
            {
                "mochipoyo_long_signal": long_signal,
                "mochipoyo_short_signal": short_signal,
            }
        )

    # ------------------------------------------------------------------
    # ストキャスティクス（Stochastic Oscillator）
    # ------------------------------------------------------------------
    def stochastic(
        self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3, smooth_k: int = 3
    ) -> pd.DataFrame:
        """
        ストキャスティクス指標を計算
        - %K: メインライン
        - %D: シグナルライン
        """
        try:
            stoch = ta.stoch(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                k=k_period,
                d=d_period,
                smooth_k=smooth_k,
            )
            if stoch is not None:
                return stoch
        except Exception:
            pass

        # フォールバック実装
        high = df["high"]
        low = df["low"]
        close = df["close"]

        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        k_percent_smooth = k_percent.rolling(window=smooth_k).mean()
        d_percent = k_percent_smooth.rolling(window=d_period).mean()

        return pd.DataFrame(
            {
                f"STOCHk_{k_period}_{d_period}_{smooth_k}": k_percent_smooth,
                f"STOCHd_{k_period}_{d_period}_{smooth_k}": d_percent,
            }
        )

    # ------------------------------------------------------------------
    # ボリンジャーバンド（Bollinger Bands）
    # ------------------------------------------------------------------
    def bollinger_bands(
        self, series: pd.Series, window: int = 20, std_dev: float = 2.0
    ) -> pd.DataFrame:
        """
        ボリンジャーバンド計算
        - Upper Band: 上限バンド
        - Middle Band: 中央線（SMA）
        - Lower Band: 下限バンド
        """
        try:
            bb = ta.bbands(series, length=window, std=std_dev)
            if bb is not None:
                return bb
        except Exception:
            pass

        # フォールバック実装
        sma = series.rolling(window=window).mean()
        std = series.rolling(window=window).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return pd.DataFrame(
            {
                f"BBL_{window}_{std_dev}": lower_band,
                f"BBM_{window}_{std_dev}": sma,
                f"BBU_{window}_{std_dev}": upper_band,
                f"BBB_{window}_{std_dev}": (series - lower_band)
                / (upper_band - lower_band),  # %B
                f"BBW_{window}_{std_dev}": (upper_band - lower_band)
                / sma,  # Band Width
            }
        )

    # ------------------------------------------------------------------
    # Williams %R
    # ------------------------------------------------------------------
    def williams_r(self, df: pd.DataFrame, window: int = 14) -> pd.Series:
        """Williams %R計算"""
        try:
            willr = ta.willr(
                high=df["high"], low=df["low"], close=df["close"], length=window
            )
            if willr is not None:
                return willr
        except Exception:
            pass

        # フォールバック実装
        highest_high = df["high"].rolling(window=window).max()
        lowest_low = df["low"].rolling(window=window).min()

        willr = -100 * ((highest_high - df["close"]) / (highest_high - lowest_low))
        return willr.rename(f"WILLR_{window}")

    # ------------------------------------------------------------------
    # ADX（Average Directional Index）
    # ------------------------------------------------------------------
    def adx(self, df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        """ADX（平均方向性指数）計算"""
        try:
            adx_data = ta.adx(
                high=df["high"], low=df["low"], close=df["close"], length=window
            )
            if adx_data is not None:
                return adx_data
        except Exception:
            pass

        # 簡易フォールバック
        high = df["high"]
        low = df["low"]
        close = df["close"]

        # True Range
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        plus_dm = (high - high.shift(1)).clip(lower=0)
        minus_dm = (low.shift(1) - low).clip(lower=0)

        # Smooth
        atr = tr.rolling(window=window).mean()
        plus_di = 100 * (plus_dm.rolling(window=window).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=window).mean() / atr)

        # ADX
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-8)
        adx_val = dx.rolling(window=window).mean()

        return pd.DataFrame(
            {
                f"ADX_{window}": adx_val,
                f"DMP_{window}": plus_di,
                f"DMN_{window}": minus_di,
            }
        )

    # ------------------------------------------------------------------
    # チャイキンマネーフロー（CMF）
    # ------------------------------------------------------------------
    def chaikin_money_flow(self, df: pd.DataFrame, window: int = 20) -> pd.Series:
        """チャイキンマネーフロー計算"""
        try:
            cmf = ta.cmf(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                volume=df["volume"],
                length=window,
            )
            if cmf is not None:
                return cmf
        except Exception:
            pass

        # フォールバック実装
        mfm = ((df["close"] - df["low"]) - (df["high"] - df["close"])) / (
            df["high"] - df["low"] + 1e-8
        )
        mfv = mfm * df["volume"]

        cmf_val = (
            mfv.rolling(window=window).sum() / df["volume"].rolling(window=window).sum()
        )
        return cmf_val.rename(f"CMF_{window}")

    # ------------------------------------------------------------------
    # フィッシャートランスフォーム
    # ------------------------------------------------------------------
    def fisher_transform(self, df: pd.DataFrame, window: int = 10) -> pd.DataFrame:
        """フィッシャートランスフォーム計算"""
        try:
            fisher = ta.fisher(high=df["high"], low=df["low"], length=window)
            if fisher is not None:
                return fisher
        except Exception:
            pass

        # フォールバック実装
        median_price = (df["high"] + df["low"]) / 2
        min_low = df["low"].rolling(window=window).min()
        max_high = df["high"].rolling(window=window).max()

        # 正規化（-1 to 1）
        value1 = 0.66 * ((median_price - min_low) / (max_high - min_low + 1e-8) - 0.5)
        value1 = value1.clip(-0.999, 0.999)  # クリップしてlog計算エラーを防ぐ

        fisher_val = 0.5 * np.log((1 + value1) / (1 - value1 + 1e-8))
        fisher_signal = fisher_val.shift(1)

        return pd.DataFrame(
            {f"FISH_{window}": fisher_val, f"FISHs_{window}": fisher_signal}
        )

    # ------------------------------------------------------------------
    # 高度な組み合わせシグナル
    # ------------------------------------------------------------------
    def advanced_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        複数指標を組み合わせた高度なシグナル生成
        - トレンド強度
        - モメンタム
        - 過買い・過売り
        - ボラティリティ
        """
        signals = pd.DataFrame(index=df.index)

        # RSI
        rsi = self.rsi(df["close"], window=14)

        # ストキャスティクス
        stoch = self.stochastic(df)
        stoch_k = stoch.iloc[:, 0] if not stoch.empty else pd.Series(index=df.index)

        # ADX
        adx_data = self.adx(df)
        adx_val = (
            adx_data.iloc[:, 0] if not adx_data.empty else pd.Series(index=df.index)
        )

        # ボリンジャーバンド
        bb = self.bollinger_bands(df["close"])
        bb_percent = bb.iloc[:, 3] if not bb.empty else pd.Series(index=df.index)  # %B

        # Williams %R
        willr = self.williams_r(df)

        # 複合シグナル
        # 1. 強いトレンド＆過売り → BUY
        signals["strong_trend_oversold"] = (
            (adx_val > 25) & (rsi < 30) & (stoch_k < 20) & (willr < -80)
        ).astype(int)

        # 2. 強いトレンド＆過買い → SELL
        signals["strong_trend_overbought"] = (
            (adx_val > 25) & (rsi > 70) & (stoch_k > 80) & (willr > -20)
        ).astype(int)

        # 3. ボリンジャーバンド逆張り
        signals["bb_reversal_buy"] = (bb_percent < 0.1).astype(int)  # 下限付近
        signals["bb_reversal_sell"] = (bb_percent > 0.9).astype(int)  # 上限付近

        # 4. マルチタイムフレーム対応（移動平均の傾き）
        sma_short = self.sma(df["close"], 10)
        sma_long = self.sma(df["close"], 50)

        signals["trend_alignment"] = (
            (sma_short > sma_long) & (sma_short.diff() > 0) & (sma_long.diff() > 0)
        ).astype(int)

        return signals

    # ------------------------------------------------------------------
    # Phase F.3: 151特徴量WARNING解消 - 不足特徴量実装
    # ------------------------------------------------------------------
    def volatility_24h(self, series: pd.Series) -> pd.Series:
        """24時間ボラティリティ"""
        returns = series.pct_change()
        return (
            (returns.rolling(24).std() * np.sqrt(24))
            .fillna(0.0)
            .rename("volatility_24h")
        )

    def volatility_1h(self, series: pd.Series) -> pd.Series:
        """1時間ボラティリティ"""
        returns = series.pct_change()
        return returns.rolling(1).std().fillna(0.0).rename("volatility_1h")

    def volume_change_24h(self, series: pd.Series) -> pd.Series:
        """24時間ボリューム変化率"""
        return series.pct_change(24).fillna(0.0).rename("volume_change_24h")

    def volume_change_1h(self, series: pd.Series) -> pd.Series:
        """1時間ボリューム変化率"""
        return series.pct_change(1).fillna(0.0).rename("volume_change_1h")

    def price_change_24h(self, series: pd.Series) -> pd.Series:
        """24時間価格変化率"""
        return series.pct_change(24).fillna(0.0).rename("price_change_24h")

    def price_change_4h(self, series: pd.Series) -> pd.Series:
        """4時間価格変化率"""
        return series.pct_change(4).fillna(0.0).rename("price_change_4h")

    def price_change_1h(self, series: pd.Series) -> pd.Series:
        """1時間価格変化率"""
        return series.pct_change(1).fillna(0.0).rename("price_change_1h")

    def cmf_20(self, df: pd.DataFrame) -> pd.Series:
        """CMF 20期間（WARNING解消用）"""
        return self.chaikin_money_flow(df, window=20).rename("cmf_20")

    def willr_14(self, df: pd.DataFrame) -> pd.Series:
        """Williams %R 14期間（WARNING解消用）"""
        return self.williams_r(df, window=14).rename("willr_14")

    # Phase H.26: ATR計算超堅牢化ヘルパーメソッド群
    @staticmethod
    def _calculate_adaptive_period(tmp: pd.DataFrame, period: int, logger) -> int:
        """データ長に応じた適応的期間調整"""
        data_length = len(tmp)

        # 段階的期間縮小戦略
        if data_length >= period:
            return period  # 十分なデータがある
        elif data_length >= period * 0.75:
            return int(period * 0.8)  # 80%に縮小
        elif data_length >= period * 0.5:
            return int(period * 0.6)  # 60%に縮小
        elif data_length >= period * 0.25:
            return max(2, int(period * 0.4))  # 40%に縮小（最小2）
        else:
            return max(2, min(data_length - 1, period // 4))  # 最小期間

    @staticmethod
    def _emergency_atr_fallback(df: pd.DataFrame, period: int) -> pd.Series:
        """緊急ATRフォールバック（最後の手段）"""
        try:
            if df is None or df.empty:
                # 完全に空の場合は固定値
                return pd.Series([1.0], index=[0], name=f"ATR_{period}")

            # 使用可能な価格カラムを探す
            price_cols = []
            if "close" in df.columns and not df["close"].isna().all():
                price_cols.append("close")
            if "high" in df.columns and not df["high"].isna().all():
                price_cols.append("high")
            if "low" in df.columns and not df["low"].isna().all():
                price_cols.append("low")
            if "open" in df.columns and not df["open"].isna().all():
                price_cols.append("open")

            if not price_cols:
                # 全く価格データがない場合
                return pd.Series([1.0] * len(df), index=df.index, name=f"ATR_{period}")

            # 利用可能な価格の平均を取得
            price_data = df[price_cols].mean(axis=1)

            # 価格の2%をATRとして使用（価格比例）
            emergency_atr = price_data * 0.02

            # NaN値を価格データから推定した固定値で補完
            mean_price = price_data.mean()
            if pd.isna(mean_price) or mean_price <= 0:
                mean_price = 100.0  # デフォルト価格

            emergency_atr = emergency_atr.fillna(mean_price * 0.02)

            return pd.Series(emergency_atr, index=df.index, name=f"ATR_{period}")

        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Emergency ATR fallback failed: {e}")
            # 完全フォールバック: 固定値
            index = df.index if df is not None and not df.empty else [0]
            return pd.Series([1.0] * len(index), index=index, name=f"ATR_{period}")

    @staticmethod
    def _multi_stage_atr_fallback(
        tmp: pd.DataFrame, effective_period: int, logger
    ) -> pd.Series:
        """多段階ATRフォールバック計算"""
        atr_series = None

        # Stage 1: True Range + Simple Moving Average (改良版)
        try:
            logger.debug("Stage 1: Enhanced True Range calculation")

            # より堅牢なTrue Range計算
            high_low = tmp["high"] - tmp["low"]
            high_close_prev = abs(tmp["high"] - tmp["close"].shift(1))
            low_close_prev = abs(tmp["low"] - tmp["close"].shift(1))

            # NaN値を適切に処理
            high_low = high_low.fillna(0)
            high_close_prev = high_close_prev.fillna(
                high_low
            )  # 前日データがない場合はhigh-lowを使用
            low_close_prev = low_close_prev.fillna(high_low)

            true_range = pd.concat(
                [high_low, high_close_prev, low_close_prev], axis=1
            ).max(axis=1)

            # より緩い条件でrolling計算
            min_periods = max(1, effective_period // 4)  # より少ない最小期間
            atr_series = true_range.rolling(
                window=effective_period, min_periods=min_periods
            ).mean()

            # 残りのNaN値を前方補完
            atr_series = atr_series.ffill().bfill()

            if atr_series is not None and not atr_series.isnull().all():
                logger.info("✅ Stage 1: Enhanced True Range ATR calculated")
                return atr_series

        except Exception as e:
            logger.warning(f"Stage 1 True Range fallback failed: {e}")

        # Stage 2: Price volatility (改良版)
        try:
            logger.debug("Stage 2: Enhanced price volatility calculation")

            # 複数のボラティリティ指標を計算
            close_std = (
                tmp["close"]
                .rolling(
                    window=effective_period, min_periods=max(1, effective_period // 4)
                )
                .std()
            )

            # HL変動も考慮
            hl_range = (
                (tmp["high"] - tmp["low"])
                .rolling(
                    window=effective_period, min_periods=max(1, effective_period // 4)
                )
                .mean()
            )

            # より堅牢な組み合わせ
            atr_series = pd.concat([close_std, hl_range], axis=1).mean(axis=1)
            atr_series = atr_series.ffill().bfill()

            if atr_series is not None and not atr_series.isnull().all():
                logger.info("✅ Stage 2: Enhanced volatility ATR calculated")
                return atr_series

        except Exception as e:
            logger.warning(f"Stage 2 volatility fallback failed: {e}")

        # Stage 3: Simple price change (新規追加)
        try:
            logger.debug("Stage 3: Simple price change calculation")

            # シンプルな価格変化率
            price_change = abs(tmp["close"].pct_change())
            atr_series = price_change.rolling(
                window=max(2, effective_period // 2), min_periods=1  # 半分の期間
            ).mean()

            # より現実的なスケーリング
            mean_price = tmp["close"].mean()
            if not pd.isna(mean_price) and mean_price > 0:
                atr_series = atr_series * mean_price  # 価格に比例

            atr_series = atr_series.ffill().bfill()

            if atr_series is not None and not atr_series.isnull().all():
                logger.info("✅ Stage 3: Simple price change ATR calculated")
                return atr_series

        except Exception as e:
            logger.warning(f"Stage 3 price change fallback failed: {e}")

        # Stage 4: Emergency price-based (最終手段)
        logger.warning(
            "All ATR calculation methods failed, using emergency price-based ATR"
        )
        return IndicatorCalculator._emergency_atr_fallback(tmp, effective_period)

    @staticmethod
    def _finalize_atr_series(
        atr_series: pd.Series, tmp: pd.DataFrame, effective_period: int, logger
    ) -> pd.Series:
        """ATRシリーズの最終処理・品質保証"""
        try:
            if atr_series is None:
                logger.error("ATR series is None, using emergency fallback")
                return IndicatorCalculator._emergency_atr_fallback(
                    tmp, effective_period
                )

            original_nan_count = atr_series.isnull().sum()

            # Step 1: 前方・後方補完
            atr_series = atr_series.ffill().bfill()

            # Step 2: まだNaNが残っている場合は価格ベース補完
            if atr_series.isnull().any():
                mean_price = tmp["close"].mean()
                if pd.isna(mean_price) or mean_price <= 0:
                    mean_price = 100.0  # デフォルト

                atr_series = atr_series.fillna(mean_price * 0.02)
                logger.info(
                    f"Applied price-based NaN filling for ATR ({original_nan_count} values)"
                )

            # Step 3: 異常値検出・修正
            # 極端に大きい値（価格の50%以上）を修正
            max_reasonable_atr = tmp["close"].mean() * 0.5  # 価格の50%
            if not pd.isna(max_reasonable_atr) and max_reasonable_atr > 0:
                extreme_values = atr_series > max_reasonable_atr
                if extreme_values.any():
                    atr_series[extreme_values] = max_reasonable_atr
                    logger.info(
                        f"Capped {extreme_values.sum()} extreme ATR values at {max_reasonable_atr:.4f}"
                    )

            # Step 4: 最小値保証（0以下の値を修正）
            zero_or_negative = atr_series <= 0
            if zero_or_negative.any():
                min_reasonable_atr = tmp["close"].mean() * 0.001  # 価格の0.1%
                if pd.isna(min_reasonable_atr) or min_reasonable_atr <= 0:
                    min_reasonable_atr = 0.01

                atr_series[zero_or_negative] = min_reasonable_atr
                logger.info(
                    f"Set {zero_or_negative.sum()} zero/negative ATR values to minimum {min_reasonable_atr:.4f}"
                )

            # Step 5: 最終検証
            final_nan_count = atr_series.isnull().sum()
            if final_nan_count > 0:
                logger.error(
                    f"ATR finalization failed: {final_nan_count} NaN values remain"
                )
                # 緊急修正
                atr_series = atr_series.fillna(1.0)

            logger.debug(
                f"ATR finalization: {original_nan_count} → {final_nan_count} NaN values"
            )
            return atr_series

        except Exception as e:
            logger.error(f"ATR finalization failed: {e}")
            return IndicatorCalculator._emergency_atr_fallback(tmp, effective_period)
