"""
tests/integration/okcoinjp/test_okcoinjp_e2e.py

OKCoin Japan 上で
  ・残高照会
  ・OHLCV取得
  ・注文・キャンセル
の統合テスト（雛形のみ／必要時に実装）
"""

import os

import pytest

# from crypto_bot.execution.okcoinjp_client import OkcoinJpClient


@pytest.fixture(scope="module")
def okcoinjp_client():
    # api_key = os.getenv("OKCOINJP_API_KEY")
    # api_secret = os.getenv("OKCOINJP_API_SECRET")
    # if not api_key or not api_secret:
    #     pytest.skip("OKCoinJP keys not set in ENV or .env")
    # client = OkcoinJpClient(api_key, api_secret)
    # yield client
    # try:
    #     client.cancel_all_orders(symbol="BTC/JPY")
    # except Exception:
    #     pass
    pass


def test_fetch_balance(okcoinjp_client):
    pass


def test_fetch_ohlcv(okcoinjp_client):
    pass


def test_place_and_cancel_order(okcoinjp_client):
    pass
