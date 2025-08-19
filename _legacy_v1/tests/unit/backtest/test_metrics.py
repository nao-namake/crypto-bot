# tests/unit/backtest/test_metrics.py
# テスト対象: crypto_bot/backtest/metrics.py
# 説明:
#   - split_walk_forward: データフレームのウォークフォワード分割
#   - max_drawdown: 最大ドローダウン（率）の計算
#   - cagr: 年率平均成長率(CAGR)の計算
#   - sharpe_ratio: シャープレシオの計算と例外処理

import os

# backtest分離により、統合バックテストシステムからimport
import sys

import numpy as np
import pandas as pd

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, os.path.join(project_root, "backtest"))
try:
    from engine import metrics
except ImportError:
    # フォールバック: 旧パスを維持
    import pytest

    pytest.skip("backtest metrics module not available", allow_module_level=True)


def test_split_walk_forward_basic():
    """データが正しくウォークフォワード分割されるか"""
    df = pd.DataFrame({"close": range(10)})
    splits = metrics.split_walk_forward(df, train_window=4, test_window=2, step=2)
    # 10本で (0-3)+(4-5), (2-5)+(6-7), (4-7)+(8-9) の3分割
    assert len(splits) == 3
    for train, test in splits:
        assert len(train) == 4
        assert len(test) == 2


def test_split_walk_forward_edge_case():
    """データが短い場合でも例外にならない"""
    df = pd.DataFrame({"close": range(5)})
    splits = metrics.split_walk_forward(df, train_window=3, test_window=2, step=1)
    assert len(splits) == 1


def test_max_drawdown_empty():
    """空データのときは0.0"""
    eq = pd.Series(dtype=float)
    assert metrics.max_drawdown(eq) == 0.0


def test_max_drawdown_normal():
    """単純な資産曲線の最大DDを計算"""
    eq = pd.Series([100, 120, 110, 130, 90, 140])
    # ドローダウン率の最小値
    dd = metrics.max_drawdown(eq)
    # 90/130 - 1 = -0.307...
    assert np.isclose(dd, -0.3076923, atol=1e-6)


def test_cagr_basic():
    """CAGR: 正常パターン"""
    eq = pd.Series([100, 110, 121])
    # 2期間で (121/100)^(1/2) - 1
    expected = (121 / 100) ** (1 / 2) - 1
    assert np.isclose(metrics.cagr(eq, periods=2), expected, atol=1e-6)


def test_cagr_zero_start():
    """CAGR: 最初が0以下→0.0"""
    eq = pd.Series([0, 100, 110])
    assert metrics.cagr(eq) == 0.0


def test_cagr_empty_or_invalid_period():
    """CAGR: 空や1点のみなども0.0"""
    assert metrics.cagr(pd.Series(dtype=float)) == 0.0
    assert metrics.cagr(pd.Series([100])) == 0.0
    # periods=0
    assert metrics.cagr(pd.Series([100, 110]), periods=0) == 0.0


def test_sharpe_ratio_basic():
    """シャープレシオ: 日次変化から計算"""
    returns = pd.Series([0.01, 0.02, -0.01, 0.0])
    sharpe = metrics.sharpe_ratio(returns)
    # 単純計算で正の値
    assert sharpe > 0


def test_sharpe_ratio_zero_std():
    """リターンが全て同じなら0"""
    returns = pd.Series([0.01, 0.01, 0.01])
    assert metrics.sharpe_ratio(returns) == 0.0


def test_sharpe_ratio_empty():
    """空リターン系列は0"""
    assert metrics.sharpe_ratio(pd.Series(dtype=float)) == 0.0
