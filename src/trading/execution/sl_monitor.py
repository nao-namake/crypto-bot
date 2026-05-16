"""
SLMonitor - Phase 87 C1 / C5 / H1

bitbank stop注文のトリガー発火後 CANCELED_UNFILLED 約定失敗を検出し、
ポジションが裸放置されるインシデント（2026-05-12 6時間放置事案）の再発を防ぐ。

責務:
1. SL注文の health check (`check_sl_health`)
   - CANCELED_UNFILLED / EXPIRED / REJECTED 検出
   - sl_placed_at から 24h 経過判定 (H1)
2. 緊急成行決済 (`emergency_market_close`)
   - 反対側 market 注文を bitbank に発行（既存ポジション決済フラグ付き）
   - dry_run モード: critical ログのみで実発注しない（初期投入時の誤発火検証用）

連携:
- `tp_sl_manager.ensure_tp_sl_for_existing_positions` (C5: 5分ループ内 health check)
- `stop_manager.check_stop_conditions` (H1: SL タイムアウト判定)
- `position_restorer.restore_positions_from_api` (H2: 起動時SL欠損のフォールバック)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from ...core.logger import CryptoBotLogger, get_logger

# 24h タイムアウトのデフォルト（thresholds.yaml から override 可能）
DEFAULT_SL_TIMEOUT_HOURS: int = 24

# Phase 89 C7 / P0-1: 実 order_id ではない placeholder 文字列
# sl_state_persistence.PLACEHOLDER_ORDER_IDS と統一（"" 空文字も含める）
PLACEHOLDER_ORDER_IDS: frozenset = frozenset({"existing", "none", "null", "unknown", ""})

# Phase 89 C7: 同一 sl_order_id で fetch_order が連続失敗した時に緊急決済へ昇格する閾値
DEFAULT_MAX_FETCH_FAILURES: int = 3


@dataclass
class SLHealthResult:
    """SL health check 結果"""

    is_healthy: bool
    failure_reason: Optional[str] = None
    # "canceled_unfilled" / "expired" / "rejected" / "timeout_24h" / "not_found" / "fetch_error"
    requires_emergency_close: bool = False
    order_info: Optional[Dict[str, Any]] = None


class SLMonitor:
    """SL注文の health check + 緊急成行決済"""

    def __init__(
        self,
        logger: Optional[CryptoBotLogger] = None,
        sl_persistence: Any = None,
        dry_run: bool = False,
        timeout_hours: int = DEFAULT_SL_TIMEOUT_HOURS,
        max_fetch_failures: int = DEFAULT_MAX_FETCH_FAILURES,
    ) -> None:
        """
        Args:
            logger: ロガー（未指定なら get_logger()）
            sl_persistence: 緊急決済時に SL永続化レコードをクリアするための SLStatePersistence
            dry_run: True なら緊急成行決済を実発注せず critical ログのみ
            timeout_hours: SL配置からの強制決済タイムアウト（H1）
            max_fetch_failures: 同一 sl_order_id で fetch_order が連続失敗した時に
                緊急決済判定へ昇格する閾値（Phase 89 C7）
        """
        self.logger = logger or get_logger()
        self.sl_persistence = sl_persistence
        self.dry_run = dry_run
        self.timeout_hours = timeout_hours
        # Phase 89 C7: sl_order_id ごとの fetch_order 連続失敗カウンタ
        self.max_fetch_failures = max(1, int(max_fetch_failures))
        self._fetch_failure_counts: Dict[str, int] = {}

    # ========================================
    # ステータス判定（純粋関数）
    # ========================================

    @staticmethod
    def _info_status(order: Dict[str, Any]) -> str:
        info = order.get("info") or {}
        return str(info.get("status", "")).upper()

    @staticmethod
    def is_canceled_unfilled(order: Dict[str, Any]) -> bool:
        """bitbank 固有の CANCELED_UNFILLED ステータス判定"""
        return SLMonitor._info_status(order) == "CANCELED_UNFILLED"

    @staticmethod
    def is_expired(order: Dict[str, Any]) -> bool:
        return SLMonitor._info_status(order) == "EXPIRED"

    @staticmethod
    def is_rejected(order: Dict[str, Any]) -> bool:
        return SLMonitor._info_status(order) == "REJECTED"

    # ========================================
    # health check
    # ========================================

    def _is_timed_out(self, sl_placed_at_iso: Optional[str]) -> bool:
        """sl_placed_at から `timeout_hours` 経過しているか。

        Args:
            sl_placed_at_iso: ISO 8601 形式の UTC 文字列を期待する。
                aware/naive 両対応で、naive datetime は UTC として解釈する
                （bot 内部は UTC 統一）。None・空文字・不正な ISO は False を返す
                （タイムアウトと判定しない＝既存運用への影響を最小化）。
        """
        if not sl_placed_at_iso:
            return False
        try:
            placed = datetime.fromisoformat(sl_placed_at_iso)
            if placed.tzinfo is None:
                placed = placed.replace(tzinfo=timezone.utc)
            elapsed = datetime.now(timezone.utc) - placed
            return elapsed > timedelta(hours=self.timeout_hours)
        except (TypeError, ValueError):
            return False

    async def check_sl_health(
        self,
        sl_order_id: Optional[str],
        sl_placed_at_iso: Optional[str],
        bitbank_client: Any,
        symbol: str = "BTC/JPY",
    ) -> SLHealthResult:
        """SL注文の健全性を判定する。

        判定優先順位:
          1. sl_order_id が空 → not_found / 緊急決済必須
          2. fetch_order の info.status が CANCELED_UNFILLED / EXPIRED / REJECTED
             → 該当 reason / 緊急決済必須
          3. sl_placed_at から timeout_hours 超過 → timeout_24h / 緊急決済必須
          4. それ以外 → healthy
        """
        if not sl_order_id:
            return SLHealthResult(
                is_healthy=False,
                failure_reason="not_found",
                requires_emergency_close=True,
            )

        # Phase 89 C7: placeholder ID（"existing" 等）は即時緊急決済判定
        # position_restorer 等で実 order_id が取得できなかった抜け穴を塞ぐ
        if str(sl_order_id).strip().lower() in PLACEHOLDER_ORDER_IDS:
            self.logger.critical(
                f"🚨 Phase 89 C7: SL placeholder ID 検出 (sl_order_id={sl_order_id!r}) - "
                f"実 order_id が取得できていないため SL の健全性確認不能。緊急決済判定。"
            )
            return SLHealthResult(
                is_healthy=False,
                failure_reason="placeholder_id",
                requires_emergency_close=True,
            )

        try:
            order = await asyncio.to_thread(bitbank_client.fetch_order, sl_order_id, symbol)
            # 成功したら連続失敗カウンタをリセット
            self._fetch_failure_counts.pop(str(sl_order_id), None)
        except Exception as e:
            # Phase 89 C7: 連続失敗カウントが閾値に達したら緊急決済判定へ昇格
            key = str(sl_order_id)
            self._fetch_failure_counts[key] = self._fetch_failure_counts.get(key, 0) + 1
            count = self._fetch_failure_counts[key]

            if count >= self.max_fetch_failures:
                self.logger.critical(
                    f"🚨 Phase 89 C7: SL fetch_order 連続失敗 {count}/{self.max_fetch_failures} 回 - "
                    f"ID={sl_order_id}, error={e}。SL 実態確認不能のため緊急決済判定。"
                )
                # カウンタをリセットして次回以降の誤発火を防ぐ
                self._fetch_failure_counts.pop(key, None)
                return SLHealthResult(
                    is_healthy=False,
                    failure_reason="fetch_error_persistent",
                    requires_emergency_close=True,
                )

            self.logger.warning(
                f"⚠️ Phase 87 C1: SL fetch_order 失敗 - "
                f"ID={sl_order_id}, error={e}（{count}/{self.max_fetch_failures} 回・"
                f"一時的なAPIエラーの可能性）"
            )
            return SLHealthResult(
                is_healthy=True,  # 一時エラーで誤発火させない
                failure_reason="fetch_error",
                requires_emergency_close=False,
            )

        if self.is_canceled_unfilled(order):
            return SLHealthResult(
                is_healthy=False,
                failure_reason="canceled_unfilled",
                requires_emergency_close=True,
                order_info=order,
            )

        if self.is_expired(order):
            return SLHealthResult(
                is_healthy=False,
                failure_reason="expired",
                requires_emergency_close=True,
                order_info=order,
            )

        if self.is_rejected(order):
            return SLHealthResult(
                is_healthy=False,
                failure_reason="rejected",
                requires_emergency_close=True,
                order_info=order,
            )

        if self._is_timed_out(sl_placed_at_iso):
            return SLHealthResult(
                is_healthy=False,
                failure_reason="timeout_24h",
                requires_emergency_close=True,
                order_info=order,
            )

        return SLHealthResult(is_healthy=True, order_info=order)

    # ========================================
    # 緊急成行決済
    # ========================================

    async def emergency_market_close(
        self,
        entry_side: str,
        amount: float,
        reason: str,
        bitbank_client: Any,
        symbol: str = "BTC/JPY",
    ) -> Optional[Dict[str, Any]]:
        """既存ポジションを緊急成行決済する。

        Args:
            entry_side: 元のエントリーサイド (buy/sell)
            amount: ポジション数量
            reason: ログ用の理由文字列（"canceled_unfilled" / "timeout_24h" 等）
            bitbank_client: BitbankClient
            symbol: 通貨ペア

        Returns:
            Dict: {"order_id": str, "dry_run": bool, "reason": str} or None（失敗時）
        """
        if entry_side.lower() not in ("buy", "sell"):
            self.logger.critical(
                f"🚨 Phase 87 C1: emergency_market_close - 不正な entry_side={entry_side}"
            )
            return None

        if amount <= 0:
            self.logger.warning(
                f"⚠️ Phase 87 C1: emergency_market_close スキップ - amount={amount} (≤0)"
            )
            return None

        exit_side = "sell" if entry_side.lower() == "buy" else "buy"
        position_side = "long" if entry_side.lower() == "buy" else "short"

        # dry_run: 実発注せずログのみ
        if self.dry_run:
            self.logger.critical(
                f"🧪 Phase 87 C1 [DRY_RUN]: 緊急成行決済シミュレーション "
                f"(reason={reason}, exit_side={exit_side}, amount={amount:.6f} BTC, "
                f"position_side={position_side}) - 実発注なし"
            )
            return {"order_id": None, "dry_run": True, "reason": reason}

        self.logger.critical(
            f"🚨 Phase 87 C1: 緊急成行決済発動 "
            f"(reason={reason}, exit_side={exit_side}, amount={amount:.6f} BTC, "
            f"position_side={position_side})"
        )

        # 既存注文の事前キャンセル（孤児防止）
        try:
            active_orders = await asyncio.to_thread(bitbank_client.fetch_active_orders, symbol, 100)
            for order in active_orders or []:
                try:
                    await asyncio.to_thread(
                        bitbank_client.cancel_order,
                        str(order.get("id", "")),
                        symbol,
                    )
                except Exception as cancel_err:
                    self.logger.warning(
                        f"⚠️ Phase 87 C1: 事前キャンセル失敗 "
                        f"(ID={order.get('id')}): {cancel_err}"
                    )
        except Exception as fetch_err:
            self.logger.warning(
                f"⚠️ Phase 87 C1: fetch_active_orders 失敗 - 事前キャンセル省略: {fetch_err}"
            )

        # SL永続化クリア（永続化レコードと実態の整合性維持）
        if self.sl_persistence is not None:
            try:
                self.sl_persistence.clear(entry_side)
            except Exception as persist_err:
                self.logger.warning(
                    f"⚠️ Phase 87 C1: SL永続化クリア失敗 ({entry_side}): {persist_err}"
                )

        # 反対側で成行決済
        try:
            close_order = await asyncio.to_thread(
                bitbank_client.create_order,
                symbol=symbol,
                order_type="market",
                side=exit_side,
                amount=amount,
                is_closing_order=True,
                entry_position_side=position_side,
            )
            order_id = close_order.get("id") if isinstance(close_order, dict) else None
            self.logger.critical(
                f"✅ Phase 87 C1: 緊急成行決済成功 - ID={order_id}, reason={reason}"
            )
            return {"order_id": order_id, "dry_run": False, "reason": reason}
        except Exception as e:
            self.logger.critical(
                f"🚨🚨 Phase 87 C1: 緊急成行決済失敗 - 手動介入必要! " f"reason={reason}, error={e}"
            )
            return None
