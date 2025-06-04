# tests/unit/execution/test_bitflyer_client.py
# テスト対象: crypto_bot/execution/bitflyer_client.py
# 説明:
#   - BitflyerClient: bitFlyer APIラッパー
#   - 注文・キャンセル・残高照会等の基本機能

import pandas as pd
import pytest

from crypto_bot.execution.bitflyer_client import BitflyerClient


@pytest.fixture
def mock_ccxt_bitflyer(monkeypatch):
    """ccxt.bitflyer の全メソッドをダミー化"""

    class DummyExchange:
        def fetch_balance(self):
            return {"JPY": 100000}

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
            return [[1710000000000, 2, 3, 1, 2.5, 0.02]]

        def create_order(self, symbol, side, type, amount, price=None, params=None):
            return {"order_id": "bf123", "status": "open"}

        def cancel_order(self, order_id, params=None):
            return {"order_id": order_id, "status": "cancelled"}

        def fetch_open_orders(self, symbol):
            return [{"id": "bf123"}]

    monkeypatch.setattr("ccxt.bitflyer", lambda *a, **kw: DummyExchange())


def test_fetch_balance(mock_ccxt_bitflyer):
    client = BitflyerClient(api_key="x", api_secret="y")
    res = client.fetch_balance()
    assert res == {"JPY": 100000}


def test_fetch_ohlcv(mock_ccxt_bitflyer):
    client = BitflyerClient(api_key="x", api_secret="y")
    df = client.fetch_ohlcv("BTC/JPY", "1m")
    assert isinstance(df, pd.DataFrame)
    assert "open" in df.columns
    assert df.iloc[0]["open"] == 2


def test_create_order(mock_ccxt_bitflyer):
    client = BitflyerClient(api_key="x", api_secret="y")
    res = client.create_order("BTC/JPY", "buy", "limit", 0.01, price=6000000)
    assert res["status"] == "open"


def test_cancel_order(mock_ccxt_bitflyer):
    client = BitflyerClient(api_key="x", api_secret="y")
    res = client.cancel_order("BTC/JPY", "bf123")
    assert res["order_id"] == "bf123"
    assert res["status"] == "cancelled"


def test_cancel_all_orders(mock_ccxt_bitflyer):
    client = BitflyerClient(api_key="x", api_secret="y")
    res = client.cancel_all_orders("BTC/JPY")
    assert isinstance(res, list)
    assert res[0]["status"] == "cancelled"


def test_set_leverage_raises(mock_ccxt_bitflyer):
    client = BitflyerClient(api_key="x", api_secret="y")
    with pytest.raises(NotImplementedError):
        client.set_leverage("BTC/JPY", 2)
