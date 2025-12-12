"""
ポジションクリーンアップサービス - Phase 49完了
Phase 37.5.3: 孤児ポジションクリーンアップ

bitbankがOCO注文をサポートしていないため、
ポジション決済後に残ったTP/SL注文を検出・削除する。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient


class PositionCleanup:
    """
    ポジションクリーンアップサービス

    孤児ポジションの検出とTP/SL注文の削除を行う。
    """

    def __init__(self):
        """PositionCleanup初期化"""
        self.logger = get_logger()
        self.position_tracker = None  # 後で注入

    def inject_position_tracker(self, position_tracker: Any) -> None:
        """
        PositionTrackerを注入

        Args:
            position_tracker: PositionTrackerインスタンス
        """
        self.position_tracker = position_tracker

    async def cleanup_orphaned_positions(
        self, bitbank_client: Optional[BitbankClient] = None
    ) -> Dict[str, Any]:
        """
        Phase 37.5.3: 孤児ポジションクリーンアップ

        実際のポジションと仮想ポジションを照合し、
        消失したポジションのTP/SL注文を削除する。

        Args:
            bitbank_client: Bitbank APIクライアント

        Returns:
            クリーンアップ結果
        """
        try:
            if not self.position_tracker:
                return {"success": False, "message": "PositionTrackerが未注入", "cleaned": 0}

            if not bitbank_client:
                return {"success": False, "message": "BitbankClientが未指定", "cleaned": 0}

            # 実際のポジション取得
            actual_positions = await self._fetch_actual_positions(bitbank_client)
            if actual_positions is None:
                return {"success": False, "message": "実ポジション取得失敗", "cleaned": 0}

            # 孤児ポジション検出
            orphaned = self.position_tracker.get_orphaned_positions(actual_positions)

            if not orphaned:
                self.logger.debug("🔍 孤児ポジションなし - クリーンアップ不要")
                return {"success": True, "message": "孤児ポジションなし", "cleaned": 0}

            # TP/SL注文削除
            cleaned_count = 0
            failed_cancels = []

            for position in orphaned:
                # TP注文削除
                tp_order_id = position.get("tp_order_id")
                if tp_order_id:
                    if await self._cancel_order(bitbank_client, tp_order_id):
                        cleaned_count += 1
                        self.logger.info(f"🧹 TP注文削除成功: {tp_order_id}")
                    else:
                        failed_cancels.append(f"TP:{tp_order_id}")

                # SL注文削除
                sl_order_id = position.get("sl_order_id")
                if sl_order_id:
                    if await self._cancel_order(bitbank_client, sl_order_id):
                        cleaned_count += 1
                        self.logger.info(f"🧹 SL注文削除成功: {sl_order_id}")
                    else:
                        failed_cancels.append(f"SL:{sl_order_id}")

                # 仮想ポジション削除
                self.position_tracker.remove_position(position["order_id"])

            # 結果サマリー
            if failed_cancels:
                self.logger.warning(f"⚠️ 一部注文削除失敗: {', '.join(failed_cancels)}")

            self.logger.info(
                f"✅ 孤児ポジションクリーンアップ完了: "
                f"{len(orphaned)}ポジション検出, {cleaned_count}注文削除"
            )

            return {
                "success": True,
                "message": f"クリーンアップ完了",
                "cleaned": cleaned_count,
                "orphaned_positions": len(orphaned),
                "failed_cancels": failed_cancels,
            }

        except Exception as e:
            self.logger.error(f"❌ 孤児ポジションクリーンアップエラー: {e}")
            return {"success": False, "message": f"クリーンアップエラー: {e}", "cleaned": 0}

    async def _fetch_actual_positions(
        self, bitbank_client: BitbankClient
    ) -> Optional[List[Dict[str, Any]]]:
        """
        実際のポジションを取得

        Args:
            bitbank_client: Bitbank APIクライアント

        Returns:
            ポジションリスト（エラー時None）
        """
        try:
            # 信用ポジション取得
            positions = await bitbank_client.fetch_margin_positions()

            if positions is None:
                self.logger.warning("⚠️ 信用ポジション取得失敗")
                return None

            # ポジション形式を統一
            actual_positions = []
            for pos in positions:
                actual_positions.append(
                    {
                        "side": pos.get("side", "").lower(),
                        "amount": float(pos.get("amount", 0)),
                        "price": float(pos.get("price", 0)),
                    }
                )

            self.logger.debug(f"📊 実ポジション取得: {len(actual_positions)}件")
            return actual_positions

        except Exception as e:
            self.logger.error(f"❌ 実ポジション取得エラー: {e}")
            return None

    async def _cancel_order(self, bitbank_client: BitbankClient, order_id: str) -> bool:
        """
        注文をキャンセル

        Args:
            bitbank_client: Bitbank APIクライアント
            order_id: キャンセルする注文ID

        Returns:
            成功の可否
        """
        try:
            result = await bitbank_client.cancel_order(symbol="btc_jpy", id=order_id)

            if result and result.get("status") == "CANCELED_UNFILLED":
                return True

            # 既にキャンセル済みまたは約定済みの場合も成功扱い
            if result and result.get("status") in ["CANCELED_PARTIALLY_FILLED", "FULLY_FILLED"]:
                self.logger.info(f"📝 注文既に処理済み: {order_id} ({result.get('status')})")
                return True

            return False

        except Exception as e:
            # 注文が存在しない場合も成功扱い（既に削除済み）
            if "60002" in str(e):  # Order not found
                self.logger.debug(f"📝 注文既に削除済み: {order_id}")
                return True

            self.logger.error(f"❌ 注文キャンセルエラー ({order_id}): {e}")
            return False

    async def check_stale_positions(
        self, max_age_hours: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        古いポジションを検出

        Args:
            max_age_hours: 最大保持時間（時間単位）

        Returns:
            古いポジションリスト
        """
        if not self.position_tracker:
            return []

        if max_age_hours is None:
            max_age_hours = get_threshold("position_management.max_position_age_hours", 24)

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        stale_positions = []

        for position in self.position_tracker.get_all_positions():
            timestamp = position.get("timestamp")
            if isinstance(timestamp, datetime):
                if timestamp < cutoff_time:
                    stale_positions.append(position)

        if stale_positions:
            self.logger.warning(
                f"⚠️ 古いポジション検出: {len(stale_positions)}件 " f"({max_age_hours}時間以上経過)"
            )

        return stale_positions

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """
        クリーンアップ統計を取得

        Returns:
            統計情報
        """
        if not self.position_tracker:
            return {"virtual_positions": 0, "total_exposure": 0, "position_sides": {}}

        virtual_positions = self.position_tracker.get_all_positions()
        exposure = self.position_tracker.get_total_exposure()

        # サイド別カウント
        buy_count = len([p for p in virtual_positions if p.get("side", "").lower() == "buy"])
        sell_count = len([p for p in virtual_positions if p.get("side", "").lower() == "sell"])

        return {
            "virtual_positions": len(virtual_positions),
            "total_exposure": exposure.get("total", 0),
            "position_sides": {"buy": buy_count, "sell": sell_count},
            "buy_exposure": exposure.get("buy", 0),
            "sell_exposure": exposure.get("sell", 0),
        }

    async def emergency_cleanup(
        self, bitbank_client: Optional[BitbankClient] = None
    ) -> Dict[str, Any]:
        """
        緊急クリーンアップ（全仮想ポジション削除）

        Args:
            bitbank_client: Bitbank APIクライアント

        Returns:
            クリーンアップ結果
        """
        try:
            if not self.position_tracker:
                return {"success": False, "message": "PositionTrackerが未注入", "cleaned": 0}

            # 全仮想ポジション取得
            all_positions = self.position_tracker.get_all_positions()

            if not all_positions:
                return {"success": True, "message": "仮想ポジションなし", "cleaned": 0}

            # TP/SL注文削除（BitbankClient利用可能な場合）
            canceled_orders = 0
            if bitbank_client:
                for position in all_positions:
                    # TP注文削除
                    tp_order_id = position.get("tp_order_id")
                    if tp_order_id:
                        if await self._cancel_order(bitbank_client, tp_order_id):
                            canceled_orders += 1

                    # SL注文削除
                    sl_order_id = position.get("sl_order_id")
                    if sl_order_id:
                        if await self._cancel_order(bitbank_client, sl_order_id):
                            canceled_orders += 1

            # 全仮想ポジションクリア
            cleared_count = self.position_tracker.clear_all_positions()

            self.logger.warning(
                f"⚠️ 緊急クリーンアップ実行: "
                f"{cleared_count}ポジション削除, {canceled_orders}注文キャンセル"
            )

            return {
                "success": True,
                "message": "緊急クリーンアップ完了",
                "cleaned": cleared_count,
                "canceled_orders": canceled_orders,
            }

        except Exception as e:
            self.logger.error(f"❌ 緊急クリーンアップエラー: {e}")
            return {"success": False, "message": f"緊急クリーンアップエラー: {e}", "cleaned": 0}
