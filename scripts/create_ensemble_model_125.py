#!/usr/bin/env python3
"""
Phase H.25: 125特徴量対応アンサンブルモデル作成スクリプト
外部API特徴量を除外した125特徴量でLGBM/XGBoost/RandomForestアンサンブルモデルを作成
"""

import logging
import os
import pickle
import sys
from datetime import datetime

import joblib
import numpy as np
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.feature_order_manager import FeatureOrderManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_dummy_data(n_samples=1000, n_features=125):
    """125特徴量のダミーデータを作成"""
    np.random.seed(42)

    # FeatureOrderManagerから特徴量順序を取得
    fom = FeatureOrderManager()
    feature_order_125 = fom.FEATURE_ORDER_125

    # FEATURE_ORDER_125の順序でデータを作成
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features), columns=feature_order_125[:n_features]
    )

    # ターゲット（バイナリ分類）
    y = np.random.randint(0, 2, size=n_samples)

    return X, y


def main():
    logger.info("🚀 Phase H.25: Creating 125-feature ensemble model...")

    # ダミーデータ作成
    X, y = create_dummy_data(n_samples=1000, n_features=125)
    logger.info(f"✅ Created dummy data: {X.shape}")

    # アンサンブルモデル設定
    ensemble_config = {
        "models": ["lgbm", "xgb", "rf"],
        "model_weights": [0.5, 0.3, 0.2],
        "lgbm_params": {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.1,
            "num_leaves": 31,
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": -1,
        },
        "xgb_params": {
            "n_estimators": 100,
            "max_depth": 5,
            "learning_rate": 0.1,
            "random_state": 42,
            "n_jobs": -1,
            "verbosity": 0,
        },
        "rf_params": {
            "n_estimators": 100,
            "max_depth": 5,
            "random_state": 42,
            "n_jobs": -1,
        },
        "use_calibration": False,
        "cv_folds": 3,
    }

    # アンサンブルモデル作成
    ensemble_model = TradingEnsembleClassifier(ensemble_config)

    # モデル学習
    logger.info("🔧 Training ensemble model...")
    ensemble_model.fit(X, y)

    # モデル保存
    model_dir = "models/production"
    os.makedirs(model_dir, exist_ok=True)

    # 既存モデルのバックアップ
    model_path = os.path.join(model_dir, "model.pkl")
    if os.path.exists(model_path):
        backup_path = os.path.join(
            model_dir, f"model_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        )
        os.rename(model_path, backup_path)
        logger.info(f"📦 Backed up existing model to: {backup_path}")

    # 新しいモデルを保存
    joblib.dump(ensemble_model, model_path)
    logger.info(f"💾 Saved ensemble model to: {model_path}")

    # feature_order.jsonも更新
    fom = FeatureOrderManager()
    fom.save_feature_order(fom.FEATURE_ORDER_125)
    logger.info("✅ Updated feature_order.json with 125 features")

    # 検証
    logger.info("\n🔍 Model validation:")
    predictions = ensemble_model.predict_proba(X[:10])
    logger.info(f"Sample predictions shape: {predictions.shape}")
    logger.info(f"Sample predictions: {predictions[:3]}")

    logger.info("\n✅ Phase H.25: Ensemble model creation completed!")
    logger.info(f"Model features: {len(fom.FEATURE_ORDER_125)} features")
    logger.info(f"Model type: TradingEnsembleClassifier with LGBM/XGBoost/RandomForest")


if __name__ == "__main__":
    main()
