# crypto_bot/backtest/metrics.py
# 説明:
# バックテスト・ウォークフォワード検証時に使う「評価指標」および
# データ分割用ユーティリティ関数をまとめたモジュールです。
# 最大ドローダウン、CAGR、シャープレシオの計算関数、
# ウォークフォワード分割用のsplit関数が定義されています。

from typing import List, Optional, Tuple
import pandas as pd

def split_walk_forward(
    df: pd.DataFrame, train_window: int, test_window: int, step: int
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    ウォークフォワード検証のためのデータ分割関数。
    dfを「train_window分の学習用」と「test_window分の検証用」に分割し、
    startをstepずつスライドしながら
    (train_df, test_df)のタプルリストを返す。

    Returns
    -------
    splits : list of (train_df, test_df)
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

    Parameters
    ----------
    equity : pd.Series
        資産曲線

    Returns
    -------
    max_dd : float
        最大ドローダウン率（負値）
    """
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    drawdowns = equity / running_max - 1.0
    return float(drawdowns.min() if not drawdowns.empty else 0.0)

def cagr(equity: pd.Series, periods: Optional[int] = None) -> float:
    """
    累積損益時系列 equity の最初と最後から
    期間ごとの平均リターンを計算（CAGR）。

    Parameters
    ----------
    equity : pd.Series
        資産曲線
    periods : int or None
        期間数。未指定ならlen(equity)-1。

    Returns
    -------
    cagr : float
        年率平均成長率（CAGR）
    """
    if equity.empty or equity.iloc[0] <= 0:
        return 0.0

    if periods is None:
        periods = len(equity) - 1

    if periods <= 0:
        return 0.0

    start = equity.iloc[0]
    end = equity.iloc[-1]
    try:
        return (end / start) ** (1.0 / periods) - 1.0
    except Exception:
        return 0.0

def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    リターン系列から年率シャープレシオを計算します。
    無リスク金利は0、分散が極小なら0を返す。

    Parameters
    ----------
    returns : pd.Series
        日次リターン系列
    periods_per_year : int
        1年あたりの期間数（デフォルト252:取引日数）

    Returns
    -------
    sharpe : float
        年率換算シャープレシオ
    """
    if returns.empty:
        return 0.0
    mean_r = returns.mean()
    std_r = returns.std(ddof=0)
    if std_r < 1e-8:
        return 0.0
    annual_factor = periods_per_year**0.5
    return float((mean_r / std_r) * annual_factor)
