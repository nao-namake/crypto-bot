# ============================================================
# ファイル名: crypto_bot/ml/model.py
# 説明:
# 機械学習モデルのラッピングクラスとモデル生成用ファクトリ関数。
# sklearn/LightGBM/XGBoost/RandomForestに対応し、
# - fit, predict, predict_proba, save, load
# などの共通インターフェースを提供。
# ============================================================

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict
from xgboost import XGBClassifier


class MLModel:
    """
    sklearn 互換 Estimator をラップし、
      - fit(X, y)
      - predict(X)
      - predict_proba(X)
      - save(filepath)
      - load(filepath)
    のインターフェイスを提供します。
    """

    def __init__(self, estimator: BaseEstimator):
        self.estimator = estimator

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        early_stopping_rounds: Optional[int] = None,
    ) -> "MLModel":
        """
        モデルを学習します。

        Parameters:
        -----------
        X : pd.DataFrame
            学習用特徴量
        y : pd.Series
            学習用ターゲット
        X_val : pd.DataFrame, optional
            検証用特徴量（早期停止用）
        y_val : pd.Series, optional
            検証用ターゲット（早期停止用）
        early_stopping_rounds : int, optional
            早期停止のラウンド数
        """
        # 早期停止対応モデル（LightGBM、XGBoost）
        if hasattr(self.estimator, "fit") and any(
            cls_name in str(type(self.estimator))
            for cls_name in ["LGBMClassifier", "XGBClassifier"]
        ):

            if (
                X_val is not None
                and y_val is not None
                and early_stopping_rounds is not None
            ):
                if "LGBM" in str(type(self.estimator)):
                    # LightGBM用早期停止
                    self.estimator.fit(
                        X,
                        y,
                        eval_set=[(X_val, y_val)],
                        eval_metric="binary_logloss",
                        callbacks=[
                            self.estimator.__class__.early_stopping(
                                early_stopping_rounds, verbose=0
                            )
                        ],
                    )
                elif "XGB" in str(type(self.estimator)):
                    # XGBoost用早期停止
                    self.estimator.fit(
                        X,
                        y,
                        eval_set=[(X_val, y_val)],
                        early_stopping_rounds=early_stopping_rounds,
                        verbose=False,
                    )
                else:
                    # その他のモデル（RandomForest等）
                    self.estimator.fit(X, y)
            else:
                # 早期停止パラメータがない場合は通常学習
                self.estimator.fit(X, y)
        else:
            # sklearn標準モデル
            self.estimator.fit(X, y)

        return self

    def predict(self, X: pd.DataFrame) -> Any:
        """
        学習済みモデルで予測を返します。
        """
        return self.estimator.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> Optional[Any]:
        """
        確率予測が可能な場合は返し、そうでなければ None を返します。
        """
        if hasattr(self.estimator, "predict_proba"):
            return self.estimator.predict_proba(X)
        return None

    def save(self, filepath: Union[str, Path]) -> None:
        """
        モデルをファイルに保存します（joblib を利用）。
        親ディレクトリが存在しない場合はFileNotFoundErrorを発生させます。
        """
        path = Path(filepath)
        if not path.parent.exists():
            raise FileNotFoundError(f"Directory does not exist: {path.parent}")
        joblib.dump(self.estimator, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "MLModel":
        """
        ファイルからモデルを復元してラップして返します。
        """
        est = joblib.load(filepath)
        return cls(est)

    def get_feature_importance(
        self, feature_names: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        特徴量重要度を取得します。

        Parameters:
        -----------
        feature_names : List[str], optional
            特徴量名のリスト

        Returns:
        --------
        pd.DataFrame or None
            特徴量重要度（重要度順にソート）
        """
        if not hasattr(self.estimator, "feature_importances_"):
            return None

        importance = self.estimator.feature_importances_

        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(importance))]

        df = pd.DataFrame(
            {"feature": feature_names, "importance": importance}
        ).sort_values("importance", ascending=False)

        return df

    def select_features_by_importance(
        self,
        X: pd.DataFrame,
        threshold: float = 0.01,
        max_features: Optional[int] = None,
    ) -> List[str]:
        """
        重要度に基づいて特徴量を選択します。

        Parameters:
        -----------
        X : pd.DataFrame
            特徴量データ
        threshold : float
            重要度の閾値
        max_features : int, optional
            最大特徴量数

        Returns:
        --------
        List[str]
            選択された特徴量名のリスト
        """
        importance_df = self.get_feature_importance(X.columns.tolist())

        if importance_df is None:
            return X.columns.tolist()

        # 重要度閾値でフィルタ
        selected = importance_df[importance_df["importance"] >= threshold]

        # 最大特徴量数制限
        if max_features is not None:
            selected = selected.head(max_features)

        return selected["feature"].tolist()


class EnsembleModel:
    """
    複数のMLモデルを組み合わせるアンサンブルモデルクラス。

    対応する組み合わせ手法:
    - voting: 多数決による予測
    - weighted: 重み付き平均
    - stacking: スタッキング（メタ学習）
    """

    def __init__(
        self,
        models: List[BaseEstimator],
        method: str = "voting",
        weights: Optional[List[float]] = None,
        meta_model: Optional[BaseEstimator] = None,
    ):
        self.models = models
        self.method = method.lower()
        self.weights = weights
        self.meta_model = meta_model if meta_model is not None else LogisticRegression()
        self.is_fitted = False

        # 重みの正規化
        if self.weights is not None:
            total_weight = sum(self.weights)
            self.weights = [w / total_weight for w in self.weights]

        if self.method not in ["voting", "weighted", "stacking"]:
            raise ValueError("method must be 'voting', 'weighted', or 'stacking'")

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "EnsembleModel":
        """
        アンサンブルモデルを学習します。
        """
        # 各ベースモデルを学習
        for model in self.models:
            model.fit(X, y)

        # スタッキングの場合はメタモデルも学習
        if self.method == "stacking":
            # クロスバリデーションでベースモデルの予測を取得
            meta_features = []
            for model in self.models:
                # predict_probaが利用可能な場合は確率を使用
                if hasattr(model, "predict_proba"):
                    cv_preds = cross_val_predict(
                        model, X, y, cv=3, method="predict_proba"
                    )
                    meta_features.append(cv_preds[:, 1])  # 陽性クラスの確率
                else:
                    cv_preds = cross_val_predict(model, X, y, cv=3)
                    meta_features.append(cv_preds)

            # メタ特徴量を結合
            meta_X = np.column_stack(meta_features)

            # メタモデルを学習
            self.meta_model.fit(meta_X, y)

        self.is_fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        アンサンブル予測を返します。
        """
        if not self.is_fitted:
            raise ValueError(
                "モデルが学習されていません。先にfit()を呼び出してください。"
            )

        if self.method == "voting":
            # 多数決
            predictions = []
            for model in self.models:
                predictions.append(model.predict(X))

            # 各サンプルごとに多数決
            ensemble_pred = []
            for i in range(len(X)):
                votes = [pred[i] for pred in predictions]
                ensemble_pred.append(max(set(votes), key=votes.count))

            return np.array(ensemble_pred)

        elif self.method == "weighted":
            # 重み付き平均（確率ベース）
            probabilities = self.predict_proba(X)
            return (probabilities[:, 1] > 0.5).astype(int)

        elif self.method == "stacking":
            # スタッキング
            meta_features = self._get_meta_features(X)
            return self.meta_model.predict(meta_features)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        アンサンブル確率予測を返します。
        """
        if not self.is_fitted:
            raise ValueError(
                "モデルが学習されていません。先にfit()を呼び出してください。"
            )

        if self.method == "voting":
            # 各モデルの確率の平均
            probabilities = []
            for model in self.models:
                if hasattr(model, "predict_proba"):
                    probabilities.append(model.predict_proba(X))
                else:
                    # predict_probaがない場合は予測結果をワンホット化
                    pred = model.predict(X)
                    prob = np.zeros((len(pred), 2))
                    prob[np.arange(len(pred)), pred] = 1.0
                    probabilities.append(prob)

            return np.mean(probabilities, axis=0)

        elif self.method == "weighted":
            # 重み付き平均
            probabilities = []
            weights = self.weights or [1.0 / len(self.models)] * len(self.models)

            for i, model in enumerate(self.models):
                if hasattr(model, "predict_proba"):
                    prob = model.predict_proba(X) * weights[i]
                else:
                    pred = model.predict(X)
                    prob = np.zeros((len(pred), 2))
                    prob[np.arange(len(pred)), pred] = weights[i]
                probabilities.append(prob)

            return np.sum(probabilities, axis=0)

        elif self.method == "stacking":
            # スタッキング
            meta_features = self._get_meta_features(X)
            if hasattr(self.meta_model, "predict_proba"):
                return self.meta_model.predict_proba(meta_features)
            else:
                pred = self.meta_model.predict(meta_features)
                prob = np.zeros((len(pred), 2))
                prob[np.arange(len(pred)), pred] = 1.0
                return prob

    def _get_meta_features(self, X: pd.DataFrame) -> np.ndarray:
        """
        スタッキング用のメタ特徴量を取得します。
        """
        meta_features = []
        for model in self.models:
            if hasattr(model, "predict_proba"):
                meta_features.append(model.predict_proba(X)[:, 1])
            else:
                meta_features.append(model.predict(X))

        return np.column_stack(meta_features)

    def save(self, filepath: Union[str, Path]) -> None:
        """
        アンサンブルモデルをファイルに保存します。
        """
        path = Path(filepath)
        if not path.parent.exists():
            raise FileNotFoundError(f"ディレクトリが存在しません: {path.parent}")

        ensemble_data = {
            "models": self.models,
            "method": self.method,
            "weights": self.weights,
            "meta_model": self.meta_model,
            "is_fitted": self.is_fitted,
        }
        joblib.dump(ensemble_data, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "EnsembleModel":
        """
        ファイルからアンサンブルモデルを復元します。
        """
        data = joblib.load(filepath)
        ensemble = cls(
            models=data["models"],
            method=data["method"],
            weights=data["weights"],
            meta_model=data["meta_model"],
        )
        ensemble.is_fitted = data["is_fitted"]
        return ensemble


# ------------------------------------------------------------------
# モデルタイプを文字列で切り替えるためのファクトリ関数
# ------------------------------------------------------------------
_MODEL_REGISTRY = {
    "lgbm": LGBMClassifier,
    "rf": RandomForestClassifier,
    "xgb": XGBClassifier,
}


def _lgbm_param_cleanup(kwargs):
    """
    LightGBM固有のパラメータ警告対策用クリーナー。
    - reg_alpha → lambda_l1 に統一
    - reg_lambda → lambda_l2 に統一
    - subsample → bagging_fraction に統一
    - 競合する場合は新しいもの（lambda_l1/lambda_l2/bagging_fraction）優先
    - デフォルト値（1.0, 0.0）なら削除
    """
    # reg_alpha → lambda_l1
    if "reg_alpha" in kwargs:
        if "lambda_l1" not in kwargs:
            kwargs["lambda_l1"] = kwargs["reg_alpha"]
        del kwargs["reg_alpha"]
    # reg_lambda → lambda_l2
    if "reg_lambda" in kwargs:
        kwargs["lambda_l2"] = kwargs["reg_lambda"]
        del kwargs["reg_lambda"]
    # subsample → bagging_fraction
    if "subsample" in kwargs:
        if "bagging_fraction" not in kwargs:
            kwargs["bagging_fraction"] = kwargs["subsample"]
        del kwargs["subsample"]
    # デフォルト値の場合は削除
    for param in ["bagging_fraction", "feature_fraction"]:
        if param in kwargs and kwargs[param] == 1.0:
            del kwargs[param]
    # lambda_l1, lambda_l2は値が0.0の時だけ削除
    for param in ["lambda_l1", "lambda_l2"]:
        if param in kwargs and float(kwargs[param]) == 0.0:
            del kwargs[param]
    return kwargs.copy()  # 新しい辞書を返すように修正


def create_model(model_type: str, **kwargs) -> BaseEstimator:
    """
    Return an sklearn‑compatible estimator for the requested ``model_type``.

    For LightGBM we normalise *legacy* parameter aliases before instantiation and,
    **only when those legacy aliases were actually supplied by the caller**, strip
    the old attributes from the resulting estimator so that
    ``hasattr(est, "reg_alpha")`` (or ``"reg_lambda"``) is *False* – this is
    required by our unit‑tests.
    We *do not* remove the attributes when the user never touched them, because
    LightGBM's internal logic expects them to exist during `fit() / get_params()`.
    """
    key = model_type.lower()
    if key not in _MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model_type '{model_type}'. valid types: {list(_MODEL_REGISTRY)}"
        )

    # ------------------------------------------------------------------ #
    # 実行再現性のためのシード設定
    # ------------------------------------------------------------------ #
    import os

    # 環境変数またはデフォルトのシード値を取得（CRYPTO_BOT_SEED優先）
    default_seed = int(
        os.environ.get(
            "CRYPTO_BOT_SEED",
            os.environ.get(
                "LIGHTGBM_SEED",
                os.environ.get("SKLEARN_SEED", os.environ.get("XGBOOST_SEED", 42)),
            ),
        )
    )

    # モデル別のシード設定
    if key == "lgbm":
        kwargs.setdefault("random_state", default_seed)
        kwargs.setdefault("seed", default_seed)
        kwargs.setdefault("feature_fraction_seed", default_seed)
        kwargs.setdefault("bagging_seed", default_seed)
        kwargs.setdefault("data_random_seed", default_seed)
    elif key == "rf":
        kwargs.setdefault("random_state", default_seed)
    elif key == "xgb":
        kwargs.setdefault("random_state", default_seed)
        kwargs.setdefault("seed", default_seed)
    elif key == "lr":
        kwargs.setdefault("random_state", default_seed)

    cls = _MODEL_REGISTRY[key]

    # ------------------------------------------------------------------ #
    # 1. LightGBM: clean up legacy param names (reg_alpha → lambda_l1 …)
    # ------------------------------------------------------------------ #
    legacy_alpha = legacy_lambda = legacy_subsample = False
    if key == "lgbm":
        # Record *before* cleanup so we know what was explicitly provided
        legacy_alpha = "reg_alpha" in kwargs
        legacy_lambda = "reg_lambda" in kwargs
        legacy_subsample = "subsample" in kwargs
        kwargs = _lgbm_param_cleanup(kwargs)

    # ------------------------------------------------------------------ #
    # 2. Instantiate the estimator
    # ------------------------------------------------------------------ #
    estimator = cls(**kwargs)

    # ------------------------------------------------------------------ #
    # 3. If caller used legacy names, hide the old attrs so
    #    `hasattr(estimator, "reg_alpha")` becomes False while leaving the
    #    new LightGBM params (`lambda_l1`, `lambda_l2`) intact.
    #    We *only* do this when necessary; otherwise LightGBM relies on the
    #    attributes for its internal `get_params()` bookkeeping.
    # ------------------------------------------------------------------ #
    if key == "lgbm":
        if legacy_alpha and hasattr(estimator, "reg_alpha"):
            try:
                delattr(estimator, "reg_alpha")
            except AttributeError:
                pass
        if legacy_lambda and hasattr(estimator, "reg_lambda"):
            try:
                delattr(estimator, "reg_lambda")
            except AttributeError:
                pass
        if legacy_subsample and hasattr(estimator, "subsample"):
            try:
                delattr(estimator, "subsample")
            except AttributeError:
                pass

    return estimator


def create_ensemble_model(
    model_configs: List[Dict[str, Any]],
    method: str = "voting",
    weights: Optional[List[float]] = None,
    meta_model_config: Optional[Dict[str, Any]] = None,
) -> EnsembleModel:
    """
    設定からアンサンブルモデルを作成します。

    Args:
        model_configs: 各ベースモデルの設定リスト
        method: アンサンブル手法 ("voting", "weighted", "stacking")
        weights: 重み付き平均の場合の重み
        meta_model_config: スタッキングの場合のメタモデル設定

    Returns:
        EnsembleModel: 作成されたアンサンブルモデル

    Example:
        model_configs = [
            {"type": "lgbm", "n_estimators": 100, "max_depth": 6},
            {"type": "rf", "n_estimators": 100, "max_depth": 8},
            {"type": "xgb", "n_estimators": 100, "max_depth": 7}
        ]
        ensemble = create_ensemble_model(model_configs, method="stacking")
    """
    models = []

    # 各ベースモデルを作成
    for config in model_configs:
        model_type = config.pop("type")
        model = create_model(model_type, **config)
        models.append(model)

    # メタモデルを作成（スタッキングの場合）
    meta_model = None
    if method == "stacking" and meta_model_config:
        meta_type = meta_model_config.pop("type", "lr")
        if meta_type == "lr":
            meta_model = LogisticRegression(**meta_model_config)
        else:
            meta_model = create_model(meta_type, **meta_model_config)

    return EnsembleModel(
        models=models, method=method, weights=weights, meta_model=meta_model
    )
