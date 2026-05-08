#!/usr/bin/env python3
"""
SL距離変更シミュレーション

過去のTP取引について、SL距離を狭めた場合に
TPに到達する前にSLヒットしていたかを bitbank 15分足で再現。

使い方:
    python3 scripts/analysis/sl_simulation.py [--since 2026-04-24] [--lookback-min 180]
"""

import argparse
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "tax" / "trade_history.db"

TARGET_NET_PROFIT = 750.0
ENTRY_FEE_RATE = 0.001  # Taker想定
EXIT_FEE_RATE_TP = 0.0  # Maker想定
FLOOR_RATIO = 0.007  # Phase 83A-2 SL floor

SCENARIOS = [
    # TP変動シナリオ (SL現状=1500/floor0.7%固定)
    {"name": "TP500 /SL1500(floor0.7%)", "tp_amount": 500.0, "sl_amount": 1500.0, "floor": 0.007},
    {
        "name": "TP750 /SL1500(floor0.7%)現状",
        "tp_amount": 750.0,
        "sl_amount": 1500.0,
        "floor": 0.007,
    },
    {"name": "TP1000/SL1500(floor0.7%)", "tp_amount": 1000.0, "sl_amount": 1500.0, "floor": 0.007},
    {"name": "TP1200/SL1500(floor0.7%)", "tp_amount": 1200.0, "sl_amount": 1500.0, "floor": 0.007},
    {"name": "TP1500/SL1500(floor0.7%)", "tp_amount": 1500.0, "sl_amount": 1500.0, "floor": 0.007},
    # TP×SL混合シナリオ
    {"name": "TP1000/SL800(floor0.4%)", "tp_amount": 1000.0, "sl_amount": 800.0, "floor": 0.004},
    {"name": "TP1200/SL800(floor0.4%)", "tp_amount": 1200.0, "sl_amount": 800.0, "floor": 0.004},
    {"name": "TP1000/SL500(floor無し)", "tp_amount": 1000.0, "sl_amount": 500.0, "floor": 0.0},
    {"name": "TP750 /SL500(floor無し)", "tp_amount": 750.0, "sl_amount": 500.0, "floor": 0.0},
    {"name": "TP750 /SL800(floor0.4%)", "tp_amount": 750.0, "sl_amount": 800.0, "floor": 0.004},
]


