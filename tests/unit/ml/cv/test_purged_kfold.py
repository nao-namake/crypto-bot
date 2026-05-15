"""
Phase 89-β: PurgedKFold テスト 8 件
"""

import numpy as np
import pytest

from src.ml.cv.purged_kfold import PurgedKFold


def test_split_yields_n_splits_folds():
    """n_splits 個の (train, test) ペアが yield される."""
    cv = PurgedKFold(n_splits=3, embargo_pct=0.0)
    X = np.zeros((90, 5))
    splits = list(cv.split(X))
    assert len(splits) == 3


def test_get_n_splits_returns_constructor_value():
    """get_n_splits は __init__ で渡した値を返す（sklearn 互換）."""
    cv = PurgedKFold(n_splits=5, embargo_pct=0.02)
    assert cv.get_n_splits() == 5
    assert cv.get_n_splits(X=np.zeros((100, 1))) == 5


def test_embargo_zero_acts_like_simple_kfold_split():
    """embargo_pct=0 では test 区間 + その他 = 全データ."""
    cv = PurgedKFold(n_splits=3, embargo_pct=0.0)
    X = np.zeros((90, 5))
    for train_idx, test_idx in cv.split(X):
        # 全データが train ∪ test
        assert len(train_idx) + len(test_idx) == len(X)
        # train と test に重複なし
        assert len(np.intersect1d(train_idx, test_idx)) == 0


def test_embargo_excludes_neighboring_train_samples():
    """embargo_pct > 0 で test 前後の train サンプルが除外される."""
    n = 100
    embargo_pct = 0.05  # 5% = 5 サンプル embargo
    cv = PurgedKFold(n_splits=4, embargo_pct=embargo_pct)
    X = np.zeros((n, 1))

    splits = list(cv.split(X))
    # 中央付近の fold（前後に train がある）で確認
    train_idx, test_idx = splits[1]
    # test 区間
    test_start = test_idx.min()
    test_end = test_idx.max()
    # embargo 範囲（前後 5 サンプル）には train が存在してはならない
    embargo_indices = np.concatenate(
        [np.arange(max(0, test_start - 5), test_start), np.arange(test_end + 1, min(n, test_end + 6))]
    )
    overlap = np.intersect1d(train_idx, embargo_indices)
    assert len(overlap) == 0


def test_train_test_indices_are_disjoint_with_embargo():
    """embargo>0 でも train と test の交差はゼロ."""
    cv = PurgedKFold(n_splits=5, embargo_pct=0.02)
    X = np.zeros((200, 3))
    for train_idx, test_idx in cv.split(X):
        assert len(np.intersect1d(train_idx, test_idx)) == 0


def test_test_indices_are_chronologically_ordered_across_folds():
    """fold ごとの test 区間が時系列順（最初の fold は最初の方、最後の fold は最後の方）."""
    cv = PurgedKFold(n_splits=4, embargo_pct=0.0)
    X = np.zeros((100, 1))
    splits = list(cv.split(X))

    test_starts = [test_idx.min() for _, test_idx in splits]
    # 単調増加
    assert all(test_starts[i] < test_starts[i + 1] for i in range(len(test_starts) - 1))


def test_full_test_coverage_each_sample_in_test_exactly_once():
    """全サンプルがちょうど 1 度 test に含まれる（K-Fold 性質）."""
    n = 60
    cv = PurgedKFold(n_splits=3, embargo_pct=0.05)
    X = np.zeros((n, 1))
    test_concat = np.concatenate([test_idx for _, test_idx in cv.split(X)])
    test_concat.sort()
    assert np.array_equal(test_concat, np.arange(n))


def test_invalid_parameters_raise():
    """n_splits<2 や embargo_pct<0 で ValueError."""
    with pytest.raises(ValueError):
        PurgedKFold(n_splits=1)
    with pytest.raises(ValueError):
        PurgedKFold(n_splits=3, embargo_pct=-0.01)

    # split: サンプル数 < n_splits でも ValueError
    cv = PurgedKFold(n_splits=5)
    with pytest.raises(ValueError):
        list(cv.split(np.zeros((3, 1))))
