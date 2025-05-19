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


def create_model(model_type: str, **kwargs) -> BaseEstimator:
    """
    model_type に応じた sklearn Estimator を返します。

    Parameters
    ----------
    model_type : str
        'lgbm' / 'rf' / 'xgb' のいずれか
    **kwargs :
        各クラスのコンストラクタ引数

    Returns
    -------
    BaseEstimator
        指定されたモデルインスタンス

    Raises
    ------
    ValueError
        未知の model_type が指定された場合
    """
    key = model_type.lower()
    if key not in _MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model_type '{model_type}'. valid types: {list(_MODEL_REGISTRY)}"
        )
    cls = _MODEL_REGISTRY[key]
    return cls(**kwargs)
