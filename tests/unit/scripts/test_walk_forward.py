# tests/unit/scripts/test_walk_forward.py
# テスト対象: crypto_bot/scripts/walk_forward.py
# 説明:
#   - WalkForwardOptimizer: ウォークフォワード最適化
#   - 訓練期間→検証期間の分割と最適化

import numpy as np
import pandas as pd

from crypto_bot.scripts.walk_forward import split_walk_forward, walk_forward_test


def dummy_strategy_factory():
    class DummyStrategy:
        def logic_signal(self, *args, **kwargs):
            return type("Signal", (), {"side": None, "price": None})()

    return DummyStrategy()


class DummyBacktestEngine:
    # statsは呼ばれるたびにダミー値で返す
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._called = []

    def run(self):
        self._called.append("run")

    def statistics(self):
        return {"total_profit": 10, "cagr": 0.05, "max_drawdown": -0.03}


def test_split_walk_forward_basic():
    df = pd.DataFrame(
        {"close": np.arange(10)}, index=pd.date_range("2020-01-01", periods=10)
    )
    splits = split_walk_forward(df, train_window=4, test_window=2, step=2)
    assert len(splits) == 3
    # 各splitの長さをチェック
    for train_df, test_df in splits:
        assert len(train_df) == 4
        assert len(test_df) == 2


def test_walk_forward_test(monkeypatch):
    # ダミーdf: 12本
    df = pd.DataFrame(
        {"close": np.arange(12)}, index=pd.date_range("2020-01-01", periods=12)
    )

    # BacktestEngineをモック
    monkeypatch.setattr(
        "crypto_bot.scripts.walk_forward.BacktestEngine", DummyBacktestEngine
    )

    results = walk_forward_test(
        df=df,
        train_window=5,
        test_window=3,
        step=2,
        strategy_factory=dummy_strategy_factory,
        starting_balance=10000,
        slippage_rate=0.0,
    )
    # 5+3=8, step2→ (0,8), (2,10), (4,12) → 3fold
    assert results.shape[0] == 3
    assert all(results["total_profit"] == 10)
    assert all(results["cagr"] == 0.05)
    assert all(results["max_drawdown"] == -0.03)
