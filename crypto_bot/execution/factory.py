# crypto_bot/execution/factory.py

from .bitbank_client import BitbankClient
from .bitflyer_client import BitflyerClient
from .bybit_client import BybitTestnetClient
from .okcoinjp_client import OkcoinJpClient


def create_exchange_client(
    exchange_id: str,
    api_key: str,
    api_secret: str,
    testnet: bool = True,
    **kwargs,
):
    eid = exchange_id.lower()
    if eid in ("bybit", "bybit-testnet", "bybit_testnet"):
        return BybitTestnetClient(api_key, api_secret, testnet=testnet)
    if eid == "bitbank":
        return BitbankClient(api_key, api_secret, testnet=testnet)
    if eid == "bitflyer":
        return BitflyerClient(api_key, api_secret, testnet=testnet)
    if eid in ("okcoinjp", "okj"):
        return OkcoinJpClient(api_key, api_secret, testnet=testnet)
    raise ValueError(f"Unknown exchange_id: {exchange_id}")
