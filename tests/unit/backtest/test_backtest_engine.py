# tests/unit/test_backtest_engine.py
from types import SimpleNamespace

import pandas as pd
import pytest

import crypto_bot.backtest.engine as be_mod
from crypto_bot.backtest.engine import BacktestEngine, TradeRecord
from crypto_bot.execution.engine import Signal
from crypto_bot.strategy.base import StrategyBase


class DummyStrategy(StrategyBase):
    """
    既存テストでも使うダミー戦略。
    logic_signal は毎バー必ず BUY シグナルを返す。
    """

    def logic_signal(self, price_df, position):
        return Signal(side="BUY", price=float(price_df["close"].iloc[-1]))


class DummyEntryExit:
    """
    run() の標準ルートテスト用に、
    最初のバーでエントリー → ２番目のバーでイグジットする EntryExit。
    """

    def __init__(self, strategy, risk_manager, atr):
        self.atr_series = atr
        self.current_balance = None

    def generate_entry_order(self, df, position):
        exist = not position.exist
        return SimpleNamespace(exist=exist, price=float(df["close"].iloc[-1]))

    def fill_order(self, order, position, balance):
        if order.exist and not position.exist:
            position.exist = True
            position.side = "BUY"
            position.entry_price = order.price
            position.lot = 1
            return balance
        if order.exist and position.exist:
            position.exist = False
            return balance
        return balance

    def generate_exit_order(self, df, position):
        price = float(df["close"].iloc[-1])
        exist = position.exist and price != position.entry_price
        return SimpleNamespace(exist=exist, price=price)


@pytest.fixture(autouse=True)
def patch_atr(monkeypatch):
    """
    IndicatorCalculator.calculate_atr を常に 1.0 シリーズにパッチ。
    """
    monkeypatch.setattr(
        be_mod.IndicatorCalculator,
        "calculate_atr",
        lambda df, period: pd.Series(1.0, index=df.index),
    )


def test_run_empty_input_returns_empty_list():
    engine = BacktestEngine(price_df=None, strategy=None)
    assert engine.run(None) == []
    assert engine.run(pd.DataFrame()) == []


def test_run_close_only_dummy_strategy_emits_one_record_per_bar():
    idx = pd.date_range("2022-01-01", periods=4, freq="H")
    df = pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0]}, index=idx)
    engine = BacktestEngine(price_df=df, strategy=DummyStrategy())
    records = engine.run()
    assert len(records) == 4
    assert all(isinstance(r, TradeRecord) for r in records)
    for r, ts in zip(records, idx):
        assert r.entry_time == ts and r.exit_time == ts
        assert r.profit == pytest.approx(0.0)


def test_run_one_trade_and_equity_and_statistics():
    idx = pd.date_range("2022-01-01", periods=2, freq="H")
    prices = [100.0, 110.0]
    df = pd.DataFrame({"close": prices, "high": prices, "low": prices}, index=idx)

    engine = BacktestEngine(
        price_df=None,
        strategy=None,
        entry_exit=DummyEntryExit(None, None, None),
        starting_balance=1000.0,
        slippage_rate=0.0,
    )

    records = engine.run(df)
    assert len(records) == 1
    rec = records[0]
    assert rec.entry_time == idx[0]
    assert rec.exit_time == idx[1]
    assert rec.entry_price == pytest.approx(100.0)
    assert rec.exit_price == pytest.approx(110.0)
    assert rec.profit == pytest.approx(10.0)
    assert pytest.approx(rec.return_rate) == 10.0

    eq = engine.get_equity_curve()
    assert list(eq.index) == [idx[1]]
    assert pytest.approx(eq.iloc[0]) == 1010.0

    stats = engine.statistics()
    assert stats["total_profit"] == pytest.approx(10.0)
    assert stats["max_drawdown"] == pytest.approx(0.0)
    # cagr は 0 または正の float
    assert isinstance(stats["cagr"], float) and stats["cagr"] >= 0.0
    assert isinstance(stats["sharpe"], float)


def test_backtest_simple_roundtrip():
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]})
    strat = DummyStrategy()
    eng = BacktestEngine(strategy=strat, risk_manager=None, entry_exit=None)
    records = eng.run(df)
    assert len(records) >= 5
    assert hasattr(records[0], "profit")
    assert isinstance(records[0].profit, float)
