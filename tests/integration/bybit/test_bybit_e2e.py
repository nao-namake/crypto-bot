"""
tests/integration/test_bybit_e2e.py

Bybit Testnet 上で
  ・Spot（現物）
  ・USDT 無期限先物（Perpetual／linear）
の残高照会・注文・キャンセルの統合テスト。
"""

import os

import pytest
from ccxt.base.errors import AuthenticationError

from crypto_bot.execution.bybit_client import BybitTestnetClient


@pytest.fixture(scope="module")
def spot_client():
    api_key = os.getenv("BYBIT_TESTNET_API_KEY")
    api_secret = os.getenv("BYBIT_TESTNET_API_SECRET")
    if not api_key or not api_secret:
        pytest.skip("Bybit Testnet keys not set in ENV or .env")
    # 必ずAPIキー明示的に渡す
    client = BybitTestnetClient(
        api_key=api_key, api_secret=api_secret, default_type="spot"
    )
    try:
        client.fetch_balance()
    except AuthenticationError:
        pytest.skip("Spot authentication failed, skipping spot tests")
    yield client
    # クリーンアップ: 未約定注文をキャンセル
    try:
        client.cancel_all_orders(symbol="BTC/USDT")
    except Exception:
        pass


def test_spot_fetch_balance(spot_client):
    bal = spot_client.fetch_balance()
    assert isinstance(bal, dict), f"Expected dict, got {type(bal)}"
    assert "free" in bal and isinstance(
        bal["free"], dict
    ), f"Expected 'free' dict, got {bal}"


def test_spot_place_and_cancel_order(spot_client):
    symbol = "BTC/USDT"
    # 板情報取得 → 買い最良値の99% で指値
    ticker = spot_client._exchange.fetch_ticker(symbol)
    bid_price = ticker.get("bid") or ticker.get("last")
    assert bid_price, "Failed to get bid price from ticker"
    price = bid_price * 0.99

    # 最小数量取得 → 5倍（注文価値を確実に最小値以上にする）
    market = spot_client._exchange.markets[symbol]
    min_amount = market["limits"]["amount"]["min"]
    min_cost = market["limits"]["cost"]["min"] or 10  # 最小注文価値のフォールバック
    amount = max(float(min_amount) * 5, min_cost / price * 1.1)

    order = spot_client.create_order(
        symbol=symbol,
        type="limit",
        side="buy",
        amount=amount,
        price=price,
    )
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
        pytest.skip("Bybit Testnet keys not set in ENV or .env")
    client = BybitTestnetClient(
        api_key=api_key, api_secret=api_secret, default_type="future"
    )
    try:
        client.fetch_balance()
    except AuthenticationError:
        pytest.skip("Perpetual authentication failed, skipping swap tests")
    yield client
    try:
        client.cancel_all_orders(symbol="BTC/USDT")
    except Exception:
        pass


def test_swap_set_leverage_and_place_order(swap_client):
    symbol = "BTC/USDT"

    # レバレッジ設定
    resp = swap_client.set_leverage(symbol=symbol, leverage=5)
    assert isinstance(resp, dict), f"set_leverage must return dict, got {resp}"

    # 板情報取得 → 買い最良値の99% で指値
    ticker = swap_client._exchange.fetch_ticker(symbol)
    bid_price = ticker.get("bid") or ticker.get("last")
    assert bid_price, "Failed to get bid price from ticker"
    price = bid_price * 0.99

    # 最小数量取得 → 1.1倍
    market = swap_client._exchange.markets[symbol]
    min_amount = market["limits"]["amount"]["min"]
    amount = float(min_amount) * 1.1

    order = swap_client.create_order(
        symbol=symbol,
        type="limit",
        side="buy",
        amount=amount,
        price=price,
    )
    order_id = order.get("id") or order.get("order_id")
    assert order_id, f"Swap order response missing id: {order}"

    cancel_resp = swap_client.cancel_order(symbol=symbol, order_id=order_id)
    cancelled_id = cancel_resp.get("id") or cancel_resp.get("order_id")
    assert cancelled_id == order_id, f"Swap cancelled order_id mismatch: {cancel_resp}"
