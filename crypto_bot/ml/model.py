# ============================================================
# ファイル名: crypto_bot/ml/model.py
# 説明:
# 機械学習モデルのラッピングクラスとモデル生成用ファクトリ関数。
# sklearn/LightGBM/XGBoost/RandomForestに対応し、
# - fit, predict, predict_proba, save, load
# などの共通インターフェースを提供。
# ============================================================

from pathlib import Path
from typing import Any, Optional, Union

import joblib
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
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

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "MLModel":
        """
        モデルを学習します。
        """
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
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.estimator, path)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "MLModel":
        """
        ファイルからモデルを復元してラップして返します。
        """
        est = joblib.load(filepath)
        return cls(est)


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
        if "lambda_l2" not in kwargs:
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
    for param in ["lambda_l1", "lambda_l2"]:
        if param in kwargs and kwargs[param] == 0.0:
            del kwargs[param]
    return kwargs

def create_model(model_type: str, **kwargs) -> BaseEstimator:
    """
    model_type に応じた sklearn Estimator を返します。
    """
    key = model_type.lower()
    if key not in _MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model_type '{model_type}'. valid types: {list(_MODEL_REGISTRY)}"
        )
    cls = _MODEL_REGISTRY[key]
    if key == "lgbm":
        kwargs = _lgbm_param_cleanup(kwargs)
    return cls(**kwargs)
