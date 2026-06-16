"""
Reconciliation の型定義（ReconcileAction / ActualState / DesiredState）

すべて frozen dataclass（不変）で、reconcile の純粋関数層（desired/diff/invariants）が
副作用なしに受け渡しできるようにする。executor 層のみがこれらを bitbank API 発注へ翻訳する。

用語:
- position_side: "long" / "short"（建玉の向き。bitbank の建玉単位）
- entry_side   : "buy"(long) / "sell"(short)（建玉を作った注文方向）
- exit_side    : "sell"(long) / "buy"(short)（決済・TP・SL の注文方向）
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

# 建玉の向き（両サイドを必ず評価する）
POSITION_SIDES: Tuple[str, str] = ("long", "short")


def entry_side_of(position_side: str) -> str:
    """建玉の向き → 建玉を作る注文方向"""
    return "buy" if position_side == "long" else "sell"


def exit_side_of(position_side: str) -> str:
    """建玉の向き → 決済（TP/SL/成行クローズ）の注文方向"""
    return "sell" if position_side == "long" else "buy"


class ActionType(Enum):
    """reconcile が計画する操作の種類"""

    NOOP = "noop"  # desired == actual。冪等の核（大半はこれ）
    PLACE_SL = "place_sl"  # SL 欠損 → stop 注文を新規配置
    PLACE_TP = "place_tp"  # TP 欠損 → limit 注文を新規配置
    REPLACE_SL = "replace_sl"  # SL の数量/価格不一致 → 旧 SL を消して張り替え
    CANCEL_ORDER = "cancel_order"  # 孤児 SL/TP・重複注文をキャンセル
    MARKET_CLOSE = "market_close"  # 裸ポジ是正/価格 SL 割れ/サイズ超過 → 成行決済


@dataclass(frozen=True)
class ReconcileAction:
    """reconcile の1操作（executor が bitbank 発注へ翻訳する）"""

    action_type: ActionType
    position_side: str = ""
    reason: str = ""
    amount: float = 0.0
    price: Optional[float] = None  # PLACE_SL/PLACE_TP/REPLACE_SL の価格（SL=trigger, TP=limit）
    order_id: Optional[str] = None  # CANCEL_ORDER/REPLACE_SL の対象注文 ID

    @property
    def is_market_close(self) -> bool:
        return self.action_type == ActionType.MARKET_CLOSE

    @property
    def places_sl(self) -> bool:
        """SL を bitbank に新規に置こうとする action か（PLACE_SL / REPLACE_SL）"""
        return self.action_type in (ActionType.PLACE_SL, ActionType.REPLACE_SL)

    # --- factory（可読性のため）---
    @classmethod
    def noop(cls, reason: str, position_side: str = "") -> "ReconcileAction":
        return cls(ActionType.NOOP, position_side=position_side, reason=reason)

    @classmethod
    def place_sl(
        cls, position_side: str, amount: float, price: float, reason: str
    ) -> "ReconcileAction":
        return cls(ActionType.PLACE_SL, position_side, reason, amount, price=price)

    @classmethod
    def place_tp(
        cls, position_side: str, amount: float, price: float, reason: str
    ) -> "ReconcileAction":
        return cls(ActionType.PLACE_TP, position_side, reason, amount, price=price)

    @classmethod
    def replace_sl(
        cls, position_side: str, amount: float, price: float, order_id: str, reason: str
    ) -> "ReconcileAction":
        return cls(
            ActionType.REPLACE_SL, position_side, reason, amount, price=price, order_id=order_id
        )

    @classmethod
    def cancel_order(cls, order_id: str, reason: str, position_side: str = "") -> "ReconcileAction":
        return cls(ActionType.CANCEL_ORDER, position_side, reason, order_id=order_id)

    @classmethod
    def market_close(cls, position_side: str, amount: float, reason: str) -> "ReconcileAction":
        return cls(ActionType.MARKET_CLOSE, position_side, reason, amount)


@dataclass(frozen=True)
class SideState:
    """ある建玉サイドの実際の状態（取引所スナップショット由来）"""

    position_side: str
    amount: float = 0.0  # 実建玉量（BTC）
    avg_price: float = 0.0  # 平均建値
    sl_amount: float = 0.0  # 実効 SL 注文の合計カバー量
    sl_order_ids: Tuple[str, ...] = ()  # 検出した SL 注文 ID 群
    sl_status: str = ""  # 代表ステータス（診断用・CANCELED_UNFILLED 等）
    tp_amount: float = 0.0  # 実効 TP 注文の合計カバー量
    tp_order_ids: Tuple[str, ...] = ()

    @property
    def has_position(self) -> bool:
        return self.amount > 0

    def sl_covered(self, ratio: float = 0.95) -> bool:
        """SL が建玉の ratio 以上をカバーしているか（建玉ゼロは True）"""
        if self.amount <= 0:
            return True
        return self.sl_amount >= self.amount * ratio

    def tp_covered(self, ratio: float = 0.95) -> bool:
        if self.amount <= 0:
            return True
        return self.tp_amount >= self.amount * ratio


@dataclass(frozen=True)
class ActualState:
    """両サイドの実際の状態 + 現在価格。fetch 失敗時は ok=False。"""

    long: SideState
    short: SideState
    current_price: float = 0.0
    ok: bool = True  # actual の取得に成功したか（False なら reconcile は ABORT）

    def side(self, position_side: str) -> SideState:
        return self.long if position_side == "long" else self.short

    @property
    def total_amount(self) -> float:
        return self.long.amount + self.short.amount

    @property
    def is_hedged(self) -> bool:
        """両建て（long と short を同時に保有）"""
        return self.long.amount > 0 and self.short.amount > 0


@dataclass(frozen=True)
class DesiredSide:
    """ある建玉サイドの「あるべき」TP/SL（実建玉に対してのみ計算）"""

    position_side: str
    amount: float
    tp_price: float
    sl_price: float


@dataclass(frozen=True)
class DesiredState:
    """両サイドの「あるべき」状態。建玉が無いサイドは None。"""

    long: Optional[DesiredSide] = None
    short: Optional[DesiredSide] = None

    def side(self, position_side: str) -> Optional[DesiredSide]:
        return self.long if position_side == "long" else self.short
