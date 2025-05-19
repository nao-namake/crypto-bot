from typing import List, Optional, Tuple

import pandas as pd


def split_walk_forward(
    df: pd.DataFrame, train_window: int, test_window: int, step: int
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    df を「train_window 本分の学習用」と
    「次の test_window 本分の検証用」に分割し、
    start を step ずつスライドしながら
    (train_df, test_df) のリストを返す。
    """
    splits: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
    start = 0
    length = len(df)
    while start + train_window + test_window <= length:
        train_df = df.iloc[start : start + train_window]
        test_df = df.iloc[start + train_window : start + train_window + test_window]
        splits.append((train_df, test_df))
        start += step
    return splits


def max_drawdown(equity: pd.Series) -> float:
    """
    時系列 equity（累積損益＋初期残高）から
    最大ドローダウン（率：負の値）を計算して返す。
    """
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    # ドローダウン率 = equity / running_max - 1
    drawdowns = equity / running_max - 1.0
    return float(drawdowns.min() if not drawdowns.empty else 0.0)


def cagr(equity: pd.Series, periods: Optional[int] = None) -> float:
    """
    累積損益時系列 equity の最初と最後から
    期間ごとの平均リターンを計算（CAGR）。
    - periods を指定しない場合は len(equity)-1 を用いる。
    - 要素数 < 2 か、初期値 <= 0 の場合は 0 を返す。
    """
    if equity.empty or equity.iloc[0] <= 0:
        return 0.0

    # 期間数を決定
    if periods is None:
        periods = len(equity) - 1

    if periods <= 0:
        return 0.0

    start = equity.iloc[0]
    end = equity.iloc[-1]
    try:
        # (end/start)^(1/periods) - 1
        return (end / start) ** (1.0 / periods) - 1.0
    except Exception:
        return 0.0


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    リターン系列 returns（日次など）から
    年率シャープレシオを計算。無リスク金利は 0 とする。
    分散が極小（定常系列）なら 0 を返す。
    """
    if returns.empty:
        return 0.0
    mean_r = returns.mean()
    std_r = returns.std(ddof=0)
    # 分散がほぼゼロ（定常系列）なら 0 を返す
    if std_r < 1e-8:
        return 0.0
    annual_factor = periods_per_year**0.5
    return float((mean_r / std_r) * annual_factor)
