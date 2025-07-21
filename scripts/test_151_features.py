#!/usr/bin/env python3
"""
151特徴量生成テストスクリプト
Phase 5.1: 統合テスト・検証の一環として、
全151特徴量が正しく生成されているかを検証
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple
import json
import time

from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.main import load_config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Feature151Tester:
    """151特徴量の生成・検証を行うテストクラス"""
    
    def __init__(self, config_path: str = "config/production/production.yml"):
        """
        Args:
            config_path: 設定ファイルパス
        """
        self.config = load_config(config_path)
        self.feature_engineer = FeatureEngineer(self.config)
        self.test_results = {
            "total_features": 0,
            "expected_features": 151,
            "missing_features": [],
            "extra_features": [],
            "feature_categories": {},
            "test_status": "PENDING",
            "execution_time": 0,
            "memory_usage": 0
        }
        
    def generate_test_data(self, n_samples: int = 500) -> pd.DataFrame:
        """テスト用のOHLCVデータを生成"""
        logger.info(f"📊 Generating {n_samples} test OHLCV samples...")
        
        # 現在時刻から過去n_samples時間分のデータを生成
        end_time = datetime.now()
        timestamps = [end_time - timedelta(hours=i) for i in range(n_samples)]
        timestamps.reverse()
        
        # リアルなOHLCVデータを生成
        base_price = 5000000  # 500万円（BTC/JPY想定）
        prices = []
        volumes = []
        
        for i in range(n_samples):
            # 価格のランダムウォーク
            price_change = np.random.normal(0, 0.002) * base_price
            base_price += price_change
            
            # OHLC生成
            high = base_price * (1 + abs(np.random.normal(0, 0.001)))
            low = base_price * (1 - abs(np.random.normal(0, 0.001)))
            open_price = base_price + np.random.normal(0, 0.0005) * base_price
            close_price = base_price
            
            prices.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price
            })
            
            # ボリューム生成（実際の取引量に近い値）
            volume = abs(np.random.normal(100, 50))
            volumes.append(volume)
        
        # DataFrameの作成
        df = pd.DataFrame(prices)
        df['volume'] = volumes
        df['timestamp'] = timestamps
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"✅ Generated test data: {len(df)} rows, shape: {df.shape}")
        return df
    
    def analyze_features(self, features_df: pd.DataFrame) -> Dict:
        """生成された特徴量を分析"""
        feature_names = list(features_df.columns)
        
        # 特徴量をカテゴリ別に分類
        categories = {
            "基本OHLCV": [],
            "テクニカル指標": [],
            "価格アクション": [],
            "時系列トレンド": [],
            "クロスアセット": [],
            "外部データ": [],
            "高度特徴量": [],
            "その他": []
        }
        
        # 特徴量名でカテゴリ分類
        for feature in feature_names:
            if feature in ['open', 'high', 'low', 'close', 'volume']:
                categories["基本OHLCV"].append(feature)
            elif any(x in feature for x in ['rsi', 'macd', 'sma', 'ema', 'bb', 'atr', 'stoch', 'willr', 'adx', 'cmf', 'fisher']):
                categories["テクニカル指標"].append(feature)
            elif any(x in feature for x in ['price_position', 'candle', 'support', 'resistance', 'breakout']):
                categories["価格アクション"].append(feature)
            elif any(x in feature for x in ['autocorrelation', 'seasonal', 'regime', 'cycle']):
                categories["時系列トレンド"].append(feature)
            elif any(x in feature for x in ['cross_correlation', 'relative_strength', 'spread']):
                categories["クロスアセット"].append(feature)
            elif any(x in feature for x in ['vix', 'dxy', 'fear_greed', 'fg_', 'funding', 'oi_']):
                categories["外部データ"].append(feature)
            elif any(x in feature for x in ['volatility_regime', 'momentum_signals', 'liquidity']):
                categories["高度特徴量"].append(feature)
            else:
                categories["その他"].append(feature)
        
        return {
            "total": len(feature_names),
            "categories": {k: len(v) for k, v in categories.items()},
            "details": categories
        }
    
    def validate_feature_quality(self, features_df: pd.DataFrame) -> Dict:
        """特徴量の品質を検証"""
        quality_metrics = {
            "nan_ratio": {},
            "inf_ratio": {},
            "constant_features": [],
            "highly_correlated": []
        }
        
        for col in features_df.columns:
            # NaN率
            nan_ratio = features_df[col].isna().sum() / len(features_df)
            if nan_ratio > 0:
                quality_metrics["nan_ratio"][col] = nan_ratio
            
            # 無限大の割合
            inf_ratio = np.isinf(features_df[col].replace([np.inf, -np.inf], np.nan)).sum() / len(features_df)
            if inf_ratio > 0:
                quality_metrics["inf_ratio"][col] = inf_ratio
            
            # 定数特徴量（分散がほぼ0）
            if features_df[col].std() < 1e-10:
                quality_metrics["constant_features"].append(col)
        
        return quality_metrics
    
    def run_test(self) -> Dict:
        """151特徴量生成テストを実行"""
        start_time = time.time()
        
        try:
            logger.info("🚀 Starting 151-feature generation test...")
            
            # Step 1: テストデータ生成
            test_data = self.generate_test_data(n_samples=500)
            
            # Step 2: 特徴量生成
            logger.info("🔧 Generating features using FeatureEngineer...")
            features_df = self.feature_engineer.transform(test_data)
            
            # Step 3: 特徴量数の確認
            actual_features = len(features_df.columns)
            self.test_results["total_features"] = actual_features
            
            logger.info(f"📊 Generated features: {actual_features} (expected: 151)")
            
            # Step 4: 特徴量の分析
            feature_analysis = self.analyze_features(features_df)
            self.test_results["feature_categories"] = feature_analysis
            
            # Step 5: 品質検証
            quality_metrics = self.validate_feature_quality(features_df)
            self.test_results["quality_metrics"] = quality_metrics
            
            # Step 6: 結果判定
            if actual_features == 151:
                self.test_results["test_status"] = "PASSED"
                logger.info("✅ Feature count test PASSED!")
            else:
                self.test_results["test_status"] = "FAILED"
                logger.error(f"❌ Feature count test FAILED! Expected 151, got {actual_features}")
                
                # 不足または余分な特徴量を特定
                if actual_features < 151:
                    self.test_results["missing_count"] = 151 - actual_features
                else:
                    self.test_results["extra_count"] = actual_features - 151
            
            # カテゴリ別レポート
            logger.info("\n📋 Feature Category Report:")
            for category, count in feature_analysis["categories"].items():
                if count > 0:
                    logger.info(f"  - {category}: {count} features")
            
            # 品質レポート
            if quality_metrics["nan_ratio"]:
                logger.warning(f"\n⚠️ Features with NaN values: {len(quality_metrics['nan_ratio'])}")
            if quality_metrics["constant_features"]:
                logger.warning(f"⚠️ Constant features detected: {len(quality_metrics['constant_features'])}")
            
            # 実行時間
            execution_time = time.time() - start_time
            self.test_results["execution_time"] = execution_time
            logger.info(f"\n⏱️ Test completed in {execution_time:.2f} seconds")
            
            # 結果をJSONファイルに保存
            self.save_results()
            
            return self.test_results
            
        except Exception as e:
            logger.error(f"❌ Test failed with error: {str(e)}")
            self.test_results["test_status"] = "ERROR"
            self.test_results["error"] = str(e)
            return self.test_results
    
    def save_results(self):
        """テスト結果をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results/feature_test_151_{timestamp}.json"
        
        os.makedirs("test_results", exist_ok=True)
        
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        logger.info(f"💾 Test results saved to: {filename}")


def main():
    """メイン実行関数"""
    logger.info("=" * 80)
    logger.info("151 Feature Generation Test - Phase 5.1")
    logger.info("=" * 80)
    
    # テスト実行
    tester = Feature151Tester()
    results = tester.run_test()
    
    # 最終サマリー
    logger.info("\n" + "=" * 80)
    logger.info("📊 FINAL TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Status: {results['test_status']}")
    logger.info(f"Total Features: {results['total_features']} / 151")
    logger.info(f"Execution Time: {results.get('execution_time', 0):.2f}s")
    
    # テスト失敗時は非ゼロで終了
    if results['test_status'] != "PASSED":
        sys.exit(1)


if __name__ == "__main__":
    main()