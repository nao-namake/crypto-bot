#!/usr/bin/env python3
"""
Phase 1診断スクリプト: hour・day_of_week特徴量enhanced_default汚染問題特定

目的:
- 125特徴量システムでhour・day_of_week特徴量が正しく生成されているか確認
- enhanced_default汚染の原因特定
- 特徴量生成プロセスの詳細ログ出力
"""

import logging
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
sys.path.append("/Users/nao/Desktop/bot")

from crypto_bot.ml.feature_engines.batch_calculator import BatchFeatureCalculator
from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def create_test_data_with_datetime_index(num_rows=100):
    """DatetimeIndexを持つテストデータ作成"""
    # 現在時刻から遡って時系列データ作成
    end_time = datetime.now(timezone.utc)
    timestamps = pd.date_range(end=end_time, periods=num_rows, freq="H")  # 1時間間隔

    # Bitcoin価格風のダミーデータ
    base_price = 50000
    price_changes = np.random.normal(0, 0.02, num_rows)  # 2%変動
    prices = [base_price]

    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)

    # OHLCV データフレーム作成
    data = {
        "open": [p * np.random.uniform(0.998, 1.002) for p in prices],
        "high": [p * np.random.uniform(1.001, 1.020) for p in prices],
        "low": [p * np.random.uniform(0.980, 0.999) for p in prices],
        "close": prices,
        "volume": np.random.uniform(100, 1000, num_rows),
    }

    df = pd.DataFrame(data, index=timestamps)
    df.index.name = "timestamp"

    logger.info(f"✅ Test data created: {len(df)} rows")
    logger.info(f"   Index type: {type(df.index)}")
    logger.info(f"   Index has hour attr: {hasattr(df.index, 'hour')}")
    logger.info(f"   Index name: {df.index.name}")
    logger.info(f"   Date range: {df.index[0]} to {df.index[-1]}")

    return df


def diagnose_time_features():
    """時間特徴量生成診断"""
    logger.info("🔍 Phase 1診断開始: hour・day_of_week特徴量enhanced_default汚染問題")

    try:
        # 1. 設定ロード
        config_path = "/Users/nao/Desktop/bot/config/production/production.yml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info("✅ Production config loaded")

        # 2. テストデータ作成
        test_df = create_test_data_with_datetime_index(50)

        # 3. バッチ計算機初期化
        batch_calc = BatchFeatureCalculator(config)

        # 4. テクニカルエンジン初期化
        tech_engine = TechnicalFeatureEngine(config, batch_calc)
        logger.info("✅ TechnicalFeatureEngine initialized")

        # 5. 時間特徴量のみ計算テスト
        logger.info("🧪 Testing missing_features_batch calculation...")
        missing_batch = tech_engine.calculate_missing_features_batch(test_df)

        # 6. 結果分析
        logger.info(f"📊 Missing features batch results:")
        logger.info(f"   Total features generated: {len(missing_batch.features)}")

        # 時間関連特徴量チェック
        time_features = [
            "hour",
            "day_of_week",
            "is_weekend",
            "is_asian_session",
            "is_european_session",
            "is_us_session",
        ]

        for feature in time_features:
            if feature in missing_batch.features:
                values = missing_batch.features[feature]
                logger.info(
                    f"   ✅ {feature}: Generated - Type: {type(values)} - Sample: {values.iloc[:5].tolist()}"
                )

                # enhanced_defaultチェック
                if hasattr(values, "dtype") and "object" in str(values.dtype):
                    unique_vals = (
                        values.unique() if hasattr(values, "unique") else [str(values)]
                    )
                    if any("enhanced_default" in str(val) for val in unique_vals):
                        logger.error(
                            f"   ❌ {feature}: ENHANCED_DEFAULT contamination detected!"
                        )
                        logger.error(f"      Unique values: {unique_vals}")
                    else:
                        logger.info(
                            f"   ✅ {feature}: No enhanced_default contamination"
                        )

            else:
                logger.error(f"   ❌ {feature}: NOT GENERATED")

        # 7. 特徴量順序確認
        feature_order_path = "/Users/nao/Desktop/bot/config/core/feature_order.json"
        if os.path.exists(feature_order_path):
            import json

            with open(feature_order_path, "r") as f:
                feature_order = json.load(f)

            logger.info(f"📋 Feature order analysis:")
            logger.info(f"   Expected features: {feature_order['num_features']}")

            # 時間特徴量が正しい順序にあるかチェック
            expected_order = feature_order["feature_order"]
            for feature in time_features:
                if feature in expected_order:
                    position = expected_order.index(feature) + 1
                    logger.info(
                        f"   ✅ {feature}: Position {position} in feature order"
                    )
                else:
                    logger.error(f"   ❌ {feature}: Missing from feature order!")

        # 8. 診断サマリ
        logger.info("🎯 診断結果サマリ:")
        generated_time_features = [
            f for f in time_features if f in missing_batch.features
        ]
        missing_time_features = [
            f for f in time_features if f not in missing_batch.features
        ]

        logger.info(f"   Generated time features: {len(generated_time_features)}/6")
        logger.info(f"   Generated: {generated_time_features}")
        if missing_time_features:
            logger.error(f"   Missing: {missing_time_features}")

        # 9. 実際のデータ値サンプル表示
        if "hour" in missing_batch.features and "day_of_week" in missing_batch.features:
            sample_df = pd.DataFrame(
                {
                    "timestamp": test_df.index[:10],
                    "hour": missing_batch.features["hour"].iloc[:10],
                    "day_of_week": missing_batch.features["day_of_week"].iloc[:10],
                    "expected_hour": test_df.index[:10].hour,
                    "expected_dow": test_df.index[:10].dayofweek,
                }
            )
            logger.info("📊 Sample time feature comparison:")
            logger.info(f"\n{sample_df.to_string()}")

            # 値の一致確認
            hour_match = (sample_df["hour"] == sample_df["expected_hour"]).all()
            dow_match = (sample_df["day_of_week"] == sample_df["expected_dow"]).all()

            logger.info(f"   Hour values match: {hour_match}")
            logger.info(f"   Day of week values match: {dow_match}")

            if not hour_match or not dow_match:
                logger.error("❌ Time feature values do not match expected values!")
                return False
            else:
                logger.info("✅ Time feature values match expected values!")

        return True

    except Exception as e:
        logger.error(f"❌ Diagnosis failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = diagnose_time_features()
    if success:
        print("\n🎉 Diagnosis completed successfully!")
        print("✅ Time features appear to be working correctly")
        print(
            "🔄 Next step: Check if the issue is in the ML pipeline or feature integration"
        )
    else:
        print("\n❌ Diagnosis revealed issues!")
        print("🔧 Time features need to be fixed before proceeding")

    sys.exit(0 if success else 1)
