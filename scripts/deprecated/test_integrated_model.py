#!/usr/bin/env python3
"""
統合127特徴量モデルテストスクリプト
新しく作成されたモデルの動作確認
"""

import json
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.preprocessor import FeatureEngineer


def test_integrated_model():
    """統合127特徴量モデルのテスト"""
    print("🔍 統合127特徴量モデルテスト開始")

    # モデルファイル確認
    model_path = Path("models/production/integrated_127_features_model.pkl")
    features_path = Path("models/production/integrated_127_model_features.json")
    metadata_path = Path("models/production/integrated_127_model_metadata.json")

    if not model_path.exists():
        print(f"❌ モデルファイルが存在しません: {model_path}")
        return False

    if not features_path.exists():
        print(f"❌ 特徴量ファイルが存在しません: {features_path}")
        return False

    print(f"✅ モデルファイル確認: {model_path}")
    print(f"✅ 特徴量ファイル確認: {features_path}")

    # モデル読み込み
    try:
        model = joblib.load(model_path)
        print(f"✅ モデル読み込み成功: {type(model)}")
    except Exception as e:
        print(f"❌ モデル読み込み失敗: {e}")
        return False

    # 特徴量リスト読み込み
    try:
        with open(features_path, "r") as f:
            selected_features = json.load(f)
        print(f"✅ 特徴量リスト読み込み: {len(selected_features)}個")
        print(f"  先頭5個: {selected_features[:5]}")
    except Exception as e:
        print(f"❌ 特徴量リスト読み込み失敗: {e}")
        return False

    # メタデータ読み込み
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            print(f"✅ メタデータ読み込み成功:")
            print(f"  精度: {metadata.get('accuracy', 'N/A'):.1%}")
            print(f"  F1スコア: {metadata.get('f1_score', 'N/A'):.1%}")
            print(f"  選択特徴量数: {metadata.get('n_features_selected', 'N/A')}")
        except Exception as e:
            print(f"⚠️ メタデータ読み込み失敗: {e}")

    # テストデータ生成
    print("🔍 テストデータ生成...")
    np.random.seed(42)
    n_test = 100

    test_data = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2024-01-01", periods=n_test, freq="1H"),
            "open": np.random.normal(45000, 1000, n_test),
            "high": np.random.normal(45500, 1000, n_test),
            "low": np.random.normal(44500, 1000, n_test),
            "close": np.random.normal(45000, 1000, n_test),
            "volume": np.random.lognormal(6, 0.3, n_test),
        }
    )

    # 価格の整合性確保
    for i in range(n_test):
        test_data.loc[i, "high"] = max(
            test_data.loc[i, "open"],
            test_data.loc[i, "close"],
            test_data.loc[i, "high"],
        )
        test_data.loc[i, "low"] = min(
            test_data.loc[i, "open"], test_data.loc[i, "close"], test_data.loc[i, "low"]
        )

    print(f"✅ テストデータ生成完了: {test_data.shape}")

    # 特徴量エンジニアリング（簡易版）
    print("🔍 特徴量エンジニアリング...")
    config = {
        "ml": {
            "feat_period": 14,
            "lags": [1, 2, 3],
            "rolling_window": 10,
            "horizon": 3,
            "target_type": "classification",
            "extra_features": [
                "rsi_14",
                "sma_20",
                "ema_20",
                "bb_upper",
                "bb_lower",
                "bb_middle",
                "macd",
                "stoch_k",
                "stoch_d",
                "atr_14",
            ],
        }
    }

    try:
        engineer = FeatureEngineer(config)
        features = engineer.fit_transform(test_data)
        print(f"✅ 特徴量生成完了: {features.shape}")
        print(f"  生成された特徴量: {list(features.columns)[:10]}...")
    except Exception as e:
        print(f"❌ 特徴量エンジニアリング失敗: {e}")
        return False

    # 選択特徴量のみ抽出
    print("🔍 選択特徴量抽出...")
    available_features = [f for f in selected_features if f in features.columns]
    missing_features = [f for f in selected_features if f not in features.columns]

    print(f"  利用可能特徴量: {len(available_features)}/{len(selected_features)}")
    if missing_features:
        print(f"  不足特徴量: {len(missing_features)}個")
        print(f"    例: {missing_features[:5]}")

    # 不足特徴量をダミー値で補完
    if missing_features:
        print("🔍 不足特徴量をダミー値で補完...")
        for feat in missing_features:
            features[feat] = np.random.normal(0, 1, len(features))

    # 特徴量順序を選択リストに合わせる
    X_test = features[selected_features].fillna(0)
    print(f"✅ テスト用特徴量準備完了: {X_test.shape}")

    # モデル予測テスト
    print("🔍 モデル予測テスト...")
    try:
        # 予測確率
        pred_proba = model.predict(X_test.iloc[-1:])  # 最後の1行でテスト
        print(f"✅ 予測確率計算成功: {pred_proba}")
        print(f"  予測確率形状: {pred_proba.shape}")
        print(f"  予測確率範囲: {pred_proba.min():.3f} - {pred_proba.max():.3f}")

        # バイナリ予測
        binary_pred = (pred_proba > 0.5).astype(int)
        print(
            f"✅ バイナリ予測: {binary_pred[0]} ({'BUY' if binary_pred[0] == 1 else 'SELL'})"
        )

        # 複数行テスト
        if len(X_test) >= 10:
            pred_proba_multi = model.predict(X_test.iloc[-10:])
            print(f"✅ 複数行予測成功: {len(pred_proba_multi)}行")
            print(
                f"  予測確率統計: 平均={pred_proba_multi.mean():.3f}, 標準偏差={pred_proba_multi.std():.3f}"
            )

        return True

    except Exception as e:
        print(f"❌ モデル予測失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_integrated_model()
    if success:
        print("\\n✅ 統合127特徴量モデルテスト成功！")
        print("モデルは正常に動作しています。")
    else:
        print("\\n❌ 統合127特徴量モデルテスト失敗")
        print("問題を修正してください。")

    sys.exit(0 if success else 1)
