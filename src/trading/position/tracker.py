"""
ポジション追跡サービス - Phase 64

仮想ポジションの管理と追跡を行う。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ...core.logger import get_logger


class PositionTracker:
    """
    ポジション追跡サービス

    仮想ポジションの追加、削除、検索機能を提供する。
    Phase 46: 個別TP/SL実装（デイトレード特化）
    """

    def __init__(self):
        """PositionTracker初期化 - Phase 46: デイトレード特化・個別TP/SL"""
        self.logger = get_logger()
        self.virtual_positions: List[Dict[str, Any]] = []

        # 平均価格追跡（統計用）
        self._average_entry_price: float = 0.0
        self._total_position_size: float = 0.0

    def add_position(
        self,
        order_id: str,
        side: str,
        amount: float,
        price: float,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
        strategy_name: str = "unknown",
        tp_order_id: Optional[str] = None,
        sl_order_id: Optional[str] = None,
        sl_placed_at: Optional[str] = None,
        restored: bool = False,
        adjusted_confidence: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        ポジションを追加

        Args:
            order_id: 注文ID
            side: 注文サイド (buy/sell)
            amount: 数量
            price: 価格
            take_profit: TP価格
            stop_loss: SL価格
            strategy_name: 戦略名
            tp_order_id: TP注文ID
            sl_order_id: SL注文ID
            sl_placed_at: SL配置時刻 (Phase 64.3)
            restored: 復元フラグ (Phase 64.3)
            adjusted_confidence: 調整済み信頼度 (Phase 64.3)
            timestamp: タイムスタンプ (Phase 64.3, デフォルト: datetime.now())

        Returns:
            追加されたポジション情報
        """
        position = {
            "order_id": order_id,
            "side": side,
            "amount": amount,
            "price": price,
            "timestamp": timestamp or datetime.now(),
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "strategy_name": strategy_name,
        }

        # TP/SL注文IDがある場合は追加
        if tp_order_id:
            position["tp_order_id"] = tp_order_id
        if sl_order_id:
            position["sl_order_id"] = sl_order_id

        # Phase 64.3: 追加フィールド（条件付き）
        if sl_placed_at:
            position["sl_placed_at"] = sl_placed_at
        if restored:
            position["restored"] = True
        if adjusted_confidence is not None:
            position["adjusted_confidence"] = adjusted_confidence

        self.virtual_positions.append(position)

        self.logger.info(
            f"📝 ポジション追加: {side} {amount} BTC @ {price:.0f}円 "
            f"(ID: {order_id}, 戦略: {strategy_name})"
        )

        return position

    def remove_position(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        ポジションを削除

        Args:
            order_id: 削除する注文ID

        Returns:
            削除されたポジション情報（存在しない場合はNone）
        """
        for position in self.virtual_positions:
            if position.get("order_id") == order_id:
                self.virtual_positions.remove(position)
                self.logger.info(f"🗑️ ポジション削除: {order_id}")
                return position

        self.logger.warning(f"⚠️ ポジション未検出: {order_id}")
        return None

    def remove_position_with_cleanup(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Phase 49.6: ポジション削除＋TP/SL注文ID取得（クリーンアップ用）

        ポジションを削除し、紐づくTP/SL注文IDを返す。
        StopManager.cleanup_position_orders()との連携用。

        Args:
            order_id: 削除する注文ID

        Returns:
            Dict: {
                "position": 削除されたポジション情報,
                "tp_order_id": TP注文ID (存在する場合),
                "sl_order_id": SL注文ID (存在する場合)
            }
            存在しない場合はNone
        """
        for position in self.virtual_positions:
            if position.get("order_id") == order_id:
                self.virtual_positions.remove(position)

                tp_order_id = position.get("tp_order_id")
                sl_order_id = position.get("sl_order_id")

                self.logger.info(
                    f"🗑️ Phase 49.6: ポジション削除（クリーンアップ対象）: {order_id} | "
                    f"TP注文ID: {tp_order_id or 'なし'}, SL注文ID: {sl_order_id or 'なし'}"
                )

                return {
                    "position": position,
                    "tp_order_id": tp_order_id,
                    "sl_order_id": sl_order_id,
                }

        self.logger.warning(f"⚠️ ポジション未検出: {order_id}")
        return None

    def find_position(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        ポジションを検索

        Args:
            order_id: 検索する注文ID

        Returns:
            ポジション情報（存在しない場合はNone）
        """
        for position in self.virtual_positions:
            if position.get("order_id") == order_id:
                return position
        return None

    def find_positions_by_side(self, side: str) -> List[Dict[str, Any]]:
        """
        サイドでポジションを検索

        Args:
            side: 注文サイド (buy/sell)

        Returns:
            該当するポジションリスト
        """
        return [
            pos for pos in self.virtual_positions if pos.get("side", "").lower() == side.lower()
        ]

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """
        すべてのポジションを取得

        Returns:
            全ポジションリスト
        """
        return self.virtual_positions.copy()

    def get_position_count(self) -> int:
        """
        ポジション数を取得

        Returns:
            ポジション数
        """
        return len(self.virtual_positions)

    def get_total_exposure(self) -> Dict[str, float]:
        """
        合計エクスポージャーを計算

        Returns:
            {"buy": float, "sell": float, "total": float}
        """
        buy_exposure = sum(
            pos["amount"] * pos["price"]
            for pos in self.virtual_positions
            if pos.get("side", "").lower() == "buy"
        )
        sell_exposure = sum(
            pos["amount"] * pos["price"]
            for pos in self.virtual_positions
            if pos.get("side", "").lower() == "sell"
        )

        return {
            "buy": buy_exposure,
            "sell": sell_exposure,
            "total": buy_exposure + sell_exposure,
        }

    def get_latest_positions(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        最新のポジションを取得

        Args:
            count: 取得する件数

        Returns:
            最新のポジションリスト
        """
        return self.virtual_positions[-count:] if self.virtual_positions else []

    def clear_all_positions(self) -> int:
        """
        すべてのポジションをクリア

        Returns:
            クリアされたポジション数
        """
        count = len(self.virtual_positions)
        self.virtual_positions.clear()
        self.logger.info(f"🧹 全ポジションクリア: {count}件")
        return count

    def update_position_tp_sl(
        self, order_id: str, tp_order_id: Optional[str] = None, sl_order_id: Optional[str] = None
    ) -> bool:
        """
        ポジションのTP/SL注文IDを更新

        Args:
            order_id: 対象ポジションの注文ID
            tp_order_id: TP注文ID
            sl_order_id: SL注文ID

        Returns:
            更新成功の可否
        """
        position = self.find_position(order_id)
        if not position:
            return False

        if tp_order_id:
            position["tp_order_id"] = tp_order_id
            self.logger.info(f"📝 TP注文ID更新: {order_id} -> {tp_order_id}")

        if sl_order_id:
            position["sl_order_id"] = sl_order_id
            self.logger.info(f"📝 SL注文ID更新: {order_id} -> {sl_order_id}")

        return True

    def get_orphaned_positions(
        self, actual_positions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        実際のポジションと比較して消失したポジションを検出

        Args:
            actual_positions: 実際のポジションリスト

        Returns:
            消失したポジションリスト
        """
        orphaned = []

        for vpos in self.virtual_positions:
            vpos_side = vpos.get("side", "").lower()
            vpos_amount = float(vpos.get("amount", 0))

            # 実際のポジションに一致するものがあるか確認
            matched = False
            for actual_pos in actual_positions:
                actual_side = actual_pos.get("side", "").lower()
                actual_amount = float(actual_pos.get("amount", 0))

                if actual_side == vpos_side and abs(actual_amount - vpos_amount) < 0.00001:
                    matched = True
                    break

            if not matched:
                orphaned.append(vpos)

        if orphaned:
            self.logger.warning(
                f"🔍 消失ポジション検出: {len(orphaned)}件 / 全{len(self.virtual_positions)}件"
            )

        return orphaned

    # ========================================
    # 統計用メソッド（平均価格計算）
    # ========================================

    def calculate_average_entry_price(self) -> float:
        """
        加重平均エントリー価格計算

        全ての仮想ポジションから加重平均価格を計算する。

        Returns:
            float: 加重平均エントリー価格（ポジションがない場合は0.0）
        """
        if not self.virtual_positions:
            return 0.0

        total_value = sum(
            float(pos.get("price", 0)) * float(pos.get("amount", 0))
            for pos in self.virtual_positions
        )
        total_size = sum(float(pos.get("amount", 0)) for pos in self.virtual_positions)

        if total_size == 0:
            return 0.0

        average_price = total_value / total_size
        self.logger.debug(
            f"📊 平均エントリー価格計算: {average_price:.0f}円 "
            f"(総額: {total_value:.0f}円 / 総数量: {total_size:.6f} BTC)"
        )

        return average_price

    def update_average_on_entry(self, price: float, amount: float) -> float:
        """
        新規エントリー時に平均価格更新

        Args:
            price: 新規エントリー価格
            amount: 新規エントリー数量

        Returns:
            float: 更新後の平均エントリー価格
        """
        old_average = self._average_entry_price
        old_size = self._total_position_size

        new_total_value = (old_average * old_size) + (price * amount)
        new_total_size = old_size + amount

        if new_total_size > 0:
            self._average_entry_price = new_total_value / new_total_size
            self._total_position_size = new_total_size
        else:
            self._average_entry_price = 0.0
            self._total_position_size = 0.0

        self.logger.info(
            f"📈 平均価格更新: {old_average:.0f}円 → {self._average_entry_price:.0f}円 "
            f"(新規: {amount:.6f} BTC @ {price:.0f}円)"
        )

        return self._average_entry_price

    def update_average_on_exit(self, amount: float) -> float:
        """
        決済時に平均価格更新

        Args:
            amount: 決済数量

        Returns:
            float: 更新後の平均エントリー価格（全決済時は0.0）
        """
        old_size = self._total_position_size
        new_size = max(0, old_size - amount)

        if new_size == 0:
            # 全決済
            self._average_entry_price = 0.0
            self._total_position_size = 0.0
            self.logger.info("📤 全ポジション決済 - 平均価格リセット")
        else:
            # 部分決済（平均価格は維持）
            self._total_position_size = new_size
            self.logger.info(
                f"📤 部分決済: {old_size:.6f} BTC → {new_size:.6f} BTC "
                f"(平均価格維持: {self._average_entry_price:.0f}円)"
            )

        return self._average_entry_price

    # ========================================
    # Phase 61.9: TP/SL自動執行検知用ヘルパー
    # ========================================

    def find_position_by_tp_order_id(self, tp_order_id: str) -> Optional[Dict[str, Any]]:
        """
        Phase 61.9: TP注文IDでポジションを検索

        Args:
            tp_order_id: TP注文ID

        Returns:
            ポジション情報（存在しない場合はNone）
        """
        for position in self.virtual_positions:
            if position.get("tp_order_id") == tp_order_id:
                return position
        return None

    def find_position_by_sl_order_id(self, sl_order_id: str) -> Optional[Dict[str, Any]]:
        """
        Phase 61.9: SL注文IDでポジションを検索

        Args:
            sl_order_id: SL注文ID

        Returns:
            ポジション情報（存在しない場合はNone）
        """
        for position in self.virtual_positions:
            if position.get("sl_order_id") == sl_order_id:
                return position
        return None

    def remove_position_by_tp_or_sl_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Phase 61.9: TP注文IDまたはSL注文IDでポジション削除

        Args:
            order_id: TP注文IDまたはSL注文ID

        Returns:
            削除されたポジション情報（存在しない場合はNone）
        """
        for position in self.virtual_positions:
            if position.get("tp_order_id") == order_id or position.get("sl_order_id") == order_id:
                self.virtual_positions.remove(position)
                self.logger.info(
                    f"🗑️ Phase 61.9: ポジション削除（TP/SL約定）- order_id={position.get('order_id')}"
                )
                return position

        self.logger.warning(f"⚠️ Phase 61.9: ポジション未検出 - tp_or_sl_order_id={order_id}")
        return None
