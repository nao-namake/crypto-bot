# =============================================================================
# ファイル名: crypto_bot/execution/base.py
# 説明:
# 取引所クライアントの「共通インターフェイス（型）」をProtocolで定義。
# すべての取引所クライアント（Bybit, Bitbank, CCXTラッパー等）はこれを満たす必要がある。
# - fetch_balance, fetch_ohlcv, create_order, cancel_order など
# - 型チェックや自動補完のための土台（直接インスタンス化はしない）
# - 実装は各クライアントファイル（bitbank_client.py等）側で
# =============================================================================

from typing import Any, List, Protocol

import pandas as pd


class ExchangeClient(Protocol):
    """すべての取引所クライアントが実装すべき共通インターフェイス"""

    def fetch_balance(self) -> dict:
        """残高情報を取ってくる"""
        ...

    def fetch_ticker(self, symbol: str) -> dict:
        """ティッカー情報を取得"""
        ...

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Any = None,
        limit: int = None,
    ) -> pd.DataFrame:
        """OHLCV データを pandas.DataFrame で返す"""
        ...

    def create_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: float | None = None,
        params: dict | None = None,
    ) -> dict:
        """注文を出す"""
        ...

    def cancel_order(self, symbol: str, order_id: str) -> dict:
        """指定 order_id の注文をキャンセル"""
        ...

    def cancel_all_orders(self, symbol: str) -> List[dict]:
        """シンボルに紐づく全建玉をキャンセル"""
        ...

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        """レバレッジ設定"""
        ...
