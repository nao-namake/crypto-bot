"""
Phase 89-γ: NBeatsPredictor - sklearn 互換ラッパー

ProductionEnsemble と統合可能な predict / predict_proba / fit インターフェースを提供。
ensemble.py の duck typing ループ（predict_proba を持つモデル）にそのまま組み込める。
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .nbeats import NBeatsClassifier, has_torch

try:
    import torch
    import torch.nn.functional as F
    import torch.optim as optim
except ImportError:  # pragma: no cover
    torch = None  # type: ignore
    F = None  # type: ignore
    optim = None  # type: ignore


class NBeatsPredictor:
    """sklearn 互換 N-BEATS Predictor.

    fit / predict / predict_proba / n_features_in_ を提供。
    ProductionEnsemble.predict_proba ループから呼ばれることを想定。
    """

    def __init__(
        self,
        n_features: Optional[int] = None,
        n_classes: int = 3,
        n_stacks: int = 2,
        n_blocks_per_stack: int = 3,
        hidden_size: int = 64,
        learning_rate: float = 1e-3,
        n_epochs: int = 50,
        batch_size: int = 64,
        device: str = "cpu",
        random_state: int = 42,
    ) -> None:
        if not has_torch():
            raise ImportError(
                "torch is required for NBeatsPredictor. " "Install: pip install torch>=2.0.0"
            )
        self.n_features = n_features
        self.n_classes = n_classes
        self.n_stacks = n_stacks
        self.n_blocks_per_stack = n_blocks_per_stack
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        self.device = device
        self.random_state = random_state
        self.model: Optional[NBeatsClassifier] = None
        self.is_fitted = False

    @property
    def n_features_in_(self) -> Optional[int]:
        """sklearn 互換: ProductionEnsemble の n_features_ 検出に使われる."""
        return self.n_features

    def fit(self, X, y) -> "NBeatsPredictor":
        """学習."""
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        X_arr = X.values if hasattr(X, "values") else np.asarray(X)
        y_arr = y.values if hasattr(y, "values") else np.asarray(y)

        n_samples, n_features = X_arr.shape
        if self.n_features is None:
            self.n_features = n_features

        self.model = NBeatsClassifier(
            n_features=self.n_features,
            n_classes=self.n_classes,
            n_stacks=self.n_stacks,
            n_blocks_per_stack=self.n_blocks_per_stack,
            hidden_size=self.hidden_size,
        ).to(self.device)

        X_tensor = torch.tensor(X_arr, dtype=torch.float32, device=self.device)
        y_tensor = torch.tensor(y_arr, dtype=torch.long, device=self.device)

        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.model.train()

        for epoch in range(self.n_epochs):
            perm = torch.randperm(n_samples)
            for start in range(0, n_samples, self.batch_size):
                idx = perm[start : start + self.batch_size]
                batch_x = X_tensor[idx]
                batch_y = y_tensor[idx]

                logits = self.model(batch_x)
                loss = F.cross_entropy(logits, batch_y)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        self.is_fitted = True
        return self

    def predict(self, X) -> np.ndarray:
        """クラス予測."""
        probas = self.predict_proba(X)
        return np.argmax(probas, axis=1)

    def predict_proba(self, X) -> np.ndarray:
        """クラス確率予測（softmax 適用）.

        ProductionEnsemble.predict_proba ループから呼ばれる。
        """
        if not self.is_fitted or self.model is None:
            # fit 前に呼ばれた場合は uniform 確率を返す（fail-open）
            n = X.shape[0] if hasattr(X, "shape") else len(X)
            return np.full((n, self.n_classes), 1.0 / self.n_classes)

        X_arr = X.values if hasattr(X, "values") else np.asarray(X)
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(X_arr, dtype=torch.float32, device=self.device)
            logits = self.model(X_tensor)
            probas = F.softmax(logits, dim=1).cpu().numpy()
        return probas
