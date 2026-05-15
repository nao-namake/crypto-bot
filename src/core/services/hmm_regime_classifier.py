"""
Phase 89-γ: HMM レジーム検出（3 状態 Gaussian HMM）

既存 MarketRegimeClassifier（4 段階ルールベース）を補完する確率的レジーム検出。
3 状態（bear / sideways / bull）の状態確率を返し、ハイブリッド統合に利用。

入力特徴量:
- returns_1（1 期間リターン）
- atr_14（14 期間 ATR・volatility proxy）
- volume_ratio（出来高比率）

学習: 履歴 1000 本以上で fit_offline → pickle 保存（models/regime/hmm_3state.pkl）
推論: predict_proba(df) で (n_samples, 3) の状態確率を返す
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import numpy as np

try:
    from hmmlearn import hmm

    _HAS_HMMLEARN = True
except ImportError:  # pragma: no cover
    hmm = None  # type: ignore
    _HAS_HMMLEARN = False

try:
    import joblib

    _HAS_JOBLIB = True
except ImportError:  # pragma: no cover
    joblib = None  # type: ignore
    _HAS_JOBLIB = False

import pandas as pd

from ..logger import get_logger


def has_hmmlearn() -> bool:
    return _HAS_HMMLEARN


class HMMRegimeClassifier:
    """3 状態 Gaussian HMM レジーム検出器."""

    DEFAULT_FEATURES: List[str] = ["returns_1", "atr_14", "volume_ratio"]

    def __init__(
        self,
        n_states: int = 3,
        feature_names: Optional[List[str]] = None,
        random_state: int = 42,
        n_iter: int = 100,
        covariance_type: str = "diag",
    ) -> None:
        if not _HAS_HMMLEARN:
            raise ImportError("hmmlearn is required. Install: pip install hmmlearn>=0.3.0")
        self.n_states = n_states
        self.feature_names = list(feature_names or self.DEFAULT_FEATURES)
        self.random_state = random_state
        self.n_iter = n_iter
        self.covariance_type = covariance_type
        self.model: Optional["hmm.GaussianHMM"] = None
        self.is_fitted = False
        self.logger = get_logger()

    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """DataFrame から HMM 入力特徴量を抽出（NaN は 0 で埋める）."""
        missing = [f for f in self.feature_names if f not in df.columns]
        if missing:
            raise ValueError(f"HMM 入力特徴量不足: {missing}")
        X = df[self.feature_names].astype(float).values
        return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    def fit_offline(self, df: pd.DataFrame, min_samples: int = 100) -> "HMMRegimeClassifier":
        """履歴データで HMM を学習."""
        if len(df) < min_samples:
            raise ValueError(f"HMM 学習には最低 {min_samples} サンプル必要（実際: {len(df)}）")
        X = self._extract_features(df)
        self.model = hmm.GaussianHMM(
            n_components=self.n_states,
            covariance_type=self.covariance_type,
            n_iter=self.n_iter,
            random_state=self.random_state,
        )
        self.model.fit(X)
        self.is_fitted = True
        self.logger.info(
            f"Phase 89-γ HMM 学習完了: states={self.n_states}, samples={len(df)}, "
            f"converged={self.model.monitor_.converged}"
        )
        return self

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """各サンプルの状態確率 (n_samples, n_states) を返す.

        fit 前は uniform 確率を返す（fail-open）.
        """
        if not self.is_fitted or self.model is None:
            n = len(df)
            return np.full((n, self.n_states), 1.0 / self.n_states)
        X = self._extract_features(df)
        try:
            return self.model.predict_proba(X)
        except Exception as e:
            self.logger.warning(f"Phase 89-γ HMM predict_proba 失敗 → uniform fallback: {e}")
            return np.full((len(df), self.n_states), 1.0 / self.n_states)

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """各サンプルの最尤状態 (n_samples,) を返す."""
        if not self.is_fitted or self.model is None:
            return np.zeros(len(df), dtype=int)
        X = self._extract_features(df)
        return self.model.predict(X)

    def save(self, path: str) -> None:
        """pickle 保存."""
        if not _HAS_JOBLIB:
            raise ImportError("joblib is required for save/load")
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted HMM")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "n_states": self.n_states,
                "feature_names": self.feature_names,
                "random_state": self.random_state,
            },
            path,
        )
        self.logger.info(f"Phase 89-γ HMM 保存: {path}")

    def load(self, path: str) -> "HMMRegimeClassifier":
        """pickle 読込."""
        if not _HAS_JOBLIB:
            raise ImportError("joblib is required for save/load")
        data = joblib.load(path)
        self.model = data["model"]
        self.n_states = data["n_states"]
        self.feature_names = data["feature_names"]
        self.random_state = data.get("random_state", 42)
        self.is_fitted = True
        return self
