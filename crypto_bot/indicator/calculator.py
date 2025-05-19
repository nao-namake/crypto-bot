# crypto_bot/indicator/calculator.py

import pandas as pd
import talib


class IndicatorCalculator:
    """
    Talib をラップして指標を計算し、Series/DataFrame を返す。
    """

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        平均真の範囲 (ATR) を計算して返す。
        """
        high = df["high"].astype("float64").values
        low = df["low"].astype("float64").values
        close = df["close"].astype("float64").values

        arr = talib.ATR(high, low, close, timeperiod=period)
        return pd.Series(arr, index=df.index, name=f"ATR_{period}")

    @staticmethod
    def calculate_bbands(
        df: pd.DataFrame, period: int = 20, nbdevup: float = 2.0, nbdevdn: float = 2.0
    ) -> pd.DataFrame:
        """
        ボリンジャーバンド (BBANDS) を計算して返す。
        """
        close = df["close"].astype("float64").values

        upper, middle, lower = talib.BBANDS(
            close,
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=0,
        )
        return pd.DataFrame(
            {"BB_upper": upper, "BB_middle": middle, "BB_lower": lower},
            index=df.index,
        )

    def sma(self, series: pd.Series, window: int) -> pd.Series:
        """
        単純移動平均 (SMA)
        """
        return series.rolling(window=window, min_periods=window).mean()

    def ema(self, series: pd.Series, window: int) -> pd.Series:
        """
        指数移動平均 (EMA)
        """
        return series.ewm(span=window, adjust=False, min_periods=window).mean()

    def atr(self, df: pd.DataFrame, window: int = 14) -> pd.Series:
        """
        DataFrame チェック付きの ATR ラッパー。
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("atr requires a pandas DataFrame")
        return self.calculate_atr(df, period=window)

    def bbands(
        self,
        df: pd.DataFrame,
        window: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0,
    ) -> pd.DataFrame:
        """
        DataFrame チェック付きの BBANDS ラッパー。
        """
        if not isinstance(df, pd.DataFrame):
            raise TypeError("bbands requires a pandas DataFrame")
        return self.calculate_bbands(
            df, period=window, nbdevup=nbdevup, nbdevdn=nbdevdn
        )
