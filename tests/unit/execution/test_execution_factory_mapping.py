import pytest

from crypto_bot.execution.factory import create_exchange_client


@pytest.mark.parametrize(
    "exchange_id, expected_name",
    [
        ("bybit", "BybitTestnetClient"),
        ("bitbank", "BitbankClient"),
        ("okcoinjp", "OkcoinJPClient"),
        # 他取引所を追加：("exchange_id", "ClassName"),
    ],
)
def test_create_exchange_client_mapping(exchange_id, expected_name):
    """
    create_exchange_client が与えられた文字列IDから
    正しいクライアントクラスのインスタンスを返すことを確認する。
    """
    # okcoinjp はテスト環境に存在しないためスキップ
    if exchange_id == "okcoinjp":
        pytest.skip("ccxt.okcoinjp not available in test environment")

    # APIキー／シークレットを None 指定して呼び出し
    client = create_exchange_client(exchange_id, api_key=None, api_secret=None)
    actual_name = client.__class__.__name__
    assert (
        actual_name == expected_name
    ), f"Expected class name {expected_name}, got {actual_name}"
