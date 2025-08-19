# =============================================================================
# ファイル名: crypto_bot/execution/bybit_client.py
# 説明:
# 🚫 Bybit Testnet専用の取引所クライアントラッパー（本番に影響しないようコメントアウト）
# - 本番環境はBitbank専用システムに移行済み
# - Bybit関連機能は保持するが非アクティブ化
# =============================================================================

# 🚫 Bybit関連コード - 本番に影響しないよう全てコメントアウト
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

import ccxt
from ccxt.base.errors import NotSupported
from dotenv import load_dotenv

from .base import ExchangeClient


class BybitTestnetClient(ExchangeClient):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
    ):
        # 環境変数を自動読み込み（.envファイルサポート）
        load_dotenv()

        # API キーが明示的に渡されない場合は環境変数から取得
        if api_key is None:
            api_key = os.getenv("BYBIT_TESTNET_API_KEY")
        if api_secret is None:
            api_secret = os.getenv("BYBIT_TESTNET_API_SECRET")

        # CCXT Bybit初期化
        self._exchange = ccxt.bybit(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "sandbox": testnet,  # True でテストネット使用
                "enableRateLimit": True,
                "rateLimit": 120,  # API 制限対応
                "options": {
                    "defaultType": "linear",  # デリバティブ取引用設定
                },
                "urls": {
                    "api": ("https://api-testnet.bybit.com" if testnet
                           else "https://api.bybit.com")
                },
            }
        )

    def __getattr__(self, name: str) -> Any:
        # 未定義メソッド・属性は内部のccxt.bybitへ自動フォールバック
        return getattr(self._exchange, name)

    def fetch_balance(self) -> Dict[str, Any]:
        return self._exchange.fetch_balance()

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[List[Union[int, float]]]:
        return self._exchange.fetch_ohlcv(symbol, timeframe, since, limit)

    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._exchange.create_order(
            symbol, side, type, amount, price, params or {}
        )

    def cancel_order(
        self, order_id: str, symbol: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self._exchange.cancel_order(order_id, symbol, params or {})

    def fetch_open_orders(
        self, symbol: Optional[str] = None, since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        return self._exchange.fetch_open_orders(symbol, since, limit)

    def cancel_all_orders(
        self, symbol: Optional[str] = None, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        return self._exchange.cancel_all_orders(symbol, params or {})

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return self._exchange.fetch_ticker(symbol)

    def fetch_trades(
        self,
        symbol: str,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        return self._exchange.fetch_trades(symbol, since, limit, params or {})

    def fetch_order_book(
        self, symbol: str, limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self._exchange.fetch_order_book(symbol, limit, params or {})

    def get_position_info(self, symbol: str) -> Dict[str, Any]:
        try:
            return self._exchange.fetch_positions([symbol])
        except NotSupported:
            return {}

    def set_leverage(
        self,
        leverage: float,
        symbol: str,
        params: Optional[Dict[str, Any]] = None,
    ):
        try:
            return self._exchange.set_leverage(leverage, symbol, params or {})
        except NotSupported:
            return {}

    def enable_unified_margin(
        self, account_type: str = "unified",
        params: Optional[Dict[str, Any]] = None
    ):
        try:
            return self._exchange.switch_account_type(account_type, params or {})
        except NotSupported:
            return {}

    @property
    def exchange_id(self) -> str:
        return "bybit"

    @property
    def is_testnet(self) -> bool:
        return True  # このクラスは常にテストネット用

    def __repr__(self) -> str:
        return f"BybitTestnetClient(testnet={self.is_testnet})"
"""

# ⚠️ 本番環境ではBitbankClientを使用してください
# from .bitbank_client import BitbankClient
