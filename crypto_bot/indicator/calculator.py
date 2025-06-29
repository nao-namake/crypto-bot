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
        """平均真の範囲 (ATR) を返す。"""
        tmp = df[["high", "low", "close"]].astype("float64")
        try:
            atr_series = ta.atr(
                high=tmp["high"],
                low=tmp["low"],
                close=tmp["close"],
                length=period,
            )
        except Exception:
            atr_series = None
        # None が返ってきた場合のフォールバック
        if atr_series is None or atr_series.isnull().all():
            # 終値の標準偏差を代わりに使用（近似）
            atr_series = tmp["close"].rolling(period).std()
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
