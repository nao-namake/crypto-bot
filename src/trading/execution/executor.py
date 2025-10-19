"""
取引実行サービス - ExecutionServiceProtocol実装
Phase 38リファクタリング - メイン実行ロジック

ライブ/ペーパーモードを自動判別し、適切な取引実行を行う。
BitbankClient.create_orderを使用した実際の注文実行機能を提供。

Silent Failure修正済み: TradeEvaluationのsideフィールドを正しく使用。
"""

import asyncio
from dataclasses import replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ...core.config import get_threshold, load_config
from ...core.exceptions import CryptoBotError
from ...core.logger import get_logger
from ...core.reporting.discord_notifier import DiscordManager
from ...data.bitbank_client import BitbankClient
from ..core import ExecutionMode, ExecutionResult, OrderStatus, TradeEvaluation


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

        # Phase 37: Discord通知初期化（ライブモードのみ）
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

            # Phase 37: 証拠金残高チェック（ライブモードのみ・Container exit回避）
            if self.balance_monitor:
                balance_check = await self.balance_monitor.validate_margin_balance(
                    mode=self.mode,
                    bitbank_client=self.bitbank_client,
                    discord_notifier=self.discord_notifier,
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
                position_check_result = await self.position_limits.check_limits(
                    evaluation,
                    self.virtual_positions,
                    self.last_order_time,
                    self.virtual_balance if self.mode == "paper" else self.current_balance,
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

            # Phase 29.6: クールダウン時刻更新
            self.last_order_time = datetime.now()

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
            # Phase 38.7: 実約定価格ベースでTP/SL再計算（SL距離5x誤差修正）
            actual_filled_price = result.filled_price or result.price

            # 実約定価格でTP/SL価格を再計算
            recalculated_tp = None
            recalculated_sl = None

            if actual_filled_price > 0 and evaluation.take_profit and evaluation.stop_loss:
                from ...strategies.utils.strategy_utils import RiskManager

                # ATR値とATR履歴を取得（evaluationのmarket_conditionsから）
                market_conditions = getattr(evaluation, "market_conditions", {})
                market_data = market_conditions.get("market_data", {})

                current_atr = None
                atr_history = None

                # 15m足ATR取得試行
                if "15m" in market_data:
                    df_15m = market_data["15m"]
                    if "atr_14" in df_15m.columns and len(df_15m) > 0:
                        current_atr = float(df_15m["atr_14"].iloc[-1])
                        atr_history = df_15m["atr_14"].dropna().tail(20).tolist()

                # 4h足ATRフォールバック
                if not current_atr and "4h" in market_data:
                    df_4h = market_data["4h"]
                    if "atr_14" in df_4h.columns and len(df_4h) > 0:
                        current_atr = float(df_4h["atr_14"].iloc[-1])

                if current_atr and current_atr > 0:
                    # 実約定価格ベースで再計算
                    config = {"take_profit_ratio": 2.5}  # デフォルト設定
                    recalculated_sl, recalculated_tp = RiskManager.calculate_stop_loss_take_profit(
                        side, actual_filled_price, current_atr, config, atr_history
                    )

                    # 再計算成功時、ログ出力
                    if recalculated_sl and recalculated_tp:
                        original_sl = evaluation.stop_loss
                        original_tp = evaluation.take_profit
                        sl_diff = abs(recalculated_sl - original_sl)
                        tp_diff = abs(recalculated_tp - original_tp)

                        self.logger.info(
                            f"🔄 Phase 38.7: 実約定価格ベースTP/SL再計算完了 - "
                            f"約定価格={actual_filled_price:.0f}円 | "
                            f"SL: {original_sl:.0f}円→{recalculated_sl:.0f}円 (差{sl_diff:.0f}円) | "
                            f"TP: {original_tp:.0f}円→{recalculated_tp:.0f}円 (差{tp_diff:.0f}円)"
                        )
                    else:
                        # Phase 38.7: 再計算失敗時のエラーハンドリング
                        self.logger.warning(
                            f"⚠️ Phase 38.7: TP/SL再計算失敗（RiskManager戻り値None） - "
                            f"ATR={current_atr:.0f}円・元のTP/SL使用継続"
                        )
                else:
                    # Phase 38.7: ATR取得失敗時のエラーハンドリング
                    self.logger.warning(
                        f"⚠️ Phase 38.7: ATR取得失敗（current_atr={current_atr}） - "
                        f"実約定価格ベースTP/SL再計算スキップ・元のTP/SL使用継続"
                    )

            # 再計算された値を使用（失敗時は元の値）
            final_tp = recalculated_tp if recalculated_tp else evaluation.take_profit
            final_sl = recalculated_sl if recalculated_sl else evaluation.stop_loss

            live_position = {
                "order_id": result.order_id,
                "side": side,
                "amount": amount,
                "price": actual_filled_price,
                "timestamp": datetime.now(),
                "take_profit": final_tp,
                "stop_loss": final_sl,
            }
            self.virtual_positions.append(live_position)

            # Phase 42: TP/SL配置モード判定（individual/consolidated）
            tp_sl_mode = get_threshold("position_management.tp_sl_mode", "individual")
            self.logger.info(f"🔍 Phase 42デバッグ: tp_sl_mode = '{tp_sl_mode}'")

            if self.stop_manager and final_tp and final_sl:
                # evaluationを再計算値で更新（immutable対応）
                if hasattr(evaluation, "__dict__"):
                    evaluation.take_profit = final_tp
                    evaluation.stop_loss = final_sl
                else:
                    evaluation = replace(evaluation, take_profit=final_tp, stop_loss=final_sl)

                # Phase 42デバッグ: 統合TP/SL条件チェック
                has_tracker = self.position_tracker is not None
                has_strategy = self.order_strategy is not None
                will_use_consolidated = (
                    tp_sl_mode == "consolidated" and has_tracker and has_strategy
                )
                self.logger.info(
                    f"🔍 Phase 42デバッグ: 統合TP/SL判定 - "
                    f"モード={tp_sl_mode}, "
                    f"tracker={'✅' if has_tracker else '❌'}, "
                    f"strategy={'✅' if has_strategy else '❌'}, "
                    f"統合使用={'✅ YES' if will_use_consolidated else '❌ NO (個別モード)'}"
                )

                if tp_sl_mode == "consolidated" and self.position_tracker and self.order_strategy:
                    # Phase 42: 統合TP/SLモード
                    await self._handle_consolidated_tp_sl(
                        live_position, evaluation, side, amount, symbol, actual_filled_price
                    )
                else:
                    # 従来の個別TP/SLモード
                    tp_sl_result = await self.stop_manager.place_tp_sl_orders(
                        evaluation, side, amount, symbol, self.bitbank_client
                    )
                    # TP/SL注文IDをポジションに追加
                    if tp_sl_result.get("tp_order_id"):
                        live_position["tp_order_id"] = tp_sl_result["tp_order_id"]
                    if tp_sl_result.get("sl_order_id"):
                        live_position["sl_order_id"] = tp_sl_result["sl_order_id"]

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

            # 仮想ポジション記録（Phase 28: TP/SL価格追加）
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

            # Phase 42: ペーパートレードでも統合TP/SL対応（整合性維持）
            tp_sl_mode = get_threshold("position_management.tp_sl_mode", "individual")
            if (
                tp_sl_mode == "consolidated"
                and self.position_tracker
                and self.order_strategy
                and virtual_position.get("take_profit")
                and virtual_position.get("stop_loss")
            ):
                try:
                    self.logger.info("🔄 Phase 42: ペーパートレード統合TP/SL処理")

                    # PositionTrackerにポジション追加
                    self.position_tracker.add_position(
                        order_id=virtual_order_id,
                        side=side,
                        amount=amount,
                        price=price,
                        take_profit=virtual_position["take_profit"],
                        stop_loss=virtual_position["stop_loss"],
                        strategy_name=virtual_position["strategy_name"],
                    )

                    # 平均価格更新
                    new_average_price = self.position_tracker.update_average_on_entry(price, amount)
                    total_size = self.position_tracker._total_position_size

                    # 統合TP/SL価格計算（ログ出力用）
                    market_conditions = getattr(evaluation, "market_conditions", {})
                    new_tp_sl = self.order_strategy.calculate_consolidated_tp_sl_prices(
                        average_entry_price=new_average_price,
                        side=side,
                        market_conditions=market_conditions,
                    )

                    self.logger.info(
                        f"📊 Phase 42: ペーパー統合TP/SL - 平均={new_average_price:.0f}円, "
                        f"総数量={total_size:.6f} BTC, TP={new_tp_sl['take_profit_price']:.0f}円, "
                        f"SL={new_tp_sl['stop_loss_price']:.0f}円"
                    )

                    # 仮想統合注文ID保存（ペーパーモード用）
                    consolidated_tp_id = f"paper_tp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    consolidated_sl_id = f"paper_sl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.position_tracker.set_consolidated_tp_sl_ids(
                        tp_order_id=consolidated_tp_id,
                        sl_order_id=consolidated_sl_id,
                        tp_price=new_tp_sl["take_profit_price"],
                        sl_price=new_tp_sl["stop_loss_price"],
                        side=side,
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ ペーパー統合TP/SL処理エラー: {e}")

            # 統計更新
            self.executed_trades += 1

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
        """バックテスト実行"""
        try:
            # バックテスト用の簡易実行
            side = evaluation.side
            amount = float(evaluation.position_size)
            price = float(getattr(evaluation, "entry_price", 0))

            result = ExecutionResult(
                success=True,
                mode=ExecutionMode.PAPER,  # バックテストはペーパーモード扱い
                order_id=f"backtest_{self.executed_trades + 1}",
                price=price,
                amount=amount,
                filled_price=price,
                filled_amount=amount,
                error_message=None,
                side=side,
                fee=0.0,
                status=OrderStatus.FILLED,
            )

            self.executed_trades += 1
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

    async def _handle_consolidated_tp_sl(
        self,
        live_position: Dict[str, Any],
        evaluation: TradeEvaluation,
        side: str,
        amount: float,
        symbol: str,
        entry_price: float,
    ) -> None:
        """
        Phase 42: 統合TP/SL処理（エントリー時）

        新規エントリー時に平均価格を再計算し、既存TP/SLをキャンセルして
        新しい統合TP/SL注文を配置する。

        Args:
            live_position: 現在のポジション情報
            evaluation: 取引評価結果
            side: 注文サイド (buy/sell)
            amount: 数量
            symbol: 取引ペア
            entry_price: エントリー価格
        """
        try:
            self.logger.info("🔄 Phase 42: 統合TP/SL処理開始")

            # 1. PositionTrackerにポジション追加
            tp_price = getattr(evaluation, "take_profit", None)
            sl_price = getattr(evaluation, "stop_loss", None)
            strategy_name = getattr(evaluation, "strategy_name", "unknown")

            self.position_tracker.add_position(
                order_id=live_position["order_id"],
                side=side,
                amount=amount,
                price=entry_price,
                take_profit=tp_price,
                stop_loss=sl_price,
                strategy_name=strategy_name,
            )

            # 2. 平均エントリー価格を更新
            new_average_price = self.position_tracker.update_average_on_entry(entry_price, amount)
            total_position_size = self.position_tracker._total_position_size

            self.logger.info(
                f"📊 平均価格更新完了: {new_average_price:.0f}円 "
                f"(総数量: {total_position_size:.6f} BTC)"
            )

            # 3. 既存の統合TP/SL注文IDを取得
            existing_ids = self.position_tracker.get_consolidated_tp_sl_ids()
            existing_tp_id = existing_ids.get("tp_order_id")
            existing_sl_id = existing_ids.get("sl_order_id")

            # 4. 既存TP/SL注文をキャンセル（存在する場合）
            if existing_tp_id or existing_sl_id:
                consolidate_on_new_entry = get_threshold(
                    "position_management.consolidated.consolidate_on_new_entry", True
                )
                if consolidate_on_new_entry:
                    self.logger.info(
                        f"🗑️ 既存統合TP/SL注文キャンセル開始: TP={existing_tp_id}, SL={existing_sl_id}"
                    )
                    cancel_result = await self.stop_manager.cancel_existing_tp_sl(
                        tp_order_id=existing_tp_id,
                        sl_order_id=existing_sl_id,
                        symbol=symbol,
                        bitbank_client=self.bitbank_client,
                    )
                    self.logger.info(
                        f"✅ 既存TP/SLキャンセル完了: {cancel_result['cancelled_count']}件"
                    )

            # 5. 市場条件を取得（適応型ATR倍率用）
            market_conditions = getattr(evaluation, "market_conditions", {})

            # 6. 平均価格ベースで新しいTP/SL価格を計算
            new_tp_sl_prices = self.order_strategy.calculate_consolidated_tp_sl_prices(
                average_entry_price=new_average_price,
                side=side,
                market_conditions=market_conditions,
            )

            new_tp_price = new_tp_sl_prices["take_profit_price"]
            new_sl_price = new_tp_sl_prices["stop_loss_price"]

            self.logger.info(
                f"🎯 新規統合TP/SL価格計算完了: "
                f"平均={new_average_price:.0f}円, TP={new_tp_price:.0f}円, SL={new_sl_price:.0f}円"
            )

            # 7. 新しい統合TP/SL注文を配置
            place_result = await self.stop_manager.place_consolidated_tp_sl(
                average_price=new_average_price,
                total_amount=total_position_size,
                side=side,
                take_profit_price=new_tp_price,
                stop_loss_price=new_sl_price,
                symbol=symbol,
                bitbank_client=self.bitbank_client,
            )

            # 8. 新しいTP/SL注文IDをPositionTrackerに保存
            new_tp_id = place_result.get("tp_order_id")
            new_sl_id = place_result.get("sl_order_id")

            if new_tp_id or new_sl_id:
                self.position_tracker.set_consolidated_tp_sl_ids(
                    tp_order_id=new_tp_id,
                    sl_order_id=new_sl_id,
                    tp_price=new_tp_price,
                    sl_price=new_sl_price,
                    side=side,
                )
                self.logger.info(
                    f"✅ Phase 42: 統合TP/SL配置完了 - TP: {new_tp_id}, SL: {new_sl_id}"
                )

                # ポジションにも記録（後方互換性維持）
                if new_tp_id:
                    live_position["tp_order_id"] = new_tp_id
                if new_sl_id:
                    live_position["sl_order_id"] = new_sl_id
            else:
                self.logger.warning("⚠️ Phase 42: 統合TP/SL注文ID取得失敗")

        except Exception as e:
            self.logger.error(f"❌ Phase 42: 統合TP/SL処理エラー: {e}", exc_info=True)
            # エラー時は個別TP/SLにフォールバック
            self.logger.warning("⚠️ 個別TP/SLモードにフォールバック")
            try:
                tp_sl_result = await self.stop_manager.place_tp_sl_orders(
                    evaluation, side, amount, symbol, self.bitbank_client
                )
                if tp_sl_result.get("tp_order_id"):
                    live_position["tp_order_id"] = tp_sl_result["tp_order_id"]
                if tp_sl_result.get("sl_order_id"):
                    live_position["sl_order_id"] = tp_sl_result["sl_order_id"]
            except Exception as fallback_error:
                self.logger.error(f"❌ フォールバックTP/SL配置も失敗: {fallback_error}")

    # ========================================
    # Phase 42.2: トレーリングストップ用メソッド
    # ========================================

    async def monitor_trailing_conditions(
        self,
        current_price: float,
    ) -> Dict[str, Any]:
        """
        Phase 42.2: トレーリングストップ条件監視

        含み益が一定水準に達した場合、トレーリングストップを更新する。
        TP超過時はTPをキャンセルして追従を継続する。

        Args:
            current_price: 現在のBTC価格

        Returns:
            Dict: {"trailing_activated": bool, "new_sl_price": float, ...}
        """
        try:
            # トレーリングストップ設定確認
            trailing_config = get_threshold("position_management.stop_loss.trailing", {})

            if not trailing_config.get("enabled", False):
                return {"trailing_activated": False}

            # 必要なサービスの存在確認
            if not self.position_tracker or not self.stop_manager or not self.bitbank_client:
                self.logger.debug("⚠️ トレーリングストップ必要サービス未注入のためスキップ")
                return {"trailing_activated": False}

            # 統合TP/SL IDを取得
            consolidated_ids = self.position_tracker.get_consolidated_tp_sl_ids()
            existing_tp_id = consolidated_ids.get("tp_order_id")
            existing_sl_id = consolidated_ids.get("sl_order_id")

            # SL注文が存在しない場合はスキップ
            if not existing_sl_id:
                return {"trailing_activated": False}

            # ポジション情報を取得
            if self.position_tracker.get_position_count() == 0:
                return {"trailing_activated": False}

            average_entry_price = self.position_tracker._average_entry_price
            total_amount = self.position_tracker._total_position_size
            side = self.position_tracker._side

            # 現在のSL価格を取得（PositionTrackerから）
            # Phase 42.2: consolidated_sl_priceを追加する必要がある
            # 暫定的に計算で求める
            current_sl_price = consolidated_ids.get("sl_price", 0)
            if current_sl_price == 0:
                # SL価格が保存されていない場合は、初期配置時の値を使用
                self.logger.debug("⚠️ 現在SL価格取得不可のためスキップ")
                return {"trailing_activated": False}

            symbol = get_threshold("trading_constraints.currency_pair", "BTC/JPY")

            # トレーリングストップ更新
            result = await self.stop_manager.update_trailing_stop_loss(
                current_price=current_price,
                average_entry_price=average_entry_price,
                current_sl_price=current_sl_price,
                side=side,
                symbol=symbol,
                total_amount=total_amount,
                bitbank_client=self.bitbank_client,
                existing_tp_id=existing_tp_id,
                existing_sl_id=existing_sl_id,
            )

            # トレーリング発動時の処理
            if result.get("trailing_activated"):
                # PositionTrackerに新しいSL IDと価格を保存
                new_sl_id = result.get("new_sl_order_id")
                new_sl_price = result.get("new_sl_price")
                if new_sl_id:
                    # TP価格は変更なし（既存値を維持）
                    existing_tp_price = consolidated_ids.get("tp_price", 0)
                    self.position_tracker.set_consolidated_tp_sl_ids(
                        tp_order_id=existing_tp_id,  # TPはそのまま
                        sl_order_id=new_sl_id,  # 新しいSL ID
                        tp_price=existing_tp_price,  # TP価格は維持
                        sl_price=new_sl_price,  # 新しいSL価格
                        side=side,
                    )

                # Phase 42.2: TP超過チェック（TPキャンセル処理）
                cancel_tp_when_exceeds = trailing_config.get("cancel_tp_when_exceeds", True)
                if cancel_tp_when_exceeds:
                    await self._cancel_tp_when_trailing_exceeds(
                        new_sl_price=result["new_sl_price"],
                        existing_tp_id=existing_tp_id,
                        side=side,
                        symbol=symbol,
                    )

            return result

        except Exception as e:
            self.logger.error(f"❌ トレーリングストップ監視エラー: {e}", exc_info=True)
            return {"trailing_activated": False}

    async def _cancel_tp_when_trailing_exceeds(
        self,
        new_sl_price: float,
        existing_tp_id: Optional[str],
        side: str,
        symbol: str,
    ) -> None:
        """
        Phase 42.2: トレーリングSLがTPを超えた場合にTPをキャンセル

        利益最大化のため、トレーリングSLがTPを超えたらTPをキャンセルして
        さらなる上昇を追従する。

        Args:
            new_sl_price: 新しいSL価格
            existing_tp_id: 既存TP注文ID
            side: 注文サイド (buy/sell)
            symbol: 取引ペア
        """
        try:
            if not existing_tp_id:
                return

            # TP価格を取得（PositionTrackerから）
            consolidated_ids = self.position_tracker.get_consolidated_tp_sl_ids()
            tp_price = consolidated_ids.get("tp_price", 0)

            if tp_price == 0:
                self.logger.debug("⚠️ TP価格取得不可のためTPキャンセルスキップ")
                return

            # SLがTPを超えたかチェック
            tp_exceeded = False
            if side.lower() == "buy" and new_sl_price >= tp_price:
                tp_exceeded = True
                self.logger.info(
                    f"🔄 Phase 42.2: 買いポジションでSLがTP超過 - "
                    f"SL={new_sl_price:.0f}円 >= TP={tp_price:.0f}円"
                )
            elif side.lower() == "sell" and new_sl_price <= tp_price:
                tp_exceeded = True
                self.logger.info(
                    f"🔄 Phase 42.2: 売りポジションでSLがTP超過 - "
                    f"SL={new_sl_price:.0f}円 <= TP={tp_price:.0f}円"
                )

            if tp_exceeded:
                # TPをキャンセル
                try:
                    await asyncio.to_thread(
                        self.bitbank_client.cancel_order, existing_tp_id, symbol
                    )
                    self.logger.info(
                        f"✅ Phase 42.2: トレーリングSL がTP超過のためTPキャンセル完了: {existing_tp_id}",
                        extra_data={
                            "tp_order_id": existing_tp_id,
                            "new_sl_price": new_sl_price,
                            "tp_price": tp_price,
                        },
                        discord_notify=True,
                    )

                    # PositionTrackerからTP ID・価格を削除
                    self.position_tracker.set_consolidated_tp_sl_ids(
                        tp_order_id=None,  # TPをクリア
                        sl_order_id=consolidated_ids.get("sl_order_id"),  # SLはそのまま
                        tp_price=0.0,  # TP価格をクリア
                        sl_price=new_sl_price,  # SL価格は維持
                        side=side,
                    )

                except Exception as e:
                    self.logger.error(
                        f"❌ Phase 42.2: TPキャンセル失敗: {e}",
                        extra_data={"error_message": str(e)},
                        discord_notify=True,
                    )

        except Exception as e:
            self.logger.error(f"❌ TP超過チェックエラー: {e}", exc_info=True)

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
