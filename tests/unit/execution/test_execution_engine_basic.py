# tests/unit/test_execution_engine_basic.py

import pytest

from crypto_bot.execution.engine import ExecutionEngine


class DummyClient:
    """
     place_order、cancel_order、set_leverage の呼び出しを記録し、
    あらかじめ渡した responses を返す、あるいは例外を投げるモッククライアント。
    """

    def __init__(self, create_responses=None, cancel_responses=None):
        # create_responses: place_order が返す結果または例外のリスト
        self.create_responses = create_responses or []
        self.cancel_responses = cancel_responses or []
        self.create_calls = []
        self.cancel_calls = []
        self.leverage_calls = []

    def create_order(self, **kwargs):
        self.create_calls.append(kwargs)
        if not self.create_responses:
            return {}
        ret = self.create_responses.pop(0)
        if isinstance(ret, Exception):
            raise ret
        return ret

    def cancel_order(self, **kwargs):
        self.cancel_calls.append(kwargs)
        if not self.cancel_responses:
            return {}
        ret = self.cancel_responses.pop(0)
        if isinstance(ret, Exception):
            raise ret
        return ret

    def set_leverage(self, **kwargs):
        self.leverage_calls.append(kwargs)
        return {"leverage": kwargs}


def test_place_order_success():
    client = DummyClient(create_responses=[{"orderId": "ok"}])
    ee = ExecutionEngine(exchange_client=client, max_retries=3, wait_seconds=0)
    res = ee.place_order("BTC/USDT", "BUY", qty=1, price=100, order_type="LIMIT")
    assert res == {"orderId": "ok"}
    assert len(client.create_calls) == 1
    call = client.create_calls[0]
    assert call["symbol"] == "BTC/USDT"
    assert call["side"] == "BUY"
    assert call["qty"] == 1
    assert call["price"] == 100
    assert call["order_type"] == "LIMIT"


def test_place_order_retry_and_succeed():
    # 最初2回は例外、その後成功
    errors = [RuntimeError("err1"), RuntimeError("err2"), {"ok": True}]
    client = DummyClient(create_responses=errors.copy())
    ee = ExecutionEngine(exchange_client=client, max_retries=5, wait_seconds=0)
    res = ee.place_order("X", "SELL", qty=2)
    assert res == {"ok": True}
    # create_order は3回呼ばれるはず
    assert len(client.create_calls) == 3


def test_place_order_exhaust_retries():
    # 全部失敗すると最終例外が伝播
    errors = [ValueError("bad")] * 4
    client = DummyClient(create_responses=errors.copy())
    ee = ExecutionEngine(exchange_client=client, max_retries=3, wait_seconds=0)
    with pytest.raises(ValueError) as excinfo:
        ee.place_order("SYM", "BUY", qty=1)
    assert "bad" in str(excinfo.value)
    # 3回呼ばれた
    assert len(client.create_calls) == 3


def test_cancel_order_basic():
    client = DummyClient(cancel_responses=[{"cancelled": True}])
    ee = ExecutionEngine(exchange_client=client, max_retries=3, wait_seconds=0)
    res = ee.cancel_order(symbol="BTC/USDT", order_id="foo123")
    assert res == {"cancelled": True}
    assert len(client.cancel_calls) == 1
    assert client.cancel_calls[0] == {"symbol": "BTC/USDT", "order_id": "foo123"}


def test_set_leverage_calls_client():
    client = DummyClient()
    ee = ExecutionEngine(exchange_client=client)
    res = ee.set_leverage(symbol="BTC/USDT", leverage=5)
    assert res == {"leverage": {"symbol": "BTC/USDT", "leverage": 5}}
    assert client.leverage_calls == [{"symbol": "BTC/USDT", "leverage": 5}]
