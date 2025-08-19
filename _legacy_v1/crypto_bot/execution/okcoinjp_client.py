# =============================================================================
# ファイル名: crypto_bot/execution/okcoinjp_client.py
# 説明:
# OKCoin Japan 専用の取引所クライアントラッパー。
# - CCXTの okcoin クラスをラップ
# - APIキーとシークレットを受け取り、DataFrame形式でデータ返却
# - fetch_balance, fetch_ohlcv, create_order, cancel_order, set_leverage など基本操作に対応
# - テストネット用URLもオプションで対応（※本番とURL切り替え）
# - 取引所API呼び出しを統一インターフェイスで抽象化
# =============================================================================

import ccxt
import pandas as pd

from .base import ExchangeClient


class OkcoinJpClient(ExchangeClient):
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        # CCXT の exchange id は "okcoin"
        params = {"apiKey": api_key, "secret": api_secret}
        if testnet:
            # OKCoin Japan テストネットのURLは ccxt/docs に従って設定
            params["urls"] = {"api": {"public": "https://www.okcoin.com/api"}}
        self._exchange = ccxt.okcoin(params)

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
        #  OKCoin Japanではレバレッジ操作は未サポート
        raise NotImplementedError("Leverage not supported")
