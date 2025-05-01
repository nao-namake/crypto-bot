import ccxt
import pandas as pd
import numpy as np
import talib
from typing import Optional

class IndicatorCalculator:
    """
    talib をラップして指標を計算し、Series/DataFrame を返す。
    """
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        arr = talib.ATR(
            df["high"].values,
            df["low"].values,
            df["close"].values,
            timeperiod=period
        )
        return pd.Series(arr, index=df.index, name=f"ATR_{period}")

    @staticmethod
    def calculate_bbands(
        df: pd.DataFrame,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0
    ) -> pd.DataFrame:
        upper, middle, lower = talib.BBANDS(
            df["close"].values,
            timeperiod=period,
            nbdevup=nbdevup,
            nbdevdn=nbdevdn,
            matype=0
        )
        return pd.DataFrame(
            {"BB_upper": upper, "BB_middle": middle, "BB_lower": lower},
            index=df.index
        )