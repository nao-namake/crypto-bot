# crypto_bot/execution/bybit_client.py

import os
from typing import Any, Dict, List, Optional

import ccxt
import pandas as pd
from ccxt.base.errors import NotSupported
from dotenv import load_dotenv

from .base import ExchangeClient


class BybitTestnetClient(ExchangeClient):
    """
    Bybit Testnet 用クライアントラッパー (CCXT 使用)。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        default_type: str = "spot",
        dotenv_path: Optional[str] = ".env",
    ):
        # .env 読み込み
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path)

        # APIキー取得
        self.api_key = api_key or os.getenv("BYBIT_TESTNET_API_KEY")
        self.api_secret = api_secret or os.getenv("BYBIT_TESTNET_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError(
                "Set BYBIT_TESTNET_API_KEY and BYBIT_TESTNET_API_SECRET in environment"
            )

        # CCXT インスタンス生成
        params = {
            "apiKey": self.api_key,
            "secret": self.api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": default_type},
        }
        self.client = ccxt.bybit(params)

        # テストネットモード（存在する場合のみ呼び出し）
        if testnet and hasattr(self.client, "set_sandbox_mode"):
            try:
                self.client.set_sandbox_mode(True)
            except Exception:
                pass

    def fetch_balance(self) -> dict:
        """残高取得"""
        return self.client.fetch_balance()

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Any = None,
        limit: int = None,
    ) -> pd.DataFrame:
        """OHLCV データを pandas.DataFrame で返す"""
        data = self.client.fetch_ohlcv(symbol, timeframe, since, limit)
        df = pd.DataFrame(
            data,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: float = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """注文作成"""
        return self.client.create_order(
            symbol,
            type.lower(),
            side.lower(),
            amount,
            price,
            params or {},
        )

    def cancel_order(
        self,
        symbol: str,
        order_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """単一注文キャンセル"""
        return self.client.cancel_order(order_id, symbol, params or {})

    def cancel_all_orders(self, symbol: str) -> List[dict]:
        """指定シンボルの全オープン注文をキャンセル"""
        open_orders = self.client.fetch_open_orders(symbol)
        results: List[dict] = []
        for o in open_orders:
            oid = o.get("id") or o.get("orderId")
            if oid:
                results.append(self.cancel_order(symbol, oid))
        return results

    def set_leverage(
        self,
        symbol: str,
        leverage: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """契約取引でレバレッジを設定"""
        try:
            return self.client.set_leverage(leverage, symbol, params or {})
        except NotSupported:
            return {}
