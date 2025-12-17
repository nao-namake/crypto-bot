#!/usr/bin/env python3
"""
MLモデル予測分布検証スクリプト - Phase 54.8

MLモデルが極端なクラスバイアス（常にHOLDを返すなど）を持っていないか検証します。

検証項目:
1. 実データでの予測分布（実運用想定）
2. 訓練データのクラス分布（バランス確認）
3. 最大クラス比率の閾値チェック（HOLD偏り検出）

使用方法:
    python scripts/testing/validate_ml_prediction_distribution.py

終了コード:
    0: 検証成功（モデルは多様な予測を生成）
    1: 検証失敗（モデルに極端なバイアスあり）

Phase 54.8: 実データ検証に変更（ランダム特徴量は無効）
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def load_model(model_path: str):
    """MLモデルを読み込む"""
    try:
        with open(model_path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"  [ERROR] モデル読み込み失敗: {model_path} - {e}")
        return None


def load_real_data(data_path: str, n_samples: int = 200) -> pd.DataFrame:
    """
    実データを読み込む

    Args:
        data_path: CSVファイルパス
        n_samples: 使用するサンプル数

    Returns:
        DataFrame（最新n_samples行）
    """
    try:
        df = pd.read_csv(data_path)
        # タイムスタンプをdatetimeに変換してインデックスに設定
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("timestamp")
            df.index = pd.DatetimeIndex(df.index)
        return df.tail(n_samples)
    except Exception as e:
        print(f"  [ERROR] データ読み込み失敗: {e}")
        return None


def generate_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    特徴量を生成

    Args:
        df: OHLCVデータ

    Returns:
        特徴量DataFrame
    """
    try:
        from src.features.feature_generator import FeatureGenerator

        generator = FeatureGenerator()
        return generator.generate_features_sync(df)
    except Exception as e:
        print(f"  [ERROR] 特徴量生成失敗: {e}")
        return None


