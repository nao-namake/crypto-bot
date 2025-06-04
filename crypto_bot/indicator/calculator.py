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
