#!/usr/bin/env python3
"""
MLモデル予測分布検証スクリプト - Phase 60.9

MLモデルが極端なクラスバイアス（常にHOLDを返すなど）を持っていないか検証します。

検証項目:
1. ランダム特徴量での予測分布（多様性確認）
2. 訓練データのクラス分布（バランス確認）
3. 最大クラス比率の閾値チェック（HOLD偏り検出）

使用方法:
    python scripts/testing/validate_ml_prediction_distribution.py

終了コード:
    0: 検証成功（モデルは多様な予測を生成）
    1: 検証失敗（モデルに極端なバイアスあり）

Phase 60.9: MLが常にHOLDを返す問題の早期検出用
"""

import json
import pickle
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np


def load_model(model_path: str):
    """MLモデルを読み込む"""
    try:
        with open(model_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"  [ERROR] モデル読み込み失敗: {model_path} - {e}")
        return None


def check_prediction_distribution(model, n_samples: int = 100) -> dict:
    """
    ランダム特徴量での予測分布を確認

    Args:
        model: 読み込んだMLモデル
        n_samples: テストサンプル数

    Returns:
        {"class_0": count, "class_1": count, "class_2": count, "max_ratio": float}
    """
    try:
        n_features = len(model.feature_names) if hasattr(model, "feature_names") else 56

        # ランダム特徴量生成（標準正規分布）
        np.random.seed(42)
        random_features = np.random.randn(n_samples, n_features)

        # 予測実行
        predictions = model.predict(random_features)

        # 分布計算
        unique, counts = np.unique(predictions, return_counts=True)
        distribution = dict(zip(unique, counts))

        # 全クラス分布を埋める（0, 1, 2）
        for i in range(3):
            if i not in distribution:
                distribution[i] = 0

        # 最大クラス比率
        max_ratio = max(counts) / n_samples

        return {
            "class_0_sell": distribution.get(0, 0),
            "class_1_hold": distribution.get(1, 0),
            "class_2_buy": distribution.get(2, 0),
            "max_ratio": max_ratio,
            "total": n_samples,
        }
    except Exception as e:
        print(f"  [ERROR] 予測分布チェック失敗: {e}")
        return None


def check_metadata_class_distribution(metadata_path: str) -> dict:
    """
    メタデータから訓練データのクラス分布を確認

    Args:
        metadata_path: メタデータJSONファイルパス

    Returns:
        クラス分布情報（存在する場合）
    """
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        # training_data.class_distribution があれば返す
        if "training_data" in metadata:
            return metadata["training_data"].get("class_distribution", None)
        return None
    except Exception as e:
        print(f"  [WARN] メタデータ読み込み失敗: {e}")
        return None


def main():
    """メイン検証処理"""
    print(">>> 🤖 MLモデル予測分布検証（Phase 60.9）")

    # モデルパス
    model_path = Path("models/production/ensemble_full.pkl")
    metadata_path = Path("models/production/production_model_metadata.json")

    # モデル存在確認
    if not model_path.exists():
        print(f"  [SKIP] モデルファイルが見つかりません: {model_path}")
        print(
            "  モデル作成が必要: python scripts/ml/create_ml_models.py --n-classes 3 --threshold 0.002"
        )
        sys.exit(0)  # モデルがない場合はスキップ（他のチェックに影響しない）

    # モデル読み込み
    model = load_model(str(model_path))
    if model is None:
        print("  [ERROR] モデル読み込み失敗")
        sys.exit(1)

    # 予測分布チェック
    print("  📊 ランダム特徴量での予測分布テスト（100サンプル）")
    distribution = check_prediction_distribution(model, n_samples=100)

    if distribution is None:
        print("  [ERROR] 予測分布チェック失敗")
        sys.exit(1)

    # 結果表示
    print(
        f"     SELL (class 0): {distribution['class_0_sell']}回 ({distribution['class_0_sell']}%)"
    )
    print(
        f"     HOLD (class 1): {distribution['class_1_hold']}回 ({distribution['class_1_hold']}%)"
    )
    print(f"     BUY  (class 2): {distribution['class_2_buy']}回 ({distribution['class_2_buy']}%)")
    print(f"     最大クラス比率: {distribution['max_ratio']*100:.1f}%")

    # 閾値チェック（HOLDが80%以上なら警告、90%以上ならエラー）
    hold_ratio = distribution["class_1_hold"] / distribution["total"]
    max_ratio = distribution["max_ratio"]

    # 厳格チェック: 最大クラスが90%以上なら失敗
    MAX_CLASS_THRESHOLD = 0.90

    if max_ratio >= MAX_CLASS_THRESHOLD:
        print(
            f"  [FAIL] モデルに極端なクラスバイアスがあります（最大クラス: {max_ratio*100:.1f}% >= {MAX_CLASS_THRESHOLD*100:.0f}%）"
        )
        print("  原因: 訓練データのクラス不均衡（閾値が厳しすぎる可能性）")
        print("  対策: より緩い閾値でモデルを再訓練")
        print(
            "        python scripts/ml/create_ml_models.py --n-classes 3 --threshold 0.002 --use-smote --optimize --n-trials 50"
        )
        sys.exit(1)
    elif max_ratio >= 0.80:
        print(
            f"  [WARN] モデルのクラスバランスがやや偏っています（最大クラス: {max_ratio*100:.1f}%）"
        )
        print("  推奨: より緩い閾値でモデルを再訓練することを検討")
    else:
        print(f"  [OK] モデルのクラスバランスは良好です（最大クラス: {max_ratio*100:.1f}% < 80%）")

    # メタデータからの訓練データ分布確認（情報提供のみ）
    if metadata_path.exists():
        class_dist = check_metadata_class_distribution(str(metadata_path))
        if class_dist:
            print(f"  📋 訓練データのクラス分布: {class_dist}")

    print("✅ MLモデル予測分布検証完了")
    sys.exit(0)


if __name__ == "__main__":
    main()
