# tests/unit/test_execution_engine.py

from unittest.mock import Mock

import pytest

from crypto_bot.execution.engine import ExecutionEngine


@pytest.fixture
def fake_client():
    """
    create_order, cancel_order メソッドを持つモッククライアントを返す。
    デフォルトの戻り値をセットしておく。
    """
    client = Mock()
    client.create_order.return_value = {
        "order_id": "12345",
        "status": "NEW",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "qty": 0.1,
    }
    client.cancel_order.return_value = {
        "order_id": "12345",
        "status": "CANCELED",
        "symbol": "BTCUSDT",
    }
    return client


def test_place_limit_order(fake_client):
    engine = ExecutionEngine(exchange_client=fake_client)

    # LIMIT 注文を発注
    result = engine.place_order(
        symbol="BTCUSDT", side="BUY", qty=0.1, price=30000.0, order_type="LIMIT"
    )

    # fake_client.create_order が正しい引数で呼ばれたか
    fake_client.create_order.assert_called_once_with(
        symbol="BTCUSDT", side="BUY", qty=0.1, order_type="LIMIT", price=30000.0
    )

    # 戻り値がそのまま返っているか
    assert result["order_id"] == "12345"
    assert result["status"] == "NEW"


def test_place_market_order(fake_client):
    engine = ExecutionEngine(exchange_client=fake_client)

    # MARKET 注文（price を指定しない）
    result = engine.place_order(
        symbol="ETHUSDT", side="SELL", qty=2.0, order_type="MARKET"
    )

    # price キーを含めずに呼び出される
    fake_client.create_order.assert_called_with(
        symbol="ETHUSDT", side="SELL", qty=2.0, order_type="MARKET"
    )

    # モックの戻り値を受け取れること
    assert result["symbol"] == "BTCUSDT"


def test_cancel_order(fake_client):
    engine = ExecutionEngine(exchange_client=fake_client)

    result = engine.cancel_order(symbol="BTCUSDT", order_id="ABC123")

    # cancel_order が正しく呼び出されたか
    fake_client.cancel_order.assert_called_once_with(
        symbol="BTCUSDT", order_id="ABC123"
    )
    assert result["status"] == "CANCELED"


def test_place_order_error(fake_client):
    """
    API レイヤーで例外が起きた場合、そのまま伝播することを期待する。
    """
    fake_client.create_order.side_effect = Exception("API Error")
    engine = ExecutionEngine(exchange_client=fake_client)

    with pytest.raises(Exception) as excinfo:
        engine.place_order("XRPUSDT", "BUY", 100)

    assert "API Error" in str(excinfo.value)
