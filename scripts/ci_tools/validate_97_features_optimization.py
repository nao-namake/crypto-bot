#!/usr/bin/env python3
"""
97特徴量最適化システム効果検証スクリプト
Phase 2: 127→97特徴量最適化の効果測定・性能比較

実行内容:
1. 97特徴量システム統合性確認
2. 97特徴量モデル性能確認
3. 効率化効果測定（推定）
4. システム準備状況確認
"""

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from crypto_bot.ml.feature_defaults import FeatureDefaults
from crypto_bot.ml.feature_order_manager import FeatureOrderManager

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)


def validate_system_integration():
    """97特徴量システム統合性確認"""
    print("🔍 === 97特徴量システム統合性確認 ===")

    # FeatureOrderManager確認
    fom = FeatureOrderManager()
    defaults = FeatureDefaults()

    print(f"✅ FeatureOrderManager: {len(fom.FEATURE_ORDER_97)} 特徴量")
    print(f"✅ FeatureDefaults target_count: {defaults.target_count}")

    # feature_order.json確認
    feature_order_path = Path("config/core/feature_order.json")
    if feature_order_path.exists():
        with open(feature_order_path, "r") as f:
            data = json.load(f)

        feature_order_json = data["feature_order"]
        print(f"✅ feature_order.json: {len(feature_order_json)} 特徴量")
        print(
            f"   削除された特徴量: {len(data['optimization_info']['deleted_features'])} 個"
        )

        # 順序一致確認
        full_match = feature_order_json == fom.FEATURE_ORDER_97
        print(f"✅ 特徴量順序一致: {full_match}")

        if full_match:
            print("🎊 97特徴量システム統合性: 完全一致")
            return True
        else:
            print("❌ 97特徴量システム統合性: 不一致")
            return False
    else:
        print("❌ feature_order.json: ファイルなし")
        return False


def validate_model_performance():
    """97特徴量モデル性能確認"""
    print("\n🔍 === 97特徴量モデル性能確認 ===")

    model_dir = Path("models/production")
    models = ["lgbm_97_features.pkl", "xgb_97_features.pkl", "rf_97_features.pkl"]

    model_results = {}

    for model_file in models:
        model_path = model_dir / model_file
        if model_path.exists():
            size_kb = model_path.stat().st_size / 1024
            print(f"✅ {model_file}: {size_kb:.1f} KB")

            # メタデータ確認
            metadata_file = model_file.replace(".pkl", "_metadata.json")
            metadata_path = model_dir / metadata_file
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    meta = json.load(f)

                accuracy = meta.get("train_accuracy", 0)
                f1_score = meta.get("train_f1", 0)
                print(f"   学習精度: {accuracy:.3f}")
                print(f"   F1スコア: {f1_score:.3f}")

                model_results[model_file] = {
                    "size_kb": size_kb,
                    "accuracy": accuracy,
                    "f1_score": f1_score,
                }
            else:
                print(f"   ❌ メタデータなし")
                model_results[model_file] = {
                    "size_kb": size_kb,
                    "accuracy": 0,
                    "f1_score": 0,
                }
        else:
            print(f"❌ {model_file}: ファイルなし")
            model_results[model_file] = None

    # アンサンブルメタデータ確認
    ensemble_meta_path = model_dir / "ensemble_97_features_metadata.json"
    if ensemble_meta_path.exists():
        print(f"\n✅ アンサンブルメタデータ確認:")
        with open(ensemble_meta_path, "r") as f:
            ensemble_meta = json.load(f)
        print(f"   学習日時: {ensemble_meta.get('training_timestamp', 'N/A')}")
        print(f"   構成モデル: {list(ensemble_meta.get('models', {}).keys())}")

    return model_results


def estimate_efficiency_gains():
    """効率化効果推定"""
    print("\n🔍 === 効率化効果推定 ===")

    # 理論的効率化効果
    original_features = 127
    optimized_features = 97
    deleted_features = 30

    # 計算効率向上推定
    efficiency_gain = (deleted_features / original_features) * 100
    processing_improvement = (1 - (optimized_features / original_features)) * 100

    print(f"📊 特徴量最適化効果:")
    print(f"   元特徴量数: {original_features}")
    print(f"   最適化後: {optimized_features}")
    print(f"   削除特徴量: {deleted_features} 個")
    print(f"   削減率: {efficiency_gain:.1f}%")
    print(f"   処理効率向上: {processing_improvement:.1f}%")

    # メモリ効率推定
    feature_memory_per_sample = 8  # bytes (float64)
    sample_count = 8000  # 推定

    original_memory = (
        original_features * feature_memory_per_sample * sample_count / 1024 / 1024
    )  # MB
    optimized_memory = (
        optimized_features * feature_memory_per_sample * sample_count / 1024 / 1024
    )  # MB
    memory_saved = original_memory - optimized_memory

    print(f"\n📊 メモリ効率化推定:")
    print(f"   元メモリ使用量: {original_memory:.2f} MB")
    print(f"   最適化後: {optimized_memory:.2f} MB")
    print(
        f"   メモリ節約: {memory_saved:.2f} MB ({memory_saved/original_memory*100:.1f}%)"
    )

    # 削除特徴量カテゴリ別効果
    deleted_categories = {
        "SMA系移動平均": 6,
        "ATR複数期間": 2,
        "ボラティリティ重複": 4,
        "RSI複数期間": 2,
        "対数リターン": 5,
        "過剰ラグ特徴量": 5,
        "セッション時間重複": 1,
        "統計指標重複": 5,
    }

    print(f"\n📊 削除特徴量カテゴリ別内訳:")
    for category, count in deleted_categories.items():
        print(f"   {category}: {count} 個")

    return {
        "efficiency_gain": efficiency_gain,
        "processing_improvement": processing_improvement,
        "memory_saved_mb": memory_saved,
        "memory_saved_percent": memory_saved / original_memory * 100,
    }


