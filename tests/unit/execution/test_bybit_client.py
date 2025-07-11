# tests/unit/execution/test_bybit_client.py
# テスト対象: crypto_bot/execution/bybit_client.py
# 🚫 Bybit関連テスト - 本番に影響しないよう全てコメントアウト

"""
import pytest

from crypto_bot.execution.bybit_client import BybitTestnetClient


@pytest.fixture
def mock_ccxt_bybit(monkeypatch):
    # ccxt.bybit の全メソッドをダミー化

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
            return {"order_id": order_id, "status": "canceled"}

        def fetch_open_orders(self, symbol=None, since=None, limit=None):
            return [{"order_id": "open1", "symbol": "BTC/USDT"}]

        def cancel_all_orders(self, symbol=None, params=None):
            return [{"order_id": "all1", "status": "canceled"}]

        def fetch_ticker(self, symbol):
            return {"last": 30000, "bid": 29999, "ask": 30001}

        def fetch_trades(self, symbol, since=None, limit=None, params=None):
            return [{"id": "trade1", "price": 30000, "amount": 0.1}]

        def fetch_order_book(self, symbol, limit=None, params=None):
            return {
                "bids": [[29999, 1.0]],
                "asks": [[30001, 1.0]]
            }

        def fetch_positions(self, symbols):
            return [{"symbol": "BTC/USDT", "size": 0.5}]

        def set_leverage(self, leverage, symbol, params=None):
            return {"leverage": leverage}

        def switch_account_type(self, account_type, params=None):
            return {"account_type": account_type}

    monkeypatch.setattr("ccxt.bybit", DummyExchange)
    return DummyExchange


def test_bybit_client_init(mock_ccxt_bybit):
    client = BybitTestnetClient(api_key="test_key", api_secret="test_secret")
    assert client.exchange_id == "bybit"
    assert client.is_testnet is True


def test_fetch_balance(mock_ccxt_bybit):
    client = BybitTestnetClient()
    balance = client.fetch_balance()
    assert balance["USDT"] == 999


def test_fetch_ohlcv(mock_ccxt_bybit):
    client = BybitTestnetClient()
    data = client.fetch_ohlcv("BTC/USDT", "1h", limit=10)
    assert len(data) == 1
    assert data[0][4] == 30500  # close price


def test_create_order(mock_ccxt_bybit):
    client = BybitTestnetClient()
    order = client.create_order(
        symbol="BTC/USDT",
        side="buy",
        type="limit",
        amount=0.01,
        price=30000
    )
    assert order["order_id"] == "bybit123"


def test_cancel_order(mock_ccxt_bybit):
    client = BybitTestnetClient()
    result = client.cancel_order("order123", "BTC/USDT")
    assert result["order_id"] == "order123"
    assert result["status"] == "canceled"


def test_fetch_open_orders(mock_ccxt_bybit):
    client = BybitTestnetClient()
    orders = client.fetch_open_orders("BTC/USDT")
    assert len(orders) == 1
    assert orders[0]["order_id"] == "open1"


def test_cancel_all_orders(mock_ccxt_bybit):
    client = BybitTestnetClient()
    results = client.cancel_all_orders("BTC/USDT")
    assert len(results) == 1
    assert results[0]["status"] == "canceled"


def test_fetch_ticker(mock_ccxt_bybit):
    client = BybitTestnetClient()
    ticker = client.fetch_ticker("BTC/USDT")
    assert ticker["last"] == 30000


def test_fetch_trades(mock_ccxt_bybit):
    client = BybitTestnetClient()
    trades = client.fetch_trades("BTC/USDT", limit=5)
    assert len(trades) == 1
    assert trades[0]["price"] == 30000


def test_fetch_order_book(mock_ccxt_bybit):
    client = BybitTestnetClient()
    orderbook = client.fetch_order_book("BTC/USDT")
    assert len(orderbook["bids"]) == 1
    assert len(orderbook["asks"]) == 1


def test_get_position_info(mock_ccxt_bybit):
    client = BybitTestnetClient()
    positions = client.get_position_info("BTC/USDT")
    assert len(positions) == 1
    assert positions[0]["symbol"] == "BTC/USDT"


def test_set_leverage(mock_ccxt_bybit):
    client = BybitTestnetClient()
    result = client.set_leverage(10, "BTC/USDT")
    assert result["leverage"] == 10


def test_enable_unified_margin(mock_ccxt_bybit):
    client = BybitTestnetClient()
    result = client.enable_unified_margin("unified")
    assert result["account_type"] == "unified"


def test_fallback_getattr(mock_ccxt_bybit):
    # 未定義メソッドのフォールバック
    client = BybitTestnetClient()
    # ccxt 内部の属性にアクセスできる
    assert hasattr(client, "apiKey")
"""

# ⚠️ 本番環境ではBitbankClient関連のテストを実行してください
