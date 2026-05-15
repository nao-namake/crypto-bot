"""
SL注文IDの永続化 - Phase 68.4 (Phase 87 H4 で内部実装を Firestore 化)

bitbankのstop_limit注文はトリガー価格到達前にINACTIVE状態となり、
fetch_active_orders（ccxt fetch_open_orders）に返されない。
Container再起動でVP（インメモリ）が消失すると、SL order IDも喪失し、
BotがSLを「存在しない」と誤判定する問題を解決する。

Phase 87 H4: ローカルJSON（Cloud Run ephemeral FSで消失）→ Firestore へ。
外部APIシグネチャ（save/load/clear/verify_with_api）は完全維持。
Firestore 不通時は自動的にローカル JSON へフォールバック。
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ...core.logger import get_logger
from ...core.persistence import FirestoreStateClient


class SLStatePersistence:
    """SL注文IDの永続化（INACTIVE SL対策 / Phase 87 H4: Firestore化）"""

    DEFAULT_STATE_PATH = "data/sl_state.json"
    COLLECTION = "sl_state"  # Phase 87 H4: Firestore コレクション名

    def __init__(
        self,
        state_path: Optional[str] = None,
        persistence: Optional[FirestoreStateClient] = None,
    ):
        """
        Args:
            state_path: ローカル JSON フォールバックのパス（後方互換）。
                親ディレクトリが FirestoreStateClient の local_fallback_dir になる。
            persistence: テスト用に FirestoreStateClient を外部注入可能。
        """
        self.state_path = state_path or self.DEFAULT_STATE_PATH
        self.logger = get_logger()

        if persistence is not None:
            self.persistence = persistence
        else:
            local_dir = os.path.dirname(self.state_path) or "data"
            self.persistence = FirestoreStateClient(local_fallback_dir=local_dir)

    # Phase 89 C7: 実 order_id ではない placeholder 文字列（save 拒否対象）
    PLACEHOLDER_ORDER_IDS = frozenset({"existing", "none", "null", "", "unknown"})

    def save(
        self,
        side: str,
        sl_order_id: str,
        sl_price: float,
        amount: float,
        sl_placed_at: str = None,
    ) -> None:
        """SL配置成功時に保存

        Args:
            side: エントリーサイド (buy/sell)
            sl_order_id: SL注文ID
            sl_price: SLトリガー価格
            amount: ポジション数量
            sl_placed_at: SL配置時刻ISO文字列（Phase 69.6: タイムアウト計算用）
        """
        # Phase 89 C7: placeholder ID は永続化拒否（fetch_order が必ず失敗するため）
        if str(sl_order_id).strip().lower() in self.PLACEHOLDER_ORDER_IDS:
            self.logger.critical(
                f"🚨 Phase 89 C7: SL永続化拒否 - placeholder ID 検出 "
                f"(sl_order_id={sl_order_id!r}, side={side}, price={sl_price:.0f}円)。"
                f"position_restorer 等で実 order_id が取得できていない可能性。手動確認推奨。"
            )
            return

        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            data = {
                "sl_order_id": str(sl_order_id),
                "sl_price": sl_price,
                "amount": amount,
                "sl_placed_at": sl_placed_at or now_iso,
                "saved_at": now_iso,
            }
            # Phase 87 Stage 2-R2: 戻り値検証で silent failure 解消
            saved = self.persistence.save(self.COLLECTION, side, data)
            if saved:
                self.logger.info(
                    f"Phase 68.4/H4: SL永続化保存 - {side} ID={sl_order_id}, "
                    f"price={sl_price:.0f}, amount={amount:.4f}"
                )
            else:
                # Firestore + ローカル fallback 両方失敗 → SL永続化が機能不全
                self.logger.critical(
                    f"🚨🚨 Phase 87 Stage 2-R2: SL永続化完全失敗 - "
                    f"{side} ID={sl_order_id}, price={sl_price:.0f}円。"
                    f"Container再起動時にSL注文IDが消失する可能性。手動確認推奨。"
                )
        except Exception as e:
            self.logger.error(f"Phase 68.4/H4: SL永続化保存エラー: {e}")

    def load(self) -> Dict[str, Any]:
        """起動時に読み込み

        Returns:
            Dict: {"buy": {...}, "sell": {...}} or {}
        """
        try:
            return self.persistence.load_collection(self.COLLECTION)
        except Exception as e:
            self.logger.warning(f"Phase 68.4/H4: SL永続化読み込みエラー: {e}")
            return {}

    def clear(self, side: str) -> None:
        """ポジション決済時にクリア

        Args:
            side: エントリーサイド (buy/sell)
        """
        try:
            self.persistence.delete(self.COLLECTION, side)
            self.logger.info(f"Phase 68.4/H4: SL永続化クリア - {side}")
        except Exception as e:
            self.logger.error(f"Phase 68.4/H4: SL永続化クリアエラー: {e}")

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
            sl_info = self.persistence.load(self.COLLECTION, side)
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
