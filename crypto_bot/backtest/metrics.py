import pandas as pd
from typing import List, Tuple

def split_walk_forward(
    df: pd.DataFrame,
    train_window: int,
    test_window: int,
    step: int
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    df を「train_window 本分の学習用」と
    「次の test_window 本分の検証用」に分割し、
    start を step ずつスライドしながら
    (train_df, test_df) のリストを返す。
    """
    splits = []
    start = 0
    length = len(df)
    while start + train_window + test_window <= length:
        train_df = df.iloc[start : start + train_window]
        test_df  = df.iloc[
            start + train_window : start + train_window + test_window
        ]
        splits.append((train_df, test_df))
        start += step
    return splits

def max_drawdown(equity: pd.Series) -> float:
    """時系列 equity（累積損益＋初期残高）から最大ドローダウンを計算"""
    running_max = equity.cummax()
    drawdowns   = running_max - equity
    return drawdowns.max()

def cagr(equity: pd.Series, days: int) -> float:
    """
    累積損益時系列 equity の最初と最後から CAGR を計算。
    days が 0 以下、または最初の equity が 0 以下の場合は 0 を返す。
    """
    if days <= 0 or equity.empty or equity.iloc[0] <= 0:
        return 0.0
    start = equity.iloc[0]
    end   = equity.iloc[-1]
    # 年率換算
    try:
        return (end / start) ** (365.0 / days) - 1.0
    except Exception:
        return 0.0

def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    リターンの時系列 returns（日次リターンなど）から
    年率シャープレシオを計算。無リスク金利は 0 とする。
    """
    if returns.empty:
        return 0.0
    mean_r = returns.mean()
    std_r  = returns.std(ddof=0)
    if std_r == 0:
        return 0.0
    return (mean_r / std_r) * (periods_per_year**0.5)