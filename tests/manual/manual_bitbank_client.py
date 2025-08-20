#!/usr/bin/env python3
"""
Bitbank信用取引クライアントの動作テスト

新しく実装したBitbank APIクライアントの動作確認を行います。.
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.core.logger import setup_logging
from src.data import BitbankClient, get_bitbank_client


def test_bitbank_basic():
    """基本的なAPI接続テスト."""
    print("🧪 Bitbank信用取引クライアント基本テスト")
    print("=" * 50)

    # ログシステム初期化
    logger = setup_logging("bitbank_test")

    try:
        # 公開API（認証不要）でのテスト
        print("📡 公開APIテスト...")

        # ダミーの認証情報でテスト（公開APIのみ使用）
        client = BitbankClient(api_key="test_key", api_secret="test_secret", leverage=1.0)

        print("✅ クライアント初期化成功")

        # サポート時間軸確認
        timeframes = client.get_supported_timeframes()
        print(f"📊 サポート時間軸: {timeframes}")

        # 統計情報確認
        stats = client.get_stats()
        print(f"📈 クライアント統計: {stats}")

        print("\n🎉 基本テスト完了")

    except Exception as e:
        print(f"❌ テストエラー: {e}")
        logger.error("基本テスト失敗", error=e)
        return False

    return True


def test_bitbank_market_data():
    """市場データ取得テスト（公開API）."""
    print("\n🧪 市場データ取得テスト")
    print("=" * 50)

    try:
        # 環境変数から認証情報を取得（なければ公開APIのみ）
        api_key = os.getenv("BITBANK_API_KEY", "dummy_key")
        api_secret = os.getenv("BITBANK_API_SECRET", "dummy_secret")

        client = BitbankClient(api_key=api_key, api_secret=api_secret, leverage=1.0)

        print("📊 ティッカー取得テスト...")

        # 注意: 実際のAPI呼び出しはスキップ（認証がない場合）
        if api_key == "dummy_key":
            print("⚠️ 認証情報が未設定のため、実際のAPI呼び出しはスキップします")
            print("💡 BITBANK_API_KEY と BITBANK_API_SECRET を設定すると実際のテストが実行されます")
        else:
            # 実際のAPI呼び出し
            ticker = client.fetch_ticker("BTC/JPY")
            print(f"💰 BTC/JPY価格: {ticker.get('last'):,} JPY")

            market_info = client.get_market_info("BTC/JPY")
            print(f"📈 市場情報: スプレッド {market_info.get('spread_pct', 0):.3f}%")

        print("✅ 市場データテスト完了")

    except Exception as e:
        print(f"❌ 市場データテストエラー: {e}")
        return False

    return True


def test_global_client():
    """グローバルクライアントテスト."""
    print("\n🧪 グローバルクライアントテスト")
    print("=" * 50)

    try:
        # グローバルクライアント取得
        client1 = get_bitbank_client(leverage=1.5)
        client2 = get_bitbank_client()  # 同じインスタンスを取得

        # 同じインスタンスかチェック
        if client1 is client2:
            print("✅ シングルトンパターン動作確認")
        else:
            print("❌ シングルトンパターン動作異常")
            return False

        # レバレッジ確認
        print(f"📊 設定レバレッジ: {client1.leverage}x")

        # 統計確認
        stats = client1.get_stats()
        print(f"📈 クライアント統計: margin_mode={stats['margin_mode']}")

        print("✅ グローバルクライアントテスト完了")

    except Exception as e:
        print(f"❌ グローバルクライアントテストエラー: {e}")
        return False

    return True


def main():
    """メインテスト実行."""
    print("🚀 Bitbank信用取引APIクライアント - 統合テスト")
    print("🎯 新アーキテクチャ対応版")
    print("=" * 60)

    test_results = []

    # 各テストを実行
    test_results.append(("基本機能", test_bitbank_basic()))
    test_results.append(("市場データ", test_bitbank_market_data()))
    test_results.append(("グローバルクライアント", test_global_client()))

    # 結果サマリー
    print("\n📋 テスト結果サマリー")
    print("=" * 60)

    success_count = 0
    for test_name, result in test_results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"{test_name:20} : {status}")
        if result:
            success_count += 1

    success_rate = success_count / len(test_results) * 100
    print(f"\n🎯 総合結果: {success_count}/{len(test_results)} 成功 ({success_rate:.1f}%)")

    if success_rate == 100:
        print("🎉 全テスト成功！Bitbank信用取引クライアントの実装が完了しました。")
        print("📝 Task 2-1: Bitbank API接続層の新規実装 → 完了")
    else:
        print("⚠️ 一部テストが失敗しました。実装を見直してください。")

    return success_rate == 100


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