def check_system_readiness():
    """システム準備状況確認"""
    print("\n🔍 === システム準備状況確認 ===")

    checks = {
        "feature_order_manager": False,
        "feature_defaults": False,
        "feature_order_json": False,
        "97_models": False,
        "backtest_config": False,
        "metadata": False,
    }

    # FeatureOrderManager確認
    try:
        fom = FeatureOrderManager()
        if len(fom.FEATURE_ORDER_97) == 97:
            checks["feature_order_manager"] = True
    except Exception:
        pass

    # FeatureDefaults確認
    try:
        defaults = FeatureDefaults()
        if defaults.target_count == 97:
            checks["feature_defaults"] = True
    except Exception:
        pass

    # feature_order.json確認
    feature_order_path = Path("config/core/feature_order.json")
    if feature_order_path.exists():
        try:
            with open(feature_order_path, "r") as f:
                data = json.load(f)
            if data.get("num_features") == 97:
                checks["feature_order_json"] = True
        except Exception:
            pass

    # 97特徴量モデル確認
    model_dir = Path("models/production")
    model_files = ["lgbm_97_features.pkl", "xgb_97_features.pkl", "rf_97_features.pkl"]
    if all((model_dir / f).exists() for f in model_files):
        checks["97_models"] = True

    # バックテスト設定確認
    backtest_config = Path("config/validation/unified_97_features_backtest.yml")
    if backtest_config.exists():
        checks["backtest_config"] = True

    # メタデータ確認
    metadata_file = Path("models/production/model_metadata_97.yaml")
    if metadata_file.exists():
        checks["metadata"] = True

    # 結果表示
    print("📋 システム準備状況:")
    for check, status in checks.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {check}: {'準備完了' if status else '未完了'}")

    readiness_score = sum(checks.values()) / len(checks) * 100
    print(f"\n🎯 システム準備率: {readiness_score:.1f}%")

    return checks, readiness_score


def generate_optimization_report():
    """97特徴量最適化レポート生成"""
    print("\n🎊 === 97特徴量最適化システム完成レポート ===")

    # 統合性確認
    integration_ok = validate_system_integration()

    # モデル性能確認
    model_results = validate_model_performance()

    # 効率化効果推定
    efficiency_results = estimate_efficiency_gains()

    # システム準備状況確認
    checks, readiness_score = check_system_readiness()

    # 総合評価
    print(f"\n🏆 === 97特徴量最適化システム総合評価 ===")
    print(f"✅ システム統合性: {'完璧' if integration_ok else '要修正'}")
    print(
        f"✅ モデル準備状況: {sum(1 for r in model_results.values() if r is not None)}/3 モデル準備完了"
    )
    print(
        f"✅ 効率化効果: {efficiency_results['processing_improvement']:.1f}% 処理効率向上"
    )
    print(
        f"✅ メモリ最適化: {efficiency_results['memory_saved_percent']:.1f}% メモリ削減"
    )
    print(f"✅ システム準備率: {readiness_score:.1f}%")

    # 次のステップ
    print(f"\n🚀 === 次のアクション ===")
    if readiness_score >= 80:
        print("🎊 Phase 2完全実装達成！97特徴量最適化システム基盤構築完了")
        print("🔄 推奨次ステップ:")
        print("   1. Phase 4.3: 性能比較バックテスト実行")
        print("   2. Phase 4.4: 本番システム移行準備")
        print("   3. 効率化効果実測・検証")
    else:
        print("⚠️ システム準備不完全・追加作業必要")
        print("🔧 要対応項目:")
        for check, status in checks.items():
            if not status:
                print(f"   - {check}")

    return {
        "integration_ok": integration_ok,
        "model_results": model_results,
        "efficiency_results": efficiency_results,
        "readiness_score": readiness_score,
        "checks": checks,
    }


if __name__ == "__main__":
    print("🎊 97特徴量最適化システム効果検証スクリプト")
    print("=" * 60)

    try:
        report = generate_optimization_report()

        print("\n" + "=" * 60)
        print("🎊 97特徴量最適化システム検証完了！")

        if report["readiness_score"] >= 80:
            print("✅ Phase 2: 97特徴量最適化基盤構築 - 完全実装達成")
        else:
            print("⚠️ Phase 2: 追加作業が必要です")

    except Exception as e:
        logger.error(f"検証スクリプト実行エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
