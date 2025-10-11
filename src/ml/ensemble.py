"""
統合アンサンブルシステム - Phase 38.4完了

EnsembleModel、VotingSystem、ProductionEnsemble機能を1つのファイルに統合。
重複コードを排除し、保守性とコードの可読性を向上。

Phase 38.4完了
"""

import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from ..core.config import get_threshold
from ..core.exceptions import DataProcessingError
from ..core.logger import get_logger
from .models import BaseMLModel, LGBMModel, RFModel, XGBModel


class VotingMethod(Enum):
    """投票方式の列挙型"""

    SOFT = "soft"  # 確率ベースの投票
    HARD = "hard"  # クラスベースの投票
    WEIGHTED = "weighted"  # 重み付け投票


class VotingSystem:
    """
    投票システム

    複数モデルの予測を統合するための投票メカニズムを提供。
    ソフト投票とハード投票の両方に対応。
    """

    def __init__(
        self,
        method: VotingMethod = VotingMethod.SOFT,
        weights: Optional[Dict[str, float]] = None,
    ):
        """
        投票システムの初期化

        Args:
            method: 投票方式（SOFT, HARD, WEIGHTED）
            weights: モデル重み辞書
        """
        self.method = method
        self.weights = weights or {}
        self.logger = get_logger()

        self.logger.info(f"✅ VotingSystem initialized with method: {method.value}")

    def vote(
        self,
        predictions: Dict[str, np.ndarray],
        probabilities: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        投票の実行

        Args:
            predictions: モデル別予測クラス辞書
            probabilities: モデル別予測確率辞書（ソフト投票用）

        Returns:
            Tuple[np.ndarray, np.ndarray]: (最終予測, 信頼度スコア)
        """
        try:
            if self.method == VotingMethod.SOFT:
                return self._soft_voting(probabilities or {})
            elif self.method == VotingMethod.HARD:
                return self._hard_voting(predictions)
            elif self.method == VotingMethod.WEIGHTED:
                return self._weighted_voting(predictions, probabilities)
            else:
                raise ValueError(f"Unsupported voting method: {self.method}")

        except Exception as e:
            self.logger.error(f"Voting failed: {e}")
            raise DataProcessingError(f"Voting process failed: {e}")

    def _soft_voting(self, probabilities: Dict[str, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """ソフト投票（確率ベース）"""
        if not probabilities:
            raise ValueError("Probabilities required for soft voting")

        avg_probabilities = self._average_probabilities(probabilities)
        predictions = np.argmax(avg_probabilities, axis=1)
        confidence = np.max(avg_probabilities, axis=1)

        return predictions, confidence

    def _hard_voting(self, predictions: Dict[str, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        """ハード投票（多数決）"""
        if not predictions:
            raise ValueError("Predictions required for hard voting")

        prediction_matrix = np.column_stack(list(predictions.values()))
        model_names = list(predictions.keys())

        final_predictions = []
        vote_agreement = []

        for i in range(prediction_matrix.shape[0]):
            votes = prediction_matrix[i, :]

            if self.weights:
                final_pred = self._weighted_hard_vote(votes, model_names)
            else:
                final_pred = self._simple_majority_vote(votes)

            agreement = np.sum(votes == final_pred) / len(votes)

            final_predictions.append(final_pred)
            vote_agreement.append(agreement)

        return np.array(final_predictions), np.array(vote_agreement)

    def _weighted_voting(
        self,
        predictions: Dict[str, np.ndarray],
        probabilities: Optional[Dict[str, np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """重み付け投票"""
        if probabilities:
            return self._weighted_soft_voting(probabilities)
        else:
            return self._hard_voting(predictions)

    def _weighted_soft_voting(
        self, probabilities: Dict[str, np.ndarray]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """重み付けソフト投票"""
        weighted_avg = self._average_probabilities(probabilities, use_weights=True)
        predictions = np.argmax(weighted_avg, axis=1)
        confidence = np.max(weighted_avg, axis=1)

        return predictions, confidence

    def _average_probabilities(
        self, probabilities: Dict[str, np.ndarray], use_weights: bool = False
    ) -> np.ndarray:
        """確率の平均化"""
        if not probabilities:
            raise ValueError("No probabilities provided")

        prob_arrays = list(probabilities.values())

        # 形状確認
        n_samples, n_classes = prob_arrays[0].shape
        for prob in prob_arrays[1:]:
            if prob.shape != (n_samples, n_classes):
                raise ValueError("All probability arrays must have the same shape")

        if use_weights and self.weights:
            # 重み付け平均
            weighted_sum = np.zeros((n_samples, n_classes))
            total_weight = 0.0

            for model_name, prob in probabilities.items():
                weight = self.weights.get(model_name, 1.0)
                weighted_sum += weight * prob
                total_weight += weight

            return weighted_sum / total_weight if total_weight > 0 else weighted_sum
        else:
            # 単純平均
            return np.mean(prob_arrays, axis=0)

    def _simple_majority_vote(self, votes: np.ndarray) -> int:
        """単純多数決"""
        unique_votes, counts = np.unique(votes, return_counts=True)
        majority_idx = np.argmax(counts)
        return unique_votes[majority_idx]

    def _weighted_hard_vote(self, votes: np.ndarray, model_names: List[str]) -> int:
        """重み付けハード投票"""
        unique_classes = np.unique(votes)
        class_weights = {}

        for cls in unique_classes:
            total_weight = 0.0
            for i, vote in enumerate(votes):
                if vote == cls:
                    model_name = model_names[i]
                    weight = self.weights.get(model_name, 1.0)
                    total_weight += weight
            class_weights[cls] = total_weight

        winning_class = max(class_weights, key=class_weights.get)
        return winning_class


class EnsembleModel:
    """
    アンサンブル分類モデル

    3つの強力なモデルを統合してロバストな予測を提供。
    重み付け投票とconfidence閾値による高精度予測。
    """

    def __init__(
        self,
        models: Optional[Dict[str, BaseMLModel]] = None,
        weights: Optional[Dict[str, float]] = None,
        confidence_threshold: Optional[float] = None,
    ):
        """
        アンサンブルモデルの初期化

        Args:
            models: 使用するモデル辞書（デフォルト: 3モデル自動作成）
            weights: モデル重み（デフォルト: 均等重み）
            confidence_threshold: 予測信頼度閾値
        """
        # confidence_thresholdを設定ファイルから取得
        if confidence_threshold is None:
            self.confidence_threshold = get_threshold("ml.confidence_threshold", 0.3)
        else:
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
        """デフォルトの3モデルを作成"""
        try:
            models = {"lgbm": LGBMModel(), "xgb": XGBModel(), "rf": RFModel()}
            self.logger.info("✅ Default models created successfully")
            return models
        except Exception as e:
            self.logger.error(f"❌ Failed to create default models: {e}")
            raise DataProcessingError(f"Model creation failed: {e}")

    def _normalize_weights(self) -> None:
        """重みの正規化（合計が1になるように調整）"""
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
            EnsembleModel: 学習済みアンサンブルモデル
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
            np.ndarray: 予測クラス
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
            np.ndarray: 予測確率（重み付け平均）
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
        """confidence閾値を適用した予測"""
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
            Dict[str, float]: 評価メトリクス
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
                            y_valid, y_pred_valid, average="weighted", zero_division=0
                        ),
                    }
                )

            self.logger.info("📊 Ensemble evaluation completed")
            self.logger.info(f"Accuracy: {metrics['accuracy']:.3f}, F1: {metrics['f1_score']:.3f}")

            return metrics

        except Exception as e:
            self.logger.error(f"Ensemble evaluation failed: {e}")
            return {}

    def save(self, filepath: Union[str, Path]) -> None:
        """アンサンブルモデルの保存"""
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
        """アンサンブルモデルの読み込み"""
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
        """学習データの妥当性チェック"""
        if X.empty or y.empty:
            raise ValueError("Training data is empty")

        if len(X) != len(y):
            raise ValueError(f"Feature and target length mismatch: {len(X)} vs {len(y)}")

        min_samples = get_threshold("ensemble.min_training_samples", 50)
        if len(X) < min_samples:  # アンサンブルには多めのデータが必要
            raise ValueError(
                f"Insufficient training data for ensemble: {len(X)} samples (minimum: {min_samples})"
            )

        # クラス数チェック
        n_classes = len(np.unique(y))
        if n_classes < 2:
            raise ValueError(f"Need at least 2 classes for classification, got {n_classes}")

    def get_model_info(self) -> Dict[str, any]:
        """アンサンブルモデルの情報を取得"""
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


class ProductionEnsemble:
    """
    本番用アンサンブルモデル（Phase 38.4時点で本番使用中）

    現在の目的：
    - scripts/ml/create_ml_models.pyで実使用中（週次自動学習）
    - 本番環境での安定動作を保証（ml_adapter/ml_loader/trading_cycle_manager）
    - models/production/production_ensemble.pkl として保存・読み込み

    将来の統合計画：
    - 新設計EnsembleModelへの段階的移行を想定
    - Phase 39以降で統合検討（現時点では削除不可）
    """

    def __init__(self, individual_models: Dict[str, Any]):
        """
        初期化

        Args:
            individual_models: 個別モデル辞書
        """
        self.models = individual_models
        self.model_names = list(individual_models.keys())

        # デフォルト重み（設定ファイルから取得）
        from ..core.config import get_threshold

        default_weights = get_threshold(
            "ensemble.weights",
            {
                "lightgbm": 0.4,
                "xgboost": 0.4,
                "random_forest": 0.2,
            },
        )
        self.weights = default_weights

        self.is_fitted = True
        # Phase 22: 特徴量定義一元化対応
        from ..core.config.feature_manager import get_feature_count, get_feature_names

        self.n_features_ = get_feature_count()
        self.feature_names = get_feature_names()

        # モデル数検証
        if len(self.models) == 0:
            raise ValueError("個別モデルが提供されていません")

    def predict(self, X) -> np.ndarray:
        """予測実行（重み付け投票）"""
        if hasattr(X, "values"):
            X_array = X.values
        else:
            X_array = X

        # 入力形状検証
        if X_array.shape[1] != self.n_features_:
            raise ValueError(f"特徴量数不一致: {X_array.shape[1]} != {self.n_features_}")

        # sklearn警告回避のため特徴量名付きDataFrameを作成
        import pandas as pd

        if not isinstance(X, pd.DataFrame):
            X_with_names = pd.DataFrame(X_array, columns=self.feature_names)
        else:
            X_with_names = X

        predictions = {}

        # 各モデルから予測取得
        for name, model in self.models.items():
            if hasattr(model, "predict"):
                pred = model.predict(X_with_names)
                predictions[name] = pred
            else:
                raise ValueError(f"モデル {name} にpredictメソッドがありません")

        # 重み付け平均計算
        ensemble_pred = np.zeros(len(X_array))
        total_weight = 0

        for name, pred in predictions.items():
            weight = self.weights.get(name, 1.0)
            ensemble_pred += pred * weight
            total_weight += weight

        # 最終予測（閾値0.5）
        return (ensemble_pred / total_weight > 0.5).astype(int)

    def predict_proba(self, X) -> np.ndarray:
        """予測確率（重み付け平均）"""
        if hasattr(X, "values"):
            X_array = X.values
        else:
            X_array = X

        # 入力形状検証
        if X_array.shape[1] != self.n_features_:
            raise ValueError(f"特徴量数不一致: {X_array.shape[1]} != {self.n_features_}")

        # sklearn警告回避のため特徴量名付きDataFrameを作成
        import pandas as pd

        if not isinstance(X, pd.DataFrame):
            X_with_names = pd.DataFrame(X_array, columns=self.feature_names)
        else:
            X_with_names = X

        probabilities = {}

        # 各モデルから確率取得
        for name, model in self.models.items():
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X_with_names)
                probabilities[name] = proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
            elif hasattr(model, "predict"):
                probabilities[name] = model.predict(X_with_names).astype(float)
            else:
                raise ValueError(f"モデル {name} に予測メソッドがありません")

        # 重み付け平均計算
        ensemble_proba = np.zeros(len(X))
        total_weight = 0

        for name, proba in probabilities.items():
            weight = self.weights.get(name, 1.0)
            ensemble_proba += proba * weight
            total_weight += weight

        final_proba = ensemble_proba / total_weight

        # [P(class=0), P(class=1)] 形式で返す
        return np.column_stack([1 - final_proba, final_proba])

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報取得"""
        return {
            "type": "ProductionEnsemble",
            "individual_models": self.model_names,
            "weights": self.weights.copy(),
            "n_features": self.n_features_,
            "feature_names": self.feature_names.copy(),
            "phase": "Phase 22",
            "status": "production_ready",
        }

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """重みの更新"""
        old_weights = self.weights.copy()
        self.weights.update(new_weights)

        # 重みの正規化
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {name: weight / total_weight for name, weight in self.weights.items()}

        print(f"重み更新: {old_weights} -> {self.weights}")

    def validate_predictions(self, X, y_true=None) -> Dict[str, Any]:
        """予測精度の検証"""
        predictions = self.predict(X)
        probabilities = self.predict_proba(X)

        validation_result = {
            "n_samples": len(X),
            "prediction_range": [int(predictions.min()), int(predictions.max())],
            "probability_range": [
                float(probabilities.min()),
                float(probabilities.max()),
            ],
            "buy_ratio": float(predictions.mean()),
            "avg_confidence": float(probabilities.max(axis=1).mean()),
        }

        if y_true is not None:
            from sklearn.metrics import accuracy_score, f1_score

            validation_result.update(
                {
                    "accuracy": float(accuracy_score(y_true, predictions)),
                    "f1_score": float(f1_score(y_true, predictions, average="weighted")),
                }
            )

        return validation_result

    def __repr__(self) -> str:
        """文字列表現"""
        return (
            f"ProductionEnsemble("
            f"models={len(self.models)}, "
            f"features={self.n_features_}, "
            f"weights={self.weights})"
        )