def check_prediction_distribution_real(model, features_df: pd.DataFrame) -> dict:
    """
    実データでの予測分布を確認

    Args:
        model: 読み込んだMLモデル
        features_df: 特徴量DataFrame

    Returns:
        {"class_0": count, "class_1": count, "class_2": count, "max_ratio": float}
    """
    try:
        # モデルの期待する特徴量を取得
        expected_features = model.feature_names if hasattr(model, "feature_names") else []

        # 不足特徴量はダミー値（0）で補完
        test_df = features_df.copy()
        for f in expected_features:
            if f not in test_df.columns:
                test_df[f] = 0.0

        # 特徴量を正しい順序で抽出
        X_test = test_df[expected_features].values

        # NaNを0で置換
        X_test = np.nan_to_num(X_test, nan=0.0)

        # 予測実行
        predictions = model.predict(X_test)

        # 分布計算
        unique, counts = np.unique(predictions, return_counts=True)
        distribution = dict(zip(unique, counts))

        # 全クラス分布を埋める（0, 1, 2）
        for i in range(3):
            if i not in distribution:
                distribution[i] = 0

        # 最大クラス比率
        total = len(predictions)
        max_ratio = max(counts) / total

        return {
            "class_0_sell": distribution.get(0, 0),
            "class_1_hold": distribution.get(1, 0),
            "class_2_buy": distribution.get(2, 0),
            "max_ratio": max_ratio,
            "total": total,
        }
    except Exception as e:
        print(f"  [ERROR] 予測分布チェック失敗: {e}")
        import traceback

        traceback.print_exc()
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
    print(">>> MLモデル予測分布検証（Phase 54.8 - 実データ版）")

    # パス設定
    model_path = Path("models/production/ensemble_full.pkl")
    metadata_path = Path("models/production/production_model_metadata.json")
    data_path = Path("src/backtest/data/historical/btc_jpy_15m.csv")

    # モデル存在確認
    if not model_path.exists():
        print(f"  [SKIP] モデルファイルが見つかりません: {model_path}")
        print(
            "  モデル作成が必要: python scripts/ml/create_ml_models.py "
            "--n-classes 3 --threshold 0.003 --use-smote"
        )
        sys.exit(0)

    # データ存在確認
    if not data_path.exists():
        print(f"  [ERROR] データファイルが見つかりません: {data_path}")
        sys.exit(1)

    # モデル読み込み
    model = load_model(str(model_path))
    if model is None:
        print("  [ERROR] モデル読み込み失敗")
        sys.exit(1)

    # 実データ読み込み
    print("  実データ読み込み中...")
    df = load_real_data(str(data_path), n_samples=300)
    if df is None:
        print("  [ERROR] データ読み込み失敗")
        sys.exit(1)
    print(f"  データ読み込み完了: {len(df)}行")

    # 特徴量生成
    print("  特徴量生成中...")
    features_df = generate_features(df)
    if features_df is None:
        print("  [ERROR] 特徴量生成失敗")
        sys.exit(1)
    print(f"  特徴量生成完了: {len(features_df)}行 x {len(features_df.columns)}列")

    # 予測分布チェック（実データ）
    print("  実データでの予測分布テスト...")
    distribution = check_prediction_distribution_real(model, features_df)

    if distribution is None:
        print("  [ERROR] 予測分布チェック失敗")
        sys.exit(1)

    # 結果表示
    total = distribution["total"]
    sell_pct = distribution["class_0_sell"] / total * 100
    hold_pct = distribution["class_1_hold"] / total * 100
    buy_pct = distribution["class_2_buy"] / total * 100

    print(f"     SELL (class 0): {distribution['class_0_sell']}回 ({sell_pct:.1f}%)")
    print(f"     HOLD (class 1): {distribution['class_1_hold']}回 ({hold_pct:.1f}%)")
    print(f"     BUY  (class 2): {distribution['class_2_buy']}回 ({buy_pct:.1f}%)")
    print(f"     最大クラス比率: {distribution['max_ratio'] * 100:.1f}%")

    # 閾値チェック
    max_ratio = distribution["max_ratio"]
    MAX_CLASS_THRESHOLD = 0.90
    WARN_THRESHOLD = 0.80

    if max_ratio >= MAX_CLASS_THRESHOLD:
        print(
            f"  [FAIL] モデルに極端なクラスバイアスがあります"
            f"（最大クラス: {max_ratio * 100:.1f}% >= {MAX_CLASS_THRESHOLD * 100:.0f}%）"
        )
        print("  原因: 訓練データのクラス不均衡 or SMOTEが未適用")
        print("  対策: SMOTE適用でモデルを再訓練")
        print(
            "        python scripts/ml/create_ml_models.py "
            "--n-classes 3 --threshold 0.003 --use-smote --optimize --n-trials 30"
        )
        sys.exit(1)
    elif max_ratio >= WARN_THRESHOLD:
        print(
            f"  [WARN] モデルのクラスバランスがやや偏っています"
            f"（最大クラス: {max_ratio * 100:.1f}%）"
        )
        print("  推奨: より緩い閾値 or SMOTEでモデルを再訓練することを検討")
    else:
        print(
            f"  [OK] モデルのクラスバランスは良好です"
            f"（最大クラス: {max_ratio * 100:.1f}% < 80%）"
        )

    # BUY/SELLバランスチェック
    if min(sell_pct, buy_pct) < 5:
        print(f"  [WARN] BUY/SELLの一方が5%未満です（SELL:{sell_pct:.1f}%, BUY:{buy_pct:.1f}%）")

    # メタデータからの訓練データ分布確認
    if metadata_path.exists():
        class_dist = check_metadata_class_distribution(str(metadata_path))
        if class_dist:
            print(f"  訓練データのクラス分布: {class_dist}")

    print(">>> MLモデル予測分布検証完了")
    sys.exit(0)


if __name__ == "__main__":
    main()
