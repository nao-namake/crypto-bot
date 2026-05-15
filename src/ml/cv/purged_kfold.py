"""
Phase 89-β: Purged K-Fold Cross-Validation

Lopez de Prado "Advances in Financial Machine Learning" 3.4 章準拠の
時系列リーク対策 K-Fold 実装。

設計:
- 時系列順に K 分割（連続区間ごと）
- test 区間と隣接する train サンプルを embargo（除外）してリーク防止
- sklearn の splitter API 互換（cross_val_score / GridSearchCV から利用可）

引数 `embargo_pct` で embargo 幅をデータ長の比率で指定（default 0.01 = 1%）。
"""

from typing import Iterator, Optional, Tuple

import numpy as np


class PurgedKFold:
    """時系列リーク対策付き K-Fold."""

    def __init__(self, n_splits: int = 3, embargo_pct: float = 0.01) -> None:
        """
        Args:
            n_splits: 分割数 (>= 2)
            embargo_pct: test 区間の前後で除外する train サンプルの割合 (>= 0.0)
        """
        if n_splits < 2:
            raise ValueError(f"n_splits must be >= 2, got {n_splits}")
        if embargo_pct < 0.0:
            raise ValueError(f"embargo_pct must be >= 0.0, got {embargo_pct}")
        self.n_splits = n_splits
        self.embargo_pct = embargo_pct

    def split(
        self,
        X,
        y=None,
        groups=None,
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        train/test インデックスを yield する.

        各 fold:
        - test: 連続区間（時系列順に K 等分のうち i 番目）
        - train: test 区間とその前後 embargo を除いた残り全部

        Args:
            X: array-like, shape=(n_samples, n_features) or DataFrame
            y: array-like or None（互換性のため受け取るだけ）
            groups: 互換性のため受け取るだけ
        """
        n = len(X)
        if n < self.n_splits:
            raise ValueError(f"Cannot split {n} samples into {self.n_splits} folds")

        embargo = int(n * self.embargo_pct)
        all_idx = np.arange(n)
        fold_size = n // self.n_splits

        for i in range(self.n_splits):
            test_start = i * fold_size
            # 最終 fold は残り全部を吸収（端数対応）
            test_end = (i + 1) * fold_size if i < self.n_splits - 1 else n
            test_idx = all_idx[test_start:test_end]

            # embargo 範囲: test の前後 `embargo` サンプルを train から除外
            embargo_start = max(0, test_start - embargo)
            embargo_end = min(n, test_end + embargo)

            train_idx = np.concatenate([all_idx[:embargo_start], all_idx[embargo_end:]])

            yield train_idx, test_idx

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        """sklearn splitter API 互換."""
        return self.n_splits
