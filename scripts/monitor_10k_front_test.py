#!/usr/bin/env python3
"""
1万円フロントテスト監視スクリプト
テスト進行状況のリアルタイム監視
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


def load_test_status():
    """テスト状況ファイル読み込み"""
    status_path = Path("/tmp/status_10k_test.json")

    if not status_path.exists():
        return None

    try:
        with open(status_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading status file: {e}")
        return None


def format_time_remaining(end_time_str):
    """残り時間をフォーマット"""
    try:
        end_time = datetime.fromisoformat(end_time_str)
        remaining = end_time - datetime.now()

        if remaining.total_seconds() <= 0:
            return "テスト期間終了"

        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return f"{hours}時間{minutes}分"
    except:
        return "不明"


def display_test_status():
    """テスト状況表示"""
    status = load_test_status()

    if not status:
        print("テスト状況ファイルが見つかりません。")
        return

    print("\n" + "=" * 60)
    print("📊 1万円フロントテスト進行状況")
    print("=" * 60)

    # 基本情報
    print(f"テスト開始時間: {status.get('test_start_time', 'N/A')}")
    print(f"残り時間: {format_time_remaining(status.get('test_end_time', ''))}")
    print(f"現在のステータス: {status.get('status', 'N/A')}")

    # トレード情報
    print(f"\n📈 取引情報:")
    print(f"  実行済み取引数: {status.get('trades_executed', 0)}")
    print(f"  最大取引数/日: {status.get('max_daily_trades', 0)}")
    print(f"  現在のP&L: {status.get('current_pnl', 0):.4f}")
    print(f"  最大ドローダウン: {status.get('max_drawdown', 0):.4f}")

    # リスク情報
    print(f"\n⚠️  リスク管理:")
    print(f"  1取引あたりリスク: {status.get('risk_per_trade', 0):.3f}%")
    print(f"  最大ポートフォリオ価値: {status.get('max_portfolio_value', 0):,}円")
    print(f"  緊急停止有効: {status.get('emergency_stop_enabled', False)}")
    print(f"  緊急停止発動回数: {status.get('emergency_stops_triggered', 0)}")

    # 注意事項
    print(f"\n📝 備考:")
    print(f"  {status.get('notes', 'N/A')}")

    print("=" * 60)


def check_system_health():
    """システムヘルスチェック"""
    try:
        # 本番環境ヘルスチェック
        import requests

        print("\n🔍 システムヘルスチェック:")

        # 基本ヘルスチェック
        response = requests.get(
            "https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health",
            timeout=10,
        )

        if response.status_code == 200:
            health_data = response.json()
            print(f"  システム状態: {health_data.get('status', 'N/A')}")
            print(f"  取引モード: {health_data.get('mode', 'N/A')}")
            print(f"  信用取引: {health_data.get('margin_mode', 'N/A')}")
        else:
            print(f"  ヘルスチェック失敗: HTTP {response.status_code}")

    except Exception as e:
        print(f"  ヘルスチェックエラー: {e}")


def display_emergency_stop_conditions():
    """緊急停止条件表示"""
    print("\n🚨 緊急停止条件:")
    print("  - 連続損失3回")
    print("  - 日次最大損失2%")
    print("  - 最大ドローダウン5%")
    print("  - 1日最大取引数5回超過")
    print("  - システムエラー発生")


def main():
    """メイン処理"""
    print("1万円フロントテスト監視を開始します...")
    print("Ctrl+Cで監視を停止できます。")

    try:
        while True:
            # クリア画面
            os.system("clear" if os.name == "posix" else "cls")

            # 現在時刻表示
            print(f"監視時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # テスト状況表示
            display_test_status()

            # システムヘルスチェック
            check_system_health()

            # 緊急停止条件表示
            display_emergency_stop_conditions()

            print("\n次回更新まで30秒...")
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n\n監視を停止しました。")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
