"""
tests/integration/bitbank/test_bitbank_e2e.py

Bitbank 上で
  ・残高照会
  ・OHLCV取得
  ・注文・キャンセル
の統合テスト（雛形だけ用意、本番運用時に実装する）
"""

import os

import pytest

# 必要な時点で import する
# from crypto_bot.execution.bitbank_client import BitbankClient


@pytest.fixture(scope="module")
def bitbank_client():
    # api_key = os.getenv("BITBANK_API_KEY")
    # api_secret = os.getenv("BITBANK_API_SECRET")
    # if not api_key or not api_secret:
    #     pytest.skip("Bitbank keys not set in ENV or .env")
    # client = BitbankClient(api_key, api_secret)
    # yield client
    # try:
    #     client.cancel_all_orders(symbol="BTC/JPY")
    # except Exception:
    #     pass
    pass  # 雛形なので空でOK


def test_fetch_balance(bitbank_client):
    pass


def test_fetch_ohlcv(bitbank_client):
    pass


def test_place_and_cancel_order(bitbank_client):
    pass
