#!/usr/bin/env python3
"""
特徴量数統一分析スクリプト
現在のシステムの特徴量数を正確に把握し、統一化方針を決定
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import joblib
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def analyze_current_system_features():
    """現在のシステムの特徴量数を正確に分析"""

    print("🔍 現在のシステム特徴量数分析開始")
    print("=" * 60)

    # 1. 設定ファイルから期待特徴量数確認
    config_path = str(project_root / "config/production/production.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # extra_features数確認
    extra_features = config.get("ml", {}).get("extra_features", [])
    base_features_count = 5  # OHLCV
    expected_total = base_features_count + len(extra_features)

    print(f"📊 設定ファイル分析:")
    print(f"   - base_features: {base_features_count}")
    print(f"   - extra_features: {len(extra_features)}")
    print(f"   - 期待合計: {expected_total}")

    # 2. 実際のFeatureEngineerでテスト生成
    print(f"\n🔧 実際の特徴量生成テスト:")

    # テストデータ作成（十分なサイズ）
    test_data_rows = 100
    test_data = {
        "open": [10000.0 + i * 10 for i in range(test_data_rows)],
        "high": [10100.0 + i * 10 for i in range(test_data_rows)],
        "low": [9900.0 + i * 10 for i in range(test_data_rows)],
        "close": [10050.0 + i * 10 for i in range(test_data_rows)],
        "volume": [1000.0 + i * 5 for i in range(test_data_rows)],
    }

    df = pd.DataFrame(test_data)
    df.index = pd.date_range("2025-01-01", periods=test_data_rows, freq="H")

    # 特徴量生成
    feature_engineer = FeatureEngineer(config)
    features_df = feature_engineer.transform(df)

    actual_features = len(features_df.columns)
    feature_names = list(features_df.columns)

    print(f"   - 実際生成数: {actual_features}")
    print(f"   - 特徴量リスト: {feature_names[:10]}... (最初の10個)")

    # 3. 保存済みモデルのメタデータ確認
    print(f"\n📋 保存済みモデルメタデータ分析:")

    metadata_path = project_root / "models/production/model_metadata.yaml"
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            metadata = yaml.safe_load(f)

        model_features = metadata.get("features_count", "Unknown")
        model_phase = metadata.get("phase", "Unknown")
        model_feature_names = metadata.get("feature_names", [])

        print(f"   - モデル特徴量数: {model_features}")
        print(f"   - モデルフェーズ: {model_phase}")
        print(f"   - モデル特徴量数: {len(model_feature_names)}")
    else:
        print("   - メタデータファイル未発見")

    # 4. feature_order.json確認
    print(f"\n📁 feature_order.json分析:")

    feature_order_path = project_root / "config/core/feature_order.json"
    if feature_order_path.exists():
        import json

        with open(feature_order_path, "r") as f:
            feature_order = json.load(f)

        ordered_features = len(feature_order.get("feature_order", []))
        print(f"   - feature_order数: {ordered_features}")
    else:
        print("   - feature_order.json未発見")

    # 5. 実際にモデルロードしてテスト
    print(f"\n🤖 実際のモデルテスト:")

    model_path = project_root / "models/production/model.pkl"
    if model_path.exists():
        try:
            model = joblib.load(model_path)

            # モデルで予測テスト
            X_test = features_df.iloc[:50]  # 50行でテスト
            predictions = model.predict_proba(X_test)

            print(f"   - モデルロード: 成功")
            print(f"   - テスト予測: 成功 ({len(predictions)}行予測)")
            print(f"   - 入力特徴量数: {X_test.shape[1]}")

        except Exception as e:
            print(f"   - モデルテストエラー: {e}")
    else:
        print("   - モデルファイル未発見")

    # 6. 統一化方針の提案
    print(f"\n" + "=" * 60)
    print("📊 特徴量数統一分析結果")
    print("=" * 60)

    if metadata_path.exists():
        print(f"🎯 現在の状況:")
        print(f"   - 設定ファイル期待値: {expected_total}")
        print(f"   - 実際生成数: {actual_features}")
        print(f"   - 保存モデル期待数: {model_features}")

        if actual_features == model_features:
            print(f"✅ 推奨統一特徴量数: {actual_features}")
            print(f"   理由: 現在のシステムとモデルが一致")
            return actual_features
        else:
            print(f"⚠️ 不一致検出:")
            print(f"   - システム生成: {actual_features}")
            print(f"   - モデル期待: {model_features}")

            # より大きい方を推奨（安全側）
            recommended = max(actual_features, model_features)
            print(f"✅ 推奨統一特徴量数: {recommended}")
            print(f"   理由: 不一致解消のため大きい方を採用")
            return recommended
    else:
        print(f"✅ 推奨統一特徴量数: {actual_features}")
        print(f"   理由: 現在のシステム生成数を基準")
        return actual_features


def create_feature_unification_plan(target_feature_count: int):
    """特徴量統一化計画作成"""

    print(f"\n" + "=" * 60)
    print(f"🎯 特徴量統一化計画: {target_feature_count}特徴量")
    print("=" * 60)

    plan = {
        "target_feature_count": target_feature_count,
        "files_to_update": [
            "models/production/model_metadata.yaml",
            "config/core/feature_order.json",
            "models/production/model.pkl",
            "tests/unit/test_*.py (期待値更新)",
            "crypto_bot/ml/feature_order_manager.py",
            "scripts/diagnose_prediction_bias.py",
        ],
        "actions": [
            f"1. {target_feature_count}特徴量でのモデル再学習",
            f"2. feature_order.json {target_feature_count}特徴量に更新",
            f"3. model_metadata.yaml特徴量数統一",
            f"4. 全テストファイルの期待値統一",
            f"5. 診断スクリプトの期待値統一",
        ],
    }

    for i, action in enumerate(plan["actions"], 1):
        print(f"   {action}")

    print(f"\n📁 更新対象ファイル:")
    for file in plan["files_to_update"]:
        print(f"   - {file}")

    return plan


if __name__ == "__main__":
    try:
        # 現在のシステム分析
        recommended_features = analyze_current_system_features()

        # 統一化計画作成
        plan = create_feature_unification_plan(recommended_features)

        print(f"\n" + "=" * 60)
        print("✅ 特徴量数統一分析完了")
        print("=" * 60)
        print(f"🎯 統一目標: {recommended_features}特徴量")
        print("🚀 次のステップ: 統一化実行スクリプト作成")
        print("=" * 60)

    except Exception as e:
        logger.error(f"❌ 分析エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
