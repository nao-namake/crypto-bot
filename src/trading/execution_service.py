"""
取引実行サービス - ExecutionServiceProtocol実装

ライブ/ペーパーモードを自動判別し、適切な取引実行を行う。
BitbankClient.create_orderを使用した実際の注文実行機能を提供。

Silent Failure修正済み: TradeEvaluationのsideフィールドを正しく使用。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, Union

from ..core.config import get_threshold
from ..core.exceptions import CryptoBotError
from ..core.logger import get_logger
from ..data.bitbank_client import BitbankClient
from .risk_manager import ExecutionMode, ExecutionResult, OrderStatus, TradeEvaluation


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
        # モード別初期残高取得（Phase 23一元管理対応）
        from ..core.config import load_config

        config = load_config("config/core/unified.yaml")
        # mode_balancesから該当モードの初期残高を取得
        mode_balances = getattr(config, "mode_balances", {})
        mode_balance_config = mode_balances.get(self.mode, {})
        self.virtual_balance = mode_balance_config.get("initial_balance", 10000.0)

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

            # ポジション管理制限チェック（口座残高使い切り問題対策）
            position_check_result = self._check_position_limits(evaluation)
            if not position_check_result["allowed"]:
                self.logger.warning(f"🚫 取引制限により取引拒否: {position_check_result['reason']}")
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
            order_execution_config = await self._get_optimal_order_execution_config(evaluation)
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

            # 実行結果作成
            result = ExecutionResult(
                success=True,
                mode=ExecutionMode.LIVE,
                order_id=order_result.get("id"),
                price=float(order_result.get("price", price or 0)),
                amount=float(order_result.get("amount", 0)),
                filled_price=float(
                    order_result.get("filled_price", order_result.get("price", price or 0))
                ),
                filled_amount=float(
                    order_result.get("filled_amount", order_result.get("amount", 0))
                ),
                error_message=None,
                side=side,
                fee=float(order_result.get("fee", 0)),
                status=(OrderStatus.FILLED if order_type == "market" else OrderStatus.SUBMITTED),
                notes=f"{order_type}注文実行 - {order_execution_config.get('strategy', 'default')}",
            )

            # 統計更新
            self.executed_trades += 1

            # ログ出力（注文タイプ別）
            if order_type == "market":
                self.logger.info(
                    f"✅ 成行注文実行成功: 注文ID={result.order_id}, 手数料: Taker(0.12%)"
                )
            else:
                self.logger.info(
                    f"✅ 指値注文投入成功: 注文ID={result.order_id}, 予想手数料: Maker(-0.02%)"
                )

            return result

        except Exception as e:
            self.logger.error(f"❌ ライブ取引実行失敗: {e}")
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
            from ..core.config import get_threshold

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
                    from dataclasses import replace

                    evaluation = replace(evaluation, position_size=min_trade_size)

            return evaluation

        except Exception as e:
            self.logger.error(f"最小ロット保証処理エラー: {e}")
            return evaluation  # エラー時は元のevaluationを返す

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
                    import asyncio

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

            # 統計更新
            self.executed_trades += 1

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

    async def check_stop_conditions(self) -> Optional[ExecutionResult]:
        """
        ストップ条件チェック（Phase 28: テイクプロフィット/ストップロス実装）

        Returns:
            ExecutionResult: ストップ実行結果（実行しない場合はNone）
        """
        try:
            # ポジションがない場合は何もしない
            if not hasattr(self, "virtual_positions") or not self.virtual_positions:
                return None

            # 現在価格取得
            current_price = await self._get_current_price()
            if current_price <= 0:
                self.logger.warning("⚠️ 現在価格取得失敗、ストップ条件チェックスキップ")
                return None

            # Phase 28: 通常のテイクプロフィット/ストップロスチェック
            tp_sl_result = await self._check_take_profit_stop_loss(current_price)
            if tp_sl_result:
                return tp_sl_result

            # 緊急ストップロス条件チェック（既存機能維持）
            emergency_result = await self._check_emergency_stop_loss()
            if emergency_result:
                return emergency_result

            if self.mode == "live" and self.bitbank_client:
                # ライブモードでは実際のポジション確認が必要
                # 現在は未実装（フェーズ2で実装予定）
                pass

            return None

        except Exception as e:
            self.logger.error(f"❌ ストップ条件チェックエラー: {e}")
            return None

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

    def _check_position_limits(self, evaluation: TradeEvaluation) -> Dict[str, Any]:
        """
        ポジション管理制限チェック（口座残高使い切り問題対策）

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        from datetime import datetime, timedelta

        from ..core.config import get_threshold

        try:
            # 0. 最小資金要件チェック（動的ポジションサイジング対応）
            min_account_balance = get_threshold("position_management.min_account_balance", 10000.0)
            current_balance = self.virtual_balance if self.mode == "paper" else self.current_balance

            # 動的ポジションサイジングが有効な場合は最小要件を緩和
            dynamic_enabled = get_threshold(
                "position_management.dynamic_position_sizing.enabled", False
            )

            if not dynamic_enabled and current_balance < min_account_balance:
                return {
                    "allowed": False,
                    "reason": f"最小運用資金要件({min_account_balance:.0f}円)を下回っています。現在: {current_balance:.0f}円",
                }

            # 動的サイジング有効時は最小ロット取引可能性をチェック
            if dynamic_enabled:
                min_trade_size = get_threshold("position_management.min_trade_size", 0.0001)
                # 概算BTC価格（最新価格が不明な場合の推定値）
                estimated_btc_price = 10000000.0  # 1000万円と仮定
                min_required_balance = min_trade_size * estimated_btc_price * 1.1  # 10%マージン

                if current_balance < min_required_balance:
                    return {
                        "allowed": False,
                        "reason": f"最小ロット取引に必要な資金({min_required_balance:.0f}円)を下回っています。現在: {current_balance:.0f}円",
                    }

            # 1. 最大ポジション数チェック
            max_positions = get_threshold("position_management.max_open_positions", 3)
            current_positions = len(self.virtual_positions) if self.mode == "paper" else 0

            if current_positions >= max_positions:
                return {
                    "allowed": False,
                    "reason": f"最大ポジション数制限({max_positions}個)に達しています。現在: {current_positions}個",
                }

            # 2. 残高利用率チェック
            max_capital_usage = get_threshold("risk.max_capital_usage", 0.3)
            current_balance = self.virtual_balance if self.mode == "paper" else self.current_balance
            initial_balance = self.virtual_balance if self.mode == "paper" else 10000.0

            # 現在の使用率計算
            current_usage_ratio = (initial_balance - current_balance) / initial_balance

            if current_usage_ratio >= max_capital_usage:
                return {
                    "allowed": False,
                    "reason": f"資金利用率制限({max_capital_usage * 100:.0f}%)に達しています。現在: {current_usage_ratio * 100:.1f}%",
                }

            # 3. 日次取引回数チェック（簡易実装）
            max_daily_trades = get_threshold("position_management.max_daily_trades", 20)

            # 今日の取引回数をカウント（virtual_positionsから）
            if hasattr(self, "virtual_positions") and self.virtual_positions:
                today = datetime.now().date()
                today_trades = sum(
                    1
                    for trade in self.virtual_positions
                    if (
                        hasattr(trade, "get")
                        and isinstance(trade.get("timestamp"), str)
                        and datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00")).date()
                        == today
                    )
                )

                if today_trades >= max_daily_trades:
                    return {
                        "allowed": False,
                        "reason": f"日次取引回数制限({max_daily_trades}回)に達しています。今日: {today_trades}回",
                    }

            # 4. 取引サイズチェック（ML信頼度連動・最小ロット優先）
            ml_confidence = getattr(evaluation, "confidence_level", 0.5)
            min_trade_size = get_threshold("position_management.min_trade_size", 0.0001)
            trade_amount = float(evaluation.position_size) * 16762000  # BTC価格概算
            min_trade_amount = min_trade_size * 16762000  # 最小ロット価値

            # ML信頼度に基づく制限比率を決定
            if ml_confidence < 0.60:
                # 低信頼度
                max_position_ratio = get_threshold(
                    "position_management.max_position_ratio_per_trade.low_confidence", 0.03
                )
                confidence_category = "low"
            elif ml_confidence < 0.75:
                # 中信頼度
                max_position_ratio = get_threshold(
                    "position_management.max_position_ratio_per_trade.medium_confidence", 0.05
                )
                confidence_category = "medium"
            else:
                # 高信頼度
                max_position_ratio = get_threshold(
                    "position_management.max_position_ratio_per_trade.high_confidence", 0.10
                )
                confidence_category = "high"

            max_allowed_amount = current_balance * max_position_ratio
            enforce_minimum = get_threshold(
                "position_management.max_position_ratio_per_trade.enforce_minimum", True
            )

            # 最小ロット優先チェック
            if enforce_minimum and trade_amount <= min_trade_amount:
                # 最小ロット以下の場合は制限を無視して許可
                self.logger.info(
                    f"💡 最小ロット優先適用: 制限¥{max_allowed_amount:,.0f} < 最小ロット¥{min_trade_amount:,.0f} → 最小ロット許可"
                )
                return {"allowed": True, "reason": "最小ロット優先による許可"}

            if trade_amount > max_allowed_amount:
                return {
                    "allowed": False,
                    "reason": f"1取引あたりの最大金額制限({confidence_category}信頼度)を超過。制限: ¥{max_allowed_amount:,.0f}, 要求: ¥{trade_amount:,.0f}",
                }

            return {"allowed": True, "reason": "制限チェック通過"}

        except Exception as e:
            self.logger.error(f"❌ ポジション制限チェックエラー: {e}")
            # エラー時は安全のため取引拒否
            return {"allowed": False, "reason": f"制限チェック処理エラー: {e}"}

    async def _check_emergency_stop_loss(self) -> Optional[ExecutionResult]:
        """
        緊急ストップロス条件チェック（急変時例外処理）

        30分のクールダウン制限を無視して、市場急変時に緊急決済を実行

        Returns:
            ExecutionResult: 緊急決済実行結果（実行しない場合はNone）
        """
        from datetime import datetime, timedelta

        from ..core.config import get_threshold

        try:
            # 緊急ストップロス設定確認
            emergency_config = get_threshold("position_management.emergency_stop_loss", {})
            if not emergency_config.get("enable", False):
                return None

            # ポジションがない場合はチェック不要
            if not hasattr(self, "virtual_positions") or not self.virtual_positions:
                return None

            self.logger.info("🔍 緊急ストップロス条件チェック開始")

            # 現在価格取得
            current_price = await self._get_current_price()
            if current_price <= 0:
                self.logger.warning("⚠️ 現在価格取得失敗、緊急ストップロスチェックスキップ")
                return None

            # 各ポジションの緊急決済チェック
            for position in self.virtual_positions:
                emergency_exit = await self._evaluate_emergency_exit(
                    position, current_price, emergency_config
                )
                if emergency_exit:
                    self.logger.critical(
                        f"🚨 緊急ストップロス発動! ポジション: {position['order_id']}"
                    )
                    return emergency_exit

            return None

        except Exception as e:
            self.logger.error(f"❌ 緊急ストップロスチェックエラー: {e}")
            return None

    async def _get_current_price(self) -> float:
        """現在価格取得（緊急時用）"""
        try:
            if self.bitbank_client:
                import asyncio

                ticker = await asyncio.to_thread(self.bitbank_client.fetch_ticker, "BTC/JPY")
                if ticker and "last" in ticker:
                    return float(ticker["last"])

            # フォールバック価格
            return get_threshold("trading.fallback_btc_jpy", 16500000.0)

        except Exception as e:
            self.logger.warning(f"⚠️ 現在価格取得エラー: {e}")
            return get_threshold("trading.fallback_btc_jpy", 16500000.0)

    async def _evaluate_emergency_exit(
        self, position: dict, current_price: float, config: dict
    ) -> Optional[ExecutionResult]:
        """
        個別ポジションの緊急決済判定

        Args:
            position: 保有ポジション情報
            current_price: 現在価格
            config: 緊急ストップロス設定

        Returns:
            ExecutionResult: 緊急決済結果（実行しない場合はNone）
        """
        try:
            entry_price = float(position.get("price", 0))
            entry_side = position.get("side", "")
            amount = float(position.get("amount", 0))
            entry_time = position.get("timestamp")

            if entry_price <= 0 or amount <= 0:
                return None

            # 最小保有時間チェック（誤発動防止）
            min_hold_minutes = config.get("min_hold_minutes", 1)
            if isinstance(entry_time, datetime):
                time_diff = datetime.now() - entry_time
                if time_diff.total_seconds() < min_hold_minutes * 60:
                    return None

            # 含み損計算
            if entry_side.lower() == "buy":
                unrealized_pnl_ratio = (current_price - entry_price) / entry_price
            elif entry_side.lower() == "sell":
                unrealized_pnl_ratio = (entry_price - current_price) / entry_price
            else:
                return None

            # 最大損失閾値チェック
            max_loss_threshold = config.get("max_loss_threshold", 0.05)
            if unrealized_pnl_ratio <= -max_loss_threshold:
                self.logger.critical(
                    f"🚨 最大損失閾値超過! 含み損: {unrealized_pnl_ratio * 100:.2f}% (閾値: -{max_loss_threshold * 100:.0f}%)"
                )

                # 緊急決済実行
                return await self._execute_emergency_exit(
                    position, current_price, "max_loss_exceeded"
                )

            # 価格急変チェック
            price_change_result = await self._check_rapid_price_movement(current_price, config)
            if price_change_result and entry_side.lower() == "buy":  # 買いポジションで急落時
                self.logger.critical(f"🚨 急落検出! 価格変動: {price_change_result}")
                return await self._execute_emergency_exit(position, current_price, "rapid_decline")
            elif price_change_result and entry_side.lower() == "sell":  # 売りポジションで急騰時
                self.logger.critical(f"🚨 急騰検出! 価格変動: {price_change_result}")
                return await self._execute_emergency_exit(position, current_price, "rapid_rise")

            return None

        except Exception as e:
            self.logger.error(f"❌ 緊急決済判定エラー: {e}")
            return None

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

    async def _execute_emergency_exit(
        self, position: dict, current_price: float, reason: str
    ) -> ExecutionResult:
        """
        緊急決済実行（クールダウン無視）

        Args:
            position: 決済対象ポジション
            current_price: 現在価格
            reason: 緊急決済理由

        Returns:
            ExecutionResult: 決済実行結果
        """
        try:
            entry_side = position.get("side", "")
            amount = float(position.get("amount", 0))

            # 反対売買（決済）のサイド決定
            exit_side = "sell" if entry_side.lower() == "buy" else "buy"

            # 緊急決済用のTradeEvaluation作成
            from .risk_manager import TradeEvaluation

            emergency_evaluation = TradeEvaluation(
                side=exit_side,
                confidence=1.0,  # 緊急決済なので最高信頼度
                position_size=amount,
                entry_price=current_price,
                stop_loss=0.0,
                take_profit=0.0,
            )

            self.logger.critical(
                f"🚨 緊急決済実行: {exit_side} {amount} BTC @ {current_price:.0f}円 - 理由: {reason}"
            )

            # 実際の決済実行（クールダウン制限を無視）
            if self.mode == "live":
                result = await self._execute_live_trade(emergency_evaluation)
            else:
                result = await self._execute_paper_trade(emergency_evaluation)

            # ポジションリストから削除
            if hasattr(self, "virtual_positions"):
                self.virtual_positions = [
                    p
                    for p in self.virtual_positions
                    if p.get("order_id") != position.get("order_id")
                ]

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
                mode=ExecutionMode.LIVE if self.mode == "live" else ExecutionMode.PAPER,
                order_id=None,
                price=current_price,
                amount=0.0,
                error_message=f"緊急決済エラー: {e}",
                side="emergency_exit",
                fee=0.0,
                status=OrderStatus.FAILED,
            )

    async def _get_optimal_order_execution_config(
        self, evaluation: TradeEvaluation
    ) -> Dict[str, Any]:
        """
        最適注文実行戦略決定（Phase 26: 指値注文オプション）

        ML信頼度・市場条件・設定に基づいて成行/指値注文を選択し、
        指値注文の場合は最適価格を計算する。

        Args:
            evaluation: 取引評価結果

        Returns:
            Dict: 注文実行設定 {"order_type": str, "price": Optional[float], "strategy": str}
        """
        try:
            # 1. 基本設定取得
            smart_order_enabled = get_threshold("order_execution.smart_order_enabled", False)

            # スマート注文機能が無効な場合はデフォルト（成行）を使用
            if not smart_order_enabled:
                default_order_type = get_threshold(
                    "trading_constraints.default_order_type", "market"
                )
                return {"order_type": default_order_type, "price": None, "strategy": "default"}

            # 2. ML信頼度による判定
            ml_confidence = float(getattr(evaluation, "confidence_level", 0.5))
            high_confidence_threshold = get_threshold(
                "order_execution.high_confidence_threshold", 0.75
            )

            # 3. 市場条件確認
            market_conditions = await self._assess_market_conditions()

            # 4. 注文戦略決定
            order_config = await self._determine_order_strategy(
                ml_confidence, high_confidence_threshold, market_conditions, evaluation
            )

            self.logger.info(
                f"📋 注文実行戦略: {order_config['strategy']} -> {order_config['order_type']}注文"
                + (f" @ {order_config.get('price', 0):.0f}円" if order_config.get("price") else "")
            )

            return order_config

        except Exception as e:
            self.logger.error(f"❌ 注文実行戦略決定エラー: {e}")
            # エラー時は安全な成行注文を使用
            return {"order_type": "market", "price": None, "strategy": "fallback_market"}

    async def _assess_market_conditions(self) -> Dict[str, Any]:
        """
        市場条件評価（指値注文判定用）

        Returns:
            Dict: 市場状況情報
        """
        try:
            conditions = {
                "spread_ratio": 0.0,
                "volume_adequate": True,
                "volatility_level": "normal",
                "liquidity_sufficient": True,
            }

            if not self.bitbank_client:
                conditions["assessment"] = "unable_to_assess"
                return conditions

            # 板情報取得（スプレッド・流動性確認）
            try:
                import asyncio

                orderbook = await asyncio.to_thread(
                    self.bitbank_client.fetch_order_book, "BTC/JPY", 10
                )

                if orderbook and "bids" in orderbook and "asks" in orderbook:
                    best_bid = float(orderbook["bids"][0][0]) if orderbook["bids"] else 0
                    best_ask = float(orderbook["asks"][0][0]) if orderbook["asks"] else 0

                    if best_bid > 0 and best_ask > 0:
                        spread_ratio = (best_ask - best_bid) / best_bid
                        conditions["spread_ratio"] = spread_ratio
                        conditions["best_bid"] = best_bid
                        conditions["best_ask"] = best_ask

                        # スプレッド判定（設定値と比較）
                        max_spread_for_limit = get_threshold(
                            "order_execution.max_spread_ratio_for_limit", 0.005
                        )  # 0.5%

                        if spread_ratio > max_spread_for_limit:
                            conditions["spread_too_wide"] = True
                            self.logger.warning(
                                f"⚠️ スプレッド拡大: {spread_ratio * 100:.2f}% > {max_spread_for_limit * 100:.1f}%"
                            )

            except Exception as e:
                self.logger.warning(f"⚠️ 板情報取得エラー: {e}")
                conditions["orderbook_error"] = str(e)

            return conditions

        except Exception as e:
            self.logger.error(f"❌ 市場条件評価エラー: {e}")
            return {"assessment": "error", "error": str(e)}

    async def _determine_order_strategy(
        self,
        ml_confidence: float,
        high_confidence_threshold: float,
        market_conditions: Dict[str, Any],
        evaluation: TradeEvaluation,
    ) -> Dict[str, Any]:
        """
        注文戦略決定ロジック

        Args:
            ml_confidence: ML信頼度
            high_confidence_threshold: 高信頼度閾値
            market_conditions: 市場条件
            evaluation: 取引評価

        Returns:
            Dict: 注文実行設定
        """
        try:
            # 1. 緊急時は成行注文
            if hasattr(evaluation, "emergency_exit") and evaluation.emergency_exit:
                return {"order_type": "market", "price": None, "strategy": "emergency_market"}

            # 2. 低信頼度の場合は成行注文（確実な約定優先）
            low_confidence_threshold = get_threshold(
                "order_execution.low_confidence_threshold", 0.4
            )
            if ml_confidence < low_confidence_threshold:
                return {"order_type": "market", "price": None, "strategy": "low_confidence_market"}

            # 3. スプレッドが広すぎる場合は成行注文
            if market_conditions.get("spread_too_wide", False):
                return {"order_type": "market", "price": None, "strategy": "wide_spread_market"}

            # 4. 高信頼度 + 良好な市場条件 = 指値注文（手数料削減）
            if (
                ml_confidence >= high_confidence_threshold
                and market_conditions.get("liquidity_sufficient", False)
                and not market_conditions.get("orderbook_error")
            ):

                # 指値価格計算
                limit_price = await self._calculate_limit_price(evaluation, market_conditions)

                if limit_price > 0:
                    return {
                        "order_type": "limit",
                        "price": limit_price,
                        "strategy": "high_confidence_limit",
                        "expected_fee": "maker_rebate",  # -0.02%
                    }

            # 5. デフォルト: 中信頼度は成行注文（安全重視）
            return {"order_type": "market", "price": None, "strategy": "medium_confidence_market"}

        except Exception as e:
            self.logger.error(f"❌ 注文戦略決定エラー: {e}")
            return {"order_type": "market", "price": None, "strategy": "error_fallback_market"}

    async def _calculate_limit_price(
        self, evaluation: TradeEvaluation, market_conditions: Dict[str, Any]
    ) -> float:
        """
        指値注文価格計算

        約定確率を考慮しつつ、手数料削減効果を最大化する指値価格を計算。

        Args:
            evaluation: 取引評価
            market_conditions: 市場条件

        Returns:
            float: 指値価格（0の場合は計算失敗）
        """
        try:
            side = evaluation.side
            best_bid = market_conditions.get("best_bid", 0)
            best_ask = market_conditions.get("best_ask", 0)

            if not best_bid or not best_ask:
                self.logger.warning("⚠️ 最良気配なし、指値価格計算不可")
                return 0

            # 指値注文の価格戦略設定
            price_improvement_ratio = get_threshold(
                "order_execution.price_improvement_ratio", 0.001
            )  # 0.1% 価格改善

            if side.lower() == "buy":
                # 買い注文：現在のbid価格より少し上（約定確率向上）
                limit_price = best_bid * (1 + price_improvement_ratio)

                # ask価格を超えないように制限
                max_buy_price = best_ask * 0.999  # askより0.1%下
                limit_price = min(limit_price, max_buy_price)

                self.logger.debug(
                    f"💰 買い指値価格計算: bid={best_bid:.0f}円 -> 指値={limit_price:.0f}円 "
                    f"(改善={price_improvement_ratio * 100:.1f}%)"
                )

            elif side.lower() == "sell":
                # 売り注文：現在のask価格より少し下（約定確率向上）
                limit_price = best_ask * (1 - price_improvement_ratio)

                # bid価格を下回らないように制限
                min_sell_price = best_bid * 1.001  # bidより0.1%上
                limit_price = max(limit_price, min_sell_price)

                self.logger.debug(
                    f"💰 売り指値価格計算: ask={best_ask:.0f}円 -> 指値={limit_price:.0f}円 "
                    f"(改善={price_improvement_ratio * 100:.1f}%)"
                )

            else:
                self.logger.error(f"❌ 不正な注文サイド: {side}")
                return 0

            # 価格の妥当性チェック
            if limit_price <= 0:
                self.logger.error(f"❌ 不正な指値価格: {limit_price}")
                return 0

            return round(limit_price)  # 円単位に丸める

        except Exception as e:
            self.logger.error(f"❌ 指値価格計算エラー: {e}")
            return 0

    async def _check_take_profit_stop_loss(self, current_price: float) -> Optional[ExecutionResult]:
        """
        Phase 28: 通常のテイクプロフィット/ストップロスチェック

        Args:
            current_price: 現在のBTC価格

        Returns:
            ExecutionResult: 決済実行結果（実行しない場合はNone）
        """
        from ..core.config import get_threshold

        try:
            # 設定取得
            tp_config = get_threshold("position_management.take_profit", {})
            sl_config = get_threshold("position_management.stop_loss", {})

            if not tp_config.get("enabled", True) and not sl_config.get("enabled", True):
                return None

            # 各ポジションのTP/SLチェック
            for position in self.virtual_positions:
                exit_result = await self._evaluate_position_exit(
                    position, current_price, tp_config, sl_config
                )
                if exit_result:
                    # ポジションリストから削除
                    self.virtual_positions.remove(position)
                    return exit_result

            return None

        except Exception as e:
            self.logger.error(f"❌ テイクプロフィット/ストップロスチェックエラー: {e}")
            return None

    async def _evaluate_position_exit(
        self, position: dict, current_price: float, tp_config: dict, sl_config: dict
    ) -> Optional[ExecutionResult]:
        """
        個別ポジションの決済判定

        Args:
            position: ポジション情報
            current_price: 現在価格
            tp_config: テイクプロフィット設定
            sl_config: ストップロス設定

        Returns:
            ExecutionResult: 決済結果（決済しない場合はNone）
        """
        try:
            entry_price = float(position.get("price", 0))
            entry_side = position.get("side", "")
            amount = float(position.get("amount", 0))
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
                    return await self._execute_position_exit(position, current_price, "take_profit")

            # ストップロスチェック
            if sl_config.get("enabled", True) and stop_loss:
                sl_triggered = False
                if entry_side.lower() == "buy" and current_price <= float(stop_loss):
                    sl_triggered = True
                elif entry_side.lower() == "sell" and current_price >= float(stop_loss):
                    sl_triggered = True

                if sl_triggered:
                    self.logger.warning(
                        f"🛑 ストップロス到達! {entry_side} {amount} BTC @ {current_price:.0f}円 (SL:{stop_loss:.0f}円)"
                    )
                    return await self._execute_position_exit(position, current_price, "stop_loss")

            return None

        except Exception as e:
            self.logger.error(f"❌ ポジション決済判定エラー: {e}")
            return None

    async def _execute_position_exit(
        self, position: dict, current_price: float, exit_reason: str
    ) -> ExecutionResult:
        """
        ポジション決済実行

        Args:
            position: ポジション情報
            current_price: 決済価格
            exit_reason: 決済理由 ("take_profit", "stop_loss", "emergency")

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

            # ExecutionResult作成
            result = ExecutionResult(
                success=True,
                mode=ExecutionMode.PAPER if self.mode == "paper" else ExecutionMode.LIVE,
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

            # 統計更新
            self.executed_trades += 1
            self.session_pnl += pnl

            # ログ出力
            pnl_status = "利益" if pnl > 0 else "損失"
            self.logger.info(
                f"🔄 ポジション決済完了: {exit_side} {amount} BTC @ {current_price:.0f}円 "
                f"({exit_reason}) {pnl_status}:{pnl:+.0f}円"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ ポジション決済実行エラー: {e}")
            # エラーの場合は失敗結果を返す
            return ExecutionResult(
                success=False,
                mode=ExecutionMode.PAPER if self.mode == "paper" else ExecutionMode.LIVE,
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
