#!/usr/bin/env python3
"""
シグナルシミュレーション - Phase 75

戦略シグナルとML品質フィルタの判断が正しかったかを事後検証する。
bitbank Public APIから15分足データを取得し、Triple Barrierでシミュレーション。

使い方:
    # 直近7日間（デフォルト）
    python3 scripts/analysis/signal_simulation.py

    # 期間指定
    python3 scripts/analysis/signal_simulation.py --start 2026-03-25 --end 2026-04-01

    # 日数指定
    python3 scripts/analysis/signal_simulation.py --days 14

    # TP/SL距離カスタム
    python3 scripts/analysis/signal_simulation.py --tp 50000 --sl 33000

    # GCPログからシグナルも取得して表示
    python3 scripts/analysis/signal_simulation.py --with-signals
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def fetch_bitbank_candles(start_date: str, end_date: str) -> pd.DataFrame:
    """bitbank Public APIから15分足データを取得"""
    all_candles = []
    current = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    while current <= end:
        date_str = current.strftime("%Y%m%d")
        url = f"https://public.bitbank.cc/btc_jpy/candlestick/15min/{date_str}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            if data.get("success") == 1:
                ohlcv = data["data"]["candlestick"][0]["ohlcv"]
                for c in ohlcv:
                    all_candles.append(
                        {
                            "open": float(c[0]),
                            "high": float(c[1]),
                            "low": float(c[2]),
                            "close": float(c[3]),
                            "volume": float(c[4]),
                            "timestamp": int(c[5]),
                        }
                    )
            time.sleep(0.3)
        except Exception as e:
            print(f"  {date_str}: 取得エラー {e}")
        current += timedelta(days=1)

    if not all_candles:
        return pd.DataFrame()

    df = pd.DataFrame(all_candles)
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("datetime").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def simulate_triple_barrier(
    df: pd.DataFrame,
    entry_idx: int,
    action: str,
    tp_dist: float,
    sl_dist: float,
    max_bars: int = 20,
) -> dict:
    """Triple Barrierシミュレーション"""
    entry_price = float(df["close"].iloc[entry_idx])

    if action == "BUY":
        tp_price = entry_price + tp_dist
        sl_price = entry_price - sl_dist
    else:
        tp_price = entry_price - tp_dist
        sl_price = entry_price + sl_dist

    end_idx = min(entry_idx + max_bars + 1, len(df))
    for j in range(entry_idx + 1, end_idx):
        bars = j - entry_idx
        h = float(df["high"].iloc[j])
        lo = float(df["low"].iloc[j])

        if action == "BUY":
            if h >= tp_price:
                return {"result": "TP", "bars": bars, "entry": entry_price, "exit": tp_price}
            if lo <= sl_price:
                return {"result": "SL", "bars": bars, "entry": entry_price, "exit": sl_price}
        else:
            if lo <= tp_price:
                return {"result": "TP", "bars": bars, "entry": entry_price, "exit": tp_price}
            if h >= sl_price:
                return {"result": "SL", "bars": bars, "entry": entry_price, "exit": sl_price}

    return {"result": "TIMEOUT", "bars": max_bars, "entry": entry_price, "exit": entry_price}


def fetch_gcp_signals(days: int = 7) -> list:
    """GCPログから品質フィルタシグナルを取得"""
    import subprocess

    signals = []

    for log_type, filter_name in [
        ("品質フィルタ通過", "通過"),
        ("品質フィルタ拒否", "拒否"),
        ("品質フィルタ中間", "中間"),
    ]:
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type=cloud_run_revision AND textPayload:"{log_type}"',
                    "--limit=50",
                    "--format=value(timestamp,textPayload)",
                    f"--freshness={days}d",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            for line in result.stdout.strip().split("\n"):
                if not line or "品質フィルタ" not in line:
                    continue

                # アクション抽出
                action = None
                if " BUY " in line or "BUY→" in line or "- BUY" in line:
                    action = "BUY"
                elif " SELL " in line or "SELL→" in line or "- SELL" in line:
                    action = "SELL"
                if not action:
                    continue

                # ML信頼度を抽出
                ml_conf = 0.5
                if "信頼度=" in line:
                    try:
                        conf_str = (
                            line.split("信頼度=")[1].split(" ")[0].split(",")[0].split(")")[0]
                        )
                        ml_conf = float(conf_str)
                    except (IndexError, ValueError):
                        pass

                # UTC タイムスタンプを抽出（format: 2026-03-31T17:45:13.117920Z）
                time_str = ""
                try:
                    # タブ区切りの最初の部分がUTCタイムスタンプ
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        utc_str = parts[0].strip()
                        # UTCをJSTに変換
                        utc_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
                        jst_dt = utc_dt + timedelta(hours=9)
                        time_str = jst_dt.strftime("%Y-%m-%d %H:%M")
                except (IndexError, ValueError):
                    pass

                if time_str:
                    signals.append(
                        {
                            "time": time_str,
                            "action": action,
                            "filter": filter_name,
                            "ml_conf": ml_conf,
                        }
                    )
        except Exception as e:
            print(f"  GCPログ取得エラー ({log_type}): {e}")

    return signals


def run_full_simulation(
    df: pd.DataFrame, tp_dist: float, sl_dist: float, max_bars: int, tp_pnl: float, sl_pnl: float
) -> dict:
    """全足でのシミュレーション（戦略シグナル関係なく全エントリーポイント）"""
    n = len(df)
    buy_wins, buy_losses, buy_timeouts = 0, 0, 0
    sell_wins, sell_losses, sell_timeouts = 0, 0, 0

    for i in range(n - max_bars - 1):
        # BUYシミュレーション
        r = simulate_triple_barrier(df, i, "BUY", tp_dist, sl_dist, max_bars)
        if r["result"] == "TP":
            buy_wins += 1
        elif r["result"] == "SL":
            buy_losses += 1
        else:
            buy_timeouts += 1

        # SELLシミュレーション
        r = simulate_triple_barrier(df, i, "SELL", tp_dist, sl_dist, max_bars)
        if r["result"] == "TP":
            sell_wins += 1
        elif r["result"] == "SL":
            sell_losses += 1
        else:
            sell_timeouts += 1

    return {
        "buy": {"wins": buy_wins, "losses": buy_losses, "timeouts": buy_timeouts},
        "sell": {"wins": sell_wins, "losses": sell_losses, "timeouts": sell_timeouts},
    }


def main():
    parser = argparse.ArgumentParser(description="シグナルシミュレーション")
    parser.add_argument("--start", type=str, help="開始日 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="終了日 (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=7, help="日数（--start未指定時に使用）")
    parser.add_argument("--tp", type=float, default=50000, help="TP距離（円）")
    parser.add_argument("--sl", type=float, default=33000, help="SL距離（円）")
    parser.add_argument("--max-bars", type=int, default=20, help="最大保有本数")
    parser.add_argument("--tp-pnl", type=float, default=750, help="TP時PnL（円）")
    parser.add_argument("--sl-pnl", type=float, default=500, help="SL時PnL（円）")
    parser.add_argument("--with-signals", action="store_true", help="GCPログからシグナルも取得")
    parser.add_argument("--full", action="store_true", help="全足でBUY/SELLシミュレーション")
    args = parser.parse_args()

    # 期間決定
    if args.start and args.end:
        start_date = args.start
        end_date = args.end
    else:
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=args.days)
        start_date = start_dt.strftime("%Y-%m-%d")
        end_date = end_dt.strftime("%Y-%m-%d")

    print(f"期間: {start_date} ~ {end_date}")
    print(f"TP距離: ¥{args.tp:,.0f} / SL距離: ¥{args.sl:,.0f} / 最大{args.max_bars}本")

    # データ取得
    print("\nbitbank APIからデータ取得中...")
    df = fetch_bitbank_candles(start_date, end_date)
    if df.empty:
        print("データ取得失敗")
        return

    print(f"取得: {len(df)}件, {df.index[0]} ~ {df.index[-1]}")
    print(f"価格: ¥{df['close'].min():,.0f} ~ ¥{df['close'].max():,.0f}")

    # 全足シミュレーション
    if args.full:
        print(f"\n{'='*70}")
        print("全足BUY/SELLシミュレーション（市場特性分析）")
        print(f"{'='*70}")

        stats = run_full_simulation(df, args.tp, args.sl, args.max_bars, args.tp_pnl, args.sl_pnl)

        for direction in ["buy", "sell"]:
            s = stats[direction]
            total = s["wins"] + s["losses"] + s["timeouts"]
            decided = s["wins"] + s["losses"]
            wr = s["wins"] / decided * 100 if decided > 0 else 0
            pnl = s["wins"] * args.tp_pnl - s["losses"] * args.sl_pnl
            print(
                f"\n  {direction.upper()}: {total}件 "
                f"(TP {s['wins']} / SL {s['losses']} / TO {s['timeouts']})"
            )
            print(f"    勝率: {wr:.1f}% | PnL: ¥{pnl:+,.0f} | 期待値: ¥{pnl/total:+,.0f}/取引")

    # GCPシグナルシミュレーション
    if args.with_signals:
        print(f"\n{'='*70}")
        print("GCPログからのシグナルシミュレーション")
        print(f"{'='*70}")

        signals = fetch_gcp_signals(args.days)
        if not signals:
            print("  シグナルなし")
            return

        wins, losses, timeouts = 0, 0, 0
        total_pnl = 0
        results_by_filter = {"通過": [], "中間": [], "拒否": []}

        for sig in signals:
            if not sig["time"]:
                continue

            try:
                sig_time = pd.Timestamp(sig["time"])
            except Exception:
                continue

            closest_idx = df.index.get_indexer([sig_time], method="nearest")[0]
            if closest_idx < 0 or closest_idx >= len(df) - args.max_bars:
                continue

            r = simulate_triple_barrier(
                df, closest_idx, sig["action"], args.tp, args.sl, args.max_bars
            )

            pnl = (
                args.tp_pnl if r["result"] == "TP" else (-args.sl_pnl if r["result"] == "SL" else 0)
            )
            if r["result"] == "TP":
                wins += 1
            elif r["result"] == "SL":
                losses += 1
            else:
                timeouts += 1
            total_pnl += pnl

            results_by_filter[sig["filter"]].append({"result": r["result"], "pnl": pnl})

            mark = {"TP": "✅", "SL": "❌", "TIMEOUT": "⏰"}[r["result"]]
            fmark = {"通過": "🟢Go ", "中間": "🟡Mid", "拒否": "🔴No "}[sig["filter"]]

            print(
                f"  {mark} {sig['action']:>4} @ ¥{r['entry']:>12,.0f} "
                f"→ {r['result']:>7} ({r['bars']:>2}本) PnL={pnl:>+5,.0f}円 "
                f"| ML={sig['ml_conf']:.3f} {fmark}"
            )

        total = wins + losses + timeouts
        if total > 0:
            print(f"\n  合計: {total}件 TP{wins}/SL{losses}/TO{timeouts}")
            if wins + losses > 0:
                print(f"  勝率: {wins/(wins+losses)*100:.0f}% | PnL: ¥{total_pnl:+,}")

            print(f"\n  MLフィルタ別:")
            for f_type in ["通過", "中間", "拒否"]:
                items = results_by_filter[f_type]
                if not items:
                    continue
                f_wins = sum(1 for i in items if i["result"] == "TP")
                f_losses = sum(1 for i in items if i["result"] == "SL")
                f_pnl = sum(i["pnl"] for i in items)
                f_total = f_wins + f_losses
                f_wr = f_wins / f_total * 100 if f_total > 0 else 0
                fmark = {"通過": "🟢", "中間": "🟡", "拒否": "🔴"}[f_type]
                print(f"    {fmark} {f_type}: {len(items)}件 勝率{f_wr:.0f}% PnL={f_pnl:+,}円")

    # 全足もシグナルもない場合はデフォルトで全足シミュレーション
    if not args.full and not args.with_signals:
        print(f"\n{'='*70}")
        print("全足BUY/SELLシミュレーション（市場特性分析）")
        print(f"{'='*70}")

        stats = run_full_simulation(df, args.tp, args.sl, args.max_bars, args.tp_pnl, args.sl_pnl)

        for direction in ["buy", "sell"]:
            s = stats[direction]
            total = s["wins"] + s["losses"] + s["timeouts"]
            decided = s["wins"] + s["losses"]
            wr = s["wins"] / decided * 100 if decided > 0 else 0
            pnl = s["wins"] * args.tp_pnl - s["losses"] * args.sl_pnl
            print(
                f"\n  {direction.upper()}: {total}件 "
                f"(TP {s['wins']} / SL {s['losses']} / TO {s['timeouts']})"
            )
            print(f"    勝率: {wr:.1f}% | PnL: ¥{pnl:+,.0f} | 期待値: ¥{pnl/total:+,.0f}/取引")


if __name__ == "__main__":
    main()
