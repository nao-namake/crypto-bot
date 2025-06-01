# =============================================================================
# ファイル名: tools/sweep_thresholds.py
# 説明:
#   ML戦略の「しきい値（threshold）」を複数パターンで一括検証し、
#   各しきい値での平均損益(mean_total_profit)を集計する自動スクリプト。
#
#   - config/default.yml に「thresholds_to_test」を事前に用意
#   - 各しきい値ごとに一時設定ファイルを作成→バックテスト実行
#   - レポートから成績を抽出・集計して results/threshold_sweep.csv に保存
#
# 【使い方例】
#   python tools/sweep_thresholds.py
#
# 【出力例】
#   results/threshold_sweep.csv
#
# 【備考】
#   - スクリプト実行前に main/backtest の動作確認推奨
#   - バックテスト実行毎に "trade_log.csv" が一時的に再生成されます
# =============================================================================

#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import pandas as pd
import re
from io import StringIO
import yaml

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
BASE_CONFIG  = os.path.join(PROJECT_ROOT, "config", "default.yml")

def run_backtest_and_capture(cfg_path: str) -> str:
    """
    一時的に書き出した設定ファイルを使ってバックテストを実行し、
    stdout 全文を文字列で返す。
    """
    cmd = [
        sys.executable, "-m", "crypto_bot.main",
        "backtest", "-c", cfg_path
    ]
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    out = proc.stdout.decode("utf-8", errors="ignore")

    # subprocess実行ログを表示（追加）
    print("=== subprocess stdout ===")
    print(out)
    print("=========================")

    if proc.returncode != 0:
        raise SystemExit(f"Error: backtest failed (exit code {proc.returncode})")
    return out

def extract_table(report: str) -> pd.DataFrame:
    """
    バックテストの全文レポートから末尾の
    'start_date ... total_profit' で始まるテーブルを切り出し、
    DataFrame にパースして返す。
    """
    lines = report.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*start_date\s+end_date\s+total_profit", line):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("テーブル部分が見つかりませんでした。")

    table_lines = []
    for line in lines[header_idx:]:
        if not line.strip():
            break
        table_lines.append(line.lstrip())

    buf = StringIO("\n".join(table_lines))
    df = pd.read_csv(
        buf,
        sep=r'\s+',
        parse_dates=["start_date", "end_date"]
    )
    return df

def main():
    old_log = os.path.join(PROJECT_ROOT, "results", "trade_log.csv")
    if os.path.exists(old_log):
        os.remove(old_log)

    with open(BASE_CONFIG) as f:
        orig_cfg = yaml.safe_load(f)

    try:
        thresholds = orig_cfg["strategy"]["params"]["thresholds_to_test"]
    except KeyError:
        sys.exit("Error: config/default.yml に thresholds_to_test が定義されていません。")

    results = []

    for thr in thresholds:
        cfg = orig_cfg.copy()
        cfg["strategy"]["params"]["threshold"] = float(thr)
        cfg.setdefault("backtest", {})["trade_log_csv"] = "results/trade_log.csv"

        fd, tmp_cfg = tempfile.mkstemp(prefix="cfg_", suffix=".yml")
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

        # 生成した一時設定ファイルのパスを表示（追加）
        print(f"🟡 Generated temp config file: {tmp_cfg}")

        print(f"▶ Running backtest with threshold={thr} …")
        try:
            report = run_backtest_and_capture(tmp_cfg)
        except SystemExit:
            print(f"⚠️ Threshold {thr}: no trades or error, skipping.")
            # os.remove(tmp_cfg)  # 一時的に削除をコメントアウト
            continue
        # os.remove(tmp_cfg)  # 一時的に削除をコメントアウト

        try:
            df = extract_table(report)
        except ValueError:
            print(f"⚠️ Threshold {thr}: レポートテーブル抽出失敗、スキップ")
            continue

        results.append({
            "threshold": thr,
            "mean_total_profit": df["total_profit"].mean()
        })

    out_df = pd.DataFrame(results).set_index("threshold")
    out_path = os.path.join(PROJECT_ROOT, "results", "threshold_sweep.csv")
    out_df.to_csv(out_path)

    print("\n=== Sweep Results ===")
    print(out_df.to_string())
    print(f"\nResults saved to {out_path}")

if __name__ == "__main__":
    main()
