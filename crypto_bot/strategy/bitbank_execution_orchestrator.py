"""
Bitbank統合実行オーケストレーター
全コンポーネント統一管理・注文フロー最適化・パフォーマンス監視統合
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from ..execution.bitbank_api_rate_limiter import AdvancedAPIRateLimiter
from ..execution.bitbank_fee_guard import BitbankFeeGuard, TradeDecision
from ..execution.bitbank_fee_optimizer import BitbankFeeOptimizer, OrderType
from ..execution.bitbank_order_manager import BitbankOrderManager, OrderPriority
from ..strategy.bitbank_day_trading_strategy import BitbankDayTradingStrategy
from ..strategy.bitbank_integrated_strategy import (
    BitbankIntegratedStrategy,
    TradeSignal,
)
from ..strategy.bitbank_taker_avoidance_strategy import (
    AvoidanceStrategy,
    BitbankTakerAvoidanceStrategy,
)

logger = logging.getLogger(__name__)


class ExecutionPhase(Enum):
    """実行フェーズ"""

    INITIALIZATION = "initialization"
    SIGNAL_ANALYSIS = "signal_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    OPTIMIZATION = "optimization"
    EXECUTION = "execution"
    MONITORING = "monitoring"
    COMPLETION = "completion"


class ExecutionStatus(Enum):
    """実行状態"""

    PENDING = "pending"
    PROCESSING = "processing"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    OPTIMIZED = "optimized"


@dataclass
class ExecutionMetrics:
    """実行メトリクス"""

    total_signals: int = 0
    processed_signals: int = 0
    executed_trades: int = 0
    optimization_count: int = 0
    total_execution_time: float = 0.0
    avg_execution_time: float = 0.0
    fee_optimization_ratio: float = 0.0
    maker_ratio: float = 0.0
    success_rate: float = 0.0

    def update_metrics(
        self, execution_time: float, optimized: bool, is_maker: bool, success: bool
    ):
        """メトリクス更新"""
        self.processed_signals += 1
        self.total_execution_time += execution_time
        self.avg_execution_time = self.total_execution_time / self.processed_signals

        if optimized:
            self.optimization_count += 1
            self.fee_optimization_ratio = (
                self.optimization_count / self.processed_signals
            )

        if success:
            self.executed_trades += 1
            self.success_rate = self.executed_trades / self.processed_signals

        if is_maker:
            # メイカー比率計算（簡易版）
            maker_count = self.executed_trades * self.maker_ratio + (
                1 if is_maker else 0
            )
            self.maker_ratio = maker_count / max(self.executed_trades, 1)


@dataclass
class ExecutionPlan:
    """実行計画"""

    signal: TradeSignal
    execution_id: str
    phase: ExecutionPhase = ExecutionPhase.INITIALIZATION
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None

    # 最適化情報
    optimal_type: Optional[OrderType] = None
    optimized_price: Optional[float] = None
    optimized_amount: Optional[float] = None
    execution_priority: OrderPriority = OrderPriority.MEDIUM
    avoidance_strategy: Optional[AvoidanceStrategy] = None

    # 実行結果
    actual_price: Optional[float] = None
    actual_amount: Optional[float] = None
    actual_fee: Optional[float] = None
    order_id: Optional[str] = None
    position_id: Optional[str] = None

    # パフォーマンス
    execution_time: float = 0.0
    optimization_time: float = 0.0
    fee_saved: float = 0.0

    # ログ・エラー
    execution_log: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def add_log(self, message: str):
        """ログ追加"""
        self.execution_log.append(
            f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]}: {message}"
        )

    def get_execution_duration(self) -> float:
        """実行時間取得"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()


