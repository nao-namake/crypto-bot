#!/usr/bin/env python3
"""収益性アトリビューション分析（読み取り専用）

実トレードの損益を「戦略別・レジーム別・方向別・曜日別・保有時間別」に分解し、
各セグメントの 件数 / 勝率 / 合計損益 / 期待値(平均損益/件) / ブートストラップ95%信頼区間 を算出する。

目的（docs/検証記録/2026-06-10_bot性能向上の方針整理.md）:
  - 損益が戦略/レジームに紐づいておらず「何が稼ぎ何が損か」判断できない欠落を埋める。
  - 小サンプル（週数件）を信頼区間で「まだ判断できない」と明示し、誤った戦略オン/オフ判断を防ぐ。

制約:
  - 戦略/レジームの紐付けは GCP ログ保持期間（約30日）以内のみ。それ以前/欠落は "unknown" に集計（除外しない）。
  - 完全に読み取り専用。bitbank API と GCP ログの参照のみ。注文・設定・DB への書き込みは一切しない。

データ取得の一部は scripts/analysis/full_entry_simulation.py の実装を踏襲（約定構造・API初期化）。

使い方:
  python3 scripts/analysis/trade_attribution.py --days 30
  python3 scripts/analysis/trade_attribution.py --days 14 --json --md
"""

import argparse
import os
import random
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

# 保有時間バケット（分単位の上限, ラベル）
HOLDING_BUCKETS = [
    (60, "<1h"),
    (240, "1-4h"),
    (720, "4-12h"),
    (1440, "12-24h"),
    (float("inf"), ">24h"),
]


