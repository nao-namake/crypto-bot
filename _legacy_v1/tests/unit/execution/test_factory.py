# tests/unit/execution/test_factory.py
# テスト対象: crypto_bot/execution/factory.py
# 説明:
#   - create_exchange_client() が exchange_id に応じて
#     適切なクライアントインスタンスを返すことを確認
#   - 未対応 exchange_id のエラーも確認

import pytest

from crypto_bot.execution.bitbank_client import BitbankClient
from crypto_bot.execution.bitflyer_client import BitflyerClient

# 🚫 from crypto_bot.execution.bybit_client import BybitTestnetClient
# 本番に影響しないようコメントアウト
from crypto_bot.execution.factory import create_exchange_client
from crypto_bot.execution.okcoinjp_client import OkcoinJpClient


@pytest.mark.parametrize(
    "exchange_id,expected_cls",
    [
        # 🚫 Bybitテストはコメントアウト
        # ("bybit", BybitTestnetClient),
        # ("bybit-testnet", BybitTestnetClient),
        # ("BYBIT_TESTNET", BybitTestnetClient),
        ("bitbank", BitbankClient),
        ("bitflyer", BitflyerClient),
        ("okcoinjp", OkcoinJpClient),
        ("okj", OkcoinJpClient),
    ],
)
def test_create_exchange_client(exchange_id, expected_cls):
    # APIキー等はNoneでも問題ない設計なので省略
    client = create_exchange_client(exchange_id)
    assert isinstance(client, expected_cls)


def test_unknown_exchange_id():
    with pytest.raises(ValueError):
        create_exchange_client("unknownex")


def test_bybit_exchange_raises_error():
    # Bybitがコメントアウトされているため、エラーが発生することを確認
    with pytest.raises(ValueError):
        create_exchange_client("bybit")
