"""
tests/integration/test_bybit_e2e.py

Bybit Testnet 上で Spot（現物）と Swap（無期限契約）の
残高照会・注文・キャンセルの統合テスト。
"""
import os
import pytest
import ccxt
from ccxt.base.errors import AuthenticationError, InvalidOrder, NotSupported, InsufficientFunds

from crypto_bot.execution.bybit_client import BybitTestnetClient

@pytest.fixture(scope="module")
def spot_client():
    api_key = os.getenv("BYBIT_TESTNET_API_KEY")
    api_secret = os.getenv("BYBIT_TESTNET_API_SECRET")
    if not api_key or not api_secret:
        pytest.skip("Bybit Testnet keys not set in .env")
    client = BybitTestnetClient(default_type="spot")
    # 認証チェック
    try:
        client.fetch_balance()
    except AuthenticationError:
        pytest.skip("Spot authentication failed, skipping spot tests")
    yield client
    # 後片付け：未約定注文をキャンセル
    try:
        client.cancel_all_orders(symbol="BTC/USDT")
    except Exception:
        pass


def test_spot_fetch_balance(spot_client):
    bal = spot_client.fetch_balance()
    # 辞書として返ってくることをチェック
    assert isinstance(bal, dict), f"Expected dict, got {type(bal)}"
    assert "free" in bal and isinstance(bal["free"], dict), f"Expected 'free' dict, got {bal}"


def test_spot_place_and_cancel_order(spot_client):
    symbol = "BTC/USDT"
    try:
        order = spot_client.create_order(
            symbol=symbol,
            type="limit",
            side="buy",
            # Testnet 環境では最小注文量・USDT残高に応じて調整してください
            amount=0.001,
            price=1000,
        )
    except (InvalidOrder, InsufficientFunds) as e:
        pytest.skip(f"Spot order cannot be placed, skipping spot order test: {e}")

    order_id = order.get("id") or order.get("order_id")
    assert order_id, f"Order response missing id: {order}"

    cancel_resp = spot_client.cancel_order(symbol=symbol, order_id=order_id)
    cancelled_id = cancel_resp.get("id") or cancel_resp.get("order_id")
    assert cancelled_id == order_id, f"Cancelled order_id mismatch: {cancel_resp}"


@pytest.fixture(scope="module")
def swap_client():
    api_key = os.getenv("BYBIT_TESTNET_API_KEY")
    api_secret = os.getenv("BYBIT_TESTNET_API_SECRET")
    if not api_key or not api_secret:
        pytest.skip("Bybit Testnet keys not set in .env")
    client = BybitTestnetClient(default_type="swap")
    try:
        client.fetch_balance()
    except AuthenticationError:
        pytest.skip("Swap authentication failed, skipping swap tests")
    yield client
    try:
        client.cancel_all_orders(symbol="BTC/USDT")
    except Exception:
        pass


def test_swap_set_leverage_and_place_order(swap_client):
    symbol = "BTC/USDT"
    try:
        resp = swap_client.set_leverage(symbol=symbol, leverage=5)
        assert isinstance(resp, dict), f"set_leverage must return dict, got {resp}"
    except NotSupported as e:
        pytest.skip(f"Swap setLeverage not supported, skipping swap tests: {e}")

    try:
        order = swap_client.create_order(
            symbol=symbol,
            type="limit",
            side="buy",
            amount=1,
            price=1000,
        )
    except (InvalidOrder, InsufficientFunds) as e:
        pytest.skip(f"Swap order cannot be placed, skipping swap order test: {e}")

    order_id = order.get("id") or order.get("order_id")
    assert order_id, f"Swap order response missing id: {order}"

    cancel_resp = swap_client.cancel_order(symbol=symbol, order_id=order_id)
    cancelled_id = cancel_resp.get("id") or cancel_resp.get("order_id")
    assert cancelled_id == order_id, f"Swap cancelled order_id mismatch: {cancel_resp}"