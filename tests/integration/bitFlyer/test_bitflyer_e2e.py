"""
tests/integration/bitflyer/test_bitflyer_e2e.py

bitFlyer 上で
  ・残高照会
  ・OHLCV取得
  ・注文・キャンセル
の統合テスト（雛形のみ／必要時に実装）
"""

import pytest

# from crypto_bot.execution.bitflyer_client import BitflyerClient


@pytest.fixture(scope="module")
def bitflyer_client():
    # api_key = os.getenv("BITFLYER_API_KEY")
    # api_secret = os.getenv("BITFLYER_API_SECRET")
    # if not api_key or not api_secret:
    #     pytest.skip("Bitflyer keys not set in ENV or .env")
    # client = BitflyerClient(api_key, api_secret)
    # yield client
    # try:
    #     client.cancel_all_orders(symbol="BTC/JPY")
    # except Exception:
    #     pass
    pass


def test_fetch_balance(bitflyer_client):
    pass


def test_fetch_ohlcv(bitflyer_client):
    pass


def test_place_and_cancel_order(bitflyer_client):
    pass
