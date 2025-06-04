# tests/unit/execution/test_okcoinjp_client.py
# テスト対象: crypto_bot/execution/okcoinjp_client.py
# 説明:
#   - OkcoinJpClient の初期化と基本メソッドが呼べるかをテスト
#   - レバレッジ未対応（例外）の動作もチェック

from unittest.mock import MagicMock, patch

import pytest

from crypto_bot.execution.okcoinjp_client import OkcoinJpClient


@patch("ccxt.okcoin")
def test_okcoinjp_client_init(mock_ccxt):
    # ccxt.okcoinインスタンスはMagicMockで代用
    mock_exch = MagicMock()
    mock_ccxt.return_value = mock_exch

    client = OkcoinJpClient(api_key="key", api_secret="secret", testnet=False)
    assert hasattr(client, "_exchange")
    mock_ccxt.assert_called_once()


@patch("ccxt.okcoin")
def test_fetch_balance(mock_ccxt):
    mock_exch = MagicMock()
    mock_exch.fetch_balance.return_value = {"JPY": 10000}
    mock_ccxt.return_value = mock_exch

    client = OkcoinJpClient("key", "secret")
    result = client.fetch_balance()
    assert result == {"JPY": 10000}


@patch("ccxt.okcoin")
def test_fetch_ohlcv(mock_ccxt):
    # サンプルデータ
    sample = [
        [1710000000000, 1, 2, 0.5, 1.5, 100],
        [1710000001000, 1.5, 2.1, 1.0, 1.8, 80],
    ]
    mock_exch = MagicMock()
    mock_exch.fetch_ohlcv.return_value = sample
    mock_ccxt.return_value = mock_exch

    client = OkcoinJpClient("key", "secret")
    df = client.fetch_ohlcv("BTC/JPY", "1m")
    assert not df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


@patch("ccxt.okcoin")
def test_create_order(mock_ccxt):
    mock_exch = MagicMock()
    mock_exch.create_order.return_value = {"id": "orderid"}
    mock_ccxt.return_value = mock_exch

    client = OkcoinJpClient("key", "secret")
    result = client.create_order("BTC/JPY", "buy", "limit", 0.1, 5000000)
    assert result["id"] == "orderid"


@patch("ccxt.okcoin")
def test_cancel_order(mock_ccxt):
    mock_exch = MagicMock()
    mock_exch.cancel_order.return_value = {"status": "canceled"}
    mock_ccxt.return_value = mock_exch

    client = OkcoinJpClient("key", "secret")
    result = client.cancel_order("BTC/JPY", "orderid")
    assert result["status"] == "canceled"


@patch("ccxt.okcoin")
def test_cancel_all_orders(mock_ccxt):
    mock_exch = MagicMock()
    mock_exch.fetch_open_orders.return_value = [{"id": "id1"}, {"id": "id2"}]
    mock_exch.cancel_order.side_effect = [
        {"status": "canceled"},
        {"status": "canceled"},
    ]
    mock_ccxt.return_value = mock_exch

    client = OkcoinJpClient("key", "secret")
    results = client.cancel_all_orders("BTC/JPY")
    assert all(r["status"] == "canceled" for r in results)


@patch("ccxt.okcoin")
def test_set_leverage_not_supported(mock_ccxt):
    mock_ccxt.return_value = MagicMock()
    client = OkcoinJpClient("key", "secret")
    with pytest.raises(NotImplementedError):
        client.set_leverage("BTC/JPY", 2)
