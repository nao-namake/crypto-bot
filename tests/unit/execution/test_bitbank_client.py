# tests/unit/execution/test_bitbank_client.py
# テスト対象: crypto_bot/execution/bitbank_client.py
# 説明:
#   - BitbankClient: bitbank.cc APIラッパー
#   - 注文・キャンセル・残高照会等の基本機能

import pytest

from crypto_bot.execution.bitbank_client import BitbankClient


@pytest.fixture
def mock_ccxt_bitbank(monkeypatch):
    """ccxt.bitbankの全メソッドをモック化"""

    class DummyExchange:
        def fetch_balance(self):
            return {"JPY": 10000}

        def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None):
            # ダミーOHLCVデータ
            return [[1710000000000, 1, 2, 0, 1.5, 0.01]]

        def create_order(self, symbol, side, type, amount, price=None, params=None):
            return {"order_id": "abc123", "status": "open"}

        def cancel_order(self, order_id, params=None):
            return {"order_id": order_id, "status": "cancelled"}

        def fetch_open_orders(self, symbol):
            return [{"id": "abc123"}]

    monkeypatch.setattr("ccxt.bitbank", lambda *a, **kw: DummyExchange())


def test_fetch_balance(mock_ccxt_bitbank):
    client = BitbankClient(api_key="x", api_secret="y")
    result = client.fetch_balance()
    assert result == {"JPY": 10000}


def test_fetch_ohlcv(mock_ccxt_bitbank):
    client = BitbankClient(api_key="x", api_secret="y")
    data = client.fetch_ohlcv("BTC/JPY", "1m")
    assert isinstance(data, list)
    assert len(data) > 0
    # OHLCV データ構造確認: [timestamp, open, high, low, close, volume]
    assert len(data[0]) == 6  # OHLCV + volume
    assert data[0][1] == 1  # open価格


def test_create_order(mock_ccxt_bitbank):
    client = BitbankClient(api_key="x", api_secret="y")
    res = client.create_order("BTC/JPY", "buy", "limit", 0.01, price=5000000)
    assert res["status"] == "open"


def test_cancel_order(mock_ccxt_bitbank):
    client = BitbankClient(api_key="x", api_secret="y")
    res = client.cancel_order("BTC/JPY", "abc123")
    assert res["order_id"] == "abc123"
    assert res["status"] == "cancelled"


def test_cancel_all_orders(mock_ccxt_bitbank):
    client = BitbankClient(api_key="x", api_secret="y")
    res = client.cancel_all_orders("BTC/JPY")
    assert isinstance(res, list)
    assert res[0]["status"] == "cancelled"


def test_set_leverage_raises(mock_ccxt_bitbank):
    client = BitbankClient(api_key="x", api_secret="y")
    with pytest.raises(NotImplementedError):
        client.set_leverage("BTC/JPY", 2)
