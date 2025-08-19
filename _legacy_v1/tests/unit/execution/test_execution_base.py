# tests/unit/execution/test_execution_base.py
# テスト対象: crypto_bot/execution/base.py
# 説明:
#   - ExchangeClient Protocolが意図通りのインターフェイス制約を持つかを確認
#   - ダミークラスにすべてのメソッド実装を強制する型安全性のテスト

from typing import List

import pandas as pd

from crypto_bot.execution.base import ExchangeClient


class DummyExchange(ExchangeClient):
    def fetch_balance(self) -> dict:
        return {"USD": 1000}

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, since=None, limit=None
    ) -> pd.DataFrame:
        # 簡易なOHLCVデータを返す
        return pd.DataFrame(
            [[1, 100, 110, 90, 105, 1.2]],
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )

    def create_order(
        self, symbol: str, side: str, type: str, amount: float, price=None, params=None
    ) -> dict:
        return {"order_id": "12345", "status": "created"}

    def cancel_order(self, symbol: str, order_id: str) -> dict:
        return {"order_id": order_id, "status": "cancelled"}

    def cancel_all_orders(self, symbol: str) -> List[dict]:
        return [{"order_id": "12345", "status": "cancelled"}]

    def set_leverage(self, symbol: str, leverage: int) -> dict:
        return {"symbol": symbol, "leverage": leverage}


def test_dummy_exchange_protocol():
    ex = DummyExchange()
    # 各メソッドが正常に呼び出せること
    assert ex.fetch_balance() == {"USD": 1000}
    df = ex.fetch_ohlcv("BTC/USDT", "1h")
    assert "open" in df.columns
    order = ex.create_order("BTC/USDT", "buy", "limit", 0.1, price=100)
    assert order["status"] == "created"
    cancel = ex.cancel_order("BTC/USDT", "12345")
    assert cancel["status"] == "cancelled"
    cancels = ex.cancel_all_orders("BTC/USDT")
    assert cancels[0]["status"] == "cancelled"
    lev = ex.set_leverage("BTC/USDT", 5)
    assert lev["leverage"] == 5