def fetch_candles(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
    """bitbank Public API から15分足取得（日付単位）"""
    all_candles = []
    cur = start_dt.date()
    end = end_dt.date()
    while cur <= end:
        url = f"https://public.bitbank.cc/btc_jpy/candlestick/15min/{cur.strftime('%Y%m%d')}"
        try:
            r = requests.get(url, timeout=10)
            d = r.json()
            if d.get("success") == 1:
                ohlcv = d["data"]["candlestick"][0]["ohlcv"]
                for c in ohlcv:
                    all_candles.append(
                        {
                            "open": float(c[0]),
                            "high": float(c[1]),
                            "low": float(c[2]),
                            "close": float(c[3]),
                            "ts_ms": int(c[5]),
                        }
                    )
            time.sleep(0.25)
        except Exception as e:
            print(f"  {cur}: 取得エラー {e}", file=sys.stderr)
        cur += timedelta(days=1)
    if not all_candles:
        return pd.DataFrame()
    df = pd.DataFrame(all_candles)
    df["dt"] = pd.to_datetime(df["ts_ms"], unit="ms", utc=True)
    df = df.set_index("dt").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df


def reconstruct_entry_price(exit_side: str, exit_price: float, amount: float, pnl: float) -> float:
    """
    exit記録から entry_price を逆算
    - exit_side='sell': 元はロング (buy entry → sell exit)
        gross = (exit - entry) * amount, pnl = gross - entry_fee - exit_fee_tp(=0)
        entry_fee = entry * amount * 0.001
        → entry = (exit*amount - pnl) / (amount * 1.001)
    - exit_side='buy': 元はショート (sell entry → buy exit)
        gross = (entry - exit) * amount, pnl = gross - entry_fee
        entry_fee = entry * amount * 0.001
        → entry = (pnl + exit*amount) / (amount * 0.999)
    """
    if exit_side == "sell":
        return (exit_price * amount - pnl) / (amount * (1 + ENTRY_FEE_RATE))
    else:
        return (pnl + exit_price * amount) / (amount * (1 - ENTRY_FEE_RATE))


def calc_sl_distance(
    entry_price: float, amount: float, sl_amount: float, floor_ratio: float
) -> float:
    """SL距離（価格レベル）を算出。floor_ratio>0 ならfloor強制"""
    fee_buffer = entry_price * amount * (ENTRY_FEE_RATE + 0.001)  # entry+exit_taker
    target_loss_distance = (sl_amount + fee_buffer) / amount
    floor_distance = entry_price * floor_ratio if floor_ratio > 0 else 0
    return max(target_loss_distance, floor_distance)


def calc_tp_distance(entry_price: float, amount: float, tp_amount: float) -> float:
    """TP距離（価格レベル）を算出。TP決済はMaker想定で決済手数料0%"""
    fee_buffer = entry_price * amount * ENTRY_FEE_RATE  # entryのみ
    return (tp_amount + fee_buffer) / amount


def simulate_trade(
    entry_dt: datetime,
    entry_price: float,
    entry_side: str,  # "buy" or "sell" (元のエントリー方向)
    tp_price: float,
    sl_distance: float,
    candles: pd.DataFrame,
    max_window_min: int,
) -> dict:
    """
    エントリー後のローソク足を時系列で走査し、TP/SLどちらに先に到達するか判定。
    candlesは15min足。各バーの中ではTP/SL同時の場合はSL優先（保守的）。
    """
    sl_price = entry_price - sl_distance if entry_side == "buy" else entry_price + sl_distance
    end_dt = entry_dt + timedelta(minutes=max_window_min)

    # entry時刻以降のバーを抽出
    window = candles[(candles.index >= entry_dt) & (candles.index <= end_dt)]
    if window.empty:
        return {"result": "NO_DATA", "exit_price": None, "bars": 0}

    for ts, bar in window.iterrows():
        hi, lo = bar["high"], bar["low"]
        if entry_side == "buy":
            sl_hit = lo <= sl_price
            tp_hit = hi >= tp_price
        else:
            sl_hit = hi >= sl_price
            tp_hit = lo <= tp_price

        if sl_hit and tp_hit:
            return {"result": "SL", "exit_price": sl_price, "bars": 0, "ts": ts}
        if sl_hit:
            return {"result": "SL", "exit_price": sl_price, "bars": 0, "ts": ts}
        if tp_hit:
            return {"result": "TP", "exit_price": tp_price, "bars": 0, "ts": ts}

    return {"result": "OPEN", "exit_price": None, "bars": len(window)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2026-04-24")
    parser.add_argument(
        "--lookback-min", type=int, default=240, help="exit時刻から逆算するentry探索ウィンドウ(分)"
    )
    parser.add_argument(
        "--max-window-min", type=int, default=240, help="entryからのシミュレーション最大時間(分)"
    )
    args = parser.parse_args()

    # 1. TP取引取得
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT timestamp, side, amount, price, pnl FROM trades "
        "WHERE timestamp >= ? AND trade_type='tp' ORDER BY timestamp",
        (args.since,),
    ).fetchall()
    conn.close()
    print(f"取得TP取引: {len(rows)}件\n")

    if not rows:
        print("対象データなし")
        return

    # 2. ローソク足取得（最古-1日 〜 最新+1日）
    times = [datetime.fromisoformat(r[0].replace("Z", "+00:00")) for r in rows]
    cstart = min(times) - timedelta(days=1)
    cend = max(times) + timedelta(days=1)
    print(f"15分足取得期間: {cstart.date()} 〜 {cend.date()}")
    candles = fetch_candles(cstart, cend)
    print(f"取得バー数: {len(candles)}\n")
    if candles.empty:
        print("ローソク足取得失敗")
        return

    # 3. 各取引について複数シナリオでシミュ
    results = {
        s["name"]: {"TP": 0, "SL": 0, "OPEN": 0, "NO_DATA": 0, "pnl": 0.0, "details": []}
        for s in SCENARIOS
    }
    DEBUG = False

    for ts_str, exit_side, amount, exit_price, pnl in rows:
        exit_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        original_entry_side = "buy" if exit_side == "sell" else "sell"
        entry_price = reconstruct_entry_price(exit_side, exit_price, amount, pnl)

        # entry時刻特定: exit_dt から逆順で entry_price に到達した最初の足
        # 探索範囲: exit_dt - lookback_min 〜 exit_dt
        win_start = exit_dt - timedelta(minutes=args.lookback_min)
        win = candles[(candles.index >= win_start) & (candles.index < exit_dt)]
        # buy entry: 安値で入る、ロングならexitより前にlow<=entry_priceの足が必ずある
        # sell entry: 高値で入る、ショートならexitより前にhigh>=entry_priceの足が必ずある
        # exit_dtに最も近い (= 最後の) 該当バーを entry時刻とする（直近のentry）
        if not win.empty:
            if original_entry_side == "buy":
                cands = win[(win["low"] <= entry_price) & (win["high"] >= entry_price)]
            else:
                cands = win[(win["low"] <= entry_price) & (win["high"] >= entry_price)]
            if not cands.empty:
                entry_dt_estimate = cands.index[-1]  # 最も新しい候補
            else:
                entry_dt_estimate = exit_dt - timedelta(minutes=15)
        else:
            entry_dt_estimate = exit_dt - timedelta(minutes=15)

        if DEBUG:
            sl_dist_now = calc_sl_distance(entry_price, amount, 1500.0, 0.007)
            tp_dist_now = calc_tp_distance(entry_price, amount, 750.0)
            print(
                f"[DEBUG] exit={exit_dt.strftime('%m-%d %H:%M')} side={original_entry_side} "
                f"entry={entry_price:.0f} entry_dt={entry_dt_estimate.strftime('%m-%d %H:%M')} "
                f"SL_dist={sl_dist_now:.0f} TP_dist={tp_dist_now:.0f}"
            )

        for sc in SCENARIOS:
            sl_dist = calc_sl_distance(entry_price, amount, sc["sl_amount"], sc["floor"])
            tp_dist = calc_tp_distance(entry_price, amount, sc["tp_amount"])
            if original_entry_side == "buy":
                tp_price_sim = entry_price + tp_dist
            else:
                tp_price_sim = entry_price - tp_dist

            res = simulate_trade(
                entry_dt_estimate,
                entry_price,
                original_entry_side,
                tp_price_sim,
                sl_dist,
                candles,
                args.max_window_min,
            )
            results[sc["name"]][res["result"]] += 1
            if res["result"] == "TP":
                results[sc["name"]]["pnl"] += sc["tp_amount"]
            elif res["result"] == "SL":
                actual_loss = sl_dist * amount + entry_price * amount * (ENTRY_FEE_RATE + 0.001)
                results[sc["name"]]["pnl"] -= actual_loss
            results[sc["name"]]["details"].append(
                {
                    "ts": ts_str,
                    "side": original_entry_side,
                    "entry": entry_price,
                    "tp": tp_price_sim,
                    "sl_dist": sl_dist,
                    "result": res["result"],
                }
            )

    # 4. レポート
    print("=" * 100)
    print(
        f"{'シナリオ':<32} | {'TP':>4} | {'SL':>4} | {'OPEN':>4} | {'NA':>3} | {'勝率':>6} | {'損益':>10}"
    )
    print("=" * 100)
    for sc in SCENARIOS:
        r = results[sc["name"]]
        total_decided = r["TP"] + r["SL"]
        wr = (r["TP"] / total_decided * 100) if total_decided > 0 else 0.0
        print(
            f"{sc['name']:<32} | {r['TP']:>4} | {r['SL']:>4} | {r['OPEN']:>4} | "
            f"{r['NO_DATA']:>3} | {wr:>5.1f}% | {r['pnl']:>+10.0f}"
        )
    print("=" * 100)
    print("\n注: ")
    print("  - 元データはTP決済24件のみ。SL→新SLは比較対象外（DBに残っていないため）")
    print("  - OPEN = 探索ウィンドウ内でTPもSLも当たらなかった = 元はTPだが新SL距離では未約定")
    print("  - NA = ローソク足データが取れない")
    print(f"  - 探索ウィンドウ: entry推定〜+{args.max_window_min}分")
    print("  - SL先勝判定は保守的（同一バーでTP/SL両方ヒットならSL優先）")


if __name__ == "__main__":
    main()