# ============================================================
# データ取得（full_entry_simulation.py 踏襲）
# ============================================================
def load_api_keys():
    """環境変数 or config/secrets/.env から bitbank API キーを読む（読み取りのみ）"""
    api_key = os.environ.get("BITBANK_API_KEY")
    api_secret = os.environ.get("BITBANK_API_SECRET")
    if not api_key or not api_secret:
        env_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "secrets", ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("BITBANK_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
                    elif line.startswith("BITBANK_API_SECRET="):
                        api_secret = line.strip().split("=", 1)[1]
    return api_key, api_secret


def fetch_all_trades_paginated(exchange, since_ms, max_pages=10):
    """bitbank約定履歴をページネーションで全取得（full_entry_simulation.py 踏襲）"""
    all_trades = []
    seen_ids = set()
    last_ts = since_ms
    for _ in range(max_pages):
        trades = exchange.fetch_my_trades("BTC/JPY", since=last_ts, limit=1000)
        if not trades:
            break
        new = [t for t in trades if t["id"] not in seen_ids]
        if not new:
            break
        for t in new:
            seen_ids.add(t["id"])
        all_trades.extend(new)
        last_ts = max(t["timestamp"] for t in new) + 1
        time.sleep(0.3)
    return all_trades


def fetch_entry_strategy_logs(days):
    """GCPログから「エントリー成功」ログ（order_id・戦略・レジーム付き）の生テキストを取得。

    gcloud 未インストール/失敗時は空文字を返す（紐付けは unknown にフォールバック）。
    """
    query = "resource.type=cloud_run_revision AND " 'textPayload:"Step 1/3: エントリー成功"'
    cmd = [
        "gcloud",
        "logging",
        "read",
        query,
        f"--freshness={days}d",
        "--format=value(textPayload)",
        "--limit=2000",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return r.stdout or ""
    except Exception as e:  # pragma: no cover - 環境依存
        print(f"  GCPログ取得失敗（紐付けはunknownにフォールバック）: {e}", file=sys.stderr)
        return ""


def parse_entry_strategy_log(raw):
    """エントリー成功ログ → {order_id(str): {"strategy", "regime"}}

    ログ例:
      ✅ Phase 51.6 Step 1/3: エントリー成功 - ID: 57997195838, 価格: 9769644円,
        戦略=BBReversal, レジーム=normal_range
    ANSIエスケープ（色コード）が混入し得るため除去してからパースする。
    """
    mapping = {}
    clean = re.sub(r"\x1b\[[0-9;]*m", "", raw or "")
    pat = re.compile(r"ID:\s*(\d+).*?戦略=(\w+).*?レジーム=(\w+)")
    for m in pat.finditer(clean):
        mapping[m.group(1)] = {"strategy": m.group(2), "regime": m.group(3)}
    return mapping


# ============================================================
# 完結トレード構築（新規）
# ============================================================
def _order_id_of(trade):
    """約定から order_id を取り出す（GCPログのIDと突合するキー）"""
    info = trade.get("info", {}) or {}
    return str(info.get("order_id") or trade.get("order") or trade.get("id") or "")


def build_round_trips(trades):
    """約定列を建玉単位（FIFO・long/short両対応）でペアリングし、完結トレードを作る。

    エントリー判定: position_side と side が同方向 (long,buy)/(short,sell)。
    決済判定: 逆方向。決済約定の info.profit_loss が実現損益（グロス）。
    部分約定/部分決済は数量按分する。

    返り値: list[dict]（entry_order_id, pos_side, entry/exit time・price, amount,
            gross_pnl, fee, holding_min, entry_weekday, entry_hour_jst）
    """
    # FIFOキュー: pos_side -> list of open lots
    open_lots = {"long": [], "short": []}
    round_trips = []

    for t in sorted(trades, key=lambda x: x["timestamp"]):
        info = t.get("info", {}) or {}
        pos = info.get("position_side", "")
        side = t.get("side", "")
        amount = float(t.get("amount", 0) or 0)
        price = float(t.get("price", 0) or 0)
        fee = float((t.get("fee") or {}).get("cost", 0) or 0)
        pl = float(info.get("profit_loss", 0) or 0)
        ts_ms = t["timestamp"]
        if amount <= 0 or pos not in ("long", "short"):
            continue

        is_entry = (pos == "long" and side == "buy") or (pos == "short" and side == "sell")

        if is_entry:
            open_lots[pos].append(
                {
                    "order_id": _order_id_of(t),
                    "ts_ms": ts_ms,
                    "price": price,
                    "remaining": amount,
                    "amount": amount,
                    "fee": fee,
                }
            )
            continue

        # 決済: pos方向のオープンロットをFIFOで消化
        remaining = amount
        while remaining > 1e-12 and open_lots[pos]:
            lot = open_lots[pos][0]
            matched = min(remaining, lot["remaining"])
            frac_exit = matched / amount if amount > 0 else 0.0
            frac_entry = matched / lot["amount"] if lot["amount"] > 0 else 0.0
            # 実現損益（グロス）: 決済約定の profit_loss を数量按分。
            # profit_loss が無い場合は価格差から算出（long: exit-entry, short: entry-exit）。
            if pl != 0:
                gross = pl * frac_exit
            elif pos == "long":
                gross = (price - lot["price"]) * matched
            else:
                gross = (lot["price"] - price) * matched
            entry_fee = lot["fee"] * frac_entry
            exit_fee = fee * frac_exit
            entry_dt = datetime.fromtimestamp(lot["ts_ms"] / 1000, tz=timezone.utc)
            entry_jst = entry_dt.astimezone(JST)
            round_trips.append(
                {
                    "entry_order_id": lot["order_id"],
                    "pos_side": pos,
                    "entry_ts_ms": lot["ts_ms"],
                    "exit_ts_ms": ts_ms,
                    "entry_price": lot["price"],
                    "exit_price": price,
                    "amount": matched,
                    "gross_pnl": gross,
                    "fee": entry_fee + exit_fee,
                    "net_pnl": gross - (entry_fee + exit_fee),
                    "holding_min": (ts_ms - lot["ts_ms"]) / 1000 / 60,
                    "entry_weekday": entry_jst.weekday(),  # 0=月
                    "entry_hour_jst": entry_jst.hour,
                    "entry_dt_jst": entry_jst,
                }
            )
            lot["remaining"] -= matched
            remaining -= matched
            if lot["remaining"] <= 1e-12:
                open_lots[pos].pop(0)

    return round_trips


def attribute_trades(round_trips, mapping):
    """各完結トレードに戦略・レジーム（GCPログ由来）と保有時間バケットを付与"""
    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    for rt in round_trips:
        m = mapping.get(rt["entry_order_id"])
        rt["strategy"] = m["strategy"] if m else "unknown"
        rt["regime"] = m["regime"] if m else "unknown"
        rt["direction"] = "long" if rt["pos_side"] == "long" else "short"
        rt["weekday_label"] = weekday_names[rt["entry_weekday"]]
        for upper, label in HOLDING_BUCKETS:
            if rt["holding_min"] < upper:
                rt["holding_bucket"] = label
                break
    return round_trips


# ============================================================
# 集計・統計（新規）
# ============================================================
def bootstrap_ci(pnls, n=10000, seed=42, alpha=0.05):
    """期待値（平均損益/件）のブートストラップ信頼区間。

    サンプルが2未満なら (None, None)。seed固定で再現性あり（テスト可能）。
    """
    k = len(pnls)
    if k < 2:
        return (None, None)
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        s = 0.0
        for _ in range(k):
            s += pnls[rng.randrange(k)]
        means.append(s / k)
    means.sort()
    lo = means[int((alpha / 2) * n)]
    hi = means[int((1 - alpha / 2) * n)]
    return (lo, hi)


def _segment_stats(trades, bootstrap_n):
    """1セグメントの完結トレード群 → 統計dict"""
    pnls = [t["net_pnl"] for t in trades]
    n = len(pnls)
    wins = sum(1 for p in pnls if p > 0)
    total = sum(pnls)
    expectancy = total / n if n else 0.0
    lo, hi = bootstrap_ci(pnls, n=bootstrap_n) if n >= 2 else (None, None)
    # 信頼区間が0をまたぐ＝期待値の符号が確定しない＝判断保留
    inconclusive = lo is None or (lo <= 0 <= hi)
    return {
        "n": n,
        "win_rate": (wins / n * 100) if n else 0.0,
        "total_pnl": total,
        "expectancy": expectancy,
        "ci_low": lo,
        "ci_high": hi,
        "inconclusive": inconclusive,
    }


def aggregate_by_segment(trades, key, bootstrap_n=10000):
    """key関数でセグメント分けし、各セグメントの統計を返す（件数降順）"""
    groups = defaultdict(list)
    for t in trades:
        groups[key(t)].append(t)
    rows = []
    for label, ts in groups.items():
        st = _segment_stats(ts, bootstrap_n)
        st["label"] = str(label)
        rows.append(st)
    rows.sort(key=lambda r: r["n"], reverse=True)
    return rows


# ============================================================
# 出力
# ============================================================
def _fmt_ci(st):
    if st["ci_low"] is None:
        return "N/A (n<2)"
    flag = " ⚠️判断保留" if st["inconclusive"] else ""
    return f"[{st['ci_low']:+.0f}, {st['ci_high']:+.0f}]{flag}"


def _print_segment(title, rows):
    print(f"\n■ {title}")
    print(f"  {'区分':<14}{'件数':>5}{'勝率':>8}{'合計損益':>11}" f"{'期待値/件':>11}  期待値95%CI")
    for st in rows:
        print(
            f"  {st['label']:<14}{st['n']:>5}{st['win_rate']:>7.0f}%"
            f"{st['total_pnl']:>+11.0f}{st['expectancy']:>+11.0f}  {_fmt_ci(st)}"
        )


def build_report(trades, bootstrap_n):
    """全セグメントの集計を辞書で返す（JSON/MD出力・テスト用）"""
    segments = {
        "overall": aggregate_by_segment(trades, lambda t: "全体", bootstrap_n),
        "strategy": aggregate_by_segment(trades, lambda t: t["strategy"], bootstrap_n),
        "regime": aggregate_by_segment(trades, lambda t: t["regime"], bootstrap_n),
        "direction": aggregate_by_segment(trades, lambda t: t["direction"], bootstrap_n),
        "weekday": aggregate_by_segment(trades, lambda t: t["weekday_label"], bootstrap_n),
        "holding": aggregate_by_segment(trades, lambda t: t["holding_bucket"], bootstrap_n),
    }
    return segments


def print_report(trades, segments, days):
    print("=" * 78)
    print(f"📊 収益性アトリビューション分析（直近{days}日・完結トレード{len(trades)}件）")
    print("=" * 78)
    if not trades:
        print("完結トレードがありません。")
        return
    matched = sum(1 for t in trades if t["strategy"] != "unknown")
    print(f"戦略紐付け: {matched}/{len(trades)}件（残りはGCPログ保持期間外/欠落でunknown）")
    titles = [
        ("overall", "全体"),
        ("strategy", "戦略別"),
        ("regime", "レジーム別"),
        ("direction", "方向別(long/short)"),
        ("weekday", "曜日別(エントリーJST)"),
        ("holding", "保有時間別"),
    ]
    for key, title in titles:
        _print_segment(title, segments[key])
    print("\n" + "-" * 78)
    print(
        "注: 期待値95%CIが0をまたぐ(⚠️判断保留)セグメントは、サンプル不足で"
        "黒字/赤字を統計的に断定できない。戦略のオン/オフ判断は保留が妥当。"
    )
    print("=" * 78)


def write_outputs(trades, segments, days, want_json, want_md):
    """JSON/Markdown を docs/検証記録/ へ出力（オプション）"""
    if not (want_json or want_md):
        return
    out_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "検証記録", "live")
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now(JST).strftime("%Y%m%d_%H%M%S")

    def _clean_rows(rows):
        return [
            {k: v for k, v in r.items() if k != "inconclusive"}
            | {"inconclusive": r["inconclusive"]}
            for r in rows
        ]

    payload = {
        "generated_jst": datetime.now(JST).isoformat(),
        "days": days,
        "round_trips": len(trades),
        "segments": {k: _clean_rows(v) for k, v in segments.items()},
    }
    if want_json:
        import json

        p = os.path.join(out_dir, f"trade_attribution_{stamp}.json")
        with open(p, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        print(f"JSON出力: {p}")
    if want_md:
        p = os.path.join(out_dir, f"trade_attribution_{stamp}.md")
        lines = [f"# 収益性アトリビューション分析（直近{days}日）", ""]
        lines.append(f"- 生成: {payload['generated_jst']}")
        lines.append(f"- 完結トレード: {len(trades)}件\n")
        title_map = {
            "overall": "全体",
            "strategy": "戦略別",
            "regime": "レジーム別",
            "direction": "方向別",
            "weekday": "曜日別",
            "holding": "保有時間別",
        }
        for key, title in title_map.items():
            lines.append(f"## {title}\n")
            lines.append("| 区分 | 件数 | 勝率 | 合計損益 | 期待値/件 | 期待値95%CI | 判断 |")
            lines.append("|------|-----|------|---------|----------|------------|------|")
            for st in segments[key]:
                ci = _fmt_ci(st).replace(" ⚠️判断保留", "")
                judge = "⚠️保留" if st["inconclusive"] else "✅有意"
                lines.append(
                    f"| {st['label']} | {st['n']} | {st['win_rate']:.0f}% | "
                    f"{st['total_pnl']:+.0f} | {st['expectancy']:+.0f} | {ci} | {judge} |"
                )
            lines.append("")
        with open(p, "w") as f:
            f.write("\n".join(lines))
        print(f"Markdown出力: {p}")


# ============================================================
# main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="収益性アトリビューション分析（読み取り専用）")
    parser.add_argument("--days", type=int, default=30, help="解析期間（日・既定30）")
    parser.add_argument(
        "--bootstrap", type=int, default=10000, help="ブートストラップ反復数（既定10000）"
    )
    parser.add_argument("--json", action="store_true", help="JSON出力する")
    parser.add_argument("--md", action="store_true", help="Markdown出力する")
    args = parser.parse_args()

    try:
        import ccxt
    except ImportError:
        print("ccxt が必要です。pip install ccxt", file=sys.stderr)
        return 1

    api_key, api_secret = load_api_keys()
    if not api_key or not api_secret:
        print("BITBANK_API_KEY/SECRET が見つかりません。", file=sys.stderr)
        return 1

    exchange = ccxt.bitbank({"apiKey": api_key, "secret": api_secret})
    since_ms = int((datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp() * 1000)

    print(f"📥 直近{args.days}日の約定履歴を取得中...", file=sys.stderr)
    trades = fetch_all_trades_paginated(exchange, since_ms)
    print(f"   約定: {len(trades)}件", file=sys.stderr)

    round_trips = build_round_trips(trades)
    print(f"   完結トレード: {len(round_trips)}件", file=sys.stderr)

    print("📥 GCPログから戦略/レジームを紐付け中...", file=sys.stderr)
    mapping = parse_entry_strategy_log(fetch_entry_strategy_logs(args.days))
    print(f"   戦略マッピング: {len(mapping)}件", file=sys.stderr)

    attribute_trades(round_trips, mapping)
    segments = build_report(round_trips, args.bootstrap)
    print_report(round_trips, segments, args.days)
    write_outputs(round_trips, segments, args.days, args.json, args.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
