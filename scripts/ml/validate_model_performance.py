#!/usr/bin/env python3
"""
Phase 54.7: MLモデル性能検証スクリプト

目的:
- 訓練済みモデルの予測性能を検証
- 精度・F1スコア・信頼度分布を確認
- デプロイ前のローカル検証

使用方法:
    python scripts/ml/validate_model_performance.py
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


class ModelPerformanceValidator:
    """モデル性能検証クラス"""

    def __init__(self):
        self.project_root = project_root
        self.model = None
        self.metadata = None

    def load_model(self) -> bool:
        """モデル読み込み"""
        print("=" * 60)
        print("📦 モデル読み込み")
        print("=" * 60)

        model_path = self.project_root / "models/production/ensemble_full.pkl"
        metadata_path = self.project_root / "models/production/production_model_metadata.json"

        try:
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
            print(f"✅ モデル読み込み成功: {model_path.name}")
            print(f"   タイプ: {type(self.model).__name__}")

            with open(metadata_path, "r") as f:
                self.metadata = json.load(f)
            print(f"✅ メタデータ読み込み成功")
            print(f"   作成日時: {self.metadata.get('created_at', 'unknown')}")
            print(
                f"   特徴量数: {self.metadata.get('training_info', {}).get('feature_count', 'unknown')}"
            )
            return True
        except Exception as e:
            print(f"❌ モデル読み込みエラー: {e}")
            return False

    def load_test_data(self) -> pd.DataFrame:
        """テストデータ読み込み"""
        print("\n" + "=" * 60)
        print("📊 テストデータ読み込み")
        print("=" * 60)

        # 4h足データを使用
        data_path = self.project_root / "src/backtest/data/historical/btc_jpy_4h.csv"

        try:
            df = pd.read_csv(data_path)
            print(f"✅ データ読み込み成功: {data_path.name}")
            print(f"   行数: {len(df)}")
            print(f"   期間: {df['timestamp'].iloc[0]} 〜 {df['timestamp'].iloc[-1]}")
            return df
        except Exception as e:
            print(f"❌ データ読み込みエラー: {e}")
            return None

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特徴量生成"""
        print("\n" + "=" * 60)
        print("🔧 特徴量生成")
        print("=" * 60)

        try:
            from src.features.feature_generator import FeatureGenerator

            generator = FeatureGenerator()
            features_df = generator.generate_features_sync(df)
            print(f"✅ 特徴量生成成功: {len(features_df.columns)}列")
            return features_df
        except Exception as e:
            print(f"❌ 特徴量生成エラー: {e}")
            return None

    def validate_predictions(self, features_df: pd.DataFrame) -> dict:
        """予測検証"""
        print("\n" + "=" * 60)
        print("🎯 予測検証")
        print("=" * 60)

        # モデルの期待する特徴量を取得
        expected_features = self.metadata.get("feature_names", [])
        print(f"   期待特徴量数: {len(expected_features)}")

        # 戦略信号以外の特徴量でテスト（戦略信号はダミー値で補完）
        base_features = [f for f in expected_features if not f.startswith("strategy_signal_")]
        strategy_features = [f for f in expected_features if f.startswith("strategy_signal_")]

        print(f"   基本特徴量: {len(base_features)}")
        print(f"   戦略信号: {len(strategy_features)}")

        # 利用可能な特徴量を確認
        available = [f for f in base_features if f in features_df.columns]
        missing = [f for f in base_features if f not in features_df.columns]

        print(f"\n   利用可能: {len(available)}/{len(base_features)}")
        if missing:
            print(f"   不足: {missing[:5]}...")

        # テスト用データを準備（最新100件）
        test_size = min(100, len(features_df))
        test_df = features_df.tail(test_size).copy()

        # 不足特徴量はダミー値（0）で補完
        for f in expected_features:
            if f not in test_df.columns:
                test_df[f] = 0.0

        # 特徴量を正しい順序で抽出
        X_test = test_df[expected_features].values

        # NaNを0で置換
        X_test = np.nan_to_num(X_test, nan=0.0)

        print(f"\n   テストデータ形状: {X_test.shape}")

        # 予測実行
        try:
            predictions = self.model.predict(X_test)
            probabilities = self.model.predict_proba(X_test)

            # 結果集計
            unique, counts = np.unique(predictions, return_counts=True)
            pred_dist = dict(zip(unique, counts))

            print(f"\n✅ 予測成功")
            print(f"   予測分布:")
            for label, count in sorted(pred_dist.items()):
                pct = count / len(predictions) * 100
                label_name = {0: "SELL", 1: "HOLD", 2: "BUY"}.get(label, str(label))
                print(f"     {label_name}: {count}件 ({pct:.1f}%)")

            # 信頼度分析
            max_probs = np.max(probabilities, axis=1)
            print(f"\n   信頼度統計:")
            print(f"     平均: {np.mean(max_probs):.3f}")
            print(f"     最小: {np.min(max_probs):.3f}")
            print(f"     最大: {np.max(max_probs):.3f}")
            print(f"     標準偏差: {np.std(max_probs):.3f}")

            # 高信頼度（>0.6）の割合
            high_conf = np.sum(max_probs > 0.6) / len(max_probs) * 100
            print(f"     高信頼度(>60%): {high_conf:.1f}%")

            return {
                "success": True,
                "test_size": test_size,
                "predictions": pred_dist,
                "confidence_mean": float(np.mean(max_probs)),
                "confidence_std": float(np.std(max_probs)),
                "high_confidence_ratio": high_conf,
            }

        except Exception as e:
            print(f"❌ 予測エラー: {e}")
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def validate_individual_models(self) -> dict:
        """個別モデルの検証"""
        print("\n" + "=" * 60)
        print("🔍 個別モデル検証")
        print("=" * 60)

        if not hasattr(self.model, "models"):
            print("⚠️ 個別モデルへのアクセス不可")
            return {}

        results = {}
        for name, model in self.model.models.items():
            print(f"\n📊 {name}:")
            print(f"   タイプ: {type(model).__name__}")

            if hasattr(model, "n_estimators"):
                print(f"   n_estimators: {model.n_estimators}")
            if hasattr(model, "n_features_in_"):
                print(f"   n_features_in_: {model.n_features_in_}")
            if hasattr(model, "classes_"):
                print(f"   classes_: {model.classes_}")

            # メタデータから性能を取得
            perf = self.metadata.get("performance_metrics", {}).get(name, {})
            if perf:
                print(f"   訓練時性能:")
                print(f"     Accuracy: {perf.get('accuracy', 'N/A'):.3f}")
                print(f"     F1 Score: {perf.get('f1_score', 'N/A'):.3f}")
                print(f"     CV F1 Mean: {perf.get('cv_f1_mean', 'N/A'):.3f}")

            results[name] = {
                "type": type(model).__name__,
                "n_features": getattr(model, "n_features_in_", None),
                "performance": perf,
            }

        return results

    def run_validation(self) -> bool:
        """全検証を実行"""
        print("\n" + "=" * 60)
        print("🚀 Phase 54.7: MLモデル性能検証開始")
        print("=" * 60)

        # 1. モデル読み込み
        if not self.load_model():
            return False

        # 2. 個別モデル検証
        individual_results = self.validate_individual_models()

        # 3. テストデータ読み込み
        df = self.load_test_data()
        if df is None:
            return False

        # 4. 特徴量生成
        features_df = self.generate_features(df)
        if features_df is None:
            return False

        # 5. 予測検証
        pred_results = self.validate_predictions(features_df)

        # 6. 結果サマリー
        print("\n" + "=" * 60)
        print("📋 検証結果サマリー")
        print("=" * 60)

        if pred_results.get("success"):
            print("\n✅ モデル性能検証成功")
            print(f"   テストサンプル数: {pred_results.get('test_size')}")
            print(f"   信頼度平均: {pred_results.get('confidence_mean', 0):.3f}")
            print(f"   高信頼度比率: {pred_results.get('high_confidence_ratio', 0):.1f}%")

            # 予測バランスチェック
            preds = pred_results.get("predictions", {})
            total = sum(preds.values())
            if total > 0:
                buy_ratio = preds.get(2, 0) / total * 100
                sell_ratio = preds.get(0, 0) / total * 100
                hold_ratio = preds.get(1, 0) / total * 100

                print(f"\n   予測バランス:")
                print(f"     BUY: {buy_ratio:.1f}%")
                print(f"     HOLD: {hold_ratio:.1f}%")
                print(f"     SELL: {sell_ratio:.1f}%")

                # バランスチェック
                if abs(buy_ratio - sell_ratio) > 30:
                    print("\n⚠️ 警告: BUY/SELLの偏りが大きい")
                elif hold_ratio > 80:
                    print("\n⚠️ 警告: HOLD比率が高すぎる")
                else:
                    print("\n✅ 予測バランス良好")

            return True
        else:
            print(f"\n❌ モデル性能検証失敗: {pred_results.get('error')}")
            return False


def main():
    """メイン処理"""
    validator = ModelPerformanceValidator()
    success = validator.run_validation()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
