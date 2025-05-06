"""
Bybit Testnet 用クライアントラッパー (CCXT 使用)。
"""

import os
import ccxt
from dotenv import load_dotenv

class BybitTestnetClient:
    def __init__(self, default_type: str = "spot", dotenv_path: str | None = ".env"):
        """
        default_type: "spot"（現物） or "swap"（無期限契約）など
        dotenv_path: ローカルで .env を読み込みたい場合に指定
        """
        # ローカル実行時に .env から読み込みたいならパスを渡す
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path)

        api_key = os.getenv("BYBIT_TESTNET_API_KEY")
        api_secret = os.getenv("BYBIT_TESTNET_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError(
                "Set BYBIT_TESTNET_API_KEY and BYBIT_TESTNET_API_SECRET in environment"
            )

        self.client = ccxt.bybit({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": default_type},
        })
        self.client.set_sandbox_mode(True)

    def fetch_balance(self) -> dict:
        """
        残高取得
        """
        return self.client.fetch_balance()

    def create_order(
        self,
        symbol: str,
        type: str,
        side: str,
        amount: float,
        price: float = None,
        params: dict = None,
    ) -> dict:
        """
        注文作成 (limit/market)
        """
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
        params: dict = None,
    ) -> dict:
        """
        単一注文キャンセル
        """
        return self.client.cancel_order(order_id, symbol, params or {})

    def cancel_all_orders(self, symbol: str) -> list[dict]:
        """
        指定シンボルの全オープン注文をキャンセル
        """
        open_orders = self.client.fetch_open_orders(symbol)
        results = []
        for o in open_orders:
            oid = o.get("id") or o.get("orderId")
            if oid:
                results.append(self.cancel_order(symbol, oid))
        return results

    def set_leverage(
        self,
        symbol: str,
        leverage: int,
        params: dict = None,
    ) -> dict:
        """
        契約取引でレバレッジを設定する
        例: BybitTestnetClient(default_type="swap").set_leverage("BTC/USDT", 5)
        """
        return self.client.set_leverage(leverage, symbol, params or {})