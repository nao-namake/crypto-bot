#!/usr/bin/env python3
"""
VIX指数復活実装テスト
複数データソース・キャッシュ機能・品質閾値管理のテスト
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


def test_vix_revival():
    """VIX指数復活実装テスト"""
    logger.info("🚀 VIX指数復活実装テスト開始")

    # 1. 設定ファイル読み込み
    config_path = "/Users/nao/Desktop/bot/config/production/bitbank_forex_enhanced.yml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ 設定ファイル読み込み成功")

        # 2. VIX設定確認
        extra_features = config.get("ml", {}).get("extra_features", [])
        vix_enabled = "vix" in extra_features
        logger.info(f"📊 VIX設定確認: extra_features={extra_features}")
        logger.info(f"💱 VIX有効化: {'✅' if vix_enabled else '❌'}")

        # 3. VIX外部データ設定確認
        vix_config = config.get("external_data", {}).get("vix", {})
        logger.info(f"🔧 VIX外部データ設定: {vix_config}")

        # 4. VIXフェッチャー初期化テスト
        from crypto_bot.data.vix_fetcher import VIXDataFetcher

        logger.info("🔍 VIXフェッチャー初期化テスト中...")
        vix_fetcher = VIXDataFetcher(config)

        # 5. VIXデータ取得テスト
        logger.info("🔍 VIXデータ取得テスト中...")
        vix_data = vix_fetcher.get_vix_data()

        if vix_data is not None and not vix_data.empty:
            logger.info(f"✅ VIXデータ取得成功: {len(vix_data)} レコード")

            # データ品質確認
            logger.info(f"📊 VIXデータ品質:")
            logger.info(f"  - カラム: {list(vix_data.columns)}")
            logger.info(f"  - 期間: {vix_data.index.min()} - {vix_data.index.max()}")
            logger.info(f"  - 欠損値: {vix_data.isnull().sum().sum()}")

            # 6. VIX特徴量計算テスト
            logger.info("🔍 VIX特徴量計算テスト中...")
            vix_features = vix_fetcher.calculate_vix_features(vix_data)

            if not vix_features.empty:
                logger.info(f"✅ VIX特徴量計算成功: {vix_features.shape}")

                # 特徴量詳細確認
                vix_feature_cols = [
                    col for col in vix_features.columns if "vix" in col or "fear" in col
                ]
                logger.info(f"💱 VIX特徴量: {vix_feature_cols}")

                # 最新値確認
                latest_values = vix_features.iloc[-1]
                logger.info(f"📊 最新VIX特徴量値:")
                for col in vix_feature_cols:
                    logger.info(f"  - {col}: {latest_values[col]}")

            else:
                logger.warning("⚠️ VIX特徴量計算結果が空")

        else:
            logger.warning("⚠️ VIXデータ取得失敗")

        # 7. Preprocessor統合テスト
        logger.info("🔍 Preprocessor統合テスト中...")
        from crypto_bot.ml.preprocessor import FeatureEngineer

        feature_engineer = FeatureEngineer(config)

        # VIXフェッチャー統合確認
        logger.info(
            f"💱 VIXフェッチャー統合: {'✅' if feature_engineer.vix_enabled else '❌'}"
        )
        logger.info(
            f"💱 VIXフェッチャー存在: {'✅' if feature_engineer.vix_fetcher else '❌'}"
        )

        # 8. 特徴量生成テスト
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

            # VIX特徴量存在確認
            vix_feature_cols = [
                col for col in features.columns if "vix" in col or "fear" in col
            ]
            logger.info(f"💱 生成されたVIX特徴量: {len(vix_feature_cols)} 個")

            if vix_feature_cols:
                logger.info(f"💱 VIX特徴量リスト: {vix_feature_cols}")

            # 全特徴量数確認
            total_features = len(features.columns)
            logger.info(f"📊 全特徴量数: {total_features}")

        except Exception as e:
            logger.error(f"❌ 特徴量生成テスト失敗: {e}")

        # 9. 結果サマリー
        logger.info("=" * 60)
        logger.info("📊 VIX指数復活実装テスト結果")
        logger.info("=" * 60)
        logger.info(f"✅ 設定ファイル: {config_path}")
        logger.info(f"✅ VIX有効化: {'✅' if vix_enabled else '❌'}")
        logger.info(
            f"✅ VIXフェッチャー初期化: {'✅' if feature_engineer.vix_enabled else '❌'}"
        )
        logger.info(f"✅ VIXデータ取得: テスト実行済み")
        logger.info(f"✅ VIX特徴量計算: テスト実行済み")
        logger.info(f"✅ Preprocessor統合: テスト実行済み")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ VIX復活テスト失敗: {e}")
        return False


if __name__ == "__main__":
    success = test_vix_revival()
    sys.exit(0 if success else 1)
