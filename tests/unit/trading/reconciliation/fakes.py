"""
reconciliation テスト用の Fake bitbank client とヘルパー

本番でしか出ない状態（VP空・SL失効・価格割れ・50062/50026/70004）を
ユニットテストで再現するための最小モック。state/executor/reconciler 共通で使う。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def make_position(side: str, amount: float, avg_price: float = 10_600_000.0) -> Dict[str, Any]:
    """fetch_margin_positions の1要素を模す"""
    return {"side": side, "amount": amount, "average_price": avg_price}


def make_order(
    order_id: str,
    order_type: str,
    side: str,
    amount: float,
    price: Optional[float] = None,
    status: str = "open",
    info_status: str = "",
) -> Dict[str, Any]:
    """fetch_active_orders / fetch_order の1要素を模す"""
    return {
        "id": order_id,
        "type": order_type,  # "stop" / "stop_limit" / "limit"
        "side": side,  # "buy" / "sell"
        "amount": amount,
        "price": price,
        "status": status,  # ccxt status
        "info": {"status": info_status},  # bitbank info.status（CANCELED_UNFILLED 等）
    }


class FakeBitbankClient:
    """bitbank client の最小 Fake。

    - fetch_margin_positions: async（本物と同じ）
    - fetch_active_orders / fetch_ticker / create_order / cancel_order: sync（本物と同じ）
    - create_order / cancel_order の呼び出しを記録（発注検証用）
    - create_error / cancel_error で例外注入（50062/70004 等の再現）
    """

    def __init__(
        self,
        positions: Optional[List[dict]] = None,
        active_orders: Optional[List[dict]] = None,
        price: float = 10_600_000.0,
        raise_on_fetch: bool = False,
        create_error: Optional[Exception] = None,
        cancel_error: Optional[Exception] = None,
    ):
        self._positions = positions or []
        self._active_orders = active_orders or []
        self._price = price
        self._raise = raise_on_fetch
        self.create_error = create_error
        self.cancel_error = cancel_error
        self.created_orders: List[Dict[str, Any]] = []
        self.canceled_orders: List[str] = []
        self._order_seq = 0

    async def fetch_margin_positions(self, symbol: str = "BTC/JPY") -> List[dict]:
        if self._raise:
            raise RuntimeError("fake fetch_margin_positions failure")
        return self._positions

    def fetch_active_orders(self, symbol: str = "BTC/JPY", limit: int = 100) -> List[dict]:
        if self._raise:
            raise RuntimeError("fake fetch_active_orders failure")
        return self._active_orders

    def fetch_ticker(self, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        if self._raise:
            raise RuntimeError("fake fetch_ticker failure")
        return {"last": self._price}

    def create_order(
        self,
        symbol: str = "BTC/JPY",
        side: str = "",
        order_type: str = "",
        amount: float = 0.0,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        is_closing_order: bool = False,
        entry_position_side: Optional[str] = None,
        post_only: bool = False,
    ) -> Dict[str, Any]:
        if self.create_error is not None:
            raise self.create_error
        self._order_seq += 1
        record = {
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "amount": amount,
            "price": price,
            "trigger_price": trigger_price,
            "is_closing_order": is_closing_order,
            "entry_position_side": entry_position_side,
            "post_only": post_only,
        }
        self.created_orders.append(record)
        # 状態遷移: 配置した SL/TP を active_orders に反映（マルチサイクル冪等性テスト用）
        if order_type in ("stop", "stop_limit", "limit"):
            self._active_orders.append(
                {
                    "id": f"new_order_{self._order_seq}",
                    "type": order_type,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "status": "open",
                    "info": {"status": ""},
                }
            )
        return {"id": f"new_order_{self._order_seq}", "status": "open"}

    def cancel_order(self, order_id: str, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        if self.cancel_error is not None:
            raise self.cancel_error
        self.canceled_orders.append(str(order_id))
        # 状態遷移: キャンセルした注文を active_orders から除去
        self._active_orders = [o for o in self._active_orders if str(o.get("id")) != str(order_id)]
        return {"id": order_id, "status": "canceled"}
