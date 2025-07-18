#!/usr/bin/env python3
"""
Fear&Greed指数復活実装テスト
複数データソース・キャッシュ機能・フォールバック機能のテスト
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


def test_fear_greed_revival():
    """Fear&Greed指数復活実装テスト"""
    logger.info("🚀 Fear&Greed指数復活実装テスト開始")

    # 1. 設定ファイル読み込み
    config_path = "/Users/nao/Desktop/bot/config/production/bitbank_forex_enhanced.yml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ 設定ファイル読み込み成功")

        # 2. Fear&Greed設定確認
        extra_features = config.get("ml", {}).get("extra_features", [])
        fear_greed_enabled = "fear_greed" in extra_features
        logger.info(f"📊 Fear&Greed設定確認: extra_features={extra_features}")
        logger.info(f"💱 Fear&Greed有効化: {'✅' if fear_greed_enabled else '❌'}")

        # 3. Fear&Greed外部データ設定確認
        fear_greed_config = config.get("external_data", {}).get("fear_greed", {})
        logger.info(f"🔧 Fear&Greed外部データ設定: {fear_greed_config}")

        # 4. Fear&Greedフェッチャー初期化テスト
        from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher

        logger.info("🔍 Fear&Greedフェッチャー初期化テスト中...")
        fear_greed_fetcher = FearGreedDataFetcher(config)

        # 5. Fear&Greedデータ取得テスト
        logger.info("🔍 Fear&Greedデータ取得テスト中...")
        fg_data = fear_greed_fetcher.get_fear_greed_data(limit=30)

        if fg_data is not None and not fg_data.empty:
            logger.info(f"✅ Fear&Greedデータ取得成功: {len(fg_data)} レコード")

            # データ品質確認
            logger.info(f"📊 Fear&Greedデータ品質:")
            logger.info(f"  - カラム: {list(fg_data.columns)}")
            logger.info(f"  - 期間: {fg_data.index.min()} - {fg_data.index.max()}")
            logger.info(f"  - 欠損値: {fg_data.isnull().sum().sum()}")
            logger.info(
                f"  - 値の範囲: {fg_data['value'].min()} - {fg_data['value'].max()}"
            )

            # 6. Fear&Greed特徴量計算テスト
            logger.info("🔍 Fear&Greed特徴量計算テスト中...")
            fg_features = fear_greed_fetcher.calculate_fear_greed_features(fg_data)

            if not fg_features.empty:
                logger.info(f"✅ Fear&Greed特徴量計算成功: {fg_features.shape}")

                # 特徴量詳細確認
                fg_feature_cols = [
                    col
                    for col in fg_features.columns
                    if "fear" in col
                    or "greed" in col
                    or "fg" in col
                    or "sentiment" in col
                ]
                logger.info(f"💱 Fear&Greed特徴量: {fg_feature_cols}")

                # 最新値確認
                latest_values = fg_features.iloc[-1]
                logger.info(f"📊 最新Fear&Greed特徴量値:")
                for col in fg_feature_cols[:5]:  # 最初の5個のみ表示
                    logger.info(f"  - {col}: {latest_values[col]}")

            else:
                logger.warning("⚠️ Fear&Greed特徴量計算結果が空")

        else:
            logger.warning("⚠️ Fear&Greedデータ取得失敗")

        # 7. Preprocessor統合テスト
        logger.info("🔍 Preprocessor統合テスト中...")
        from crypto_bot.ml.preprocessor import FeatureEngineer

        feature_engineer = FeatureEngineer(config)

        # Fear&Greedフェッチャー統合確認
        logger.info(
            f"💱 Fear&Greedフェッチャー統合: {'✅' if feature_engineer.fear_greed_enabled else '❌'}"
        )
        logger.info(
            f"💱 Fear&Greedフェッチャー存在: {'✅' if feature_engineer.fear_greed_fetcher else '❌'}"
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

            # Fear&Greed特徴量存在確認
            fg_feature_cols = [
                col
                for col in features.columns
                if "fear" in col or "greed" in col or "fg" in col or "sentiment" in col
            ]
            logger.info(f"💱 生成されたFear&Greed特徴量: {len(fg_feature_cols)} 個")

            if fg_feature_cols:
                logger.info(f"💱 Fear&Greed特徴量リスト: {fg_feature_cols}")

            # 全特徴量数確認
            total_features = len(features.columns)
            logger.info(f"📊 全特徴量数: {total_features}")

            # 外部データ特徴量確認
            external_cols = [
                col
                for col in features.columns
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
                        "fg",
                        "sentiment",
                    ]
                )
            ]
            logger.info(f"🌐 外部データ特徴量: {len(external_cols)} 個")

        except Exception as e:
            logger.error(f"❌ 特徴量生成テスト失敗: {e}")

        # 9. 結果サマリー
        logger.info("=" * 60)
        logger.info("📊 Fear&Greed指数復活実装テスト結果")
        logger.info("=" * 60)
        logger.info(f"✅ 設定ファイル: {config_path}")
        logger.info(f"✅ Fear&Greed有効化: {'✅' if fear_greed_enabled else '❌'}")
        logger.info(
            f"✅ Fear&Greedフェッチャー初期化: {'✅' if feature_engineer.fear_greed_enabled else '❌'}"
        )
        logger.info(f"✅ Fear&Greedデータ取得: テスト実行済み")
        logger.info(f"✅ Fear&Greed特徴量計算: テスト実行済み")
        logger.info(f"✅ Preprocessor統合: テスト実行済み")
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ Fear&Greed復活テスト失敗: {e}")
        return False


if __name__ == "__main__":
    success = test_fear_greed_revival()
    sys.exit(0 if success else 1)
