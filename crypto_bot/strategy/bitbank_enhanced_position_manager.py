"""
Bitbank強化建玉管理システム
自動決済期限管理・金利回避スケジューリング・ポジション最適化
"""

# import asyncio  # unused
import logging
import math
import threading
import time as time_module
from collections import deque
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

# import pandas as pd  # unused
# import pytz  # unused
import numpy as np

from ..execution.bitbank_fee_guard import BitbankFeeGuard
from ..execution.bitbank_fee_optimizer import BitbankFeeOptimizer
from ..execution.bitbank_order_manager import BitbankOrderManager
from ..strategy.bitbank_day_trading_strategy import BitbankDayTradingStrategy, Position

logger = logging.getLogger(__name__)


class PositionPriority(Enum):
    """ポジション優先度"""

    CRITICAL = "critical"  # 緊急決済必要
    HIGH = "high"  # 高優先度
    MEDIUM = "medium"  # 中優先度
    LOW = "low"  # 低優先度
    MONITORING = "monitoring"  # 監視のみ


class InterestAccrualMode(Enum):
    """金利発生モード"""

    NONE = "none"  # 金利発生なし
    DAILY = "daily"  # 日次発生
    HOURLY = "hourly"  # 時間毎発生
    CONTINUOUS = "continuous"  # 継続発生


class OptimizationTarget(Enum):
    """最適化目標"""

    PROFIT_MAXIMIZATION = "profit_maximization"  # 利益最大化
    RISK_MINIMIZATION = "risk_minimization"  # リスク最小化
    INTEREST_AVOIDANCE = "interest_avoidance"  # 金利回避
    FEE_OPTIMIZATION = "fee_optimization"  # 手数料最適化
    BALANCED = "balanced"  # バランス型


@dataclass
class PositionOptimizationConfig:
    """ポジション最適化設定"""

    target: OptimizationTarget = OptimizationTarget.BALANCED
    max_holding_hours: int = 18  # 最大保有時間
    interest_threshold: float = 0.0002  # 金利閾値 (0.02%)
    profit_target: float = 0.01  # 利益目標 (1%)
    stop_loss: float = -0.02  # 損切り (-2%)
    position_size_limits: Tuple[float, float] = (0.001, 1.0)  # ポジションサイズ制限
    rebalance_interval: int = 3600  # リバランス間隔 (秒)
    volatility_adjustment: bool = True  # ボラティリティ調整
    correlation_check: bool = True  # 相関チェック


@dataclass
class InterestSchedule:
    """金利スケジュール"""

    position_id: str
    symbol: str
    interest_rate: float
    accrual_mode: InterestAccrualMode
    start_time: datetime
    next_accrual: datetime
    accumulated_interest: float = 0.0
    projected_interest: float = 0.0
    avoidance_deadline: Optional[datetime] = None


@dataclass
class PositionOptimizationResult:
    """ポジション最適化結果"""

    position_id: str
    original_priority: PositionPriority
    optimized_priority: PositionPriority
    recommended_action: str
    target_close_time: Optional[datetime]
    risk_score: float
    profit_potential: float
    interest_cost: float
    optimization_score: float
    reasoning: str


