"""
Phase 89-γ: N-BEATS 軽量実装（Pure PyTorch・CPU 推論専用）

Oreshkin et al. 2019 "N-BEATS: Neural basis expansion analysis for interpretable
time series forecasting" を分類タスク向けに簡略化:

- 入力: 特徴量ベクトル (batch, n_features)
- 出力: クラス確率 (batch, n_classes)
- Backbone: 浅い MLP (stacks=2, blocks=3, layer_widths=64)

学習時のみ torch を使う。推論レイテンシ < 50ms / sample を CPU で達成する。
GPU 不要のため Cloud Run（CPU 1）でも動作可能。

torch 未インストール環境では import 時 ImportError → ProductionEnsemble は LGB/XGB/RF
の 3 モデル fallback で動作（duck typing）。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

try:
    import torch
    import torch.nn as nn

    _HAS_TORCH = True
except ImportError:  # pragma: no cover
    torch = None  # type: ignore
    nn = None  # type: ignore
    _HAS_TORCH = False


def has_torch() -> bool:
    """torch インストール確認."""
    return _HAS_TORCH


if _HAS_TORCH:

    class NBeatsBlock(nn.Module):
        """N-BEATS の単一 block: stack 内で重み共有なし.

        backcast / forecast 用に分岐する FC ヘッドを持つ。分類タスクのため backcast は不要。
        """

        def __init__(self, n_features: int, hidden_size: int = 64, n_classes: int = 3) -> None:
            super().__init__()
            self.fc1 = nn.Linear(n_features, hidden_size)
            self.fc2 = nn.Linear(hidden_size, hidden_size)
            self.fc3 = nn.Linear(hidden_size, hidden_size)
            self.fc4 = nn.Linear(hidden_size, hidden_size)
            self.forecast_head = nn.Linear(hidden_size, n_classes)
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(p=0.1)

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            h = self.relu(self.fc1(x))
            h = self.dropout(h)
            h = self.relu(self.fc2(h))
            h = self.dropout(h)
            h = self.relu(self.fc3(h))
            h = self.relu(self.fc4(h))
            return self.forecast_head(h)

    class NBeatsClassifier(nn.Module):
        """N-BEATS スタイル分類器（軽量版）.

        Args:
            n_features: 入力特徴量数（EXPECTED_FEATURE_COUNT に連動）
            n_classes: 出力クラス数（デフォルト 3: SELL/HOLD/BUY）
            n_stacks: stack 数（デフォルト 2）
            n_blocks_per_stack: stack あたり block 数（デフォルト 3）
            hidden_size: hidden layer 幅（デフォルト 64）
        """

        def __init__(
            self,
            n_features: int,
            n_classes: int = 3,
            n_stacks: int = 2,
            n_blocks_per_stack: int = 3,
            hidden_size: int = 64,
        ) -> None:
            super().__init__()
            self.n_features = n_features
            self.n_classes = n_classes
            self.n_stacks = n_stacks
            self.n_blocks_per_stack = n_blocks_per_stack
            self.hidden_size = hidden_size

            self.blocks = nn.ModuleList(
                [
                    NBeatsBlock(n_features, hidden_size, n_classes)
                    for _ in range(n_stacks * n_blocks_per_stack)
                ]
            )

        def forward(self, x: "torch.Tensor") -> "torch.Tensor":
            """各 block の forecast を加算 → softmax で確率化（softmax は train/test 側で）.

            Returns:
                logits (batch, n_classes)
            """
            logits_sum = torch.zeros(x.shape[0], self.n_classes, device=x.device, dtype=x.dtype)
            for block in self.blocks:
                logits_sum = logits_sum + block(x)
            return logits_sum

else:
    # torch 未インストール時のスタブ
    class NBeatsBlock:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "torch is required for NBeatsBlock. " "Install: pip install torch>=2.0.0"
            )

    class NBeatsClassifier:  # type: ignore
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "torch is required for NBeatsClassifier. " "Install: pip install torch>=2.0.0"
            )
