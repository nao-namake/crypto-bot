"""
Atomic Entry管理サービス - AtomicEntryManager
Phase 52.4-B完了 - executor.pyからAtomic Entry Pattern実装分離

エントリー・TP・SL注文のアトミックトランザクション管理を担当。
リトライ・ロールバック・クリーンアップ機能を提供。
"""

import asyncio
from typing import Any, Dict, List, Optional

from ...core.config import get_threshold
from ...core.logger import CryptoBotLogger
from ...data.bitbank_client import BitbankClient


class AtomicEntryManager:
    """Atomic Entry管理サービス

    Phase 52.4-B: executor.pyから分離
    Phase 56.4: 約定済み注文判定・補償ロジック追加
    責任: エントリー・TP・SL注文のアトミック配置・リトライ・ロールバック・クリーンアップ
    """

    def __init__(
        self,
        logger: CryptoBotLogger,
        bitbank_client: BitbankClient,
        stop_manager: Any,
    ):
        """
        AtomicEntryManager初期化

        Args:
            logger: ロガーインスタンス
            bitbank_client: BitbankClientインスタンス
            stop_manager: StopManagerインスタンス
        """
        self.logger = logger
        self.bitbank_client = bitbank_client
        self.stop_manager = stop_manager

    def _is_filled_order_error(self, error: Exception) -> bool:
        """
        Phase 56.4: 約定済み注文キャンセル試行エラーかどうかを判定

        bitbank APIエラーコード（thresholds.yamlから取得）:
        - 60004: 既に約定済みの注文
        - 60005: 既にキャンセル済みの注文
        - 60006: 注文が存在しない
        - 60007: キャンセル不可の状態

        Args:
            error: 発生した例外

        Returns:
            bool: 約定済み/キャンセル済み注文のエラーかどうか
        """
        error_str = str(error).lower()

        # Phase 56.4: 設定ファイルからエラーコードを取得
        filled_error_codes = get_threshold(
            "position_management.atomic_entry.filled_order_error_codes",
            ["60004", "60005", "60006", "60007"],
        )

        # APIエラーコードと一般的なキーワードを結合
        filled_indicators = list(filled_error_codes) + [
            "already filled",
            "already cancelled",
            "already canceled",
            "order not found",
            "order already",
        ]
        return any(indicator in error_str for indicator in filled_indicators)

    async def place_tp_with_retry(
        self,
        side: str,
        amount: float,
        entry_price: float,
        take_profit_price: float,
        symbol: str,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 52.4-B: TP注文配置（Exponential Backoff リトライ）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            take_profit_price: TP価格
            symbol: 通貨ペア
            max_retries: 最大リトライ回数（デフォルト3回）

        Returns:
            Dict: TP注文情報 {"order_id": str, "price": float} or None
        """
        for attempt in range(max_retries):
            try:
                tp_order = await self.stop_manager.place_take_profit(
                    side=side,
                    amount=amount,
                    entry_price=entry_price,
                    take_profit_price=take_profit_price,
                    symbol=symbol,
                    bitbank_client=self.bitbank_client,
                )
                if tp_order:
                    if attempt > 0:
                        self.logger.info(
                            f"✅ Phase 52.4-B: TP配置成功（試行{attempt + 1}回目） - ID: {tp_order.get('order_id')}"
                        )
                    return tp_order
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ Phase 52.4-B: TP配置失敗（試行{attempt + 1}/{max_retries}）: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Phase 52.4-B: TP配置失敗（全{max_retries}回試行）: {e}")
                    raise

        return None

    async def place_sl_with_retry(
        self,
        side: str,
        amount: float,
        entry_price: float,
        stop_loss_price: float,
        symbol: str,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 52.4-B: SL注文配置（Exponential Backoff リトライ）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            stop_loss_price: SL価格
            symbol: 通貨ペア
            max_retries: 最大リトライ回数（デフォルト3回）

        Returns:
            Dict: SL注文情報 {"order_id": str, "price": float} or None
        """
        for attempt in range(max_retries):
            try:
                sl_order = await self.stop_manager.place_stop_loss(
                    side=side,
                    amount=amount,
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    symbol=symbol,
                    bitbank_client=self.bitbank_client,
                )
                if sl_order:
                    if attempt > 0:
                        self.logger.info(
                            f"✅ Phase 52.4-B: SL配置成功（試行{attempt + 1}回目） - ID: {sl_order.get('order_id')}"
                        )
                    return sl_order
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ Phase 52.4-B: SL配置失敗（試行{attempt + 1}/{max_retries}）: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Phase 52.4-B: SL配置失敗（全{max_retries}回試行）: {e}")
                    raise

        return None

    async def cleanup_old_tp_sl_before_entry(
        self,
        side: str,
        symbol: str,
        entry_order_id: str,
        virtual_positions: List[Dict[str, Any]],
    ) -> None:
        """
        Phase 52.4-B: エントリー前の古いTP/SL注文クリーンアップ

        同一ポジション側（BUY or SELL）の古い未約定TP/SL注文を削除する。
        Phase 52.4-Bで実装したAtomic Entry Patternを完全にするための追加機能。

        背景:
        - Phase 52.4-B実装後、14エントリー → 28個のTP/SL注文が蓄積
        - 既存のcleanup_old_unfilled_orders()は全ポジションのTP/SLを保護するため削除されない
        - bitbank API 30件制限により、古いTP/SL注文が新規注文をブロック（-1.22%異常配置率）

        設計方針:
        - Phase 46思想遵守: 個別TP/SL管理維持
        - Phase 52.4-B思想完成: Atomic Entry Pattern維持
        - 新規エントリー前に同一側の古いTP/SL注文のみ削除

        Args:
            side: エントリーサイド (buy/sell) - この側の古いTP/SL注文のみ削除
            symbol: 通貨ペア
            entry_order_id: 今回のエントリー注文ID（ログ用）
            virtual_positions: 仮想ポジションリスト（保護対象注文ID取得用）
        """
        try:
            # 全アクティブ注文取得（Phase 55.8: async修正・メソッド名修正）
            active_orders = await self.bitbank_client.fetch_active_orders(symbol, limit=100)

            if not active_orders:
                self.logger.debug("📋 Phase 52.4-B: アクティブ注文なし - クリーンアップ不要")
                return

            # 同一ポジション側の古いTP/SL注文を検索
            # - BUYエントリー → SELL側のTP（利確）・SELL側のSL（損切）
            # - SELLエントリー → BUY側のTP（利確）・BUY側のSL（損切）
            target_tp_side = "sell" if side == "buy" else "buy"
            target_sl_side = "sell" if side == "buy" else "buy"

            # 現在のアクティブポジションのTP/SL注文IDを取得（保護対象）
            protected_order_ids = set()
            if virtual_positions:
                for pos in virtual_positions:
                    # 同じ側のポジションのTP/SL注文は保護
                    if pos.get("side") == side:
                        tp_id = pos.get("tp_order_id")
                        sl_id = pos.get("sl_order_id")
                        if tp_id:
                            protected_order_ids.add(str(tp_id))
                        if sl_id:
                            protected_order_ids.add(str(sl_id))

            # 削除対象の注文を収集
            orders_to_cancel = []
            for order in active_orders:
                order_id = str(order["order_id"])
                order_side = order["side"]
                order_type = order.get("type", "")

                # 保護対象の注文はスキップ
                if order_id in protected_order_ids:
                    continue

                # 同一側のTP/SL注文のみ削除対象
                # TP: limit注文 & 反対サイド
                # SL: stop注文 & 反対サイド
                is_tp = order_type == "limit" and order_side == target_tp_side
                is_sl = order_type == "stop" and order_side == target_sl_side

                if is_tp or is_sl:
                    orders_to_cancel.append(
                        {
                            "order_id": order_id,
                            "side": order_side,
                            "type": order_type,
                            "price": order.get("price"),
                        }
                    )

            # 削除実行
            if not orders_to_cancel:
                self.logger.info(
                    "✅ Phase 52.4-B: クリーンアップ不要 - "
                    f"{side}側の古いTP/SL注文なし（Entry: {entry_order_id}）"
                )
                return

            cancel_success = 0
            cancel_fail = 0

            for order in orders_to_cancel:
                try:
                    # Phase 55.8: async修正
                    await self.bitbank_client.cancel_order(order["order_id"], symbol)
                    cancel_success += 1
                    self.logger.info(
                        "🗑️ Phase 52.4-B: 古いTP/SL削除成功 - "
                        f"ID: {order['order_id']}, "
                        f"Type: {order['type']}, "
                        f"Price: {order.get('price', 'N/A')}"
                    )
                except Exception as e:
                    cancel_fail += 1
                    self.logger.warning(
                        "⚠️ Phase 52.4-B: TP/SL削除失敗（継続） - "
                        f"ID: {order['order_id']}, エラー: {e}"
                    )

            self.logger.info(
                "✅ Phase 52.4-B: クリーンアップ完了 - "
                f"{side}側 {cancel_success}件削除成功・{cancel_fail}件失敗 "
                f"（Entry: {entry_order_id}）"
            )

        except Exception as e:
            # クリーンアップ失敗してもエントリーは継続（Phase 52.4-B: L383-385と同様）
            self.logger.warning(
                "⚠️ Phase 52.4-B: エントリー前クリーンアップ失敗（処理継続） - "
                f"Entry: {entry_order_id}, エラー: {e}"
            )

    async def rollback_entry(
        self,
        entry_order_id: Optional[str],
        tp_order_id: Optional[str],
        sl_order_id: Optional[str],
        symbol: str,
        error: Exception,
    ) -> Dict[str, Any]:
        """
        Phase 52.4-B: Atomic Entry ロールバック

        エントリー・TP・SLのいずれかが失敗した場合、全ての注文をキャンセルする。

        Args:
            entry_order_id: エントリー注文ID
            tp_order_id: TP注文ID（配置済みの場合）
            sl_order_id: SL注文ID（配置済みの場合）
            symbol: 通貨ペア
            error: 発生したエラー

        Returns:
            Dict: ロールバック状況 {
                "success": bool,
                "cancelled_orders": List[str],
                "failed_cancellations": List[str],
                "manual_intervention_required": bool,
            }
        """
        self.logger.error(
            "🔄 Phase 52.4-B: Atomic Entry ロールバック開始 - "
            f"Entry: {entry_order_id}, TP: {tp_order_id}, SL: {sl_order_id}"
        )

        rollback_status = {
            "success": True,
            "cancelled_orders": [],
            "failed_cancellations": [],
            "manual_intervention_required": False,
        }

        # TP注文キャンセル（配置済みの場合）
        if tp_order_id:
            try:
                # Phase 55.8: async修正
                await self.bitbank_client.cancel_order(tp_order_id, symbol)
                self.logger.info(f"✅ Phase 52.4-B: TP注文キャンセル成功 - ID: {tp_order_id}")
                rollback_status["cancelled_orders"].append(tp_order_id)
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 52.4-B: TP注文キャンセル失敗: {e}")
                rollback_status["failed_cancellations"].append(tp_order_id)

        # SL注文キャンセル（配置済みの場合）
        if sl_order_id:
            try:
                # Phase 55.8: async修正
                await self.bitbank_client.cancel_order(sl_order_id, symbol)
                self.logger.info(f"✅ Phase 52.4-B: SL注文キャンセル成功 - ID: {sl_order_id}")
                rollback_status["cancelled_orders"].append(sl_order_id)
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 52.4-B: SL注文キャンセル失敗: {e}")
                rollback_status["failed_cancellations"].append(sl_order_id)

        # エントリー注文キャンセル（最重要）
        if entry_order_id:
            try:
                # Phase 55.8: async修正
                await self.bitbank_client.cancel_order(entry_order_id, symbol)
                self.logger.error(
                    "🚨 Phase 52.4-B: エントリー注文ロールバック成功 - "
                    f"ID: {entry_order_id}, 理由: {error}"
                )
                rollback_status["cancelled_orders"].append(entry_order_id)
            except Exception as e:
                # Phase 56.4: 約定済み注文エラーの場合は正常状態として扱う
                if self._is_filled_order_error(e):
                    self.logger.warning(
                        f"⚠️ Phase 56.4: Entry注文は既に約定済み - "
                        f"ID: {entry_order_id}, ロールバック対象外（補償処理実行）"
                    )
                    # 約定済みフラグを設定（executor.pyで補償処理を実行）
                    rollback_status["entry_filled"] = True
                    # 約定済みの場合は手動介入不要（補償処理で対応）
                    rollback_status["cancelled_orders"].append(entry_order_id)
                else:
                    # 一時的なAPI errorの場合のみ手動介入フラグ
                    self.logger.critical(
                        "❌ CRITICAL: エントリー注文キャンセル失敗（手動介入必要） - "
                        f"ID: {entry_order_id}, エラー: {e}"
                    )
                    rollback_status["failed_cancellations"].append(entry_order_id)
                    rollback_status["manual_intervention_required"] = True
                    rollback_status["success"] = False

        # ロールバック結果サマリーログ
        if rollback_status["success"]:
            self.logger.info(
                f"✅ Phase 52.4-B: ロールバック完全成功 - "
                f"キャンセル成功: {len(rollback_status['cancelled_orders'])}件"
            )
        else:
            self.logger.error(
                f"❌ Phase 52.4-B: ロールバック失敗 - "
                f"成功: {len(rollback_status['cancelled_orders'])}件, "
                f"失敗: {len(rollback_status['failed_cancellations'])}件, "
                f"手動介入必要: {rollback_status['manual_intervention_required']}"
            )

        return rollback_status
