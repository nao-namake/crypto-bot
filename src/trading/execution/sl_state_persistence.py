"""
SL注文IDのローカルファイル永続化 - Phase 68.4

bitbankのstop_limit注文はトリガー価格到達前にINACTIVE状態となり、
fetch_active_orders（ccxt fetch_open_orders）に返されない。
Container再起動でVP（インメモリ）が消失すると、SL order IDも喪失し、
BotがSLを「存在しない」と誤判定する問題を解決する。

drawdown.pyの_save_state/_load_stateパターンを参考に、
SL注文IDをローカルJSONファイルに永続化する。
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ...core.logger import get_logger


class SLStatePersistence:
    """SL注文IDのローカルファイル永続化（INACTIVE SL対策）"""

    DEFAULT_STATE_PATH = "data/sl_state.json"

    def __init__(self, state_path: str = None):
        self.state_path = state_path or self.DEFAULT_STATE_PATH
        self.logger = get_logger()

    def save(self, side: str, sl_order_id: str, sl_price: float, amount: float) -> None:
        """SL配置成功時に保存

        Args:
            side: エントリーサイド (buy/sell)
            sl_order_id: SL注文ID
            sl_price: SLトリガー価格
            amount: ポジション数量
        """
        try:
            state = self._load_raw()
            state[side] = {
                "sl_order_id": str(sl_order_id),
                "sl_price": sl_price,
                "amount": amount,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            self._write(state)
            self.logger.info(
                f"Phase 68.4: SL永続化保存 - {side} ID={sl_order_id}, "
                f"price={sl_price:.0f}, amount={amount:.4f}"
            )
        except Exception as e:
            self.logger.error(f"Phase 68.4: SL永続化保存エラー: {e}")

    def load(self) -> Dict[str, Any]:
        """起動時に読み込み

        Returns:
            Dict: {"buy": {...}, "sell": {...}} or {}
        """
        return self._load_raw()

    def clear(self, side: str) -> None:
        """ポジション決済時にクリア

        Args:
            side: エントリーサイド (buy/sell)
        """
        try:
            state = self._load_raw()
            if side in state:
                del state[side]
                self._write(state)
                self.logger.info(f"Phase 68.4: SL永続化クリア - {side}")
        except Exception as e:
            self.logger.error(f"Phase 68.4: SL永続化クリアエラー: {e}")

    def verify_with_api(
        self, side: str, bitbank_client: Any, symbol: str = "BTC/JPY"
    ) -> Optional[str]:
        """保存済みSL IDをfetch_orderで検証、有効ならIDを返す

        INACTIVE状態のSL注文もfetch_order(id)で個別取得可能。
        ステータスがopen/INACTIVE/activeなら有効とみなす。

        Args:
            side: エントリーサイド (buy/sell)
            bitbank_client: BitbankClientインスタンス
            symbol: 通貨ペア

        Returns:
            有効なSL注文IDまたはNone
        """
        try:
            state = self._load_raw()
            sl_info = state.get(side)
            if not sl_info:
                return None

            sl_order_id = sl_info.get("sl_order_id")
            if not sl_order_id:
                return None

            # fetch_orderでINACTIVE含むステータス取得
            order = bitbank_client.fetch_order(sl_order_id, symbol)
            if not order:
                self.logger.info(
                    f"Phase 68.4: 永続化SL検証失敗（注文なし） - {side} ID={sl_order_id}"
                )
                self.clear(side)
                return None

            status = str(order.get("status", "")).lower()
            # open, INACTIVE, active は有効（canceled, closed, expired は無効）
            valid_statuses = ("open", "inactive", "active", "unfilled", "partially_filled")
            if status in valid_statuses:
                self.logger.info(
                    f"Phase 68.4: 永続化SL検証成功 - {side} ID={sl_order_id}, " f"status={status}"
                )
                return sl_order_id
            else:
                self.logger.info(
                    f"Phase 68.4: 永続化SL無効（status={status}） - {side} ID={sl_order_id}"
                )
                self.clear(side)
                return None

        except Exception as e:
            error_str = str(e)
            if "OrderNotFound" in error_str or "not found" in error_str.lower():
                self.logger.info(
                    f"Phase 68.4: 永続化SL検証 - 注文消失（約定/キャンセル済み） - {side}"
                )
                self.clear(side)
            else:
                self.logger.warning(f"Phase 68.4: 永続化SL検証エラー: {e}")
            return None

    def _load_raw(self) -> Dict[str, Any]:
        """JSONファイル読み込み"""
        try:
            if not os.path.exists(self.state_path):
                return {}
            with open(self.state_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write(self, state: Dict[str, Any]) -> None:
        """JSONファイル書き込み"""
        os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(state, f, indent=2)
