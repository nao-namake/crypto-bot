"""
ストップ条件管理サービス - Phase 62.17: stop_limit未約定バグ修正
Phase 28: TP/SL機能、Phase 31.1: 柔軟クールダウン、Phase 37.5.3: 残注文クリーンアップ
Phase 46: 個別TP/SL配置、Phase 49.6: ポジション決済時クリーンアップ
Phase 51.6: Discord通知削除・SL価格検証強化・エラー30101対策
Phase 61.3: 決済注文の約定確認・リトライ機能
Phase 62.17: stop_limit未約定バグ修正（Bot側SL監視スキップ・タイムアウトフォールバック）

ストップロス、テイクプロフィット、緊急決済、クールダウン管理を統合。
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...core.config import get_threshold
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient
from ..core import ExecutionMode, ExecutionResult, OrderStatus, TradeEvaluation
from .tp_sl_config import TPSLConfig


class StopManager:
    """
    ストップ条件管理サービス

    TP/SL、緊急決済、残注文クリーンアップなどのストップ条件を管理する。
    """

    def __init__(self):
        """StopManager初期化"""
        self.logger = get_logger()

    # ========================================
    # Phase 61.9: TP/SL自動執行検知機能
    # ========================================

    async def detect_auto_executed_orders(
        self,
        virtual_positions: List[Dict[str, Any]],
        actual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
        symbol: str = "BTC/JPY",
    ) -> List[Dict[str, Any]]:
        """
        Phase 61.9: TP/SL自動執行検知

        bitbankがTP/SL注文を自動執行した際に、その約定を検知・記録する。

        処理フロー:
        1. virtual_positionsと実ポジションを照合し消失検出
        2. 消失ポジションのtp_order_id/sl_order_idをfetch_order()で確認
        3. status="closed"ならTP/SL約定と判定
        4. ログ出力・残注文キャンセル

        Args:
            virtual_positions: 仮想ポジションリスト
            actual_positions: 実ポジションリスト（bitbank API取得済み）
            bitbank_client: BitbankClientインスタンス
            symbol: 通貨ペア

        Returns:
            検知された自動執行リスト
        """
        # 設定取得
        config = get_threshold(TPSLConfig.AUTO_DETECTION, {})
        if not config.get("enabled", True):
            return []

        detected_executions = []

        try:
            # Step 1: 消失ポジション検出
            disappeared = self._find_disappeared_positions(virtual_positions, actual_positions)

            if not disappeared:
                self.logger.debug("📊 Phase 61.9: 消失ポジションなし")
                return []

            self.logger.info(f"🔍 Phase 61.9: 消失ポジション検出 - {len(disappeared)}件")

            # Step 2: 各消失ポジションのTP/SL注文ステータス確認
            for vpos in disappeared:
                execution_info = await self._check_tp_sl_execution(vpos, bitbank_client, symbol)

                if execution_info:
                    detected_executions.append(execution_info)

                    # ログ出力
                    self._log_auto_execution(execution_info, config)

                    # 残注文キャンセル
                    await self._cancel_remaining_order(execution_info, bitbank_client, symbol)

            return detected_executions

        except Exception as e:
            self.logger.warning(f"⚠️ Phase 61.9: 自動執行検知エラー: {e}")
            return []

    def _find_disappeared_positions(
        self,
        virtual_positions: List[Dict[str, Any]],
        actual_positions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Phase 61.9: 消失ポジション検出

        virtual_positionsにあるが、actual_positionsにないポジションを検出する。

        Args:
            virtual_positions: 仮想ポジションリスト
            actual_positions: 実ポジションリスト

        Returns:
            消失ポジションリスト
        """
        disappeared = []

        for vpos in virtual_positions:
            # TP/SL注文IDを持つポジションのみ対象
            if not vpos.get("tp_order_id") and not vpos.get("sl_order_id"):
                continue

            vside = vpos.get("side", "").lower()
            vamt = float(vpos.get("amount", 0))

            if vamt <= 0:
                continue

            # 実ポジションとマッチング
            matched = False
            for apos in actual_positions:
                # actual_positionsはfetch_margin_positions()の結果
                # side: "long" or "short"
                apos_side = apos.get("side", "")
                # long -> buy, short -> sell に変換
                if apos_side == "long":
                    aside = "buy"
                elif apos_side == "short":
                    aside = "sell"
                else:
                    aside = apos_side.lower()

                aamt = float(apos.get("amount", 0))

                # Phase 63: Bug 5修正 - サイド一致かつ実ポジション存在でマッチ
                # ポジション集約時に個別数量と集約量が異なるため、
                # サイド一致のみでマッチング
                if aside == vside and aamt > 0:
                    matched = True
                    break

            if not matched:
                disappeared.append(vpos)

        return disappeared

    async def _check_tp_sl_execution(
        self,
        vpos: Dict[str, Any],
        bitbank_client: BitbankClient,
        symbol: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 61.9: TP/SL注文のステータス確認

        消失ポジションのTP/SL注文を確認し、約定情報を取得する。

        Args:
            vpos: 消失した仮想ポジション
            bitbank_client: BitbankClientインスタンス
            symbol: 通貨ペア

        Returns:
            約定情報（TP/SL約定なしの場合はNone）
        """
        tp_order_id = vpos.get("tp_order_id")
        sl_order_id = vpos.get("sl_order_id")
        entry_price = float(vpos.get("price", 0))
        amount = float(vpos.get("amount", 0))
        side = vpos.get("side", "")

        execution_type = None
        exit_price = None
        executed_order_id = None
        remaining_order_id = None

        # TP注文確認
        if tp_order_id:
            try:
                tp_order = await asyncio.to_thread(bitbank_client.fetch_order, tp_order_id, symbol)
                if tp_order.get("status") == "closed":
                    execution_type = "take_profit"
                    exit_price = float(tp_order.get("average", tp_order.get("price", 0)))
                    executed_order_id = tp_order_id
                    remaining_order_id = sl_order_id
            except Exception as e:
                self.logger.debug(f"📊 Phase 61.9: TP注文確認エラー（許容）: {e}")

        # SL注文確認（TPが約定していない場合）
        if not execution_type and sl_order_id:
            try:
                sl_order = await asyncio.to_thread(bitbank_client.fetch_order, sl_order_id, symbol)
                if sl_order.get("status") == "closed":
                    execution_type = "stop_loss"
                    exit_price = float(sl_order.get("average", sl_order.get("price", 0)))
                    executed_order_id = sl_order_id
                    remaining_order_id = tp_order_id
            except Exception as e:
                self.logger.debug(f"📊 Phase 61.9: SL注文確認エラー（許容）: {e}")

        if not execution_type:
            return None

        # 損益計算
        pnl = self._calc_pnl(entry_price, exit_price, amount, side)

        return {
            "execution_type": execution_type,
            "order_id": vpos.get("order_id"),
            "tp_order_id": tp_order_id,
            "sl_order_id": sl_order_id,
            "executed_order_id": executed_order_id,
            "remaining_order_id": remaining_order_id,
            "side": side,
            "amount": amount,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "strategy_name": vpos.get("strategy_name", "unknown"),
            "timestamp": datetime.now(),
        }

    def _calc_pnl(
        self,
        entry_price: float,
        exit_price: float,
        amount: float,
        side: str,
    ) -> float:
        """
        Phase 62.19: 手数料考慮した実現損益計算

        bitbank手数料（2026年2月2日改定）:
          - エントリー/TP決済: Maker 0%（post_only約定時）
          - SL決済: Taker 0.1%（post_only非対応）

        計算式:
          粗利益 = (決済価格 - エントリー価格) × 数量  ※ロングの場合
          エントリー手数料 = エントリー約定金額 × Taker手数料率
          決済手数料 = 決済約定金額 × Taker手数料率
          実現損益 = 粗利益 - エントリー手数料 - 決済手数料

        Args:
            entry_price: エントリー価格
            exit_price: 決済価格
            amount: 数量
            side: エントリーサイド（buy/sell）

        Returns:
            実現損益（円）※手数料差引後
        """
        if entry_price <= 0 or exit_price <= 0 or amount <= 0:
            return 0.0

        # 粗利益計算
        if side.lower() == "buy":
            # ロング: 価格上昇で利益
            gross_pnl = (exit_price - entry_price) * amount
        else:
            # ショート: 価格下落で利益
            gross_pnl = (entry_price - exit_price) * amount

        # Phase 62.19: 手数料計算（SL約定はTaker扱い）
        entry_fee_rate = get_threshold(TPSLConfig.ENTRY_TAKER_RATE, 0.001)
        exit_fee_rate = get_threshold(TPSLConfig.EXIT_TAKER_RATE, 0.001)

        entry_notional = entry_price * amount  # エントリー約定金額
        exit_notional = exit_price * amount  # 決済約定金額

        entry_fee = entry_notional * entry_fee_rate
        exit_fee = exit_notional * exit_fee_rate

        # 実現損益 = 粗利益 - 手数料
        net_pnl = gross_pnl - entry_fee - exit_fee

        self.logger.debug(
            f"📊 Phase 62.6: 損益計算 - 粗利益={gross_pnl:.0f}円, "
            f"エントリー手数料={entry_fee:.2f}円, 決済手数料={exit_fee:.2f}円, "
            f"実現損益={net_pnl:.0f}円"
        )

        return net_pnl

    def _log_auto_execution(
        self,
        execution_info: Dict[str, Any],
        config: Dict[str, Any],
    ) -> None:
        """
        Phase 61.9: 自動執行のログ出力

        Args:
            execution_info: 約定情報
            config: 設定
        """
        exec_type = execution_info["execution_type"]
        side = execution_info["side"]
        amount = execution_info["amount"]
        exit_price = execution_info["exit_price"]
        pnl = execution_info["pnl"]
        strategy = execution_info["strategy_name"]

        if exec_type == "take_profit":
            pnl_str = f"利益: +{pnl:.0f}円" if pnl > 0 else f"損益: {pnl:.0f}円"
            log_msg = (
                f"🎯 Phase 61.9: TP自動執行検知 - "
                f"{side.upper()} {amount:.6f} BTC @ {exit_price:.0f}円 "
                f"({pnl_str}) 戦略: {strategy}"
            )
            self.logger.info(log_msg)
        else:  # stop_loss
            pnl_str = f"損失: {pnl:.0f}円" if pnl < 0 else f"損益: +{pnl:.0f}円"
            log_msg = (
                f"🛑 Phase 61.9: SL自動執行検知 - "
                f"{side.upper()} {amount:.6f} BTC @ {exit_price:.0f}円 "
                f"({pnl_str}) 戦略: {strategy}"
            )
            self.logger.warning(log_msg)

    async def _cancel_remaining_order(
        self,
        execution_info: Dict[str, Any],
        bitbank_client: BitbankClient,
        symbol: str,
    ) -> None:
        """
        Phase 61.9: 残注文キャンセル

        TP約定時は残SLをキャンセル、SL約定時は残TPをキャンセル

        Args:
            execution_info: 約定情報
            bitbank_client: BitbankClientインスタンス
            symbol: 通貨ペア
        """
        remaining_order_id = execution_info.get("remaining_order_id")
        if not remaining_order_id:
            return

        exec_type = execution_info["execution_type"]
        remaining_type = "SL" if exec_type == "take_profit" else "TP"

        try:
            await asyncio.to_thread(bitbank_client.cancel_order, remaining_order_id, symbol)
            self.logger.info(
                f"✅ Phase 61.9: 残{remaining_type}注文キャンセル成功 - "
                f"ID: {remaining_order_id}"
            )
        except Exception as e:
            error_str = str(e)
            # OrderNotFoundは許容（既にキャンセル/約定済み）
            if "OrderNotFound" in error_str or "not found" in error_str.lower():
                self.logger.debug(
                    f"ℹ️ Phase 61.9: 残{remaining_type}注文は既にキャンセル/約定済み - "
                    f"ID: {remaining_order_id}"
                )
            else:
                self.logger.warning(
                    f"⚠️ Phase 61.9: 残{remaining_type}注文キャンセル失敗 - "
                    f"ID: {remaining_order_id}, エラー: {e}"
                )

    async def _wait_for_fill(
        self,
        order_id: str,
        bitbank_client: BitbankClient,
        symbol: str = "BTC/JPY",
        timeout_seconds: int = 30,
        check_interval: int = 3,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Phase 61.3: 決済注文の約定を待機

        決済注文発行後、約定するまで待機する。
        タイムアウトした場合は未約定として返す。

        Args:
            order_id: 確認対象の注文ID
            bitbank_client: BitbankClientインスタンス
            symbol: 通貨ペア
            timeout_seconds: タイムアウト秒数（デフォルト30秒）
            check_interval: 確認間隔秒数（デフォルト3秒）

        Returns:
            Tuple[bool, Optional[Dict]]:
                - bool: 約定完了ならTrue、未約定ならFalse
                - Dict: 注文情報（約定時）またはNone
        """
        max_checks = timeout_seconds // check_interval

        self.logger.info(
            f"🔄 Phase 61.3: 約定確認開始 - order_id={order_id}, "
            f"timeout={timeout_seconds}秒, interval={check_interval}秒"
        )

        for i in range(max_checks):
            try:
                order = await asyncio.to_thread(bitbank_client.fetch_order, order_id, symbol)
                status = order.get("status", "")

                self.logger.debug(
                    f"📊 Phase 61.3: 約定確認中 ({i + 1}/{max_checks}) - "
                    f"order_id={order_id}, status={status}"
                )

                if status == "closed":  # ccxtでは"closed"が約定済み
                    self.logger.info(
                        f"✅ Phase 61.3: 約定確認完了 - order_id={order_id}, "
                        f"filled={order.get('filled', 0):.6f} BTC"
                    )
                    return True, order
                elif status == "canceled":
                    self.logger.warning(f"⚠️ Phase 61.3: 注文キャンセル検出 - order_id={order_id}")
                    return False, order
                elif status == "expired":
                    self.logger.warning(f"⚠️ Phase 61.3: 注文期限切れ検出 - order_id={order_id}")
                    return False, order

                # まだオープン状態、次の確認まで待機
                await asyncio.sleep(check_interval)

            except Exception as e:
                self.logger.warning(f"⚠️ Phase 61.3: 約定確認エラー ({i + 1}/{max_checks}): {e}")
                await asyncio.sleep(check_interval)

        # タイムアウト
        self.logger.warning(
            f"⏰ Phase 61.3: 約定確認タイムアウト - order_id={order_id}, "
            f"{timeout_seconds}秒経過"
        )
        return False, None

    async def _retry_close_order_with_price_update(
        self,
        bitbank_client: BitbankClient,
        symbol: str,
        exit_side: str,
        amount: float,
        entry_position_side: str,
        original_order_id: str,
        max_retries: int = 3,
        slippage_increase_per_retry: float = 0.001,
    ) -> Tuple[bool, Optional[str]]:
        """
        Phase 61.3: 決済注文リトライ（価格更新付き）

        未約定の決済注文をキャンセルし、より有利な価格で再注文する。

        Args:
            bitbank_client: BitbankClientインスタンス
            symbol: 通貨ペア
            exit_side: 決済方向（"buy" / "sell"）
            amount: 決済数量
            entry_position_side: エントリー時のposition_side
            original_order_id: 元の注文ID（キャンセル用）
            max_retries: 最大リトライ回数
            slippage_increase_per_retry: リトライ毎のスリッページ増加量

        Returns:
            Tuple[bool, Optional[str]]:
                - bool: 約定成功ならTrue
                - str: 約定した注文ID（成功時）またはNone
        """
        for retry in range(max_retries):
            try:
                # 元の注文をキャンセル
                try:
                    await asyncio.to_thread(bitbank_client.cancel_order, original_order_id, symbol)
                    self.logger.info(
                        f"🔄 Phase 61.3: 未約定注文キャンセル成功 - "
                        f"order_id={original_order_id}"
                    )
                except Exception as cancel_error:
                    # キャンセル失敗（既に約定/キャンセル済み）は許容
                    self.logger.debug(f"ℹ️ Phase 61.3: 注文キャンセル失敗（許容）: {cancel_error}")

                # 現在価格を取得
                ticker = await asyncio.to_thread(bitbank_client.fetch_ticker, symbol)
                current_price = float(ticker.get("last", 0))

                if current_price <= 0:
                    self.logger.warning(f"⚠️ Phase 61.3: 現在価格取得失敗 - リトライスキップ")
                    continue

                # スリッページを加味した価格計算
                slippage = slippage_increase_per_retry * (retry + 1)
                if exit_side.lower() == "sell":
                    # 売り決済: 少し安い価格で約定しやすく
                    new_price = current_price * (1 - slippage)
                else:
                    # 買い決済: 少し高い価格で約定しやすく
                    new_price = current_price * (1 + slippage)

                self.logger.info(
                    f"🔄 Phase 61.3: リトライ {retry + 1}/{max_retries} - "
                    f"新価格={new_price:.0f}円 (slippage={slippage * 100:.2f}%)"
                )

                # 新しい決済注文を発行
                new_order = await asyncio.to_thread(
                    bitbank_client.create_order,
                    symbol=symbol,
                    side=exit_side,
                    order_type="limit",
                    price=new_price,
                    amount=amount,
                    is_closing_order=True,
                    entry_position_side=entry_position_side,
                )
                new_order_id = new_order.get("id")

                if not new_order_id:
                    self.logger.warning(f"⚠️ Phase 61.3: リトライ注文ID取得失敗")
                    continue

                # 約定確認
                fill_config = get_threshold(TPSLConfig.SL_FILL_CONFIRMATION, {})
                timeout = fill_config.get("timeout_seconds", 30)
                interval = fill_config.get("check_interval_seconds", 3)

                is_filled, _ = await self._wait_for_fill(
                    new_order_id, bitbank_client, symbol, timeout, interval
                )

                if is_filled:
                    self.logger.info(
                        f"✅ Phase 61.3: リトライ約定成功 - " f"order_id={new_order_id}"
                    )
                    return True, new_order_id

                # 次のリトライのために注文IDを更新
                original_order_id = new_order_id

            except Exception as e:
                self.logger.error(f"❌ Phase 61.3: リトライエラー ({retry + 1}/{max_retries}): {e}")

        self.logger.error(f"❌ Phase 61.3: 全{max_retries}回リトライ失敗 - 手動決済が必要")
        return False, None

    async def check_stop_conditions(
        self,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: Optional[BitbankClient],
        mode: str,
        executed_trades: int,
        session_pnl: float,
    ) -> Optional[ExecutionResult]:
        """
        ストップ条件チェック（Phase 28: テイクプロフィット/ストップロス実装）

        Args:
            virtual_positions: 保有ポジションリスト
            bitbank_client: BitbankClientインスタンス
            mode: 実行モード
            executed_trades: 実行済み取引数
            session_pnl: セッションP&L

        Returns:
            ExecutionResult: ストップ実行結果（実行しない場合はNone）
        """
        try:
            # Phase 51.8-J4-D再修正: バックテストモードでは決済処理をスキップ
            # backtest_runner.py の _check_tp_sl_triggers() が唯一の決済ルート（証拠金返還含む）
            # stop_manager.py で重複決済すると証拠金が返還されず残高が減る問題を回避
            if mode == "backtest":
                return None

            # ポジションがない場合は何もしない
            if not virtual_positions:
                return None

            # 現在価格取得
            current_price = await self._get_current_price(bitbank_client)
            if current_price <= 0:
                self.logger.warning("⚠️ 現在価格取得失敗、ストップ条件チェックスキップ")
                return None

            # Phase 28: 通常のテイクプロフィット/ストップロスチェック
            # Phase 49.6: bitbank_clientを渡してクリーンアップ対応
            tp_sl_result = await self._check_take_profit_stop_loss(
                current_price, virtual_positions, mode, executed_trades, session_pnl, bitbank_client
            )
            if tp_sl_result:
                return tp_sl_result

            # 緊急ストップロス条件チェック（既存機能維持）
            emergency_result = await self._check_emergency_stop_loss(
                virtual_positions, current_price, mode, executed_trades, session_pnl
            )
            if emergency_result:
                return emergency_result

            # Phase 51.6: Phase 50.5コメントアウトコード削除
            # Phase 37.5.3クリーンアップ機能は、virtual_positionsにsl_order_id保存必須のため
            # 現時点で安全に動作するまで無効化維持（Phase 49.6で個別クリーンアップ実装済み）

            return None

        except Exception as e:
            self.logger.error(f"❌ ストップ条件チェックエラー: {e}")
            return None

    async def _check_take_profit_stop_loss(
        self,
        current_price: float,
        virtual_positions: List[Dict[str, Any]],
        mode: str,
        executed_trades: int,
        session_pnl: float,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> Optional[ExecutionResult]:
        """
        Phase 28: 通常のテイクプロフィット/ストップロスチェック

        Args:
            current_price: 現在のBTC価格
            virtual_positions: ポジションリスト
            mode: 実行モード
            executed_trades: 実行済み取引数
            session_pnl: セッションP&L

        Returns:
            ExecutionResult: 決済実行結果（実行しない場合はNone）
        """
        try:
            # 設定取得
            tp_config = get_threshold(TPSLConfig.TP_CONFIG, {})
            sl_config = get_threshold(TPSLConfig.SL_CONFIG, {})

            if not tp_config.get("enabled", True) and not sl_config.get("enabled", True):
                return None

            # Phase 58.1: 全ポジションのTP/SLチェック（単一決済パターン修正）
            # 価格急変時に複数ポジションが同時にTP/SL到達した場合、全て処理する
            positions_to_remove = []
            first_result = None

            for position in list(virtual_positions):  # コピーでイテレート（削除安全）
                exit_result = await self._evaluate_position_exit(
                    position, current_price, tp_config, sl_config, mode, bitbank_client
                )
                if exit_result:
                    positions_to_remove.append(position)
                    # 統計更新（P&L計算）
                    if hasattr(exit_result, "paper_pnl") and exit_result.paper_pnl:
                        session_pnl += exit_result.paper_pnl
                    # 最初の結果を保持（戻り値用）
                    if first_result is None:
                        first_result = exit_result

            # Phase 58.1: まとめて削除（イテレーション終了後）
            for pos in positions_to_remove:
                if pos in virtual_positions:
                    virtual_positions.remove(pos)

            if positions_to_remove:
                self.logger.info(f"🔄 Phase 58.1: {len(positions_to_remove)}件のポジション決済完了")

            return first_result

        except Exception as e:
            self.logger.error(f"❌ テイクプロフィット/ストップロスチェックエラー: {e}")
            return None

    async def _evaluate_position_exit(
        self,
        position: dict,
        current_price: float,
        tp_config: dict,
        sl_config: dict,
        mode: str,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> Optional[ExecutionResult]:
        """
        個別ポジションの決済判定

        Phase 62.17: stop_limit配置済みの場合はBot側SL監視をスキップ
        （bitbankのstop_limitトリガーに任せる）

        Args:
            position: ポジション情報
            current_price: 現在価格
            tp_config: テイクプロフィット設定
            sl_config: ストップロス設定
            mode: 実行モード

        Returns:
            ExecutionResult: 決済結果（決済しない場合はNone）
        """
        try:
            # Phase 53.11: None値の防御的処理
            raw_price = position.get("price")
            raw_amount = position.get("amount")
            entry_side = position.get("side", "")

            if raw_price is None or raw_amount is None:
                self.logger.debug(
                    f"⏭️ Phase 53.11: 不完全ポジションスキップ - "
                    f"price={raw_price}, amount={raw_amount}"
                )
                return None

            entry_price = float(raw_price)
            amount = float(raw_amount)
            take_profit = position.get("take_profit")
            stop_loss = position.get("stop_loss")

            if entry_price <= 0 or amount <= 0:
                return None

            # テイクプロフィットチェック
            if tp_config.get("enabled", True) and take_profit:
                tp_triggered = False
                if entry_side.lower() == "buy" and current_price >= float(take_profit):
                    tp_triggered = True
                elif entry_side.lower() == "sell" and current_price <= float(take_profit):
                    tp_triggered = True

                if tp_triggered:
                    self.logger.info(
                        f"🎯 テイクプロフィット到達! {entry_side} {amount} BTC @ {current_price:.0f}円 (TP:{take_profit:.0f}円)"
                    )
                    # Phase 49.6: bitbank_clientを渡してクリーンアップ実行
                    return await self._execute_position_exit(
                        position, current_price, "take_profit", mode, bitbank_client
                    )

            # ========================================
            # Phase 62.17: stop_limit配置済み時のBot側SL監視スキップ
            # ========================================
            # stop_limit注文が配置済みの場合、Bot側のSL監視をスキップし
            # bitbankのstop_limitトリガーに任せる（二重決済防止）
            # ========================================
            if sl_config.get("enabled", True) and stop_loss:
                # Phase 62.17: stop_limit配置済みかチェック
                skip_bot_sl_monitoring = self._should_skip_bot_sl_monitoring(position, sl_config)

                if skip_bot_sl_monitoring:
                    # タイムアウトチェック（stop_limitが長時間未約定の場合のフォールバック）
                    timeout_result = await self._check_stop_limit_timeout(
                        position, current_price, sl_config, mode, bitbank_client
                    )
                    if timeout_result:
                        return timeout_result
                    # タイムアウトしていない場合は、bitbankのstop_limitトリガー待機
                    return None

                # 従来のBot側SLチェック（stop_limit未配置 or stop_limit以外の場合）
                sl_triggered = False
                if entry_side.lower() == "buy" and current_price <= float(stop_loss):
                    sl_triggered = True
                elif entry_side.lower() == "sell" and current_price >= float(stop_loss):
                    sl_triggered = True

                if sl_triggered:
                    self.logger.warning(
                        f"🛑 ストップロス到達! {entry_side} {amount} BTC @ {current_price:.0f}円 (SL:{stop_loss:.0f}円)"
                    )
                    # Phase 49.6: bitbank_clientを渡してクリーンアップ実行
                    return await self._execute_position_exit(
                        position, current_price, "stop_loss", mode, bitbank_client
                    )

            return None

        except Exception as e:
            self.logger.error(f"❌ ポジション決済判定エラー: {e}")
            return None

    def _should_skip_bot_sl_monitoring(
        self,
        position: dict,
        sl_config: dict,
    ) -> bool:
        """
        Phase 62.17: Bot側SL監視をスキップすべきか判定

        stop_limit注文が配置済みで、skip_bot_monitoringが有効な場合は
        Bot側のSL監視をスキップし、bitbankのトリガーに任せる。

        Args:
            position: ポジション情報
            sl_config: SL設定

        Returns:
            bool: スキップすべき場合はTrue
        """
        # skip_bot_monitoringが無効な場合はスキップしない
        if not sl_config.get("skip_bot_monitoring", True):
            return False

        # SL注文IDが存在しない場合はスキップしない
        sl_order_id = position.get("sl_order_id")
        if not sl_order_id:
            return False

        # order_typeがstop_limit以外の場合はスキップしない
        order_type = sl_config.get("order_type", "stop")
        if order_type != "stop_limit":
            return False

        self.logger.debug(
            f"📊 Phase 62.17: stop_limit配置済み - Bot側SL監視スキップ "
            f"(sl_order_id={sl_order_id})"
        )
        return True

    async def _check_stop_limit_timeout(
        self,
        position: dict,
        current_price: float,
        sl_config: dict,
        mode: str,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> Optional[ExecutionResult]:
        """
        Phase 62.17: stop_limitタイムアウトチェック

        stop_limit注文が配置後、一定時間経過しても約定しない場合、
        成行でフォールバック決済を行う。

        Args:
            position: ポジション情報
            current_price: 現在価格
            sl_config: SL設定
            mode: 実行モード
            bitbank_client: BitbankClientインスタンス

        Returns:
            ExecutionResult: タイムアウト時の決済結果（タイムアウトしていない場合はNone）
        """
        # SL配置時刻を取得
        sl_placed_at = position.get("sl_placed_at")
        if not sl_placed_at:
            # 配置時刻が記録されていない場合はタイムアウトチェックスキップ
            return None

        # タイムアウト秒数を取得
        timeout_seconds = sl_config.get("stop_limit_timeout", 300)  # デフォルト5分

        # 経過時間を計算
        if isinstance(sl_placed_at, str):
            sl_placed_at = datetime.fromisoformat(sl_placed_at.replace("Z", "+00:00"))
        elif not isinstance(sl_placed_at, datetime):
            return None

        # タイムゾーン対応
        now = datetime.now(timezone.utc)
        if sl_placed_at.tzinfo is None:
            sl_placed_at = sl_placed_at.replace(tzinfo=timezone.utc)

        elapsed_seconds = (now - sl_placed_at).total_seconds()

        if elapsed_seconds < timeout_seconds:
            # タイムアウトしていない
            return None

        # Phase 63: Bug 4修正 - タイムアウト前にSL注文の存在を確認
        # SLが既に約定済み/キャンセル済みの場合はフォールバック不要
        sl_order_id = position.get("sl_order_id")
        if sl_order_id and bitbank_client:
            try:
                symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")
                sl_order_status = await asyncio.to_thread(
                    bitbank_client.fetch_order, sl_order_id, symbol
                )
                order_status = sl_order_status.get("status", "")
                if order_status in ("closed", "canceled", "cancelled"):
                    self.logger.info(
                        f"📊 Phase 63: SL注文 {sl_order_id} は既に{order_status} - フォールバック不要"
                    )
                    return None
                elif order_status == "open":
                    self.logger.info(
                        f"📊 Phase 63: SL注文 {sl_order_id} はまだアクティブ - "
                        f"bitbankトリガー待機継続（フォールバックスキップ）"
                    )
                    return None
                else:
                    # Phase 64.9: 不明ステータスでも安全側（フォールバックしない）
                    self.logger.warning(
                        f"⚠️ Phase 64.9: SL注文 {sl_order_id} 不明ステータス: '{order_status}' "
                        f"- 安全側でフォールバックスキップ"
                    )
                    return None
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 63: SL注文確認エラー: {e} - フォールバックスキップ")
                return None  # API一時エラー時は安全側（フォールバックしない）

        # Phase 64.9: sl_order_id未設定の場合のみフォールバック実行
        if not sl_order_id:
            self.logger.warning(
                f"⚠️ Phase 64.9: sl_order_idが未設定 - タイムアウトフォールバック実行"
            )

        # タイムアウト発生 - フォールバック決済（SL注文が確認できない場合のみ）
        entry_side = position.get("side", "")
        amount = float(position.get("amount", 0))
        stop_loss = position.get("stop_loss")

        # Phase 63.4: 価格安全チェック - SLゾーン外なら実行しない
        if stop_loss and current_price > 0:
            sl_price = float(stop_loss)
            if entry_side.lower() == "buy":
                # ロング: 現在価格がSL+1.5%以上なら、SL発動は不合理
                if current_price > sl_price * TPSLConfig.SL_SAFETY_MARGIN_BUY:
                    self.logger.warning(
                        f"⚠️ Phase 63.4: SLタイムアウト中止 - "
                        f"現在価格({current_price:.0f})がSL({sl_price:.0f})より"
                        f"大幅に高い。bitbankトリガー待機継続。"
                    )
                    return None
            elif entry_side.lower() == "sell":
                # ショート: 現在価格がSL-1.5%以下なら不合理
                if current_price < sl_price * TPSLConfig.SL_SAFETY_MARGIN_SELL:
                    self.logger.warning(
                        f"⚠️ Phase 63.4: SLタイムアウト中止 - "
                        f"現在価格({current_price:.0f})がSL({sl_price:.0f})より"
                        f"大幅に低い。bitbankトリガー待機継続。"
                    )
                    return None

        self.logger.warning(
            f"⚠️ Phase 63: stop_limitタイムアウト ({elapsed_seconds:.0f}秒経過) - "
            f"SL注文確認不可のため成行フォールバック実行 "
            f"({entry_side} {amount:.6f} BTC, SL: {stop_loss:.0f}円, 現在: {current_price:.0f}円)"
        )

        # 成行でフォールバック決済
        result = await self._execute_position_exit(
            position, current_price, "stop_loss_timeout", mode, bitbank_client
        )

        # Phase 62.21: 決済失敗時は警告ログ出力（10分後のTP/SL検証で再構築される）
        if not result.success:
            self.logger.warning(
                f"⚠️ Phase 62.21: タイムアウト決済失敗 - " f"10分後のTP/SL検証でSL再設置される予定"
            )

        return result

    async def _execute_position_exit(
        self,
        position: dict,
        current_price: float,
        exit_reason: str,
        mode: str,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> ExecutionResult:
        """
        ポジション決済実行

        Args:
            position: ポジション情報
            current_price: 決済価格
            exit_reason: 決済理由 ("take_profit", "stop_loss", "emergency")
            mode: 実行モード
            bitbank_client: BitbankClientインスタンス（Phase 49.6: クリーンアップ用）

        Returns:
            ExecutionResult: 決済実行結果
        """
        try:
            entry_side = position.get("side", "")
            amount = float(position.get("amount", 0))
            entry_price = float(position.get("price", 0))

            # 決済注文は反対売買
            exit_side = "sell" if entry_side.lower() == "buy" else "buy"

            # 損益計算
            if entry_side.lower() == "buy":
                pnl = (current_price - entry_price) * amount
            else:
                pnl = (entry_price - current_price) * amount

            # Phase 49.6: ポジション決済時にTP/SL注文クリーンアップ
            if bitbank_client and mode == "live":
                tp_order_id = position.get("tp_order_id")
                sl_order_id = position.get("sl_order_id")

                if tp_order_id or sl_order_id:
                    try:
                        symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")
                        cleanup_result = await self.cleanup_position_orders(
                            tp_order_id=tp_order_id,
                            sl_order_id=sl_order_id,
                            symbol=symbol,
                            bitbank_client=bitbank_client,
                            reason=exit_reason,
                        )
                        if cleanup_result["cancelled_count"] > 0:
                            self.logger.info(
                                f"🧹 Phase 49.6: ポジション決済時クリーンアップ実行 - "
                                f"{cleanup_result['cancelled_count']}件キャンセル"
                            )
                    except Exception as e:
                        # Phase 59.6: クリーンアップエラーは処理継続（孤児SLは別途記録済み）
                        self.logger.warning(f"⚠️ Phase 59.6: クリーンアップエラー（処理継続）: {e}")

                # Phase 58.1: 実際の決済注文をbitbankに発行
                # Phase 60: 指値化（手数料削減 0.12%→0.02%）
                # Phase 61.3: 約定確認・リトライ機能追加
                try:
                    entry_position_side = "long" if entry_side.lower() == "buy" else "short"
                    symbol = "BTC/JPY"

                    close_order = await asyncio.to_thread(
                        bitbank_client.create_order,
                        symbol=symbol,
                        side=exit_side,
                        order_type="limit",
                        price=current_price,
                        amount=amount,
                        is_closing_order=True,
                        entry_position_side=entry_position_side,
                    )
                    close_order_id = close_order.get("id", "unknown")
                    self.logger.info(
                        f"✅ Phase 58.1: bitbank決済注文発行成功 - "
                        f"ID: {close_order_id}, {exit_side} {amount:.6f} BTC"
                    )

                    # Phase 61.3: 約定確認（設定で有効化時のみ）
                    fill_config = get_threshold(
                        "position_management.stop_loss.fill_confirmation", {}
                    )
                    if fill_config.get("enabled", False):
                        timeout = fill_config.get("timeout_seconds", 30)
                        interval = fill_config.get("check_interval_seconds", 3)

                        is_filled, _ = await self._wait_for_fill(
                            close_order_id, bitbank_client, symbol, timeout, interval
                        )

                        if not is_filled:
                            # 未約定の場合、リトライ設定を確認
                            retry_config = get_threshold(TPSLConfig.SL_RETRY_UNFILLED, {})
                            if retry_config.get("enabled", False):
                                max_retries = retry_config.get("max_retries", 3)
                                slippage_inc = retry_config.get(
                                    "slippage_increase_per_retry", 0.001
                                )

                                self.logger.warning(
                                    f"⚠️ Phase 61.3: 決済注文未約定 - リトライ開始 "
                                    f"(max_retries={max_retries})"
                                )

                                (
                                    retry_success,
                                    retry_order_id,
                                ) = await self._retry_close_order_with_price_update(
                                    bitbank_client=bitbank_client,
                                    symbol=symbol,
                                    exit_side=exit_side,
                                    amount=amount,
                                    entry_position_side=entry_position_side,
                                    original_order_id=close_order_id,
                                    max_retries=max_retries,
                                    slippage_increase_per_retry=slippage_inc,
                                )

                                if retry_success:
                                    self.logger.info(
                                        f"✅ Phase 61.3: リトライ約定成功 - "
                                        f"ID: {retry_order_id}"
                                    )
                                else:
                                    self.logger.error(
                                        f"❌ Phase 61.3: リトライ失敗 - "
                                        f"手動決済が必要な可能性があります"
                                    )
                            else:
                                self.logger.warning(
                                    f"⚠️ Phase 61.3: 決済注文未約定 - "
                                    f"リトライ無効（手動確認推奨）"
                                )
                        else:
                            self.logger.info(
                                f"✅ Phase 61.3: 決済注文約定確認完了 - " f"ID: {close_order_id}"
                            )

                except Exception as e:
                    error_message = str(e)
                    self.logger.error(
                        f"❌ Phase 58.1: bitbank決済注文発行失敗: {error_message} - "
                        f"手動決済が必要な可能性があります"
                    )

                    # Phase 62.21: エラー50062の場合、ポジション存在確認の可能性を示唆
                    if "50062" in error_message:
                        self.logger.info(
                            "ℹ️ Phase 62.21: エラー50062 - "
                            "ポジションが既に決済済み（TP約定等）の可能性あり"
                        )

                    # Phase 62.21: 決済失敗時はsuccess=Falseで返す（バグ修正）
                    return ExecutionResult(
                        success=False,
                        mode=ExecutionMode.PAPER if mode == "paper" else ExecutionMode.LIVE,
                        order_id=f"exit_error_{position.get('order_id', 'unknown')}",
                        price=current_price,
                        amount=0,
                        filled_price=0,
                        filled_amount=0,
                        error_message=error_message,
                        side=exit_side,
                        fee=0.0,
                        status=OrderStatus.FAILED,
                        paper_pnl=0,
                        timestamp=datetime.now(),
                    )

            # ExecutionResult作成
            result = ExecutionResult(
                success=True,
                mode=ExecutionMode.PAPER if mode == "paper" else ExecutionMode.LIVE,
                order_id=f"exit_{position.get('order_id', 'unknown')}",
                price=current_price,
                amount=amount,
                filled_price=current_price,
                filled_amount=amount,
                error_message=None,
                side=exit_side,
                fee=0.0,  # ペーパーは手数料なし
                status=OrderStatus.FILLED,
                paper_pnl=pnl,  # 損益をpaper_pnlフィールドに保存
                timestamp=datetime.now(),
            )

            # ログ出力（Phase 62.17: 決済理由の詳細化）
            pnl_status = "利益" if pnl > 0 else "損失"
            exit_reason_display = {
                "take_profit": "TP到達",
                "stop_loss": "SL到達",
                "stop_loss_timeout": "SLタイムアウト",
                "emergency": "緊急決済",
            }.get(exit_reason, exit_reason)

            self.logger.info(
                f"🔄 ポジション決済完了: {exit_side} {amount:.6f} BTC @ {current_price:.0f}円 "
                f"(理由: {exit_reason_display}, エントリー: {entry_price:.0f}円) "
                f"{pnl_status}:{pnl:+.0f}円"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ ポジション決済実行エラー: {e}")
            # エラーの場合は失敗結果を返す
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.PAPER if mode == "paper" else ExecutionMode.LIVE,
                order_id=f"exit_error_{position.get('order_id', 'unknown')}",
                price=current_price,
                amount=0,
                filled_price=0,
                filled_amount=0,
                error_message=str(e),
                side="unknown",
                fee=0.0,
                status=OrderStatus.FAILED,
            )

    async def _check_emergency_stop_loss(
        self,
        virtual_positions: List[Dict[str, Any]],
        current_price: float,
        mode: str,
        executed_trades: int,
        session_pnl: float,
    ) -> Optional[ExecutionResult]:
        """
        緊急ストップロス条件チェック（急変時例外処理）

        30分のクールダウン制限を無視して、市場急変時に緊急決済を実行

        Args:
            virtual_positions: ポジションリスト
            current_price: 現在価格
            mode: 実行モード
            executed_trades: 実行済み取引数
            session_pnl: セッションP&L

        Returns:
            ExecutionResult: 緊急決済実行結果（実行しない場合はNone）
        """
        try:
            # 緊急ストップロス設定確認
            emergency_config = get_threshold(TPSLConfig.EMERGENCY_SL, {})
            if not emergency_config.get("enable", False):
                return None

            self.logger.info("🔍 緊急ストップロス条件チェック開始")

            # 各ポジションの緊急決済チェック
            for position in virtual_positions:
                emergency_exit = await self._evaluate_emergency_exit(
                    position, current_price, emergency_config
                )
                if emergency_exit:
                    self.logger.critical(
                        f"🚨 緊急ストップロス発動! ポジション: {position['order_id']}"
                    )

                    # 緊急決済実行
                    result = await self._execute_emergency_exit(
                        position, current_price, "emergency", mode
                    )

                    # ポジションリストから削除
                    virtual_positions.remove(position)

                    return result

            return None

        except Exception as e:
            self.logger.error(f"❌ 緊急ストップロスチェックエラー: {e}")
            return None

    async def _evaluate_emergency_exit(
        self, position: dict, current_price: float, config: dict
    ) -> bool:
        """
        個別ポジションの緊急決済判定

        Args:
            position: 保有ポジション情報
            current_price: 現在価格
            config: 緊急ストップロス設定

        Returns:
            bool: 緊急決済が必要か
        """
        try:
            # Phase 53.11: None値の防御的処理
            raw_price = position.get("price")
            entry_side = position.get("side", "")
            entry_time = position.get("timestamp")

            if raw_price is None:
                self.logger.debug(f"⏭️ Phase 53.11: 不完全ポジションスキップ（緊急） - price=None")
                return False

            entry_price = float(raw_price)

            if entry_price <= 0:
                return False

            # 最小保有時間チェック（誤発動防止）
            min_hold_minutes = config.get("min_hold_minutes", 1)
            if isinstance(entry_time, datetime):
                time_diff = datetime.now() - entry_time
                if time_diff.total_seconds() < min_hold_minutes * 60:
                    return False

            # 含み損計算
            if entry_side.lower() == "buy":
                unrealized_pnl_ratio = (current_price - entry_price) / entry_price
            elif entry_side.lower() == "sell":
                unrealized_pnl_ratio = (entry_price - current_price) / entry_price
            else:
                return False

            # 最大損失閾値チェック
            max_loss_threshold = config.get("max_loss_threshold", 0.05)
            if unrealized_pnl_ratio <= -max_loss_threshold:
                self.logger.critical(
                    f"🚨 最大損失閾値超過! 含み損: {unrealized_pnl_ratio * 100:.2f}% (閾値: -{max_loss_threshold * 100:.0f}%)"
                )
                return True

            # 価格急変チェック
            price_change_result = await self._check_rapid_price_movement(current_price, config)
            if price_change_result and entry_side.lower() == "buy":  # 買いポジションで急落時
                self.logger.critical(f"🚨 急落検出! 価格変動: {price_change_result}")
                return True
            elif price_change_result and entry_side.lower() == "sell":  # 売りポジションで急騰時
                self.logger.critical(f"🚨 急騰検出! 価格変動: {price_change_result}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"❌ 緊急決済判定エラー: {e}")
            return False

    async def _execute_emergency_exit(
        self, position: dict, current_price: float, reason: str, mode: str
    ) -> ExecutionResult:
        """
        緊急決済実行（クールダウン無視）

        Args:
            position: 決済対象ポジション
            current_price: 現在価格
            reason: 緊急決済理由
            mode: 実行モード

        Returns:
            ExecutionResult: 決済実行結果
        """
        try:
            entry_side = position.get("side", "")
            amount = float(position.get("amount", 0))

            # 反対売買（決済）のサイド決定
            exit_side = "sell" if entry_side.lower() == "buy" else "buy"

            self.logger.critical(
                f"🚨 緊急決済実行: {exit_side} {amount} BTC @ {current_price:.0f}円 - 理由: {reason}"
            )

            # 決済実行結果作成
            result = await self._execute_position_exit(position, current_price, reason, mode)

            # 緊急決済フラグ設定
            result.emergency_exit = True
            result.emergency_reason = reason

            self.logger.info(f"✅ 緊急決済完了: {result.order_id}")

            return result

        except Exception as e:
            self.logger.error(f"❌ 緊急決済実行エラー: {e}")
            # エラー時も結果を返す（失敗として）
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.LIVE if mode == "live" else ExecutionMode.PAPER,
                order_id=None,
                price=current_price,
                amount=0.0,
                error_message=f"緊急決済エラー: {e}",
                side="emergency_exit",
                fee=0.0,
                status=OrderStatus.FAILED,
            )

    # Phase 51.6: _cleanup_orphaned_orders()/_cancel_orphaned_tp_sl_orders()削除（約160行）
    # 理由: Phase 50.5で無効化済み・Phase 49.6でcleanup_position_orders()に置き換え済み

    async def cleanup_position_orders(
        self,
        tp_order_id: Optional[str],
        sl_order_id: Optional[str],
        symbol: str,
        bitbank_client: BitbankClient,
        reason: str = "position_exit",
    ) -> Dict[str, Any]:
        """
        Phase 49.6: ポジション決済時のTP/SL注文クリーンアップ
        Phase 58.8: リトライ+検証ロジック追加（孤児SL防止）

        TP到達時: 残SL注文を自動削除
        SL到達時: 残TP注文を自動削除
        手動決済時: 両方を自動削除

        Args:
            tp_order_id: TP注文ID（存在する場合）
            sl_order_id: SL注文ID（存在する場合）
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス
            reason: クリーンアップ理由（"take_profit", "stop_loss", "manual"）

        Returns:
            Dict: {"cancelled_count": int, "errors": List[str], "success": bool}

        Raises:
            Exception: SL注文キャンセル失敗時（孤児SL防止）
        """
        cancelled_count = 0
        errors = []
        max_retries = 3
        retry_delay = 0.5  # 500ms

        async def _cancel_with_retry(order_id: str, order_type: str) -> bool:
            """リトライ付きキャンセル（Phase 58.8）"""
            for attempt in range(max_retries):
                try:
                    # キャンセル試行
                    await asyncio.to_thread(bitbank_client.cancel_order, order_id, symbol)
                    self.logger.info(
                        f"✅ Phase 58.8: {order_type}注文キャンセル成功 - "
                        f"ID: {order_id}, 試行: {attempt + 1}/{max_retries}"
                    )
                    return True
                except Exception as e:
                    error_str = str(e)
                    # 既にキャンセル/約定済みの場合は成功扱い
                    if "OrderNotFound" in error_str or "not found" in error_str.lower():
                        self.logger.debug(f"ℹ️ {order_type}注文{order_id}は既にキャンセル/約定済み")
                        return True

                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"⚠️ Phase 58.8: {order_type}注文キャンセル失敗 - "
                            f"ID: {order_id}, 試行: {attempt + 1}/{max_retries}, "
                            f"エラー: {e}, リトライ中..."
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        self.logger.error(
                            f"❌ Phase 58.8: {order_type}注文キャンセル最終失敗 - "
                            f"ID: {order_id}, 全{max_retries}回試行失敗: {e}"
                        )
            return False

        # TP注文キャンセル（SL到達時・手動決済時）
        if tp_order_id and reason in ["stop_loss", "manual", "position_exit"]:
            if await _cancel_with_retry(tp_order_id, "TP"):
                cancelled_count += 1
            else:
                errors.append(f"TP注文{tp_order_id}キャンセル失敗")

        # SL注文キャンセル（TP到達時・手動決済時）
        # Phase 59.6: 失敗時は例外を発生させず、孤児SL候補として記録（決済処理は続行）
        if sl_order_id and reason in ["take_profit", "manual", "position_exit"]:
            if await _cancel_with_retry(sl_order_id, "SL"):
                cancelled_count += 1
            else:
                error_msg = f"SL注文{sl_order_id}キャンセル失敗"
                errors.append(error_msg)
                # Phase 59.6: 例外ではなく孤児SL候補として記録（起動時クリーンアップ対象）
                self.logger.error(
                    f"⚠️ Phase 59.6: SL注文{sl_order_id}キャンセル失敗 - 孤児SL候補として記録"
                )
                self._mark_orphan_sl(sl_order_id, reason)

        if cancelled_count > 0:
            self.logger.info(
                f"🧹 Phase 58.8: ポジション決済時クリーンアップ完了 - "
                f"{cancelled_count}件キャンセル, 理由: {reason}"
            )

        return {"cancelled_count": cancelled_count, "errors": errors, "success": True}

    # Phase 64: should_apply_cooldown / _calculate_trend_strength は
    # cooldown.py (CooldownManager) に同一実装があるため削除

    async def _get_current_price(self, bitbank_client: Optional[BitbankClient]) -> float:
        """現在価格取得（緊急時用）"""
        try:
            if bitbank_client:
                ticker = await asyncio.to_thread(bitbank_client.fetch_ticker, "BTC/JPY")
                if ticker and "last" in ticker:
                    return float(ticker["last"])

            # フォールバック価格
            return get_threshold(TPSLConfig.FALLBACK_BTC_JPY, TPSLConfig.DEFAULT_FALLBACK_BTC_JPY)

        except Exception as e:
            self.logger.warning(f"⚠️ 現在価格取得エラー: {e}")
            return get_threshold(TPSLConfig.FALLBACK_BTC_JPY, TPSLConfig.DEFAULT_FALLBACK_BTC_JPY)

    async def _check_rapid_price_movement(
        self, current_price: float, config: dict
    ) -> Optional[str]:
        """
        急激な価格変動検出

        Returns:
            str: 価格変動情報（変動なしの場合はNone）
        """
        try:
            # 簡易実装: 設定された閾値以上の変動を検出
            # 実際の実装では過去5分間の価格履歴を確認する
            price_change_threshold = config.get("price_change_threshold", 0.03)

            # TODO: 実際の価格履歴データベースから過去5分間の価格変動を計算
            # 現在は簡易実装として、大きな価格変動があったと仮定した場合の処理のみ

            return None  # 実際の価格変動検出は将来実装

        except Exception as e:
            self.logger.error(f"❌ 価格変動チェックエラー: {e}")
            return None

    # Phase 64: place_take_profit / _place_tp_maker / _place_tp_native / place_stop_loss は
    # tp_sl_manager.py (TPSLManager) に移動

    # Phase 64: cleanup_old_unfilled_orders / cleanup_orphan_sl_orders は
    # position_restorer.py (PositionRestorer) に移動

    def _mark_orphan_sl(self, sl_order_id: str, reason: str) -> None:
        """
        Phase 59.6: 孤児SL候補をファイルに記録（次回起動時にクリーンアップ）

        Args:
            sl_order_id: キャンセルに失敗したSL注文ID
            reason: 失敗理由（take_profit, manual, position_exit等）
        """
        try:
            orphan_file = Path("logs/orphan_sl_orders.json")
            orphan_file.parent.mkdir(parents=True, exist_ok=True)

            orphans = []
            if orphan_file.exists():
                try:
                    orphans = json.loads(orphan_file.read_text())
                except json.JSONDecodeError:
                    orphans = []

            # 重複チェック
            existing_ids = {o.get("sl_order_id") for o in orphans}
            if sl_order_id not in existing_ids:
                orphans.append(
                    {
                        "sl_order_id": sl_order_id,
                        "reason": reason,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                orphan_file.write_text(json.dumps(orphans, indent=2, ensure_ascii=False))
                self.logger.info(
                    f"📝 Phase 59.6: 孤児SL候補記録 - ID: {sl_order_id}, 理由: {reason}"
                )

        except Exception as e:
            self.logger.error(f"❌ Phase 59.6: 孤児SL記録失敗: {e}")

    # Phase 64: cleanup_orphan_sl_orders は position_restorer.py (PositionRestorer) に移動
