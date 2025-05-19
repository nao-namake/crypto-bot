import pytest

from crypto_bot.execution.bitbank_client import BitbankClient
from crypto_bot.execution.bitflyer_client import BitflyerClient
from crypto_bot.execution.bybit_client import BybitTestnetClient
from crypto_bot.execution.factory import create_exchange_client
from crypto_bot.execution.okcoinjp_client import OkcoinJpClient


@pytest.mark.parametrize(
    "exchange_id, expected_cls",
    [
        ("bybit", BybitTestnetClient),
        ("ByBit_TestNet", BybitTestnetClient),
        ("bitbank", BitbankClient),
        ("bitflyer", BitflyerClient),
        ("okcoinjp", OkcoinJpClient),
        ("okj", OkcoinJpClient),
    ],
)
def test_factory_returns_correct_class(monkeypatch, exchange_id, expected_cls):
    """
    create_exchange_client が文字列から正しいクライアントクラスを
    返すことを検証する。
    """
    # __init__ をモックして実際の接続は行わない
    monkeypatch.setattr(expected_cls, "__init__", lambda self, *a, **k: None)

    client = create_exchange_client(
        exchange_id, api_key="dummy", api_secret="dummy", testnet=False
    )
    assert isinstance(client, expected_cls)
