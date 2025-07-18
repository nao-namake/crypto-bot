"""
Bitbank手数料最適化システム
メイカー手数料-0.02%活用・テイカー手数料0.12%回避・動的注文タイプ選択
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """注文タイプ"""

    MAKER = "maker"
    TAKER = "taker"


class FeeOptimizationStrategy(Enum):
    """手数料最適化戦略"""

    MAKER_PRIORITY = "maker_priority"
    TAKER_AVOIDANCE = "taker_avoidance"
    BALANCED = "balanced"
    EMERGENCY = "emergency"


@dataclass
class FeeCalculation:
    """手数料計算結果"""

    maker_fee: float  # メイカー手数料（-0.02%）
    taker_fee: float  # テイカー手数料（0.12%）
    optimal_type: OrderType  # 最適な注文タイプ
    expected_fee: float  # 予想手数料
    fee_impact: float  # 手数料影響度
    break_even_threshold: float  # 手数料負け防止閾値


@dataclass
class FeePerformanceMetrics:
    """手数料パフォーマンス指標"""

    total_maker_rebates: float  # メイカーリベート総額
    total_taker_costs: float  # テイカーコスト総額
    net_fee_result: float  # 純手数料結果
    maker_ratio: float  # メイカー比率
    taker_ratio: float  # テイカー比率
    avg_fee_per_trade: float  # 平均手数料/取引
    fee_optimization_score: float  # 手数料最適化スコア


class BitbankFeeOptimizer:
    """
    Bitbank手数料最適化システム

    メイカー手数料-0.02%を最大限活用し、テイカー手数料0.12%を回避する
    動的注文タイプ選択システム
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Bitbank手数料設定
        self.MAKER_FEE_RATE = -0.0002  # -0.02% (リベート)
        self.TAKER_FEE_RATE = 0.0012  # 0.12% (コスト)

        # 最適化設定
        fee_config = self.config.get("bitbank_fee_optimization", {})
        self.maker_priority = fee_config.get("maker_priority", True)
        self.taker_avoidance = fee_config.get("taker_avoidance", True)
        self.emergency_threshold = fee_config.get("emergency_threshold", 0.005)  # 0.5%

        # 手数料負け防止設定
        self.min_profit_threshold = fee_config.get(
            "min_profit_threshold", 0.0015
        )  # 0.15%
        self.fee_accumulation_limit = fee_config.get(
            "fee_accumulation_limit", 0.01
        )  # 1.0%

        # パフォーマンス追跡
        self.fee_performance_history: List[FeePerformanceMetrics] = []
        self.current_session_fees: Dict[str, float] = {
            "maker_rebates": 0.0,
            "taker_costs": 0.0,
            "trade_count": 0,
        }

        logger.info("BitbankFeeOptimizer initialized")
        logger.info(
            "Maker fee rate: %.4f (%.2f%%)",
            self.MAKER_FEE_RATE,
            self.MAKER_FEE_RATE * 100,
        )
        logger.info(
            "Taker fee rate: %.4f (%.2f%%)",
            self.TAKER_FEE_RATE,
            self.TAKER_FEE_RATE * 100,
        )

    def calculate_optimal_order_type(
        self,
        symbol: str,
        side: str,
        amount: float,
        current_price: float,
        target_price: Optional[float] = None,
        urgency_level: float = 0.0,
        market_volatility: float = 0.0,
    ) -> Tuple[OrderType, FeeCalculation]:
        """
        最適な注文タイプを判定

        Args:
            symbol: 通貨ペア
            side: 売買方向 (buy/sell)
            amount: 注文量
            current_price: 現在価格
            target_price: 目標価格
            urgency_level: 緊急度 (0.0-1.0)
            market_volatility: 市場ボラティリティ

        Returns:
            最適な注文タイプと手数料計算結果
        """
        # 手数料計算
        notional_value = amount * current_price
        maker_fee = notional_value * self.MAKER_FEE_RATE
        taker_fee = notional_value * self.TAKER_FEE_RATE

        # 基本戦略：メイカー優先
        optimal_type = OrderType.MAKER
        expected_fee = maker_fee

        # 緊急度による調整
        if urgency_level > 0.8:
            logger.info(f"High urgency ({urgency_level:.2f}), considering taker order")
            optimal_type = OrderType.TAKER
            expected_fee = taker_fee

        # 市場ボラティリティによる調整
        if market_volatility > 0.02:  # 2%以上のボラティリティ
            logger.info(
                f"High volatility ({market_volatility:.2f}), prioritizing execution"
            )
            if urgency_level > 0.5:
                optimal_type = OrderType.TAKER
                expected_fee = taker_fee

        # 価格条件による調整
        if target_price is not None:
            price_diff = abs(target_price - current_price) / current_price
            if price_diff > 0.001:  # 0.1%以上の価格差
                logger.debug(f"Price difference {price_diff:.4f} allows maker order")
                optimal_type = OrderType.MAKER
                expected_fee = maker_fee

        # 手数料負け防止チェック
        break_even_threshold = self._calculate_break_even_threshold(
            optimal_type, notional_value
        )

        # 手数料影響度計算
        fee_impact = abs(expected_fee) / notional_value

        fee_calculation = FeeCalculation(
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            optimal_type=optimal_type,
            expected_fee=expected_fee,
            fee_impact=fee_impact,
            break_even_threshold=break_even_threshold,
        )

        logger.debug(f"Optimal order type: {optimal_type.value}")
        logger.debug(f"Expected fee: {expected_fee:.6f} ({fee_impact*100:.4f}%)")

        return optimal_type, fee_calculation

    def estimate_fee_impact(
        self, symbol: str, amount: float, price: float, order_type: OrderType
    ) -> Dict[str, float]:
        """
        手数料影響度を詳細に計算

        Args:
            symbol: 通貨ペア
            amount: 注文量
            price: 価格
            order_type: 注文タイプ

        Returns:
            手数料影響度の詳細
        """
        notional_value = amount * price

        if order_type == OrderType.MAKER:
            fee_amount = notional_value * self.MAKER_FEE_RATE
            fee_rate = self.MAKER_FEE_RATE
        else:
            fee_amount = notional_value * self.TAKER_FEE_RATE
            fee_rate = self.TAKER_FEE_RATE

        # 手数料影響度計算
        fee_impact = abs(fee_amount) / notional_value

        # セッション累積影響度
        session_impact = self._calculate_session_fee_impact(fee_amount)

        return {
            "fee_amount": fee_amount,
            "fee_rate": fee_rate,
            "fee_impact": fee_impact,
            "notional_value": notional_value,
            "session_impact": session_impact,
            "is_profitable": fee_amount < 0,  # メイカーの場合はTrue
            "break_even_required": abs(fee_amount) / notional_value,
        }

    def optimize_order_execution(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        strategy: FeeOptimizationStrategy = FeeOptimizationStrategy.MAKER_PRIORITY,
    ) -> Dict[str, any]:
        """
        注文実行最適化

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 価格
            strategy: 最適化戦略

        Returns:
            最適化された注文パラメータ
        """
        # 戦略別最適化
        if strategy == FeeOptimizationStrategy.MAKER_PRIORITY:
            order_type = "limit"
            time_in_force = "GTC"
            post_only = True
        elif strategy == FeeOptimizationStrategy.TAKER_AVOIDANCE:
            order_type = "limit"
            time_in_force = "IOC"
            post_only = False
        elif strategy == FeeOptimizationStrategy.EMERGENCY:
            order_type = "market"
            time_in_force = "IOC"
            post_only = False
        else:  # BALANCED
            order_type = "limit"
            time_in_force = "GTC"
            post_only = False

        # 手数料計算
        optimal_type, fee_calc = self.calculate_optimal_order_type(
            symbol, side, amount, price
        )

        # 最適化されたパラメータ
        optimized_params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "amount": amount,
            "price": price,
            "time_in_force": time_in_force,
            "post_only": post_only,
            "expected_fee": fee_calc.expected_fee,
            "fee_optimization_strategy": strategy.value,
            "break_even_threshold": fee_calc.break_even_threshold,
        }

        logger.info(f"Optimized order: {strategy.value} - {order_type}")
        logger.info(f"Expected fee: {fee_calc.expected_fee:.6f}")

        return optimized_params

    def track_fee_performance(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        actual_fee: float,
        order_type: OrderType,
    ) -> None:
        """
        手数料パフォーマンスを追跡

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 価格
            actual_fee: 実際の手数料
            order_type: 注文タイプ
        """
        # セッション統計更新
        self.current_session_fees["trade_count"] += 1

        if order_type == OrderType.MAKER:
            self.current_session_fees["maker_rebates"] += abs(actual_fee)
        else:
            self.current_session_fees["taker_costs"] += actual_fee

        # パフォーマンス計算
        total_trades = self.current_session_fees["trade_count"]
        maker_rebates = self.current_session_fees["maker_rebates"]
        taker_costs = self.current_session_fees["taker_costs"]

        net_fee_result = maker_rebates - taker_costs

        # 比率計算
        maker_ratio = (
            maker_rebates / (maker_rebates + taker_costs)
            if (maker_rebates + taker_costs) > 0
            else 0
        )
        taker_ratio = 1 - maker_ratio

        # 平均手数料計算
        avg_fee_per_trade = net_fee_result / total_trades if total_trades > 0 else 0

        # 最適化スコア計算 (メイカー比率重視)
        fee_optimization_score = (maker_ratio * 0.7) + (net_fee_result / 1000 * 0.3)

        # パフォーマンス記録
        performance = FeePerformanceMetrics(
            total_maker_rebates=maker_rebates,
            total_taker_costs=taker_costs,
            net_fee_result=net_fee_result,
            maker_ratio=maker_ratio,
            taker_ratio=taker_ratio,
            avg_fee_per_trade=avg_fee_per_trade,
            fee_optimization_score=fee_optimization_score,
        )

        self.fee_performance_history.append(performance)

        logger.info(
            f"Fee performance updated: net={net_fee_result:.6f}, "
            f"maker_ratio={maker_ratio:.2f}"
        )

    def get_fee_performance_summary(self) -> Dict[str, any]:
        """
        手数料パフォーマンスサマリー取得

        Returns:
            パフォーマンスサマリー
        """
        if not self.fee_performance_history:
            return {
                "total_trades": 0,
                "net_fee_result": 0.0,
                "maker_ratio": 0.0,
                "optimization_score": 0.0,
            }

        latest = self.fee_performance_history[-1]

        # 日次/週次サマリー
        daily_summary = self._calculate_daily_summary()
        weekly_summary = self._calculate_weekly_summary()

        return {
            "session_summary": {
                "total_trades": self.current_session_fees["trade_count"],
                "maker_rebates": self.current_session_fees["maker_rebates"],
                "taker_costs": self.current_session_fees["taker_costs"],
                "net_fee_result": latest.net_fee_result,
                "maker_ratio": latest.maker_ratio,
                "taker_ratio": latest.taker_ratio,
                "avg_fee_per_trade": latest.avg_fee_per_trade,
                "optimization_score": latest.fee_optimization_score,
            },
            "daily_summary": daily_summary,
            "weekly_summary": weekly_summary,
            "recommendations": self._generate_recommendations(),
        }

    def should_avoid_taker_order(
        self, symbol: str, expected_profit: float, notional_value: float
    ) -> bool:
        """
        テイカー注文を避けるべきかを判定

        Args:
            symbol: 通貨ペア
            expected_profit: 予想利益
            notional_value: 想定元本

        Returns:
            テイカー注文を避けるべきか
        """
        taker_fee = notional_value * self.TAKER_FEE_RATE

        # 手数料負け確認
        if expected_profit < taker_fee * 1.5:  # 手数料の1.5倍以上の利益が必要
            logger.warning(
                f"Taker order avoided: expected_profit={expected_profit:.6f} < "
                f"taker_fee={taker_fee:.6f}"
            )
            return True

        # セッション累積手数料確認
        session_impact = self._calculate_session_fee_impact(taker_fee)
        if session_impact > self.fee_accumulation_limit:
            logger.warning(
                "Taker order avoided: session_impact=%.4f > limit=%.4f",
                session_impact,
                self.fee_accumulation_limit,
            )
            return True

        return False

    def _calculate_break_even_threshold(
        self, order_type: OrderType, notional_value: float
    ) -> float:
        """
        手数料負け防止閾値計算

        Args:
            order_type: 注文タイプ
            notional_value: 想定元本

        Returns:
            損益分岐点閾値
        """
        if order_type == OrderType.MAKER:
            # メイカーの場合はリベートがあるのでより有利
            return abs(notional_value * self.MAKER_FEE_RATE) * 0.5
        else:
            # テイカーの場合は手数料を上回る利益が必要
            return notional_value * self.TAKER_FEE_RATE * 1.2

    def _calculate_session_fee_impact(self, additional_fee: float) -> float:
        """
        セッション累積手数料影響度計算

        Args:
            additional_fee: 追加手数料

        Returns:
            累積手数料影響度
        """
        total_fees = self.current_session_fees["taker_costs"] + abs(additional_fee)
        total_rebates = self.current_session_fees["maker_rebates"]

        net_impact = (total_fees - total_rebates) / 10000  # 1万円あたりの影響度
        return net_impact

    def _calculate_daily_summary(self) -> Dict[str, float]:
        """日次サマリー計算"""
        # 簡易実装：現在のセッション統計を返す
        return {
            "daily_trades": self.current_session_fees["trade_count"],
            "daily_net_fee": self.current_session_fees["maker_rebates"]
            - self.current_session_fees["taker_costs"],
            "daily_optimization_score": 0.8,  # 仮の値
        }

    def _calculate_weekly_summary(self) -> Dict[str, float]:
        """週次サマリー計算"""
        # 簡易実装：現在のセッション統計を返す
        return {
            "weekly_trades": self.current_session_fees["trade_count"],
            "weekly_net_fee": self.current_session_fees["maker_rebates"]
            - self.current_session_fees["taker_costs"],
            "weekly_optimization_score": 0.75,  # 仮の値
        }

    def _generate_recommendations(self) -> List[str]:
        """
        手数料最適化の推奨事項生成

        Returns:
            推奨事項リスト
        """
        recommendations = []

        if not self.fee_performance_history:
            return ["データが不足しています。取引を実行してください。"]

        latest = self.fee_performance_history[-1]

        # メイカー比率の推奨
        if latest.maker_ratio < 0.7:
            recommendations.append(
                "メイカー注文の比率を70%以上に上げることを推奨します。"
            )

        # 手数料効率の推奨
        if latest.net_fee_result < 0:
            recommendations.append(
                "手数料コストが利益を上回っています。メイカー注文を増やしてください。"
            )

        # 最適化スコアの推奨
        if latest.fee_optimization_score < 0.6:
            recommendations.append(
                "手数料最適化スコアが低いです。指値注文を優先してください。"
            )

        return recommendations
