"""
統合MLモデル実装 - Phase 49完了

BaseMLModel基底クラスと個別モデル（LightGBM、XGBoost、RandomForest）を統合。
重複コードを排除し、保守性とコードの可読性を向上。

Phase 49完了
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

from ..core.config import get_threshold
from ..core.exceptions import DataProcessingError
from ..core.logger import get_logger


class BaseMLModel(ABC):
    """
    機械学習モデルの基底クラス

    全ての個別モデルが実装すべき共通インターフェースを定義。
    """

    def __init__(self, model_name: str, **kwargs):
        """
        ベースモデルの初期化

        Args:
            model_name: モデル識別名
            **kwargs: モデル固有のパラメータ
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
        """具体的なestimatorを作成（サブクラスで実装）"""
        pass

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BaseMLModel":
        """モデルの学習"""
        try:
            self._validate_training_data(X, y)
            self.feature_names = X.columns.tolist()

            self.logger.info(
                f"Training {self.model_name} with {len(X)} samples, {len(X.columns)} features"
            )

            self.estimator.fit(X, y)
            self.is_fitted = True

            self.logger.info(f"✅ {self.model_name} training completed successfully")
            return self

        except Exception as e:
            self.logger.error(f"❌ {self.model_name} training failed: {e}")
            raise DataProcessingError(f"Model training failed: {e}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """予測値の取得"""
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
        """確率予測の取得"""
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
                # Phase 51.9-6D: クラス数自動検出（3クラス想定）
                n_classes = len(np.unique(predictions))
                if n_classes < 2:
                    n_classes = 2  # 最小2クラス
                if n_classes != 3:
                    self.logger.warning(
                        f"Expected 3 classes but detected {n_classes} in predictions"
                    )
                probabilities = np.zeros((n_samples, n_classes))
                probabilities[np.arange(n_samples), predictions] = 1.0
                return probabilities

        except Exception as e:
            self.logger.error(f"Probability prediction failed for {self.model_name}: {e}")
            raise DataProcessingError(f"Probability prediction failed: {e}")

    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """特徴量重要度の取得"""
        if not self.is_fitted or not self.feature_names:
            return None

        try:
            importance = self._get_model_importance()
            if importance is None:
                return None

            importance_df = pd.DataFrame(
                {"feature": self.feature_names, "importance": importance}
            ).sort_values("importance", ascending=False)

            return importance_df

        except Exception as e:
            self.logger.error(f"Failed to get feature importance for {self.model_name}: {e}")
            return None

    def save(self, filepath: Union[str, Path]) -> None:
        """モデルの保存"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

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
        """モデルの読み込み"""
        try:
            model_data = joblib.load(filepath)

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

    def _validate_training_data(self, X, y) -> None:
        """学習データの妥当性チェック"""
        # NumPy配列とPandas両方に対応
        x_empty = (
            X.empty if hasattr(X, "empty") else (X.size == 0 if hasattr(X, "size") else len(X) == 0)
        )
        y_empty = (
            y.empty if hasattr(y, "empty") else (y.size == 0 if hasattr(y, "size") else len(y) == 0)
        )

        if x_empty or y_empty:
            raise ValueError("Training data is empty")

        if len(X) != len(y):
            raise ValueError(f"Feature and target length mismatch: {len(X)} vs {len(y)}")

        min_samples = get_threshold("models.min_training_samples", 10)
        if len(X) < min_samples:
            raise ValueError(
                f"Insufficient training data: {len(X)} samples (minimum: {min_samples})"
            )

        # NaN値チェック（NumPy配列とPandas両方に対応）
        if hasattr(X, "isna"):
            # Pandas DataFrame
            x_nan_ratio = X.isna().sum().sum() / (len(X) * len(X.columns))
        else:
            # NumPy配列
            import numpy as np

            x_nan_ratio = np.isnan(X).sum() / X.size if X.size > 0 else 0

        if hasattr(y, "isna"):
            # Pandas Series
            y_nan_ratio = y.isna().sum() / len(y)
        else:
            # NumPy配列
            import numpy as np

            y_nan_ratio = np.isnan(y).sum() / len(y) if len(y) > 0 else 0

        max_nan_features = get_threshold("ensemble.max_nan_ratio_features", 0.5)
        max_nan_target = get_threshold("ensemble.max_nan_ratio_target", 0.3)

        if x_nan_ratio > max_nan_features:
            raise ValueError(
                f"Too many NaN values in features: {x_nan_ratio:.2%} (max: {max_nan_features:.2%})"
            )
        if y_nan_ratio > max_nan_target:
            raise ValueError(
                f"Too many NaN values in target: {y_nan_ratio:.2%} (max: {max_nan_target:.2%})"
            )

    def _align_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """特徴量の整合性確保"""
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
        """モデル固有の重要度取得"""
        if hasattr(self.estimator, "feature_importances_"):
            return self.estimator.feature_importances_
        elif hasattr(self.estimator, "coef_"):
            return np.abs(self.estimator.coef_[0])
        else:
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報の取得"""
        return {
            "model_name": self.model_name,
            "model_type": type(self.estimator).__name__,
            "is_fitted": self.is_fitted,
            "n_features": len(self.feature_names) if self.feature_names else 0,
            "feature_names": self.feature_names,
            "model_params": self.model_params,
        }


class LGBMModel(BaseMLModel):
    """LightGBM分類モデル"""

    def __init__(self, **kwargs):
        """
        LightGBMモデルの初期化

        Phase 60.5: 設定ファイルからシード値を取得（モデル差別化対応）
        """
        # デフォルトパラメータ（設定ファイルから取得）
        config_params = get_threshold("models.lgbm", {})
        # Phase 51.9-6D: 3クラス専用（デフォルトをmulticlassに変更）
        default_params = {
            "objective": config_params.get("objective", "multiclass"),
            "num_class": config_params.get("num_class", 3),
            "boosting_type": "gbdt",
            "verbose": -1,
            **config_params,  # 設定ファイルの値で上書き
        }

        merged_params = {**default_params, **kwargs}

        # Phase 60.5: シード値設定（kwargs > 設定ファイル > 環境変数 > デフォルト）
        if "random_state" in kwargs:
            seed = kwargs["random_state"]  # kwargsで明示的に指定された場合はそれを使用
        else:
            seed = config_params.get("random_state", int(os.environ.get("CRYPTO_BOT_SEED", 42)))
        merged_params.update(
            {
                "random_state": seed,
                "seed": seed,
                "feature_fraction_seed": seed,
                "bagging_seed": seed,
                "data_random_seed": seed,
            }
        )

        super().__init__(model_name="LightGBM", **merged_params)

    def _create_estimator(self, **kwargs) -> BaseEstimator:
        """LightGBM estimatorの作成"""
        try:
            clean_params = self._clean_lgbm_params(kwargs)
            estimator = LGBMClassifier(**clean_params)
            self.logger.info(f"✅ LightGBM estimator created with {len(clean_params)} parameters")
            return estimator
        except Exception as e:
            self.logger.error(f"❌ Failed to create LightGBM estimator: {e}")
            raise

    def _clean_lgbm_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """LightGBMパラメータのクリーンアップ"""
        clean_params = params.copy()

        # レガシーパラメータ名の変換
        param_mapping = {
            "reg_alpha": "lambda_l1",
            "reg_lambda": "lambda_l2",
            "subsample": "bagging_fraction",
        }

        for old_param, new_param in param_mapping.items():
            if old_param in clean_params:
                if new_param not in clean_params:
                    clean_params[new_param] = clean_params[old_param]
                del clean_params[old_param]

        # デフォルト値の削除
        default_removals = {
            "bagging_fraction": 1.0,
            "feature_fraction": 1.0,
            "lambda_l1": 0.0,
            "lambda_l2": 0.0,
        }

        for param, default_value in default_removals.items():
            if param in clean_params and clean_params[param] == default_value:
                del clean_params[param]

        return clean_params

    def get_model_info(self) -> Dict[str, Any]:
        """LightGBM固有の情報を含むモデル情報"""
        base_info = super().get_model_info()

        lgbm_info = {
            "boosting_type": self.model_params.get("boosting_type", "gbdt"),
            "num_leaves": self.model_params.get("num_leaves", 31),
            "learning_rate": self.model_params.get("learning_rate", 0.05),
            "n_estimators": self.model_params.get("n_estimators", 100),
        }

        # 学習済みの場合は追加情報
        if self.is_fitted and hasattr(self.estimator, "best_iteration"):
            lgbm_info["best_iteration"] = self.estimator.best_iteration

        return {**base_info, "lgbm_specific": lgbm_info}


class XGBModel(BaseMLModel):
    """XGBoost分類モデル"""

    def __init__(self, **kwargs):
        """
        XGBoostモデルの初期化

        Phase 60.5: 設定ファイルからシード値を取得（モデル差別化対応）
        """
        # デフォルトパラメータ（設定ファイルから取得）
        config_params = get_threshold("models.xgb", {})
        # Phase 51.9-6D: 3クラス専用（デフォルトをmulti:softprobに変更）
        default_params = {
            "objective": config_params.get("objective", "multi:softprob"),
            "num_class": config_params.get("num_class", 3),
            "verbosity": 0,
            "eval_metric": config_params.get("eval_metric", "mlogloss"),
            "use_label_encoder": False,
            "tree_method": "hist",
            "grow_policy": "depthwise",
            **config_params,  # 設定ファイルの値で上書き
        }

        merged_params = {**default_params, **kwargs}

        # Phase 60.5: シード値設定（kwargs > 設定ファイル > 環境変数 > デフォルト）
        if "random_state" in kwargs:
            seed = kwargs["random_state"]  # kwargsで明示的に指定された場合はそれを使用
        else:
            seed = config_params.get("random_state", int(os.environ.get("CRYPTO_BOT_SEED", 123)))
        merged_params.update({"random_state": seed, "seed": seed})

        super().__init__(model_name="XGBoost", **merged_params)

    def _create_estimator(self, **kwargs) -> BaseEstimator:
        """XGBoost estimatorの作成"""
        try:
            clean_params = self._clean_xgb_params(kwargs)
            estimator = XGBClassifier(**clean_params)
            self.logger.info(f"✅ XGBoost estimator created with {len(clean_params)} parameters")
            return estimator
        except Exception as e:
            self.logger.error(f"❌ Failed to create XGBoost estimator: {e}")
            raise

    def _clean_xgb_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """XGBoostパラメータのクリーンアップ"""
        clean_params = params.copy()

        # 非推奨パラメータの除去
        deprecated_params = ["silent", "nthread"]

        for param in deprecated_params:
            if param in clean_params:
                del clean_params[param]
                self.logger.warning(f"Removed deprecated XGBoost parameter: {param}")

        # パラメータ名の正規化
        if "silent" in clean_params:
            if "verbosity" not in clean_params:
                clean_params["verbosity"] = 0 if clean_params["silent"] else 1
            del clean_params["silent"]

        if "nthread" in clean_params:
            if "n_jobs" not in clean_params:
                clean_params["n_jobs"] = clean_params["nthread"]
            del clean_params["nthread"]

        # 警告抑制設定
        if "use_label_encoder" not in clean_params:
            clean_params["use_label_encoder"] = False

        return clean_params

    def get_model_info(self) -> Dict[str, Any]:
        """XGBoost固有の情報を含むモデル情報"""
        base_info = super().get_model_info()

        xgb_info = {
            "objective": self.model_params.get("objective", "binary:logistic"),
            "max_depth": self.model_params.get("max_depth", 6),
            "learning_rate": self.model_params.get("learning_rate", 0.05),
            "n_estimators": self.model_params.get("n_estimators", 100),
            "subsample": self.model_params.get("subsample", 0.8),
            "colsample_bytree": self.model_params.get("colsample_bytree", 0.8),
        }

        # 学習済みの場合は追加情報
        if self.is_fitted and hasattr(self.estimator, "best_iteration"):
            xgb_info["best_iteration"] = self.estimator.best_iteration
        if self.is_fitted and hasattr(self.estimator, "best_score"):
            xgb_info["best_score"] = self.estimator.best_score

        return {**base_info, "xgb_specific": xgb_info}


class RFModel(BaseMLModel):
    """RandomForest分類モデル"""

    def __init__(self, **kwargs):
        """
        RandomForestモデルの初期化

        Phase 60.5: 設定ファイルからシード値を取得（モデル差別化対応）
        """
        # デフォルトパラメータ（設定ファイルから取得）
        config_params = get_threshold("models.rf", {})
        default_params = {
            "n_jobs": 1,  # Python 3.13 Parallel処理エラー回避のため単一スレッド化
            "warm_start": False,
            "max_samples": None,
            "criterion": "gini",
            "min_weight_fraction_leaf": 0.0,
            "max_leaf_nodes": None,
            "min_impurity_decrease": 0.0,
            "ccp_alpha": 0.0,
            **config_params,  # 設定ファイルの値で上書き
        }

        merged_params = {**default_params, **kwargs}

        # Phase 60.5: シード値設定（kwargs > 設定ファイル > 環境変数 > デフォルト）
        if "random_state" in kwargs:
            seed = kwargs["random_state"]  # kwargsで明示的に指定された場合はそれを使用
        else:
            seed = config_params.get("random_state", int(os.environ.get("CRYPTO_BOT_SEED", 456)))
        merged_params["random_state"] = seed

        super().__init__(model_name="RandomForest", **merged_params)

    def _create_estimator(self, **kwargs) -> BaseEstimator:
        """RandomForest estimatorの作成"""
        try:
            clean_params = self._clean_rf_params(kwargs)
            estimator = RandomForestClassifier(**clean_params)
            self.logger.info(
                f"✅ RandomForest estimator created with {len(clean_params)} parameters"
            )
            return estimator
        except Exception as e:
            self.logger.error(f"❌ Failed to create RandomForest estimator: {e}")
            raise

    def _clean_rf_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """RandomForestパラメータのクリーンアップ"""
        clean_params = params.copy()

        # scikit-learn バージョン互換性チェック
        try:
            from sklearn import __version__

            sklearn_version = tuple(map(int, __version__.split(".")[:2]))

            # scikit-learn 1.2 未満ではmonotonic_cstを除去
            if sklearn_version < (1, 2) and "monotonic_cst" in clean_params:
                del clean_params["monotonic_cst"]
                self.logger.info(
                    "Removed monotonic_cst parameter (unsupported in this sklearn version)"
                )

        except Exception as e:
            self.logger.warning(f"Could not check sklearn version: {e}")

        # パラメータ検証
        if "max_features" in clean_params:
            max_features = clean_params["max_features"]
            if isinstance(max_features, str) and max_features not in [
                "sqrt",
                "log2",
                "auto",
            ]:
                self.logger.warning(f"Invalid max_features: {max_features}, using 'sqrt'")
                clean_params["max_features"] = "sqrt"

        # n_estimators の最小値チェック
        if "n_estimators" in clean_params and clean_params["n_estimators"] < 1:
            self.logger.warning(f"n_estimators too small: {clean_params['n_estimators']}, using 10")
            clean_params["n_estimators"] = 10

        return clean_params

    def get_oob_score(self) -> float:
        """Out-of-bag scoreの取得"""
        if not self.is_fitted:
            self.logger.warning("Model is not fitted. Cannot get OOB score.")
            return 0.0

        if hasattr(self.estimator, "oob_score_"):
            return float(self.estimator.oob_score_)
        else:
            self.logger.warning("OOB score not available (oob_score=False)")
            return 0.0

    def get_tree_count(self) -> int:
        """決定木の数を取得"""
        if not self.is_fitted:
            return self.model_params.get("n_estimators", 0)

        if hasattr(self.estimator, "n_estimators_"):
            return self.estimator.n_estimators_
        else:
            return len(getattr(self.estimator, "estimators_", []))

    def get_model_info(self) -> Dict[str, Any]:
        """RandomForest固有の情報を含むモデル情報"""
        base_info = super().get_model_info()

        rf_info = {
            "n_estimators": self.model_params.get("n_estimators", 100),
            "max_depth": self.model_params.get("max_depth", 10),
            "max_features": self.model_params.get("max_features", "sqrt"),
            "class_weight": self.model_params.get("class_weight", "balanced"),
            "bootstrap": self.model_params.get("bootstrap", True),
            "oob_score_enabled": self.model_params.get("oob_score", True),
        }

        # 学習済みの場合は追加情報
        if self.is_fitted:
            rf_info["actual_tree_count"] = self.get_tree_count()
            rf_info["oob_score"] = self.get_oob_score()

        return {**base_info, "rf_specific": rf_info}
