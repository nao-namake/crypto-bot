#!/usr/bin/env python3
"""
bitbank注文状況確認スクリプト
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, "src")

# .env読み込み
env_path = Path(__file__).parent / "config/secrets/.env"
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

import asyncio
from src.data.bitbank_client import BitbankClient
from src.core.logger import setup_logging

async def main():
    logger = setup_logging("check_orders")
    client = BitbankClient()

    # 最近の注文ID
    order_ids = [
        "50534560215",  # SL注文
        "50534558546",  # TP注文
        "50534558239",  # エントリー注文
    ]

    print("\n" + "="*60)
    print("📋 bitbank注文状況確認")
    print("="*60 + "\n")

    for order_id in order_ids:
        try:
            print(f"🔍 注文ID: {order_id}")
            order = client.fetch_order(order_id)

            print(f"  ステータス: {order.get('status', 'UNKNOWN')}")
            print(f"  タイプ: {order.get('type', 'UNKNOWN')}")
            print(f"  サイド: {order.get('side', 'UNKNOWN')}")
            print(f"  数量: {order.get('amount', 0)}")
            print(f"  価格: {order.get('price', 'N/A')}")

            # トリガー価格（stop注文の場合）
            if 'triggerPrice' in order:
                print(f"  トリガー価格: {order['triggerPrice']}")
            if 'trigger_price' in order:
                print(f"  トリガー価格: {order['trigger_price']}")

            # その他の情報
            if 'info' in order:
                info = order['info']
                print(f"  Raw Info: {info}")

            print()

        except Exception as e:
            print(f"  ❌ エラー: {e}\n")

    # アクティブな注文を取得
    print("\n" + "="*60)
    print("📋 アクティブな注文一覧")
    print("="*60 + "\n")

    try:
        # ccxtのfetch_open_ordersを使用
        active_orders = client.exchange.fetch_open_orders("BTC/JPY")
        print(f"合計: {len(active_orders)}件\n")

        for order in active_orders:
            print(f"注文ID: {order.get('id', 'UNKNOWN')}")
            print(f"  ステータス: {order.get('status', 'UNKNOWN')}")
            print(f"  タイプ: {order.get('type', 'UNKNOWN')}")
            print(f"  サイド: {order.get('side', 'UNKNOWN')}")
            print(f"  数量: {order.get('amount', 0)}")
            print(f"  価格: {order.get('price', 'N/A')}")

            # info詳細表示
            if 'info' in order:
                info = order['info']
                if 'trigger_price' in info:
                    print(f"  トリガー価格: {info['trigger_price']}")
            print()

    except Exception as e:
        print(f"❌ エラー: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
