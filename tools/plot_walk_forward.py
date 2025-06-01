# =============================================================================
# ファイル名: tools/plot_walk_forward.py
# 説明:
#   ウォークフォワードテストの結果（CSV: walk_forward_metrics.csv）から、
#   各分割セグメントごとのCAGR・Sharpeレシオの推移グラフを自動作成しPNG保存します。
#
# 【主な機能】
#   - ウォークフォワードごとの「CAGR」「Sharpe Ratio」グラフを保存
#   - 結果CSVのコピーも同時に保存（検証用）
#
# 【使い方例】
#   python tools/plot_walk_forward.py --input results/walk_forward_metrics.csv --output results/perf_report
#
# 【前提】
#   - ウォークフォワードの各種メトリクスが "results/walk_forward_metrics.csv" に保存されている
#   - "cagr" および "sharpe" カラムが存在する
#   - "start_date", "end_date" カラムもdatetime型として読込可能
#
# =============================================================================

#!/usr/bin/env python3
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = ['AppleGothic', 'Arial Unicode MS', 'Helvetica', 'sans-serif']

def main():
    parser = argparse.ArgumentParser(description="Plot walk-forward metrics")
    parser.add_argument('--input', '-i', default='results/walk_forward_metrics.csv', help='Path to walk-forward metrics CSV')
    parser.add_argument('--output', '-o', default='results/perf_report', help='Directory to save plots')
    args = parser.parse_args()

    # Load CSV
    df = pd.read_csv(args.input, parse_dates=["start_date", "end_date"])
    df = df.reset_index(drop=True)

    # 保存: 入力したウォークフォワード指標を出力ディレクトリにコピー
    os.makedirs(args.output, exist_ok=True)
    df.to_csv(os.path.join(args.output, "walkforward_metrics_copy.csv"), index=False)

    # CAGR 推移
    plt.figure()
    plt.plot(df.index, df["cagr"], marker="o")
    plt.title("ウォークフォワード別 CAGR 推移")
    plt.xlabel("セグメント番号")
    plt.ylabel("CAGR")
    plt.tight_layout()
    plt.savefig(os.path.join(args.output, "walkforward_cagr.png"))

    # Sharpe 推移
    plt.figure()
    plt.plot(df.index, df["sharpe"], marker="o")
    plt.title("ウォークフォワード別 Sharpe 推移")
    plt.xlabel("セグメント番号")
    plt.ylabel("Sharpe Ratio")
    plt.tight_layout()
    plt.savefig(os.path.join(args.output, "walkforward_sharpe.png"))

if __name__ == "__main__":
    main()
