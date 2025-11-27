"""
取引実行サービス - ExecutionServiceProtocol実装
Phase 52.4-B完了 - Atomic Entry Pattern・TP/SL設定完全見直し

ライブ/ペーパー/バックテストモード対応の取引実行サービス。
BitbankClient.create_orderを使用した実際の注文実行機能を提供。

主要機能:
  - Atomic Entry Pattern（Entry/TP/SL一体化・全成功 or 全ロールバック）
  - 3段階ATRフォールバック（evaluation → DataService → fallback_atr）
  - 取引履歴記録（TradeRecorder・TradeTracker）
  - 証拠金残高チェック・ポジション制限

Phase履歴:
  - Phase 52.4-B: Atomic Entry Pattern・TP/SL設定完全見直し
  - Phase 47: 取引履歴記録システム
  - Phase 46: デイトレード特化・統合TP/SL削除
"""

from dataclasses import replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from tax.trade_history_recorder import TradeHistoryRecorder

from ...backtest.reporter import TradeTracker
from ...core.config import get_threshold, load_config
from ...core.exceptions import CryptoBotError
from ...core.logger import get_logger
from ...core.reporting.discord_notifier import DiscordManager
from ...data.bitbank_client import BitbankClient
from ..core import ExecutionMode, ExecutionResult, OrderStatus, TradeEvaluation
from .atomic_entry_manager import AtomicEntryManager
from .tp_sl_calculator import TPSLCalculator


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
        self.trade_history = []

        # Phase 47: 取引履歴記録システム
        try:
            self.trade_recorder = TradeHistoryRecorder()
        except Exception as e:
            self.logger.warning(f"⚠️ TradeHistoryRecorder初期化失敗: {e}")
            self.trade_recorder = None

        # Phase 52.4-B: バックテストレポート用取引追跡
        try:
            self.trade_tracker = TradeTracker()
        except Exception as e:
            self.logger.warning(f"⚠️ TradeTracker初期化失敗: {e}")
            self.trade_tracker = None

        # ペーパートレード用
        self.virtual_positions = []

        # Phase 29.6: クールダウン管理
        self.last_order_time = None

        # Phase 30: 指値注文タイムアウト管理
        self.pending_limit_orders: List[Dict[str, Any]] = []

        # モード別初期残高取得（Phase 23一元管理対応）
        config = load_config("config/core/unified.yaml")
        # mode_balancesから該当モードの初期残高を取得
        mode_balances = getattr(config, "mode_balances", {})
        mode_balance_config = mode_balances.get(self.mode, {})
        self.virtual_balance = mode_balance_config.get("initial_balance", 10000.0)

        # Phase 52.4-B: Discord通知初期化（ライブモードのみ）
        self.discord_notifier = None
        if self.mode == "live":
            try:
                self.discord_notifier = DiscordManager()
                self.logger.info("✅ Discord通知システム初期化完了（残高アラート有効）")
            except Exception as e:
                self.logger.warning(f"⚠️ Discord通知初期化失敗: {e} - 残高アラートは無効化されます")

        # 関連サービスの初期化（後で注入される）
        self.order_strategy = None
        self.stop_manager = None
        self.position_limits = None
        self.balance_monitor = None
        self.position_tracker = None  # Phase 42: 統合TP/SL用ポジション追跡
        # Phase 52.5: TP/SLCalculator デフォルト初期化（テスト互換性）
        self.tp_sl_calculator = TPSLCalculator(
            logger=self.logger,
            data_service=None,  # inject_services()で後から設定可能
        )
        self.atomic_entry_manager = None  # Phase 52.4-B: Atomic Entry管理サービス

        self.logger.info(f"✅ ExecutionService初期化完了 - モード: {mode}")

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

            # Phase 52.4-B: 証拠金残高チェック（ライブモードのみ・Container exit回避）
            if self.balance_monitor:
                balance_check = await self.balance_monitor.validate_margin_balance(
                    mode=self.mode,
                    bitbank_client=self.bitbank_client,
                    discord_notifier=self.discord_notifier,
                )
                if not balance_check["sufficient"]:
                    self.logger.info(
                        "💤 証拠金不足のため取引スキップ（Container exit回避） - "
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
                # Phase 52.4-B: レジーム情報を取得（market_conditionsから）
                regime = evaluation.market_conditions.get("regime", None)

                position_check_result = await self.position_limits.check_limits(
                    evaluation,
                    self.virtual_positions,
                    self.last_order_time,
                    self.virtual_balance if self.mode == "paper" else self.current_balance,
                    regime=regime,  # Phase 52.4-B: レジーム別制限適用
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
            evaluation = self._ensure_minimum_trade_size(evaluation)

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
            symbol = get_threshold("trading_constraints.currency_pair", "BTC/JPY")
            side = evaluation.side  # "buy" or "sell"
            amount = float(evaluation.position_size)

            # 指値注文オプション機能（Phase 26）
            if self.order_strategy:
                order_execution_config = await self.order_strategy.get_optimal_execution_config(
                    evaluation, self.bitbank_client
                )
            else:
                # フォールバック: デフォルト注文タイプ使用
                order_execution_config = {
                    "order_type": get_threshold("trading_constraints.default_order_type", "market"),
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

            # 実際の注文実行（Phase 55.8: async修正）
            order_result = await self.bitbank_client.create_order(**order_params)

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
                filled_amount=float(
                    order_result.get("filled_amount") or order_result.get("amount") or 0
                ),
                error_message=None,
                side=side,
                fee=float(order_result.get("fee") or 0),
                status=(OrderStatus.FILLED if order_type == "market" else OrderStatus.SUBMITTED),
                notes=f"{order_type}注文実行 - {order_execution_config.get('strategy', 'default')}",
            )

            # 統計更新
            self.executed_trades += 1

            # Phase 47: 取引履歴記録（ライブモード）
            if self.trade_recorder:
                try:
                    self.trade_recorder.record_trade(
                        trade_type="entry",
                        side=side,
                        amount=result.filled_amount,
                        price=result.filled_price,
                        fee=result.fee,
                        order_id=result.order_id,
                        notes=f"Live {order_type}注文 - {order_execution_config.get('strategy', 'default')}",
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ 取引履歴記録失敗: {e}")

            # Phase 52.4-B: TradeTracker記録（バックテストレポート用）
            self._record_trade_tracker_entry(
                evaluation=evaluation,
                order_id=result.order_id,
                side=side,
                amount=result.filled_amount,
                price=result.filled_price,
                strategy=order_execution_config.get("strategy", "unknown"),
            )

            # Phase 52.4-B: クールダウン時刻更新
            self._update_cooldown_timestamp()

            # ログ出力（注文タイプ別）
            if order_type == "market":
                self.logger.info(
                    f"✅ 成行注文実行成功: 注文ID={result.order_id}, 手数料: Taker(0.12%)"
                )
            else:
                self.logger.info(
                    f"✅ 指値注文投入成功: 注文ID={result.order_id}, 予想手数料: Maker(-0.02%)"
                )

            # Phase 29.6: ライブモードでもポジション追跡（バグ修正）
            # Phase 52.4-B: TP/SL再計算メソッド抽出（可読性向上・保守性向上）
            actual_filled_price = result.filled_price or result.price

            # TP/SL再計算（3段階ATRフォールバック）
            try:
                final_tp, final_sl = await self.tp_sl_calculator.calculate(
                    evaluation, result, side, amount
                )
            except CryptoBotError as e:
                # ATR取得失敗・TP/SL再計算失敗時のエントリー中止
                self.logger.error(f"❌ Phase 52.4-B: TP/SL再計算エラー - {e}")
                return ExecutionResult(
                    success=False,
                    error_message=str(e),
                    mode=ExecutionMode.LIVE,
                    order_id=None,
                    side=side,
                    amount=0.0,
                    price=0.0,
                    status=OrderStatus.FAILED,
                    timestamp=datetime.now(),
                )

            # virtual_positionsに追加
            live_position = {
                "order_id": result.order_id,
                "side": side,
                "amount": amount,
                "price": actual_filled_price,
                "timestamp": datetime.now(),
                "take_profit": final_tp,
                "stop_loss": final_sl,
                "tp_order_id": None,  # Phase 52.4-B.1: TP注文ID追跡用
                "sl_order_id": None,  # Phase 52.4-B.1: SL注文ID追跡用
            }
            self.virtual_positions.append(live_position)

            # Phase 52.4-B: 古い注文クリーンアップ（bitbank 30件制限対策）
            if self.stop_manager:
                try:
                    symbol = get_threshold("trading_constraints.currency_pair", "BTC/JPY")
                    # Phase 52.4-B: クリーンアップ設定をthresholds.yamlから取得
                    max_age_hours = get_threshold("position_management.cleanup.max_age_hours", 24)
                    threshold_count = get_threshold(
                        "position_management.cleanup.threshold_count", 25
                    )

                    cleanup_result = await self.stop_manager.cleanup_old_unfilled_orders(
                        symbol=symbol,
                        bitbank_client=self.bitbank_client,
                        virtual_positions=self.virtual_positions,
                        max_age_hours=max_age_hours,
                        threshold_count=threshold_count,
                    )
                    if cleanup_result["cancelled_count"] > 0:
                        self.logger.info(
                            "🧹 Phase 52.4-B: 古い孤児注文クリーンアップ実行 - "
                            f"{cleanup_result['cancelled_count']}件キャンセル "
                            f"（{cleanup_result['order_count']}件中）"
                        )
                except Exception as e:
                    # クリーンアップ失敗しても処理継続（TP/SL配置を優先）
                    self.logger.warning(
                        f"⚠️ Phase 52.4-B: 古い注文クリーンアップ失敗（処理継続）: {e}"
                    )

            # Phase 52.4-B: エントリー前の同一側TP/SL注文クリーンアップ
            if self.atomic_entry_manager:
                try:
                    await self.atomic_entry_manager.cleanup_old_tp_sl_before_entry(
                        side=side,
                        symbol=symbol,
                        entry_order_id=result.order_id,
                        virtual_positions=self.virtual_positions,
                    )
                except Exception as e:
                    # クリーンアップ失敗してもエントリーは継続（Phase 52.4-B思想維持）
                    self.logger.warning(
                        f"⚠️ Phase 52.4-B: エントリー前クリーンアップ失敗（処理継続）: {e}"
                    )

            # Phase 52.4-B: Atomic Entry Pattern（Entry/TP/SL一体化・全成功 or 全ロールバック）
            if self.stop_manager and final_tp and final_sl:
                # PositionTrackerに追加（統合ID管理なし）
                if self.position_tracker:
                    self.position_tracker.add_position(
                        order_id=result.order_id,
                        side=side,
                        amount=amount,
                        price=actual_filled_price,
                    )

                # Phase 52.4-B: Atomic Entry Pattern - TP/SL注文ID初期化
                tp_order_id = None
                sl_order_id = None

                try:
                    # Step 1/3: エントリー注文実行済み
                    self.logger.info(
                        "✅ Phase 52.4-B Step 1/3: エントリー成功 - "
                        f"ID: {result.order_id}, 価格: {actual_filled_price:.0f}円"
                    )

                    # Step 2/3: TP注文配置（リトライ付き）
                    tp_order = await self.atomic_entry_manager.place_tp_with_retry(
                        side=side,
                        amount=amount,
                        entry_price=actual_filled_price,
                        take_profit_price=final_tp,
                        symbol=symbol,
                        max_retries=3,
                    )
                    if not tp_order:
                        raise Exception("TP注文配置失敗（3回リトライ後）")

                    tp_order_id = tp_order.get("order_id")
                    self.logger.info(
                        "✅ Phase 52.4-B Step 2/3: TP配置成功 - "
                        f"ID: {tp_order_id}, 価格: {final_tp:.0f}円"
                    )

                    # Step 3/3: SL注文配置（リトライ付き）
                    sl_order = await self.atomic_entry_manager.place_sl_with_retry(
                        side=side,
                        amount=amount,
                        entry_price=actual_filled_price,
                        stop_loss_price=final_sl,
                        symbol=symbol,
                        max_retries=3,
                    )
                    if not sl_order:
                        raise Exception("SL注文配置失敗（3回リトライ後）")

                    sl_order_id = sl_order.get("order_id")
                    self.logger.info(
                        "✅ Phase 52.4-B Step 3/3: SL配置成功 - "
                        f"ID: {sl_order_id}, 価格: {final_sl:.0f}円"
                    )

                    # 全成功 → TP/SL注文ID保存
                    self.logger.info("🎉 Phase 52.4-B: Atomic Entry完了 - Entry/TP/SL すべて成功")

                    # PositionTrackerに注文IDを保存
                    if self.position_tracker:
                        try:
                            self.position_tracker.update_position_tp_sl(
                                order_id=result.order_id,
                                tp_order_id=tp_order_id,
                                sl_order_id=sl_order_id,
                            )
                            self.logger.debug(
                                "💾 Phase 52.4-B: TP/SL注文ID保存完了 - "
                                f"TP: {tp_order_id}, SL: {sl_order_id}"
                            )
                        except Exception as e:
                            self.logger.warning(f"⚠️ Phase 52.4-B: TP/SL注文ID保存失敗（継続）: {e}")

                    # virtual_positionsにも保存（stop_manager互換性維持）
                    live_position["tp_order_id"] = tp_order_id
                    live_position["sl_order_id"] = sl_order_id

                except Exception as e:
                    # Phase 52.4-B: Atomic Entry失敗 → 全ロールバック
                    self.logger.error(f"❌ Phase 52.4-B: Atomic Entry失敗 - ロールバック開始: {e}")

                    # ロールバック実行（TP/SL/Entry注文をすべてキャンセル）
                    rollback_status = await self.atomic_entry_manager.rollback_entry(
                        entry_order_id=result.order_id,
                        tp_order_id=tp_order_id,
                        sl_order_id=sl_order_id,
                        symbol=symbol,
                        error=e,
                    )

                    # Phase 52.4-B: ロールバック失敗時の追加処理
                    if rollback_status.get("manual_intervention_required"):
                        self.logger.critical(
                            "🚨 CRITICAL: 手動介入が必要です - "
                            f"失敗注文ID: {rollback_status['failed_cancellations']}"
                        )

                    # virtual_positionsから削除（不完全なポジション削除）
                    self.virtual_positions = [
                        p for p in self.virtual_positions if p.get("order_id") != result.order_id
                    ]

                    # PositionTrackerからも削除
                    if self.position_tracker:
                        try:
                            self.position_tracker.remove_position(result.order_id)
                        except Exception:
                            pass  # 削除失敗は無視

                    # エラー結果返却
                    return ExecutionResult(
                        success=False,
                        order_id=result.order_id,
                        side=side,
                        amount=amount,
                        price=actual_filled_price,
                        error_message=f"Phase 52.4-B Atomic Entry失敗（ロールバック完了）: {e}",
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
                    # Phase 55.8: async修正
                    ticker = await self.bitbank_client.fetch_ticker("BTC/JPY")
                    if ticker and "last" in ticker:
                        price = float(ticker["last"])
                        self.logger.info(f"📊 ペーパートレード実価格取得: {price:.0f}円")
                    else:
                        price = get_threshold("trading.fallback_btc_jpy", 16500000.0)
                        self.logger.warning(
                            f"⚠️ ticker取得失敗、フォールバック価格使用: {price:.0f}円"
                        )
                except Exception as e:
                    price = get_threshold("trading.fallback_btc_jpy", 16500000.0)
                    self.logger.warning(
                        f"⚠️ 価格取得エラー、フォールバック価格使用: {price:.0f}円 - {e}"
                    )
            elif price == 0:
                price = get_threshold("trading.fallback_btc_jpy", 16500000.0)
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

            # 仮想ポジション記録（Phase 52.4-B: TP/SL価格追加）
            virtual_position = {
                "order_id": virtual_order_id,
                "side": side,
                "amount": amount,
                "price": price,
                "timestamp": datetime.now(),
                "take_profit": getattr(evaluation, "take_profit", None),
                "stop_loss": getattr(evaluation, "stop_loss", None),
                "strategy_name": getattr(evaluation, "strategy_name", "unknown"),
            }
            self.virtual_positions.append(virtual_position)

            # Phase 46: ペーパートレード - シンプルなポジション追加のみ（統合TP/SL削除）
            if self.position_tracker:
                try:
                    self.position_tracker.add_position(
                        order_id=virtual_order_id,
                        side=side,
                        amount=amount,
                        price=price,
                    )
                    self.logger.debug(
                        f"📊 Phase 46: ペーパーポジション追加 - ID: {virtual_order_id}, "
                        f"価格: {price:.0f}円, 数量: {amount:.6f} BTC"
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ ペーパーポジション追加エラー: {e}")

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

            # Phase 52.4-B: TradeTracker記録（バックテストレポート用）
            self._record_trade_tracker_entry(
                evaluation=evaluation,
                order_id=virtual_order_id,
                side=side,
                amount=amount,
                price=price,
                strategy=virtual_position.get("strategy_name", "unknown"),
            )

            # Phase 52.4-B: クールダウン時刻更新
            self._update_cooldown_timestamp()

            # ログ出力（Phase 52.4-B: TP/SL価格表示追加）
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
        バックテスト実行（Phase 52.4-B: ライブモード完全一致化）
        Phase 52.4-B-J4-D: 残高管理追加（エントリー時資金控除・不足時拒否）
        """
        try:
            # バックテスト用の簡易実行
            side = evaluation.side
            amount = float(evaluation.position_size)
            price = float(getattr(evaluation, "entry_price", 0))

            # Phase 52.4-B-J4-D: 必要証拠金計算（bitbank信用取引は4倍レバレッジ固定）
            order_total = price * amount  # 注文総額
            required_margin = order_total / 4  # 必要証拠金（25%）

            # Phase 52.4-B-J4-D: 残高チェック
            if self.virtual_balance < required_margin:
                self.logger.warning(
                    "⚠️ Phase 52.4-B-J4-D: 残高不足により取引拒否 - "
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

            # Phase 52.4-B-J4-D: エントリー時に証拠金を控除
            self.virtual_balance -= required_margin

            # Phase 52.4-B-J4-E: 手数料シミュレーション（Maker: -0.02%リベート）
            fee_rate = -0.0002  # Maker手数料（指値注文）
            fee_amount = order_total * fee_rate  # 負の値（リベート）
            self.virtual_balance -= fee_amount  # 負の手数料なので残高増加

            self.logger.info(
                "💰 Phase 52.4-B-J4-D/E: エントリー処理 - "
                f"証拠金控除: -¥{required_margin:,.0f}, "
                f"手数料リベート: +¥{abs(fee_amount):,.2f} → 残高: ¥{self.virtual_balance:,.0f}"
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

            # Phase 52.4-B: 仮想ポジション記録（TP/SL価格追加 - ライブモード一致化）
            virtual_position = {
                "order_id": virtual_order_id,
                "side": side,
                "amount": amount,
                "price": price,
                "timestamp": datetime.now(),
                "take_profit": getattr(evaluation, "take_profit", None),
                "stop_loss": getattr(evaluation, "stop_loss", None),
                "strategy_name": getattr(evaluation, "strategy_name", "unknown"),
            }
            self.virtual_positions.append(virtual_position)

            # Phase 52.4-B: PositionTracker登録（ポジション管理統一）
            if self.position_tracker:
                try:
                    self.position_tracker.add_position(
                        order_id=virtual_order_id,
                        side=side,
                        amount=amount,
                        price=price,
                    )
                    self.logger.debug(
                        f"📊 Phase 52.4-B: バックテストポジション追加 - ID: {virtual_order_id}, "
                        f"価格: {price:.0f}円, TP: {virtual_position.get('take_profit'):.0f}円, "
                        f"SL: {virtual_position.get('stop_loss'):.0f}円"
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ バックテストポジション追加エラー: {e}")

            # 統計更新
            self.executed_trades += 1

            # Phase 52.4-B: TradeTracker記録（バックテストレポート用）
            self._record_trade_tracker_entry(
                evaluation=evaluation,
                order_id=result.order_id,
                side=side,
                amount=amount,
                price=price,
                strategy=getattr(evaluation, "strategy_name", "unknown"),
            )

            # Phase 52.4-B: クールダウン時刻更新（一貫性向上）
            self._update_cooldown_timestamp()

            return result

        except Exception as e:
            self.logger.error(f"❌ バックテスト実行失敗: {e}")
            raise

    def _ensure_minimum_trade_size(self, evaluation: TradeEvaluation) -> TradeEvaluation:
        """
        最小ロットサイズを保証する（動的ポジションサイジング対応）

        Args:
            evaluation: 元の取引評価結果

        Returns:
            調整されたTradeEvaluation
        """
        try:
            # 動的ポジションサイジングが有効かチェック
            dynamic_enabled = get_threshold(
                "position_management.dynamic_position_sizing.enabled", False
            )

            if not dynamic_enabled:
                return evaluation  # 従来通り変更なし

            # 最小取引サイズ取得
            min_trade_size = get_threshold("position_management.min_trade_size", 0.0001)

            # 現在のポジションサイズと比較
            current_position_size = float(getattr(evaluation, "position_size", 0))

            if current_position_size < min_trade_size:
                # 最小ロット保証適用
                self.logger.info(
                    f"📏 最小ロット保証適用: {current_position_size:.6f} -> {min_trade_size:.6f} BTC"
                )

                # evaluationのposition_sizeを更新（immutableなdataclassの場合を考慮）
                if hasattr(evaluation, "__dict__"):
                    evaluation.position_size = min_trade_size
                else:
                    # dataclassの場合は新しいインスタンスを作成
                    evaluation = replace(evaluation, position_size=min_trade_size)

            return evaluation

        except Exception as e:
            self.logger.error(f"最小ロット保証処理エラー: {e}")
            return evaluation  # エラー時は元のevaluationを返す

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
        if self.mode == "paper":
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
    ) -> None:
        """
        関連サービスを注入

        Args:
            order_strategy: OrderStrategyインスタンス
            stop_manager: StopManagerインスタンス
            position_limits: PositionLimitsインスタンス
            balance_monitor: BalanceMonitorインスタンス
            position_tracker: PositionTrackerインスタンス (Phase 42)
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
            self.position_tracker = position_tracker

        # Phase 52.4-B: 新サービス初期化
        if not self.tp_sl_calculator:
            self.tp_sl_calculator = TPSLCalculator(
                logger=self.logger,
                data_service=getattr(self, "data_service", None),
            )
        if not self.atomic_entry_manager and stop_manager:
            self.atomic_entry_manager = AtomicEntryManager(
                logger=self.logger,
                bitbank_client=self.bitbank_client,
                stop_manager=stop_manager,
            )

    # ========================================
    # Phase 52.4-B: ヘルパーメソッド（重複コード統合）
    # ========================================

    def _record_trade_tracker_entry(
        self,
        evaluation: TradeEvaluation,
        order_id: str,
        side: str,
        amount: float,
        price: float,
        strategy: str,
    ) -> None:
        """
        Phase 52.4-B: TradeTracker記録ヘルパー（3モード共通化）

        Args:
            evaluation: 取引評価（レジーム情報取得用）
            order_id: 注文ID
            side: 取引方向
            amount: 数量
            price: 価格
            strategy: 戦略名
        """
        if not self.trade_tracker:
            return

        try:
            # Phase 52.4-B-10: レジーム情報取得・記録（文字列値使用）
            regime_value = evaluation.market_conditions.get("regime_value", None)

            self.trade_tracker.record_entry(
                order_id=order_id,
                side=side,
                amount=amount,
                price=price,
                timestamp=datetime.now(),
                strategy=strategy,
                regime=regime_value,
            )
        except Exception as e:
            self.logger.warning(f"⚠️ TradeTracker記録失敗: {e}")

    def _update_cooldown_timestamp(self) -> None:
        """Phase 52.4-B: クールダウン時刻更新（3モード共通化）"""
        self.last_order_time = datetime.now()

    # ========================================
    # Phase 52.4-B: ストップ条件チェック
    # ========================================

    async def check_stop_conditions(self) -> Optional[ExecutionResult]:
        """
        ストップ条件チェック（StopManagerに委譲）

        Returns:
            ExecutionResult: ストップ実行結果（実行しない場合はNone）
        """
        if self.stop_manager:
            return await self.stop_manager.check_stop_conditions(
                self.virtual_positions,
                self.bitbank_client,
                self.mode,
                self.executed_trades,
                self.session_pnl,
            )
        return None