class BitbankExecutionOrchestrator:
    """
    Bitbank統合実行オーケストレーター

    全コンポーネントを統合管理し、最適化された注文フローを実現
    """

    def __init__(self, bitbank_client, config: Optional[Dict] = None):

        self.bitbank_client = bitbank_client
        self.config = config or {}

        # オーケストレーター設定
        orchestrator_config = self.config.get("bitbank_orchestrator", {})
        self.max_concurrent_executions = orchestrator_config.get(
            "max_concurrent_executions", 5
        )
        self.execution_timeout = orchestrator_config.get(
            "execution_timeout", 300
        )  # 5分
        self.retry_attempts = orchestrator_config.get("retry_attempts", 3)
        self.performance_monitoring = orchestrator_config.get(
            "performance_monitoring", True
        )

        # コンポーネント初期化
        self.fee_optimizer = BitbankFeeOptimizer(config)
        self.fee_guard = BitbankFeeGuard(config)
        self.order_manager = BitbankOrderManager(bitbank_client, config)
        self.api_limiter = AdvancedAPIRateLimiter(
            get_limit=10, post_limit=6, max_retries=3
        )
        self.integrated_strategy = BitbankIntegratedStrategy(bitbank_client, config)
        self.taker_avoidance = BitbankTakerAvoidanceStrategy(
            bitbank_client, self.fee_optimizer, self.fee_guard, config
        )
        self.day_trading_strategy = BitbankDayTradingStrategy(
            bitbank_client,
            self.fee_optimizer,
            self.fee_guard,
            self.order_manager,
            config,
        )

        # 実行管理
        self.execution_queue: List[ExecutionPlan] = []
        self.active_executions: Dict[str, ExecutionPlan] = {}
        self.completed_executions: List[ExecutionPlan] = []
        self.execution_counter = 0

        # メトリクス・統計
        self.metrics = ExecutionMetrics()
        self.performance_history: List[Dict] = []

        # 制御・監視
        self.orchestrator_active = False
        self.processing_thread = None
        self.monitoring_thread = None

        logger.info("BitbankExecutionOrchestrator initialized")
        logger.info(f"Max concurrent executions: {self.max_concurrent_executions}")
        logger.info(f"Execution timeout: {self.execution_timeout}s")

    def submit_execution_request(self, signal: TradeSignal) -> str:
        """
        実行リクエスト提出

        Args:
            signal: 取引シグナル

        Returns:
            実行ID
        """
        self.execution_counter += 1
        execution_id = (
            f"exec_{signal.symbol}_{self.execution_counter}_{int(time.time())}"
        )

        execution_plan = ExecutionPlan(signal=signal, execution_id=execution_id)

        execution_plan.add_log(
            f"Execution request submitted: {signal.symbol} "
            f"{signal.side} {signal.amount}"
        )

        self.execution_queue.append(execution_plan)
        self.metrics.total_signals += 1

        logger.info(f"Execution request submitted: {execution_id}")

        # 処理開始
        if not self.orchestrator_active:
            self.start_orchestrator()

        return execution_id

    def start_orchestrator(self) -> None:
        """オーケストレーター開始"""
        if self.orchestrator_active:
            return

        self.orchestrator_active = True

        # 処理スレッド開始
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()

        # 監視スレッド開始
        if self.performance_monitoring:
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()

        # 各コンポーネント開始
        self.integrated_strategy.start_integrated_strategy()
        self.day_trading_strategy.start_monitoring()
        self.order_manager.start_processing()

        logger.info("Orchestrator started")

    def stop_orchestrator(self) -> None:
        """オーケストレーター停止"""
        self.orchestrator_active = False

        # 処理中の実行を完了待ち
        self._wait_for_active_executions()

        # 各コンポーネント停止
        self.integrated_strategy.stop_integrated_strategy()
        self.day_trading_strategy.stop_monitoring()
        self.order_manager.stop_processing()

        logger.info("Orchestrator stopped")

    def _processing_loop(self) -> None:
        """処理メインループ"""
        while self.orchestrator_active:
            try:
                # 実行キューから処理
                if (
                    self.execution_queue
                    and len(self.active_executions) < self.max_concurrent_executions
                ):
                    execution_plan = self.execution_queue.pop(0)
                    self._start_execution(execution_plan)

                # 完了した実行の後処理
                self._cleanup_completed_executions()

                # 短時間待機
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(1)

    def _monitoring_loop(self) -> None:
        """監視メインループ"""
        while self.orchestrator_active:
            try:
                # タイムアウト実行チェック
                self._check_execution_timeouts()

                # パフォーマンス記録
                self._record_performance_metrics()

                # 1分間隔で監視
                time.sleep(60)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)

    def _start_execution(self, execution_plan: ExecutionPlan) -> None:
        """実行開始"""
        execution_plan.phase = ExecutionPhase.SIGNAL_ANALYSIS
        execution_plan.status = ExecutionStatus.PROCESSING
        execution_plan.add_log("Starting execution analysis")

        self.active_executions[execution_plan.execution_id] = execution_plan

        # 非同期実行開始
        execution_thread = threading.Thread(
            target=self._execute_plan, args=(execution_plan,)
        )
        execution_thread.daemon = True
        execution_thread.start()

    def _execute_plan(self, execution_plan: ExecutionPlan) -> None:
        """実行計画実行"""
        start_time = time.time()

        try:
            # Phase 1: Signal Analysis
            execution_plan.phase = ExecutionPhase.SIGNAL_ANALYSIS
            execution_plan.add_log("Analyzing trade signal")

            # Phase 2: Risk Assessment
            execution_plan.phase = ExecutionPhase.RISK_ASSESSMENT
            execution_plan.add_log("Assessing risk")

            risk_assessment = self.fee_guard.evaluate_trade_risk(
                execution_plan.signal.symbol,
                execution_plan.signal.side,
                execution_plan.signal.amount,
                execution_plan.signal.target_price,
                execution_plan.signal.expected_profit,
                OrderType.MAKER,  # 初期仮定
                execution_plan.signal.urgency,
            )

            if risk_assessment.recommended_action == TradeDecision.REJECT:
                execution_plan.status = ExecutionStatus.FAILED
                execution_plan.error_message = (
                    f"Risk assessment rejected: {risk_assessment.reasons}"
                )
                execution_plan.add_log("Execution rejected by risk assessment")
                return

            # Phase 3: Optimization
            execution_plan.phase = ExecutionPhase.OPTIMIZATION
            execution_plan.add_log("Optimizing execution")

            optimization_start = time.time()

            # 手数料最適化
            optimal_type, fee_calc = self.fee_optimizer.calculate_optimal_order_type(
                execution_plan.signal.symbol,
                execution_plan.signal.side,
                execution_plan.signal.amount,
                execution_plan.signal.target_price,
                urgency_level=execution_plan.signal.urgency,
            )

            execution_plan.optimal_type = optimal_type
            execution_plan.optimized_price = execution_plan.signal.target_price
            execution_plan.optimized_amount = execution_plan.signal.amount

            # テイカー回避戦略（必要に応じて）
            if optimal_type == OrderType.TAKER and execution_plan.signal.urgency < 0.7:
                execution_plan.add_log("Attempting taker avoidance")

                avoidance_result = self.taker_avoidance.attempt_taker_avoidance(
                    execution_plan.signal.symbol,
                    execution_plan.signal.side,
                    execution_plan.signal.amount,
                    execution_plan.signal.target_price,
                    execution_plan.signal.urgency,
                )

                if avoidance_result.success:
                    execution_plan.optimal_type = OrderType.MAKER
                    execution_plan.avoidance_strategy = avoidance_result.strategy_used
                    execution_plan.fee_saved = avoidance_result.fee_saved
                    execution_plan.add_log(
                        f"Taker avoidance successful: "
                        f"{avoidance_result.strategy_used.value}"
                    )
                else:
                    execution_plan.add_log(
                        f"Taker avoidance failed: {avoidance_result.reason}"
                    )

            # 優先度設定
            if execution_plan.optimal_type == OrderType.MAKER:
                execution_plan.execution_priority = OrderPriority.HIGH
            else:
                execution_plan.execution_priority = OrderPriority.MEDIUM

            execution_plan.optimization_time = time.time() - optimization_start
            execution_plan.add_log(
                f"Optimization completed in {execution_plan.optimization_time:.2f}s"
            )

            # Phase 4: Execution
            execution_plan.phase = ExecutionPhase.EXECUTION
            execution_plan.add_log("Executing order")

            # API制限管理付きで注文実行
            def _execute_order():
                return self.order_manager.submit_order(
                    symbol=execution_plan.signal.symbol,
                    side=execution_plan.signal.side,
                    type=(
                        "limit"
                        if execution_plan.optimal_type == OrderType.MAKER
                        else "market"
                    ),
                    amount=execution_plan.optimized_amount,
                    price=(
                        execution_plan.optimized_price
                        if execution_plan.optimal_type == OrderType.MAKER
                        else None
                    ),
                    priority=execution_plan.execution_priority,
                )

            success, message, order_id = self.api_limiter.execute_with_limit(
                _execute_order, "POST"
            )

            if success:
                execution_plan.order_id = order_id
                execution_plan.status = ExecutionStatus.EXECUTED
                execution_plan.add_log(f"Order executed successfully: {order_id}")

                # 日次取引戦略でポジション管理
                if execution_plan.signal.side in ["buy", "sell"]:
                    position_success, position_message, position_id = (
                        self.day_trading_strategy.open_position(
                            execution_plan.signal.symbol,
                            execution_plan.signal.side,
                            execution_plan.optimized_amount,
                            execution_plan.optimized_price,
                            reason=f"Orchestrator execution: "
                            f"{execution_plan.execution_id}",
                        )
                    )

                    if position_success:
                        execution_plan.position_id = position_id
                        execution_plan.add_log(f"Position opened: {position_id}")
                    else:
                        execution_plan.add_log(
                            f"Position opening failed: {position_message}"
                        )

                # 手数料パフォーマンス記録
                self.fee_optimizer.track_fee_performance(
                    execution_plan.signal.symbol,
                    execution_plan.signal.side,
                    execution_plan.optimized_amount,
                    execution_plan.optimized_price,
                    fee_calc.expected_fee,
                    execution_plan.optimal_type,
                )

                execution_plan.actual_fee = fee_calc.expected_fee

            else:
                execution_plan.status = ExecutionStatus.FAILED
                execution_plan.error_message = message
                execution_plan.add_log(f"Order execution failed: {message}")

            # Phase 5: Monitoring
            execution_plan.phase = ExecutionPhase.MONITORING
            execution_plan.add_log("Monitoring execution")

            # Phase 6: Completion
            execution_plan.phase = ExecutionPhase.COMPLETION
            execution_plan.end_time = datetime.now()
            execution_plan.execution_time = time.time() - start_time
            execution_plan.add_log(
                f"Execution completed in {execution_plan.execution_time:.2f}s"
            )

            # メトリクス更新
            self.metrics.update_metrics(
                execution_plan.execution_time,
                execution_plan.optimization_time > 0,
                execution_plan.optimal_type == OrderType.MAKER,
                execution_plan.status == ExecutionStatus.EXECUTED,
            )

        except Exception as e:
            execution_plan.status = ExecutionStatus.FAILED
            execution_plan.error_message = str(e)
            execution_plan.end_time = datetime.now()
            execution_plan.execution_time = time.time() - start_time
            execution_plan.add_log(f"Execution failed with exception: {e}")
            logger.error(f"Execution failed: {execution_plan.execution_id} - {e}")

    def _cleanup_completed_executions(self) -> None:
        """完了した実行の後処理"""
        completed_ids = []

        for execution_id, execution_plan in self.active_executions.items():
            if execution_plan.status in [
                ExecutionStatus.EXECUTED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            ]:
                completed_ids.append(execution_id)

        for execution_id in completed_ids:
            execution_plan = self.active_executions.pop(execution_id)
            self.completed_executions.append(execution_plan)

            # 履歴サイズ制限
            if len(self.completed_executions) > 1000:
                self.completed_executions = self.completed_executions[-500:]

    def _check_execution_timeouts(self) -> None:
        """実行タイムアウトチェック"""
        timeout_threshold = datetime.now() - timedelta(seconds=self.execution_timeout)

        for execution_plan in list(self.active_executions.values()):
            if execution_plan.start_time < timeout_threshold:
                execution_plan.status = ExecutionStatus.FAILED
                execution_plan.error_message = "Execution timeout"
                execution_plan.end_time = datetime.now()
                execution_plan.add_log("Execution timed out")
                logger.warning(f"Execution timed out: {execution_plan.execution_id}")

    def _record_performance_metrics(self) -> None:
        """パフォーマンスメトリクス記録"""
        if not self.performance_monitoring:
            return

        # 統合パフォーマンス取得
        integrated_performance = self.integrated_strategy.get_performance_summary()
        fee_performance = self.fee_optimizer.get_fee_performance_summary()
        avoidance_stats = self.taker_avoidance.get_avoidance_statistics()
        day_trading_status = self.day_trading_strategy.get_position_status()

        performance_record = {
            "timestamp": datetime.now().isoformat(),
            "orchestrator_metrics": {
                "total_signals": self.metrics.total_signals,
                "processed_signals": self.metrics.processed_signals,
                "executed_trades": self.metrics.executed_trades,
                "success_rate": self.metrics.success_rate,
                "avg_execution_time": self.metrics.avg_execution_time,
                "fee_optimization_ratio": self.metrics.fee_optimization_ratio,
                "maker_ratio": self.metrics.maker_ratio,
                "active_executions": len(self.active_executions),
                "queue_size": len(self.execution_queue),
            },
            "integrated_performance": integrated_performance,
            "fee_performance": fee_performance,
            "avoidance_stats": avoidance_stats,
            "day_trading_status": day_trading_status,
        }

        self.performance_history.append(performance_record)

        # 履歴サイズ制限
        if len(self.performance_history) > 1440:  # 24時間分（1分間隔）
            self.performance_history = self.performance_history[-720:]  # 12時間分残す

    def _wait_for_active_executions(self) -> None:
        """アクティブな実行の完了待機"""
        timeout = 30  # 30秒でタイムアウト
        start_time = time.time()

        while self.active_executions and (time.time() - start_time) < timeout:
            time.sleep(1)

        if self.active_executions:
            logger.warning(
                f"Force stopping {len(self.active_executions)} active executions"
            )

    def get_execution_status(self, execution_id: str) -> Optional[ExecutionPlan]:
        """実行状況取得"""
        # アクティブな実行から検索
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]

        # 完了した実行から検索
        for execution_plan in self.completed_executions:
            if execution_plan.execution_id == execution_id:
                return execution_plan

        return None

    def get_orchestrator_status(self) -> Dict[str, Any]:
        """オーケストレーター状況取得"""
        return {
            "orchestrator_active": self.orchestrator_active,
            "queue_size": len(self.execution_queue),
            "active_executions": len(self.active_executions),
            "completed_executions": len(self.completed_executions),
            "metrics": {
                "total_signals": self.metrics.total_signals,
                "processed_signals": self.metrics.processed_signals,
                "executed_trades": self.metrics.executed_trades,
                "success_rate": self.metrics.success_rate,
                "avg_execution_time": self.metrics.avg_execution_time,
                "fee_optimization_ratio": self.metrics.fee_optimization_ratio,
                "maker_ratio": self.metrics.maker_ratio,
            },
            "component_status": {
                "fee_optimizer": "active",
                "fee_guard": "active",
                "order_manager": "active",
                "api_limiter": "active",
                "integrated_strategy": "active",
                "taker_avoidance": "active",
                "day_trading_strategy": "active",
            },
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """パフォーマンスレポート取得"""
        if not self.performance_history:
            return {"status": "no_data", "message": "No performance data available"}

        latest_record = self.performance_history[-1]

        # 時系列統計
        if len(self.performance_history) > 1:
            first_record = self.performance_history[0]
            time_span = (
                datetime.fromisoformat(latest_record["timestamp"])
                - datetime.fromisoformat(first_record["timestamp"])
            ).total_seconds() / 3600

            signal_rate = self.metrics.total_signals / max(time_span, 1)
            execution_rate = self.metrics.executed_trades / max(time_span, 1)
        else:
            signal_rate = 0
            execution_rate = 0

        return {
            "reporting_period": {
                "start_time": self.performance_history[0]["timestamp"],
                "end_time": latest_record["timestamp"],
                "duration_hours": len(self.performance_history) / 60,  # 1分間隔想定
            },
            "orchestrator_performance": {
                "signal_processing_rate": signal_rate,
                "execution_rate": execution_rate,
                "success_rate": self.metrics.success_rate,
                "avg_execution_time": self.metrics.avg_execution_time,
                "fee_optimization_effectiveness": self.metrics.fee_optimization_ratio,
                "maker_ratio_achievement": self.metrics.maker_ratio,
            },
            "component_integration": {
                "fee_optimizer": latest_record["fee_performance"],
                "taker_avoidance": latest_record["avoidance_stats"],
                "day_trading": latest_record["day_trading_status"],
            },
            "recommendations": self._generate_performance_recommendations(),
        }

    def _generate_performance_recommendations(self) -> List[str]:
        """パフォーマンス推奨事項生成"""
        recommendations = []

        if self.metrics.success_rate < 0.8:
            recommendations.append(
                "実行成功率が低いです。リスク評価基準の調整を検討してください。"
            )

        if self.metrics.maker_ratio < 0.7:
            recommendations.append(
                "メイカー比率が低いです。テイカー回避戦略の強化が必要です。"
            )

        if self.metrics.avg_execution_time > 10:
            recommendations.append(
                "実行時間が長いです。最適化アルゴリズムの改善を検討してください。"
            )

        if self.metrics.fee_optimization_ratio < 0.5:
            recommendations.append(
                "手数料最適化の使用率が低いです。最適化トリガーの調整が必要です。"
            )

        if len(recommendations) == 0:
            recommendations.append(
                "オーケストレーターは良好に動作しています。現在の設定を維持してください。"
            )

        return recommendations

    def __del__(self):
        """デストラクタ"""
        if self.orchestrator_active:
            self.stop_orchestrator()
