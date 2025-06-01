# =============================================================================
# ファイル名: crypto_bot/execution/bybit_client.py
# 説明:
# Bybit Testnet専用の取引所クライアントラッパー。
# - .env自動読込対応
# - CCXTライブラリのBybit実装に型ヒントとPythonicなラップを提供
# - 未定義メソッド/属性は内部のccxt.bybitへ自動フォールバック
# - バックテスト・リアル取引・データ取得に共通利用
# - 必要に応じて認証・テストネット対応、注文・残高・OHLCV取得可
# =============================================================================

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

import ccxt
import pandas as pd
from ccxt.base.errors import NotSupported
from dotenv import load_dotenv

from .base import ExchangeClient

class BybitTestnetClient(ExchangeClient):
    """
    Bybit Testnet 用の軽量ラッパー。

    * キー未設定でも公開エンドポイントのみで動作可能
    * attributes が見つからない場合は内部 ccxt Exchange へ自動委譲
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        default_type: str = "linear",
        ccxt_options: Optional[Dict[str, Any]] = None,
        dotenv_path: Optional[str] = ".env",
        **_: Any,
    ):
        # ── .env 読み込み ────────────────────────────────────────────
        if dotenv_path:
            load_dotenv(dotenv_path=dotenv_path)

        self.api_key = api_key or os.getenv("BYBIT_TESTNET_API_KEY")
        self.api_secret = api_secret or os.getenv("BYBIT_TESTNET_API_SECRET")

        # ── ccxt Exchange インスタンス生成 ──────────────────────────
        opts: Dict[str, Any] = {
            "enableRateLimit": True,
            "urls": {"api": "https://api-testnet.bybit.com"},
            "options": {"defaultType": default_type},
        }
        if ccxt_options:
            opts.update(ccxt_options)

        self._exchange = ccxt.bybit(opts)

        # 認証キー設定（存在する場合のみ）
        if self.api_key:
            self._exchange.apiKey = self.api_key
            self._exchange.secret = self.api_secret

        # テストネット sandbox モード（互換性のため try/except）
        if testnet and hasattr(self._exchange, "set_sandbox_mode"):
            try:
                self._exchange.set_sandbox_mode(True)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # ❶ 未定義属性は _exchange へ自動フォールバック
    # ------------------------------------------------------------------
    def __getattr__(self, item: str):  # noqa: D401
        return getattr(self._exchange, item)

    # ------------------------------------------------------------------
    # ❷ 型ヒント付きラッパー（必要最低限）
    # ------------------------------------------------------------------
    def fetch_balance(self) -> dict:
        return self._exchange.fetch_balance()

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[Union[int, float]] = None,
        limit: int | None = None,
    ):
        return self._exchange.fetch_ohlcv(symbol, timeframe, since, limit)

    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: float | None = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        return self._exchange.create_order(
            symbol, type.lower(), side.lower(), amount, price, params or {}
        )

    def cancel_order(
        self,
        symbol: str,
        order_id: str,
        params: Optional[Dict[str, Any]] = None,
    ):
        return self._exchange.cancel_order(order_id, symbol, params or {})

    def cancel_all_orders(self, symbol: str) -> List[dict]:
        results: List[dict] = []
        for o in self._exchange.fetch_open_orders(symbol):
            oid = o.get("id") or o.get("orderId")
            if oid:
                results.append(self.cancel_order(symbol, oid))
        return results

    def set_leverage(
        self,
        symbol: str,
        leverage: int,
        params: Optional[Dict[str, Any]] = None,
    ):
        try:
            return self._exchange.set_leverage(leverage, symbol, params or {})
        except NotSupported:
            return {}
