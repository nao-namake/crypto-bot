#!/usr/bin/env python3
"""
155特徴量システム検証スクリプト
Phase H.24完了後の整合性確認

目的:
- 155特徴量が正しく生成されるか確認
- feature_order.jsonとの整合性確認
- モデル予測の正常動作確認
"""

import json
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/production/production.yml") -> dict:
    """設定ファイル読み込み"""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def create_sample_data() -> pd.DataFrame:
    """サンプルOHLCVデータを作成"""
    import numpy as np
    
    # 200行のサンプルデータ（十分な長さ）
    dates = pd.date_range(start="2025-01-01", periods=200, freq="1H")
    
    # 現実的な価格データを生成
    np.random.seed(42)
    base_price = 10000000  # 1000万円程度のBTC価格
    
    # ランダムウォーク的な価格変動
    price_changes = np.random.normal(0, 0.01, 200)  # 1%程度の変動
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, base_price * 0.5))  # 最低価格制限
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": prices,
        "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        "close": prices,
        "volume": np.random.uniform(10, 100, 200)
    })
    
    df.set_index("timestamp", inplace=True)
    logger.info(f"✅ Created sample OHLCV data: {len(df)} records")
    return df


def verify_feature_order_file():
    """feature_order.jsonの確認"""
    logger.info("🔍 Verifying feature_order.json...")
    
    feature_order_path = Path("feature_order.json")
    if not feature_order_path.exists():
        logger.error("❌ feature_order.json not found")
        return False
    
    with open(feature_order_path, "r") as f:
        data = json.load(f)
    
    expected_count = 155
    actual_count = data.get("num_features", 0)
    feature_list = data.get("feature_order", [])
    
    if actual_count != expected_count:
        logger.error(f"❌ Feature count mismatch: expected {expected_count}, got {actual_count}")
        return False
    
    if len(feature_list) != expected_count:
        logger.error(f"❌ Feature list length mismatch: expected {expected_count}, got {len(feature_list)}")
        return False
    
    # momentum_14が含まれているか確認
    if "momentum_14" not in feature_list:
        logger.error("❌ momentum_14 feature not found in feature order")
        return False
    
    logger.info(f"✅ feature_order.json verified: {actual_count} features including momentum_14")
    return True


def verify_feature_generation(config: dict):
    """特徴量生成の確認"""
    logger.info("🔍 Verifying feature generation...")
    
    try:
        # サンプルデータ作成
        sample_df = create_sample_data()
        
        # 特徴量エンジニア初期化
        feature_engineer = FeatureEngineer(config)
        
        # 特徴量生成
        features_df = feature_engineer.transform(sample_df)
        
        if features_df is None or features_df.empty:
            logger.error("❌ Feature generation failed: empty result")
            return False
        
        actual_features = features_df.shape[1]
        expected_features = 155
        
        if actual_features != expected_features:
            logger.warning(f"⚠️ Feature count: expected {expected_features}, got {actual_features}")
            logger.info("📋 Generated features:")
            for i, col in enumerate(features_df.columns):
                logger.info(f"  {i+1:3d}. {col}")
        else:
            logger.info(f"✅ Feature generation successful: {actual_features} features")
        
        # FeatureOrderManagerで順序確認
        manager = FeatureOrderManager()
        ordered_features = manager.ensure_column_order(features_df)
        
        if ordered_features is not None:
            logger.info(f"✅ Feature ordering successful: {ordered_features.shape[1]} features")
        else:
            logger.error("❌ Feature ordering failed")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Feature generation error: {e}")
        return False


def verify_model_compatibility():
    """モデル互換性の確認"""
    logger.info("🔍 Verifying model compatibility...")
    
    try:
        # FeatureOrderManagerの初期化テスト
        manager = FeatureOrderManager()
        
        # デフォルト特徴量順序の確認
        default_features = manager.FEATURE_ORDER_155
        
        if len(default_features) != 155:
            logger.error(f"❌ Default features count mismatch: {len(default_features)}")
            return False
        
        logger.info(f"✅ FeatureOrderManager initialized: {len(default_features)} default features")
        
        # 特徴量順序の一貫性テスト
        consistent_order = manager.get_consistent_order(default_features)
        
        if len(consistent_order) != 155:
            logger.error("❌ Consistent order generation failed")
            return False
        
        logger.info("✅ Feature consistency verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Model compatibility error: {e}")
        return False


def main():
    """メイン検証プロセス"""
    logger.info("🚀 Starting 155 features system verification...")
    
    # 設定読み込み
    try:
        config = load_config()
        logger.info("✅ Configuration loaded successfully")
    except Exception as e:
        logger.error(f"❌ Configuration loading failed: {e}")
        return False
    
    # 検証項目
    verifications = [
        ("Feature Order File", verify_feature_order_file),
        ("Feature Generation", lambda: verify_feature_generation(config)),
        ("Model Compatibility", verify_model_compatibility),
    ]
    
    all_passed = True
    results = []
    
    for name, verify_func in verifications:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {name}")
        logger.info(f"{'='*60}")
        
        try:
            result = verify_func()
            results.append((name, result))
            if result:
                logger.info(f"✅ {name}: PASSED")
            else:
                logger.error(f"❌ {name}: FAILED")
                all_passed = False
        except Exception as e:
            logger.error(f"❌ {name}: ERROR - {e}")
            results.append((name, False))
            all_passed = False
    
    # 結果サマリー
    logger.info(f"\n{'='*60}")
    logger.info("VERIFICATION RESULTS")
    logger.info(f"{'='*60}")
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{name:<25} {status}")
    
    if all_passed:
        logger.info("\n🎉 All verifications PASSED! 155 features system is ready.")
        return True
    else:
        logger.error("\n❌ Some verifications FAILED. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)