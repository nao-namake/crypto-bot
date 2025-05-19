# tests/unit/test_execution_engine_retry.py

import logging
import time

import pytest

from crypto_bot.execution.engine import ExecutionEngine


class DummyClient:
    def __init__(self, side_effects):
        """
        side_effects: list of return values or exceptions
        """
        self._effects = side_effects
        self.calls = 0

    def create_order(self, **params):
        self.calls += 1
        eff = self._effects[self.calls - 1]
        if isinstance(eff, Exception):
            raise eff
        return eff

    def cancel_order(self, **params):
        self.calls += 1
        eff = self._effects[self.calls - 1]
        if isinstance(eff, Exception):
            raise eff
        return eff


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # place_order 内で使われる time.sleep を無効化
    monkeypatch.setattr(time, "sleep", lambda _: None)


def test_place_order_succeeds_first_try(caplog):
    caplog.set_level(logging.INFO)
    result = {"order_id": "ok"}
    client = DummyClient(side_effects=[result])
    ee = ExecutionEngine(exchange_client=client)

    ret = ee.place_order(symbol="FOO", side="BUY", qty=1.23, price=45.6)
    assert ret == result
    assert client.calls == 1
    assert "Placing order" in caplog.text
    assert "Order placed" in caplog.text


def test_place_order_retries_then_succeeds(caplog):
    caplog.set_level(logging.WARNING)
    client = DummyClient(
        side_effects=[
            Exception("conn error1"),
            Exception("conn error2"),
            {"order_id": "retry_ok"},
        ]
    )
    ee = ExecutionEngine(exchange_client=client)

    ret = ee.place_order(symbol="FOO", side="SELL", qty=0.5)
    assert ret == {"order_id": "retry_ok"}
    assert client.calls == 3
    assert "conn error" in caplog.text


def test_place_order_max_attempts_exceeded():
    """
    place_order で max_retries を超えた場合、
    最終的に元の例外がそのまま投げられることを確認
    """
    client = DummyClient(side_effects=[ConnectionError("fail")] * 10)
    ee = ExecutionEngine(exchange_client=client)

    with pytest.raises(ConnectionError):
        ee.place_order(symbol="X", side="BUY", qty=1.0)


@pytest.mark.parametrize(
    "method_name, max_attempts, call_kwargs",
    [
        ("place_order", 5, {"symbol": "S", "side": "BUY", "qty": 0.1}),
        ("cancel_order", 3, {"symbol": "S", "order_id": "foo123"}),
    ],
)
def test_retry_counts(method_name, max_attempts, call_kwargs):
    """
    place_order は max_retries=5、cancel_order は retry(stop_after_attempt=3)
    が正しく適用されているか確認
    """
    # side_effects を max_attempts+2 回分エラーにする
    client = DummyClient(side_effects=[ValueError("e")] * (max_attempts + 2))
    ee = ExecutionEngine(exchange_client=client)
    method = getattr(ee, method_name)

    with pytest.raises(ValueError, match="e"):
        method(**call_kwargs)

    # 呼び出し回数が max_attempts に一致すること
    assert client.calls == max_attempts
