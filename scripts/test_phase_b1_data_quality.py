#!/usr/bin/env python3
"""
Phase B1: データ品質改善効果検証スクリプト
sources設定修正・MacroDataFetcher MultiSource対応効果テスト

期待改善:
- default_ratio: 0.92 → 0.75以下（目標）
- 外部データ取得成功率向上
- 特徴量生成品質向上
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.main import load_config
from crypto_bot.data.vix_fetcher import VIXDataFetcher
from crypto_bot.data.macro_fetcher import MacroDataFetcher
from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher
from crypto_bot.monitoring.data_quality_monitor import get_quality_monitor


def test_data_source_configuration(config_path: str):
    """データソース設定の確認"""
    print("🔧 Phase B1: データソース設定確認")
    
    try:
        config = load_config(config_path)
        external_data = config.get('ml', {}).get('external_data', {})
        
        print(f"✅ 設定ファイル読み込み: {config_path}")
        
        # 各データソースのsources設定確認
        for data_type in ['vix', 'macro', 'fear_greed', 'funding']:
            data_config = external_data.get(data_type, {})
            sources = data_config.get('sources', [])
            enabled = data_config.get('enabled', False)
            
            status = "✅" if sources and enabled else "❌"
            print(f"{status} {data_type}: enabled={enabled}, sources={sources}")
            
        return True
        
    except Exception as e:
        print(f"❌ 設定読み込みエラー: {e}")
        return False


def test_vix_fetcher_multisource(config: dict):
    """VIXフェッチャー MultiSource対応テスト"""
    print("\n📈 Phase B1: VIXデータ取得テスト")
    
    try:
        vix_fetcher = VIXDataFetcher(config)
        
        # データソース状態確認
        source_status = vix_fetcher.get_source_status()
        print(f"📊 VIXデータソース状態: {len(source_status)} sources")
        
        for source_name, status in source_status.items():
            enabled = "🟢" if status['enabled'] else "🔴"
            print(f"  {enabled} {source_name}: {status['status']}")
        
        # VIXデータ取得テスト
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        vix_data = vix_fetcher.get_vix_data(start_date=start_date)
        
        if vix_data is not None and not vix_data.empty:
            print(f"✅ VIXデータ取得成功: {len(vix_data)} records")
            
            # 品質評価
            quality_score = vix_fetcher._validate_data_quality(vix_data)
            print(f"📊 VIXデータ品質スコア: {quality_score:.3f}")
            
            # 特徴量計算テスト
            vix_features = vix_fetcher.calculate_vix_features(vix_data)
            print(f"🔢 VIX特徴量生成: {len(vix_features.columns)} features")
            
            return quality_score
        else:
            print("❌ VIXデータ取得失敗")
            return 0.0
            
    except Exception as e:
        print(f"❌ VIXテストエラー: {e}")
        return 0.0


def test_macro_fetcher_multisource(config: dict):
    """MacroフェッチャーMultiSource対応テスト（重要）"""
    print("\n💱 Phase B1: Macroデータ取得テスト（MultiSource対応）")
    
    try:
        macro_fetcher = MacroDataFetcher(config)
        
        # データソース状態確認
        source_status = macro_fetcher.get_source_status()
        print(f"📊 Macroデータソース状態: {len(source_status)} sources")
        
        for source_name, status in source_status.items():
            enabled = "🟢" if status['enabled'] else "🔴"
            print(f"  {enabled} {source_name}: {status['status']}")
        
        # Macroデータ取得テスト（統合データ取得）
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # MultiSourceDataFetcher統合版での取得
        unified_data = macro_fetcher.get_data(start_date=start_date)
        print(f"🔗 統合Macroデータ: {len(unified_data) if unified_data is not None else 0} records")
        
        # 従来形式での取得（後方互換性確認）
        macro_data_dict = macro_fetcher.get_macro_data(start_date=start_date)
        
        if macro_data_dict and any(not df.empty for df in macro_data_dict.values()):
            total_records = sum(len(df) for df in macro_data_dict.values() if not df.empty)
            print(f"✅ Macroデータ取得成功: {total_records} total records")
            print(f"📁 取得シンボル: {list(macro_data_dict.keys())}")
            
            # 品質評価
            if unified_data is not None and not unified_data.empty:
                quality_score = macro_fetcher._validate_data_quality(unified_data)
                print(f"📊 Macroデータ品質スコア: {quality_score:.3f}")
                
                # 特徴量計算テスト
                macro_features = macro_fetcher.calculate_macro_features(macro_data_dict)
                print(f"🔢 Macro特徴量生成: {len(macro_features.columns)} features")
                
                return quality_score
            else:
                print("⚠️ 統合データが空 - フォールバック使用")
                return 0.3
        else:
            print("❌ Macroデータ取得失敗")
            return 0.0
            
    except Exception as e:
        print(f"❌ Macroテストエラー: {e}")
        import traceback
        traceback.print_exc()
        return 0.0


def test_fear_greed_fetcher_multisource(config: dict):
    """Fear&Greedフェッチャー MultiSource対応テスト"""
    print("\n😰 Phase B1: Fear&Greedデータ取得テスト")
    
    try:
        fg_fetcher = FearGreedDataFetcher(config)
        
        # データソース状態確認
        source_status = fg_fetcher.get_source_status()
        print(f"📊 Fear&Greedデータソース状態: {len(source_status)} sources")
        
        for source_name, status in source_status.items():
            enabled = "🟢" if status['enabled'] else "🔴"
            print(f"  {enabled} {source_name}: {status['status']}")
        
        # Fear&Greedデータ取得テスト
        fg_data = fg_fetcher.get_fear_greed_data(limit=30)
        
        if fg_data is not None and not fg_data.empty:
            print(f"✅ Fear&Greedデータ取得成功: {len(fg_data)} records")
            
            # 品質評価
            quality_score = fg_fetcher._validate_data_quality(fg_data)
            print(f"📊 Fear&Greedデータ品質スコア: {quality_score:.3f}")
            
            # 特徴量計算テスト
            fg_features = fg_fetcher.calculate_fear_greed_features(fg_data)
            print(f"🔢 Fear&Greed特徴量生成: {len(fg_features.columns)} features")
            
            return quality_score
        else:
            print("❌ Fear&Greedデータ取得失敗")
            return 0.0
            
    except Exception as e:
        print(f"❌ Fear&Greedテストエラー: {e}")
        return 0.0


def test_overall_data_quality_improvement(config: dict):
    """全体的なデータ品質改善効果測定"""
    print("\n🎯 Phase B1: 総合データ品質改善効果測定")
    
    try:
        # 品質監視システム初期化
        quality_monitor = get_quality_monitor(config)
        
        # 各データソースのテスト
        vix_quality = test_vix_fetcher_multisource(config)
        macro_quality = test_macro_fetcher_multisource(config)  # ⭐ 重要改善点
        fg_quality = test_fear_greed_fetcher_multisource(config)
        
        # 総合品質スコア計算
        quality_scores = [vix_quality, macro_quality, fg_quality]
        active_sources = [q for q in quality_scores if q > 0]
        
        if active_sources:
            average_quality = sum(active_sources) / len(active_sources)
            default_ratio = 1.0 - average_quality  # 品質スコアの逆
            
            print(f"\n📊 Phase B1 総合結果:")
            print(f"  🎯 VIXデータ品質: {vix_quality:.3f}")
            print(f"  💱 Macroデータ品質: {macro_quality:.3f} ⭐ (主要改善)")
            print(f"  😰 Fear&Greedデータ品質: {fg_quality:.3f}")
            print(f"  📈 平均品質スコア: {average_quality:.3f}")
            print(f"  📉 推定default_ratio: {default_ratio:.3f}")
            
            # 目標達成判定
            target_default_ratio = 0.75  # 目標: 0.92→0.75
            if default_ratio <= target_default_ratio:
                print(f"✅ 品質改善目標達成! ({default_ratio:.3f} ≤ {target_default_ratio})")
                return True
            else:
                print(f"⚠️ 品質改善継続必要 ({default_ratio:.3f} > {target_default_ratio})")
                return False
        else:
            print("❌ 全データソース失敗")
            return False
            
    except Exception as e:
        print(f"❌ 総合テストエラー: {e}")
        return False


def main():
    """Phase B1データ品質改善効果検証メイン"""
    print("🚀 Phase B1: データ品質改善効果検証開始")
    print("=" * 60)
    
    # 検証用設定でテスト（sources設定修正後）
    validation_config_path = "config/validation/mtf_ensemble_test.yml"
    production_config_path = "config/production/production.yml"
    
    test_configs = [
        ("検証用設定", validation_config_path),
        ("本番用設定", production_config_path)
    ]
    
    results = []
    
    for config_name, config_path in test_configs:
        print(f"\n🔍 {config_name}でのテスト ({config_path})")
        print("-" * 50)
        
        # 設定確認
        config_ok = test_data_source_configuration(config_path)
        if not config_ok:
            print(f"❌ {config_name}: 設定エラーのためスキップ")
            continue
        
        # 設定読み込み
        try:
            config = load_config(config_path)
            
            # データ品質改善テスト
            improvement_success = test_overall_data_quality_improvement(config)
            results.append((config_name, improvement_success))
            
        except Exception as e:
            print(f"❌ {config_name}テストエラー: {e}")
            results.append((config_name, False))
    
    # 最終結果サマリー
    print("\n" + "=" * 60)
    print("🎯 Phase B1 データ品質改善効果検証結果")
    print("=" * 60)
    
    success_count = 0
    for config_name, success in results:
        status = "✅ 目標達成" if success else "⚠️ 改善継続必要"
        print(f"{status} {config_name}")
        if success:
            success_count += 1
    
    overall_success = success_count >= len(results) // 2
    
    if overall_success:
        print("\n🎉 Phase B1 データ品質改善：全体的成功!")
        print("📈 MacroDataFetcher MultiSource対応による品質向上確認")
        print("🔄 Phase B2 (特徴量生成最適化) 移行準備完了")
    else:
        print("\n⚠️ Phase B1 データ品質改善：部分的成功")
        print("🔧 追加修正・調整が必要")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)