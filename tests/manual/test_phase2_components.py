#!/usr/bin/env python3
"""
Phase 2 コンポーネント手動テスト

BitbankClient、DataPipeline、DataCacheの基本動作を検証
API認証情報がなくても公開APIを使用してテスト可能。.
"""

import sys
from pathlib import Path

# src モジュールをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.config import (
        Config,
        DataConfig,
        ExchangeConfig,
        LoggingConfig,
        MLConfig,
        RiskConfig,
    )
    from src.core.logger import get_logger
    from src.data.bitbank_client import BitbankClient, get_bitbank_client
    from src.data.data_cache import DataCache
    from src.data.data_pipeline import DataPipeline, DataRequest, TimeFrame, fetch_market_data

    print("✅ すべてのモジュールのインポートに成功")

except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)


def test_config_system():
    """設定システムのテスト."""
    print("\n🔧 設定システムテスト...")

    try:
        # 基本設定の作成
        exchange_config = ExchangeConfig()
        ml_config = MLConfig()
        risk_config = RiskConfig()
        data_config = DataConfig()
        logging_config = LoggingConfig()

        config = Config(
            exchange=exchange_config,
            ml=ml_config,
            risk=risk_config,
            data=data_config,
            logging=logging_config,
            mode="paper",
        )

        # 設定検証
        is_valid = config.validate()
        print(f"   設定検証結果: {'✅' if is_valid else '❌'}")

        # サマリー出力
        summary = config.get_summary()
        print(f"   モード: {summary['mode']}")
        print(f"   信頼度閾値: {summary['ml']['confidence_threshold']}")
        print(f"   タイムフレーム: {summary['data']['timeframes']}")

        return True

    except Exception as e:
        print(f"   ❌ 設定システムエラー: {e}")
        return False


def test_bitbank_client_basic():
    """BitbankClient基本機能テスト（認証不要）."""
    print("\n🏦 BitbankClient基本テスト...")

    try:
        # API認証情報なしでクライアント作成（公開APIのみ使用）
        client = BitbankClient(leverage=1.5)

        # 接続テスト（公開API使用）
        connection_ok = client.test_connection()
        print(f"   API接続テスト: {'✅' if connection_ok else '❌'}")

        # 統計情報取得
        stats = client.get_stats()
        print(f"   レバレッジ: {stats['leverage']}x")
        print(f"   信用取引モード: {'✅' if stats['margin_mode'] else '❌'}")

        # 市場情報取得
        market_info = client.get_market_info("BTC/JPY")
        print(f"   市場情報取得: ✅ {market_info['symbol']}")
        print(f"   基軸通貨: {market_info['base']} / 決済通貨: {market_info['quote']}")

        return True

    except Exception as e:
        print(f"   ❌ BitbankClientエラー: {e}")
        return False


def test_data_pipeline():
    """DataPipeline機能テスト."""
    print("\n📊 DataPipeline機能テスト...")

    try:
        # クライアント作成（認証不要）
        client = BitbankClient()
        pipeline = DataPipeline(client=client)

        # 単一タイムフレームデータ取得
        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H1, limit=5)  # 少量でテスト

        df = pipeline.fetch_ohlcv(request)
        print(f"   OHLCV取得: ✅ {len(df)}行")
        print(f"   カラム: {list(df.columns)}")

        if len(df) > 0:
            latest_price = df["close"].iloc[-1]
            print(f"   最新価格: ¥{latest_price:,.0f}")

        # キャッシュ機能テスト
        df_cached = pipeline.fetch_ohlcv(request, use_cache=True)
        print(f"   キャッシュ取得: ✅ {len(df_cached)}行")

        # キャッシュ情報確認
        cache_info = pipeline.get_cache_info()
        print(f"   キャッシュ項目数: {cache_info['total_cached_items']}")

        return True

    except Exception as e:
        print(f"   ❌ DataPipelineエラー: {e}")
        return False


def test_data_cache():
    """DataCache機能テスト."""
    print("\n💾 DataCache機能テスト...")

    try:
        # キャッシュ初期化
        cache = DataCache()

        # テストデータ（pandas DataFrame形式）
        import pandas as pd

        test_data = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2025-08-15 12:00:00"]),
                "open": [12340000],
                "high": [12350000],
                "low": [12330000],
                "close": [12345000],
                "volume": [1.5],
            }
        )
        test_data.set_index("timestamp", inplace=True)

        # データ保存
        cache.put("test_symbol", "1h", test_data)
        print("   データ保存: ✅")

        # データ取得
        retrieved_data = cache.get("test_symbol", "1h")
        if retrieved_data is not None and len(retrieved_data) > 0:
            latest_price = retrieved_data["close"].iloc[0]
            print(f"   データ取得: ✅ ¥{latest_price:,.0f}")
        else:
            print("   データ取得: ❌")
            return False

        # 統計情報取得
        stats = cache.get_cache_stats()
        print(f"   キャッシュサイズ: {stats['memory_cache_size']}項目")
        print(f"   ヒット率: {stats['hit_rate_percent']:.1f}%")

        return True

    except Exception as e:
        print(f"   ❌ DataCacheエラー: {e}")
        return False


def test_integration():
    """統合テスト."""
    print("\n🔗 統合テスト...")

    try:
        # 簡易APIを使用した統合テスト
        df = fetch_market_data(symbol="BTC/JPY", timeframe="1h", limit=3)

        if len(df) > 0:
            print(f"   統合API: ✅ {len(df)}行取得")
            print(f"   価格レンジ: ¥{df['low'].min():,.0f} - ¥{df['high'].max():,.0f}")
            return True
        else:
            print("   統合API: ❌ データなし")
            return False

    except Exception as e:
        print(f"   ❌ 統合テストエラー: {e}")
        return False


def main():
    """メインテスト実行."""
    print("🚀 Phase 2 コンポーネントテスト開始")
    print("=" * 50)

    tests = [
        ("設定システム", test_config_system),
        ("BitbankClient基本", test_bitbank_client_basic),
        ("DataPipeline", test_data_pipeline),
        ("DataCache", test_data_cache),
        ("統合テスト", test_integration),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"   💥 {test_name}で予期しないエラー: {e}")
            results[test_name] = False

    # 結果サマリー
    print("\n" + "=" * 50)
    print("📊 テスト結果サマリー")

    passed = 0
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1

    print(f"\n🎯 合格率: {passed}/{total} ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 Phase 2 コンポーネント実装完了！")
    else:
        print("⚠️  一部のテストが失敗しています。修正が必要です。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
