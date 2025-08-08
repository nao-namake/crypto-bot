#!/usr/bin/env python3
"""
実データ特徴量生成時のenhanced_default汚染詳細診断

目的:
- 実際のBTC/JPYデータで特徴量生成時の汚染状況確認
- バックテスト時と同じ条件での問題再現
- 根本原因の特定
"""

import logging
import os
import sys

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.append("/Users/nao/Desktop/bot")

import yaml

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.feature_engines.batch_calculator import BatchFeatureCalculator
from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_real_data():
    """実際のBTC/JPYデータ読み込み"""
    csv_path = "data/btc_usd_2024_hourly.csv"

    if os.path.exists(csv_path):
        logger.info(f"📊 CSVファイル読み込み: {csv_path}")
        df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

        # 最新100件に制限（診断用）
        df = df.tail(100)
        logger.info(f"✅ 実データ読み込み: {len(df)}件")
        return df
    else:
        logger.error(f"❌ CSVファイル未発見: {csv_path}")
        return None


def diagnose_feature_generation():
    """実データでの特徴量生成診断"""
    logger.info("🔍 実データ特徴量生成診断開始")

    # 設定読み込み
    config_path = "/Users/nao/Desktop/bot/config/production/production.yml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 実データ読み込み
    raw_data = load_real_data()
    if raw_data is None:
        return False

    try:
        # バッチ計算機・テクニカルエンジン初期化
        batch_calc = BatchFeatureCalculator(config)
        tech_engine = TechnicalFeatureEngine(config, batch_calc)

        logger.info("🔧 特徴量生成開始（実データ）")

        # 全テクニカル特徴量バッチ計算
        feature_batches = tech_engine.calculate_all_technical_batches(raw_data)

        # 特徴量統合
        feature_df = raw_data.copy()
        total_features = 0
        enhanced_default_count = 0
        missing_features = []

        for batch in feature_batches:
            if len(batch) > 0:
                batch_features = batch.to_dataframe()

                # enhanced_default汚染チェック
                for col in batch_features.columns:
                    if "enhanced_default" in str(col):
                        enhanced_default_count += 1
                        logger.error(f"❌ enhanced_default汚染検出: {col}")

                    # 特徴量の実際の値をサンプル確認
                    sample_values = batch_features[col].dropna().head(3)
                    if any("enhanced_default" in str(val) for val in sample_values):
                        logger.error(
                            f"❌ 値レベルでenhanced_default汚染: {col} = {sample_values.tolist()}"
                        )

                # 重複列を除去
                overlapping_cols = batch_features.columns.intersection(
                    feature_df.columns
                )
                if len(overlapping_cols) > 0:
                    batch_features = batch_features.drop(columns=overlapping_cols)

                # 特徴量統合
                if not batch_features.empty:
                    feature_df = feature_df.join(batch_features, how="left")
                    total_features += len(batch_features.columns)
                    logger.info(
                        f"   ✅ {batch.name}: {len(batch_features.columns)}特徴量追加"
                    )

        # 期待される重要特徴量の存在確認
        expected_features = [
            "hour",
            "day_of_week",
            "rsi_14",
            "rsi_21",
            "macd",
            "sma_20",
        ]
        for feature in expected_features:
            if feature not in feature_df.columns:
                missing_features.append(feature)
                logger.error(f"❌ 重要特徴量欠損: {feature}")
            else:
                sample_vals = feature_df[feature].dropna().head(3)
                logger.info(f"✅ {feature}: {sample_vals.tolist()}")

        # 最終結果
        logger.info("📊 診断結果:")
        logger.info(f"   総特徴量数: {total_features}")
        logger.info(f"   enhanced_default汚染: {enhanced_default_count}個")
        logger.info(f"   重要特徴量欠損: {len(missing_features)}個")

        if enhanced_default_count > 0:
            logger.error("❌ enhanced_default汚染が残存！")

            # 汚染列の詳細確認
            contaminated_cols = [
                col for col in feature_df.columns if "enhanced_default" in str(col)
            ]
            logger.error(f"汚染列: {contaminated_cols}")

        if missing_features:
            logger.error(f"❌ 重要特徴量欠損: {missing_features}")

        # 125特徴量システム整合性確認
        ml_extra_features = config.get("ml", {}).get("extra_features", [])
        expected_count = len(ml_extra_features) + 5  # OHLCV
        actual_count = len(feature_df.columns)

        logger.info(f"📊 125特徴量システム整合性:")
        logger.info(f"   期待: {expected_count}特徴量")
        logger.info(f"   実際: {actual_count}特徴量")

        if actual_count != expected_count:
            logger.warning(f"⚠️ 特徴量数不一致: {actual_count} != {expected_count}")

        # 特徴量一覧保存
        feature_list_path = "/Users/nao/Desktop/bot/results/real_data_features_list.txt"
        with open(feature_list_path, "w") as f:
            f.write("実データ特徴量生成結果:\n")
            f.write(f"総数: {len(feature_df.columns)}\n\n")
            for i, col in enumerate(feature_df.columns):
                sample_val = (
                    feature_df[col].dropna().iloc[0]
                    if not feature_df[col].dropna().empty
                    else "NaN"
                )
                f.write(f"{i+1:3d}. {col}: {sample_val}\n")

        logger.info(f"✅ 特徴量一覧保存: {feature_list_path}")

        return enhanced_default_count == 0 and len(missing_features) == 0

    except Exception as e:
        logger.error(f"❌ 診断失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メイン実行"""
    logger.info("=" * 60)
    logger.info("実データ特徴量生成・enhanced_default汚染診断")
    logger.info("=" * 60)

    success = diagnose_feature_generation()

    if success:
        print("\n✅ 診断完了: enhanced_default汚染なし・重要特徴量完全")
        print("🚀 特徴量生成システム正常・モデル再学習準備完了")
    else:
        print("\n❌ 診断失敗: enhanced_default汚染または重要特徴量欠損")
        print("🔧 technical_engine.py追加修正が必要")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
