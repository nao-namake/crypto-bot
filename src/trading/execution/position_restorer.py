"""
ポジション復元・孤児スキャン - Phase 64.4

executor.pyから2メソッドを抽出し、起動時ポジション復元と孤児スキャンを集約。

責務:
- 起動時の実ポジションベース復元（restore_positions_from_api）
- 30分間隔の孤児ポジション定期スキャン（scan_orphan_positions）
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient
from .tp_sl_config import TPSLConfig


class PositionRestorer:
    """ポジション復元・孤児スキャン"""

    def __init__(self):
        self.logger = get_logger()
        self._last_orphan_scan_time: Optional[datetime] = None

    # ========================================
    # 起動時ポジション復元
    # ========================================

    async def restore_positions_from_api(
        self,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
        position_tracker: Any,
        mode: str,
    ) -> None:
        """
        Phase 63.4: 実ポジションベースの復元

        Cloud Run環境では5分毎にコンテナが再起動される可能性があり、
        その際にvirtual_positions = []にリセットされてしまう。

        Args:
            virtual_positions: 仮想ポジションリスト（直接更新される）
            bitbank_client: BitbankClientインスタンス
            position_tracker: PositionTrackerインスタンス
            mode: 実行モード
        """
        if mode != "live":
            return

        try:
            # Step 1: 実ポジション取得（信用建玉）
            margin_positions = await bitbank_client.fetch_margin_positions("BTC/JPY")

            if not margin_positions:
                self.logger.info("📊 Phase 63.4: 実ポジションなし")
                return

            # ログ出力
            for pos in margin_positions:
                self.logger.info(
                    f"  └ {pos.get('side')} {pos.get('amount', 0):.4f} BTC "
                    f"@ {pos.get('average_price', 0):.0f}円"
                )

            # Step 2: アクティブ注文取得（TP/SLマッチング用）
            active_orders = await asyncio.to_thread(
                bitbank_client.fetch_active_orders,
                "BTC/JPY",
                TPSLConfig.API_ORDER_LIMIT,
            )

            # Step 3: 各ポジションに対してvirtual_position作成
            restored_count = 0
            for pos in margin_positions:
                pos_side = pos.get("side")  # "long" or "short"
                pos_amount = float(pos.get("amount", 0))
                avg_price = float(pos.get("average_price", pos.get("avg_price", 0)))

                if pos_amount <= 0:
                    continue

                entry_side = "buy" if pos_side == "long" else "sell"
                exit_side = "sell" if pos_side == "long" else "buy"

                # TP/SL注文をマッチング
                tp_order_id = None
                sl_order_id = None
                tp_price = None
                sl_price = None
                sl_placed_at = None

                for order in active_orders or []:
                    order_side = order.get("side", "").lower()
                    order_type = order.get("type", "").lower()

                    if order_side == exit_side:
                        if order_type == "limit" and not tp_order_id:
                            tp_order_id = str(order.get("id", ""))
                            tp_price = float(order.get("price", 0))
                        elif order_type in ("stop", "stop_limit") and not sl_order_id:
                            # Phase 64.12: トリガー価格の妥当性検証（3%以内）
                            trigger_price = float(
                                order.get(
                                    "stopPrice",
                                    order.get(
                                        "triggerPrice",
                                        order.get("price", 0),
                                    ),
                                )
                            )
                            if avg_price > 0 and trigger_price > 0:
                                distance_ratio = abs(trigger_price - avg_price) / avg_price
                                if distance_ratio > 0.03:
                                    self.logger.warning(
                                        f"⚠️ Phase 64.12: SL注文スキップ（価格乖離 "
                                        f"{distance_ratio * 100:.1f}%）"
                                        f" - ID: {order.get('id')}, "
                                        f"trigger={trigger_price:.0f}, avg={avg_price:.0f}"
                                    )
                                    continue
                            sl_order_id = str(order.get("id", ""))
                            sl_price = trigger_price
                            order_dt = order.get("datetime")
                            sl_placed_at = (
                                order_dt if order_dt else datetime.now(timezone.utc).isoformat()
                            )

                virtual_positions.append(
                    {
                        "order_id": f"restored_{pos_side}_{int(datetime.now().timestamp())}",
                        "side": entry_side,
                        "amount": pos_amount,
                        "price": avg_price,
                        "timestamp": datetime.now(),
                        "take_profit": tp_price,
                        "stop_loss": sl_price,
                        "tp_order_id": tp_order_id,
                        "sl_order_id": sl_order_id,
                        "sl_placed_at": sl_placed_at,
                        "restored": True,
                    }
                )
                restored_count += 1

                self.logger.info(
                    f"✅ Phase 63.4: ポジション復元 - {pos_side} {pos_amount:.4f} BTC "
                    f"@ {avg_price:.0f}円 "
                    f"(TP: {'あり' if tp_order_id else 'なし'}, "
                    f"SL: {'あり' if sl_order_id else 'なし'})"
                )

            self.logger.info(f"✅ Phase 63.4: {restored_count}件のポジション復元完了")

        except Exception as e:
            self.logger.warning(f"⚠️ Phase 63.4: ポジション復元失敗: {e}")

    # ========================================
    # 孤児ポジション定期スキャン
    # ========================================

    async def scan_orphan_positions(
        self,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
        tp_sl_manager: Any,
    ) -> None:
        """
        Phase 63.3: 孤児ポジション定期スキャン（30分間隔）

        bitbank上に実ポジションがあるがvirtual_positionsに存在しないケースを検出。

        Args:
            virtual_positions: 仮想ポジションリスト（直接更新される）
            bitbank_client: BitbankClientインスタンス
            tp_sl_manager: TPSLManagerインスタンス
        """
        now = datetime.now()
        scan_interval = get_threshold(TPSLConfig.ORPHAN_SCAN_INTERVAL, 1800)

        if (
            self._last_orphan_scan_time
            and (now - self._last_orphan_scan_time).total_seconds() < scan_interval
        ):
            return

        self._last_orphan_scan_time = now

        try:
            symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")
            actual_positions = await bitbank_client.fetch_margin_positions(symbol)

            if not actual_positions:
                return

            for pos in actual_positions:
                pos_side = pos.get("side", "")
                pos_amount = float(pos.get("amount", 0))

                if pos_amount <= 0:
                    continue

                # virtual_positionsに同じサイドのエントリがあるかチェック
                has_matching = False
                for vp in virtual_positions:
                    vp_side = "long" if vp.get("side") == "buy" else "short"
                    if vp_side == pos_side:
                        has_matching = True
                        break

                if has_matching:
                    continue

                # 孤児ポジション検出
                self.logger.warning(
                    f"🔍 Phase 63.3: 孤児ポジション検出 - "
                    f"side={pos_side}, amount={pos_amount} BTC"
                )

                # アクティブ注文でTP/SLが既にあるか確認（Phase 64.4: 数量ベース95%カバレッジ）
                active_orders = await asyncio.to_thread(bitbank_client.fetch_active_orders, symbol)
                entry_side = "buy" if pos_side == "long" else "sell"
                exit_side = "sell" if pos_side == "long" else "buy"

                tp_total = sum(
                    float(o.get("amount", 0))
                    for o in active_orders
                    if o.get("side", "").lower() == exit_side
                    and o.get("type", "").lower() == "limit"
                )
                sl_total = sum(
                    float(o.get("amount", 0))
                    for o in active_orders
                    if o.get("side", "").lower() == exit_side
                    and o.get("type", "").lower() in ("stop", "stop_limit")
                )
                has_tp = tp_total >= pos_amount * 0.95
                has_sl = sl_total >= pos_amount * 0.95

                if has_tp and has_sl:
                    self.logger.info(
                        f"✅ Phase 63.3: 孤児ポジションにTP/SL既設置 - "
                        f"side={pos_side}, amount={pos_amount} BTC"
                    )
                    avg_price = float(pos.get("avg_price", pos.get("price", 0)))
                    orphan_entry = {
                        "order_id": f"orphan_{pos_side}_{int(now.timestamp())}",
                        "side": entry_side,
                        "amount": pos_amount,
                        "price": avg_price,
                        "timestamp": now,
                        "take_profit": None,
                        "stop_loss": None,
                        "tp_order_id": "existing",
                        "sl_order_id": "existing",
                        "sl_placed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    virtual_positions.append(orphan_entry)
                    continue

                # TP/SLがない場合は設置試行
                avg_price = float(pos.get("avg_price", pos.get("price", 0)))
                if avg_price <= 0:
                    self.logger.critical(
                        f"🚨 Phase 63.3: 孤児ポジションの平均価格取得失敗 - "
                        f"手動介入必要。side={pos_side}, amount={pos_amount} BTC"
                    )
                    continue

                # Phase 64.9: 共通ヘルパーで計算（デフォルト: normal_range = 安全側）
                tp_price, sl_price = tp_sl_manager.calculate_recovery_tp_sl_prices(
                    position_side=pos_side,
                    avg_price=avg_price,
                )

                self.logger.warning(
                    f"⚠️ Phase 63.3: 孤児ポジションTP/SL設置試行 - "
                    f"side={pos_side}, amount={pos_amount} BTC, "
                    f"avg_price={avg_price:.0f}円, TP={tp_price:.0f}円, SL={sl_price:.0f}円"
                )

                tp_result = None
                sl_result = None
                try:
                    if not has_tp:
                        tp_result = await tp_sl_manager.place_tp_with_retry(
                            side=entry_side,
                            amount=pos_amount,
                            entry_price=avg_price,
                            take_profit_price=tp_price,
                            symbol=symbol,
                            bitbank_client=bitbank_client,
                            max_retries=3,
                        )
                    if not has_sl:
                        # Phase 64.4: 共通ヘルパーに委譲
                        sl_result = await tp_sl_manager.place_sl_or_market_close(
                            entry_side=entry_side,
                            position_side=pos_side,
                            amount=pos_amount,
                            avg_price=avg_price,
                            sl_price=sl_price,
                            symbol=symbol,
                            bitbank_client=bitbank_client,
                        )
                except Exception as tp_sl_err:
                    self.logger.critical(
                        f"🚨 Phase 63.3: 孤児TP/SL設置失敗 - "
                        f"手動介入必要。side={pos_side}, amount={pos_amount} BTC, "
                        f"error={tp_sl_err}"
                    )
                    continue

                # Phase 64.2: TP/SL両方成功した場合のみvirtual_positionsに追加
                tp_ok = has_tp or (tp_result and tp_result.get("order_id"))
                sl_ok = has_sl or (sl_result and sl_result.get("order_id"))

                if tp_ok and sl_ok:
                    orphan_entry = {
                        "order_id": f"orphan_{pos_side}_{int(now.timestamp())}",
                        "side": entry_side,
                        "amount": pos_amount,
                        "price": avg_price,
                        "timestamp": now,
                        "take_profit": tp_price,
                        "stop_loss": sl_price,
                        "tp_order_id": (tp_result.get("order_id") if tp_result else None),
                        "sl_order_id": (sl_result.get("order_id") if sl_result else None),
                        "sl_placed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    virtual_positions.append(orphan_entry)
                    self.logger.info(
                        f"✅ Phase 63.3: 孤児ポジションTP/SL設置・virtual_positions追加完了 - "
                        f"side={pos_side}, amount={pos_amount} BTC"
                    )
                else:
                    self.logger.critical(
                        f"🚨 Phase 64.2: 孤児TP/SL配置不完全（virtual_positions未追加・次回チェックで再試行）"
                        f" - TP={'OK' if tp_ok else 'NG'}, SL={'OK' if sl_ok else 'NG'}"
                        f" (side={pos_side}, amount={pos_amount} BTC)"
                    )

        except Exception as e:
            self.logger.warning(f"⚠️ Phase 63.3: 孤児スキャンエラー: {e}")

    # ========================================
    # Phase 51.6: 古い注文クリーンアップ（bitbank 30件制限対策）
    # ========================================

    async def cleanup_old_unfilled_orders(
        self,
        symbol: str,
        bitbank_client: BitbankClient,
        virtual_positions: List[Dict[str, Any]],
        max_age_hours: int = 24,
        threshold_count: int = 25,
    ) -> Dict[str, Any]:
        """
        Phase 51.6: 古い未約定注文クリーンアップ（bitbank 30件制限対策）

        bitbank API仕様: 同一取引ペアで30件制限（エラー60011）
        「孤児注文」（ポジションが存在しない古い注文）のみを削除し、
        アクティブなポジションのTP/SL注文は保護する。

        Args:
            symbol: 通貨ペア（例: "BTC/JPY"）
            bitbank_client: BitbankClientインスタンス
            virtual_positions: 現在のアクティブポジション（TP/SL注文ID含む）
            max_age_hours: 削除対象の注文経過時間（デフォルト24時間）
            threshold_count: クリーンアップ発動閾値（デフォルト25件・30件の83%）

        Returns:
            Dict: {"cancelled_count": int, "order_count": int, "errors": List[str]}
        """
        try:
            # アクティブ注文取得
            active_orders = await asyncio.to_thread(
                bitbank_client.fetch_active_orders, symbol, limit=100
            )
            order_count = len(active_orders)

            # 閾値未満なら何もしない
            if order_count < threshold_count:
                self.logger.debug(
                    f"📊 Phase 51.6: アクティブ注文数{order_count}件（{threshold_count}件未満・クリーンアップ不要）"
                )
                return {"cancelled_count": 0, "order_count": order_count, "errors": []}

            self.logger.warning(
                f"⚠️ Phase 51.6: アクティブ注文数{order_count}件（{threshold_count}件以上）- 古い注文クリーンアップ開始"
            )

            # アクティブポジションのTP/SL注文IDを収集（削除対象から除外）
            protected_order_ids = set()
            for position in virtual_positions:
                # Phase 53.12: 復元されたポジションのorder_idを保護
                if position.get("restored"):
                    order_id = position.get("order_id")
                    if order_id:
                        protected_order_ids.add(str(order_id))
                # 通常のポジションのTP/SL注文を保護
                else:
                    tp_id = position.get("tp_order_id")
                    sl_id = position.get("sl_order_id")
                    if tp_id:
                        protected_order_ids.add(str(tp_id))
                    if sl_id:
                        protected_order_ids.add(str(sl_id))

            if protected_order_ids:
                self.logger.info(
                    f"🛡️ Phase 51.6: {len(protected_order_ids)}件の注文を保護（アクティブポジション）"
                )

            # 24時間以上経過した孤児注文を抽出
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            old_orphan_orders = []

            for order in active_orders:
                order_id = str(order.get("id"))

                # アクティブポジションのTP/SL注文は除外
                if order_id in protected_order_ids:
                    continue

                # TP注文のみ対象（limit注文）
                if order.get("type") != "limit":
                    continue

                # 注文時刻チェック
                order_timestamp = order.get("timestamp", 0)
                if order_timestamp == 0:
                    continue

                order_time = datetime.fromtimestamp(order_timestamp / 1000)
                if order_time < cutoff_time:
                    old_orphan_orders.append(order)

            if not old_orphan_orders:
                self.logger.info(
                    f"ℹ️ Phase 51.6: 24時間以上経過した孤児注文なし（{order_count}件中0件）"
                )
                return {"cancelled_count": 0, "order_count": order_count, "errors": []}

            # 古い孤児注文を削除
            cancelled_count = 0
            errors = []

            for order in old_orphan_orders:
                order_id = order.get("id")
                try:
                    await asyncio.to_thread(bitbank_client.cancel_order, order_id, symbol)
                    cancelled_count += 1
                    self.logger.info(
                        f"✅ Phase 51.6: 古いTP注文キャンセル成功 - ID: {order_id}, "
                        f"経過時間: {(datetime.now() - datetime.fromtimestamp(order['timestamp'] / 1000)).total_seconds() / 3600:.1f}時間"
                    )
                except Exception as e:
                    error_msg = f"注文{order_id}キャンセル失敗: {e}"
                    # OrderNotFoundは許容（既にキャンセル/約定済み）
                    if "OrderNotFound" in str(e) or "not found" in str(e).lower():
                        self.logger.debug(f"ℹ️ {error_msg}（既にキャンセル/約定済み）")
                    else:
                        errors.append(error_msg)
                        self.logger.warning(f"⚠️ {error_msg}")

            self.logger.info(
                f"🧹 Phase 51.6: 古い孤児注文クリーンアップ完了 - "
                f"{cancelled_count}件キャンセル（{order_count}件中{len(old_orphan_orders)}件対象・保護{len(protected_order_ids)}件）"
            )

            return {
                "cancelled_count": cancelled_count,
                "order_count": order_count,
                "errors": errors,
            }

        except Exception as e:
            self.logger.error(f"❌ Phase 51.6: 古い注文クリーンアップエラー: {e}")
            return {"cancelled_count": 0, "order_count": 0, "errors": [str(e)]}

    # ========================================
    # Phase 59.6: 孤児SLクリーンアップ
    # ========================================

    async def cleanup_orphan_sl_orders(
        self,
        bitbank_client: BitbankClient,
        symbol: str = "BTC/JPY",
    ) -> Dict[str, Any]:
        """
        Phase 59.6: 起動時に孤児SL候補をクリーンアップ

        前回実行時にキャンセルに失敗したSL注文を削除する。

        Args:
            bitbank_client: BitbankClientインスタンス
            symbol: 通貨ペア

        Returns:
            Dict: {"cleaned": int, "failed": int, "errors": List[str]}
        """
        orphan_file = Path("logs/orphan_sl_orders.json")

        if not orphan_file.exists():
            self.logger.debug("📊 Phase 59.6: 孤児SL候補なし")
            return {"cleaned": 0, "failed": 0, "errors": []}

        try:
            orphans = json.loads(orphan_file.read_text())
        except json.JSONDecodeError:
            orphan_file.unlink()
            return {"cleaned": 0, "failed": 0, "errors": ["JSONデコードエラー"]}

        if not orphans:
            orphan_file.unlink()
            return {"cleaned": 0, "failed": 0, "errors": []}

        self.logger.info(f"🧹 Phase 59.6: 孤児SLクリーンアップ開始 - {len(orphans)}件")

        cleaned = 0
        failed = 0
        errors = []

        for orphan in orphans:
            sl_order_id = orphan.get("sl_order_id")
            if not sl_order_id:
                continue

            try:
                await asyncio.to_thread(bitbank_client.cancel_order, sl_order_id, symbol)
                cleaned += 1
                self.logger.info(f"✅ Phase 59.6: 孤児SL削除成功 - ID: {sl_order_id}")
            except Exception as e:
                error_str = str(e)
                # OrderNotFoundは許容（既にキャンセル/約定済み）
                if "OrderNotFound" in error_str or "not found" in error_str.lower():
                    cleaned += 1  # 既に削除済みなのでcleanedにカウント
                    self.logger.debug(f"ℹ️ Phase 59.6: 孤児SL既に削除済み - ID: {sl_order_id}")
                else:
                    failed += 1
                    errors.append(f"SL {sl_order_id}: {error_str}")
                    self.logger.warning(f"⚠️ Phase 59.6: 孤児SL削除失敗 - ID: {sl_order_id}: {e}")

        # ファイル削除
        try:
            orphan_file.unlink()
        except Exception:
            pass

        self.logger.info(
            f"🧹 Phase 59.6: 孤児SLクリーンアップ完了 - " f"成功: {cleaned}件, 失敗: {failed}件"
        )

        return {"cleaned": cleaned, "failed": failed, "errors": errors}
