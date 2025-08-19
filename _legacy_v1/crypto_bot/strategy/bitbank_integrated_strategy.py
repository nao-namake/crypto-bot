"""
Bitbank統合戦略システム
手数料最適化・API制限対応・リスク管理を統合した取引戦略
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..execution.bitbank_api_rate_limiter import AdvancedAPIRateLimiter
from ..execution.bitbank_fee_guard import BitbankFeeGuard, TradeDecision
from ..execution.bitbank_fee_optimizer import (
    BitbankFeeOptimizer,
    FeeOptimizationStrategy,
    OrderType,
)
from ..execution.bitbank_order_manager import BitbankOrderManager, OrderPriority
from ..strategy.bitbank_day_trading_strategy import BitbankDayTradingStrategy

logger = logging.getLogger(__name__)


class TradingDecision(Enum):
    """取引判定"""

    EXECUTE = "execute"
    POSTPONE = "postpone"
    REJECT = "reject"
    OPTIMIZE = "optimize"


@dataclass
class TradeSignal:
    """取引シグナル"""

    symbol: str
    side: str  # buy/sell
    amount: float
    target_price: float
    confidence: float
    urgency: float
    timestamp: datetime
    source: str  # ML, momentum, etc.
    expected_profit: float

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class OptimizedTradeExecution:
    """最適化された取引実行"""

    original_signal: TradeSignal
    optimized_type: OrderType
    optimized_price: float
    optimized_amount: float
    execution_priority: OrderPriority
    fee_optimization_strategy: FeeOptimizationStrategy
    expected_fee: float
    risk_level: str
    execution_reason: str
    modifications: Dict[str, Any]


class BitbankIntegratedStrategy:
    """
    Bitbank統合戦略システム

    全コンポーネントを統合し、メイカー手数料-0.02%を最大限活用する
    統合取引戦略を実装
    """

    def __init__(self, bitbank_client, config: Optional[Dict] = None):

        self.bitbank_client = bitbank_client
        self.config = config or {}

        # 統合設定
        integrated_config = self.config.get("bitbank_integrated_strategy", {})
        self.maker_preference_threshold = integrated_config.get(
            "maker_preference_threshold", 0.8
        )
        self.fee_optimization_priority = integrated_config.get(
            "fee_optimization_priority", True
        )
        self.max_daily_trades = integrated_config.get("max_daily_trades", 100)
        self.min_profit_ratio = integrated_config.get(
            "min_profit_ratio", 0.0015
        )  # 0.15%

        # コンポーネント初期化
        self.fee_optimizer = BitbankFeeOptimizer(config)
        self.fee_guard = BitbankFeeGuard(config)
        self.order_manager = BitbankOrderManager(bitbank_client, config)
        self.api_limiter = AdvancedAPIRateLimiter(
            get_limit=10, post_limit=6, max_retries=3
        )
        self.day_trading_strategy = BitbankDayTradingStrategy(
            bitbank_client,
            self.fee_optimizer,
            self.fee_guard,
            self.order_manager,
            config,
        )

        # 統計情報
        self.daily_stats = {
            "total_signals": 0,
            "executed_trades": 0,
            "rejected_trades": 0,
            "optimized_trades": 0,
            "maker_trades": 0,
            "taker_trades": 0,
            "total_fees_saved": 0.0,
            "total_profit": 0.0,
            "success_rate": 0.0,
        }

        # 信号処理履歴
        self.signal_history: List[TradeSignal] = []
        self.execution_history: List[OptimizedTradeExecution] = []

        # 制御フラグ
        self.active = False
        self.processing_thread = None

        logger.info("BitbankIntegratedStrategy initialized")
        logger.info(f"Maker preference threshold: {self.maker_preference_threshold}")
        logger.info(f"Fee optimization priority: {self.fee_optimization_priority}")

    def process_trade_signal(
        self, signal: TradeSignal
    ) -> Tuple[TradingDecision, Optional[OptimizedTradeExecution]]:
        """
        取引信号を処理し、最適化された実行プランを生成

        Args:
            signal: 取引シグナル

        Returns:
            (取引判定, 最適化実行プラン)
        """
        self.daily_stats["total_signals"] += 1
        self.signal_history.append(signal)

        logger.info(
            f"Processing signal: {signal.symbol} {signal.side} "
            f"{signal.amount} @ {signal.target_price}"
        )

        # 1. 日次制限チェック
        if not self.day_trading_strategy.can_open_position():
            logger.warning(
                "Cannot open position: market closed or position limit reached"
            )
            return TradingDecision.REJECT, None

        # 2. 手数料最適化計算
        optimal_type, fee_calc = self.fee_optimizer.calculate_optimal_order_type(
            signal.symbol,
            signal.side,
            signal.amount,
            signal.target_price,
            urgency_level=signal.urgency,
            market_volatility=0.01,
        )

        # 3. 手数料リスク評価
        risk_assessment = self.fee_guard.evaluate_trade_risk(
            signal.symbol,
            signal.side,
            signal.amount,
            signal.target_price,
            signal.expected_profit,
            optimal_type,
            signal.urgency,
        )

        # 4. 統合判定
        decision, optimized_execution = self._make_integrated_decision(
            signal, optimal_type, fee_calc, risk_assessment
        )

        # 5. 統計更新
        self._update_statistics(decision, optimized_execution)

        logger.info(f"Decision: {decision.value}")
        if optimized_execution:
            logger.info(
                f"Optimized: {optimized_execution.optimized_type.value} @ "
                f"{optimized_execution.optimized_price}"
            )

        return decision, optimized_execution

    def execute_optimized_trade(
        self, execution: OptimizedTradeExecution
    ) -> Tuple[bool, str]:
        """
        最適化された取引を実行

        Args:
            execution: 最適化された実行プラン

        Returns:
            (成功/失敗, メッセージ)
        """
        try:
            # API制限チェック付きで実行
            def _execute_order():
                return self.order_manager.submit_order(
                    symbol=execution.original_signal.symbol,
                    side=execution.original_signal.side,
                    type=(
                        "limit"
                        if execution.optimized_type == OrderType.MAKER
                        else "market"
                    ),
                    amount=execution.optimized_amount,
                    price=(
                        execution.optimized_price
                        if execution.optimized_type == OrderType.MAKER
                        else None
                    ),
                    priority=execution.execution_priority,
                )

            # API制限管理付きで実行
            success, message, order_id = self.api_limiter.execute_with_limit(
                _execute_order, "POST"
            )

            if success:
                # 日次取引戦略でポジション管理
                if execution.original_signal.side in ["buy", "sell"]:
                    position_success, position_message, position_id = (
                        self.day_trading_strategy.open_position(
                            execution.original_signal.symbol,
                            execution.original_signal.side,
                            execution.optimized_amount,
                            execution.optimized_price,
                            reason=f"Integrated strategy: {execution.execution_reason}",
                        )
                    )

                    if position_success:
                        logger.info(f"Position opened: {position_id}")

                # 実行履歴に追加
                self.execution_history.append(execution)
                self.daily_stats["executed_trades"] += 1

                # 手数料パフォーマンス追跡
                self.fee_optimizer.track_fee_performance(
                    execution.original_signal.symbol,
                    execution.original_signal.side,
                    execution.optimized_amount,
                    execution.optimized_price,
                    execution.expected_fee,
                    execution.optimized_type,
                )

                return True, f"Trade executed: {order_id}"
            else:
                return False, f"Order failed: {message}"

        except Exception as e:
            logger.error(f"Failed to execute optimized trade: {e}")
            return False, f"Execution error: {e}"

    def _make_integrated_decision(
        self, signal: TradeSignal, optimal_type: OrderType, fee_calc, risk_assessment
    ) -> Tuple[TradingDecision, Optional[OptimizedTradeExecution]]:
        """
        統合判定ロジック

        Args:
            signal: 取引シグナル
            optimal_type: 最適注文タイプ
            fee_calc: 手数料計算結果
            risk_assessment: リスク評価結果

        Returns:
            (判定, 最適化実行プラン)
        """
        # 1. 高リスクの場合は拒否
        if risk_assessment.recommended_action == TradeDecision.REJECT:
            self.daily_stats["rejected_trades"] += 1
            logger.warning(f"Trade rejected: {risk_assessment.reasons}")
            return TradingDecision.REJECT, None

        # 2. 手数料負けチェック
        if self.fee_guard.should_block_trade(
            signal.symbol, signal.expected_profit, fee_calc.expected_fee, optimal_type
        )[0]:
            self.daily_stats["rejected_trades"] += 1
            logger.warning("Trade blocked by fee guard")
            return TradingDecision.REJECT, None

        # 3. メイカー優先判定
        execution_priority = OrderPriority.MEDIUM
        execution_reason = "standard_execution"

        if optimal_type == OrderType.MAKER:
            execution_priority = OrderPriority.HIGH
            execution_reason = "maker_fee_optimization"
            self.daily_stats["maker_trades"] += 1
        else:
            self.daily_stats["taker_trades"] += 1

            # テイカー注文の場合、緊急度が低ければメイカーに変更を試行
            if signal.urgency < self.maker_preference_threshold:
                optimal_type = OrderType.MAKER
                execution_priority = OrderPriority.HIGH
                execution_reason = "converted_to_maker"
                logger.info("Converted taker to maker order for fee optimization")

        # 4. 最適化実行プラン作成
        optimized_execution = OptimizedTradeExecution(
            original_signal=signal,
            optimized_type=optimal_type,
            optimized_price=signal.target_price,
            optimized_amount=signal.amount,
            execution_priority=execution_priority,
            fee_optimization_strategy=(
                FeeOptimizationStrategy.MAKER_PRIORITY
                if optimal_type == OrderType.MAKER
                else FeeOptimizationStrategy.BALANCED
            ),
            expected_fee=fee_calc.expected_fee,
            risk_level=risk_assessment.risk_level.value,
            execution_reason=execution_reason,
            modifications=risk_assessment.suggested_modifications,
        )

        # 5. 最終判定
        if risk_assessment.recommended_action == TradeDecision.MODIFY:
            self.daily_stats["optimized_trades"] += 1
            return TradingDecision.OPTIMIZE, optimized_execution
        else:
            return TradingDecision.EXECUTE, optimized_execution

    def _update_statistics(
        self, decision: TradingDecision, execution: Optional[OptimizedTradeExecution]
    ) -> None:
        """統計情報更新"""
        if execution:
            # 手数料節約効果計算
            taker_fee = execution.optimized_amount * execution.optimized_price * 0.0012
            actual_fee = execution.expected_fee
            fee_saved = taker_fee - actual_fee

            self.daily_stats["total_fees_saved"] += fee_saved
            self.daily_stats[
                "total_profit"
            ] += execution.original_signal.expected_profit

        # 成功率計算
        if self.daily_stats["total_signals"] > 0:
            self.daily_stats["success_rate"] = (
                self.daily_stats["executed_trades"] / self.daily_stats["total_signals"]
            )

    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリー取得"""
        # 手数料最適化効果
        fee_performance = self.fee_optimizer.get_fee_performance_summary()

        # 日次取引状況
        day_trading_status = self.day_trading_strategy.get_position_status()

        # API制限状況
        api_status = self.api_limiter.get_status()

        return {
            "strategy_performance": {
                "daily_stats": self.daily_stats.copy(),
                "maker_ratio": self.daily_stats["maker_trades"]
                / max(self.daily_stats["total_signals"], 1),
                "optimization_effectiveness": self.daily_stats["optimized_trades"]
                / max(self.daily_stats["total_signals"], 1),
                "fee_saved_per_trade": self.daily_stats["total_fees_saved"]
                / max(self.daily_stats["executed_trades"], 1),
                "average_profit_per_trade": self.daily_stats["total_profit"]
                / max(self.daily_stats["executed_trades"], 1),
            },
            "fee_optimization": fee_performance,
            "day_trading": day_trading_status,
            "api_management": api_status,
            "integration_health": {
                "components_active": True,
                "last_signal_time": (
                    self.signal_history[-1].timestamp.isoformat()
                    if self.signal_history
                    else None
                ),
                "signal_processing_rate": len(self.signal_history)
                / 24.0,  # signals per hour
                "execution_success_rate": self.daily_stats["success_rate"],
            },
        }

    def start_integrated_strategy(self) -> None:
        """統合戦略開始"""
        self.active = True

        # 日次取引戦略監視開始
        self.day_trading_strategy.start_monitoring()

        # 注文管理開始
        self.order_manager.start_processing()

        logger.info("Integrated strategy started")

    def stop_integrated_strategy(self) -> None:
        """統合戦略停止"""
        self.active = False

        # 全ポジション決済
        self.day_trading_strategy.close_all_positions("strategy_stop")

        # 各コンポーネント停止
        self.day_trading_strategy.stop_monitoring()
        self.order_manager.stop_processing()

        logger.info("Integrated strategy stopped")

    def reset_daily_stats(self) -> None:
        """日次統計リセット"""
        self.daily_stats = {
            "total_signals": 0,
            "executed_trades": 0,
            "rejected_trades": 0,
            "optimized_trades": 0,
            "maker_trades": 0,
            "taker_trades": 0,
            "total_fees_saved": 0.0,
            "total_profit": 0.0,
            "success_rate": 0.0,
        }

        # 各コンポーネントの統計もリセット
        self.day_trading_strategy.reset_daily_stats()
        self.api_limiter.reset_stats()

        # 履歴クリア
        self.signal_history.clear()
        self.execution_history.clear()

        logger.info("Daily stats reset")

    def get_maker_fee_optimization_report(self) -> Dict[str, Any]:
        """メイカー手数料最適化レポート"""
        total_trades = self.daily_stats["executed_trades"]
        if total_trades == 0:
            return {"status": "no_trades", "message": "No trades executed yet"}

        maker_ratio = self.daily_stats["maker_trades"] / total_trades
        fee_saved_per_trade = self.daily_stats["total_fees_saved"] / total_trades

        # 理論的最大節約額（全てテイカーだった場合との比較）
        theoretical_max_savings = total_trades * 0.0014  # 0.14% difference
        optimization_efficiency = (
            self.daily_stats["total_fees_saved"] / theoretical_max_savings
            if theoretical_max_savings > 0
            else 0
        )

        return {
            "optimization_summary": {
                "total_trades": total_trades,
                "maker_trades": self.daily_stats["maker_trades"],
                "taker_trades": self.daily_stats["taker_trades"],
                "maker_ratio": maker_ratio,
                "target_maker_ratio": 0.8,  # 目標80%
                "maker_ratio_achievement": maker_ratio / 0.8,
            },
            "fee_savings": {
                "total_fees_saved": self.daily_stats["total_fees_saved"],
                "average_savings_per_trade": fee_saved_per_trade,
                "theoretical_max_savings": theoretical_max_savings,
                "optimization_efficiency": optimization_efficiency,
            },
            "recommendations": self._generate_optimization_recommendations(
                maker_ratio, optimization_efficiency
            ),
        }

    def _generate_optimization_recommendations(
        self, maker_ratio: float, efficiency: float
    ) -> List[str]:
        """最適化推奨事項生成"""
        recommendations = []

        if maker_ratio < 0.7:
            recommendations.append(
                "メイカー比率が低いです。緊急度の低い取引でメイカー注文を増やしてください。"
            )

        if efficiency < 0.6:
            recommendations.append(
                "手数料最適化効率が低いです。注文タイプ選択アルゴリズムの調整が必要です。"
            )

        if (
            self.daily_stats["rejected_trades"]
            > self.daily_stats["executed_trades"] * 0.2
        ):
            recommendations.append(
                "取引拒否率が高いです。リスク閾値の調整を検討してください。"
            )

        if len(recommendations) == 0:
            recommendations.append(
                "手数料最適化が効果的に機能しています。現在の設定を維持してください。"
            )

        return recommendations

    def __del__(self):
        """デストラクタ"""
        if self.active:
            self.stop_integrated_strategy()
