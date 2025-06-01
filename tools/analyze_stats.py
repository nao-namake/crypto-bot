#!/usr/bin/env python3
# =============================================================================
# ファイル名: tools/analyze_stats.py
# 説明:
#   バックテストやウォークフォワード結果（csvやレポートファイル）から
#   基本統計量やヒストグラム・箱ひげ図などを自動生成する分析スクリプトです。
#
# 【用途】
#   - 戦略の利益分布・リスクをすぐに可視化したいとき
#   - ウォークフォワード/最適化の結果を素早く要約したいとき
#
# 【使い方例】
#   python tools/analyze_stats.py -i results/backtest_results.csv
#   python tools/analyze_stats.py --input results/walk_forward_metrics.csv
#   # テキストレポートからでもOK:
#   python tools/analyze_stats.py -i some_report.txt
#
# 使うと
#   - カラム名の一覧表示
#   - 純利益などの統計量（平均・分散・標準偏差・分位点）
#   - シャープレシオやCAGRの平均も自動集計
#   - ヒストグラムや箱ひげ図のグラフ表示
# =============================================================================

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
import argparse

def read_table(path):
    # CSV or レポートファイル自動判定
    if path.endswith('.csv'):
        df = pd.read_csv(path)
        # もし 'start_date' カラムが日付っぽい場合
        if 'start_date' in df.columns:
            try:
                df['start_date'] = pd.to_datetime(df['start_date'])
            except Exception:
                pass
        if 'end_date' in df.columns:
            try:
                df['end_date'] = pd.to_datetime(df['end_date'])
            except Exception:
                pass
        return df
    else:
        # テーブル抽出式（backtest_results.txtなど用）
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        table_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("start_date"):
                table_start = i
                break
        if table_start is None:
            raise RuntimeError("テーブル部分が見つかりません。")
        table_lines = []
        for line in lines[table_start:]:
            if not line.strip():
                break
            table_lines.append(line)
        table_str = "".join(table_lines)
        df = pd.read_csv(StringIO(table_str), sep=r"\s+", engine='python', parse_dates=['start_date', 'end_date'])
        return df

def main():
    parser = argparse.ArgumentParser(description="バックテストまたはウォークフォワードcsvの統計分析")
    parser.add_argument('--input', '-i', default="backtest_results.csv", help="分析対象ファイル（csvまたはレポート）")
    args = parser.parse_args()

    file_path = args.input
    if not os.path.isfile(file_path):
        print(f"Error: ファイルが見つかりません: {file_path!r}")
        sys.exit(1)

    # テーブル読み込み
    try:
        df = read_table(file_path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("=== 読み込んだカラム一覧 ===")
    print(list(df.columns))

    # 取引なし（total_profit == 0）があれば除外（なければそのまま）
    if "total_profit" in df.columns:
        df = df[df["total_profit"] != 0]
        print(f"\n=== '取引なし' 除外後の期間数: {len(df)} ===")
        main_col = "total_profit"
    elif "final_profit" in df.columns:
        main_col = "final_profit"
    else:
        print("純利益カラムが見つかりません (total_profit, final_profit)")
        sys.exit(1)

    # 基本統計量
    print("\n=== 基本統計量 ===")
    print(df[main_col].describe())
    # 四分位数, 分散, 標準偏差
    q1, q2, q3 = df[main_col].quantile([0.25, 0.5, 0.75])
    var_val = df[main_col].var()
    std_val = df[main_col].std()
    print(f"1st Quartile (Q1) : {q1:.6f}")
    print(f"Median (Q2)       : {q2:.6f}")
    print(f"3rd Quartile (Q3) : {q3:.6f}")
    print(f"分散 (Variance)   : {var_val:.6f}")
    print(f"標準偏差 (StdDev) : {std_val:.6f}")

    # 追加分析例: シャープレシオ・CAGRがあれば
    if "sharpe" in df.columns:
        win_rate = (df["sharpe"] > 0).mean()
        print(f"勝率 (sharpe>0)   : {win_rate:.4f}")
    if "cagr" in df.columns:
        print(f"CAGR 平均         : {df['cagr'].mean():.6f}")

    # ヒストグラム
    plt.figure(figsize=(8, 4))
    plt.hist(df[main_col], bins=20)
    plt.xlabel(main_col)
    plt.ylabel("Frequency")
    plt.title(f"Histogram of {main_col}")
    plt.tight_layout()
    plt.show()

    # 箱ひげ図
    plt.figure(figsize=(4, 6))
    plt.boxplot(df[main_col], vert=True)
    plt.ylabel(main_col)
    plt.title(f"Boxplot of {main_col}")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
