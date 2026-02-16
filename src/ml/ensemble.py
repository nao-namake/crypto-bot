"""
本番用アンサンブルシステム - Phase 64.6

ProductionEnsemble: 本番環境で使用する3モデルアンサンブル予測クラス。
LightGBM・XGBoost・RandomForestの重み付け投票により安定した予測を提供。

Phase 64.6: 未使用クラス削除（VotingSystem・EnsembleModel・StackingEnsemble）
Phase 51.9: 3クラス分類対応
Phase 50.7: レベル別特徴量数対応
"""

from typing import Any, Dict

import numpy as np
import pandas as pd

from ..core.config import get_threshold
from ..core.config.feature_manager import get_feature_count, get_feature_names
from ..core.logger import get_logger


class ProductionEnsemble:
    """
    本番用アンサンブルモデル

    scripts/ml/create_ml_models.pyで週次自動学習。
    本番環境での安定動作を保証（ml_adapter/ml_loader/trading_cycle_manager）。
    ensemble_level1/2/3.pkl として保存・読み込み。
    """

    def __init__(self, individual_models: Dict[str, Any]):
        """
        初期化

        Args:
            individual_models: 個別モデル辞書
        """
        self.models = individual_models
        self.model_names = list(individual_models.keys())
        self.logger = get_logger()

        # デフォルト重み（設定ファイルから取得）
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
        # レベル別特徴量数対応 - 実際のモデルから特徴量数を取得
        detected_n_features = None
        for model_name, model in self.models.items():
            if hasattr(model, "n_features_in_"):
                detected_n_features = model.n_features_in_
                break
            elif hasattr(model, "_n_features"):
                detected_n_features = model._n_features
                break

        # モデルから検出できた場合はそれを使用、できない場合はフォールバック
        if detected_n_features is not None:
            self.n_features_ = detected_n_features
            # 特徴量名もレベルに応じて切り詰める
            all_feature_names = get_feature_names()
            self.feature_names = all_feature_names[: self.n_features_]
        else:
            # フォールバック: 全特徴量を使用（Level 1相当）
            self.n_features_ = get_feature_count()
            self.feature_names = get_feature_names()

        # モデル数検証
        if len(self.models) == 0:
            raise ValueError("個別モデルが提供されていません")

    def predict(self, X) -> np.ndarray:
        """予測実行（重み付け投票）

        3クラス分類対応:
        - predict_proba()を使用してクラス確率を取得
        - argmax()で最も確率の高いクラスを返す
        """
        probas = self.predict_proba(X)
        return np.argmax(probas, axis=1)

    def predict_proba(self, X) -> np.ndarray:
        """予測確率（重み付け平均）

        3クラス分類対応:
        - 各モデルの全クラス確率を保持
        - 重み付け平均で統合
        - 2クラス・3クラス両対応
        """
        if hasattr(X, "values"):
            X_array = X.values
        else:
            X_array = X

        # 入力形状検証
        if X_array.shape[1] != self.n_features_:
            raise ValueError(f"特徴量数不一致: {X_array.shape[1]} != {self.n_features_}")

        # sklearn警告回避のため特徴量名付きDataFrameを作成
        if not isinstance(X, pd.DataFrame):
            X_with_names = pd.DataFrame(X_array, columns=self.feature_names)
        else:
            X_with_names = X

        probabilities = {}
        n_classes = None

        # 各モデルから確率取得
        for name, model in self.models.items():
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X_with_names)
                probabilities[name] = proba
                if n_classes is None:
                    n_classes = proba.shape[1]
            elif hasattr(model, "predict"):
                # predict_probaがない場合はpredictを使用
                pred = model.predict(X_with_names).astype(int)
                # one-hot encoding
                proba = np.zeros((len(pred), n_classes if n_classes else 2))
                proba[np.arange(len(pred)), pred] = 1.0
                probabilities[name] = proba
            else:
                raise ValueError(f"モデル {name} に予測メソッドがありません")

        # 重み付け平均計算（全クラス確率を統合）
        ensemble_proba = np.zeros((len(X_array), n_classes))
        total_weight = 0

        for name, proba in probabilities.items():
            weight = self.weights.get(name, 1.0)
            ensemble_proba += proba * weight
            total_weight += weight

        final_proba = ensemble_proba / total_weight

        return final_proba

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

        self.logger.info(f"重み更新: {old_weights} -> {self.weights}")

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
