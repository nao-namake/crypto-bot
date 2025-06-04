# tests/unit/execution/test_execution_engine.py
# テスト対象: crypto_bot/execution/engine.py
# 説明:
#   - ExecutionEngine: 注文実行エンジン
#   - シグナル→注文→約定→ポジション管理の一連の流れ

import pandas as pd
import pytest

from crypto_bot.execution.engine import (
    EntryExit,
    ExecutionEngine,
    Order,
    Position,
    Signal,
)


class DummyStrategy:
    """常にBUY→SELLを返すシンプル戦略"""

    def __init__(self):
        self.count = 0

    def logic_signal(self, price_df, position):
        if not position.exist:
            return Signal(side="BUY", price=100)
        else:
            # 2回目はSELL
            return Signal(side="SELL", price=105)


class DummyRiskManager:
    def calc_stop_price(self, entry_price, atr_series):
        return entry_price - 10

    def calc_lot(self, balance, entry_price, stop_price):
        return 1.0


@pytest.fixture
def entry_exit():
    strat = DummyStrategy()
    risk = DummyRiskManager()
    atr = None
    ee = EntryExit(strat, risk, atr)
    ee.current_balance = 1000
    return ee


def test_generate_entry_order(entry_exit):
    pos = Position()
    price_df = None  # ダミー
    order = entry_exit.generate_entry_order(price_df, pos)
    assert order.exist is True
    assert order.side == "BUY"
    assert order.price == 100
    assert order.lot == 1.0


def test_generate_exit_order(entry_exit):
    pos = Position(exist=True, side="BUY", entry_price=100, lot=1.0, stop_price=90)
    # stop-lossトリガー：low <= stop_price
    price_df = pd.DataFrame({"low": [90]})
    order = entry_exit.generate_exit_order(price_df, pos)
    assert order.exist is True
    assert order.side == "SELL"
    assert order.price == 90


def test_fill_order_entry_and_exit(entry_exit):
    pos = Position()
    # エントリー
    entry_order = Order(exist=True, side="BUY", price=100, lot=1.0, stop_price=90)
    bal = entry_exit.fill_order(entry_order, pos, 1000)
    assert pos.exist is True
    assert pos.entry_price == 100
    # イグジット
    exit_order = Order(exist=True, side="SELL", price=110, lot=1.0)
    bal2 = entry_exit.fill_order(exit_order, pos, bal)
    assert pos.exist is False
    assert bal2 == bal + 10


class DummyClient:
    def __init__(self):
        self.orders = []
        self.leverage_set = []

    def create_order(self, **kwargs):
        self.orders.append(kwargs)
        return {"order_id": "123"}

    def cancel_order(self, order_id, symbol=None, **kwargs):
        return {"order_id": order_id, "status": "cancelled"}

    def set_leverage(self, *a, **kw):
        self.leverage_set.append((a, kw))
        return {"ok": True}


def test_execution_engine_place_order(monkeypatch):
    cli = DummyClient()
    engine = ExecutionEngine(client=cli)
    res = engine.place_order("BTC/USDT", "BUY", 0.1, price=100, order_type="LIMIT")
    assert res["order_id"] == "123"
    assert cli.orders[0]["symbol"] == "BTC/USDT"


def test_execution_engine_cancel_order():
    cli = DummyClient()
    engine = ExecutionEngine(client=cli)
    res = engine.cancel_order("BTC/USDT", "12345")
    assert res["status"] == "cancelled"


def test_execution_engine_set_leverage():
    cli = DummyClient()
    engine = ExecutionEngine(client=cli)
    res = engine.set_leverage("BTC/USDT", 5)
    assert res["ok"] is True
    assert cli.leverage_set
