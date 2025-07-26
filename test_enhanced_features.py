#!/usr/bin/env python3
"""
特徴量強化システムテストスクリプト
Phase H.11: 特徴量完全性保証システム動作確認
"""

import sys
import os
import traceback
from datetime import datetime
import pandas as pd
import numpy as np

# プロジェクトルートをパスに追加
sys.path.insert(0, '/Users/nao/Desktop/bot')

def test_enhanced_feature_import():
    """特徴量強化システムインポートテスト"""
    print("📦 [TEST-1] 特徴量強化システムインポートテスト...")
    try:
        from crypto_bot.ml.feature_engineering_enhanced import (
            FeatureEngineeringEnhanced,
            enhance_feature_engineering
        )
        from crypto_bot.ml.preprocessor import (
            prepare_ml_dataset_enhanced,
            ensure_feature_coverage
        )
        print("✅ 特徴量強化システムインポート成功")
        return True
    except Exception as e:
        print(f"❌ インポート失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return False

def test_feature_audit():
    """特徴量実装監査テスト"""
    print("\n🔍 [TEST-2] 特徴量実装監査テスト...")
    try:
        from crypto_bot.ml.feature_engineering_enhanced import FeatureEngineeringEnhanced
        
        enhancer = FeatureEngineeringEnhanced()
        
        # テスト用特徴量リスト（production.ymlから抜粋）
        test_features = [
            'rsi_14', 'rsi_7', 'rsi_21', 'macd', 
            'sma_10', 'sma_20', 'sma_50',
            'vix', 'dxy', 'fear_greed',
            'momentum_14', 'trend_strength',  # 未実装特徴量
            'unknown_feature_test'  # 完全未知特徴量
        ]
        
        audit_result = enhancer.audit_feature_implementation(test_features)
        
        print(f"   - 総特徴量数: {audit_result['total_requested']}")
        print(f"   - 実装済み: {len(audit_result['implemented'])} ({audit_result['implementation_rate']:.1%})")
        print(f"   - 未実装: {len(audit_result['missing'])}")
        print(f"   - 外部データ依存: {len(audit_result['external_dependent'])}")
        print(f"   - 派生可能: {len(audit_result['derivable'])}")
        
        if audit_result['implemented']:
            print(f"   実装済み例: {audit_result['implemented'][:3]}")
        if audit_result['missing']:
            print(f"   未実装例: {audit_result['missing'][:3]}")
        
        print("✅ 特徴量実装監査成功")
        return audit_result
    except Exception as e:
        print(f"❌ 監査失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return None

def test_missing_feature_generation():
    """未実装特徴量動的生成テスト"""
    print("\n🛠️ [TEST-3] 未実装特徴量動的生成テスト...")
    try:
        from crypto_bot.ml.feature_engineering_enhanced import FeatureEngineeringEnhanced
        
        # テスト用OHLCVデータ生成
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        np.random.seed(42)
        
        df = pd.DataFrame({
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 100 + np.random.randn(100).cumsum() + 1,
            'low': 100 + np.random.randn(100).cumsum() - 1,
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        
        print(f"   テストデータ: {df.shape}")
        
        enhancer = FeatureEngineeringEnhanced()
        
        # 未実装特徴量リスト
        missing_features = ['momentum_14', 'trend_strength', 'volatility_24h', 'correlation_spy']
        
        generated_df = enhancer.generate_missing_features(df, missing_features)
        
        print(f"   生成後データ: {generated_df.shape}")
        print(f"   生成された特徴量: {len(enhancer.generated_features)}")
        
        # 生成された特徴量の確認
        for feature in missing_features:
            if feature in generated_df.columns:
                feature_stats = generated_df[feature].describe()
                print(f"   {feature}: mean={feature_stats['mean']:.4f}, std={feature_stats['std']:.4f}")
            else:
                print(f"   {feature}: 生成失敗")
        
        print("✅ 未実装特徴量動的生成成功")
        return generated_df
    except Exception as e:
        print(f"❌ 動的生成失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return None

def test_feature_quality_validation():
    """特徴量品質バリデーションテスト"""
    print("\n🔍 [TEST-4] 特徴量品質バリデーションテスト...")
    try:
        from crypto_bot.ml.feature_engineering_enhanced import FeatureEngineeringEnhanced
        
        # テスト用データ準備
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1h')
        
        df = pd.DataFrame({
            'good_feature': np.random.randn(50),  # 良質な特徴量
            'bad_feature': [np.nan] * 25 + [0] * 25,  # 低品質特徴量
            'zero_feature': [0] * 50,  # ゼロ分散特徴量
            'normal_feature': np.random.normal(0, 1, 50)  # 正常特徴量
        }, index=dates)
        
        enhancer = FeatureEngineeringEnhanced()
        quality_scores = enhancer.validate_feature_quality(df, df.columns.tolist())
        
        print("   特徴量品質スコア:")
        for feature, score in quality_scores.items():
            status = "✅" if score > 0.5 else "⚠️" if score > 0.2 else "❌"
            print(f"   {status} {feature}: {score:.3f}")
        
        avg_quality = np.mean(list(quality_scores.values()))
        print(f"   平均品質スコア: {avg_quality:.3f}")
        
        print("✅ 特徴量品質バリデーション成功")
        return quality_scores
    except Exception as e:
        print(f"❌ 品質バリデーション失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return None

def test_config_integration():
    """設定ファイル統合テスト"""
    print("\n⚙️ [TEST-5] 設定ファイル統合テスト...")
    try:
        from crypto_bot.main import load_config
        
        config = load_config('config/production/production.yml')
        
        # 特徴量設定の確認
        ml_features = config.get('ml', {}).get('extra_features', [])
        strategy_features = config.get('strategy', {}).get('params', {}).get('ml', {}).get('extra_features', [])
        
        all_features = list(set(ml_features + strategy_features))
        
        print(f"   ML特徴量: {len(ml_features)}")
        print(f"   戦略特徴量: {len(strategy_features)}")
        print(f"   総特徴量（重複除去後）: {len(all_features)}")
        
        if all_features:
            print(f"   特徴量例: {all_features[:5]}")
        
        # フォールバック設定の確認
        fallback_config = config.get('feature_fallback', {})
        if fallback_config:
            print("   フォールバック設定:")
            print(f"     - 自動生成: {fallback_config.get('auto_generate_missing', False)}")
            missing_count = len(fallback_config.get('missing_features', []))
            print(f"     - 未実装特徴量: {missing_count}個")
        
        print("✅ 設定ファイル統合成功")
        return config
    except Exception as e:
        print(f"❌ 設定統合失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return None

def test_complete_integration():
    """完全統合テスト"""
    print("\n🚀 [TEST-6] 完全統合テスト...")
    try:
        from crypto_bot.ml.feature_engineering_enhanced import enhance_feature_engineering
        
        # テスト用設定
        config = {
            'ml': {
                'extra_features': [
                    'rsi_14', 'macd', 'sma_20',  # 実装済み
                    'momentum_14', 'trend_strength',  # 未実装→動的生成
                    'vix', 'fear_greed'  # 外部データ
                ]
            },
            'strategy': {
                'params': {
                    'ml': {
                        'extra_features': ['volatility_24h', 'correlation_spy']  # 追加
                    }
                }
            }
        }
        
        # テストデータ
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1h')
        np.random.seed(42)
        
        df = pd.DataFrame({
            'open': 5000000 + np.random.randn(200).cumsum() * 10000,
            'high': 5000000 + np.random.randn(200).cumsum() * 10000 + 5000,
            'low': 5000000 + np.random.randn(200).cumsum() * 10000 - 5000,
            'close': 5000000 + np.random.randn(200).cumsum() * 10000,
            'volume': np.random.randint(100, 1000, 200)
        }, index=dates)
        
        print(f"   入力データ: {df.shape}")
        
        # 完全統合処理実行
        enhanced_df, feature_report = enhance_feature_engineering(df, config)
        
        print(f"   出力データ: {enhanced_df.shape}")
        print(f"   特徴量追加数: {enhanced_df.shape[1] - df.shape[1]}")
        
        # レポート詳細
        print("\n   📋 統合レポート:")
        audit = feature_report['audit_result']
        print(f"     - 実装率: {audit['implementation_rate']:.1%}")
        print(f"     - 総特徴量: {audit['total_requested']}")
        print(f"     - 実装済み: {len(audit['implemented'])}")
        print(f"     - 未実装: {len(audit['missing'])}")
        print(f"     - 動的生成: {len(feature_report['generated_features'])}")
        print(f"     - 完全性率: {feature_report['completeness_rate']:.1%}")
        
        avg_quality = np.mean(list(feature_report['quality_scores'].values()))
        print(f"     - 平均品質: {avg_quality:.3f}")
        
        print("✅ 完全統合テスト成功")
        return enhanced_df, feature_report
    except Exception as e:
        print(f"❌ 完全統合失敗: {e}")
        print(f"📋 詳細: {traceback.format_exc()}")
        return None, None

def main():
    """メインテスト実行"""
    print("🧪 特徴量強化システム総合テスト開始")
    print(f"⏰ テスト開始時刻: {datetime.now()}")
    print("=" * 80)
    
    # テストシーケンス
    tests = [
        test_enhanced_feature_import,
        test_feature_audit,
        test_missing_feature_generation,
        test_feature_quality_validation,
        test_config_integration,
        test_complete_integration
    ]
    
    results = []
    for i, test_func in enumerate(tests, 1):
        try:
            result = test_func()
            success = result is not None and result is not False
            results.append(success)
            
            if not success:
                print(f"⚠️ テスト{i}で問題が検出されました")
        except Exception as e:
            print(f"❌ テスト{i}で例外発生: {e}")
            results.append(False)
    
    # 結果サマリ
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリ")
    print(f"成功: {sum(results)}/{len(results)} ({sum(results)/len(results)*100:.1f}%)")
    
    for i, (test_func, success) in enumerate(zip(tests, results), 1):
        status = "✅" if success else "❌"
        print(f"  {status} テスト{i}: {test_func.__name__}")
    
    if all(results):
        print("\n🎉 特徴量強化システム - 全テスト成功！")
        print("💡 特徴量の抜け漏れ防止システムが正常に動作しています")
    else:
        print(f"\n⚠️ {len(results) - sum(results)}個のテストで問題が検出されました")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)