"""
ReconcileExecutor — ReconcileAction を bitbank 発注へ翻訳する唯一の副作用層

設計:
- shadow_mode=True（R0）: 発注せず「本来こうする」を WARNING ログに出すだけ（実害ゼロ）。
- action 適用順は CANCEL → PLACE/REPLACE → MARKET_CLOSE に固定（消す→作る→最終手段）。
- bitbank エラーコードを冪等に解釈:
    50026（該当注文なし）   = 目標（注文が無い状態）達成済み → 成功扱い
    50062（建玉数量超過）   = 既存 SL 存在の証拠 / 反映待ち       → 成功扱い
    70004（取引一時停止）   = 一時的 → retry（次サイクルに委ねる）
    30101（trigger 未指定） = プログラムバグ → abort（発注しない）
- MARKET_CLOSE は既存注文を全キャンセルしてから成行（二重決済防止・Phase 64.12 を踏襲）。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, List, Optional

from ...core.logger import get_logger
from .actions import ActionType, ReconcileAction, entry_side_of, exit_side_of

# action 適用順（小さいほど先）
_ORDER_PRIORITY = {
    ActionType.CANCEL_ORDER: 0,
    ActionType.REPLACE_SL: 1,
    ActionType.PLACE_SL: 1,
    ActionType.PLACE_TP: 1,
    ActionType.MARKET_CLOSE: 2,
    ActionType.NOOP: 3,
}


@dataclass
class ActionResult:
    """1 action の適用結果"""

    action: ReconcileAction
    status: str  # shadow / success / idempotent_ok / retry / abort / error / noop
    detail: str = ""


@dataclass
class ReconcileReport:
    """reconcile 1 サイクルの適用結果サマリ"""

    results: List[ActionResult] = field(default_factory=list)
    shadow_mode: bool = True

    @property
    def market_closes(self) -> List[ActionResult]:
        return [r for r in self.results if r.action.is_market_close]

    @property
    def applied_count(self) -> int:
        return sum(1 for r in self.results if r.status in ("success", "idempotent_ok"))

    def summary(self) -> str:
        from collections import Counter

        c = Counter(r.status for r in self.results)
        return ", ".join(f"{k}={v}" for k, v in sorted(c.items()))


class ReconcileExecutor:
    """ReconcileAction を bitbank へ適用する副作用層。"""

    def __init__(
        self,
        bitbank_client: Any,
        logger: Optional[Any] = None,
        shadow_mode: bool = True,
        sl_persistence: Any = None,
        symbol: str = "BTC/JPY",
    ):
        self.client = bitbank_client
        self.logger = logger or get_logger()
        self.shadow_mode = shadow_mode
        self.sl_persistence = sl_persistence
        self.symbol = symbol

    async def apply(self, actions: List[ReconcileAction]) -> ReconcileReport:
        report = ReconcileReport(shadow_mode=self.shadow_mode)
        for action in sorted(actions, key=lambda a: _ORDER_PRIORITY.get(a.action_type, 1)):
            report.results.append(await self._apply_one(action))
        return report

    async def _apply_one(self, action: ReconcileAction) -> ActionResult:
        if action.action_type == ActionType.NOOP:
            return ActionResult(action, "noop")

        # R0: shadow モードは発注せず「本来こうする」をログのみ
        if self.shadow_mode:
            self.logger.warning(
                f"🌑 Phase 90π [SHADOW] {action.action_type.value} "
                f"side={action.position_side} amount={action.amount:.4f} "
                f"price={action.price} reason={action.reason} - 実発注なし"
            )
            return ActionResult(action, "shadow")

        try:
            if action.action_type == ActionType.CANCEL_ORDER:
                return await self._cancel(action)
            if action.action_type in (ActionType.PLACE_SL, ActionType.REPLACE_SL):
                return await self._place_sl(action)
            if action.action_type == ActionType.PLACE_TP:
                return await self._place_tp(action)
            if action.action_type == ActionType.MARKET_CLOSE:
                return await self._market_close(action)
        except Exception as e:
            return self._classify_error(action, e)
        return ActionResult(action, "error", "unknown action type")

    # --- bitbank エラーコードの冪等解釈 ---
    def _classify_error(self, action: ReconcileAction, e: Exception) -> ActionResult:
        s = str(e)
        if "50026" in s:  # 該当注文なし = 既に消滅 = 目標達成
            return ActionResult(action, "idempotent_ok", "50026 order already gone")
        if "50062" in s:  # 建玉数量超過 = 既存 SL 存在 / 反映待ち
            return ActionResult(action, "idempotent_ok", "50062 existing sl or reflect-wait")
        if "70004" in s:  # 取引一時停止 = 一時的 → 次サイクルで再試行
            self.logger.warning(f"⚠️ Phase 90π reconcile: 70004 取引停止 → retry: {action.reason}")
            return ActionResult(action, "retry", "70004 suspended")
        if "30101" in s:  # trigger_price 未指定 = バグ
            self.logger.critical(
                f"🚨 Phase 90π reconcile: 30101 trigger未指定（バグ）: {action.reason}"
            )
            return ActionResult(action, "abort", "30101 trigger_price missing")
        self.logger.error(f"❌ Phase 90π reconcile action 失敗 {action.action_type.value}: {e}")
        return ActionResult(action, "error", s[:200])

    async def _cancel(self, action: ReconcileAction) -> ActionResult:
        await asyncio.to_thread(self.client.cancel_order, action.order_id, self.symbol)
        self.logger.info(
            f"🗑️ Phase 90π reconcile: 注文キャンセル {action.order_id} ({action.reason})"
        )
        return ActionResult(action, "success", f"cancel {action.order_id}")

    async def _place_sl(self, action: ReconcileAction) -> ActionResult:
        exit_side = exit_side_of(action.position_side)
        order = await asyncio.to_thread(
            self.client.create_order,
            symbol=self.symbol,
            side=exit_side,
            order_type="stop",
            amount=action.amount,
            trigger_price=action.price,
            is_closing_order=True,
            entry_position_side=action.position_side,
        )
        oid = str(order.get("id", ""))
        if self.sl_persistence is not None:
            try:
                self.sl_persistence.save(
                    entry_side_of(action.position_side), oid, action.price, action.amount
                )
            except Exception as e:  # 永続化失敗は致命でない（actual から再構築できる）
                self.logger.warning(f"⚠️ Phase 90π reconcile: SL永続化保存失敗（継続）: {e}")
        self.logger.warning(
            f"✅ Phase 90π reconcile: SL配置 side={action.position_side} "
            f"amount={action.amount:.4f} trigger={action.price:.0f} id={oid} ({action.reason})"
        )
        return ActionResult(action, "success", f"place_sl id={oid}")

    async def _place_tp(self, action: ReconcileAction) -> ActionResult:
        exit_side = exit_side_of(action.position_side)
        order = await asyncio.to_thread(
            self.client.create_order,
            symbol=self.symbol,
            side=exit_side,
            order_type="limit",
            amount=action.amount,
            price=action.price,
            is_closing_order=True,
            entry_position_side=action.position_side,
            post_only=True,
        )
        self.logger.info(
            f"✅ Phase 90π reconcile: TP配置 side={action.position_side} "
            f"amount={action.amount:.4f} price={action.price:.0f} id={order.get('id')}"
        )
        return ActionResult(action, "success", f"place_tp id={order.get('id')}")

    async def _market_close(self, action: ReconcileAction) -> ActionResult:
        exit_side = exit_side_of(action.position_side)
        # 二重決済防止: 既存注文を全キャンセルしてから成行（Phase 64.12 踏襲）
        try:
            orders = await asyncio.to_thread(self.client.fetch_active_orders, self.symbol, 100)
            for o in orders or []:
                try:
                    await asyncio.to_thread(
                        self.client.cancel_order, str(o.get("id", "")), self.symbol
                    )
                except Exception as e:
                    if "50026" not in str(e):
                        self.logger.warning(
                            f"⚠️ Phase 90π reconcile: 成行前キャンセル失敗（継続）: {e}"
                        )
        except Exception as e:
            self.logger.warning(
                f"⚠️ Phase 90π reconcile: 成行前 active_orders 取得失敗（継続）: {e}"
            )

        if self.sl_persistence is not None:
            try:
                self.sl_persistence.clear(entry_side_of(action.position_side))
            except Exception:
                pass

        close = await asyncio.to_thread(
            self.client.create_order,
            symbol=self.symbol,
            side=exit_side,
            order_type="market",
            amount=action.amount,
            is_closing_order=True,
            entry_position_side=action.position_side,
        )
        self.logger.critical(
            f"🚨 Phase 90π reconcile: 裸ポジ成行決済 side={action.position_side} "
            f"amount={action.amount:.4f} reason={action.reason} id={close.get('id')}"
        )
        return ActionResult(action, "success", f"market_close id={close.get('id')}")
