"""
ベースモデル抽象クラス - Phase 12実装・CI/CD統合・手動実行監視・段階的デプロイ対応

全ての機械学習モデル（LightGBM、XGBoost、RandomForest）の
共通インターフェースを定義する抽象クラス。

レガシーシステムの複雑性を削減し、必要最小限の機能に特化。.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator

from ...core.exceptions import DataProcessingError
from ...core.logger import get_logger


class BaseMLModel(ABC):
    """
    機械学習モデルの基底クラス

    全ての個別モデルが実装すべき共通インターフェースを定義。
    シンプルで理解しやすい設計により、保守性を向上。.
    """

    def __init__(self, model_name: str, **kwargs):
        """
        ベースモデルの初期化

        Args:
            model_name: モデル識別名
            **kwargs: モデル固有のパラメータ.
        """
        self.model_name = model_name
        self.model_params = kwargs
        self.estimator = None
        self.is_fitted = False
        self.feature_names = None
        self.logger = get_logger()

        # モデル作成
        self.estimator = self._create_estimator(**kwargs)

    @abstractmethod
    def _create_estimator(self, **kwargs) -> BaseEstimator:
        """
        具体的なestimatorを作成（サブクラスで実装）

        Returns:
            BaseEstimator: sklearn互換のestimator.
        """
        pass

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BaseMLModel":
        """
        モデルの学習

        Args:
            X: 特徴量データ
            y: ターゲットデータ

        Returns:
            BaseMLModel: 学習済みモデル（メソッドチェーン用）.
        """
        try:
            self._validate_training_data(X, y)

            # 特徴量名を保存
            self.feature_names = X.columns.tolist()

            self.logger.info(
                f"Training {self.model_name} with {len(X)} samples, {len(X.columns)} features"
            )

            # 学習実行
            self.estimator.fit(X, y)
            self.is_fitted = True

            self.logger.info(f"✅ {self.model_name} training completed successfully")
            return self

        except Exception as e:
            self.logger.error(f"❌ {self.model_name} training failed: {e}")
            raise DataProcessingError(f"Model training failed: {e}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        予測値の取得

        Args:
            X: 特徴量データ

        Returns:
            np.ndarray: 予測クラス.
        """
        if not self.is_fitted:
            raise ValueError(f"{self.model_name} is not fitted. Call fit() first.")

        try:
            X_aligned = self._align_features(X)
            predictions = self.estimator.predict(X_aligned)
            return predictions

        except Exception as e:
            self.logger.error(f"Prediction failed for {self.model_name}: {e}")
            raise DataProcessingError(f"Prediction failed: {e}")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        確率予測の取得

        Args:
            X: 特徴量データ

        Returns:
            np.ndarray: 予測確率（各クラスの確率）.
        """
        if not self.is_fitted:
            raise ValueError(f"{self.model_name} is not fitted. Call fit() first.")

        try:
            X_aligned = self._align_features(X)

            if hasattr(self.estimator, "predict_proba"):
                probabilities = self.estimator.predict_proba(X_aligned)
                return probabilities
            else:
                # predict_probaがない場合は予測値を確率風に変換
                predictions = self.estimator.predict(X_aligned)
                n_samples = len(predictions)
                probabilities = np.zeros((n_samples, 2))
                probabilities[np.arange(n_samples), predictions] = 1.0
                return probabilities

        except Exception as e:
            self.logger.error(f"Probability prediction failed for {self.model_name}: {e}")
            raise DataProcessingError(f"Probability prediction failed: {e}")

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        特徴量重要度の取得

        Returns:
            pd.DataFrame: 特徴量重要度（重要度順にソート）.
        """
        if not self.is_fitted:
            self.logger.warning(f"{self.model_name} is not fitted. Cannot get feature importance.")
            return None

        if not self.feature_names:
            self.logger.warning("No feature names available")
            return None

        try:
            # モデル固有の重要度取得方法
            importance = self._get_model_importance()

            if importance is None:
                return None

            # DataFrameとして整理
            importance_df = pd.DataFrame(
                {"feature": self.feature_names, "importance": importance}
            ).sort_values("importance", ascending=False)

            return importance_df

        except Exception as e:
            self.logger.error(f"Failed to get feature importance for {self.model_name}: {e}")
            return None

    def save(self, filepath: Union[str, Path]) -> None:
        """
        モデルの保存

        Args:
            filepath: 保存先ファイルパス.
        """
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # モデル情報をまとめて保存
            model_data = {
                "model_name": self.model_name,
                "model_params": self.model_params,
                "estimator": self.estimator,
                "is_fitted": self.is_fitted,
                "feature_names": self.feature_names,
            }

            joblib.dump(model_data, path)
            self.logger.info(f"✅ {self.model_name} saved to {path}")

        except Exception as e:
            self.logger.error(f"Failed to save {self.model_name}: {e}")
            raise DataProcessingError(f"Model save failed: {e}")

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "BaseMLModel":
        """
        モデルの読み込み

        Args:
            filepath: 読み込み元ファイルパス

        Returns:
            BaseMLModel: 読み込んだモデル.
        """
        try:
            model_data = joblib.load(filepath)

            # モデルインスタンスを復元
            model = cls.__new__(cls)
            model.model_name = model_data["model_name"]
            model.model_params = model_data["model_params"]
            model.estimator = model_data["estimator"]
            model.is_fitted = model_data["is_fitted"]
            model.feature_names = model_data["feature_names"]
            model.logger = get_logger()

            model.logger.info(f"✅ {model.model_name} loaded from {filepath}")
            return model

        except Exception as e:
            logger = get_logger()
            logger.error(f"Failed to load model from {filepath}: {e}")
            raise DataProcessingError(f"Model load failed: {e}")

    def _validate_training_data(self, X: pd.DataFrame, y: pd.Series) -> None:
        """学習データの妥当性チェック."""
        # pandas/numpyの両方に対応したemptyチェック
        x_empty = X.empty if hasattr(X, "empty") else (len(X) == 0)
        y_empty = y.empty if hasattr(y, "empty") else (len(y) == 0)

        if x_empty or y_empty:
            raise ValueError("Training data is empty")

        if len(X) != len(y):
            raise ValueError(f"Feature and target length mismatch: {len(X)} vs {len(y)}")

        if len(X) < 10:
            raise ValueError(f"Insufficient training data: {len(X)} samples")

        # NaN値チェック（pandas/numpyの両方に対応）
        if hasattr(X, "isna"):
            x_nan_ratio = X.isna().sum().sum() / (len(X) * len(X.columns))
        else:
            import numpy as np

            x_nan_ratio = np.isnan(X).sum() / X.size

        if hasattr(y, "isna"):
            y_nan_ratio = y.isna().sum() / len(y)
        else:
            import numpy as np

            y_nan_ratio = np.isnan(y).sum() / len(y)

        if x_nan_ratio > 0.5:
            raise ValueError(f"Too many NaN values in features: {x_nan_ratio:.2%}")

        if y_nan_ratio > 0.3:
            raise ValueError(f"Too many NaN values in target: {y_nan_ratio:.2%}")

    def _align_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """特徴量の整合性確保."""
        if not self.feature_names:
            return X

        try:
            # 不足する特徴量を0で補完
            missing_features = set(self.feature_names) - set(X.columns)
            if missing_features:
                self.logger.warning(f"Adding missing features with zeros: {len(missing_features)}")
                for feature in missing_features:
                    X[feature] = 0.0

            # 余分な特徴量を削除
            extra_features = set(X.columns) - set(self.feature_names)
            if extra_features:
                self.logger.warning(f"Removing extra features: {len(extra_features)}")
                X = X.drop(columns=extra_features)

            # 順序を合わせる
            X = X[self.feature_names]

            return X

        except Exception as e:
            self.logger.error(f"Feature alignment failed: {e}")
            return X

    def _get_model_importance(self) -> Optional[np.ndarray]:
        """モデル固有の重要度取得（サブクラスでオーバーライド可能）."""
        if hasattr(self.estimator, "feature_importances_"):
            return self.estimator.feature_importances_
        elif hasattr(self.estimator, "coef_"):
            return np.abs(self.estimator.coef_[0])
        else:
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報の取得."""
        return {
            "model_name": self.model_name,
            "model_type": type(self.estimator).__name__,
            "is_fitted": self.is_fitted,
            "n_features": len(self.feature_names) if self.feature_names else 0,
            "feature_names": self.feature_names,
            "model_params": self.model_params,
        }
