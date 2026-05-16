"""
Phase 89-γ + Phase 89 NB1-NB5 fix: NBeatsPredictor - sklearn 互換ラッパー

ProductionEnsemble と統合可能な predict / predict_proba / fit インターフェースを提供。
ensemble.py の duck typing ループ（predict_proba を持つモデル）にそのまま組み込める。

Phase 89 NB1-NB5 完全版実装:
- NB1: StandardScaler 内蔵（大スケール特徴量を正規化）
- NB2: n_epochs 200 + EarlyStopping (validation loss patience=20)
- NB3: NBeatsClassifier 内部で Kaiming init + logits 平均化を実施
- NB4: class_weights 受け取り（CrossEntropyLoss に渡す）
- NB5: epoch ごとの train/val loss / confidence_std を logger.info で出力
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.preprocessing import StandardScaler

from ..core.logger import get_logger
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

    Phase 89 NB1-NB5 修正版:
    - fit/predict/predict_proba/n_features_in_ を提供
    - 内部 StandardScaler で特徴量正規化
    - validation loss ベースの Early Stopping
    - epoch ごとのログ出力
    - クラス不均衡を class_weights で吸収
    - ProductionEnsemble.predict_proba ループから呼ばれる
    """

    def __init__(
        self,
        n_features: Optional[int] = None,
        n_classes: int = 3,
        n_stacks: int = 2,
        n_blocks_per_stack: int = 3,
        hidden_size: int = 64,
        learning_rate: float = 1e-3,
        n_epochs: int = 200,
        batch_size: int = 64,
        device: str = "cpu",
        random_state: int = 42,
        patience: int = 20,
        val_split: float = 0.1,
        log_every: int = 10,
    ) -> None:
        if not has_torch():
            raise ImportError(
                "torch is required for NBeatsPredictor. Install: pip install torch>=2.0.0"
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
        # NB2 / NB5
        self.patience = patience
        self.val_split = val_split
        self.log_every = log_every
        # 学習結果
        self.model: Optional[NBeatsClassifier] = None
        self.is_fitted = False
        # NB1: StandardScaler 内蔵（fit 後に self.scaler.transform で同じスケーリング適用）
        self.scaler: Optional[StandardScaler] = None
        # NB2: Early Stopping 記録
        self.best_epoch: int = 0
        self.best_val_loss: float = float("inf")
        self.training_history: List[Dict[str, float]] = []
        self.logger = get_logger()

    @property
    def n_features_in_(self) -> Optional[int]:
        """sklearn 互換: ProductionEnsemble の n_features_ 検出に使われる."""
        return self.n_features

    # ------------------------------------------------------------------
    # 学習
    # ------------------------------------------------------------------

    def fit(
        self,
        X,
        y,
        class_weights: Any = "balanced",
    ) -> "NBeatsPredictor":
        """学習（NB1 scaler + NB2 early stop + NB4 class_weights + NB5 ログ）.

        Args:
            X: 学習データ (n_samples, n_features) ndarray or DataFrame
            y: ラベル (n_samples,) ndarray or Series
            class_weights: クラスごとの重み (n_classes,) ndarray、文字列、または None。
                - "balanced" (default): sklearn compute_class_weight で自動算出
                - ndarray: そのまま使用
                - None: CrossEntropyLoss uniform weight

        Returns:
            self
        """
        torch.manual_seed(self.random_state)
        np.random.seed(self.random_state)

        X_arr = X.values if hasattr(X, "values") else np.asarray(X)
        y_arr = y.values if hasattr(y, "values") else np.asarray(y)
        X_arr = X_arr.astype(np.float32)
        y_arr = y_arr.astype(np.int64)

        n_samples, n_features = X_arr.shape
        if self.n_features is None:
            self.n_features = n_features

        # NB1: StandardScaler を fit して全データに適用
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_arr).astype(np.float32)

        # NB4: class_weights を解決
        weights_array: Optional[np.ndarray] = None
        if isinstance(class_weights, str) and class_weights == "balanced":
            try:
                from sklearn.utils.class_weight import compute_class_weight

                classes = np.unique(y_arr)
                computed = compute_class_weight("balanced", classes=classes, y=y_arr)
                # クラス index 順に並べる（CrossEntropyLoss は index 順を期待）
                weights_array = np.ones(self.n_classes, dtype=np.float32)
                for cls_idx, w in zip(classes, computed):
                    if 0 <= int(cls_idx) < self.n_classes:
                        weights_array[int(cls_idx)] = float(w)
            except Exception as e:
                self.logger.warning(
                    f"Phase 89 NB4: class_weight 自動算出失敗（uniform で続行）: {e}"
                )
                weights_array = None
        elif class_weights is not None:
            weights_array = np.asarray(class_weights, dtype=np.float32)

        # NB2: train/val split（時系列性は考慮しない単純シャッフル分割・既存 sklearn パターン）
        from sklearn.model_selection import train_test_split

        try:
            X_tr, X_val, y_tr, y_val = train_test_split(
                X_scaled,
                y_arr,
                test_size=self.val_split,
                random_state=self.random_state,
                stratify=y_arr,
            )
        except ValueError:
            # クラス サンプルが少なすぎる場合 stratify を諦める
            X_tr, X_val, y_tr, y_val = train_test_split(
                X_scaled,
                y_arr,
                test_size=self.val_split,
                random_state=self.random_state,
            )

        # NBeatsClassifier 構築（NB3: 内部で Kaiming init + logits 平均化）
        self.model = NBeatsClassifier(
            n_features=self.n_features,
            n_classes=self.n_classes,
            n_stacks=self.n_stacks,
            n_blocks_per_stack=self.n_blocks_per_stack,
            hidden_size=self.hidden_size,
        ).to(self.device)

        # NB4: CrossEntropyLoss に class_weights を渡す（None なら uniform）
        if weights_array is not None:
            weight_tensor = torch.tensor(weights_array, dtype=torch.float32, device=self.device)
            criterion = torch.nn.CrossEntropyLoss(weight=weight_tensor)
            self.logger.info(f"Phase 89 NB4: N-BEATS class_weights 適用: {weights_array.tolist()}")
        else:
            criterion = torch.nn.CrossEntropyLoss()

        optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate, weight_decay=1e-5)
        # NB2: ReduceLROnPlateau で val loss 停滞時に lr 削減
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode="min", factor=0.5, patience=max(1, self.patience // 4)
        )

        X_tr_t = torch.tensor(X_tr, dtype=torch.float32, device=self.device)
        y_tr_t = torch.tensor(y_tr, dtype=torch.long, device=self.device)
        X_val_t = torch.tensor(X_val, dtype=torch.float32, device=self.device)
        y_val_t = torch.tensor(y_val, dtype=torch.long, device=self.device)

        best_state: Optional[Dict[str, "torch.Tensor"]] = None
        patience_counter = 0
        n_tr = X_tr_t.shape[0]

        # NB5: 学習開始ログ
        self.logger.info(
            f"Phase 89 N-BEATS 学習開始: n_samples={n_samples}, n_features={n_features}, "
            f"n_classes={self.n_classes}, n_epochs={self.n_epochs}, patience={self.patience}, "
            f"lr={self.learning_rate}, val_split={self.val_split}"
        )

        for epoch in range(self.n_epochs):
            # ---- train ----
            self.model.train()
            perm = torch.randperm(n_tr)
            train_loss_sum = 0.0
            train_batches = 0
            for start in range(0, n_tr, self.batch_size):
                idx = perm[start : start + self.batch_size]
                batch_x = X_tr_t[idx]
                batch_y = y_tr_t[idx]
                logits = self.model(batch_x)
                loss = criterion(logits, batch_y)
                optimizer.zero_grad()
                loss.backward()
                # NB3: 勾配クリッピングで爆発防止
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
                optimizer.step()
                train_loss_sum += float(loss.item())
                train_batches += 1
            train_loss = train_loss_sum / max(1, train_batches)

            # ---- val ----
            self.model.eval()
            with torch.no_grad():
                val_logits = self.model(X_val_t)
                val_loss = float(criterion(val_logits, y_val_t).item())
                val_proba = F.softmax(val_logits, dim=1).cpu().numpy()
                val_pred = val_proba.argmax(axis=1)
                val_accuracy = float((val_pred == y_val).mean())
                val_conf_std = float(val_proba.max(axis=1).std())

            self.training_history.append(
                {
                    "epoch": epoch + 1,
                    "train_loss": train_loss,
                    "val_loss": val_loss,
                    "val_accuracy": val_accuracy,
                    "val_confidence_std": val_conf_std,
                }
            )

            # NB5: log_every ごとにログ出力
            if (epoch + 1) % self.log_every == 0 or epoch == 0:
                self.logger.info(
                    f"Phase 89 N-BEATS epoch {epoch + 1}/{self.n_epochs}: "
                    f"train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, "
                    f"val_acc={val_accuracy:.4f}, val_conf_std={val_conf_std:.4f}"
                )

            # NB2: best update + early stopping
            scheduler.step(val_loss)
            if val_loss < self.best_val_loss - 1e-5:
                self.best_val_loss = val_loss
                self.best_epoch = epoch + 1
                best_state = {k: v.detach().clone() for k, v in self.model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.patience:
                    self.logger.info(
                        f"Phase 89 N-BEATS EarlyStopping at epoch {epoch + 1} "
                        f"(best={self.best_epoch}, best_val_loss={self.best_val_loss:.4f})"
                    )
                    break

        # best state を復元
        if best_state is not None:
            self.model.load_state_dict(best_state)

        self.is_fitted = True
        self.model.eval()

        # NB5: 学習完了サマリー
        if self.training_history:
            final = self.training_history[-1]
            self.logger.info(
                f"Phase 89 N-BEATS 学習完了: best_epoch={self.best_epoch}, "
                f"best_val_loss={self.best_val_loss:.4f}, "
                f"final_val_acc={final['val_accuracy']:.4f}, "
                f"final_conf_std={final['val_confidence_std']:.4f}"
            )
        return self

    # ------------------------------------------------------------------
    # 推論
    # ------------------------------------------------------------------

    def predict(self, X) -> np.ndarray:
        """クラス予測."""
        probas = self.predict_proba(X)
        return np.argmax(probas, axis=1)

    def predict_proba(self, X) -> np.ndarray:
        """クラス確率予測（softmax 適用・NB1 scaler 経由）.

        ProductionEnsemble.predict_proba ループから呼ばれる。
        """
        if not self.is_fitted or self.model is None or self.scaler is None:
            # fit 前に呼ばれた場合は uniform 確率を返す（fail-open）
            n = X.shape[0] if hasattr(X, "shape") else len(X)
            return np.full((n, self.n_classes), 1.0 / self.n_classes)

        X_arr = X.values if hasattr(X, "values") else np.asarray(X)
        X_arr = X_arr.astype(np.float32)
        X_scaled = self.scaler.transform(X_arr).astype(np.float32)

        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.tensor(X_scaled, dtype=torch.float32, device=self.device)
            logits = self.model(X_tensor)
            probas = F.softmax(logits, dim=1).cpu().numpy()
        return probas

    # ------------------------------------------------------------------
    # sklearn 互換 set_params（Optuna 等のため）
    # ------------------------------------------------------------------

    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        return {
            "n_features": self.n_features,
            "n_classes": self.n_classes,
            "n_stacks": self.n_stacks,
            "n_blocks_per_stack": self.n_blocks_per_stack,
            "hidden_size": self.hidden_size,
            "learning_rate": self.learning_rate,
            "n_epochs": self.n_epochs,
            "batch_size": self.batch_size,
            "device": self.device,
            "random_state": self.random_state,
            "patience": self.patience,
            "val_split": self.val_split,
            "log_every": self.log_every,
        }

    def set_params(self, **params) -> "NBeatsPredictor":
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self
