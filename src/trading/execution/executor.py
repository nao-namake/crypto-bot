"""
取引実行サービス - ExecutionServiceProtocol実装
Phase 49.16完了 - メイン実行ロジック・TP/SL設定完全見直し

ライブ/ペーパーモードを自動判別し、適切な取引実行を行う。
BitbankClient.create_orderを使用した実際の注文実行機能を提供。

Silent Failure修正済み: TradeEvaluationのsideフィールドを正しく使用。
Phase 49.16: TP/SL設定完全渡し（thresholds.yaml完全準拠）
"""

import asyncio
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from tax.trade_history_recorder import TradeHistoryRecorder

from ...backtest.reporter import TradeTracker
from ...core.config import get_threshold
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

        # ペーパートレード用
        self.virtual_positions = []

        # Phase 29.6: クールダウン管理
        self.last_order_time = None

        # Phase 56.3: バックテスト時刻管理（バックテスト時にシミュレーション時刻を使用）
        self.current_time: Optional[datetime] = None

        # Phase 30: 指値注文タイムアウト管理
        self.pending_limit_orders: List[Dict[str, Any]] = []

        # Phase 63: TP/SL検証スケジュール管理（asyncio.create_task廃止）
        self._pending_verifications: List[Dict[str, Any]] = []

        # モード別初期残高取得（Phase 55.9: get_threshold()使用に変更）
        # 旧方式: load_config()ではmode_balances属性が取得できないバグがあった
        # フォールバック値はすべて¥100,000（バックテスト基準）
        if self.mode == "backtest":
            self.virtual_balance = get_threshold("mode_balances.backtest.initial_balance", 100000.0)
        elif self.mode == "paper":
            self.virtual_balance = get_threshold("mode_balances.paper.initial_balance", 100000.0)
        else:
            self.virtual_balance = get_threshold("mode_balances.live.initial_balance", 100000.0)

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
        self.data_service = None  # Phase 54.6: ATR取得Level 2用

        self.logger.info(f"✅ ExecutionService初期化完了 - モード: {mode}")

    async def restore_positions_from_api(self):
        """
        Phase 53.6: 起動時にbitbank APIからポジションを復元
        Phase 58.3: 実ポジション同期を追加
        再起動時にvirtual_positionsがリセットされる問題を解決

        Cloud Run環境では5分毎にコンテナが再起動される可能性があり、
        その際にvirtual_positions = []にリセットされてしまう。
        これにより、既存のTP/SL注文を認識できず、ポジション制限が機能しなくなる。

        この関数は起動時にbitbank APIからアクティブ注文を取得し、
        virtual_positionsを復元することで、ポジション制限を正しく機能させる。
        """
        if self.mode != "live":
            return  # ライブモード以外は復元不要

        try:
            # Phase 58.3: まず実ポジションを確認してログ出力
            margin_positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")
            if margin_positions:
                total_position_value = sum(
                    p.get("amount", 0) * p.get("average_price", 0) for p in margin_positions
                )
                self.logger.info(
                    f"📊 Phase 58.3: 実ポジション確認 - {len(margin_positions)}件, "
                    f"総額: {total_position_value:.0f}円"
                )
                for pos in margin_positions:
                    self.logger.info(
                        f"  └ {pos.get('side')} {pos.get('amount', 0):.4f} BTC "
                        f"@ {pos.get('average_price', 0):.0f}円 "
                        f"(含み損益: {pos.get('unrealized_pnl', 0):.0f}円)"
                    )
            else:
                self.logger.info("📊 Phase 58.3: 実ポジションなし（ノーポジション）")

            # アクティブ注文を取得
            active_orders = await asyncio.to_thread(
                self.bitbank_client.fetch_active_orders, "BTC/JPY", 100
            )

            if not active_orders:
                self.logger.info("📊 Phase 53.6: アクティブ注文なし、復元スキップ")
                return

            # TP/SL注文をvirtual_positionsに復元
            restored_count = 0
            for order in active_orders:
                order_type = order.get("type", "")
                order_id = order.get("id")

                # TP注文またはSL注文を検出して復元
                if order_type in ["stop", "stop_limit", "limit"]:
                    # Phase 53.11: None値チェック（不完全なデータは復元しない）
                    side = order.get("side")
                    amount = order.get("amount")
                    price = order.get("price")

                    if side is None or amount is None or price is None:
                        self.logger.warning(
                            f"⚠️ Phase 53.11: 不完全な注文スキップ - id={order_id}, "
                            f"side={side}, amount={amount}, price={price}"
                        )
                        continue

                    self.virtual_positions.append(
                        {
                            "order_id": order_id,
                            "type": order_type,
                            "side": side,
                            "amount": float(amount),
                            "price": float(price),
                            "restored": True,  # 復元フラグ
                        }
                    )
                    restored_count += 1

            self.logger.info(
                f"✅ Phase 53.6: {restored_count}件のポジション/注文を復元 "
                f"(アクティブ注文: {len(active_orders)}件)"
            )

        except Exception as e:
            self.logger.warning(f"⚠️ Phase 53.6: ポジション復元失敗: {e}")

    async def ensure_tp_sl_for_existing_positions(self):
        """
        Phase 56.5: 既存ポジションのTP/SL確保

        起動時にTP/SL注文がないポジションを検出し、自動配置する。
        Phase 53.6の問題（アクティブ注文ベースの復元では検出できない）を解決。
        """
        if self.mode != "live":
            return  # ライブモード以外はスキップ

        try:
            # Step 1: 信用建玉情報取得（/user/margin/positions）
            margin_positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")

            if not margin_positions:
                self.logger.info("📊 Phase 56.5: 既存ポジションなし")
                return

            # Step 2: アクティブ注文取得（TP/SL存在確認用）
            active_orders = await asyncio.to_thread(
                self.bitbank_client.fetch_active_orders, "BTC/JPY", 100
            )

            # Step 3: 各ポジションのTP/SL存在確認
            for position in margin_positions:
                position_side = position.get("side")  # "long" or "short"
                amount = position.get("amount", 0)
                avg_price = position.get("average_price", 0)

                if amount <= 0:
                    continue

                # TP/SL注文の存在確認
                has_tp, has_sl = self._check_tp_sl_orders_exist(
                    position_side, amount, active_orders
                )

                if has_tp and has_sl:
                    self.logger.debug(
                        f"✅ Phase 56.5: 既存ポジション TP/SL確認済み - "
                        f"{position_side} {amount:.4f} BTC"
                    )
                    continue

                # Step 4: 不足しているTP/SL注文を配置
                self.logger.info(
                    f"⚠️ Phase 56.5: TP/SLなしポジション検出 - "
                    f"{position_side} {amount:.4f} BTC @ {avg_price:.0f}円 "
                    f"(TP: {'あり' if has_tp else 'なし'}, SL: {'あり' if has_sl else 'なし'})"
                )

                await self._place_missing_tp_sl(
                    position_side=position_side,
                    amount=amount,
                    avg_price=avg_price,
                    has_tp=has_tp,
                    has_sl=has_sl,
                )

        except Exception as e:
            self.logger.warning(f"⚠️ Phase 56.5: 既存ポジションTP/SL確保失敗: {e}")

    def _check_tp_sl_orders_exist(
        self,
        position_side: str,
        position_amount: float,
        active_orders: List[Dict],
    ) -> Tuple[bool, bool]:
        """
        Phase 56.5: 既存注文からTP/SL注文の存在確認

        Args:
            position_side: "long" or "short"
            position_amount: ポジション数量
            active_orders: アクティブ注文リスト

        Returns:
            Tuple[bool, bool]: (has_tp, has_sl)
        """
        has_tp = False
        has_sl = False

        # TP/SL注文の方向決定
        # long position -> TP: sell, SL: sell
        # short position -> TP: buy, SL: buy
        exit_side = "sell" if position_side == "long" else "buy"

        for order in active_orders:
            order_side = order.get("side")
            order_type = order.get("type")
            order_amount = float(order.get("amount", 0))

            if order_side != exit_side:
                continue

            # Phase 63: Bug 2修正 - 数量マッチング緩和
            # ポジション集約時に個別エントリー量と集約量が異なるため、
            # サイド一致のみでマッチング（量チェック削除）
            if order_amount <= 0:
                continue

            # TP: limit注文
            if order_type == "limit":
                has_tp = True

            # SL: stop注文またはstop_limit注文（Phase 63: Bug 1修正）
            if order_type in ("stop", "stop_limit"):
                has_sl = True

        return has_tp, has_sl

    async def _place_missing_tp_sl(
        self,
        position_side: str,
        amount: float,
        avg_price: float,
        has_tp: bool,
        has_sl: bool,
    ):
        """
        Phase 56.5: 不足しているTP/SL注文を配置

        Args:
            position_side: "long" or "short"
            amount: ポジション数量
            avg_price: 平均取得価格
            has_tp: TP注文が存在するか
            has_sl: SL注文が存在するか
        """
        symbol = get_threshold("trading_constraints.currency_pair", "BTC/JPY")

        # レジーム別TP/SL設定（デフォルト: normal_range）
        # Phase 52.0のレジーム別設定を使用
        tp_ratio = get_threshold(
            "position_management.take_profit.regime_configs.normal_range.take_profit_ratio",
            get_threshold("position_management.take_profit.default_ratio", 0.009),
        )
        sl_ratio = get_threshold(
            "position_management.stop_loss.regime_configs.normal_range.max_loss_ratio",
            get_threshold("position_management.stop_loss.max_loss_ratio", 0.007),
        )

        if position_side == "long":
            tp_price = avg_price * (1 + tp_ratio)
            sl_price = avg_price * (1 - sl_ratio)
            entry_side = "buy"
        else:  # short
            tp_price = avg_price * (1 - tp_ratio)
            sl_price = avg_price * (1 + sl_ratio)
            entry_side = "sell"

        # Phase 62.17: TP/SL注文結果を初期化
        tp_order = None
        sl_order = None

        # TP配置
        if not has_tp and self.stop_manager:
            try:
                tp_order = await self.stop_manager.place_take_profit(
                    side=entry_side,
                    amount=amount,
                    entry_price=avg_price,
                    take_profit_price=tp_price,
                    symbol=symbol,
                    bitbank_client=self.bitbank_client,
                )
                if tp_order:
                    self.logger.info(
                        f"✅ Phase 56.5: TP注文配置成功 - "
                        f"{position_side} {amount:.4f} BTC @ {tp_price:.0f}円"
                    )
            except Exception as e:
                self.logger.error(f"❌ Phase 56.5: TP配置失敗: {e}")

        # SL配置
        if not has_sl and self.stop_manager:
            try:
                sl_order = await self.stop_manager.place_stop_loss(
                    side=entry_side,
                    amount=amount,
                    entry_price=avg_price,
                    stop_loss_price=sl_price,
                    symbol=symbol,
                    bitbank_client=self.bitbank_client,
                )
                if sl_order:
                    self.logger.info(
                        f"✅ Phase 56.5: SL注文配置成功 - "
                        f"{position_side} {amount:.4f} BTC @ {sl_price:.0f}円"
                    )
            except Exception as e:
                self.logger.error(f"❌ Phase 56.5: SL配置失敗: {e}")

        # virtual_positionsに追加（ポジション制限管理用）
        # Phase 62.17: sl_order_id, sl_placed_at追加（stop_limit監視用）
        recovered_position = {
            "order_id": f"recovered_{position_side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "side": entry_side,
            "amount": amount,
            "price": avg_price,
            "timestamp": datetime.now(),
            "take_profit": tp_price if not has_tp else None,
            "stop_loss": sl_price if not has_sl else None,
            "recovered": True,  # 復旧フラグ
            "tp_order_id": tp_order.get("order_id") if tp_order else None,
            "sl_order_id": sl_order.get("order_id") if sl_order else None,
            "sl_placed_at": sl_order.get("sl_placed_at") if sl_order else None,
        }
        self.virtual_positions.append(recovered_position)

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
                maker_result = await self._execute_maker_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    maker_config=maker_config,
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
                    # Phase 62.21: フォールバックでもMaker優先（post_only追加）
                    if get_threshold("order_execution.maker_strategy.enabled", True):
                        order_params["post_only"] = True

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
                    f"✅ 成行注文実行成功: 注文ID={result.order_id}, 手数料: Taker(0.12%)"
                )
            else:
                self.logger.info(
                    f"✅ 指値注文投入成功: 注文ID={result.order_id}, 予想手数料: Maker(-0.02%)"
                )

            # Phase 29.6: ライブモードでもポジション追跡（バグ修正）
            # Phase 51.6: TP/SL再計算メソッド抽出（可読性向上・保守性向上）
            actual_filled_price = result.filled_price or result.price

            # TP/SL再計算（3段階ATRフォールバック）
            try:
                final_tp, final_sl = await self._calculate_tp_sl_for_live_trade(
                    evaluation, result, side, amount
                )
            except CryptoBotError as e:
                # ATR取得失敗・TP/SL再計算失敗時のエントリー中止
                self.logger.error(f"❌ Phase 51.6: TP/SL再計算エラー - {e}")
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
                "tp_order_id": None,  # Phase 50.3.1: TP注文ID追跡用
                "sl_order_id": None,  # Phase 50.3.1: SL注文ID追跡用
            }
            self.virtual_positions.append(live_position)

            # Phase 51.6: 古い注文クリーンアップ（bitbank 30件制限対策）
            if self.stop_manager:
                try:
                    symbol = get_threshold("trading_constraints.currency_pair", "BTC/JPY")
                    cleanup_result = await self.stop_manager.cleanup_old_unfilled_orders(
                        symbol=symbol,
                        bitbank_client=self.bitbank_client,
                        virtual_positions=self.virtual_positions,
                        max_age_hours=24,
                        threshold_count=25,
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
            if self.stop_manager:
                try:
                    await self._cleanup_old_tp_sl_before_entry(
                        side=side,
                        symbol=symbol,
                        entry_order_id=result.order_id,
                    )
                except Exception as e:
                    # クリーンアップ失敗してもエントリーは継続（Phase 51.6思想維持）
                    self.logger.warning(
                        f"⚠️ Phase 51.10-A: エントリー前クリーンアップ失敗（処理継続）: {e}"
                    )

            # Phase 51.6: Atomic Entry Pattern（Entry/TP/SL一体化・全成功 or 全ロールバック）
            if self.stop_manager and final_tp and final_sl:
                # PositionTrackerに追加（統合ID管理なし）
                if self.position_tracker:
                    self.position_tracker.add_position(
                        order_id=result.order_id,
                        side=side,
                        amount=amount,
                        price=actual_filled_price,
                    )

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
                    tp_order = await self._place_tp_with_retry(
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
                        f"✅ Phase 51.6 Step 2/3: TP配置成功 - "
                        f"ID: {tp_order_id}, 価格: {final_tp:.0f}円"
                    )

                    # Step 3/3: SL注文配置（リトライ付き）
                    sl_order = await self._place_sl_with_retry(
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

                    # Phase 62.20: TP/SL欠損自動復旧 - 5分後検証をスケジュール
                    self._schedule_tp_sl_verification(
                        entry_order_id=result.order_id,
                        side=side,
                        amount=amount,
                        entry_price=actual_filled_price,
                        tp_order_id=tp_order_id,
                        sl_order_id=sl_order_id,
                        symbol=symbol,
                    )

                except Exception as e:
                    # Phase 51.6: Atomic Entry失敗 → 全ロールバック
                    self.logger.error(f"❌ Phase 51.6: Atomic Entry失敗 - ロールバック開始: {e}")

                    # ロールバック実行（TP/SL/Entry注文をすべてキャンセル）
                    await self._rollback_entry(
                        entry_order_id=result.order_id,
                        tp_order_id=tp_order_id,
                        sl_order_id=sl_order_id,
                        symbol=symbol,
                        error=e,
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
                "adjusted_confidence": getattr(
                    evaluation, "adjusted_confidence", None
                ),  # Phase 59.3
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
            virtual_position = {
                "order_id": virtual_order_id,
                "side": side,
                "amount": amount,
                "price": price,
                "timestamp": trade_timestamp,
                "take_profit": getattr(evaluation, "take_profit", None),
                "stop_loss": getattr(evaluation, "stop_loss", None),
                "strategy_name": getattr(evaluation, "strategy_name", "unknown"),
                "adjusted_confidence": getattr(
                    evaluation, "adjusted_confidence", None
                ),  # Phase 59.3: バックテスト用
            }
            self.virtual_positions.append(virtual_position)

            # Phase 51.7: PositionTracker登録（ポジション管理統一）
            if self.position_tracker:
                try:
                    self.position_tracker.add_position(
                        order_id=virtual_order_id,
                        side=side,
                        amount=amount,
                        price=price,
                    )
                    self.logger.debug(
                        f"📊 Phase 51.7: バックテストポジション追加 - ID: {virtual_order_id}, "
                        f"価格: {price:.0f}円, TP: {virtual_position.get('take_profit'):.0f}円, "
                        f"SL: {virtual_position.get('stop_loss'):.0f}円"
                    )
                except Exception as e:
                    self.logger.warning(f"⚠️ バックテストポジション追加エラー: {e}")

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
        if data_service:
            self.data_service = data_service

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
                        self.virtual_positions = [
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
                            self.virtual_positions = [
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
        if self.mode == "live":
            try:
                await self._process_pending_verifications()
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 63: pending_verifications処理エラー: {e}")

        if self.stop_manager:
            return await self.stop_manager.check_stop_conditions(
                self.virtual_positions,
                self.bitbank_client,
                self.mode,
                self.executed_trades,
                self.session_pnl,
            )
        return None

    async def _calculate_tp_sl_for_live_trade(
        self,
        evaluation: TradeEvaluation,
        result: ExecutionResult,
        side: str,
        amount: float,
    ) -> Tuple[float, float]:
        """
        Phase 51.6: ライブトレードTP/SL再計算（3段階ATRフォールバック）

        Args:
            evaluation: 取引評価
            result: 注文実行結果
            side: 取引方向（buy/sell）
            amount: 取引数量

        Returns:
            Tuple[float, float]: (final_tp, final_sl)

        Raises:
            CryptoBotError: ATR取得失敗・TP/SL再計算失敗時
        """
        # Phase 38.7: 実約定価格ベースでTP/SL再計算（SL距離5x誤差修正）
        # Phase 51.5-C: TP/SL再計算強化（3段階ATRフォールバック + 再計算必須化）
        actual_filled_price = result.filled_price or result.price

        # 実約定価格でTP/SL価格を再計算
        recalculated_tp = None
        recalculated_sl = None

        if actual_filled_price > 0 and evaluation.take_profit and evaluation.stop_loss:
            from ...strategies.utils.strategy_utils import RiskManager
            from ..core.types import PositionFeeData

            # ATR値とATR履歴を取得（3段階フォールバック）
            market_conditions = getattr(evaluation, "market_conditions", {})
            market_data = market_conditions.get("market_data", {})

            # Phase 61.7: 固定金額TPモード用の手数料データ取得
            fee_data = None
            fixed_amount_enabled = get_threshold(
                "position_management.take_profit.fixed_amount.enabled", False
            )

            if fixed_amount_enabled and self.bitbank_client:
                try:
                    positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")
                    for pos in positions:
                        raw_data = pos.get("raw_data", {})
                        pos_side = raw_data.get("position_side", "")
                        # ポジション方向でマッチング（buy→long, sell→short）
                        if (side == "buy" and pos_side == "long") or (
                            side == "sell" and pos_side == "short"
                        ):
                            fee_data = PositionFeeData.from_api_response(raw_data)
                            self.logger.info(
                                f"📊 Phase 63.2: 手数料データ取得（参考値・TP計算には未使用） - "
                                f"累積手数料={fee_data.unrealized_fee_amount:.0f}円, "
                                f"累積利息={fee_data.unrealized_interest_amount:.0f}円"
                            )
                            break
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Phase 61.7: 手数料データ取得失敗 - フォールバック使用: {e}"
                    )

            current_atr = None
            atr_history = None
            atr_source = None  # デバッグ用：ATR取得元

            # Phase 62.13: Level 0（最優先）- market_conditions["atr_current"]から直接取得
            # RiskManager.evaluate_trade_opportunity()で既に計算・格納済みの値を使用
            atr_current_value = market_conditions.get("atr_current")
            if atr_current_value and atr_current_value > 0:
                current_atr = float(atr_current_value)
                atr_source = "market_conditions[atr_current]"
                self.logger.info(f"📊 Phase 62.13: ATR取得成功 - atr_current={current_atr:.0f}円")

            # Phase 51.5-C → Phase 61.6: 2段階ATRフォールバック（Level 2削除）
            # Level 1: evaluation.market_conditions から取得（後方互換）
            if not current_atr and "15m" in market_data:
                df_15m = market_data["15m"]
                if "atr_14" in df_15m.columns and len(df_15m) > 0:
                    current_atr = float(df_15m["atr_14"].iloc[-1])
                    atr_history = df_15m["atr_14"].dropna().tail(20).tolist()
                    atr_source = "evaluation.market_conditions[15m]"

            if not current_atr and "4h" in market_data:
                df_4h = market_data["4h"]
                if "atr_14" in df_4h.columns and len(df_4h) > 0:
                    current_atr = float(df_4h["atr_14"].iloc[-1])
                    atr_source = "evaluation.market_conditions[4h]"

            # Level 2: thresholds.yaml fallback_atr使用（Phase 61.6: Level 2→削除、Level 3→Level 2に繰り上げ）
            if not current_atr:
                try:
                    fallback_atr = float(get_threshold("risk.fallback_atr", 500000))
                except (ValueError, TypeError):
                    # 型変換失敗時はデフォルト値使用
                    fallback_atr = 500000.0
                    self.logger.warning(
                        "⚠️ Phase 51.5-C: fallback_atr型変換失敗 - デフォルト値500,000円使用"
                    )
                current_atr = fallback_atr
                atr_source = "thresholds.yaml[fallback_atr]"
                self.logger.warning(
                    f"⚠️ Phase 51.5-C: フォールバックATR使用 - fallback_atr={fallback_atr:.0f}円"
                )

            # ATR取得完了（2段階いずれかで取得）
            if current_atr and current_atr > 0:
                # Phase 51.6: TP/SL設定完全渡し（ハードコード削除・設定ファイル一元管理）
                # Phase 52.0: レジーム情報取得追加
                config = {
                    # TP設定（Phase 51.6: TP 0.9%・RR比1.29:1）
                    "take_profit_ratio": get_threshold(
                        "position_management.take_profit.default_ratio"
                    ),
                    "min_profit_ratio": get_threshold(
                        "position_management.take_profit.min_profit_ratio"
                    ),
                    # SL設定（Phase 51.6: SL 0.7%）
                    "max_loss_ratio": get_threshold("position_management.stop_loss.max_loss_ratio"),
                    "min_distance_ratio": get_threshold(
                        "position_management.stop_loss.min_distance.ratio"
                    ),
                    "default_atr_multiplier": get_threshold(
                        "position_management.stop_loss.default_atr_multiplier"
                    ),
                }

                # Phase 52.0: レジーム情報取得
                regime = market_conditions.get("regime", None)
                regime_str = None
                if regime:
                    # RegimeType enumの場合は文字列に変換
                    regime_str = regime.value if hasattr(regime, "value") else str(regime)
                    self.logger.info(f"🎯 Phase 52.0: レジーム情報取得 - {regime_str}")

                # Phase 52.0: レジーム情報を含めてTP/SL計算
                # Phase 58.6: 土日判定用にcurrent_time追加
                # Phase 61.7: 固定金額TP用にfee_data, position_amount追加
                recalculated_sl, recalculated_tp = RiskManager.calculate_stop_loss_take_profit(
                    side,
                    actual_filled_price,
                    current_atr,
                    config,
                    atr_history,
                    regime=regime_str,
                    current_time=self.current_time,
                    fee_data=fee_data,
                    position_amount=amount,
                )

                # 再計算成功時、ログ出力
                if recalculated_sl and recalculated_tp:
                    original_sl = evaluation.stop_loss
                    original_tp = evaluation.take_profit
                    sl_diff = abs(recalculated_sl - original_sl)
                    tp_diff = abs(recalculated_tp - original_tp)

                    # 価格差異計算（entry_priceがある場合）
                    if evaluation.entry_price is not None:
                        entry_price_val = float(evaluation.entry_price)
                        actual_price_val = float(actual_filled_price)
                        price_diff = abs(actual_price_val - entry_price_val)
                        price_info = (
                            f"価格: シグナル時={entry_price_val:.0f}円"
                            f"→実約定={actual_price_val:.0f}円 (差{price_diff:.0f}円) | "
                        )
                    else:
                        actual_price_val = float(actual_filled_price)
                        price_info = f"実約定価格={actual_price_val:.0f}円 | "

                    self.logger.info(
                        f"🔄 Phase 51.5-C: 実約定価格ベースTP/SL再計算完了 - "
                        f"ATR取得元={atr_source}, ATR={current_atr:.0f}円 | "
                        f"{price_info}"
                        f"SL: {original_sl:.0f}円→{recalculated_sl:.0f}円 (差{sl_diff:.0f}円) | "
                        f"TP: {original_tp:.0f}円→{recalculated_tp:.0f}円 (差{tp_diff:.0f}円)"
                    )
                else:
                    # Phase 51.5-C: 再計算失敗時のハンドリング
                    require_recalc = get_threshold("risk.require_tpsl_recalculation", True)
                    if require_recalc:
                        # 再計算必須モード：エントリー中止
                        self.logger.error(
                            f"❌ Phase 51.5-C: TP/SL再計算失敗（require_tpsl_recalculation=True） - "
                            f"ATR={current_atr:.0f}円・エントリー中止"
                        )
                        raise CryptoBotError("TP/SL再計算失敗によりエントリー中止")
                    else:
                        # 再計算任意モード：元のTP/SL使用
                        self.logger.warning(
                            f"⚠️ Phase 51.5-C: TP/SL再計算失敗（RiskManager戻り値None） - "
                            f"ATR={current_atr:.0f}円・元のTP/SL使用継続"
                        )
            else:
                # Phase 51.5-C: ATR取得失敗時のハンドリング
                require_recalc = get_threshold("risk.require_tpsl_recalculation", True)
                if require_recalc:
                    # 再計算必須モード：エントリー中止
                    self.logger.error(
                        f"❌ Phase 51.5-C: ATR取得失敗（require_tpsl_recalculation=True） - "
                        f"current_atr={current_atr}・エントリー中止"
                    )
                    raise CryptoBotError("ATR取得失敗によりエントリー中止")
                else:
                    # 再計算任意モード：元のTP/SL使用
                    self.logger.warning(
                        f"⚠️ Phase 51.5-C: ATR取得失敗（current_atr={current_atr}） - "
                        f"実約定価格ベースTP/SL再計算スキップ・元のTP/SL使用継続"
                    )

        # 再計算された値を使用（失敗時は元の値）
        final_tp = recalculated_tp if recalculated_tp else evaluation.take_profit
        final_sl = recalculated_sl if recalculated_sl else evaluation.stop_loss

        return final_tp, final_sl

    # ========================================
    # Phase 51.6: 原子的エントリー実装（Atomic Entry Pattern）
    # ========================================

    async def _place_tp_with_retry(
        self,
        side: str,
        amount: float,
        entry_price: float,
        take_profit_price: float,
        symbol: str,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 51.6: TP注文配置（Exponential Backoff リトライ）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            take_profit_price: TP価格
            symbol: 通貨ペア
            max_retries: 最大リトライ回数（デフォルト3回）

        Returns:
            Dict: TP注文情報 {"order_id": str, "price": float} or None
        """
        for attempt in range(max_retries):
            try:
                tp_order = await self.stop_manager.place_take_profit(
                    side=side,
                    amount=amount,
                    entry_price=entry_price,
                    take_profit_price=take_profit_price,
                    symbol=symbol,
                    bitbank_client=self.bitbank_client,
                )
                if tp_order:
                    if attempt > 0:
                        self.logger.info(
                            f"✅ Phase 51.6: TP配置成功（試行{attempt + 1}回目） - ID: {tp_order.get('order_id')}"
                        )
                    return tp_order
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ Phase 51.6: TP配置失敗（試行{attempt + 1}/{max_retries}）: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Phase 51.6: TP配置失敗（全{max_retries}回試行）: {e}")
                    raise

        return None

    async def _place_sl_with_retry(
        self,
        side: str,
        amount: float,
        entry_price: float,
        stop_loss_price: float,
        symbol: str,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 51.6: SL注文配置（Exponential Backoff リトライ）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            stop_loss_price: SL価格
            symbol: 通貨ペア
            max_retries: 最大リトライ回数（デフォルト3回）

        Returns:
            Dict: SL注文情報 {"order_id": str, "price": float} or None
        """
        for attempt in range(max_retries):
            try:
                sl_order = await self.stop_manager.place_stop_loss(
                    side=side,
                    amount=amount,
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    symbol=symbol,
                    bitbank_client=self.bitbank_client,
                )
                if sl_order:
                    if attempt > 0:
                        self.logger.info(
                            f"✅ Phase 51.6: SL配置成功（試行{attempt + 1}回目） - ID: {sl_order.get('order_id')}"
                        )
                    return sl_order
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ Phase 51.6: SL配置失敗（試行{attempt + 1}/{max_retries}）: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Phase 51.6: SL配置失敗（全{max_retries}回試行）: {e}")
                    raise

        return None

    async def _cleanup_old_tp_sl_before_entry(
        self,
        side: str,
        symbol: str,
        entry_order_id: str,
    ) -> None:
        """
        Phase 51.10-A: エントリー前の古いTP/SL注文クリーンアップ

        同一ポジション側（BUY or SELL）の古い未約定TP/SL注文を削除する。
        Phase 51.6で実装したAtomic Entry Patternを完全にするための追加機能。

        背景:
        - Phase 51.6実装後、14エントリー → 28個のTP/SL注文が蓄積
        - 既存のcleanup_old_unfilled_orders()は全ポジションのTP/SLを保護するため削除されない
        - bitbank API 30件制限により、古いTP/SL注文が新規注文をブロック（-1.22%異常配置率）

        設計方針:
        - Phase 46思想遵守: 個別TP/SL管理維持
        - Phase 51.6思想完成: Atomic Entry Pattern維持
        - 新規エントリー前に同一側の古いTP/SL注文のみ削除

        Args:
            side: エントリーサイド (buy/sell) - この側の古いTP/SL注文のみ削除
            symbol: 通貨ペア
            entry_order_id: 今回のエントリー注文ID（ログ用）
        """
        try:
            # Phase 53.7: メソッド名修正（get_active_orders → fetch_active_orders）
            # 全アクティブ注文取得
            active_orders = await asyncio.to_thread(
                self.bitbank_client.fetch_active_orders, symbol, 100
            )

            if not active_orders:
                self.logger.debug(f"📋 Phase 51.10-A: アクティブ注文なし - クリーンアップ不要")
                return

            # 同一ポジション側の古いTP/SL注文を検索
            # - BUYエントリー → SELL側のTP（利確）・SELL側のSL（損切）
            # - SELLエントリー → BUY側のTP（利確）・BUY側のSL（損切）
            target_tp_side = "sell" if side == "buy" else "buy"
            target_sl_side = "sell" if side == "buy" else "buy"

            # 現在のアクティブポジションのTP/SL注文IDを取得（保護対象）
            # Phase 58.1: 全ポジションのTP/SL注文を保護（同一側制限を撤廃）
            protected_order_ids = set()
            if self.virtual_positions:
                for pos in self.virtual_positions:
                    # Phase 58.1: 全ポジションのtp_order_id/sl_order_idを保護
                    tp_id = pos.get("tp_order_id")
                    sl_id = pos.get("sl_order_id")
                    if tp_id:
                        protected_order_ids.add(str(tp_id))
                    if sl_id:
                        protected_order_ids.add(str(sl_id))

                    # Phase 53.12: 復元されたポジションのorder_idも保護
                    if pos.get("restored"):
                        order_id = pos.get("order_id")
                        if order_id:
                            protected_order_ids.add(str(order_id))
                            self.logger.debug(
                                f"🛡️ Phase 58.1: 復元ポジション保護 - order_id={order_id}"
                            )

            # Phase 53.12: 保護対象の注文IDをログ出力
            if protected_order_ids:
                self.logger.info(
                    f"🛡️ Phase 53.12: {len(protected_order_ids)}件の注文を保護対象に設定"
                )

            # 削除対象の注文を収集
            # Phase 53.7: CCXTの戻り値形式に合わせてキー名修正（order_id → id）
            orders_to_cancel = []
            for order in active_orders:
                order_id = str(order.get("id", order.get("order_id", "")))
                order_side = order.get("side", "")
                order_type = order.get("type", "")

                # 保護対象の注文はスキップ
                if order_id in protected_order_ids:
                    continue

                # 同一側のTP/SL注文のみ削除対象
                # TP: limit注文 & 反対サイド
                # SL: stop注文 & 反対サイド
                is_tp = order_type == "limit" and order_side == target_tp_side
                is_sl = order_type == "stop" and order_side == target_sl_side

                if is_tp or is_sl:
                    orders_to_cancel.append(
                        {
                            "order_id": order_id,
                            "side": order_side,
                            "type": order_type,
                            "price": order.get("price"),
                        }
                    )

            # 削除実行
            if not orders_to_cancel:
                self.logger.info(
                    f"✅ Phase 51.10-A: クリーンアップ不要 - "
                    f"{side}側の古いTP/SL注文なし（Entry: {entry_order_id}）"
                )
                return

            cancel_success = 0
            cancel_fail = 0

            for order in orders_to_cancel:
                try:
                    await asyncio.to_thread(
                        self.bitbank_client.cancel_order, order["order_id"], symbol
                    )
                    cancel_success += 1
                    self.logger.info(
                        f"🗑️ Phase 51.10-A: 古いTP/SL削除成功 - "
                        f"ID: {order['order_id']}, "
                        f"Type: {order['type']}, "
                        f"Price: {order.get('price', 'N/A')}"
                    )
                except Exception as e:
                    cancel_fail += 1
                    self.logger.warning(
                        f"⚠️ Phase 51.10-A: TP/SL削除失敗（継続） - "
                        f"ID: {order['order_id']}, エラー: {e}"
                    )

            self.logger.info(
                f"✅ Phase 51.10-A: クリーンアップ完了 - "
                f"{side}側 {cancel_success}件削除成功・{cancel_fail}件失敗 "
                f"（Entry: {entry_order_id}）"
            )

        except Exception as e:
            # クリーンアップ失敗してもエントリーは継続（Phase 51.6: L383-385と同様）
            self.logger.warning(
                f"⚠️ Phase 51.10-A: エントリー前クリーンアップ失敗（処理継続） - "
                f"Entry: {entry_order_id}, エラー: {e}"
            )

    async def _rollback_entry(
        self,
        entry_order_id: Optional[str],
        tp_order_id: Optional[str],
        sl_order_id: Optional[str],
        symbol: str,
        error: Exception,
    ) -> None:
        """
        Phase 51.6: Atomic Entry ロールバック

        エントリー・TP・SLのいずれかが失敗した場合、全ての注文をキャンセルする。

        Args:
            entry_order_id: エントリー注文ID
            tp_order_id: TP注文ID（配置済みの場合）
            sl_order_id: SL注文ID（配置済みの場合）
            symbol: 通貨ペア
            error: 発生したエラー
        """
        self.logger.error(
            f"🔄 Phase 51.6: Atomic Entry ロールバック開始 - "
            f"Entry: {entry_order_id}, TP: {tp_order_id}, SL: {sl_order_id}"
        )

        # TP注文キャンセル（配置済みの場合）
        if tp_order_id:
            try:
                await asyncio.to_thread(self.bitbank_client.cancel_order, tp_order_id, symbol)
                self.logger.info(f"✅ Phase 51.6: TP注文キャンセル成功 - ID: {tp_order_id}")
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 51.6: TP注文キャンセル失敗: {e}")

        # SL注文キャンセル（配置済みの場合）
        if sl_order_id:
            try:
                await asyncio.to_thread(self.bitbank_client.cancel_order, sl_order_id, symbol)
                self.logger.info(f"✅ Phase 51.6: SL注文キャンセル成功 - ID: {sl_order_id}")
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 51.6: SL注文キャンセル失敗: {e}")

        # エントリー注文キャンセル（最重要・Phase 57.11: リトライ追加）
        if entry_order_id:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await asyncio.to_thread(
                        self.bitbank_client.cancel_order, entry_order_id, symbol
                    )
                    self.logger.error(
                        f"🚨 Phase 51.6: エントリー注文ロールバック成功 - "
                        f"ID: {entry_order_id}, 理由: {error}"
                        + (f" (試行{attempt + 1}回目)" if attempt > 0 else "")
                    )
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # 1秒, 2秒
                        self.logger.warning(
                            f"⚠️ Phase 57.11: エントリーロールバック失敗（リトライ{attempt + 1}/{max_retries}）: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # 全リトライ失敗は致命的エラー
                        self.logger.critical(
                            f"❌ CRITICAL: エントリー注文キャンセル失敗（手動介入必要） - "
                            f"ID: {entry_order_id}, 全{max_retries}回試行失敗, エラー: {e}"
                        )

    # ========================================
    # Phase 62.9: Maker戦略実装
    # ========================================

    async def _execute_maker_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        maker_config: Dict[str, Any],
    ) -> Optional[ExecutionResult]:
        """
        Phase 62.9: Maker注文実行（リトライ機構付き）

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文数量
            maker_config: Maker戦略設定（price, best_bid, best_ask等）

        Returns:
            ExecutionResult: 成功時は約定結果、失敗時はNone
        """
        from src.core.exceptions import PostOnlyCancelledException

        config = get_threshold("order_execution.maker_strategy", {})
        max_retries = config.get("max_retries", 3)
        retry_interval = config.get("retry_interval_ms", 500) / 1000
        timeout = config.get("timeout_seconds", 30)
        tick = config.get("price_adjustment_tick", 1)
        max_adj = config.get("max_price_adjustment_ratio", 0.001)

        initial_price = maker_config.get("price", 0)
        if initial_price <= 0:
            self.logger.warning("⚠️ Phase 62.9: Maker価格が無効")
            return None

        current_price = initial_price
        start = datetime.now()

        for attempt in range(max_retries):
            elapsed = (datetime.now() - start).total_seconds()
            if elapsed >= timeout:
                self.logger.warning(
                    f"⚠️ Phase 62.9: Makerタイムアウト ({elapsed:.1f}秒 >= {timeout}秒)"
                )
                return None

            try:
                self.logger.info(
                    f"📡 Phase 62.9: Maker注文試行 {attempt + 1}/{max_retries} - "
                    f"{side} {amount:.4f} BTC @ {current_price:.0f}円 (post_only)"
                )

                # post_only指値注文
                order = self.bitbank_client.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="limit",
                    amount=amount,
                    price=current_price,
                    post_only=True,
                )

                order_id = order.get("id")
                if not order_id:
                    self.logger.warning("⚠️ Phase 62.9: 注文IDなし")
                    continue

                # 約定待機
                remaining_timeout = timeout - (datetime.now() - start).total_seconds()
                filled = await self._wait_for_maker_fill(
                    order_id, symbol, max(remaining_timeout, 5)
                )

                if filled:
                    filled_price = filled.get("price", current_price)
                    filled_amount = filled.get("amount", amount)

                    self.logger.info(
                        f"✅ Phase 62.9: Maker約定成功 - "
                        f"ID: {order_id}, 価格: {filled_price:.0f}円, "
                        f"手数料: Maker(-0.02%)"
                    )

                    return ExecutionResult(
                        success=True,
                        mode=ExecutionMode.LIVE,
                        order_id=order_id,
                        price=filled_price,
                        amount=filled_amount,
                        filled_price=filled_price,
                        filled_amount=filled_amount,
                        error_message=None,
                        side=side,
                        fee=0.0,  # Makerリベートは後で計算
                        status=OrderStatus.FILLED,
                        notes="Phase 62.9: Maker約定",
                    )

                # 未約定 → キャンセル
                self.logger.info(f"📡 Phase 62.9: 未約定 - 注文キャンセル試行 (ID: {order_id})")
                try:
                    await asyncio.to_thread(self.bitbank_client.cancel_order, order_id, symbol)
                except Exception as cancel_e:
                    self.logger.warning(
                        f"⚠️ Phase 62.9: キャンセル失敗（約定済みの可能性）: {cancel_e}"
                    )
                    # キャンセル失敗=約定済みの可能性があるので再確認
                    filled = await self._wait_for_maker_fill(order_id, symbol, 2)
                    if filled:
                        return ExecutionResult(
                            success=True,
                            mode=ExecutionMode.LIVE,
                            order_id=order_id,
                            price=filled.get("price", current_price),
                            amount=filled.get("amount", amount),
                            filled_price=filled.get("price", current_price),
                            filled_amount=filled.get("amount", amount),
                            error_message=None,
                            side=side,
                            fee=0.0,
                            status=OrderStatus.FILLED,
                            notes="Phase 62.9: Maker約定（キャンセル後確認）",
                        )

            except PostOnlyCancelledException as e:
                self.logger.info(f"📡 Phase 62.9: post_onlyキャンセル（価格調整） - {e}")

            except Exception as e:
                self.logger.warning(f"⚠️ Phase 62.9: Maker注文エラー: {e}")

            # 価格調整（不利側へ1tick）
            if side.lower() == "buy":
                current_price += tick  # 買いは高く
                if current_price > initial_price * (1 + max_adj):
                    self.logger.warning(
                        f"⚠️ Phase 62.9: 価格調整上限到達 {current_price:.0f} > {initial_price * (1 + max_adj):.0f}"
                    )
                    return None
            else:
                current_price -= tick  # 売りは安く
                if current_price < initial_price * (1 - max_adj):
                    self.logger.warning(
                        f"⚠️ Phase 62.9: 価格調整下限到達 {current_price:.0f} < {initial_price * (1 - max_adj):.0f}"
                    )
                    return None

            await asyncio.sleep(retry_interval)

        self.logger.warning(f"⚠️ Phase 62.9: 最大リトライ回数到達 ({max_retries}回)")
        return None

    async def _wait_for_maker_fill(
        self,
        order_id: str,
        symbol: str,
        timeout: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 62.9: Maker注文の約定待機

        Args:
            order_id: 注文ID
            symbol: 通貨ペア
            timeout: タイムアウト秒数

        Returns:
            Dict: 約定情報（約定時）、None（未約定時）
        """
        check_interval = 0.5  # 500ms間隔でチェック
        start = datetime.now()

        while (datetime.now() - start).total_seconds() < timeout:
            try:
                order = await asyncio.to_thread(self.bitbank_client.fetch_order, order_id, symbol)

                if order:
                    status = order.get("status", "").lower()
                    filled_amount = float(order.get("filled", 0))
                    order_amount = float(order.get("amount", 0))

                    # 完全約定
                    if status == "closed" or (
                        filled_amount > 0 and filled_amount >= order_amount * 0.99
                    ):
                        return {
                            "price": float(order.get("average", order.get("price", 0))),
                            "amount": filled_amount,
                        }

                    # キャンセル済み
                    if status == "canceled":
                        return None

            except Exception as e:
                self.logger.debug(f"📡 Phase 62.9: 注文状態確認エラー: {e}")

            await asyncio.sleep(check_interval)

        return None

    # ========================================
    # Phase 62.20: TP/SL欠損自動復旧
    # ========================================

    def _schedule_tp_sl_verification(
        self,
        entry_order_id: str,
        side: str,
        amount: float,
        entry_price: float,
        tp_order_id: Optional[str],
        sl_order_id: Optional[str],
        symbol: str,
    ) -> None:
        """
        Phase 62.20: TP/SL欠損検証をスケジュール

        Atomic Entry完了後、5分後にTP/SL設置状態を再確認し、
        欠損があれば自動的に再構築する。

        背景:
        - Phase 62.17のSLタイムアウトフォールバック失敗時にSL欠損が発生
        - APIエラー50062などでBot内部状態とbitbank実態が乖離する可能性

        Args:
            entry_order_id: エントリー注文ID
            side: 売買方向（buy/sell）
            amount: ポジション数量
            entry_price: エントリー価格
            tp_order_id: TP注文ID
            sl_order_id: SL注文ID
            symbol: 通貨ペア
        """
        delay_seconds = get_threshold("tp_sl_verification.delay_seconds", 600)  # デフォルト10分

        # Phase 63: Bug 3修正 - asyncio.create_task廃止
        # fire-and-forgetではなく、pending_verificationsに保存し
        # メインサイクルで期限到来分を処理する方式に変更
        self._pending_verifications.append(
            {
                "scheduled_at": datetime.now(timezone.utc),
                "verify_after": datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
                "entry_order_id": entry_order_id,
                "side": side,
                "amount": amount,
                "entry_price": entry_price,
                "expected_tp_order_id": tp_order_id,
                "expected_sl_order_id": sl_order_id,
                "symbol": symbol,
            }
        )

        self.logger.info(
            f"📋 Phase 63: TP/SL検証スケジュール - {delay_seconds}秒後 "
            f"(Entry: {entry_order_id}, pending: {len(self._pending_verifications)}件)"
        )

    async def _process_pending_verifications(self):
        """
        Phase 63: Bug 3修正 - メインサイクルで期限到来の検証を処理

        asyncio.create_taskの代わりに、メインサイクルの各サイクルで
        期限到来分のTP/SL検証を実行する。
        Cloud Runの5分サイクル間でcontainer再起動やイベントループ終了で
        タスクが消失する問題を解決。
        """
        if not self._pending_verifications:
            return

        now = datetime.now(timezone.utc)
        due = [v for v in self._pending_verifications if now >= v["verify_after"]]
        self._pending_verifications = [
            v for v in self._pending_verifications if now < v["verify_after"]
        ]

        if due:
            self.logger.info(f"🔍 Phase 63: TP/SL検証実行 - {len(due)}件期限到来")

        for v in due:
            try:
                await self._verify_and_rebuild_tp_sl(
                    entry_order_id=v["entry_order_id"],
                    side=v["side"],
                    amount=v["amount"],
                    entry_price=v["entry_price"],
                    expected_tp_order_id=v["expected_tp_order_id"],
                    expected_sl_order_id=v["expected_sl_order_id"],
                    symbol=v["symbol"],
                    delay_seconds=0,  # 既に待機済み
                )
            except Exception as e:
                self.logger.error(
                    f"❌ Phase 63: TP/SL検証エラー - Entry: {v['entry_order_id']}, {e}"
                )

    async def _verify_and_rebuild_tp_sl(
        self,
        entry_order_id: str,
        side: str,
        amount: float,
        entry_price: float,
        expected_tp_order_id: Optional[str],
        expected_sl_order_id: Optional[str],
        symbol: str,
        delay_seconds: int,
    ) -> None:
        """
        Phase 62.20: TP/SL欠損検証・自動再構築

        Args:
            entry_order_id: エントリー注文ID
            side: 売買方向（buy/sell）
            amount: ポジション数量
            entry_price: エントリー価格
            expected_tp_order_id: 期待されるTP注文ID
            expected_sl_order_id: 期待されるSL注文ID
            symbol: 通貨ペア
            delay_seconds: 待機秒数
        """
        try:
            # Phase 63: Bug 3修正 - sleepはpending_verifications方式で代替済み
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            self.logger.info(f"🔍 Phase 63: TP/SL検証開始 - Entry: {entry_order_id}")

            # Step 2: ポジション存在確認
            positions = await self.bitbank_client.fetch_margin_positions(symbol)
            if not positions:
                self.logger.info(
                    f"✅ Phase 62.20: ポジションなし（既に決済済み） - Entry: {entry_order_id}"
                )
                return

            # 該当ポジションを探す（side + amount でマッチング）
            # side: buy -> short, sell -> long ではなく、信用取引では逆
            # buy注文 -> longポジション, sell注文 -> shortポジション
            expected_pos_side = "long" if side == "buy" else "short"

            matching_position = None
            for pos in positions:
                pos_side = pos.get("side", "")
                pos_amount = float(pos.get("amount", 0))

                # Phase 63: Bug 2修正 - サイド一致のみでマッチング
                # ポジション集約時に個別エントリー量と集約ポジション量が異なるため
                if pos_side == expected_pos_side and pos_amount > 0:
                    matching_position = pos
                    break

            if not matching_position:
                self.logger.info(
                    f"✅ Phase 62.20: 該当ポジションなし（決済済みまたは変更済み） - "
                    f"Entry: {entry_order_id}"
                )
                return

            # Step 3: アクティブ注文確認（TP/SL存在チェック）
            active_orders = await asyncio.to_thread(self.bitbank_client.fetch_active_orders, symbol)

            has_tp = False
            has_sl = False

            for order in active_orders:
                order_type = order.get("type", "").lower()
                order_id = str(order.get("id", ""))

                # TP（limit注文）
                if order_type == "limit":
                    # 期待されるTP注文IDと一致、または反対方向の決済注文
                    if order_id == expected_tp_order_id:
                        has_tp = True
                    else:
                        # サイドチェック：ポジションと反対方向の指値 = TP候補
                        order_side = order.get("side", "").lower()
                        tp_side = "sell" if side == "buy" else "buy"
                        if order_side == tp_side:
                            has_tp = True

                # SL（stop_limit注文）
                if order_type in ("stop", "stop_limit"):
                    if order_id == expected_sl_order_id:
                        has_sl = True
                    else:
                        # サイドチェック：ポジションと反対方向のストップ = SL候補
                        order_side = order.get("side", "").lower()
                        sl_side = "sell" if side == "buy" else "buy"
                        if order_side == sl_side:
                            has_sl = True

            # Step 4: 欠損があれば再構築
            if has_tp and has_sl:
                self.logger.info(f"✅ Phase 62.20: TP/SL正常設置確認 - Entry: {entry_order_id}")
                return

            # 欠損検出
            missing = []
            if not has_tp:
                missing.append("TP")
            if not has_sl:
                missing.append("SL")

            self.logger.warning(
                f"⚠️ Phase 62.20: TP/SL欠損検出 - {', '.join(missing)} " f"- Entry: {entry_order_id}"
            )

            # エントリー価格をAPIから再取得（精度向上）
            actual_entry_price = float(matching_position.get("avg_price", entry_price))

            # レジーム別TP/SL幅を取得（デフォルト: tight_range）
            regime = "tight_range"  # 保守的なデフォルト
            tp_config = get_threshold(f"position_management.take_profit.regime_based.{regime}", {})
            sl_config = get_threshold(f"position_management.stop_loss.regime_based.{regime}", {})

            tp_ratio = tp_config.get("min_profit_ratio", 0.004)  # 0.4%
            sl_ratio = sl_config.get("max_loss_ratio", 0.004)  # 0.4%

            # Step 5: TP再構築
            if not has_tp:
                if side == "buy":
                    tp_price = actual_entry_price * (1 + tp_ratio)
                else:
                    tp_price = actual_entry_price * (1 - tp_ratio)

                try:
                    tp_order = await self._place_tp_with_retry(
                        side=side,
                        amount=amount,
                        entry_price=actual_entry_price,
                        take_profit_price=tp_price,
                        symbol=symbol,
                        max_retries=3,
                    )
                    if tp_order:
                        self.logger.info(
                            f"✅ Phase 62.20: TP再構築成功 - "
                            f"ID: {tp_order.get('order_id')}, 価格: {tp_price:.0f}円"
                        )
                    else:
                        self.logger.error(f"❌ Phase 62.20: TP再構築失敗 - Entry: {entry_order_id}")
                except Exception as e:
                    self.logger.error(f"❌ Phase 62.20: TP再構築エラー - {e}")

            # Step 6: SL再構築
            if not has_sl:
                if side == "buy":
                    sl_price = actual_entry_price * (1 - sl_ratio)
                else:
                    sl_price = actual_entry_price * (1 + sl_ratio)

                try:
                    sl_order = await self._place_sl_with_retry(
                        side=side,
                        amount=amount,
                        entry_price=actual_entry_price,
                        stop_loss_price=sl_price,
                        symbol=symbol,
                        max_retries=3,
                    )
                    if sl_order:
                        self.logger.info(
                            f"✅ Phase 62.20: SL再構築成功 - "
                            f"ID: {sl_order.get('order_id')}, 価格: {sl_price:.0f}円"
                        )
                    else:
                        self.logger.error(f"❌ Phase 62.20: SL再構築失敗 - Entry: {entry_order_id}")
                except Exception as e:
                    self.logger.error(f"❌ Phase 62.20: SL再構築エラー - {e}")

        except Exception as e:
            self.logger.error(f"❌ Phase 62.20: TP/SL検証エラー - Entry: {entry_order_id}, {e}")
