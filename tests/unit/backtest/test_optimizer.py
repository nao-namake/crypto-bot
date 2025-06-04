# tests/unit/backtest/test_optimizer.py
# テスト対象: crypto_bot/backtest/optimizer.py
# 説明:
#   - ParameterOptimizer: パラメータグリッドでのダミーバックテストの走査・集計
#   - optimize_backtest: 設定dictから全自動最適化実行

from datetime import timedelta

import numpy as np
import pandas as pd

from crypto_bot.backtest.optimizer import ParameterOptimizer, optimize_backtest


class DummyBacktestEngine:
    """BacktestEngineのダミー（runでダミートレードを返す）"""

    def __init__(self, price_df, *args, **kwargs):
        self.df = price_df

    def run(self):
        from types import SimpleNamespace

        # 2件だけ適当なTradeRecordもどきを返す
        base = self.df.index[0]
        return [
            SimpleNamespace(
                entry_time=base,
                exit_time=base + timedelta(minutes=5),
                side="BUY",
                entry_price=100,
                exit_price=110,
                profit=10,
                return_rate=0.1,
                duration_bars=5,
                slippage=0,
                commission=0,
                size=1,
            ),
            SimpleNamespace(
                entry_time=base + timedelta(minutes=5),
                exit_time=base + timedelta(minutes=10),
                side="SELL",
                entry_price=110,
                exit_price=100,
                profit=-10,
                return_rate=-0.09,
                duration_bars=5,
                slippage=0,
                commission=0,
                size=1,
            ),
        ]


def test_parameter_optimizer_scan(monkeypatch):
    # ダミーエンジンに差し替え
    monkeypatch.setattr(
        "crypto_bot.backtest.optimizer.BacktestEngine", DummyBacktestEngine
    )
    dtidx = pd.date_range("2023-01-01", periods=10, freq="T")
    df = pd.DataFrame({"close": np.arange(10)}, index=dtidx)
    optimizer = ParameterOptimizer(df, starting_balance=1000, slippage_rate=0.0)
    result = optimizer.scan(periods=[5, 10], nbdevs=[1, 2])
    assert set(result.columns) >= {
        "n_trades",
        "win_rate",
        "avg_return",
        "total_profit",
        "max_drawdown",
        "cagr",
        "period",
        "nbdev",
        "timeframe",
    }
    # パラメータ組み合わせ分、集計行ができる
    assert len(result) == 4


def test_compute_stats_empty():
    # 空リスト時の返り値
    optimizer = ParameterOptimizer(pd.DataFrame())
    stats = optimizer._compute_stats([], None, None, 0)
    for v in stats.values():
        assert v == 0 or v == 0.0


def test_optimize_backtest(monkeypatch):
    # DataPreprocessor.clean, MarketDataFetcher, BacktestEngine をダミー化
    class DummyFetcher:
        def __init__(self, **kwargs):
            pass

        def get_price_df(self, **kwargs):
            idx = pd.date_range("2024-01-01", periods=6, freq="T")
            return pd.DataFrame({"close": np.arange(6)}, index=idx)

    class DummyCleaner:
        @staticmethod
        def clean(df, **kwargs):
            return df

    monkeypatch.setattr("crypto_bot.backtest.optimizer.MarketDataFetcher", DummyFetcher)
    monkeypatch.setattr("crypto_bot.backtest.optimizer.DataPreprocessor", DummyCleaner)
    monkeypatch.setattr(
        "crypto_bot.backtest.optimizer.BacktestEngine", DummyBacktestEngine
    )
    config = {
        "data": {
            "exchange": "dummy",
            "symbol": "BTC/USDT",
            "timeframe": "1m",
            "since": None,
            "limit": 6,
        },
        "strategy": {"params": {"period": 2}},
        "optimizer": {"periods": [2], "nbdevs": [1]},
        "backtest": {"starting_balance": 1000, "slippage_rate": 0.0},
    }
    df = optimize_backtest(config)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert set(df.columns) >= {
        "n_trades",
        "win_rate",
        "avg_return",
        "total_profit",
        "max_drawdown",
        "cagr",
    }
