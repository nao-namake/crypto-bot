import pandas as pd


def make_regression_target(df: pd.DataFrame, horizon: int) -> pd.Series:
    """
    N期間後のリターン (close_t+horizon / close_t) - 1 を返す。
    最後の horizon 件は NaN。
    """
    future = df["close"].shift(-horizon)
    ret = future / df["close"] - 1.0
    return ret.rename(f"return_{horizon}")


def make_classification_target(
    df: pd.DataFrame, horizon: int, threshold: float = 0.0
) -> pd.Series:
    """
    N期間後のリターン > threshold なら 1, それ以外は 0 のラベルを返す。
    """
    future = df["close"].shift(-horizon)
    ret = future / df["close"] - 1.0
    label = (ret > threshold).astype(int)
    return label.rename(f"up_{horizon}")