class BitbankEnhancedPositionManager(BitbankDayTradingStrategy):
    """
    Bitbank強化建玉管理システム

    自動決済期限管理・金利回避スケジューリング・ポジション最適化を実現
    """

    def __init__(
        self,
        bitbank_client,
        fee_optimizer: BitbankFeeOptimizer,
        fee_guard: BitbankFeeGuard,
        order_manager: BitbankOrderManager,
        config: Optional[Dict] = None,
    ):

        # 基底クラス初期化
        super().__init__(
            bitbank_client, fee_optimizer, fee_guard, order_manager, config
        )

        # 強化設定
        enhanced_config = self.config.get("bitbank_enhanced_position_manager", {})
        self.optimization_config = PositionOptimizationConfig(
            target=OptimizationTarget(
                enhanced_config.get("optimization_target", "balanced")
            ),
            max_holding_hours=enhanced_config.get("max_holding_hours", 18),
            interest_threshold=enhanced_config.get("interest_threshold", 0.0002),
            profit_target=enhanced_config.get("profit_target", 0.01),
            stop_loss=enhanced_config.get("stop_loss", -0.02),
            position_size_limits=tuple(
                enhanced_config.get("position_size_limits", [0.001, 1.0])
            ),
            rebalance_interval=enhanced_config.get("rebalance_interval", 3600),
            volatility_adjustment=enhanced_config.get("volatility_adjustment", True),
            correlation_check=enhanced_config.get("correlation_check", True),
        )

        # 強化管理システム
        self.position_priorities: Dict[str, PositionPriority] = {}
        self.interest_schedules: Dict[str, InterestSchedule] = {}
        self.optimization_history: List[PositionOptimizationResult] = []

        # 市場データキャッシュ
        self.market_data_cache: Dict[str, Dict] = {}
        self.volatility_cache: Dict[str, deque] = {}
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}

        # 最適化スレッド
        self.optimization_thread = None
        self.optimization_active = False

        # パフォーマンス追跡
        self.enhanced_metrics = {
            "positions_optimized": 0,
            "interest_avoided_total": 0.0,
            "optimization_decisions": 0,
            "profit_improvements": 0.0,
            "risk_reductions": 0.0,
            "average_holding_time": 0.0,
            "position_success_rate": 0.0,
        }

        logger.info("BitbankEnhancedPositionManager initialized")
        logger.info(f"Optimization target: {self.optimization_config.target.value}")
        logger.info(f"Max holding hours: {self.optimization_config.max_holding_hours}")
        logger.info(
            f"Interest threshold: {self.optimization_config.interest_threshold:.4f}"
        )

    def open_position(
        self, symbol: str, side: str, amount: float, price: float, reason: str = ""
    ) -> Tuple[bool, str, Optional[str]]:
        """
        強化ポジション開設

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 価格
            reason: 開設理由

        Returns:
            (成功/失敗, メッセージ, ポジションID)
        """
        # 1. ポジションサイズ最適化
        optimized_amount = self._optimize_position_size(symbol, side, amount, price)

        # 2. 基底クラスでポジション開設
        success, message, position_id = super().open_position(
            symbol, side, optimized_amount, price, reason
        )

        if success and position_id:
            # 3. 強化管理システムに追加
            self._initialize_enhanced_position(
                position_id, symbol, side, optimized_amount, price
            )

            # 4. 最適化スレッド開始
            if not self.optimization_active:
                self.start_optimization()

        return success, message, position_id

    def _initialize_enhanced_position(
        self, position_id: str, symbol: str, side: str, amount: float, price: float
    ) -> None:
        """強化ポジション初期化"""
        # 1. 初期優先度設定
        initial_priority = self._calculate_initial_priority(symbol, side, amount, price)
        self.position_priorities[position_id] = initial_priority

        # 2. 金利スケジュール作成
        interest_schedule = self._create_interest_schedule(
            position_id, symbol, amount, price
        )
        self.interest_schedules[position_id] = interest_schedule

        # 3. 市場データ初期化
        self._initialize_market_data(symbol)

        logger.info(f"Enhanced position initialized: {position_id}")
        logger.info(f"Initial priority: {initial_priority.value}")
        logger.info(
            f"Interest avoidance deadline: {interest_schedule.avoidance_deadline}"
        )

    def _optimize_position_size(
        self, symbol: str, side: str, amount: float, price: float
    ) -> float:
        """ポジションサイズ最適化"""
        # 1. 基本制限チェック
        min_size, max_size = self.optimization_config.position_size_limits
        amount = max(min_size, min(max_size, amount))

        # 2. ボラティリティ調整
        if self.optimization_config.volatility_adjustment:
            volatility = self._get_volatility(symbol)
            if volatility > 0.02:  # 2%以上の高ボラティリティ
                amount *= 0.8  # 20%削減
            elif volatility < 0.005:  # 0.5%以下の低ボラティリティ
                amount *= 1.2  # 20%増加

        # 3. 相関チェック
        if self.optimization_config.correlation_check:
            correlation_adjustment = self._calculate_correlation_adjustment(
                symbol, side
            )
            amount *= correlation_adjustment

        # 4. 最適化目標別調整
        if self.optimization_config.target == OptimizationTarget.RISK_MINIMIZATION:
            amount *= 0.7  # リスク最小化
        elif self.optimization_config.target == OptimizationTarget.PROFIT_MAXIMIZATION:
            amount *= 1.3  # 利益最大化

        # 5. 最終制限チェック
        return max(min_size, min(max_size, amount))

    def _calculate_initial_priority(
        self, symbol: str, side: str, amount: float, price: float
    ) -> PositionPriority:
        """初期優先度計算"""
        # 1. 金利コスト評価
        daily_interest = amount * price * self.day_config.daily_interest_rate

        # 2. 市場状況評価
        volatility = self._get_volatility(symbol)

        # 3. ポジションサイズ評価
        notional = amount * price

        # 4. 優先度決定
        if daily_interest > self.optimization_config.interest_threshold * notional:
            return PositionPriority.HIGH
        elif volatility > 0.03:  # 3%以上の高ボラティリティ
            return PositionPriority.MEDIUM
        elif notional > 100000:  # 10万円以上の大口
            return PositionPriority.MEDIUM
        else:
            return PositionPriority.LOW

    def _create_interest_schedule(
        self, position_id: str, symbol: str, amount: float, price: float
    ) -> InterestSchedule:
        """金利スケジュール作成"""
        now = datetime.now(self.timezone)
        notional = amount * price
        daily_rate = self.day_config.daily_interest_rate

        # 次回発生時刻計算
        next_accrual = now + timedelta(days=1)
        next_accrual = next_accrual.replace(hour=0, minute=0, second=0, microsecond=0)

        # 金利回避期限計算
        avoidance_deadline = next_accrual - timedelta(hours=2)  # 2時間前

        # 予想金利計算
        projected_daily_interest = notional * daily_rate

        return InterestSchedule(
            position_id=position_id,
            symbol=symbol,
            interest_rate=daily_rate,
            accrual_mode=InterestAccrualMode.DAILY,
            start_time=now,
            next_accrual=next_accrual,
            accumulated_interest=0.0,
            projected_interest=projected_daily_interest,
            avoidance_deadline=avoidance_deadline,
        )

    def _get_volatility(self, symbol: str) -> float:
        """ボラティリティ取得"""
        try:
            # キャッシュチェック
            if symbol in self.volatility_cache:
                prices = self.volatility_cache[symbol]
                if len(prices) >= 2:
                    returns = [
                        math.log(prices[i] / prices[i - 1])
                        for i in range(1, len(prices))
                    ]
                    return np.std(returns) * math.sqrt(24)  # 日次ボラティリティ

            # 新規取得
            ohlcv = self.bitbank_client.fetch_ohlcv(symbol, "1h", limit=24)
            prices = [candle[4] for candle in ohlcv]  # 終値

            if symbol not in self.volatility_cache:
                self.volatility_cache[symbol] = deque(maxlen=24)

            self.volatility_cache[symbol].extend(prices)

            if len(prices) >= 2:
                returns = [
                    math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))
                ]
                return np.std(returns) * math.sqrt(24)

            return 0.01  # デフォルト値

        except Exception as e:
            logger.error(f"Failed to get volatility for {symbol}: {e}")
            return 0.01

    def _calculate_correlation_adjustment(self, symbol: str, side: str) -> float:
        """相関調整計算"""
        try:
            # 既存ポジションとの相関チェック
            total_exposure = 0.0

            for _position_id, position in self.active_positions.items():
                if position.symbol == symbol and position.side == side:
                    total_exposure += position.amount * position.entry_price

            # 過度の集中を回避
            if total_exposure > 50000:  # 5万円以上
                return 0.5  # 50%削減
            elif total_exposure > 20000:  # 2万円以上
                return 0.8  # 20%削減

            return 1.0  # 調整なし

        except Exception as e:
            logger.error(f"Failed to calculate correlation adjustment: {e}")
            return 1.0

    def _initialize_market_data(self, symbol: str) -> None:
        """市場データ初期化"""
        try:
            ticker = self.bitbank_client.fetch_ticker(symbol)
            self.market_data_cache[symbol] = {
                "last_price": ticker["last"],
                "bid": ticker["bid"],
                "ask": ticker["ask"],
                "volume": ticker["quoteVolume"],
                "timestamp": datetime.now(),
            }
        except Exception as e:
            logger.error(f"Failed to initialize market data for {symbol}: {e}")

    def optimize_positions(self) -> List[PositionOptimizationResult]:
        """ポジション最適化実行"""
        optimization_results = []

        for position_id, position in self.active_positions.items():
            try:
                result = self._optimize_single_position(position_id, position)
                optimization_results.append(result)

                # 最適化アクション実行
                self._execute_optimization_action(result)

            except Exception as e:
                logger.error(f"Failed to optimize position {position_id}: {e}")

        # 最適化履歴に追加
        self.optimization_history.extend(optimization_results)

        # 履歴サイズ制限
        if len(self.optimization_history) > 1000:
            self.optimization_history = self.optimization_history[-500:]

        # メトリクス更新
        self.enhanced_metrics["optimization_decisions"] += len(optimization_results)

        return optimization_results

    def _optimize_single_position(
        self, position_id: str, position: Position
    ) -> PositionOptimizationResult:
        """単一ポジション最適化"""
        # 1. 現在の優先度取得
        current_priority = self.position_priorities.get(
            position_id, PositionPriority.MEDIUM
        )

        # 2. 市場データ更新
        current_price = self._get_current_price(position.symbol)
        if current_price is None:
            current_price = position.entry_price

        # 3. リスクスコア計算
        risk_score = self._calculate_risk_score(position, current_price)

        # 4. 利益ポテンシャル計算
        profit_potential = self._calculate_profit_potential(position, current_price)

        # 5. 金利コスト計算
        interest_cost = self._calculate_interest_cost(position_id, position)

        # 6. 最適化スコア計算
        optimization_score = self._calculate_optimization_score(
            risk_score, profit_potential, interest_cost
        )

        # 7. 最適化済み優先度決定
        optimized_priority = self._determine_optimized_priority(
            position, risk_score, profit_potential, interest_cost
        )

        # 8. 推奨アクション決定
        recommended_action = self._determine_recommended_action(
            position, optimized_priority, risk_score, profit_potential
        )

        # 9. 目標決済時間計算
        target_close_time = self._calculate_target_close_time(
            position, optimized_priority, interest_cost
        )

        # 10. 理由生成
        reasoning = self._generate_optimization_reasoning(
            position, risk_score, profit_potential, interest_cost, recommended_action
        )

        return PositionOptimizationResult(
            position_id=position_id,
            original_priority=current_priority,
            optimized_priority=optimized_priority,
            recommended_action=recommended_action,
            target_close_time=target_close_time,
            risk_score=risk_score,
            profit_potential=profit_potential,
            interest_cost=interest_cost,
            optimization_score=optimization_score,
            reasoning=reasoning,
        )

    def _calculate_risk_score(self, position: Position, current_price: float) -> float:
        """リスクスコア計算"""
        # 1. 価格変動リスク
        price_change = abs(current_price - position.entry_price) / position.entry_price
        price_risk = min(price_change * 10, 1.0)  # 0-1に正規化

        # 2. 時間リスク
        holding_time = position.get_holding_time()
        time_risk = min(holding_time.total_seconds() / (24 * 3600), 1.0)  # 24時間で1.0

        # 3. ボラティリティリスク
        volatility = self._get_volatility(position.symbol)
        vol_risk = min(volatility * 10, 1.0)  # 10%で1.0

        # 4. 流動性リスク
        try:
            orderbook = self.bitbank_client.fetch_order_book(position.symbol)
            spread = (orderbook["asks"][0][0] - orderbook["bids"][0][0]) / orderbook[
                "bids"
            ][0][0]
            liquidity_risk = min(spread * 100, 1.0)  # 1%で1.0
        except Exception:
            liquidity_risk = 0.5  # デフォルト

        # 5. 統合リスクスコア
        risk_score = (
            price_risk * 0.3 + time_risk * 0.2 + vol_risk * 0.3 + liquidity_risk * 0.2
        )

        return max(0.0, min(1.0, risk_score))

    def _calculate_profit_potential(
        self, position: Position, current_price: float
    ) -> float:
        """利益ポテンシャル計算"""
        # 1. 現在の未実現損益
        current_pnl = position.calculate_unrealized_pnl(current_price)
        current_pnl_ratio = current_pnl / (position.amount * position.entry_price)

        # 2. 価格モメンタム
        volatility = self._get_volatility(position.symbol)
        momentum_potential = volatility * 0.5  # ボラティリティの50%を潜在利益とする

        # 3. 時間価値
        holding_time = position.get_holding_time()
        time_decay = max(0, 1 - holding_time.total_seconds() / (12 * 3600))  # 12時間で0

        # 4. 統合利益ポテンシャル
        profit_potential = current_pnl_ratio + momentum_potential * time_decay

        return max(-1.0, min(1.0, profit_potential))

    def _calculate_interest_cost(self, position_id: str, position: Position) -> float:
        """金利コスト計算"""
        if position_id not in self.interest_schedules:
            return 0.0

        schedule = self.interest_schedules[position_id]

        # 1. 現在までの累積金利
        accumulated = schedule.accumulated_interest

        # 2. 今後の予想金利
        now = datetime.now(self.timezone)
        if schedule.next_accrual > now:
            time_until_accrual = (schedule.next_accrual - now).total_seconds()
            hours_until_accrual = time_until_accrual / 3600

            if hours_until_accrual < 24:
                # 24時間以内なら金利発生
                notional = position.amount * position.entry_price
                projected_interest = notional * schedule.interest_rate
                return accumulated + projected_interest

        return accumulated

    def _calculate_optimization_score(
        self, risk_score: float, profit_potential: float, interest_cost: float
    ) -> float:
        """最適化スコア計算"""
        # 1. 最適化目標別重み
        if self.optimization_config.target == OptimizationTarget.PROFIT_MAXIMIZATION:
            profit_weight, risk_weight, interest_weight = 0.6, 0.2, 0.2
        elif self.optimization_config.target == OptimizationTarget.RISK_MINIMIZATION:
            profit_weight, risk_weight, interest_weight = 0.2, 0.6, 0.2
        elif self.optimization_config.target == OptimizationTarget.INTEREST_AVOIDANCE:
            profit_weight, risk_weight, interest_weight = 0.2, 0.2, 0.6
        else:  # BALANCED
            profit_weight, risk_weight, interest_weight = 0.4, 0.3, 0.3

        # 2. スコア計算
        profit_score = max(0, profit_potential)
        risk_penalty = risk_score
        interest_penalty = min(interest_cost * 100, 1.0)  # 正規化

        optimization_score = (
            profit_score * profit_weight
            - risk_penalty * risk_weight
            - interest_penalty * interest_weight
        )

        return max(-1.0, min(1.0, optimization_score))

    def _determine_optimized_priority(
        self,
        position: Position,
        risk_score: float,
        profit_potential: float,
        interest_cost: float,
    ) -> PositionPriority:
        """最適化済み優先度決定"""
        # 1. 緊急条件チェック
        if risk_score > 0.8:
            return PositionPriority.CRITICAL

        # 2. 金利回避期限チェック
        position_id = None
        for pid, pos in self.active_positions.items():
            if pos == position:
                position_id = pid
                break

        if position_id and position_id in self.interest_schedules:
            schedule = self.interest_schedules[position_id]
            if schedule.avoidance_deadline:
                time_until_deadline = (
                    schedule.avoidance_deadline - datetime.now(self.timezone)
                ).total_seconds()
                if time_until_deadline < 7200:  # 2時間以内
                    return PositionPriority.HIGH

        # 3. 利益・リスクバランス
        if profit_potential > 0.05 and risk_score < 0.3:
            return PositionPriority.LOW  # 利益期待でホールド
        elif profit_potential < -0.02 or risk_score > 0.6:
            return PositionPriority.HIGH  # 損切りまたはリスク回避
        else:
            return PositionPriority.MEDIUM

    def _determine_recommended_action(
        self,
        position: Position,
        priority: PositionPriority,
        risk_score: float,
        profit_potential: float,
    ) -> str:
        """推奨アクション決定"""
        if priority == PositionPriority.CRITICAL:
            return "CLOSE_IMMEDIATELY"
        elif priority == PositionPriority.HIGH:
            if profit_potential < -0.01:
                return "CLOSE_STOP_LOSS"
            else:
                return "CLOSE_SCHEDULED"
        elif priority == PositionPriority.MEDIUM:
            if profit_potential > 0.02:
                return "HOLD_PROFIT_TARGET"
            else:
                return "MONITOR_CLOSELY"
        else:  # LOW or MONITORING
            return "HOLD_NORMAL"

    def _calculate_target_close_time(
        self, position: Position, priority: PositionPriority, interest_cost: float
    ) -> Optional[datetime]:
        """目標決済時間計算"""
        now = datetime.now(self.timezone)

        if priority == PositionPriority.CRITICAL:
            return now + timedelta(minutes=5)
        elif priority == PositionPriority.HIGH:
            return now + timedelta(hours=1)
        elif priority == PositionPriority.MEDIUM:
            return now + timedelta(hours=4)
        else:
            # 金利回避期限または強制決済時間
            force_close_time = datetime.combine(
                now.date(), self.day_config.force_close_time
            )
            force_close_time = self.timezone.localize(force_close_time)

            return force_close_time - timedelta(minutes=30)

    def _generate_optimization_reasoning(
        self,
        position: Position,
        risk_score: float,
        profit_potential: float,
        interest_cost: float,
        recommended_action: str,
    ) -> str:
        """最適化理由生成"""
        reasons = []

        if risk_score > 0.7:
            reasons.append(f"高リスク ({risk_score:.2f})")

        if profit_potential > 0.03:
            reasons.append(f"利益期待 ({profit_potential:.2%})")
        elif profit_potential < -0.02:
            reasons.append(f"損失リスク ({profit_potential:.2%})")

        if interest_cost > 0.001:
            reasons.append(f"金利コスト ({interest_cost:.6f})")

        holding_time = position.get_holding_time()
        if holding_time.total_seconds() > 18 * 3600:  # 18時間以上
            reasons.append(f"長期保有 ({holding_time})")

        if not reasons:
            reasons.append("通常監視")

        return f"{recommended_action}: {', '.join(reasons)}"

    def _execute_optimization_action(self, result: PositionOptimizationResult) -> None:
        """最適化アクション実行"""
        # 優先度更新
        self.position_priorities[result.position_id] = result.optimized_priority

        # アクション実行
        if result.recommended_action == "CLOSE_IMMEDIATELY":
            self.close_position(result.position_id, "optimization_critical", force=True)
        elif result.recommended_action == "CLOSE_STOP_LOSS":
            self.close_position(
                result.position_id, "optimization_stop_loss", force=True
            )
        elif result.recommended_action == "CLOSE_SCHEDULED":
            # スケジュールされた決済（後で実行）
            pass

        # メトリクス更新
        self.enhanced_metrics["positions_optimized"] += 1

        if result.optimization_score > 0:
            self.enhanced_metrics["profit_improvements"] += result.optimization_score

        if result.risk_score > result.original_priority.name.count("HIGH"):
            self.enhanced_metrics["risk_reductions"] += 1

    def start_optimization(self) -> None:
        """最適化スレッド開始"""
        if self.optimization_active:
            return

        self.optimization_active = True
        self.optimization_thread = threading.Thread(target=self._optimization_loop)
        self.optimization_thread.daemon = True
        self.optimization_thread.start()

        logger.info("Enhanced position optimization started")

    def stop_optimization(self) -> None:
        """最適化スレッド停止"""
        self.optimization_active = False

        if self.optimization_thread is not None:
            self.optimization_thread.join(timeout=5)

        logger.info("Enhanced position optimization stopped")

    def _optimization_loop(self) -> None:
        """最適化メインループ"""
        while self.optimization_active:
            try:
                # 1. ポジション最適化実行
                # optimization_results = self.optimize_positions()
                self.optimize_positions()

                # 2. 金利スケジュール更新
                self._update_interest_schedules()

                # 3. 市場データ更新
                self._update_market_data()

                # 4. パフォーマンス分析
                self._analyze_performance()

                # 5. リバランス間隔で待機
                time_module.sleep(self.optimization_config.rebalance_interval)

            except Exception as e:
                logger.error(f"Error in optimization loop: {e}")
                time_module.sleep(60)

    def _update_interest_schedules(self) -> None:
        """金利スケジュール更新"""
        now = datetime.now(self.timezone)

        for position_id, schedule in self.interest_schedules.items():
            if position_id in self.active_positions:
                # 金利発生チェック
                if now >= schedule.next_accrual:
                    position = self.active_positions[position_id]
                    notional = position.amount * position.entry_price
                    daily_interest = notional * schedule.interest_rate

                    schedule.accumulated_interest += daily_interest
                    schedule.next_accrual += timedelta(days=1)

                    # 回避期限更新
                    schedule.avoidance_deadline = schedule.next_accrual - timedelta(
                        hours=2
                    )

                    # メトリクス更新
                    self.enhanced_metrics["interest_avoided_total"] += daily_interest

                    logger.info(
                        f"Interest accrued for {position_id}: {daily_interest:.6f}"
                    )

    def _update_market_data(self) -> None:
        """市場データ更新"""
        for symbol in set(pos.symbol for pos in self.active_positions.values()):
            try:
                ticker = self.bitbank_client.fetch_ticker(symbol)
                self.market_data_cache[symbol] = {
                    "last_price": ticker["last"],
                    "bid": ticker["bid"],
                    "ask": ticker["ask"],
                    "volume": ticker["quoteVolume"],
                    "timestamp": datetime.now(),
                }

                # ボラティリティキャッシュ更新
                if symbol not in self.volatility_cache:
                    self.volatility_cache[symbol] = deque(maxlen=24)

                self.volatility_cache[symbol].append(ticker["last"])

            except Exception as e:
                logger.error(f"Failed to update market data for {symbol}: {e}")

    def _analyze_performance(self) -> None:
        """パフォーマンス分析"""
        if not self.closed_positions:
            return

        # 1. 平均保有時間
        total_holding_time = sum(
            pos.get_holding_time().total_seconds() for pos in self.closed_positions
        )
        avg_holding_time = (
            total_holding_time / len(self.closed_positions) / 3600
        )  # 時間単位
        self.enhanced_metrics["average_holding_time"] = avg_holding_time

        # 2. ポジション成功率
        profitable_positions = sum(
            1 for pos in self.closed_positions if pos.profit_loss > 0
        )
        success_rate = profitable_positions / len(self.closed_positions)
        self.enhanced_metrics["position_success_rate"] = success_rate

        # 3. 最適化効果分析
        if len(self.optimization_history) >= 10:
            recent_optimizations = self.optimization_history[-10:]
            avg_optimization_score = sum(
                r.optimization_score for r in recent_optimizations
            ) / len(recent_optimizations)

            if avg_optimization_score > 0.1:
                logger.info(
                    f"Optimization performing well: {avg_optimization_score:.3f}"
                )
            elif avg_optimization_score < -0.1:
                logger.warning(
                    f"Optimization may need adjustment: {avg_optimization_score:.3f}"
                )

    def get_enhanced_position_status(self) -> Dict[str, Any]:
        """強化ポジション状況取得"""
        base_status = self.get_position_status()

        # 強化情報追加
        enhanced_positions = []
        for position_id, position in self.active_positions.items():
            current_price = self._get_current_price(position.symbol)

            # 優先度と金利情報
            priority = self.position_priorities.get(
                position_id, PositionPriority.MEDIUM
            )
            interest_schedule = self.interest_schedules.get(position_id)

            enhanced_info = {
                "position_id": position_id,
                "symbol": position.symbol,
                "side": position.side,
                "amount": position.amount,
                "entry_price": position.entry_price,
                "current_price": current_price,
                "unrealized_pnl": (
                    position.calculate_unrealized_pnl(current_price)
                    if current_price
                    else 0
                ),
                "priority": priority.value,
                "holding_time": str(position.get_holding_time()),
                "expected_exit": (
                    position.expected_exit_time.strftime("%H:%M:%S")
                    if position.expected_exit_time
                    else None
                ),
                "interest_info": {
                    "accumulated_interest": (
                        interest_schedule.accumulated_interest
                        if interest_schedule
                        else 0
                    ),
                    "projected_interest": (
                        interest_schedule.projected_interest if interest_schedule else 0
                    ),
                    "avoidance_deadline": (
                        interest_schedule.avoidance_deadline.strftime("%H:%M:%S")
                        if interest_schedule and interest_schedule.avoidance_deadline
                        else None
                    ),
                },
            }
            enhanced_positions.append(enhanced_info)

        # 強化メトリクス追加
        base_status["enhanced_metrics"] = self.enhanced_metrics.copy()
        base_status["optimization_config"] = {
            "target": self.optimization_config.target.value,
            "max_holding_hours": self.optimization_config.max_holding_hours,
            "interest_threshold": self.optimization_config.interest_threshold,
            "profit_target": self.optimization_config.profit_target,
            "stop_loss": self.optimization_config.stop_loss,
        }
        base_status["enhanced_positions"] = enhanced_positions
        base_status["optimization_active"] = self.optimization_active

        return base_status

    def get_optimization_report(self) -> Dict[str, Any]:
        """最適化レポート取得"""
        if not self.optimization_history:
            return {"status": "no_data", "message": "No optimization history available"}

        recent_optimizations = self.optimization_history[-50:]  # 直近50件

        # 統計計算
        avg_optimization_score = sum(
            r.optimization_score for r in recent_optimizations
        ) / len(recent_optimizations)
        avg_risk_score = sum(r.risk_score for r in recent_optimizations) / len(
            recent_optimizations
        )
        avg_profit_potential = sum(
            r.profit_potential for r in recent_optimizations
        ) / len(recent_optimizations)
        avg_interest_cost = sum(r.interest_cost for r in recent_optimizations) / len(
            recent_optimizations
        )

        # アクション別統計
        action_stats = {}
        for result in recent_optimizations:
            action = result.recommended_action
            if action not in action_stats:
                action_stats[action] = 0
            action_stats[action] += 1

        # 優先度変更統計
        priority_changes = sum(
            1
            for r in recent_optimizations
            if r.original_priority != r.optimized_priority
        )

        return {
            "optimization_summary": {
                "total_optimizations": len(recent_optimizations),
                "avg_optimization_score": avg_optimization_score,
                "avg_risk_score": avg_risk_score,
                "avg_profit_potential": avg_profit_potential,
                "avg_interest_cost": avg_interest_cost,
                "priority_changes": priority_changes,
                "priority_change_rate": priority_changes / len(recent_optimizations),
            },
            "action_distribution": action_stats,
            "enhanced_metrics": self.enhanced_metrics.copy(),
            "optimization_target": self.optimization_config.target.value,
            "recommendations": self._generate_optimization_recommendations(),
        }

    def _generate_optimization_recommendations(self) -> List[str]:
        """最適化推奨事項生成"""
        recommendations = []

        if self.enhanced_metrics["position_success_rate"] < 0.6:
            recommendations.append(
                "ポジション成功率が低いです。リスク管理設定の見直しを検討してください。"
            )

        if self.enhanced_metrics["average_holding_time"] > 12:
            recommendations.append(
                "平均保有時間が長すぎます。決済タイミングの最適化が必要です。"
            )

        if self.enhanced_metrics["interest_avoided_total"] > 0.01:
            recommendations.append(
                "金利回避効果が高いです。現在の戦略を維持してください。"
            )

        if len(recommendations) == 0:
            recommendations.append(
                "最適化システムは良好に動作しています。現在の設定を維持してください。"
            )

        return recommendations

    def __del__(self):
        """デストラクタ"""
        self.stop_optimization()
        super().__del__()
