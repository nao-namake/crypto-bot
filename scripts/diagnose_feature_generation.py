#!/usr/bin/env python3
"""
Phase 3: 特徴量生成診断スクリプト
実際に生成される特徴量と期待される特徴量の差異を特定する
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def diagnose_feature_generation():
    """特徴量生成を診断"""
    # 設定ファイル読み込み
    config_path = str(project_root / "config/production/production.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # モデルメタデータ読み込み
    metadata_path = project_root / "models/production/model_metadata.yaml"
    with open(metadata_path, "r") as f:
        metadata = yaml.safe_load(f)

    model_features = metadata["feature_names"]
    expected_count = metadata["features_count"]

    logger.info(f"📊 モデル期待特徴量数: {expected_count}")
    logger.info(f"📊 モデル特徴量リスト: {len(model_features)}個")

    # データ取得（簡易版）
    fetcher = MarketDataFetcher(
        exchange_id="bitbank",
        symbol="BTC/JPY",
        api_key=config.get("data", {}).get("api_key"),
        api_secret=config.get("data", {}).get("api_secret"),
        testnet=False,
    )

    # 小規模データで実験
    from datetime import datetime, timedelta

    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    df = fetcher.get_price_df(
        timeframe="1h", since=int(start_time.timestamp() * 1000), limit=24
    )
    logger.info(f"📊 テストデータ: {len(df)}レコード")

    # 特徴量生成
    feature_engineer = FeatureEngineer(config)
    features_df = feature_engineer.transform(df)

    generated_features = list(features_df.columns)
    logger.info(f"📊 生成された特徴量数: {len(generated_features)}")

    # 差異分析
    print("\n" + "=" * 60)
    print("🔍 特徴量生成診断結果")
    print("=" * 60)

    # 欠落特徴量
    missing_features = set(model_features) - set(generated_features)
    if missing_features:
        print(f"\n❌ 欠落特徴量 ({len(missing_features)}個):")
        for feat in sorted(missing_features):
            print(f"  - {feat}")
            # 特に重要な3つをハイライト
            if feat in ["close_mean_10", "close_std_10", "rsi_21"]:
                print(f"    ⚠️ 重要: この特徴量がモデル予測エラーの原因です")

    # 追加特徴量
    extra_features = set(generated_features) - set(model_features)
    if extra_features:
        print(f"\n⚠️ 追加特徴量 ({len(extra_features)}個):")
        for feat in sorted(extra_features)[:10]:  # 最初の10個のみ表示
            print(f"  - {feat}")
        if len(extra_features) > 10:
            print(f"  ... 他{len(extra_features)-10}個")

    # 類似特徴量の検索
    print("\n🔍 類似特徴量の検索:")
    for missing_feat in ["close_mean_10", "close_std_10", "rsi_21"]:
        if missing_feat in missing_features:
            # 類似の特徴量を探す
            similar = [f for f in generated_features if missing_feat.split("_")[0] in f]
            if similar:
                print(f"\n  {missing_feat} の類似特徴量:")
                for s in similar[:5]:
                    print(f"    - {s}")

    # rolling_window設定の確認
    rolling_window = config["ml"].get("rolling_window", 14)
    print(f"\n📊 rolling_window設定: {rolling_window}")
    print(
        f"  → close_mean_{rolling_window}, close_std_{rolling_window} が生成されているはず"
    )

    # RSI設定の確認
    rsi_features = [f for f in generated_features if f.startswith("rsi_")]
    print(f"\n📊 生成されたRSI特徴量:")
    for rsi in sorted(rsi_features):
        print(f"  - {rsi}")

    # FeatureOrderManagerの確認
    feature_order_manager = FeatureOrderManager()
    try:
        ordered_features = feature_order_manager.ensure_column_order(features_df)
        print(f"\n📊 FeatureOrderManager後の特徴量数: {len(ordered_features.columns)}")
    except Exception as e:
        print(f"\n❌ FeatureOrderManager エラー: {e}")

    # 解決策の提案
    print("\n" + "=" * 60)
    print("🔧 推奨される解決策:")
    print("=" * 60)

    if "close_mean_10" in missing_features or "close_std_10" in missing_features:
        print("\n1. rolling統計の修正:")
        print("   - technical_engine.pyのcalculate_lag_rolling_batch()を修正")
        print("   - 固定で10期間のrolling統計を追加")

    if "rsi_21" in missing_features:
        print("\n2. RSI_21の追加:")
        print("   - RSI期間リストに21を確実に含める")
        print("   - _parse_technical_features()でrsi_21が正しく解析されるか確認")

    print("\n3. 特徴量順序の統一:")
    print("   - FeatureOrderManagerを更新して127特徴量に対応")
    print("   - feature_order.jsonを再生成")

    return missing_features, extra_features


if __name__ == "__main__":
    try:
        missing, extra = diagnose_feature_generation()

        # 重要な欠落特徴量があるか確認
        critical_missing = {"close_mean_10", "close_std_10", "rsi_21"} & missing
        if critical_missing:
            logger.error(f"❌ 重要な欠落特徴量: {critical_missing}")
            exit(1)
        else:
            logger.info("✅ 重要な特徴量は全て生成されています")

    except Exception as e:
        logger.error(f"❌ 診断失敗: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
