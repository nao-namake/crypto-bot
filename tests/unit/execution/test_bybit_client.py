# tests/unit/execution/test_bybit_client.py
# テスト対象: crypto_bot/execution/bybit_client.py
# 説明:
#   - BybitTestnetClient: Bybit APIラッパー
#   - 注文・キャンセル・残高照会等の基本機能

import pytest

from crypto_bot.execution.bybit_client import BybitTestnetClient


@pytest.fixture
def mock_ccxt_bybit(monkeypatch):
    """ccxt.bybit の全メソッドをダミー化"""

    class DummyExchange:
        def __init__(self, *a, **kw):
            self.apiKey = None
            self.secret = None

        def fetch_balance(self):
            return {"USDT": 999}

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
            return [[1710000000000, 30000, 31000, 29900, 30500, 0.5]]

        def create_order(self, symbol, type, side, amount, price=None, params=None):
            return {"order_id": "bybit123", "status": "open"}

        def cancel_order(self, order_id, symbol, params=None):
            return {"order_id": order_id, "status": "cancelled"}

        def fetch_open_orders(self, symbol):
            return [{"id": "bybit123"}]

        def set_sandbox_mode(self, v):
            pass

        def set_leverage(self, leverage, symbol, params=None):
            if leverage == 99:
                # 疑似的に NotSupported を投げる
                from ccxt.base.errors import NotSupported

                raise NotSupported()
            return {"symbol": symbol, "leverage": leverage}

    monkeypatch.setattr("ccxt.bybit", lambda *a, **kw: DummyExchange())


def test_fetch_balance(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="x", api_secret="y")
    res = client.fetch_balance()
    assert res == {"USDT": 999}


def test_fetch_ohlcv(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="x", api_secret="y")
    res = client.fetch_ohlcv("BTC/USDT", "1m")
    assert isinstance(res, list)
    assert res[0][1] == 30000


def test_create_order(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="x", api_secret="y")
    res = client.create_order("BTC/USDT", "buy", "limit", 0.01, price=30000)
    assert res["status"] == "open"


def test_cancel_order(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="x", api_secret="y")
    res = client.cancel_order("BTC/USDT", "bybit123")
    assert res["order_id"] == "bybit123"
    assert res["status"] == "cancelled"


def test_cancel_all_orders(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="x", api_secret="y")
    res = client.cancel_all_orders("BTC/USDT")
    assert isinstance(res, list)
    assert res[0]["status"] == "cancelled"


def test_set_leverage(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="x", api_secret="y")
    res = client.set_leverage("BTC/USDT", 10)
    assert res["leverage"] == 10


def test_set_leverage_notsupported(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="x", api_secret="y")
    # leverage=99で NotSupported エラーを疑似発生 → 空dictを返す想定
    res = client.set_leverage("BTC/USDT", 99)
    assert res == {}
