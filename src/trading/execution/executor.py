"""
取引実行サービス - ExecutionServiceProtocol実装
Phase 49.16完了 - メイン実行ロジック・TP/SL設定完全見直し

ライブ/ペーパーモードを自動判別し、適切な取引実行を行う。
BitbankClient.create_orderを使用した実際の注文実行機能を提供。

Silent Failure修正済み: TradeEvaluationのsideフィールドを正しく使用。
Phase 49.16: TP/SL設定完全渡し（thresholds.yaml完全準拠）
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from tax.trade_history_recorder import TradeHistoryRecorder

from ...backtest.reporter import TradeTracker
from ...core.config import get_threshold
from ...core.exceptions import CryptoBotError
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient
from ..core import ExecutionMode, ExecutionResult, OrderStatus, TradeEvaluation
from .tp_sl_config import TPSLConfig


class ExecutionService:
    """
    取引実行サービス

    ExecutionServiceProtocolを実装し、ライブ/ペーパーモードで
    適切な取引実行を行う。
    """

    def __init__(self, mode: str = "paper", bitbank_client: Optional[BitbankClient] = None):
        """
        ExecutionService初期化

        Args:
            mode: 実行モード (live/paper/backtest)
            bitbank_client: BitbankClientインスタンス
        """
        self.mode = mode
        self.logger = get_logger()
        self.bitbank_client = bitbank_client

        # 統計情報
        self.executed_trades = 0
        self.session_pnl = 0.0
        self.current_balance = 0.0
        # Phase 47: 取引履歴記録システム
        try:
            self.trade_recorder = TradeHistoryRecorder()
        except Exception as e:
            self.logger.warning(f"⚠️ TradeHistoryRecorder初期化失敗: {e}")
            self.trade_recorder = None

        # Phase 49.15: バックテストレポート用取引追跡
        try:
            self.trade_tracker = TradeTracker()
        except Exception as e:
            self.logger.warning(f"⚠️ TradeTracker初期化失敗: {e}")
            self.trade_tracker = None

        # Phase 64.3: PositionTracker注入前のfallback用
        self._virtual_positions_fallback: List[Dict[str, Any]] = []

        # Phase 29.6: クールダウン管理
        self.last_order_time = None

        # Phase 56.3: バックテスト時刻管理（バックテスト時にシミュレーション時刻を使用）
        self.current_time: Optional[datetime] = None

        # Phase 64: _pending_verifications, _last_tp_sl_check_time, _last_orphan_scan_time
        # はTPSLManager / PositionRestorerに移動済み

        # モード別初期残高取得（Phase 55.9: get_threshold()使用に変更）
        # 旧方式: load_config()ではmode_balances属性が取得できないバグがあった
        # フォールバック値はすべて¥100,000（バックテスト基準）
        if self.mode == "backtest":
            self.virtual_balance = get_threshold("mode_balances.backtest.initial_balance", 100000.0)
        elif self.mode == "paper":
            self.virtual_balance = get_threshold("mode_balances.paper.initial_balance", 100000.0)
        else:
            self.virtual_balance = get_threshold("mode_balances.live.initial_balance", 100000.0)

        # 関連サービスの初期化（後で注入される）
        from .order_strategy import OrderStrategy

        self.order_strategy = OrderStrategy()
        self.stop_manager = None
        self.position_limits = None
        self.balance_monitor = None
        self.position_tracker = None  # Phase 42: 統合TP/SL用ポジション追跡
        self.data_service = None  # Phase 54.6: ATR取得Level 2用
        # Phase 64: TP/SL統合管理・ポジション復元（デフォルト生成。orchestratorから上書き注入可能）
        from .position_restorer import PositionRestorer
        from .tp_sl_manager import TPSLManager

        self.tp_sl_manager = TPSLManager()
        self.position_restorer = PositionRestorer()

        self.logger.info(f"✅ ExecutionService初期化完了 - モード: {mode}")

    @property
    def virtual_positions(self) -> List[Dict[str, Any]]:
        """Phase 64.3: PositionTrackerのlistを返す（単一ソース化）"""
        if self.position_tracker is not None:
            return self.position_tracker.virtual_positions
        return self._virtual_positions_fallback

    @virtual_positions.setter
    def virtual_positions(self, value: List[Dict[str, Any]]):
        """Phase 64.3: list再代入をin-place更新に変換"""
        if self.position_tracker is not None:
            self.position_tracker.virtual_positions[:] = value
        else:
            self._virtual_positions_fallback = value

    async def restore_positions_from_api(self):
        """Phase 63.4: 実ポジションベースの復元（Phase 64: PositionRestorerに委譲）"""
        if self.position_restorer:
            await self.position_restorer.restore_positions_from_api(
                virtual_positions=self.virtual_positions,
                bitbank_client=self.bitbank_client,
                position_tracker=self.position_tracker,
                mode=self.mode,
            )

    async def ensure_tp_sl_for_existing_positions(self):
        """Phase 56.5: 既存ポジションのTP/SL確保（Phase 64: TPSLManagerに委譲）"""
        if self.tp_sl_manager:
            await self.tp_sl_manager.ensure_tp_sl_for_existing_positions(
                virtual_positions=self.virtual_positions,
                bitbank_client=self.bitbank_client,
                position_tracker=self.position_tracker,
                mode=self.mode,
            )

    # Phase 64: _check_tp_sl_orders_exist / _place_missing_tp_sl は
    # tp_sl_manager.py (TPSLManager) に直接実装済み

    async def execute_trade(self, evaluation: TradeEvaluation) -> ExecutionResult:
        """
        取引実行メイン処理

        Args:
            evaluation: 取引評価結果

        Returns:
            ExecutionResult: 実行結果
        """
        try:
            self.logger.info(
                f"🚀 取引実行開始 - モード: {self.mode}, アクション: {evaluation.side}"
            )

            # holdシグナルの場合は取引実行しない（根本解決）
            if getattr(evaluation, "side", "").lower() in ["hold", "none", ""]:
                self.logger.info(f"📤 holdシグナルのため取引スキップ - side: {evaluation.side}")
                return ExecutionResult(
                    success=True,  # holdは正常な状態なので成功扱い
                    mode=ExecutionMode.LIVE if self.mode == "live" else ExecutionMode.PAPER,
                    order_id=None,
                    price=0.0,
                    amount=0.0,
                    error_message=None,
                    side=evaluation.side,
                    fee=0.0,
                    status=OrderStatus.CANCELLED,  # スキップ状態（holdのため）
                )

            # Phase 37: 証拠金残高チェック（ライブモードのみ・Container exit回避）
            if self.balance_monitor:
                balance_check = await self.balance_monitor.validate_margin_balance(
                    mode=self.mode,
                    bitbank_client=self.bitbank_client,
                )
                if not balance_check["sufficient"]:
                    self.logger.info(
                        f"💤 証拠金不足のため取引スキップ（Container exit回避） - "
                        f"利用可能={balance_check['available']:.0f}円 < 必要={balance_check['required']:.0f}円"
                    )
                    available = balance_check["available"]
                    required = balance_check["required"]
                    return ExecutionResult(
                        success=False,
                        mode=ExecutionMode.LIVE if self.mode == "live" else ExecutionMode.PAPER,
                        order_id=None,
                        price=0.0,
                        amount=0.0,
                        error_message=f"証拠金不足: {available:.0f}円 < {required:.0f}円",
                        side=evaluation.side,
                        fee=0.0,
                        status=OrderStatus.REJECTED,  # 残高不足により拒否
                    )

            # ポジション管理制限チェック（口座残高使い切り問題対策）
            if self.position_limits:
                # Phase 51.8: レジーム情報を取得（market_conditionsから）
                regime = evaluation.market_conditions.get("regime", None)

                # Phase 55.6: backtestモードでもvirtual_balanceを使用
                # Phase 56.3: current_time追加（バックテスト時刻対応）
                position_check_result = await self.position_limits.check_limits(
                    evaluation,
                    self.virtual_positions,
                    self.last_order_time,
                    (
                        self.virtual_balance
                        if self.mode in ["paper", "backtest"]
                        else self.current_balance
                    ),
                    regime=regime,  # Phase 51.8: レジーム別制限適用
                    current_time=self.current_time,  # Phase 56.3: バックテスト時刻
                    mode=self.mode,  # Phase 65.6: 残高ベース推定排除
                )
                if not position_check_result["allowed"]:
                    self.logger.warning(
                        f"🚫 取引制限により取引拒否: {position_check_result['reason']}"
                    )
                    return ExecutionResult(
                        success=False,
                        mode=ExecutionMode.LIVE if self.mode == "live" else ExecutionMode.PAPER,
                        order_id=None,
                        price=0.0,
                        amount=0.0,
                        error_message=position_check_result["reason"],
                        side=evaluation.side,
                        fee=0.0,
                        status=OrderStatus.REJECTED,  # 制限により拒否
                    )

            # 最小ロット保証（動的サイジング対応）
            evaluation = self.order_strategy.ensure_minimum_trade_size(evaluation)

            if self.mode == "live":
                return await self._execute_live_trade(evaluation)
            elif self.mode == "paper":
                return await self._execute_paper_trade(evaluation)
            else:
                return await self._execute_backtest_trade(evaluation)

        except Exception as e:
            self.logger.error(f"❌ 取引実行エラー: {e}")
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.LIVE if self.mode == "live" else ExecutionMode.PAPER,
                order_id=None,
                price=0.0,
                amount=0.0,
                error_message=str(e),
                side=getattr(evaluation, "side", "unknown"),
                fee=0.0,
                status=OrderStatus.FAILED,
            )

    async def _execute_live_trade(self, evaluation: TradeEvaluation) -> ExecutionResult:
        """ライブトレード実行（Phase 26: 指値注文オプション対応）"""
        try:
            if not self.bitbank_client:
                raise CryptoBotError("ライブトレードにはBitbankClientが必要です")

            # 注文パラメータ作成（設定ファイル化）
            symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")
            side = evaluation.side  # "buy" or "sell"
            amount = float(evaluation.position_size)

            # Phase 62.9: Maker戦略判定
            maker_result = None
            use_maker = False
            maker_config = None

            if self.order_strategy:
                maker_config = await self.order_strategy.get_maker_execution_config(
                    evaluation, self.bitbank_client
                )
                use_maker = maker_config.get("use_maker", False)

            if use_maker:
                # Maker注文試行
                maker_result = await self.order_strategy.execute_maker_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    maker_config=maker_config,
                    bitbank_client=self.bitbank_client,
                )

                if maker_result and maker_result.success:
                    self.logger.info("✅ Phase 62.9: Maker約定成功 → 後続処理へ")
                else:
                    # Maker失敗 → Takerフォールバック判定
                    fallback_enabled = get_threshold(
                        "order_execution.maker_strategy.fallback_to_taker", True
                    )
                    if fallback_enabled:
                        self.logger.info("📡 Phase 62.9: Maker失敗 → Takerフォールバック")
                        maker_result = None  # Takerロジックへ
                    else:
                        self.logger.warning(
                            "⚠️ Phase 62.9: Maker失敗・フォールバック無効 → エントリー中止"
                        )
                        return ExecutionResult(
                            success=False,
                            mode=ExecutionMode.LIVE,
                            order_id=None,
                            price=0.0,
                            amount=0.0,
                            error_message="Phase 62.9: Maker失敗・フォールバック無効",
                            side=side,
                            fee=0.0,
                            status=OrderStatus.FAILED,
                        )

            # Maker成功時はスキップ、それ以外はTaker注文
            if maker_result and maker_result.success:
                order_result = {
                    "id": maker_result.order_id,
                    "price": maker_result.price,
                    "amount": maker_result.amount,
                    "filled_price": maker_result.filled_price,
                    "filled_amount": maker_result.filled_amount,
                    "fee": maker_result.fee,
                }
                order_type = "limit"
                price = maker_result.price
                order_execution_config = {"strategy": "maker_post_only"}
            else:
                # 指値注文オプション機能（Phase 26）- Taker注文
                if self.order_strategy:
                    order_execution_config = await self.order_strategy.get_optimal_execution_config(
                        evaluation, self.bitbank_client
                    )
                else:
                    # フォールバック: デフォルト注文タイプ使用
                    order_execution_config = {
                        "order_type": get_threshold(
                            "trading_constraints.default_order_type", "market"
                        ),
                        "price": None,
                        "strategy": "default",
                    }

                order_type = order_execution_config["order_type"]
                price = order_execution_config.get("price")

                self.logger.info(
                    f"💰 Bitbank注文実行: {side} {amount} BTC ({order_type}注文)"
                    + (f" @ {price:.0f}円" if price else "")
                )

                # 注文パラメータ構築
                order_params = {
                    "symbol": symbol,
                    "side": side,
                    "order_type": order_type,
                    "amount": amount,
                }

                # 指値注文の場合は価格を追加
                if order_type == "limit" and price:
                    order_params["price"] = price
                    # Phase 63.3: Bug 1修正 - Taker fallbackではpost_only不要
                    # このコードブロックはmaker_result=None（Maker失敗後）にのみ到達
                    # Maker失敗後に再度post_onlyを設定するのは論理矛盾
                    # 旧: Phase 62.21でpost_only追加していたがTaker約定を阻害していた

                # 実際の注文実行
                order_result = self.bitbank_client.create_order(**order_params)

            # 実行結果作成（Phase 32.1: NoneType対策強化）
            result = ExecutionResult(
                success=True,
                mode=ExecutionMode.LIVE,
                order_id=order_result.get("id"),
                price=float(order_result.get("price") or price or 0),
                amount=float(order_result.get("amount") or 0),
                filled_price=float(
                    order_result.get("filled_price") or order_result.get("price") or price or 0
                ),
                # Phase 64.3: フォールバック廃止 - 未約定時に全量でTP/SL配置するバグを防止
                filled_amount=float(order_result.get("filled_amount") or 0),
                error_message=None,
                side=side,
                fee=float(order_result.get("fee") or 0),
                status=(OrderStatus.FILLED if order_type == "market" else OrderStatus.SUBMITTED),
                notes=f"{order_type}注文実行 - {order_execution_config.get('strategy', 'default')}",
            )

            # Phase 67.5: SUBMITTED limit注文の約定ポーリング
            # bitbankはlimit注文を即時返却(filled_amount=0)するが、
            # 数秒以内に約定することが多いためポーリングで確認
            if result.status == OrderStatus.SUBMITTED and result.filled_amount <= 0:
                poll_order_id = result.order_id
                if poll_order_id and self.bitbank_client:
                    max_attempts = 5
                    poll_interval = 2  # 秒（合計最大10秒）
                    for attempt in range(max_attempts):
                        await asyncio.sleep(poll_interval)
                        try:
                            order_info = await asyncio.to_thread(
                                self.bitbank_client.fetch_order,
                                poll_order_id,
                                symbol,
                            )
                            filled = float(order_info.get("filled", 0))
                            if filled > 0:
                                result.filled_amount = filled
                                result.filled_price = float(
                                    order_info.get("average", 0)
                                    or order_info.get("price", 0)
                                    or result.price
                                )
                                result.status = OrderStatus.FILLED
                                self.logger.info(
                                    f"✅ Phase 67.5: 約定確認 - "
                                    f"試行{attempt + 1}/{max_attempts}, "
                                    f"数量={filled}"
                                )
                                break
                            order_status = order_info.get("status", "")
                            if order_status in (
                                "closed",
                                "canceled",
                                "cancelled",
                            ):
                                self.logger.info(
                                    f"ℹ️ Phase 67.5: 注文状態={order_status} - ポーリング終了"
                                )
                                break
                        except Exception as e:
                            self.logger.warning(
                                f"⚠️ Phase 67.5: 約定確認エラー " f"(試行{attempt + 1}): {e}"
                            )

            # 統計更新
            self.executed_trades += 1

            # Phase 47: 取引履歴記録（ライブモード）
            # Phase 62.16: スリッページ記録追加
            if self.trade_recorder:
                try:
                    # Phase 62.16: スリッページ計算（期待価格 vs 約定価格）
                    expected_price = float(getattr(evaluation, "entry_price", 0)) or price
                    actual_price = result.filled_price
                    # スリッページ = 約定価格 - 期待価格（buy時は正が不利、sell時は負が不利）
                    slippage = actual_price - expected_price if expected_price > 0 else None

                    self.trade_recorder.record_trade(
                        trade_type="entry",
                        side=side,
                        amount=result.filled_amount,
                        price=result.filled_price,
                        fee=result.fee,
                        order_id=result.order_id,
                        notes=f"Live {order_type}注文 - {order_execution_config.get('strategy', 'default')}",
                        slippage=slippage,
                        expected_price=expected_price,
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ 取引履歴記録失敗: {e}")

            # Phase 49.15: TradeTracker記録（バックテストレポート用）
            if self.trade_tracker:
                try:
                    # Phase 51.8-10: レジーム情報取得・記録（文字列値使用）
                    regime_value = evaluation.market_conditions.get("regime_value", None)

                    self.trade_tracker.record_entry(
                        order_id=result.order_id,
                        side=side,
                        amount=result.filled_amount,
                        price=result.filled_price,
                        timestamp=datetime.now(),
                        strategy=order_execution_config.get("strategy", "unknown"),
                        regime=regime_value,  # Phase 51.8-10: レジーム情報（文字列）
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ TradeTracker記録失敗: {e}")

            # Phase 29.6: クールダウン時刻更新
            self.last_order_time = datetime.now()

            # ログ出力（注文タイプ別）
            if order_type == "market":
                self.logger.info(
                    f"✅ 成行注文実行成功: 注文ID={result.order_id}, 手数料: Taker(0.1%)"
                )
            else:
                self.logger.info(
                    f"✅ 指値注文投入成功: 注文ID={result.order_id}, 予想手数料: Maker(0%)"
                )

            # Phase 29.6: ライブモードでもポジション追跡（バグ修正）
            # Phase 51.6: TP/SL再計算メソッド抽出（可読性向上・保守性向上）
            actual_filled_price = result.filled_price or result.price

            # TP/SL再計算（3段階ATRフォールバック）
            try:
                final_tp, final_sl = await self.tp_sl_manager.calculate_tp_sl_for_live_trade(
                    evaluation,
                    result,
                    side,
                    amount,
                    bitbank_client=self.bitbank_client,
                    current_time=self.current_time,
                )
            except CryptoBotError as e:
                # ATR取得失敗・TP/SL再計算失敗時のエントリー中止
                self.logger.error(f"❌ Phase 51.6: TP/SL再計算エラー - {e}")
                # Phase 65.5: order_id・約定情報を保持（ロールバック追跡用）
                return ExecutionResult(
                    success=False,
                    error_message=str(e),
                    mode=ExecutionMode.LIVE,
                    order_id=result.order_id,
                    side=side,
                    amount=result.amount,
                    price=result.price,
                    filled_price=result.filled_price,
                    filled_amount=result.filled_amount,
                    status=OrderStatus.FAILED,
                    timestamp=datetime.now(),
                )

            # Phase 64.3: filled_amount=0ならTP/SL配置スキップ（未約定limit注文）
            # Phase 67.5: 次サイクルでTP/SLチェックを強制実行するためゲートリセット
            actual_amount = result.filled_amount
            if actual_amount <= 0:
                self.logger.warning(
                    f"⚠️ Phase 67.5: ポーリング後もfilled_amount=0 - "
                    f"次サイクル強制チェック（注文状態: {result.status}）"
                )
                if self.tp_sl_manager:
                    self.tp_sl_manager._last_tp_sl_check_time = None
                return result

            # Phase 64.3: position_tracker経由で追加（単一ソース化）
            if self.position_tracker:
                live_position = self.position_tracker.add_position(
                    order_id=result.order_id,
                    side=side,
                    amount=actual_amount,
                    price=actual_filled_price,
                    take_profit=final_tp,
                    stop_loss=final_sl,
                )
            else:
                live_position = {
                    "order_id": result.order_id,
                    "side": side,
                    "amount": actual_amount,
                    "price": actual_filled_price,
                    "timestamp": datetime.now(),
                    "take_profit": final_tp,
                    "stop_loss": final_sl,
                    "tp_order_id": None,
                    "sl_order_id": None,
                }
                self.virtual_positions.append(live_position)

            # Phase 51.6: 古い注文クリーンアップ（bitbank 30件制限対策）
            if self.position_restorer:
                try:
                    symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")
                    # Phase 64.4: position_restorerに直接委譲（ラッパー削除）
                    cleanup_result = await self.position_restorer.cleanup_old_unfilled_orders(
                        symbol=symbol,
                        bitbank_client=self.bitbank_client,
                        virtual_positions=self.virtual_positions,
                    )
                    if cleanup_result["cancelled_count"] > 0:
                        self.logger.info(
                            f"🧹 Phase 51.6: 古い孤児注文クリーンアップ実行 - "
                            f"{cleanup_result['cancelled_count']}件キャンセル "
                            f"（{cleanup_result['order_count']}件中）"
                        )
                except Exception as e:
                    # クリーンアップ失敗しても処理継続（TP/SL配置を優先）
                    self.logger.warning(
                        f"⚠️ Phase 51.6: 古い注文クリーンアップ失敗（処理継続）: {e}"
                    )

            # Phase 51.10-A: エントリー前の同一側TP/SL注文クリーンアップ
            if self.tp_sl_manager:
                try:
                    await self.tp_sl_manager.cleanup_old_tp_sl_before_entry(
                        side=side,
                        symbol=symbol,
                        entry_order_id=result.order_id,
                        virtual_positions=self.virtual_positions,
                        bitbank_client=self.bitbank_client,
                    )
                except Exception as e:
                    # クリーンアップ失敗してもエントリーは継続（Phase 51.6思想維持）
                    self.logger.warning(
                        f"⚠️ Phase 51.10-A: エントリー前クリーンアップ失敗（処理継続）: {e}"
                    )

            # Phase 51.6: Atomic Entry Pattern（Entry/TP/SL一体化・全成功 or 全ロールバック）
            if self.stop_manager and final_tp and final_sl:
                # Phase 64.3: position_tracker.add_position()はvirtual_positions追加時に実行済み

                # Phase 51.6: Atomic Entry Pattern - TP/SL注文ID初期化
                tp_order_id = None
                sl_order_id = None

                try:
                    # Step 1/3: エントリー注文実行済み
                    self.logger.info(
                        f"✅ Phase 51.6 Step 1/3: エントリー成功 - "
                        f"ID: {result.order_id}, 価格: {actual_filled_price:.0f}円"
                    )

                    # Step 2/3: TP注文配置（リトライ付き）
                    # Phase 63.3: Bug 2修正 - actual_amount使用（部分約定対応）
                    tp_order = await self.tp_sl_manager.place_tp_with_retry(
                        side=side,
                        amount=actual_amount,
                        entry_price=actual_filled_price,
                        take_profit_price=final_tp,
                        symbol=symbol,
                        bitbank_client=self.bitbank_client,
                        max_retries=3,
                    )
                    if not tp_order:
                        raise Exception("TP注文配置失敗（3回リトライ後）")

                    tp_order_id = tp_order.get("order_id")
                    self.logger.info(
                        f"✅ Phase 51.6 Step 2/3: TP配置成功 - "
                        f"ID: {tp_order_id}, 価格: {final_tp:.0f}円"
                    )

                    # Step 3/3: SL注文配置（リトライ付き）
                    # Phase 63.3: Bug 2修正 - actual_amount使用（部分約定対応）
                    sl_order = await self.tp_sl_manager.place_sl_with_retry(
                        side=side,
                        amount=actual_amount,
                        entry_price=actual_filled_price,
                        stop_loss_price=final_sl,
                        symbol=symbol,
                        bitbank_client=self.bitbank_client,
                        max_retries=3,
                    )
                    if not sl_order:
                        raise Exception("SL注文配置失敗（3回リトライ後）")

                    sl_order_id = sl_order.get("order_id")
                    # Phase 62.17: SL配置時刻を取得（タイムアウトチェック用）
                    sl_placed_at = sl_order.get("sl_placed_at")
                    self.logger.info(
                        f"✅ Phase 51.6 Step 3/3: SL配置成功 - "
                        f"ID: {sl_order_id}, 価格: {final_sl:.0f}円"
                    )

                    # 全成功 → TP/SL注文ID保存
                    self.logger.info("🎉 Phase 51.6: Atomic Entry完了 - Entry/TP/SL すべて成功")

                    # PositionTrackerに注文IDを保存
                    if self.position_tracker:
                        try:
                            self.position_tracker.update_position_tp_sl(
                                order_id=result.order_id,
                                tp_order_id=tp_order_id,
                                sl_order_id=sl_order_id,
                            )
                            self.logger.debug(
                                f"💾 Phase 51.6: TP/SL注文ID保存完了 - "
                                f"TP: {tp_order_id}, SL: {sl_order_id}"
                            )
                        except Exception as e:
                            self.logger.warning(f"⚠️ Phase 51.6: TP/SL注文ID保存失敗（継続）: {e}")

                    # virtual_positionsにも保存（stop_manager互換性維持）
                    live_position["tp_order_id"] = tp_order_id
                    live_position["sl_order_id"] = sl_order_id
                    # Phase 62.17: SL配置時刻を保存（タイムアウトチェック用）
                    live_position["sl_placed_at"] = sl_placed_at

                    # Phase 62.20: TP/SL欠損自動復旧 - 10分後検証をスケジュール
                    # Phase 63.3: Bug 2修正 - actual_amount使用
                    self.tp_sl_manager.schedule_tp_sl_verification(
                        entry_order_id=result.order_id,
                        side=side,
                        amount=actual_amount,
                        entry_price=actual_filled_price,
                        tp_order_id=tp_order_id,
                        sl_order_id=sl_order_id,
                        symbol=symbol,
                    )

                except Exception as e:
                    # Phase 51.6: Atomic Entry失敗 → 全ロールバック
                    self.logger.error(f"❌ Phase 51.6: Atomic Entry失敗 - ロールバック開始: {e}")

                    # ロールバック実行（TP/SL/Entry注文をすべてキャンセル）
                    await self.tp_sl_manager.rollback_entry(
                        entry_order_id=result.order_id,
                        tp_order_id=tp_order_id,
                        sl_order_id=sl_order_id,
                        symbol=symbol,
                        error=e,
                        bitbank_client=self.bitbank_client,
                    )

                    # Phase 63.3: Bug 3修正 - ロールバック後に部分約定チェック
                    # エントリー注文がキャンセルされても約定済み分は残る
                    partial_filled = 0.0
                    try:
                        order_info = await asyncio.to_thread(
                            self.bitbank_client.fetch_order, result.order_id, symbol
                        )
                        if order_info:
                            partial_filled = float(order_info.get("filled") or 0)
                    except Exception as e:
                        self.logger.debug(f"Phase 65.5: 注文情報取得失敗（0として扱う）: {e}")

                    if partial_filled > 0:
                        # 部分約定あり → virtual_positionsを約定量で更新（削除しない）
                        self.logger.critical(
                            f"🚨 Phase 63.3: 部分約定検出 - {partial_filled} BTC残存。"
                            f"TP/SL再配置試行。order_id={result.order_id}"
                        )
                        # Phase 64.3: virtual_positionsの量を約定分に更新（単一ソース）
                        if self.position_tracker:
                            pos = self.position_tracker.find_position(result.order_id)
                            if pos:
                                pos["amount"] = partial_filled
                        else:
                            for vp in self.virtual_positions:
                                if vp.get("order_id") == result.order_id:
                                    vp["amount"] = partial_filled
                                    break

                        # TP/SL再配置試行
                        try:
                            tp_retry = await self.tp_sl_manager.place_tp_with_retry(
                                side=side,
                                amount=partial_filled,
                                entry_price=actual_filled_price,
                                take_profit_price=final_tp,
                                symbol=symbol,
                                bitbank_client=self.bitbank_client,
                                max_retries=3,
                            )
                            sl_retry = await self.tp_sl_manager.place_sl_with_retry(
                                side=side,
                                amount=partial_filled,
                                entry_price=actual_filled_price,
                                stop_loss_price=final_sl,
                                symbol=symbol,
                                bitbank_client=self.bitbank_client,
                                max_retries=3,
                            )
                            # Phase 64.3: order_idの存在確認（偽成功防止）
                            tp_ok = tp_retry and tp_retry.get("order_id")
                            sl_ok = sl_retry and sl_retry.get("order_id")
                            if tp_ok and sl_ok:
                                # 再配置成功 → virtual_positionsにTP/SL情報追加
                                for vp in self.virtual_positions:
                                    if vp.get("order_id") == result.order_id:
                                        vp["tp_order_id"] = tp_retry["order_id"]
                                        vp["sl_order_id"] = sl_retry["order_id"]
                                        break
                                self.logger.info(
                                    f"✅ Phase 63.3: 部分約定分TP/SL再配置成功 - "
                                    f"{partial_filled} BTC"
                                )
                            else:
                                self.logger.critical(
                                    f"🚨 Phase 64.3: 部分約定分TP/SL再配置失敗 - "
                                    f"TP={'OK' if tp_ok else 'NG'}, "
                                    f"SL={'OK' if sl_ok else 'NG'}, "
                                    f"order_id={result.order_id}, "
                                    f"amount={partial_filled} BTC"
                                )
                        except Exception as tp_sl_err:
                            self.logger.critical(
                                f"🚨 Phase 63.3: 部分約定TP/SL再配置エラー - "
                                f"手動介入必要。order_id={result.order_id}, "
                                f"amount={partial_filled} BTC, error={tp_sl_err}"
                            )

                        # 部分約定があったので成功として返す（TP/SLは再配置済みまたは手動介入）
                        return ExecutionResult(
                            success=True,
                            order_id=result.order_id,
                            side=side,
                            amount=partial_filled,
                            price=actual_filled_price,
                            filled_amount=partial_filled,
                            filled_price=actual_filled_price,
                            error_message=f"Phase 63.3: 部分約定 {partial_filled} BTC（TP/SL再配置済み）",
                            mode=ExecutionMode.LIVE,
                            status=OrderStatus.FILLED,
                        )

                    # 約定なし → 通常のロールバック（従来動作）
                    # Phase 64.3: 単一ソースから削除（listは共有）
                    if self.position_tracker:
                        self.position_tracker.remove_position(result.order_id)
                    else:
                        self.virtual_positions[:] = [
                            p
                            for p in self.virtual_positions
                            if p.get("order_id") != result.order_id
                        ]

                    # エラー結果返却
                    # Phase 65.5: mode引数追加
                    return ExecutionResult(
                        success=False,
                        mode=ExecutionMode.LIVE,
                        order_id=result.order_id,
                        side=side,
                        amount=amount,
                        price=actual_filled_price,
                        error_message=f"Phase 51.6 Atomic Entry失敗（ロールバック完了）: {e}",
                    )

            return result

        except Exception as e:
            # Phase 33: エラーコード50061（残高不足）を明示的に検出
            error_message = str(e)
            if "50061" in error_message:
                self.logger.error(
                    f"❌ ライブ取引実行失敗（残高不足）: エラーコード50061 - 新規注文に必要な利用可能証拠金が不足しています - {error_message}"
                )
            else:
                self.logger.error(f"❌ ライブ取引実行失敗: {e}")
            raise

    async def _execute_paper_trade(self, evaluation: TradeEvaluation) -> ExecutionResult:
        """ペーパートレード実行"""
        try:
            # 仮想実行（実際の注文は行わない）
            side = evaluation.side
            amount = float(evaluation.position_size)

            # 実際の市場価格取得（ペーパーモードでも正確な価格記録）
            price = float(getattr(evaluation, "entry_price", 0))
            if price == 0 and self.bitbank_client:
                try:
                    # Bitbank公開APIから現在価格取得（認証不要・ペーパーモードでも使用可能）
                    ticker = await asyncio.to_thread(self.bitbank_client.fetch_ticker, "BTC/JPY")
                    if ticker and "last" in ticker:
                        price = float(ticker["last"])
                        self.logger.info(f"📊 ペーパートレード実価格取得: {price:.0f}円")
                    else:
                        price = get_threshold(
                            TPSLConfig.FALLBACK_BTC_JPY, TPSLConfig.DEFAULT_FALLBACK_BTC_JPY
                        )
                        self.logger.warning(
                            f"⚠️ ticker取得失敗、フォールバック価格使用: {price:.0f}円"
                        )
                except Exception as e:
                    price = get_threshold(
                        TPSLConfig.FALLBACK_BTC_JPY, TPSLConfig.DEFAULT_FALLBACK_BTC_JPY
                    )
                    self.logger.warning(
                        f"⚠️ 価格取得エラー、フォールバック価格使用: {price:.0f}円 - {e}"
                    )
            elif price == 0:
                price = get_threshold(
                    TPSLConfig.FALLBACK_BTC_JPY, TPSLConfig.DEFAULT_FALLBACK_BTC_JPY
                )
                self.logger.warning(f"⚠️ BitbankClient未設定、フォールバック価格使用: {price:.0f}円")

            # 仮想実行結果作成
            virtual_order_id = f"paper_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            result = ExecutionResult(
                success=True,
                mode=ExecutionMode.PAPER,
                order_id=virtual_order_id,
                price=price,
                amount=amount,
                filled_price=price,
                filled_amount=amount,
                error_message=None,
                side=side,
                fee=0.0,  # ペーパーは手数料なし
                status=OrderStatus.FILLED,
            )

            # Phase 64.3: position_tracker経由で追加（単一ソース化）
            virtual_position = {
                "order_id": virtual_order_id,
                "side": side,
                "amount": amount,
                "price": price,
                "timestamp": datetime.now(),
                "take_profit": getattr(evaluation, "take_profit", None),
                "stop_loss": getattr(evaluation, "stop_loss", None),
                "strategy_name": getattr(evaluation, "strategy_name", "unknown"),
                "adjusted_confidence": getattr(evaluation, "adjusted_confidence", None),
            }
            if self.position_tracker:
                try:
                    virtual_position = self.position_tracker.add_position(
                        order_id=virtual_order_id,
                        side=side,
                        amount=amount,
                        price=price,
                        take_profit=getattr(evaluation, "take_profit", None),
                        stop_loss=getattr(evaluation, "stop_loss", None),
                        strategy_name=getattr(evaluation, "strategy_name", "unknown"),
                        adjusted_confidence=getattr(evaluation, "adjusted_confidence", None),
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ ペーパーポジション追加エラー: {e}")
                    self._virtual_positions_fallback.append(virtual_position)
            else:
                self.virtual_positions.append(virtual_position)

            # 統計更新
            self.executed_trades += 1

            # Phase 47: 取引履歴記録（ペーパーモード）
            if self.trade_recorder:
                try:
                    self.trade_recorder.record_trade(
                        trade_type="entry",
                        side=side,
                        amount=amount,
                        price=price,
                        fee=0.0,
                        order_id=virtual_order_id,
                        notes=f"Paper trade - {virtual_position.get('strategy_name', 'unknown')}",
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ 取引履歴記録失敗: {e}")

            # Phase 49.15: TradeTracker記録（バックテストレポート用）
            if self.trade_tracker:
                try:
                    # Phase 51.8-10: レジーム情報取得・記録（文字列値使用）
                    regime_value = evaluation.market_conditions.get("regime_value", None)

                    self.trade_tracker.record_entry(
                        order_id=virtual_order_id,
                        side=side,
                        amount=amount,
                        price=price,
                        timestamp=datetime.now(),
                        strategy=virtual_position.get("strategy_name", "unknown"),
                        regime=regime_value,  # Phase 51.8-10: レジーム情報（文字列）
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ TradeTracker記録失敗: {e}")

            # Phase 29.6: クールダウン時刻更新
            self.last_order_time = datetime.now()

            # ログ出力（Phase 28: TP/SL価格表示追加）
            tp_info = (
                f", TP:{virtual_position['take_profit']:.0f}円"
                if virtual_position.get("take_profit")
                else ""
            )
            sl_info = (
                f", SL:{virtual_position['stop_loss']:.0f}円"
                if virtual_position.get("stop_loss")
                else ""
            )
            self.logger.info(
                f"📝 ペーパー取引実行: {side} {amount} BTC @ {price:.0f}円{tp_info}{sl_info}"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ ペーパー取引実行失敗: {e}")
            raise

    async def _execute_backtest_trade(self, evaluation: TradeEvaluation) -> ExecutionResult:
        """
        バックテスト実行（Phase 51.7: ライブモード完全一致化）
        Phase 51.8-J4-D: 残高管理追加（エントリー時資金控除・不足時拒否）
        """
        try:
            # バックテスト用の簡易実行
            side = evaluation.side
            amount = float(evaluation.position_size)
            price = float(getattr(evaluation, "entry_price", 0))

            # Phase 57: 必要証拠金計算（bitbank信用取引は2倍レバレッジ）
            order_total = price * amount  # 注文総額
            required_margin = order_total / 2  # 必要証拠金（50%）

            # Phase 51.8-J4-D: 残高チェック
            if self.virtual_balance < required_margin:
                self.logger.warning(
                    f"⚠️ Phase 51.8-J4-D: 残高不足により取引拒否 - "
                    f"必要証拠金: ¥{required_margin:,.0f}, "
                    f"現在残高: ¥{self.virtual_balance:,.0f}"
                )
                return ExecutionResult(
                    success=False,
                    mode=ExecutionMode.PAPER,
                    order_id=None,
                    price=0.0,
                    amount=0.0,
                    filled_price=0.0,
                    filled_amount=0.0,
                    error_message=f"残高不足: 必要¥{required_margin:,.0f}, 残高¥{self.virtual_balance:,.0f}",
                    side=side,
                    fee=0.0,
                    status=OrderStatus.FAILED,
                )

            # Phase 51.8-J4-D: エントリー時に証拠金を控除
            self.virtual_balance -= required_margin

            # Phase 62.8: 手数料はreporter.pyで一括計算（多重計算バグ修正）
            # 修正前: executor.py/backtest_runner.py/reporter.pyで4箇所計算 → 2.5倍過剰控除
            # 修正後: reporter.pyのみで往復手数料を計算
            fee_amount = 0  # ログ出力用（実際の控除はreporter.pyで実施）

            self.logger.info(
                f"💰 Phase 62.8: エントリー処理 - "
                f"証拠金控除: -¥{required_margin:,.0f} → 残高: ¥{self.virtual_balance:,.0f}"
            )

            virtual_order_id = f"backtest_{self.executed_trades + 1}"

            result = ExecutionResult(
                success=True,
                mode=ExecutionMode.PAPER,  # バックテストはペーパーモード扱い
                order_id=virtual_order_id,
                price=price,
                amount=amount,
                filled_price=price,
                filled_amount=amount,
                error_message=None,
                side=side,
                fee=abs(fee_amount),  # 手数料（正の値で記録）
                status=OrderStatus.FILLED,
            )

            # Phase 51.7: 仮想ポジション記録（TP/SL価格追加 - ライブモード一致化）
            # Phase 56.3: バックテスト時はcurrent_time使用
            trade_timestamp = self.current_time if self.current_time else datetime.now()
            # Phase 64.3: position_tracker経由で追加（単一ソース化）
            virtual_position = {
                "order_id": virtual_order_id,
                "side": side,
                "amount": amount,
                "price": price,
                "timestamp": trade_timestamp,
                "take_profit": getattr(evaluation, "take_profit", None),
                "stop_loss": getattr(evaluation, "stop_loss", None),
                "strategy_name": getattr(evaluation, "strategy_name", "unknown"),
                "adjusted_confidence": getattr(evaluation, "adjusted_confidence", None),
            }
            if self.position_tracker:
                try:
                    virtual_position = self.position_tracker.add_position(
                        order_id=virtual_order_id,
                        side=side,
                        amount=amount,
                        price=price,
                        take_profit=getattr(evaluation, "take_profit", None),
                        stop_loss=getattr(evaluation, "stop_loss", None),
                        strategy_name=getattr(evaluation, "strategy_name", "unknown"),
                        adjusted_confidence=getattr(evaluation, "adjusted_confidence", None),
                        timestamp=trade_timestamp,
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ バックテストポジション追加エラー: {e}")
                    self._virtual_positions_fallback.append(virtual_position)
            else:
                self.virtual_positions.append(virtual_position)

            # 統計更新
            self.executed_trades += 1

            # Phase 49.15: TradeTracker記録（バックテストレポート用）
            if self.trade_tracker:
                try:
                    # Phase 51.8-10: レジーム情報取得・記録（文字列値使用）
                    regime_value = evaluation.market_conditions.get("regime_value", None)

                    self.trade_tracker.record_entry(
                        order_id=result.order_id,
                        side=side,
                        amount=amount,
                        price=price,
                        timestamp=trade_timestamp,  # Phase 56.3: バックテスト時刻使用
                        strategy=getattr(evaluation, "strategy_name", "unknown"),
                        regime=regime_value,  # Phase 51.8-10: レジーム情報（文字列）
                        ml_prediction=getattr(evaluation, "ml_prediction", None),  # Phase 57.12
                        ml_confidence=getattr(evaluation, "ml_confidence", None),  # Phase 57.12
                        adjusted_confidence=getattr(
                            evaluation, "adjusted_confidence", None
                        ),  # Phase 59.3: 調整済み信頼度
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ TradeTracker記録失敗: {e}")

            # Phase 56.3: クールダウン時刻更新（バックテスト時刻使用）
            self.last_order_time = trade_timestamp

            return result

        except Exception as e:
            self.logger.error(f"❌ バックテスト実行失敗: {e}")
            raise

    # Phase 64: _ensure_minimum_trade_size は
    # order_strategy.py (OrderStrategy) に移動

    def get_trading_statistics(self) -> Dict[str, Union[int, float, str]]:
        """
        取引統計情報取得

        Returns:
            取引統計情報
        """
        return {
            "mode": self.mode,
            "executed_trades": self.executed_trades,
            "session_pnl": self.session_pnl,
            "current_balance": self.current_balance,
            "virtual_positions": len(self.virtual_positions) if self.mode == "paper" else 0,
            "virtual_balance": self.virtual_balance if self.mode == "paper" else 0.0,
        }

    def update_balance(self, new_balance: float) -> None:
        """残高更新"""
        self.current_balance = new_balance
        if self.mode in ["paper", "backtest"]:  # Phase 55.9: backtestモード追加
            self.virtual_balance = new_balance

    def get_position_summary(self) -> Dict[str, Any]:
        """ポジションサマリー取得"""
        if self.mode == "paper":
            return {
                "positions": len(self.virtual_positions),
                "latest_trades": self.virtual_positions[-5:] if self.virtual_positions else [],
            }
        else:
            return {"positions": 0, "latest_trades": []}

    def inject_services(
        self,
        order_strategy: Optional[Any] = None,
        stop_manager: Optional[Any] = None,
        position_limits: Optional[Any] = None,
        balance_monitor: Optional[Any] = None,
        position_tracker: Optional[Any] = None,
        data_service: Optional[Any] = None,
        tp_sl_manager: Optional[Any] = None,
        position_restorer: Optional[Any] = None,
    ) -> None:
        """
        関連サービスを注入

        Args:
            order_strategy: OrderStrategyインスタンス
            stop_manager: StopManagerインスタンス
            position_limits: PositionLimitsインスタンス
            balance_monitor: BalanceMonitorインスタンス
            position_tracker: PositionTrackerインスタンス (Phase 42)
            data_service: DataServiceインスタンス (Phase 54.6: ATR取得Level 2用)
            tp_sl_manager: TPSLManagerインスタンス (Phase 64)
            position_restorer: PositionRestorerインスタンス (Phase 64)
        """
        if order_strategy:
            self.order_strategy = order_strategy
        if stop_manager:
            self.stop_manager = stop_manager
        if position_limits:
            self.position_limits = position_limits
        if balance_monitor:
            self.balance_monitor = balance_monitor
        if position_tracker:
            # Phase 64.3: fallbackに蓄積された既存データをtrackerに移行
            if self._virtual_positions_fallback:
                position_tracker.virtual_positions.extend(self._virtual_positions_fallback)
                self._virtual_positions_fallback.clear()
            self.position_tracker = position_tracker
        if data_service:
            self.data_service = data_service
        if tp_sl_manager:
            self.tp_sl_manager = tp_sl_manager
        if position_restorer:
            self.position_restorer = position_restorer

    # ========================================
    # Phase 46: 統合TP/SL・トレーリングストップ削除（デイトレード特化）
    # ========================================
    # Phase 42.1統合TP/SL・Phase 42.2トレーリングストップを削除
    # デイトレード特化設計では不要なため、個別TP/SL配置に回帰

    async def check_stop_conditions(self) -> Optional[ExecutionResult]:
        """
        ストップ条件チェック（StopManagerに委譲）
        Phase 61.9: TP/SL自動執行検知を追加

        Returns:
            ExecutionResult: ストップ実行結果（実行しない場合はNone）
        """
        # Phase 63: Bug 6修正 - virtual_positions整合性チェック
        # 実ポジションが0件なのにvirtual_positionsにTP/SLエントリがある場合はクリーンアップ
        actual_positions = None  # Phase 63: API呼び出し結果を再利用するための変数
        if self.mode == "live" and self.bitbank_client:
            try:
                actual_positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")

                if not actual_positions and self.virtual_positions:
                    tp_sl_entries = [
                        v
                        for v in self.virtual_positions
                        if v.get("tp_order_id") or v.get("sl_order_id")
                    ]
                    if tp_sl_entries:
                        self.logger.info(
                            f"🧹 Phase 63: virtual_positions整合性クリーンアップ - "
                            f"{len(tp_sl_entries)}件の孤立エントリ削除"
                        )
                        self.virtual_positions[:] = [
                            v
                            for v in self.virtual_positions
                            if not (v.get("tp_order_id") or v.get("sl_order_id"))
                        ]
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 63: 整合性チェックエラー: {e}")
                actual_positions = None

        # Phase 61.9: 自動執行検知（毎サイクル先頭、ライブモードのみ）
        if self.mode == "live" and self.bitbank_client and self.stop_manager:
            try:
                # Phase 63: actual_positionsをBug 6で取得済みなら再利用
                if actual_positions is None:
                    actual_positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")
                detected = await self.stop_manager.detect_auto_executed_orders(
                    virtual_positions=self.virtual_positions,
                    actual_positions=actual_positions,
                    bitbank_client=self.bitbank_client,
                )
                # 検知されたポジションをvirtual_positionsから削除
                if detected:
                    for exec_info in detected:
                        order_id = exec_info.get("order_id")
                        exec_type = exec_info.get("execution_type", "exit")
                        strategy_name = exec_info.get("strategy_name", "unknown")
                        pnl = exec_info.get("pnl", 0)

                        if order_id:
                            # order_idでポジション削除
                            self.virtual_positions[:] = [
                                p for p in self.virtual_positions if p.get("order_id") != order_id
                            ]
                            self.logger.info(
                                f"🗑️ Phase 61.9: 自動執行ポジション削除 - order_id={order_id}"
                            )

                        # Phase 62.18: 取引履歴にexit記録を追加（order_idがなくても記録）
                        if self.trade_recorder:
                            try:
                                # trade_type変換: take_profit→tp, stop_loss→sl
                                trade_type = "tp" if exec_type == "take_profit" else "sl"
                                exit_side = exec_info.get("side", "unknown")
                                # 決済は反対売買なので反転
                                record_side = "sell" if exit_side == "buy" else "buy"

                                # 一意なorder_id生成（なければtp/sl_order_idを使用）
                                record_order_id = (
                                    order_id
                                    or exec_info.get("executed_order_id")
                                    or f"auto_{exec_type}_{exec_info.get('tp_order_id', '') or exec_info.get('sl_order_id', '')}"
                                )

                                self.trade_recorder.record_trade(
                                    trade_type=trade_type,
                                    side=record_side,
                                    amount=exec_info.get("amount", 0),
                                    price=exec_info.get("exit_price", 0),
                                    pnl=pnl,
                                    order_id=record_order_id,
                                    notes=f"Phase 62.18: {exec_type} - {strategy_name}",
                                )
                                self.logger.info(
                                    f"📝 Phase 62.18: exit記録追加 - type={trade_type}, pnl={pnl:.0f}円, strategy={strategy_name}"
                                )
                            except Exception as e:
                                self.logger.warning(f"⚠️ Phase 62.18: exit記録失敗: {e}")
                        else:
                            self.logger.warning(
                                f"⚠️ Phase 62.18: trade_recorder未初期化のためexit記録スキップ"
                            )
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 61.9: 自動執行検知エラー: {e}")

        # Phase 63: Bug 3修正 - pending_verificationsの期限到来分を処理
        if self.mode == "live" and self.tp_sl_manager:
            try:
                # Phase 64.4: virtual_positions/position_tracker引数追加
                await self.tp_sl_manager.process_pending_verifications(
                    bitbank_client=self.bitbank_client,
                    virtual_positions=self.virtual_positions,
                    position_tracker=self.position_tracker,
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 63: pending_verifications処理エラー: {e}")

        # Phase 63.6: TP/SL健全性定期チェック（10分間隔）
        if self.mode == "live" and self.bitbank_client and self.tp_sl_manager:
            try:
                await self.tp_sl_manager.periodic_tp_sl_check(
                    virtual_positions=self.virtual_positions,
                    bitbank_client=self.bitbank_client,
                    position_tracker=self.position_tracker,
                    mode=self.mode,
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 63.6: TP/SL定期チェックエラー: {e}")

        # Phase 63.3: Bug 4修正 - 孤児ポジション定期スキャン（30分間隔）
        if self.mode == "live" and self.bitbank_client and self.position_restorer:
            try:
                await self.position_restorer.scan_orphan_positions(
                    virtual_positions=self.virtual_positions,
                    bitbank_client=self.bitbank_client,
                    tp_sl_manager=self.tp_sl_manager,
                )
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 63.3: 孤児スキャンエラー: {e}")

        if self.stop_manager:
            return await self.stop_manager.check_stop_conditions(
                self.virtual_positions,
                self.bitbank_client,
                self.mode,
                self.executed_trades,
                self.session_pnl,
            )
        return None

    # Phase 64: _calculate_tp_sl_for_live_trade は tp_sl_manager.py (TPSLManager) に移動

    # Phase 64: _place_tp_with_retry / _place_sl_with_retry / _cleanup_old_tp_sl_before_entry は
    # 呼び出し元で直接 tp_sl_manager のメソッドを呼び出すようにインライン化

    # Phase 64: _rollback_entry は
    # tp_sl_manager.py (TPSLManager) に移動

    # Phase 64: _execute_maker_order / _wait_for_maker_fill は
    # order_strategy.py (OrderStrategy) に移動

    # Phase 64: _schedule_tp_sl_verification / _process_pending_verifications /
    # _periodic_tp_sl_check / _scan_orphan_positions は
    # 呼び出し元で直接 tp_sl_manager / position_restorer のメソッドを呼び出すようにインライン化
