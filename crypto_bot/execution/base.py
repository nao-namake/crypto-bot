from typing import Any, List, Protocol

import pandas as pd


class ExchangeClient(Protocol):
    """すべての取引所クライアントが実装すべき共通インターフェイス"""

    def fetch_balance(self) -> dict:
        """残高情報を取ってくる"""
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
