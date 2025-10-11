"""
ポジション追跡サービス - Phase 38リファクタリング

仮想ポジションの管理と追跡を行う。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from ...core.logger import get_logger


class PositionTracker:
    """
    ポジション追跡サービス

    仮想ポジションの追加、削除、検索機能を提供する。
    """

    def __init__(self):
        """PositionTracker初期化"""
        self.logger = get_logger()
        self.virtual_positions: List[Dict[str, Any]] = []

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

        Returns:
            追加されたポジション情報
        """
        position = {
            "order_id": order_id,
            "side": side,
            "amount": amount,
            "price": price,
            "timestamp": datetime.now(),
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "strategy_name": strategy_name,
        }

        # TP/SL注文IDがある場合は追加
        if tp_order_id:
            position["tp_order_id"] = tp_order_id
        if sl_order_id:
            position["sl_order_id"] = sl_order_id

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
