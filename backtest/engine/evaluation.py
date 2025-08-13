"""
バックテスト評価・分析統合モジュール
metrics.py と analysis.py を統合し、バックテスト結果の評価を一元化
"""

from typing import List, Optional, Tuple

import pandas as pd


# =============================================================================
# データ分割機能（旧metrics.pyから）
# =============================================================================

def split_walk_forward(
    df: pd.DataFrame, train_window: int, test_window: int, step: int
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    ウォークフォワード検証のためのデータ分割関数。
    dfを「train_window分の学習用」と「test_window分の検証用」に分割し、
    startをstepずつスライドしながら
    (train_df, test_df)のタプルリストを返す。

    Parameters
    ----------
    df : pd.DataFrame
        分割対象のデータフレーム
    train_window : int
        学習用データの期間数
    test_window : int
        テスト用データの期間数  
    step : int
        スライドステップ数

    Returns
    -------
    splits : List[Tuple[pd.DataFrame, pd.DataFrame]]
        (train_df, test_df) のタプルリスト
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


# =============================================================================
# 評価指標計算機能（旧metrics.pyから）
# =============================================================================

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


def calculate_win_rate(trade_df: pd.DataFrame) -> float:
    """
    勝率を計算

    Parameters
    ----------
    trade_df : pd.DataFrame
        取引記録DataFrame（'profit'列必須）

    Returns
    -------
    win_rate : float
        勝率（0.0-1.0）
    """
    if trade_df.empty or 'profit' not in trade_df.columns:
        return 0.0
    
    winning_trades = (trade_df['profit'] > 0).sum()
    total_trades = len(trade_df)
    
    return float(winning_trades / total_trades) if total_trades > 0 else 0.0


def calculate_profit_factor(trade_df: pd.DataFrame) -> float:
    """
    プロフィットファクターを計算

    Parameters
    ----------
    trade_df : pd.DataFrame
        取引記録DataFrame（'profit'列必須）

    Returns
    -------
    profit_factor : float
        プロフィットファクター
    """
    if trade_df.empty or 'profit' not in trade_df.columns:
        return 0.0
    
    gross_profit = trade_df[trade_df['profit'] > 0]['profit'].sum()
    gross_loss = abs(trade_df[trade_df['profit'] < 0]['profit'].sum())
    
    return float(gross_profit / gross_loss) if gross_loss > 0 else float('inf')


def calculate_average_trade(trade_df: pd.DataFrame) -> dict:
    """
    平均トレード統計を計算

    Parameters
    ----------
    trade_df : pd.DataFrame
        取引記録DataFrame

    Returns
    -------
    stats : dict
        平均トレード統計
    """
    if trade_df.empty:
        return {
            'avg_profit': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'avg_duration': 0.0
        }
    
    stats = {}
    
    if 'profit' in trade_df.columns:
        stats['avg_profit'] = float(trade_df['profit'].mean())
        win_trades = trade_df[trade_df['profit'] > 0]['profit']
        loss_trades = trade_df[trade_df['profit'] < 0]['profit']
        stats['avg_win'] = float(win_trades.mean() if not win_trades.empty else 0.0)
        stats['avg_loss'] = float(loss_trades.mean() if not loss_trades.empty else 0.0)
    
    if 'duration_bars' in trade_df.columns:
        stats['avg_duration'] = float(trade_df['duration_bars'].mean())
    
    return stats


# =============================================================================
# トレードログ分析機能（旧analysis.pyから）
# =============================================================================

def preprocess_trade_log(df: pd.DataFrame) -> pd.DataFrame:
    """
    entry_timeをdatetime化し、exit_timeを計算して返す
    
    Parameters
    ----------
    df : pd.DataFrame
        取引ログデータフレーム

    Returns
    -------
    processed_df : pd.DataFrame
        前処理済みデータフレーム
    """
    df = df.copy()
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    # duration_barsが分単位で記録されている前提
    if "duration_bars" in df.columns:
        df["exit_time"] = df["entry_time"] + pd.to_timedelta(
            df["duration_bars"], unit="min"
        )
    return df


def aggregate_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    指定した期間単位（period: 'D'=日次, 'W'=週次, 'M'=月次）で集計します。
    出力: トレード数・勝率・平均リターン・合計損益

    Parameters
    ----------
    df : pd.DataFrame
        取引ログデータフレーム
    period : str
        集計期間（'D', 'W', 'M'）

    Returns
    -------
    aggregated_df : pd.DataFrame
        期間別集計結果
    """
    # 'ME'（MonthEnd）→ 'M'（月末）に変換（CI環境互換性）
    if period == "ME":
        period = "M"
    
    df = preprocess_trade_log(df).set_index("exit_time")
    agg = df.groupby(pd.Grouper(freq=period)).apply(
        lambda g: {
            "trades": len(g),
            "win_rate": (g["profit"] > 0).mean() if len(g) > 0 else 0.0,
            "avg_return": g["profit"].mean() if len(g) > 0 else 0.0,
            "total_pl": g["profit"].sum(),
        }
    )
    return pd.DataFrame(list(agg.values), index=agg.index)


def export_aggregates(df: pd.DataFrame, out_prefix: str):
    """
    日次・週次・月次の3パターンで集計してCSV出力

    Parameters
    ----------
    df : pd.DataFrame
        取引ログデータフレーム
    out_prefix : str
        出力ファイルのプレフィックス
    """
    # CI環境互換性のため 'M' を使用
    for freq, name in [("D", "daily"), ("W", "weekly"), ("M", "monthly")]:
        agg = aggregate_by_period(df, freq)
        agg.to_csv(f"{out_prefix}_{name}.csv")


# =============================================================================
# 統合評価レポート機能（新機能）
# =============================================================================

def generate_backtest_report(
    portfolio_values: pd.Series,
    trade_df: pd.DataFrame,
    starting_balance: float = 1000000
) -> dict:
    """
    包括的なバックテストレポートを生成

    Parameters
    ----------
    portfolio_values : pd.Series
        ポートフォリオ価値時系列
    trade_df : pd.DataFrame
        取引記録
    starting_balance : float
        初期残高

    Returns
    -------
    report : dict
        包括的なレポート
    """
    if portfolio_values.empty:
        return {}
    
    # リターン計算
    returns = portfolio_values.pct_change().dropna()
    total_return = (portfolio_values.iloc[-1] / starting_balance) - 1
    
    # 基本統計
    report = {
        'performance': {
            'starting_balance': starting_balance,
            'ending_balance': float(portfolio_values.iloc[-1]),
            'total_return': float(total_return),
            'total_return_pct': float(total_return * 100),
            'cagr': cagr(portfolio_values),
            'max_drawdown': max_drawdown(portfolio_values),
            'sharpe_ratio': sharpe_ratio(returns)
        },
        'trading': {
            'total_trades': len(trade_df),
            'win_rate': calculate_win_rate(trade_df),
            'profit_factor': calculate_profit_factor(trade_df),
        },
        'average_trade': calculate_average_trade(trade_df)
    }
    
    # 月別分析（可能な場合）
    if not trade_df.empty and 'entry_time' in trade_df.columns:
        monthly_agg = aggregate_by_period(trade_df, 'M')
        if not monthly_agg.empty:
            report['monthly_stats'] = {
                'avg_monthly_trades': float(monthly_agg['trades'].mean()),
                'avg_monthly_return': float(monthly_agg['avg_return'].mean()),
                'best_month': float(monthly_agg['total_pl'].max()),
                'worst_month': float(monthly_agg['total_pl'].min())
            }
    
    return report


def print_backtest_summary(report: dict):
    """
    バックテストレポートのサマリーを表示

    Parameters
    ----------
    report : dict
        generate_backtest_report() の出力
    """
    if not report:
        print("レポートデータが空です")
        return
    
    print("=" * 60)
    print("🎯 バックテスト結果サマリー")
    print("=" * 60)
    
    if 'performance' in report:
        perf = report['performance']
        print(f"初期残高:     {perf.get('starting_balance', 0):,.0f} 円")
        print(f"最終残高:     {perf.get('ending_balance', 0):,.0f} 円")
        print(f"総リターン:   {perf.get('total_return_pct', 0):.2f}%")
        print(f"CAGR:         {perf.get('cagr', 0):.4f}")
        print(f"最大DD:       {perf.get('max_drawdown', 0):.4f}")
        print(f"シャープ:     {perf.get('sharpe_ratio', 0):.4f}")
    
    if 'trading' in report:
        trading = report['trading']
        print(f"総取引数:     {trading.get('total_trades', 0)}")
        print(f"勝率:         {trading.get('win_rate', 0):.2%}")
        print(f"PF:           {trading.get('profit_factor', 0):.2f}")
    
    if 'average_trade' in report:
        avg = report['average_trade']
        print(f"平均損益:     {avg.get('avg_profit', 0):,.0f} 円")
        print(f"平均勝ち:     {avg.get('avg_win', 0):,.0f} 円") 
        print(f"平均負け:     {avg.get('avg_loss', 0):,.0f} 円")
    
    print("=" * 60)