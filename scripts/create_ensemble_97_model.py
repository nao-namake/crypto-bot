#!/usr/bin/env python3
"""
97特徴量アンサンブルモデル統合スクリプト
Phase 2: LightGBM・XGBoost・RandomForest統合アンサンブル

目的:
- 3つの個別モデルを統合したアンサンブルモデル作成
- 重み付け予測による安定性・精度向上
- 本番環境での統合運用対応
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin

# プロジェクトルートの追加
sys.path.insert(0, str(Path(__file__).parent.parent))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class Ensemble97FeatureClassifier(BaseEstimator, ClassifierMixin):
    """
    97特徴量用アンサンブル分類器

    LightGBM・XGBoost・RandomForestの3モデルを統合
    重み付き予測による安定性向上
    """

    def __init__(self, model_weights: List[float] = None):
        """
        初期化

        Args:
            model_weights: モデル重み [lgbm, xgb, rf]
        """
        self.model_weights = model_weights or [0.5, 0.3, 0.2]
        self.models = {}
        self.feature_names = None
        self.n_features = 97

        logger.info("🤖 Ensemble97FeatureClassifier initialized")
        logger.info(f"  - Model weights: {self.model_weights}")

    def load_individual_models(self, model_dir: str = "models/production"):
        """
        個別モデルの読み込み

        Args:
            model_dir: モデルディレクトリ
        """
        model_dir = Path(model_dir)

        try:
            # 個別モデル読み込み
            model_files = {
                "lgbm": model_dir / "lgbm_97_features.pkl",
                "xgb": model_dir / "xgb_97_features.pkl",
                "rf": model_dir / "rf_97_features.pkl",
            }

            for model_name, model_path in model_files.items():
                if model_path.exists():
                    self.models[model_name] = joblib.load(model_path)
                    logger.info(f"✅ Loaded {model_name} model from {model_path}")
                else:
                    logger.error(f"❌ Model not found: {model_path}")
                    raise FileNotFoundError(f"Model file not found: {model_path}")

            # 特徴量名取得（最初のモデルから）
            first_model = list(self.models.values())[0]
            if hasattr(first_model, "feature_names_in_"):
                self.feature_names = list(first_model.feature_names_in_)
            elif hasattr(first_model, "feature_name_"):
                self.feature_names = first_model.feature_name_
            else:
                # メタデータから取得
                metadata_path = model_dir / "lgbm_97_features_metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                        self.feature_names = metadata.get("feature_names", [])

            logger.info(f"✅ Ensemble loaded: {len(self.models)} models")
            logger.info(
                f"  - Feature names: {len(self.feature_names) if self.feature_names else 'Unknown'}"
            )

        except Exception as e:
            logger.error(f"❌ Failed to load individual models: {e}")
            raise

    def predict(self, X) -> np.ndarray:
        """
        アンサンブル予測（クラス）

        Args:
            X: 入力特徴量

        Returns:
            予測クラス
        """
        try:
            # 予測確率取得
            probabilities = self.predict_proba(X)

            # 最大確率のクラスを返す
            predictions = np.argmax(probabilities, axis=1)

            return predictions

        except Exception as e:
            logger.error(f"❌ Ensemble prediction failed: {e}")
            raise

    def predict_proba(self, X) -> np.ndarray:
        """
        アンサンブル予測（確率）

        Args:
            X: 入力特徴量

        Returns:
            予測確率
        """
        try:
            if not self.models:
                raise ValueError(
                    "Models not loaded. Call load_individual_models() first."
                )

            # 入力検証
            if hasattr(X, "shape"):
                if len(X.shape) == 1:
                    X = X.reshape(1, -1)
                if X.shape[1] != self.n_features:
                    logger.warning(
                        f"Feature count mismatch: {X.shape[1]} != {self.n_features}"
                    )

            # 各モデルの予測確率を取得
            model_predictions = []
            model_names = ["lgbm", "xgb", "rf"]

            for i, model_name in enumerate(model_names):
                if model_name in self.models:
                    model = self.models[model_name]

                    # モデル予測
                    if hasattr(model, "predict_proba"):
                        pred_proba = model.predict_proba(X)
                    else:
                        # predict_probaがない場合（一部のモデル）
                        pred = model.predict(X)
                        pred_proba = np.column_stack([(1 - pred), pred])

                    # 重み適用
                    weighted_proba = pred_proba * self.model_weights[i]
                    model_predictions.append(weighted_proba)

                    logger.debug(
                        f"  {model_name}: {pred_proba[0] if len(pred_proba) > 0 else 'empty'}"
                    )
                else:
                    logger.warning(f"⚠️ Model {model_name} not available")

            if not model_predictions:
                raise ValueError("No valid model predictions available")

            # アンサンブル予測（重み付き平均）
            ensemble_proba = np.sum(model_predictions, axis=0)

            # 正規化（重みの合計が1でない場合）
            ensemble_proba = ensemble_proba / np.sum(
                self.model_weights[: len(model_predictions)]
            )

            logger.debug(
                f"🔮 Ensemble prediction: {ensemble_proba[0] if len(ensemble_proba) > 0 else 'empty'}"
            )

            return ensemble_proba

        except Exception as e:
            logger.error(f"❌ Ensemble prediction probability failed: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """
        アンサンブルモデル情報取得

        Returns:
            モデル情報辞書
        """
        return {
            "ensemble_type": "97_features_optimized",
            "model_count": len(self.models),
            "model_names": list(self.models.keys()),
            "model_weights": self.model_weights,
            "feature_count": self.n_features,
            "feature_names": (
                self.feature_names[:10] if self.feature_names else None
            ),  # 最初の10個のみ
        }


def create_ensemble_model(
    model_dir: str = "models/production",
) -> Ensemble97FeatureClassifier:
    """
    アンサンブルモデル作成

    Args:
        model_dir: モデルディレクトリ

    Returns:
        統合アンサンブルモデル
    """
    logger.info("🚀 Creating 97-feature ensemble model...")

    try:
        # アンサンブル分類器初期化
        ensemble = Ensemble97FeatureClassifier(
            model_weights=[0.5, 0.3, 0.2]  # XGBoost重視の重み
        )

        # 個別モデル読み込み
        ensemble.load_individual_models(model_dir)

        # 情報表示
        info = ensemble.get_model_info()
        logger.info("✅ Ensemble model created successfully:")
        logger.info(f"  - Models: {info['model_names']}")
        logger.info(f"  - Weights: {info['model_weights']}")
        logger.info(f"  - Features: {info['feature_count']}")

        return ensemble

    except Exception as e:
        logger.error(f"❌ Failed to create ensemble model: {e}")
        raise


def save_ensemble_model(
    ensemble: Ensemble97FeatureClassifier,
    output_path: str = "models/production/ensemble_97_features.pkl",
):
    """
    アンサンブルモデル保存

    Args:
        ensemble: アンサンブルモデル
        output_path: 出力パス
    """
    logger.info(f"💾 Saving ensemble model to {output_path}...")

    try:
        # モデル保存
        joblib.dump(ensemble, output_path)

        # メタデータ作成
        metadata = {
            **ensemble.get_model_info(),
            "creation_timestamp": pd.Timestamp.now().isoformat(),
            "model_file": output_path,
            "usage_instructions": {
                "load": 'joblib.load("ensemble_97_features.pkl")',
                "predict": "model.predict(X)",
                "predict_proba": "model.predict_proba(X)",
            },
        }

        # メタデータ保存
        metadata_path = Path(output_path).with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"✅ Ensemble model saved:")
        logger.info(f"  - Model: {output_path}")
        logger.info(f"  - Metadata: {metadata_path}")
        logger.info(f"  - Model count: {metadata['model_count']}")

    except Exception as e:
        logger.error(f"❌ Failed to save ensemble model: {e}")
        raise


def test_ensemble_model(ensemble: Ensemble97FeatureClassifier):
    """
    アンサンブルモデルテスト

    Args:
        ensemble: アンサンブルモデル
    """
    logger.info("🧪 Testing ensemble model...")

    try:
        # テストデータ生成（97特徴量）
        np.random.seed(42)
        test_X = np.random.randn(5, 97)

        # 予測テスト
        predictions = ensemble.predict(test_X)
        probabilities = ensemble.predict_proba(test_X)

        logger.info("✅ Ensemble model test successful:")
        logger.info(f"  - Test samples: {len(test_X)}")
        logger.info(f"  - Predictions: {predictions}")
        logger.info(f"  - Probabilities shape: {probabilities.shape}")
        logger.info(f"  - Sample probabilities: {probabilities[0]}")

        return True

    except Exception as e:
        logger.error(f"❌ Ensemble model test failed: {e}")
        return False


def main():
    """メイン実行関数"""
    logger.info("🎯 97特徴量アンサンブルモデル統合開始")

    try:
        # 1. アンサンブルモデル作成
        ensemble = create_ensemble_model()

        # 2. モデルテスト
        test_success = test_ensemble_model(ensemble)
        if not test_success:
            raise RuntimeError("Ensemble model test failed")

        # 3. モデル保存
        save_ensemble_model(ensemble)

        logger.info("🎉 Ensemble model integration completed successfully!")
        logger.info("Next steps:")
        logger.info("1. Update production config to use ensemble_97_features.pkl")
        logger.info("2. Test with backtest system")
        logger.info("3. Deploy to production environment")

    except Exception as e:
        logger.error(f"❌ Ensemble integration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
