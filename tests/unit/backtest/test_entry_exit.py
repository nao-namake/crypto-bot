import pandas as pd
import pytest

from crypto_bot.execution.engine import EntryExit, Order, Position, Signal


class DummyStrategy:
    def __init__(self, signal: Signal):
        self.signal = signal

    def logic_signal(self, price_df, position):
        return self.signal


class DummyRiskManager:
    def __init__(self, stop_price: float, lot: float):
        self._stop = stop_price
        self._lot = lot

    def calc_stop_price(self, entry_price, atr_series):
        return self._stop

    def calc_lot(self, balance, entry_price, stop_price):
        return self._lot


@pytest.fixture
def simple_df():
    # 全て float 型にすることで、後続の df.loc[..., "low"]=0.5 の警告を抑制
    return pd.DataFrame(
        {
            "open": [1.0, 2.0, 3.0],
            "high": [1.0, 2.0, 3.0],
            "low": [1.0, 2.0, 3.0],
            "close": [1.0, 2.0, 3.0],
        }
    )


def test_generate_entry_order_buy(simple_df):
    strat = DummyStrategy(Signal(side="BUY", price=100.0))
    rm = DummyRiskManager(stop_price=90.0, lot=0.5)
    ee = EntryExit(strategy=strat, risk_manager=rm, atr_series=None)
    ee.current_balance = 1000.0
    pos = Position()
    order = ee.generate_entry_order(simple_df, pos)
    assert order.exist
    assert order.side == "BUY"
    assert order.price == pytest.approx(100.0)
    assert order.stop_price == pytest.approx(90.0)
    assert order.lot == pytest.approx(0.5)


def test_generate_entry_order_no_signal(simple_df):
    strat = DummyStrategy(Signal(side=None, price=None))
    rm = DummyRiskManager(stop_price=0.0, lot=0.0)
    ee = EntryExit(strategy=strat, risk_manager=rm, atr_series=None)
    ee.current_balance = 1000.0
    order = ee.generate_entry_order(simple_df, Position())
    assert not order.exist


def test_generate_exit_order_stop_loss(simple_df):
    df = simple_df.copy()
    # この代入でも警告が出なくなります
    df.loc[df.index[-1], "low"] = 0.5
    strat = DummyStrategy(Signal(side="SELL", price=50.0))
    ee = EntryExit(strategy=strat, risk_manager=None, atr_series=None)
    pos = Position(exist=True, side="BUY", entry_price=10.0, lot=1.0, stop_price=1.0)
    order = ee.generate_exit_order(df, pos)
    assert order.exist
    assert order.side == "SELL"
    assert order.price == pytest.approx(1.0)


def test_generate_exit_order_sell_signal(simple_df):
    strat = DummyStrategy(Signal(side="SELL", price=80.0))
    ee = EntryExit(strategy=strat, risk_manager=None, atr_series=None)
    pos = Position(exist=True, side="BUY", entry_price=10.0, lot=1.0, stop_price=1.0)
    order = ee.generate_exit_order(simple_df, pos)
    assert order.exist
    assert order.side == "SELL"
    assert order.price == pytest.approx(80.0)


def test_generate_exit_order_no_signal(simple_df):
    strat = DummyStrategy(Signal(side=None, price=None))
    ee = EntryExit(strategy=strat, risk_manager=None, atr_series=None)
    order = ee.generate_exit_order(simple_df, Position(exist=False))
    assert not order.exist


def test_fill_order_buy_sets_position():
    order = Order(exist=True, side="BUY", price=10.0, lot=2.0, stop_price=8.0)
    pos = Position()
    ee = EntryExit(strategy=None, risk_manager=None, atr_series=None)
    new_bal = ee.fill_order(order, pos, balance=100.0)
    assert new_bal == pytest.approx(100.0)
    assert pos.exist
    assert pos.side == "BUY"
    assert pos.entry_price == pytest.approx(10.0)
    assert pos.lot == pytest.approx(2.0)
    assert pos.stop_price == pytest.approx(8.0)
    assert pos.hold_bars == 0


def test_fill_order_sell_closes_and_profits():
    pos = Position(exist=True, side="BUY", entry_price=10.0, lot=2.0)
    order = Order(exist=True, side="SELL", price=15.0)
    ee = EntryExit(strategy=None, risk_manager=None, atr_series=None)
    new_bal = ee.fill_order(order, pos, balance=100.0)
    assert new_bal == pytest.approx(110.0)
    assert not pos.exist


def test_fill_order_no_action(simple_df):
    pos = Position(exist=True, side="BUY", entry_price=10.0, lot=1.0, stop_price=5.0)
    ee = EntryExit(strategy=None, risk_manager=None, atr_series=None)
    order1 = Order(exist=False)
    bal1 = ee.fill_order(order1, pos, balance=50.0)
    assert bal1 == pytest.approx(50.0)
    order2 = Order(exist=True, side="BUY", price=10.0, lot=0.0, stop_price=5.0)
    bal2 = ee.fill_order(order2, pos, balance=50.0)
    assert bal2 == pytest.approx(50.0)
