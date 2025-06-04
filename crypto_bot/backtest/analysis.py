# crypto_bot/backtest/analysis.py
# 説明:
# このファイルは「トレードログ（trade_log.csv等）」から、日次・週次・月次など期間ごとの
# 集計（トレード数・勝率・平均損益・合計損益）を算出し、CSVとして出力するモジュールです。
# 分析やレポート作成などの自動化にも使えます。

import pandas as pd


def preprocess_trade_log(df: pd.DataFrame) -> pd.DataFrame:
    """entry_timeをdatetime化し、exit_timeを計算して返す"""
    df = df.copy()
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    # duration_barsが分単位で記録されている前提
    df["exit_time"] = df["entry_time"] + pd.to_timedelta(
        df["duration_bars"], unit="min"
    )
    return df


def aggregate_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """
    指定した期間単位（period: 'D'=日次, 'W'=週次, 'ME'=月次）で集計します。
    出力: トレード数・勝率・平均リターン・合計損益
    """
    # 'M'（月末）→ 'ME'（MonthEnd）に統一
    if period == "M":
        period = "ME"
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
    """
    # 'M'（月次）は将来廃止予定なので 'ME' を使う
    for freq, name in [("D", "daily"), ("W", "weekly"), ("ME", "monthly")]:
        agg = aggregate_by_period(df, freq)
        agg.to_csv(f"{out_prefix}_{name}.csv")
