# crypto_bot/scripts/plot_equity.py
# 説明:
# バックテスト結果のCSVファイル（例: backtest_results.csv）から
# 累積損益やエクイティカーブ（資産推移）の折れ線グラフを作成するスクリプトです。
#
# 使い方（例）:
#   python scripts/plot_equity.py -c ./results/backtest_results.csv --equity
#
# ポイント:
# ・CSVの "equity" 列 or "total_profit" 列を自動で検出してグラフ化
# ・Jupyterではなく「ターミナル用」なので、コマンドライン引数でCSVを指定
# ・matplotlib でグラフ描画

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt

def main():
    parser = argparse.ArgumentParser(
        description="バックテスト結果CSVからグラフを作成します"
    )
    parser.add_argument(
        "-c", "--csv",
        dest="csv_path",
        default="backtest_results.csv",
        help="バックテスト結果CSVのパス（デフォルト: backtest_results.csv）"
    )
    parser.add_argument(
        "--equity",
        action="store_true",
        help="equity カラムがあればエクイティカーブを折れ線でプロット"
    )
    args = parser.parse_args()

    csv_path = args.csv_path
    if not os.path.isfile(csv_path):
        print(f"Error: CSVファイルが見つかりません: {csv_path!r}")
        return

    df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
    print("=== DataFrame head ===")
    print(df.head())
    print("\n=== Index & Columns ===")
    print(f"Index: {df.index}")
    print(f"Columns: {list(df.columns)}")

    # どのカラムをプロットするか選択
    if args.equity and "equity" in df.columns:
        y = df["equity"]
        label = "Equity"
        ylabel = "Equity"
        title = "Equity Curve"
    elif "total_profit" in df.columns:
        y = df["total_profit"].cumsum()  # 累積利益に変更
        label = "Cumulative Profit"
        ylabel = "Cumulative Profit"
        title = "Cumulative Profit Over All Splits"
    else:
        print("プロット可能なカラム（'equity' or 'total_profit'）がありません。")
        return

    # １枚の折れ線グラフで全期間をまとめて描画
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, y, marker="o", label=label)
    plt.xlabel("Index")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
