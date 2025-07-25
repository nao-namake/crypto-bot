# crypto_bot/execution/bitflyer_client.py
# 説明:
# bitFlyer向けの取引所クライアントラッパー（ccxt利用）。
# OHLCV取得、注文発注、キャンセル等の基本機能を提供。

import ccxt
import pandas as pd

from .base import ExchangeClient


class BitflyerClient(ExchangeClient):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self._exchange = ccxt.bitflyer(
            {
                "apiKey": api_key,
                "secret": api_secret,
            }
        )

    def fetch_balance(self) -> dict:
        return self._exchange.fetch_balance()

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None) -> pd.DataFrame:
        data = self._exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        df = pd.DataFrame(
            data, columns=["ts", "open", "high", "low", "close", "volume"]
        )
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df.set_index("ts")

    def create_order(self, symbol, side, type, amount, price=None, params=None):
        params = params or {}
        return self._exchange.create_order(symbol, side, type, amount, price, params)

    def cancel_order(self, symbol, order_id):
        return self._exchange.cancel_order(order_id, {"symbol": symbol})

    def cancel_all_orders(self, symbol):
        orders = self._exchange.fetch_open_orders(symbol)
        results = []
        for o in orders:
            results.append(self._exchange.cancel_order(o["id"], {"symbol": symbol}))
        return results

    def set_leverage(self, symbol, leverage):
        # bitFlyer はレバレッジ操作未対応（現状は未実装）
        raise NotImplementedError("Leverage not supported")
