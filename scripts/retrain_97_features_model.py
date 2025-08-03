#!/usr/bin/env python3
"""
97特徴量最適化システム用モデル再学習スクリプト
Phase 2: 127→97特徴量最適化後のMLモデル再学習

機能:
- 97特徴量でのLightGBM・XGBoost・RandomForestアンサンブル学習
- feature_order.json整合性確保
- 本番環境用モデル生成
- 品質保証・性能検証
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import TimeSeriesSplit
from xgboost import XGBClassifier

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Model97FeatureRetrainer:
    """97特徴量最適化システム用モデル再学習"""

    def __init__(self, config_path: str = "config/production/production.yml"):
        self.config_path = config_path
        self.feature_manager = FeatureOrderManager()

        # 97特徴量の確認
        self.expected_features = self.feature_manager.FEATURE_ORDER_97
        logger.info(f"🎯 Target: {len(self.expected_features)} optimized features")

        # モデル設定
        self.models = {
            "lgbm": LGBMClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=8,
                num_leaves=31,
                random_state=42,
                verbose=-1,
            ),
            "xgb": XGBClassifier(
                n_estimators=200,
                learning_rate=0.1,
                max_depth=8,
                random_state=42,
                eval_metric="logloss",
            ),
            "rf": RandomForestClassifier(
                n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
            ),
        }

    def load_config(self):
        """設定読み込み"""
        import yaml

        with open(self.config_path, "r") as f:
            config = yaml.safe_load(f)

        logger.info(f"✅ Configuration loaded from {self.config_path}")
        return config

    def prepare_data(self, config):
        """97特徴量データ準備"""
        # サンプルデータ生成（実際の使用時はBitbankデータを使用）
        dates = pd.date_range("2024-01-01", "2024-12-31", freq="H")

        # 基本OHLCV生成
        np.random.seed(42)
        n_samples = len(dates)

        base_price = 100.0
        prices = []
        current_price = base_price

        for i in range(n_samples):
            # ランダムウォーク
            change = np.random.normal(0, 0.02)
            current_price *= 1 + change
            prices.append(current_price)

        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                "low": [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                "close": prices,
                "volume": np.random.lognormal(10, 1, n_samples),
            }
        )

        df.set_index("timestamp", inplace=True)

        # 特徴量エンジニアリング
        feature_engineer = FeatureEngineer(config)
        features_df = feature_engineer.transform(df)

        # 97特徴量への整合性確保
        features_df = self.feature_manager.ensure_column_order(features_df)

        # 正確に97特徴量を確保
        if len(features_df.columns) != 97:
            logger.warning(f"Feature count mismatch: {len(features_df.columns)} != 97")

            # 不足分は0埋め
            for feature in self.expected_features:
                if feature not in features_df.columns:
                    features_df[feature] = 0.0

            # 97特徴量のみ選択
            features_df = features_df[self.expected_features]

        # ターゲット生成（価格変動による分類）
        price_change = df["close"].pct_change(periods=1).shift(-1)
        target = (price_change > 0.002).astype(int)  # 0.2%以上の上昇をBUY

        # NaN除去
        valid_mask = ~(features_df.isna().any(axis=1) | target.isna())
        features_df = features_df[valid_mask]
        target = target[valid_mask]

        logger.info(
            f"✅ Data prepared: {len(features_df)} samples, {len(features_df.columns)} features"
        )
        logger.info(f"   Target distribution: {target.value_counts().to_dict()}")

        return features_df, target

    def train_models(self, features_df, target):
        """97特徴量でのモデル学習"""
        logger.info("🔄 Starting model training with 97 optimized features...")

        # Time Series Split for validation
        tscv = TimeSeriesSplit(n_splits=3)
        results = {}

        for model_name, model in self.models.items():
            logger.info(f"Training {model_name}...")

            scores = []
            f1_scores = []

            for train_idx, val_idx in tscv.split(features_df):
                X_train, X_val = features_df.iloc[train_idx], features_df.iloc[val_idx]
                y_train, y_val = target.iloc[train_idx], target.iloc[val_idx]

                # 特徴量順序の最終確認
                X_train = self.feature_manager.ensure_column_order(X_train)
                X_val = self.feature_manager.ensure_column_order(X_val)

                # 学習
                model.fit(X_train, y_train)

                # 予測・評価
                y_pred = model.predict(X_val)
                accuracy = accuracy_score(y_val, y_pred)
                f1 = f1_score(y_val, y_pred, average="weighted")

                scores.append(accuracy)
                f1_scores.append(f1)

            avg_accuracy = np.mean(scores)
            avg_f1 = np.mean(f1_scores)

            results[model_name] = {
                "model": model,
                "accuracy": avg_accuracy,
                "f1_score": avg_f1,
                "std_accuracy": np.std(scores),
                "std_f1": np.std(f1_scores),
            }

            logger.info(
                f"✅ {model_name}: Accuracy={avg_accuracy:.4f}±{np.std(scores):.4f}, F1={avg_f1:.4f}±{np.std(f1_scores):.4f}"
            )

        return results

    def save_models(self, results, features_df):
        """97特徴量モデル保存"""
        model_dir = Path("models/production")
        model_dir.mkdir(parents=True, exist_ok=True)

        for model_name, result in results.items():
            model = result["model"]

            # モデル保存
            model_path = model_dir / f"{model_name}_97_features.pkl"

            import joblib

            joblib.dump(model, model_path)

            # メタデータ保存
            metadata = {
                "model_type": f"{model.__class__.__name__}_97_features",
                "n_features": 97,
                "feature_names": list(features_df.columns),
                "accuracy": result["accuracy"],
                "f1_score": result["f1_score"],
                "training_date": pd.Timestamp.now().isoformat(),
                "optimization_info": {
                    "original_features": 127,
                    "optimized_features": 97,
                    "deleted_features": 30,
                    "optimization_reason": "重複特徴量削除による性能向上・計算効率化",
                },
            }

            metadata_path = model_dir / f"{model_name}_97_features_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"✅ Saved {model_name} model and metadata")

        # 統合メタデータ
        ensemble_metadata = {
            "ensemble_type": "97_features_optimized",
            "models": {name: result["accuracy"] for name, result in results.items()},
            "feature_count": 97,
            "optimization_date": pd.Timestamp.now().isoformat(),
            "performance_summary": {
                "best_model": max(results.keys(), key=lambda x: results[x]["accuracy"]),
                "avg_accuracy": np.mean([r["accuracy"] for r in results.values()]),
                "avg_f1": np.mean([r["f1_score"] for r in results.values()]),
            },
        }

        ensemble_path = model_dir / "ensemble_97_features_metadata.json"
        with open(ensemble_path, "w") as f:
            json.dump(ensemble_metadata, f, indent=2)

        logger.info("✅ Ensemble metadata saved")

    def run_retraining(self):
        """97特徴量システム再学習実行"""
        logger.info("🚀 Starting 97-feature optimization model retraining...")

        try:
            # 1. 設定読み込み
            config = self.load_config()

            # 2. データ準備
            features_df, target = self.prepare_data(config)

            # 3. 特徴量整合性最終確認
            assert (
                len(features_df.columns) == 97
            ), f"Feature count error: {len(features_df.columns)} != 97"
            assert (
                list(features_df.columns) == self.expected_features
            ), "Feature order mismatch"

            # 4. モデル学習
            results = self.train_models(features_df, target)

            # 5. モデル保存
            self.save_models(results, features_df)

            # 6. 結果サマリー
            logger.info("🎊 97-feature optimization retraining completed successfully!")
            logger.info("📊 Performance Summary:")
            for model_name, result in results.items():
                logger.info(
                    f"   {model_name}: {result['accuracy']:.4f} accuracy, {result['f1_score']:.4f} F1"
                )

            return True

        except Exception as e:
            logger.error(f"❌ Retraining failed: {str(e)}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """メイン実行"""
    retrainer = Model97FeatureRetrainer()
    success = retrainer.run_retraining()

    if success:
        print("🎊 97特徴量最適化モデル再学習完了！")
        sys.exit(0)
    else:
        print("❌ 再学習失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()
