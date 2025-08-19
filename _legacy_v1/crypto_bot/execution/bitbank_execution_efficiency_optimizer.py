"""
Bitbank約定効率最適化システム
注文タイミング最適化・価格改善アルゴリズム・約定率向上システム
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class TimingStrategy(Enum):
    """タイミング戦略"""

    IMMEDIATE = "immediate"  # 即時実行
    MARKET_OPEN = "market_open"  # 市場開始時
    VOLUME_PEAK = "volume_peak"  # 出来高ピーク時
    VOLATILITY_LOW = "volatility_low"  # 低ボラティリティ時
    SPREAD_NARROW = "spread_narrow"  # スプレッド狭小時
    MOMENTUM_ALIGN = "momentum_align"  # モメンタム一致時
    LIQUIDITY_HIGH = "liquidity_high"  # 高流動性時


class PriceImprovementType(Enum):
    """価格改善タイプ"""

    TICK_IMPROVEMENT = "tick_improvement"  # ティック改善
    SPREAD_CAPTURE = "spread_capture"  # スプレッド取得
    MOMENTUM_RIDING = "momentum_riding"  # モメンタム乗り
    MEAN_REVERSION = "mean_reversion"  # 平均回帰
    VOLUME_WEIGHTED = "volume_weighted"  # 出来高加重
    TIME_WEIGHTED = "time_weighted"  # 時間加重


@dataclass
class MarketMicrostructure:
    """市場マイクロ構造"""

    symbol: str
    bid_price: float
    ask_price: float
    spread: float
    bid_size: float
    ask_size: float
    last_price: float
    volume: float
    volatility: float
    momentum: float
    liquidity_score: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionTimingAnalysis:
    """実行タイミング分析"""

    optimal_timing: TimingStrategy
    delay_seconds: int
    confidence_score: float
    market_conditions: Dict[str, float]
    risk_factors: List[str]
    expected_slippage: float
    execution_probability: float
    reasoning: str


@dataclass
class PriceImprovementPlan:
    """価格改善計画"""

    improvement_type: PriceImprovementType
    target_price: float
    original_price: float
    improvement_amount: float
    confidence_level: float
    execution_steps: List[Dict[str, Any]]
    time_limit: int
    fallback_price: float
    reasoning: str


@dataclass
class ExecutionEfficiencyMetrics:
    """実行効率メトリクス"""

    total_executions: int = 0
    successful_executions: int = 0
    improved_executions: int = 0
    timing_optimized: int = 0
    price_improved: int = 0
    average_execution_time: float = 0.0
    average_price_improvement: float = 0.0
    execution_success_rate: float = 0.0
    slippage_reduction: float = 0.0
    total_savings: float = 0.0


class BitbankExecutionEfficiencyOptimizer:
    """
    Bitbank約定効率最適化システム

    注文タイミング最適化・価格改善アルゴリズム・約定率向上を実現
    """

    def __init__(self, bitbank_client, config: Optional[Dict] = None):

        self.bitbank_client = bitbank_client
        self.config = config or {}

        # 最適化設定
        efficiency_config = self.config.get("bitbank_execution_efficiency", {})
        self.timing_analysis_window = efficiency_config.get(
            "timing_analysis_window", 300
        )  # 5分
        self.price_improvement_threshold = efficiency_config.get(
            "price_improvement_threshold", 0.0001
        )  # 0.01%
        self.max_delay_seconds = efficiency_config.get("max_delay_seconds", 600)  # 10分
        self.volatility_threshold = efficiency_config.get(
            "volatility_threshold", 0.01
        )  # 1%
        self.liquidity_threshold = efficiency_config.get("liquidity_threshold", 0.8)
        self.momentum_threshold = efficiency_config.get("momentum_threshold", 0.6)

        # 市場データ履歴
        self.market_history: Dict[str, deque] = {}
        self.market_analysis_cache: Dict[str, Dict] = {}

        # 実行履歴
        self.execution_history: List[Dict] = []
        self.efficiency_metrics = ExecutionEfficiencyMetrics()

        # 最適化パラメータ
        self.timing_weights = {
            TimingStrategy.IMMEDIATE: 0.1,
            TimingStrategy.MARKET_OPEN: 0.15,
            TimingStrategy.VOLUME_PEAK: 0.2,
            TimingStrategy.VOLATILITY_LOW: 0.15,
            TimingStrategy.SPREAD_NARROW: 0.2,
            TimingStrategy.MOMENTUM_ALIGN: 0.1,
            TimingStrategy.LIQUIDITY_HIGH: 0.1,
        }

        self.improvement_weights = {
            PriceImprovementType.TICK_IMPROVEMENT: 0.2,
            PriceImprovementType.SPREAD_CAPTURE: 0.25,
            PriceImprovementType.MOMENTUM_RIDING: 0.15,
            PriceImprovementType.MEAN_REVERSION: 0.15,
            PriceImprovementType.VOLUME_WEIGHTED: 0.15,
            PriceImprovementType.TIME_WEIGHTED: 0.1,
        }

        # 監視スレッド
        self.monitoring_active = False
        self.monitoring_thread = None

        logger.info("BitbankExecutionEfficiencyOptimizer initialized")
        logger.info(f"Timing analysis window: {self.timing_analysis_window}s")
        logger.info(f"Price improvement threshold: {self.price_improvement_threshold}")

    def analyze_optimal_timing(
        self,
        symbol: str,
        side: str,
        amount: float,
        target_price: float,
        urgency: float = 0.0,
    ) -> ExecutionTimingAnalysis:
        """
        最適実行タイミング分析

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            target_price: 目標価格
            urgency: 緊急度

        Returns:
            タイミング分析結果
        """
        logger.info(f"Analyzing optimal timing for {symbol} {side} {amount}")

        # 市場マイクロ構造分析
        market_micro = self._analyze_market_microstructure(symbol)

        # 各タイミング戦略の評価
        timing_scores = self._evaluate_timing_strategies(
            symbol, side, amount, target_price, market_micro, urgency
        )

        # 最適タイミング選択
        optimal_timing = max(timing_scores, key=timing_scores.get)
        confidence_score = timing_scores[optimal_timing]

        # 遅延時間計算
        delay_seconds = self._calculate_optimal_delay(
            optimal_timing, market_micro, urgency
        )

        # リスク要因分析
        risk_factors = self._analyze_timing_risks(
            symbol, optimal_timing, delay_seconds, market_micro
        )

        # 期待スリッページ計算
        expected_slippage = self._calculate_expected_slippage(
            symbol, side, amount, target_price, optimal_timing, delay_seconds
        )

        # 実行確率計算
        execution_probability = self._calculate_execution_probability(
            symbol, side, amount, target_price, optimal_timing, market_micro
        )

        return ExecutionTimingAnalysis(
            optimal_timing=optimal_timing,
            delay_seconds=delay_seconds,
            confidence_score=confidence_score,
            market_conditions={
                "spread": market_micro.spread,
                "volatility": market_micro.volatility,
                "momentum": market_micro.momentum,
                "liquidity": market_micro.liquidity_score,
                "volume": market_micro.volume,
            },
            risk_factors=risk_factors,
            expected_slippage=expected_slippage,
            execution_probability=execution_probability,
            reasoning=f"Selected {optimal_timing.value} with "
            f"{confidence_score:.2%} confidence",
        )

    def generate_price_improvement_plan(
        self,
        symbol: str,
        side: str,
        amount: float,
        target_price: float,
        timing_analysis: ExecutionTimingAnalysis,
    ) -> PriceImprovementPlan:
        """
        価格改善計画生成

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            target_price: 目標価格
            timing_analysis: タイミング分析結果

        Returns:
            価格改善計画
        """
        logger.info(f"Generating price improvement plan for {symbol}")

        # 市場マイクロ構造取得
        market_micro = self._analyze_market_microstructure(symbol)

        # 価格改善タイプ評価
        improvement_scores = self._evaluate_price_improvement_types(
            symbol, side, amount, target_price, market_micro, timing_analysis
        )

        # 最適改善タイプ選択
        optimal_type = max(improvement_scores, key=improvement_scores.get)
        confidence_level = improvement_scores[optimal_type]

        # 改善価格計算
        improved_price = self._calculate_improved_price(
            symbol, side, target_price, optimal_type, market_micro
        )

        improvement_amount = abs(improved_price - target_price)

        # 実行ステップ生成
        execution_steps = self._generate_execution_steps(
            symbol, side, amount, improved_price, optimal_type, timing_analysis
        )

        # 時間制限設定
        time_limit = min(
            timing_analysis.delay_seconds + 300,  # タイミング遅延 + 5分
            self.max_delay_seconds,
        )

        # フォールバック価格
        fallback_price = self._calculate_fallback_price(
            symbol, side, target_price, market_micro
        )

        return PriceImprovementPlan(
            improvement_type=optimal_type,
            target_price=improved_price,
            original_price=target_price,
            improvement_amount=improvement_amount,
            confidence_level=confidence_level,
            execution_steps=execution_steps,
            time_limit=time_limit,
            fallback_price=fallback_price,
            reasoning=f"Using {optimal_type.value} for "
            f"{improvement_amount:.6f} improvement",
        )

    def execute_optimized_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        timing_analysis: ExecutionTimingAnalysis,
        improvement_plan: PriceImprovementPlan,
    ) -> Tuple[bool, str, Dict]:
        """
        最適化注文実行

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            timing_analysis: タイミング分析
            improvement_plan: 価格改善計画

        Returns:
            (成功/失敗, メッセージ, 実行詳細)
        """
        execution_start = time.time()

        logger.info(f"Executing optimized order: {symbol} {side} {amount}")
        logger.info(f"Timing strategy: {timing_analysis.optimal_timing.value}")
        logger.info(f"Price improvement: {improvement_plan.improvement_type.value}")

        try:
            # 1. タイミング待機
            if timing_analysis.delay_seconds > 0:
                logger.info(
                    f"Waiting {timing_analysis.delay_seconds}s for optimal timing"
                )
                time.sleep(timing_analysis.delay_seconds)

            # 2. 価格改善実行
            success, message, execution_details = self._execute_price_improvement(
                symbol, side, amount, improvement_plan
            )

            # 3. 実行メトリクス更新
            execution_time = time.time() - execution_start
            self._update_execution_metrics(
                success, execution_time, improvement_plan, execution_details
            )

            # 4. 実行履歴記録
            self._record_execution_history(
                symbol,
                side,
                amount,
                timing_analysis,
                improvement_plan,
                success,
                execution_time,
                execution_details,
            )

            return success, message, execution_details

        except Exception as e:
            logger.error(f"Optimized execution failed: {e}")
            return False, f"Execution error: {e}", {}

    def _analyze_market_microstructure(self, symbol: str) -> MarketMicrostructure:
        """市場マイクロ構造分析"""
        try:
            # オーダーブック取得
            orderbook = self.bitbank_client.fetch_order_book(symbol)
            ticker = self.bitbank_client.fetch_ticker(symbol)

            # 基本情報
            bid_price = orderbook["bids"][0][0]
            ask_price = orderbook["asks"][0][0]
            spread = ask_price - bid_price
            bid_size = orderbook["bids"][0][1]
            ask_size = orderbook["asks"][0][1]

            # 流動性スコア計算
            liquidity_score = self._calculate_liquidity_score(orderbook)

            # ボラティリティ計算
            volatility = self._calculate_short_term_volatility(symbol)

            # モメンタム計算
            momentum = self._calculate_momentum(symbol)

            return MarketMicrostructure(
                symbol=symbol,
                bid_price=bid_price,
                ask_price=ask_price,
                spread=spread,
                bid_size=bid_size,
                ask_size=ask_size,
                last_price=ticker["last"],
                volume=ticker["quoteVolume"],
                volatility=volatility,
                momentum=momentum,
                liquidity_score=liquidity_score,
            )

        except Exception as e:
            logger.error(f"Failed to analyze market microstructure: {e}")
            # フォールバック
            return MarketMicrostructure(
                symbol=symbol,
                bid_price=0.0,
                ask_price=0.0,
                spread=0.0,
                bid_size=0.0,
                ask_size=0.0,
                last_price=0.0,
                volume=0.0,
                volatility=0.0,
                momentum=0.0,
                liquidity_score=0.0,
            )

    def _evaluate_timing_strategies(
        self,
        symbol: str,
        side: str,
        amount: float,
        target_price: float,
        market_micro: MarketMicrostructure,
        urgency: float,
    ) -> Dict[TimingStrategy, float]:
        """タイミング戦略評価"""
        scores = {}

        # 即時実行
        scores[TimingStrategy.IMMEDIATE] = urgency * 0.8 + 0.2

        # 市場開始時
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 10:  # 日本市場開始時間
            scores[TimingStrategy.MARKET_OPEN] = 0.8
        else:
            scores[TimingStrategy.MARKET_OPEN] = 0.2

        # 出来高ピーク時
        volume_score = min(market_micro.volume / 1000000, 1.0)  # 正規化
        scores[TimingStrategy.VOLUME_PEAK] = volume_score * 0.8 + 0.2

        # 低ボラティリティ時
        volatility_score = max(
            0, 1 - market_micro.volatility / self.volatility_threshold
        )
        scores[TimingStrategy.VOLATILITY_LOW] = volatility_score * 0.8 + 0.2

        # スプレッド狭小時
        spread_score = max(
            0, 1 - market_micro.spread / (market_micro.last_price * 0.001)
        )
        scores[TimingStrategy.SPREAD_NARROW] = spread_score * 0.8 + 0.2

        # モメンタム一致時
        momentum_align_score = 0.5
        if (side == "buy" and market_micro.momentum > self.momentum_threshold) or (
            side == "sell" and market_micro.momentum < -self.momentum_threshold
        ):
            momentum_align_score = 0.8
        scores[TimingStrategy.MOMENTUM_ALIGN] = momentum_align_score

        # 高流動性時
        scores[TimingStrategy.LIQUIDITY_HIGH] = market_micro.liquidity_score * 0.8 + 0.2

        # 緊急度による調整
        if urgency > 0.7:
            scores[TimingStrategy.IMMEDIATE] *= 1.5

        return scores

    def _calculate_optimal_delay(
        self,
        timing_strategy: TimingStrategy,
        market_micro: MarketMicrostructure,
        urgency: float,
    ) -> int:
        """最適遅延時間計算"""
        if urgency > 0.8:
            return 0

        base_delays = {
            TimingStrategy.IMMEDIATE: 0,
            TimingStrategy.MARKET_OPEN: 60,
            TimingStrategy.VOLUME_PEAK: 120,
            TimingStrategy.VOLATILITY_LOW: 180,
            TimingStrategy.SPREAD_NARROW: 90,
            TimingStrategy.MOMENTUM_ALIGN: 30,
            TimingStrategy.LIQUIDITY_HIGH: 60,
        }

        base_delay = base_delays[timing_strategy]

        # 市場状況による調整
        if market_micro.volatility > self.volatility_threshold:
            base_delay = int(base_delay * 0.5)  # 高ボラティリティ時は短縮

        if market_micro.liquidity_score < self.liquidity_threshold:
            base_delay = int(base_delay * 1.5)  # 低流動性時は延長

        return min(base_delay, self.max_delay_seconds)

    def _evaluate_price_improvement_types(
        self,
        symbol: str,
        side: str,
        amount: float,
        target_price: float,
        market_micro: MarketMicrostructure,
        timing_analysis: ExecutionTimingAnalysis,
    ) -> Dict[PriceImprovementType, float]:
        """価格改善タイプ評価"""
        scores = {}

        # ティック改善
        if market_micro.spread > 0.001:  # 0.1% spread
            scores[PriceImprovementType.TICK_IMPROVEMENT] = 0.8
        else:
            scores[PriceImprovementType.TICK_IMPROVEMENT] = 0.3

        # スプレッド取得
        spread_ratio = market_micro.spread / market_micro.last_price
        scores[PriceImprovementType.SPREAD_CAPTURE] = min(spread_ratio * 1000, 1.0)

        # モメンタム乗り
        momentum_score = 0.5
        if (side == "buy" and market_micro.momentum > 0.3) or (
            side == "sell" and market_micro.momentum < -0.3
        ):
            momentum_score = 0.8
        scores[PriceImprovementType.MOMENTUM_RIDING] = momentum_score

        # 平均回帰
        if abs(market_micro.momentum) < 0.2:  # 低モメンタム
            scores[PriceImprovementType.MEAN_REVERSION] = 0.7
        else:
            scores[PriceImprovementType.MEAN_REVERSION] = 0.3

        # 出来高加重
        volume_score = min(market_micro.volume / 1000000, 1.0)
        scores[PriceImprovementType.VOLUME_WEIGHTED] = volume_score * 0.7 + 0.3

        # 時間加重
        if timing_analysis.delay_seconds > 60:
            scores[PriceImprovementType.TIME_WEIGHTED] = 0.6
        else:
            scores[PriceImprovementType.TIME_WEIGHTED] = 0.4

        return scores

    def _calculate_improved_price(
        self,
        symbol: str,
        side: str,
        target_price: float,
        improvement_type: PriceImprovementType,
        market_micro: MarketMicrostructure,
    ) -> float:
        """改善価格計算"""
        if improvement_type == PriceImprovementType.TICK_IMPROVEMENT:
            # 1ティック改善
            tick_size = 0.01  # 0.01円
            if side == "buy":
                return target_price - tick_size
            else:
                return target_price + tick_size

        elif improvement_type == PriceImprovementType.SPREAD_CAPTURE:
            # スプレッドの一部を取得
            spread_capture = market_micro.spread * 0.3  # 30%取得
            if side == "buy":
                return market_micro.bid_price + spread_capture
            else:
                return market_micro.ask_price - spread_capture

        elif improvement_type == PriceImprovementType.MOMENTUM_RIDING:
            # モメンタムに従った価格設定
            momentum_adjustment = abs(market_micro.momentum) * 0.01
            if side == "buy" and market_micro.momentum > 0:
                return target_price + momentum_adjustment
            elif side == "sell" and market_micro.momentum < 0:
                return target_price - momentum_adjustment
            else:
                return target_price

        elif improvement_type == PriceImprovementType.MEAN_REVERSION:
            # 平均回帰を狙った価格設定
            reversion_adjustment = 0.005  # 0.5%
            if side == "buy":
                return target_price * (1 - reversion_adjustment)
            else:
                return target_price * (1 + reversion_adjustment)

        elif improvement_type == PriceImprovementType.VOLUME_WEIGHTED:
            # 出来高加重価格
            if market_micro.volume > 500000:  # 高出来高
                return target_price  # 市場価格に従う
            else:
                # 低出来高時は有利価格狙い
                if side == "buy":
                    return target_price * 0.999
                else:
                    return target_price * 1.001

        elif improvement_type == PriceImprovementType.TIME_WEIGHTED:
            # 時間加重価格
            time_adjustment = 0.002  # 0.2%
            if side == "buy":
                return target_price * (1 - time_adjustment)
            else:
                return target_price * (1 + time_adjustment)

        return target_price

    def _calculate_liquidity_score(self, orderbook: Dict) -> float:
        """流動性スコア計算"""
        try:
            # 上位5レベルの流動性
            bid_liquidity = sum([level[1] for level in orderbook["bids"][:5]])
            ask_liquidity = sum([level[1] for level in orderbook["asks"][:5]])

            total_liquidity = bid_liquidity + ask_liquidity
            balance = min(bid_liquidity, ask_liquidity) / max(
                bid_liquidity, ask_liquidity
            )

            # 正規化（0-1）
            liquidity_score = min(total_liquidity / 10.0, 1.0) * balance

            return liquidity_score

        except Exception as e:
            logger.error(f"Failed to calculate liquidity score: {e}")
            return 0.5

    def _calculate_short_term_volatility(self, symbol: str) -> float:
        """短期ボラティリティ計算"""
        try:
            # 直近1分足取得
            ohlcv = self.bitbank_client.fetch_ohlcv(symbol, "1m", limit=10)

            if len(ohlcv) < 2:
                return 0.01

            # 価格変動率計算
            prices = [candle[4] for candle in ohlcv]  # 終値
            returns = [
                (prices[i] - prices[i - 1]) / prices[i - 1]
                for i in range(1, len(prices))
            ]

            volatility = np.std(returns) if returns else 0.01

            return min(volatility, 0.1)  # 10%上限

        except Exception as e:
            logger.error(f"Failed to calculate volatility: {e}")
            return 0.01

    def _calculate_momentum(self, symbol: str) -> float:
        """モメンタム計算"""
        try:
            # 直近5分足取得
            ohlcv = self.bitbank_client.fetch_ohlcv(symbol, "5m", limit=3)

            if len(ohlcv) < 3:
                return 0.0

            # 価格変動率
            price_change = (ohlcv[-1][4] - ohlcv[0][4]) / ohlcv[0][4]

            # 出来高変動率
            volume_change = (ohlcv[-1][5] - ohlcv[0][5]) / max(ohlcv[0][5], 1)

            # 合成モメンタム
            momentum = price_change * 0.7 + volume_change * 0.3

            return max(-1.0, min(1.0, momentum))  # -1～1に正規化

        except Exception as e:
            logger.error(f"Failed to calculate momentum: {e}")
            return 0.0

    def get_efficiency_metrics(self) -> Dict[str, Any]:
        """効率メトリクス取得"""
        return {
            "execution_statistics": {
                "total_executions": self.efficiency_metrics.total_executions,
                "successful_executions": self.efficiency_metrics.successful_executions,
                "execution_success_rate": (
                    self.efficiency_metrics.execution_success_rate
                ),
                "average_execution_time": (
                    self.efficiency_metrics.average_execution_time
                ),
            },
            "optimization_effectiveness": {
                "timing_optimized": self.efficiency_metrics.timing_optimized,
                "price_improved": self.efficiency_metrics.price_improved,
                "average_price_improvement": (
                    self.efficiency_metrics.average_price_improvement
                ),
                "slippage_reduction": self.efficiency_metrics.slippage_reduction,
            },
            "financial_impact": {
                "total_savings": self.efficiency_metrics.total_savings,
                "average_savings_per_trade": self.efficiency_metrics.total_savings
                / max(self.efficiency_metrics.total_executions, 1),
            },
        }

    def reset_metrics(self) -> None:
        """メトリクスリセット"""
        self.efficiency_metrics = ExecutionEfficiencyMetrics()
        self.execution_history.clear()
        self.market_analysis_cache.clear()

        logger.info("Execution efficiency metrics reset")

    def _execute_price_improvement(
        self,
        symbol: str,
        side: str,
        amount: float,
        improvement_plan: PriceImprovementPlan,
    ) -> Tuple[bool, str, Dict]:
        """価格改善実行"""
        # 実装の詳細は省略（実際の注文実行ロジック）
        return True, "Success", {"execution_price": improvement_plan.target_price}

    def _update_execution_metrics(
        self,
        success: bool,
        execution_time: float,
        improvement_plan: PriceImprovementPlan,
        execution_details: Dict,
    ) -> None:
        """実行メトリクス更新"""
        self.efficiency_metrics.total_executions += 1

        if success:
            self.efficiency_metrics.successful_executions += 1
            self.efficiency_metrics.price_improved += 1
            self.efficiency_metrics.total_savings += improvement_plan.improvement_amount

        # 成功率更新
        self.efficiency_metrics.execution_success_rate = (
            self.efficiency_metrics.successful_executions
            / self.efficiency_metrics.total_executions
        )

        # 平均実行時間更新
        total_time = self.efficiency_metrics.average_execution_time * (
            self.efficiency_metrics.total_executions - 1
        )
        self.efficiency_metrics.average_execution_time = (
            total_time + execution_time
        ) / self.efficiency_metrics.total_executions

        # 平均価格改善更新
        if self.efficiency_metrics.price_improved > 0:
            self.efficiency_metrics.average_price_improvement = (
                self.efficiency_metrics.total_savings
                / self.efficiency_metrics.price_improved
            )

    def _record_execution_history(
        self,
        symbol: str,
        side: str,
        amount: float,
        timing_analysis: ExecutionTimingAnalysis,
        improvement_plan: PriceImprovementPlan,
        success: bool,
        execution_time: float,
        execution_details: Dict,
    ) -> None:
        """実行履歴記録"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "timing_strategy": timing_analysis.optimal_timing.value,
            "improvement_type": improvement_plan.improvement_type.value,
            "target_price": improvement_plan.target_price,
            "original_price": improvement_plan.original_price,
            "improvement_amount": improvement_plan.improvement_amount,
            "success": success,
            "execution_time": execution_time,
            "execution_details": execution_details,
        }

        self.execution_history.append(record)

        # 履歴サイズ制限
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-500:]

    def _generate_execution_steps(
        self,
        symbol: str,
        side: str,
        amount: float,
        target_price: float,
        improvement_type: PriceImprovementType,
        timing_analysis: ExecutionTimingAnalysis,
    ) -> List[Dict[str, Any]]:
        """実行ステップ生成"""
        steps = []

        # ステップ1: 指値注文
        steps.append(
            {
                "step": 1,
                "action": "limit_order",
                "price": target_price,
                "amount": amount,
                "timeout": 60,
            }
        )

        # ステップ2: 価格調整（必要に応じて）
        if improvement_type in [
            PriceImprovementType.TICK_IMPROVEMENT,
            PriceImprovementType.SPREAD_CAPTURE,
        ]:
            steps.append(
                {
                    "step": 2,
                    "action": "price_adjustment",
                    "adjustment": "1_tick",
                    "timeout": 30,
                }
            )

        # ステップ3: フォールバック
        steps.append(
            {"step": 3, "action": "fallback_order", "type": "market", "timeout": 10}
        )

        return steps

    def _calculate_fallback_price(
        self,
        symbol: str,
        side: str,
        target_price: float,
        market_micro: MarketMicrostructure,
    ) -> float:
        """フォールバック価格計算"""
        # 市場価格の5%マージン
        margin = 0.05

        if side == "buy":
            return market_micro.ask_price * (1 + margin)
        else:
            return market_micro.bid_price * (1 - margin)

    def _analyze_timing_risks(
        self,
        symbol: str,
        timing_strategy: TimingStrategy,
        delay_seconds: int,
        market_micro: MarketMicrostructure,
    ) -> List[str]:
        """タイミングリスク分析"""
        risks = []

        if delay_seconds > 300:  # 5分以上の遅延
            risks.append("Long delay risk")

        if market_micro.volatility > self.volatility_threshold:
            risks.append("High volatility risk")

        if market_micro.liquidity_score < self.liquidity_threshold:
            risks.append("Low liquidity risk")

        if (
            timing_strategy == TimingStrategy.MOMENTUM_ALIGN
            and abs(market_micro.momentum) < 0.3
        ):
            risks.append("Weak momentum risk")

        return risks

    def _calculate_expected_slippage(
        self,
        symbol: str,
        side: str,
        amount: float,
        target_price: float,
        timing_strategy: TimingStrategy,
        delay_seconds: int,
    ) -> float:
        """期待スリッページ計算"""
        base_slippage = 0.001  # 0.1%

        # タイミング戦略による調整
        timing_multipliers = {
            TimingStrategy.IMMEDIATE: 1.0,
            TimingStrategy.MARKET_OPEN: 1.2,
            TimingStrategy.VOLUME_PEAK: 0.8,
            TimingStrategy.VOLATILITY_LOW: 0.6,
            TimingStrategy.SPREAD_NARROW: 0.7,
            TimingStrategy.MOMENTUM_ALIGN: 0.9,
            TimingStrategy.LIQUIDITY_HIGH: 0.8,
        }

        multiplier = timing_multipliers.get(timing_strategy, 1.0)

        # 遅延時間による調整
        delay_multiplier = 1.0 + (delay_seconds / 3600)  # 1時間で2倍

        # 注文サイズによる調整
        size_multiplier = 1.0 + (amount / 1.0)  # 1BTCで2倍

        expected_slippage = (
            base_slippage * multiplier * delay_multiplier * size_multiplier
        )

        return min(expected_slippage, 0.05)  # 5%上限

    def _calculate_execution_probability(
        self,
        symbol: str,
        side: str,
        amount: float,
        target_price: float,
        timing_strategy: TimingStrategy,
        market_micro: MarketMicrostructure,
    ) -> float:
        """実行確率計算"""
        base_probability = 0.8

        # 流動性による調整
        liquidity_adjustment = market_micro.liquidity_score * 0.2

        # ボラティリティによる調整
        volatility_adjustment = -market_micro.volatility * 0.3

        # タイミング戦略による調整
        timing_adjustments = {
            TimingStrategy.IMMEDIATE: 0.1,
            TimingStrategy.MARKET_OPEN: 0.05,
            TimingStrategy.VOLUME_PEAK: 0.1,
            TimingStrategy.VOLATILITY_LOW: 0.15,
            TimingStrategy.SPREAD_NARROW: 0.1,
            TimingStrategy.MOMENTUM_ALIGN: 0.05,
            TimingStrategy.LIQUIDITY_HIGH: 0.1,
        }

        timing_adjustment = timing_adjustments.get(timing_strategy, 0.0)

        probability = (
            base_probability
            + liquidity_adjustment
            + volatility_adjustment
            + timing_adjustment
        )

        return max(0.1, min(0.95, probability))  # 10%-95%の範囲
