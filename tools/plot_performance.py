# =============================================================================
# ファイル名: tools/plot_performance.py
# 説明: バックテストや実トレードの取引履歴CSV（trade_log.csvなど）から
#   エクイティカーブ（残高推移）・ドローダウン・主要指標（勝率・シャープレシオ等）を
#   自動で計算・グラフ化し、PNG画像やCSVファイルとして保存するレポート生成ツールです。
# =============================================================================

import argparse
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import variation

matplotlib.rcParams["font.family"] = [
    "AppleGothic",
    "Arial Unicode MS",
    "Helvetica",
    "sans-serif",
]


def load_trade_log(path: Path) -> pd.DataFrame:
    # 日時列を 'entry_time' として読み込む
    df = pd.read_csv(path, parse_dates=["entry_time"])
    # profit 列を pnl と balance 用に複製
    df["pnl"] = df["profit"]
    df["balance"] = df["pnl"].cumsum()  # 初期残高0スタートで累積損益を残高代わりに
    df.sort_values("entry_time", inplace=True)
    df["cum_pnl"] = df["pnl"].cumsum()
    df["cum_balance"] = df["balance"]
    return df.set_index("entry_time")


def draw_equity_curve(df: pd.DataFrame, out_dir: Path):
    fig, ax = plt.subplots()
    df["cum_balance"].plot(ax=ax)
    ax.set_title("Equity Curve")
    ax.set_ylabel("Balance (JPY)")
    fig.tight_layout()
    fig.savefig(out_dir / "equity_curve.png")


def draw_drawdown(df: pd.DataFrame, out_dir: Path):
    running_max = df["cum_balance"].cummax()
    drawdown = df["cum_balance"] - running_max
    fig, ax = plt.subplots()
    drawdown.plot(ax=ax)
    ax.set_title("Drawdown")
    ax.set_ylabel("Drawdown (JPY)")
    fig.tight_layout()
    fig.savefig(out_dir / "drawdown.png")
    return drawdown


def calc_metrics(df: pd.DataFrame) -> pd.Series:
    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] < 0]
    win_rate = len(wins) / len(df) if len(df) > 0 else 0.0
    avg_return = df["pnl"].mean() if len(df) > 0 else 0.0
    expect = (
        wins["pnl"].mean() * win_rate + losses["pnl"].mean() * (1 - win_rate)
        if len(wins) > 0 and len(losses) > 0
        else 0.0
    )
    daily_return = (
        df["pnl"].resample("1D").sum() if not df.empty else pd.Series(dtype=float)
    )
    sharpe = (
        daily_return.mean() / daily_return.std() if daily_return.std() != 0 else 0.0
    )
    max_dd = (
        (df["cum_balance"] - df["cum_balance"].cummax()).min() if not df.empty else 0.0
    )
    return pd.Series(
        {
            "Total Trades": len(df),
            "Win Rate": win_rate,
            "Average Return": avg_return,
            "Expected Value": expect,
            "Sharpe Ratio": sharpe,
            "Max Drawdown": max_dd,
            "Coef of Var": variation(df["pnl"]) if not df.empty else 0.0,
        }
    )


def save_metrics_table(metrics: pd.Series, out_dir: Path):
    tbl_path = out_dir / "metrics.csv"
    metrics.to_csv(tbl_path, header=False)
    print(f"[INFO] metrics saved -> {tbl_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True)
    ap.add_argument("--output", default="./results/perf_report")
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_trade_log(Path(args.log))
    draw_equity_curve(df, out_dir)
    draw_drawdown(df, out_dir)
    metrics = calc_metrics(df)
    save_metrics_table(metrics, out_dir)
    print("[INFO] finished")


if __name__ == "__main__":
    main()
