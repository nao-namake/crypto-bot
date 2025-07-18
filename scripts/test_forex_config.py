#!/usr/bin/env python3
"""
USD/JPY為替特徴量設定テスト
為替特徴量統合版設定の動作確認
"""

import os
import sys

sys.path.append("/Users/nao/Desktop/bot")

import logging
from datetime import datetime

import pandas as pd
import yaml

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_forex_config():
    """為替特徴量設定のテスト"""
    logger.info("🚀 USD/JPY為替特徴量設定テスト開始")

    # 1. 設定ファイル読み込み
    config_path = "/Users/nao/Desktop/bot/config/production/bitbank_forex_enhanced.yml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ 設定ファイル読み込み成功: {config_path}")

        # 2. 為替特徴量設定確認
        extra_features = config.get("ml", {}).get("extra_features", [])
        logger.info(f"📊 extra_features: {extra_features}")

        # 3. 為替特徴量有効化確認
        forex_enabled = "usdjpy" in extra_features
        logger.info(f"💱 USD/JPY為替特徴量有効化: {'✅' if forex_enabled else '❌'}")

        # 4. 外部データ設定確認
        external_data = config.get("external_data", {})
        forex_config = external_data.get("forex", {})
        logger.info(f"🔧 外部データ設定: {external_data.get('enabled', False)}")
        logger.info(f"🔧 為替データ設定: {forex_config.get('enabled', False)}")

        # 5. Preprocessor初期化テスト
        from crypto_bot.ml.preprocessor import FeatureEngineer

        logger.info("🔍 FeatureEngineer初期化テスト中...")
        feature_engineer = FeatureEngineer(config)

        # 為替フェッチャー初期化確認
        logger.info(
            f"💱 Forex fetcher初期化: {'✅' if feature_engineer.forex_enabled else '❌'}"
        )
        logger.info(
            f"💱 Forex fetcher存在: {'✅' if feature_engineer.forex_fetcher else '❌'}"
        )

        # 6. 為替データ取得テスト
        if feature_engineer.forex_enabled and feature_engineer.forex_fetcher:
            logger.info("🔍 為替データ取得テスト中...")
            try:
                # 簡単なテスト取得
                test_data = feature_engineer.forex_fetcher.get_macro_data()
                if (
                    test_data
                    and "usdjpy" in test_data
                    and not test_data["usdjpy"].empty
                ):
                    logger.info(
                        f"✅ USD/JPY為替データ取得成功: {len(test_data['usdjpy'])} レコード"
                    )

                    # 為替特徴量計算テスト
                    forex_features = (
                        feature_engineer.forex_fetcher.calculate_macro_features(
                            test_data
                        )
                    )
                    if not forex_features.empty:
                        forex_cols = [
                            col for col in forex_features.columns if "usdjpy" in col
                        ]
                        logger.info(
                            f"✅ USD/JPY為替特徴量計算成功: {len(forex_cols)} 特徴量"
                        )
                        logger.info(f"💱 為替特徴量: {forex_cols}")
                    else:
                        logger.warning("⚠️ 為替特徴量計算結果が空")
                else:
                    logger.warning("⚠️ USD/JPY為替データ取得失敗")

            except Exception as e:
                logger.error(f"❌ 為替データ取得テスト失敗: {e}")

        # 7. 特徴量生成テスト
        logger.info("🔍 特徴量生成テスト中...")

        # ダミーデータ作成
        dummy_data = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [102, 103, 104],
                "volume": [1000, 1100, 1200],
            },
            index=pd.date_range("2025-01-01", periods=3, freq="1h", tz="UTC"),
        )

        try:
            features = feature_engineer.transform(dummy_data)
            logger.info(f"✅ 特徴量生成成功: {features.shape}")

            # 為替・マクロ特徴量存在確認
            forex_feature_cols = [col for col in features.columns if "usdjpy" in col]
            macro_feature_cols = [
                col
                for col in features.columns
                if any(
                    prefix in col
                    for prefix in ["dxy_", "treasury_", "yield_curve", "risk_sentiment"]
                )
            ]

            logger.info(f"💱 生成された為替特徴量: {len(forex_feature_cols)} 個")
            logger.info(f"💱 生成されたマクロ特徴量: {len(macro_feature_cols)} 個")

            if forex_feature_cols:
                logger.info(f"💱 為替特徴量リスト: {forex_feature_cols}")
            if macro_feature_cols:
                logger.info(f"💱 マクロ特徴量リスト: {macro_feature_cols}")

            # 全特徴量の確認
            all_feature_cols = list(features.columns)
            logger.info(f"📊 全特徴量数: {len(all_feature_cols)}")

            # 外部データ関連特徴量の確認
            external_cols = [
                col
                for col in all_feature_cols
                if any(
                    prefix in col
                    for prefix in [
                        "vix",
                        "dxy",
                        "treasury",
                        "fear_greed",
                        "usdjpy",
                        "yield",
                        "risk",
                    ]
                )
            ]
            logger.info(f"🌐 外部データ特徴量: {len(external_cols)} 個")
            if external_cols:
                logger.info(f"🌐 外部データ特徴量リスト: {external_cols}")

        except Exception as e:
            logger.error(f"❌ 特徴量生成テスト失敗: {e}")

        # 8. 結果サマリー
        logger.info("=" * 60)
        logger.info("📊 USD/JPY為替特徴量設定テスト結果")
        logger.info("=" * 60)
        logger.info(f"✅ 設定ファイル: {config_path}")
        logger.info(f"✅ 為替特徴量有効化: {'✅' if forex_enabled else '❌'}")
        logger.info(
            f"✅ Preprocessor初期化: {'✅' if feature_engineer.forex_enabled else '❌'}"
        )
        logger.info(f"✅ 為替データ取得: テスト実行済み")
        logger.info(f"✅ 特徴量生成: テスト実行済み")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ 設定テスト失敗: {e}")
        return False


if __name__ == "__main__":
    test_forex_config()
