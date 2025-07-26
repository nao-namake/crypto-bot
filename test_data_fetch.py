#!/usr/bin/env python3
"""
データ取得機能テストスクリプト
修正した設定でのデータ取得が実際に動作するかテスト
"""

import sys
import os
import traceback
from datetime import datetime
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, '/Users/nao/Desktop/bot')

def test_config_loading():
    """設定ファイル読み込みテスト"""
    print("📋 [TEST-1] 設定ファイル読み込みテスト...")
    try:
        from crypto_bot.main import load_config
        config = load_config('config/production/production.yml')
        
        data_config = config.get('data', {})
        print(f"✅ 設定読み込み成功")
        print(f"   - exchange: {data_config.get('exchange')}")
        print(f"   - symbol: {data_config.get('symbol')}")
        print(f"   - limit: {data_config.get('limit')}")
        print(f"   - per_page: {data_config.get('per_page')}")
        print(f"   - since_hours: {data_config.get('since_hours')}")
        return config
    except Exception as e:
        print(f"❌ 設定読み込み失敗: {e}")
        return None

def test_api_credentials():
    """API認証情報テスト"""
    print("\n🔑 [TEST-2] API認証情報テスト...")
    try:
        api_key = os.getenv('BITBANK_API_KEY')
        api_secret = os.getenv('BITBANK_API_SECRET')
        
        if api_key and api_secret:
            print(f"✅ API認証情報存在: キー長={len(api_key)}, シークレット長={len(api_secret)}")
            return True
        else:
            print(f"❌ API認証情報不足: キー={bool(api_key)}, シークレット={bool(api_secret)}")
            return False
    except Exception as e:
        print(f"❌ API認証チェック失敗: {e}")
        return False

def test_data_fetcher_init(config):
    """データフェッチャー初期化テスト"""
    print("\n🔌 [TEST-3] データフェッチャー初期化テスト...")
    try:
        from crypto_bot.data.fetcher import MarketDataFetcher
        
        dd = config.get('data', {})
        fetcher = MarketDataFetcher(
            exchange_id=dd.get('exchange'),
            symbol=dd.get('symbol'),
            ccxt_options=dd.get('ccxt_options', {}),
        )
        print(f"✅ フェッチャー初期化成功")
        return fetcher
    except Exception as e:
        print(f"❌ フェッチャー初期化失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return None

def test_small_data_fetch(fetcher, config):
    """少量データ取得テスト"""
    print("\n📊 [TEST-4] 少量データ取得テスト（10件）...")
    try:
        dd = config.get('data', {})
        
        # まず少量で試す
        df = fetcher.get_price_df(
            timeframe='1h',
            limit=10,  # 少量でテスト
            paginate=False,  # シンプルに
        )
        
        if df is not None and not df.empty:
            print(f"✅ 少量データ取得成功: {len(df)} 件")
            print(f"   - データ範囲: {df.index.min()} ～ {df.index.max()}")
            print(f"   - カラム: {list(df.columns)}")
            return True
        else:
            print(f"❌ 少量データ取得失敗: データが空")
            return False
    except Exception as e:
        print(f"❌ 少量データ取得失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return False

def test_medium_data_fetch(fetcher, config):
    """中量データ取得テスト"""
    print("\n📈 [TEST-5] 中量データ取得テスト（100件）...")
    try:
        dd = config.get('data', {})
        
        # 中量で試す
        df = fetcher.get_price_df(
            timeframe='1h',
            limit=100,  # 中量でテスト
            paginate=True,  # ページネーション有効
            per_page=50,   # 小さめのページサイズ
        )
        
        if df is not None and not df.empty:
            print(f"✅ 中量データ取得成功: {len(df)} 件")
            print(f"   - データ範囲: {df.index.min()} ～ {df.index.max()}")
            return True
        else:
            print(f"❌ 中量データ取得失敗: データが空")
            return False
    except Exception as e:
        print(f"❌ 中量データ取得失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return False

def test_atr_calculation(df):
    """ATR計算テスト"""
    print("\n🔢 [TEST-6] ATR計算テスト...")
    try:
        from crypto_bot.indicator.calculator import IndicatorCalculator
        
        calculator = IndicatorCalculator()
        atr_series = calculator.calculate_atr(df, period=14)
        
        if atr_series is not None and not atr_series.empty:
            latest_atr = atr_series.iloc[-1]
            print(f"✅ ATR計算成功: {len(atr_series)} 値")
            print(f"   - 最新ATR: {latest_atr:.6f}")
            print(f"   - 平均ATR: {atr_series.mean():.6f}")
            return True
        else:
            print(f"❌ ATR計算失敗: 結果が空")
            return False
    except Exception as e:
        print(f"❌ ATR計算失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return False

def main():
    """メインテスト実行"""
    print("🧪 データ取得機能テスト開始")
    print(f"⏰ テスト開始時刻: {datetime.now()}")
    print("=" * 60)
    
    # テストシーケンス
    config = test_config_loading()
    if not config:
        return False
        
    if not test_api_credentials():
        print("⚠️ API認証情報がないため、データ取得テストをスキップ")
        return False
        
    fetcher = test_data_fetcher_init(config)
    if not fetcher:
        return False
        
    if not test_small_data_fetch(fetcher, config):
        return False
        
    if not test_medium_data_fetch(fetcher, config):
        return False
        
    # 最後に取得したデータでATRテスト
    try:
        df = fetcher.get_price_df(timeframe='1h', limit=30, paginate=False)
        if df is not None and not df.empty:
            test_atr_calculation(df)
    except:
        pass
    
    print("\n" + "=" * 60)
    print("✅ データ取得機能テスト完了")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)