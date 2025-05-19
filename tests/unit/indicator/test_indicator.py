import numpy as np
import pandas as pd

from crypto_bot.indicator.calculator import IndicatorCalculator


def test_sma():
    series = pd.Series([1, 2, 3, 4, 5], name="close")
    calc = IndicatorCalculator()
    sma = calc.sma(series, window=3)
    assert np.isclose(sma.iloc[-1], (3 + 4 + 5) / 3)


def test_atr_requires_dataframe():
    df = pd.DataFrame(
        {
            "high": [1, 2, 3, 4, 5],
            "low": [1, 2, 3, 4, 5],
            "close": [1, 2, 3, 4, 5],
        }
    )
    calc = IndicatorCalculator()
    atr = calc.atr(df, window=2)
    assert isinstance(atr, pd.Series)
