import pytest

from crypto_bot.execution.factory import create_exchange_client


@pytest.mark.parametrize(
    "exchange_id",
    ["bybit", "bitbank", "okcoinjp"],
)
def test_client_basic_methods(exchange_id):
    """
    各取引所IDからクライアントを生成し、基本的なメソッドを提供していることを確認する。
    """
    if exchange_id == "okcoinjp":
        pytest.skip("ccxt.okcoinjp not available in test environment")
    client = create_exchange_client(exchange_id, api_key=None, api_secret=None)
    assert client is not None
    assert client.__class__.__name__.lower().startswith(exchange_id)
