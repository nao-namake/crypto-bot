"""
Phase 85: 真の運用シミュレーション

bitbank API から過去の全エントリー取引を取得し（TP決済のみではなく全件）、
各エントリーから15分足を使って TP/SL先着判定を行う。

sl_simulation.py は trade_type='tp' で抽出していたため母集団バイアスがあり、
勝率が過大評価されていた問題を解消する。

判定方法:
- bitbank trades の position_side（"long"/"short"）と side（"buy"/"sell"）でエントリー識別
  - position_side=long + side=buy → ロングエントリー
  - position_side=short + side=sell → ショートエントリー
  - その他は決済（profit_loss が非0）
- profit_loss > 0 → TP、< 0 → SL
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / "config" / "secrets" / ".env")

import ccxt  # noqa: E402

ENTRY_FEE_RATE = 0.001  # Taker想定
EXIT_FEE_RATE_TP = 0.0  # Maker想定

SCENARIOS = [
    # ユーザー希望3パターン
    {"name": "TP1500/SL800 (floor無し)", "tp_amount": 1500.0, "sl_amount": 800.0, "floor": 0.0},
    {"name": "TP1500/SL1000(floor無し)", "tp_amount": 1500.0, "sl_amount": 1000.0, "floor": 0.0},
    {"name": "TP1500/SL1200(floor無し)", "tp_amount": 1500.0, "sl_amount": 1200.0, "floor": 0.0},
    # 浅いTP系（Phase 61相当）
    {
        "name": "TP500 /SL500 (floor無し)Phase61風",
        "tp_amount": 500.0,
        "sl_amount": 500.0,
        "floor": 0.0,
    },
    {"name": "TP750 /SL750 (floor無し)", "tp_amount": 750.0, "sl_amount": 750.0, "floor": 0.0},
    # floor 0.7% 入りシナリオ（Phase 82-83A）
    {
        "name": "TP500 /SL1500(floor0.7%)Phase82風",
        "tp_amount": 500.0,
        "sl_amount": 1500.0,
        "floor": 0.007,
    },
    {
        "name": "TP750 /SL1500(floor0.7%)Phase83A",
        "tp_amount": 750.0,
        "sl_amount": 1500.0,
        "floor": 0.007,
    },
    {"name": "TP1000/SL1500(floor0.7%)", "tp_amount": 1000.0, "sl_amount": 1500.0, "floor": 0.007},
    {"name": "TP1500/SL2000(floor0.7%)", "tp_amount": 1500.0, "sl_amount": 2000.0, "floor": 0.007},
    # 比較用
    {"name": "TP1200/SL800 (floor無し)", "tp_amount": 1200.0, "sl_amount": 800.0, "floor": 0.0},
    {"name": "TP1000/SL1000(floor無し)", "tp_amount": 1000.0, "sl_amount": 1000.0, "floor": 0.0},
    {
        "name": "TP750 /SL500 (floor無し)Phase70",
        "tp_amount": 750.0,
        "sl_amount": 500.0,
        "floor": 0.0,
    },
    {
        "name": "TP1000/SL500 (floor無し)現状83B",
        "tp_amount": 1000.0,
        "sl_amount": 500.0,
        "floor": 0.0,
    },
]


def fetch_candles(start_dt: datetime, end_dt: datetime) -> pd.DataFrame:
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


def calc_sl_distance(entry_price, amount, sl_amount, floor_ratio):
    """実コード（strategy_utils.py:485-487）と同じ手数料控除ロジック"""
    entry_fee = entry_price * amount * ENTRY_FEE_RATE
    exit_fee = entry_price * amount * 0.001
    gross_loss = sl_amount - entry_fee - exit_fee
    if gross_loss <= 0:
        target_loss_distance = sl_amount / amount
    else:
        target_loss_distance = gross_loss / amount
    floor_distance = entry_price * floor_ratio if floor_ratio > 0 else 0
    return max(target_loss_distance, floor_distance)


def calc_tp_distance(entry_price, amount, tp_amount):
    entry_fee = entry_price * amount * ENTRY_FEE_RATE
    gross_profit = tp_amount - entry_fee
    return gross_profit / amount


def simulate_trade(
    entry_dt, entry_price, entry_side, tp_price, sl_distance, candles, max_window_min
):
    sl_price = entry_price - sl_distance if entry_side == "buy" else entry_price + sl_distance
    end_dt = entry_dt + timedelta(minutes=max_window_min)
    window = candles[(candles.index >= entry_dt) & (candles.index <= end_dt)]
    if window.empty:
        return {"result": "NO_DATA"}
    for ts, bar in window.iterrows():
        hi, lo = bar["high"], bar["low"]
        if entry_side == "buy":
            sl_hit = lo <= sl_price
            tp_hit = hi >= tp_price
        else:
            sl_hit = hi >= sl_price
            tp_hit = lo <= tp_price
        if sl_hit and tp_hit:
            return {"result": "SL", "ts": ts}  # 同時はSL優先（保守的）
        if sl_hit:
            return {"result": "SL", "ts": ts}
        if tp_hit:
            return {"result": "TP", "ts": ts}
    return {"result": "OPEN"}


def fetch_all_trades_paginated(exchange, since_ms, max_pages=10):
    """bitbank APIで複数ページ分のtradesを取得"""
    all_trades = []
    last_ts = since_ms
    for page in range(max_pages):
        batch = exchange.fetch_my_trades("BTC/JPY", since=last_ts, limit=1000)
        if not batch:
            break
        # 重複排除（trade_idベース）
        existing_ids = {t.get("info", {}).get("trade_id") for t in all_trades}
        new = [t for t in batch if t.get("info", {}).get("trade_id") not in existing_ids]
        if not new:
            break
        all_trades.extend(new)
        last_ts = max(t["timestamp"] for t in new) + 1
        time.sleep(0.3)
    return all_trades


def extract_entries(trades):
    """tradesからエントリー取引のみを抽出してorder_idで集約"""
    # order_idでグルーピング
    by_order = {}
    for t in trades:
        info = t["info"]
        oid = info.get("order_id")
        if not oid:
            continue
        pos_side = info.get("position_side")  # "long" or "short"
        side = info.get("side")  # "buy" or "sell"
        pl = float(info.get("profit_loss", 0))
        # エントリー判定: position_side と side が一致方向
        is_entry = (pos_side == "long" and side == "buy") or (
            pos_side == "short" and side == "sell"
        )
        if not is_entry:
            continue  # 決済は対象外
        if oid not in by_order:
            by_order[oid] = {
                "order_id": oid,
                "timestamp": t["timestamp"],
                "datetime": t["datetime"],
                "side": side,
                "pos_side": pos_side,
                "amount_sum": 0.0,
                "amount_x_price": 0.0,
                "executed_count": 0,
                "pl": pl,
            }
        agg = by_order[oid]
        agg["amount_sum"] += float(info.get("amount", 0))
        agg["amount_x_price"] += float(info.get("amount", 0)) * float(info.get("price", 0))
        agg["executed_count"] += 1
        # 同order_idの最初のtimestampを採用
        if t["timestamp"] < agg["timestamp"]:
            agg["timestamp"] = t["timestamp"]
            agg["datetime"] = t["datetime"]
    # エントリー一覧
    entries = []
    for oid, agg in by_order.items():
        if agg["amount_sum"] <= 0:
            continue
        avg_price = agg["amount_x_price"] / agg["amount_sum"]
        entries.append(
            {
                "order_id": oid,
                "datetime": agg["datetime"],
                "timestamp_ms": agg["timestamp"],
                "side": agg["side"],
                "amount": agg["amount_sum"],
                "entry_price": avg_price,
                "executed_count": agg["executed_count"],
            }
        )
    entries.sort(key=lambda e: e["timestamp_ms"])
    return entries


def load_regime_log(path):
    """GCPログのレジーム判定 (`動的戦略選択: レジーム=X`) をパースして時系列リスト化"""
    import re

    pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)Z.*動的戦略選択: レジーム=(\w+)"
    )
    records = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    ts = pd.to_datetime(m.group(1), utc=True)
                    records.append((ts, m.group(2)))
    except FileNotFoundError:
        return []
    records.sort(key=lambda r: r[0])
    return records


def find_regime_at(regime_log, target_dt):
    """target_dt直前(直近5分以内)のレジームを返す。なければNone"""
    if not regime_log:
        return None
    # bsearch
    lo, hi = 0, len(regime_log) - 1
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        if regime_log[mid][0] <= target_dt:
            best = regime_log[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    if best is None:
        return None
    # 直近10分以内のみ採用（5分→10分でカバレッジ拡大）
    if (target_dt - best[0]).total_seconds() > 600:
        return None
    return best[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--max-window-min", type=int, default=1440)
    parser.add_argument(
        "--regime-log", default="/tmp/regime_logs.txt", help="GCPレジームログのパス"
    )
    args = parser.parse_args()

    # 1. bitbank API でtrades取得
    exchange = ccxt.bitbank(
        {
            "apiKey": os.environ.get("BITBANK_API_KEY"),
            "secret": os.environ.get("BITBANK_API_SECRET"),
        }
    )
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp() * 1000)
    print(f"📥 過去{args.days}日のbitbank取引履歴取得中...")
    trades = fetch_all_trades_paginated(exchange, since_ms)
    print(f"   取得trades: {len(trades)}件")

    # 2. エントリー取引を抽出
    entries = extract_entries(trades)
    print(f"📊 エントリー注文数: {len(entries)}件\n")
    if not entries:
        print("対象データなし")
        return

    # buy/sell内訳
    buy_count = sum(1 for e in entries if e["side"] == "buy")
    sell_count = len(entries) - buy_count
    print(f"   buy(long): {buy_count}件 / sell(short): {sell_count}件")

    # 3. 15分足取得
    first_dt = pd.to_datetime(entries[0]["timestamp_ms"], unit="ms", utc=True)
    last_dt = pd.to_datetime(entries[-1]["timestamp_ms"], unit="ms", utc=True)
    cstart = first_dt - timedelta(days=1)
    cend = last_dt + timedelta(days=2)
    print(f"📈 15分足取得: {cstart.date()} 〜 {cend.date()}")
    candles = fetch_candles(cstart, cend)
    print(f"   バー数: {len(candles)}\n")
    if candles.empty:
        print("ローソク足取得失敗")
        return

    # 4. レジームログ読み込み・各エントリーにレジーム紐付け
    regime_log = load_regime_log(args.regime_log)
    print(f"📊 レジーム判定ログ: {len(regime_log)}件\n")
    regime_counts = {
        "tight_range": 0,
        "normal_range": 0,
        "trending": 0,
        "high_volatility": 0,
        "unknown": 0,
    }
    for e in entries:
        entry_dt = pd.to_datetime(e["timestamp_ms"], unit="ms", utc=True)
        e["regime"] = find_regime_at(regime_log, entry_dt) or "unknown"
        regime_counts[e["regime"]] = regime_counts.get(e["regime"], 0) + 1
    print(f"   エントリー時レジーム内訳: {regime_counts}\n")

    # 5. 各シナリオでシミュ + レジーム別集計
    results = {
        s["name"]: {"TP": 0, "SL": 0, "OPEN": 0, "NO_DATA": 0, "pnl": 0.0} for s in SCENARIOS
    }
    # レジーム別の (TP/SL/PnL) を最良シナリオ TP1500/SL2000 で集計
    regime_breakdown = {}  # regime -> scenario -> {TP,SL,OPEN,pnl}

    for e in entries:
        entry_dt = pd.to_datetime(e["timestamp_ms"], unit="ms", utc=True)
        regime = e["regime"]
        if regime not in regime_breakdown:
            regime_breakdown[regime] = {
                s["name"]: {"TP": 0, "SL": 0, "OPEN": 0, "pnl": 0.0} for s in SCENARIOS
            }
        for s in SCENARIOS:
            tp_dist = calc_tp_distance(e["entry_price"], e["amount"], s["tp_amount"])
            sl_dist = calc_sl_distance(e["entry_price"], e["amount"], s["sl_amount"], s["floor"])
            tp_price = (
                e["entry_price"] + tp_dist if e["side"] == "buy" else e["entry_price"] - tp_dist
            )
            r = simulate_trade(
                entry_dt,
                e["entry_price"],
                e["side"],
                tp_price,
                sl_dist,
                candles,
                args.max_window_min,
            )
            results[s["name"]][r["result"]] += 1
            regime_breakdown[regime][s["name"]][r["result"]] = (
                regime_breakdown[regime][s["name"]].get(r["result"], 0) + 1
            )
            if r["result"] == "TP":
                results[s["name"]]["pnl"] += s["tp_amount"]
                regime_breakdown[regime][s["name"]]["pnl"] += s["tp_amount"]
            elif r["result"] == "SL":
                results[s["name"]]["pnl"] -= s["sl_amount"]
                regime_breakdown[regime][s["name"]]["pnl"] -= s["sl_amount"]

    # 6. 出力
    print("=" * 110)
    print(
        f"{'シナリオ':<40} | {'TP':>4} | {'SL':>4} | OPEN | NA  | {'勝率':>8} | {'損益':>10} | {'期待値/件':>10}"
    )
    print("=" * 110)
    for s in SCENARIOS:
        r = results[s["name"]]
        decided = r["TP"] + r["SL"]
        winrate = r["TP"] / decided * 100 if decided > 0 else 0
        ev = r["pnl"] / len(entries) if entries else 0
        print(
            f"{s['name']:<40} | {r['TP']:>4} | {r['SL']:>4} | {r['OPEN']:>4} | {r['NO_DATA']:>3} | "
            f"{winrate:>7.1f}% | {r['pnl']:>+10.0f} | {ev:>+8.0f}円"
        )
    print("=" * 110)
    print(
        f"\nエントリー総数: {len(entries)}件、解析期間: {args.days}日、max_window: {args.max_window_min}分"
    )
    print(
        "注: 期待値はスリッページ・手数料未考慮の理論値。実損益は -400円/件 のスリッページぶん下振れする可能性"
    )

    # 7. レジーム別ブレークダウン（最良候補シナリオ抜粋）
    print("\n" + "=" * 110)
    print("📊 レジーム別の勝率（過去の運用エントリー106件中）")
    print("=" * 110)
    target_scenarios = [
        "TP500 /SL1500(floor0.7%)Phase82風",
        "TP750 /SL1500(floor0.7%)Phase83A",
        "TP1500/SL2000(floor0.7%)",
        "TP1500/SL1200(floor無し)",
        "TP1000/SL500 (floor無し)現状83B",
    ]
    for regime in ["tight_range", "normal_range", "trending", "high_volatility", "unknown"]:
        if regime not in regime_breakdown:
            continue
        rcount = regime_counts.get(regime, 0)
        if rcount == 0:
            continue
        print(f"\n■ レジーム: {regime} ({rcount}件)")
        print(
            f"  {'シナリオ':<40} | {'TP':>3} | {'SL':>3} | {'勝率':>7} | {'損益':>8} | {'期待値':>7}"
        )
        for sname in target_scenarios:
            rb = regime_breakdown[regime].get(sname, {})
            tp = rb.get("TP", 0)
            sl = rb.get("SL", 0)
            decided = tp + sl
            wr = tp / decided * 100 if decided > 0 else 0
            ev = rb.get("pnl", 0) / rcount if rcount > 0 else 0
            print(
                f"  {sname:<40} | {tp:>3} | {sl:>3} | {wr:>6.1f}% | {rb.get('pnl', 0):>+8.0f} | {ev:>+6.0f}円"
            )


if __name__ == "__main__":
    main()
