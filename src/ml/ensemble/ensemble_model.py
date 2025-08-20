"""
アンサンブルモデル実装 - Phase 12実装・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応

3つの機械学習モデル（LightGBM、XGBoost、RandomForest）を統合し、
ソフト投票によって予測精度を向上させるアンサンブル学習システム。

保守性と性能のバランスを重視したシンプルな実装。.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

from ...core.exceptions import DataProcessingError
from ...core.logger import get_logger
from ..models import BaseMLModel, LGBMModel, RFModel, XGBModel


class EnsembleModel:
    """
    アンサンブル分類モデル

    3つの強力なモデルを統合してロバストな予測を提供。
    レガシーシステムの複雑性を排除し、理解しやすい設計を採用。.
    """

    def __init__(
        self,
        models: Optional[Dict[str, BaseMLModel]] = None,
        weights: Optional[Dict[str, float]] = None,
        confidence_threshold: float = 0.35,
    ):
        """
        アンサンブルモデルの初期化

        Args:
            models: 使用するモデル辞書（デフォルト: 3モデル自動作成）
            weights: モデル重み（デフォルト: 均等重み）
            confidence_threshold: 予測信頼度閾値.
        """
        self.confidence_threshold = confidence_threshold
        self.logger = get_logger()

        # デフォルトモデルの作成
        if models is None:
            self.models = self._create_default_models()
        else:
            self.models = models

        # デフォルト重みの設定（均等重み）
        if weights is None:
            num_models = len(self.models)
            self.weights = {name: 1.0 / num_models for name in self.models.keys()}
        else:
            self.weights = weights

        # 重みの正規化
        self._normalize_weights()

        # 学習状態の管理
        self.is_fitted = False
        self.feature_names = None
        self.classes_ = None
        self.model_performance = {}

        self.logger.info(f"✅ EnsembleModel initialized with {len(self.models)} models")
        self.logger.info(f"Models: {list(self.models.keys())}")
        self.logger.info(f"Weights: {self.weights}")

    def _create_default_models(self) -> Dict[str, BaseMLModel]:
        """デフォルトの3モデルを作成."""
        try:
            models = {"lgbm": LGBMModel(), "xgb": XGBModel(), "rf": RFModel()}

            self.logger.info("✅ Default models created successfully")
            return models

        except Exception as e:
            self.logger.error(f"❌ Failed to create default models: {e}")
            raise DataProcessingError(f"Model creation failed: {e}")

    def _normalize_weights(self) -> None:
        """重みの正規化（合計が1になるように調整）."""
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {name: weight / total_weight for name, weight in self.weights.items()}
        else:
            # 全重みが0の場合は均等重みに戻す
            num_models = len(self.weights)
            self.weights = {name: 1.0 / num_models for name in self.weights.keys()}

        self.logger.debug(f"Normalized weights: {self.weights}")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "EnsembleModel":
        """
        アンサンブルモデルの学習

        Args:
            X: 特徴量データ
            y: ターゲットデータ

        Returns:
            EnsembleModel: 学習済みアンサンブルモデル.
        """
        try:
            self.logger.info(f"Starting ensemble training with {len(X)} samples")

            # データの妥当性チェック
            self._validate_training_data(X, y)

            # 特徴量名とクラスを保存
            self.feature_names = X.columns.tolist()
            self.classes_ = np.unique(y)

            start_time = time.time()

            # 各モデルを個別に学習
            for model_name, model in self.models.items():
                model_start = time.time()

                self.logger.info(f"Training {model_name}...")
                model.fit(X, y)

                # 学習時間を記録
                training_time = time.time() - model_start
                self.model_performance[model_name] = {
                    "training_time": training_time,
                    "is_fitted": model.is_fitted,
                }

                self.logger.info(f"✅ {model_name} training completed in {training_time:.2f}s")

            total_time = time.time() - start_time
            self.is_fitted = True

            self.logger.info(f"🎉 Ensemble training completed in {total_time:.2f}s")
            return self

        except Exception as e:
            self.logger.error(f"❌ Ensemble training failed: {e}")
            raise DataProcessingError(f"Ensemble training failed: {e}")

    def predict(self, X: pd.DataFrame, use_confidence: bool = True) -> np.ndarray:
        """
        アンサンブル予測の実行

        Args:
            X: 特徴量データ
            use_confidence: confidence閾値を使用するかどうか

        Returns:
            np.ndarray: 予測クラス.
        """
        if not self.is_fitted:
            raise ValueError("EnsembleModel is not fitted. Call fit() first.")

        try:
            # 確率予測を取得
            probabilities = self.predict_proba(X)

            if use_confidence:
                # confidence閾値を適用
                predictions = self._apply_confidence_threshold(probabilities)
            else:
                # 単純に最大確率のクラスを選択
                predictions = np.argmax(probabilities, axis=1)

            return predictions

        except Exception as e:
            self.logger.error(f"Ensemble prediction failed: {e}")
            raise DataProcessingError(f"Prediction failed: {e}")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        アンサンブル確率予測の実行

        Args:
            X: 特徴量データ

        Returns:
            np.ndarray: 予測確率（重み付け平均）.
        """
        if not self.is_fitted:
            raise ValueError("EnsembleModel is not fitted. Call fit() first.")

        try:
            weighted_probabilities = None
            total_weight = 0.0

            # 各モデルの予測確率を重み付けして統合
            for model_name, model in self.models.items():
                if not model.is_fitted:
                    self.logger.warning(f"{model_name} is not fitted, skipping...")
                    continue

                # モデルの確率予測を取得
                model_proba = model.predict_proba(X)

                # 重み付けして加算
                weight = self.weights.get(model_name, 0.0)
                if weighted_probabilities is None:
                    weighted_probabilities = weight * model_proba
                else:
                    weighted_probabilities += weight * model_proba

                total_weight += weight

            if weighted_probabilities is None or total_weight == 0:
                raise ValueError("No fitted models available for prediction")

            # 重みで正規化
            if total_weight != 1.0:
                weighted_probabilities /= total_weight

            return weighted_probabilities

        except Exception as e:
            self.logger.error(f"Ensemble probability prediction failed: {e}")
            raise DataProcessingError(f"Probability prediction failed: {e}")

    def _apply_confidence_threshold(self, probabilities: np.ndarray) -> np.ndarray:
        """
        confidence閾値を適用した予測

        Args:
            probabilities: 予測確率

        Returns:
            np.ndarray: 閾値適用後の予測クラス.
        """
        predictions = np.argmax(probabilities, axis=1)
        max_probabilities = np.max(probabilities, axis=1)

        # confidence閾値未満の予測は不明クラス（-1）とする
        low_confidence_mask = max_probabilities < self.confidence_threshold
        predictions[low_confidence_mask] = -1

        confidence_ratio = 1.0 - (low_confidence_mask.sum() / len(predictions))
        self.logger.debug(f"Confidence ratio: {confidence_ratio:.3f}")

        return predictions

    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]:
        """
        アンサンブルモデルの評価

        Args:
            X: 特徴量データ
            y: 正解ラベル

        Returns:
            Dict[str, float]: 評価メトリクス.
        """
        try:
            # アンサンブル予測
            y_pred = self.predict(X, use_confidence=False)  # 閾値なしで評価
            y_pred_conf = self.predict(X, use_confidence=True)  # 閾値ありで評価

            # 基本メトリクス（閾値なし）
            metrics = {
                "accuracy": accuracy_score(y, y_pred),
                "precision": precision_score(y, y_pred, average="weighted", zero_division=0),
                "recall": recall_score(y, y_pred, average="weighted", zero_division=0),
                "f1_score": f1_score(y, y_pred, average="weighted", zero_division=0),
            }

            # confidence閾値適用時のメトリクス
            valid_mask = y_pred_conf != -1
            if valid_mask.sum() > 0:
                y_valid = y[valid_mask]
                y_pred_valid = y_pred_conf[valid_mask]

                metrics.update(
                    {
                        "confidence_coverage": valid_mask.sum() / len(y),
                        "confidence_accuracy": accuracy_score(y_valid, y_pred_valid),
                        "confidence_precision": precision_score(
                            y_valid,
                            y_pred_valid,
                            average="weighted",
                            zero_division=0,
                        ),
                    }
                )

            self.logger.info(f"📊 Ensemble evaluation completed")
            self.logger.info(f"Accuracy: {metrics['accuracy']:.3f}, F1: {metrics['f1_score']:.3f}")

            return metrics

        except Exception as e:
            self.logger.error(f"Ensemble evaluation failed: {e}")
            return {}

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        統合された特徴量重要度を取得

        Returns:
            pd.DataFrame: 重み付け平均された特徴量重要度.
        """
        if not self.is_fitted or not self.feature_names:
            return None

        try:
            importance_sum = np.zeros(len(self.feature_names))
            total_weight = 0.0

            # 各モデルの重要度を重み付けして統合
            for model_name, model in self.models.items():
                importance_df = model.get_feature_importance()
                if importance_df is not None:
                    weight = self.weights.get(model_name, 0.0)
                    importance_sum += importance_df["importance"].values * weight
                    total_weight += weight

            if total_weight == 0:
                return None

            # 正規化
            importance_sum /= total_weight

            # DataFrameとして整理
            ensemble_importance = pd.DataFrame(
                {"feature": self.feature_names, "importance": importance_sum}
            ).sort_values("importance", ascending=False)

            return ensemble_importance

        except Exception as e:
            self.logger.error(f"Failed to get ensemble feature importance: {e}")
            return None

    def save(self, filepath: Union[str, Path]) -> None:
        """
        アンサンブルモデルの保存

        Args:
            filepath: 保存先ディレクトリパス.
        """
        try:
            path = Path(filepath)
            path.mkdir(parents=True, exist_ok=True)

            # 各モデルを個別に保存
            for model_name, model in self.models.items():
                model_path = path / f"{model_name}_model.pkl"
                model.save(model_path)

            # アンサンブル設定を保存
            import joblib

            ensemble_config = {
                "weights": self.weights,
                "confidence_threshold": self.confidence_threshold,
                "feature_names": self.feature_names,
                "classes_": self.classes_,
                "is_fitted": self.is_fitted,
                "model_performance": self.model_performance,
            }

            config_path = path / "ensemble_config.pkl"
            joblib.dump(ensemble_config, config_path)

            self.logger.info(f"✅ EnsembleModel saved to {path}")

        except Exception as e:
            self.logger.error(f"Failed to save EnsembleModel: {e}")
            raise DataProcessingError(f"Model save failed: {e}")

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "EnsembleModel":
        """
        アンサンブルモデルの読み込み

        Args:
            filepath: 読み込み元ディレクトリパス

        Returns:
            EnsembleModel: 読み込んだアンサンブルモデル.
        """
        try:
            path = Path(filepath)

            # アンサンブル設定を読み込み
            import joblib

            config_path = path / "ensemble_config.pkl"
            ensemble_config = joblib.load(config_path)

            # 各モデルを読み込み
            models = {}
            for model_name in ["lgbm", "xgb", "rf"]:
                model_path = path / f"{model_name}_model.pkl"
                if model_path.exists():
                    if model_name == "lgbm":
                        models[model_name] = LGBMModel.load(model_path)
                    elif model_name == "xgb":
                        models[model_name] = XGBModel.load(model_path)
                    elif model_name == "rf":
                        models[model_name] = RFModel.load(model_path)

            # アンサンブルモデルを復元
            ensemble = cls(
                models=models,
                weights=ensemble_config["weights"],
                confidence_threshold=ensemble_config["confidence_threshold"],
            )

            # 状態を復元
            ensemble.feature_names = ensemble_config["feature_names"]
            ensemble.classes_ = ensemble_config["classes_"]
            ensemble.is_fitted = ensemble_config["is_fitted"]
            ensemble.model_performance = ensemble_config["model_performance"]

            logger = get_logger()
            logger.info(f"✅ EnsembleModel loaded from {path}")

            return ensemble

        except Exception as e:
            logger = get_logger()
            logger.error(f"Failed to load EnsembleModel from {filepath}: {e}")
            raise DataProcessingError(f"Model load failed: {e}")

    def _validate_training_data(self, X: pd.DataFrame, y: pd.Series) -> None:
        """学習データの妥当性チェック."""
        if X.empty or y.empty:
            raise ValueError("Training data is empty")

        if len(X) != len(y):
            raise ValueError(f"Feature and target length mismatch: {len(X)} vs {len(y)}")

        if len(X) < 50:  # アンサンブルには多めのデータが必要
            raise ValueError(f"Insufficient training data for ensemble: {len(X)} samples")

        # クラス数チェック
        n_classes = len(np.unique(y))
        if n_classes < 2:
            raise ValueError(f"Need at least 2 classes for classification, got {n_classes}")

    def get_model_info(self) -> Dict[str, any]:
        """アンサンブルモデルの情報を取得."""
        return {
            "ensemble_type": "soft_voting",
            "n_models": len(self.models),
            "model_names": list(self.models.keys()),
            "weights": self.weights,
            "confidence_threshold": self.confidence_threshold,
            "is_fitted": self.is_fitted,
            "n_features": len(self.feature_names) if self.feature_names else 0,
            "feature_names": self.feature_names,
            "classes": (self.classes_.tolist() if self.classes_ is not None else None),
            "model_performance": self.model_performance,
        }
