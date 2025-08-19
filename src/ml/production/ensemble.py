"""
本番用アンサンブルモデル - Phase 11実装・CI/CD統合・24時間監視・段階的デプロイ対応

個別MLモデル（LightGBM・XGBoost・RandomForest）を統合し、
実取引で使用する本番用アンサンブルモデルを提供。

特徴:
- 重み付け投票による予測統合・GitHub Actions対応
- pickle対応（独立モジュール）・CI/CD品質ゲート対応
- 12特徴量最適化システム対応・24時間監視対応・段階的デプロイ対応.
"""

from typing import Any, Dict, List

import numpy as np


class ProductionEnsemble:
    """
    本番用アンサンブルモデル

    複数の個別MLモデルを統合し、重み付け投票により
    最終的な予測を生成する本番用モデル。.
    """

    def __init__(self, individual_models: Dict[str, Any]):
        """
        初期化

        Args:
            individual_models: 個別モデル辞書.
        """
        self.models = individual_models
        self.model_names = list(individual_models.keys())

        # デフォルト重み（性能に基づく）
        self.weights = {
            "lightgbm": 0.4,  # 高いCV F1スコア
            "xgboost": 0.4,  # 高い精度
            "random_forest": 0.2,  # 安定性重視
        }

        self.is_fitted = True
        self.n_features_ = 12  # 新システム12特徴量

        # 新システム特徴量定義
        self.feature_names = [
            "close",
            "volume",
            "returns_1",
            "rsi_14",
            "macd",
            "macd_signal",
            "atr_14",
            "bb_position",
            "ema_20",
            "ema_50",
            "zscore",
            "volume_ratio",
        ]

        # モデル数検証
        if len(self.models) == 0:
            raise ValueError("個別モデルが提供されていません")

    def predict(self, X) -> np.ndarray:
        """
        予測実行（重み付け投票）

        Args:
            X: 特徴量データ（12特徴量）

        Returns:
            np.ndarray: 予測クラス（0 or 1）.
        """
        if hasattr(X, "values"):
            X = X.values

        # 入力形状検証
        if X.shape[1] != self.n_features_:
            raise ValueError(
                f"特徴量数不一致: {X.shape[1]} != {self.n_features_}"
            )

        predictions = {}

        # 各モデルから予測取得
        for name, model in self.models.items():
            if hasattr(model, "predict"):
                pred = model.predict(X)
                predictions[name] = pred
            else:
                raise ValueError(
                    f"モデル {name} にpredictメソッドがありません"
                )

        # 重み付け平均計算
        ensemble_pred = np.zeros(len(X))
        total_weight = 0

        for name, pred in predictions.items():
            weight = self.weights.get(name, 1.0)
            ensemble_pred += pred * weight
            total_weight += weight

        # 最終予測（閾値0.5）
        return (ensemble_pred / total_weight > 0.5).astype(int)

    def predict_proba(self, X) -> np.ndarray:
        """
        予測確率（重み付け平均）

        Args:
            X: 特徴量データ（12特徴量）

        Returns:
            np.ndarray: 予測確率 [[P(class=0), P(class=1)], ...].
        """
        if hasattr(X, "values"):
            X = X.values

        # 入力形状検証
        if X.shape[1] != self.n_features_:
            raise ValueError(
                f"特徴量数不一致: {X.shape[1]} != {self.n_features_}"
            )

        probabilities = {}

        # 各モデルから確率取得
        for name, model in self.models.items():
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba(X)
                # クラス1の確率を取得
                probabilities[name] = (
                    proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]
                )
            elif hasattr(model, "predict"):
                # predict_probaがない場合はpredictの結果を使用
                probabilities[name] = model.predict(X).astype(float)
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
        """
        モデル情報取得

        Returns:
            Dict[str, Any]: モデル詳細情報.
        """
        return {
            "type": "ProductionEnsemble",
            "individual_models": self.model_names,
            "weights": self.weights.copy(),
            "n_features": self.n_features_,
            "feature_names": self.feature_names.copy(),
            "phase": "Phase 11",
            "status": "production_ready",
        }

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """
        重みの更新

        Args:
            new_weights: 新しい重み辞書.
        """
        old_weights = self.weights.copy()
        self.weights.update(new_weights)

        # 重みの正規化
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {
                name: weight / total_weight
                for name, weight in self.weights.items()
            }

        print(f"重み更新: {old_weights} -> {self.weights}")

    def validate_predictions(self, X, y_true=None) -> Dict[str, Any]:
        """
        予測精度の検証

        Args:
            X: テストデータ
            y_true: 正解ラベル（オプション）

        Returns:
            Dict[str, Any]: 検証結果.
        """
        predictions = self.predict(X)
        probabilities = self.predict_proba(X)

        validation_result = {
            "n_samples": len(X),
            "prediction_range": [
                int(predictions.min()),
                int(predictions.max()),
            ],
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
                    "f1_score": float(
                        f1_score(y_true, predictions, average="weighted")
                    ),
                }
            )

        return validation_result

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"ProductionEnsemble("
            f"models={len(self.models)}, "
            f"features={self.n_features_}, "
            f"weights={self.weights})"
        )
