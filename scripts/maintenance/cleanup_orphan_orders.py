"""
孤児 stop/stop_limit 注文クリーンアップスクリプト (Phase 90γ-②)

ポジションが 0 件なのに stop/stop_limit 注文が残存している状態
（2026-05-21T22:40 の bitbank 50062 連鎖事案で発生）を解消する一回限り操作。

実行前ガード:
- ポジション 0 件であることを必須確認
- ポジションが残っている場合は対応 SL の可能性があるため中止

使い方:
    venv/bin/python3 scripts/maintenance/cleanup_orphan_orders.py        # ドライラン
    venv/bin/python3 scripts/maintenance/cleanup_orphan_orders.py --apply  # 実キャンセル
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.data.bitbank_client import BitbankClient  # noqa: E402


async def main(apply: bool) -> int:
    # .env から API キーを読み込み
    env_path = ROOT / "config" / "secrets" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

    client = BitbankClient()
    symbol = "BTC/JPY"

    # 1. ポジション確認（async）
    try:
        positions = await client.fetch_margin_positions(symbol)
    except Exception as e:
        print(f"❌ ポジション取得失敗: {e}")
        return 1

    pos_total = sum(abs(float(p.get("amount", 0))) for p in positions or [])
    print(f"📊 現在のポジション: {len(positions or [])} 件 / 合計 {pos_total:.4f} BTC")

    if pos_total > 0:
        print("⚠️ ポジションが残っているため、クリーンアップを中止します。")
        print("   （現役の SL/TP 注文を誤キャンセルするリスクがあるため）")
        for p in positions or []:
            print(f"   - side={p.get('side')}, amount={p.get('amount')}, price={p.get('price')}")
        return 0

    # 2. アクティブ注文取得（同期 API）
    try:
        orders = client.fetch_active_orders(symbol)
    except Exception as e:
        print(f"❌ アクティブ注文取得失敗: {e}")
        return 1

    stop_orders = [o for o in orders or [] if o.get("type") in ("stop", "stop_limit")]
    print(f"📋 検出された孤児 stop/stop_limit 注文: {len(stop_orders)} 件")

    if not stop_orders:
        print("✅ 孤児注文なし。クリーンアップ不要です。")
        return 0

    for o in stop_orders:
        info = o.get("info", {}) or {}
        print(
            f"   - ID={o.get('id')}, type={o.get('type')}, side={o.get('side')}, "
            f"amount={o.get('amount')}, trigger={info.get('trigger_price') or o.get('price')}"
        )

    if not apply:
        print()
        print("ℹ️ ドライランモード。--apply を付けると実キャンセルされます。")
        return 0

    # 3. 実キャンセル
    print()
    print("🚀 キャンセル実行中...")
    success = 0
    fail = 0
    for o in stop_orders:
        order_id = str(o.get("id", ""))
        try:
            result = client.cancel_order(order_id, symbol)
            print(f"   ✅ キャンセル成功 - ID={order_id} (result={result})")
            success += 1
        except Exception as e:
            print(f"   ❌ キャンセル失敗 - ID={order_id}: {e}")
            fail += 1

    print()
    print(f"📊 結果: 成功={success} / 失敗={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="孤児 stop 注文クリーンアップ (Phase 90γ-②)")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="実キャンセルを実行（指定なしならドライラン）",
    )
    args = parser.parse_args()

    sys.exit(asyncio.run(main(apply=args.apply)))
