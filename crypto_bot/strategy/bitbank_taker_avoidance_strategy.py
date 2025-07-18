"""
Bitbank テイカー手数料回避戦略
0.12%コスト回避・成行注文最小化・利益率向上システム
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from ..execution.bitbank_fee_guard import BitbankFeeGuard
from ..execution.bitbank_fee_optimizer import BitbankFeeOptimizer, OrderType

logger = logging.getLogger(__name__)


class AvoidanceStrategy(Enum):
    """回避戦略"""

    WAIT_FOR_FILL = "wait_for_fill"  # 約定待機
    PRICE_IMPROVEMENT = "price_improvement"  # 価格改善
    SPLIT_ORDER = "split_order"  # 分割注文
    TIME_DELAY = "time_delay"  # 時間遅延
    CANCEL_AND_REORDER = "cancel_and_reorder"  # キャンセル・再注文


class MarketCondition(Enum):
    """市場状況"""

    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLUME = "high_volume"
    LOW_VOLUME = "low_volume"


@dataclass
class TakerAvoidanceConfig:
    """テイカー回避設定"""

    max_wait_time_seconds: int = 300  # 最大待機時間（5分）
    price_improvement_ticks: int = 1  # 価格改善ティック数
    split_order_threshold: float = 0.005  # 分割注文閾値（0.5%）
    max_split_parts: int = 3  # 最大分割数
    reorder_attempts: int = 3  # 再注文試行回数
    volatility_threshold: float = 0.02  # ボラティリティ閾値（2%）
    volume_threshold_multiplier: float = 1.5  # 出来高閾値倍率

    # 緊急時設定
    emergency_taker_threshold: float = 0.8  # 緊急時テイカー許可閾値
    force_execution_time_limit: int = 600  # 強制実行制限時間（10分）


@dataclass
class AvoidanceResult:
    """回避結果"""

    strategy_used: AvoidanceStrategy
    success: bool
    original_order_type: OrderType
    final_order_type: OrderType
    fee_saved: float
    time_taken: float
    execution_price: float
    reason: str
    market_condition: MarketCondition


class BitbankTakerAvoidanceStrategy:
    """
    Bitbank テイカー手数料回避戦略

    0.12%テイカー手数料を回避し、メイカー手数料-0.02%を最大化する
    高度な注文管理システム
    """

    def __init__(
        self,
        bitbank_client,
        fee_optimizer: BitbankFeeOptimizer,
        fee_guard: BitbankFeeGuard,
        config: Optional[Dict] = None,
    ):

        self.bitbank_client = bitbank_client
        self.fee_optimizer = fee_optimizer
        self.fee_guard = fee_guard
        self.config = config or {}

        # 回避設定
        avoidance_config = self.config.get("bitbank_taker_avoidance", {})
        self.avoidance_config = TakerAvoidanceConfig(
            max_wait_time_seconds=avoidance_config.get("max_wait_time_seconds", 300),
            price_improvement_ticks=avoidance_config.get("price_improvement_ticks", 1),
            split_order_threshold=avoidance_config.get("split_order_threshold", 0.005),
            max_split_parts=avoidance_config.get("max_split_parts", 3),
            reorder_attempts=avoidance_config.get("reorder_attempts", 3),
            volatility_threshold=avoidance_config.get("volatility_threshold", 0.02),
            volume_threshold_multiplier=avoidance_config.get(
                "volume_threshold_multiplier", 1.5
            ),
            emergency_taker_threshold=avoidance_config.get(
                "emergency_taker_threshold", 0.8
            ),
            force_execution_time_limit=avoidance_config.get(
                "force_execution_time_limit", 600
            ),
        )

        # 統計情報
        self.avoidance_stats = {
            "total_attempts": 0,
            "successful_avoidances": 0,
            "failed_avoidances": 0,
            "emergency_taker_executions": 0,
            "total_fees_saved": 0.0,
            "average_wait_time": 0.0,
            "strategy_usage": {strategy.value: 0 for strategy in AvoidanceStrategy},
        }

        # 市場データキャッシュ
        self.market_data_cache: Dict[str, Dict] = {}
        self.cache_expiry = 30  # 30秒

        # 実行履歴
        self.avoidance_history: List[AvoidanceResult] = []

        logger.info("BitbankTakerAvoidanceStrategy initialized")
        logger.info(f"Max wait time: {self.avoidance_config.max_wait_time_seconds}s")
        logger.info(
            f"Emergency threshold: {self.avoidance_config.emergency_taker_threshold}"
        )

    def attempt_taker_avoidance(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        urgency: float = 0.0,
        max_slippage: float = 0.001,
    ) -> AvoidanceResult:
        """
        テイカー手数料回避を試行

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 目標価格
            urgency: 緊急度（0.0-1.0）
            max_slippage: 最大スリッページ

        Returns:
            回避結果
        """
        start_time = time.time()
        self.avoidance_stats["total_attempts"] += 1

        logger.info(f"Attempting taker avoidance: {symbol} {side} {amount} @ {price}")

        # 1. 市場状況分析
        market_condition = self._analyze_market_condition(symbol)

        # 2. 緊急時チェック
        if urgency >= self.avoidance_config.emergency_taker_threshold:
            logger.warning(f"High urgency ({urgency}), proceeding with taker order")
            return self._execute_emergency_taker(
                symbol, side, amount, price, market_condition, start_time
            )

        # 3. 最適回避戦略選択
        strategy = self._select_avoidance_strategy(
            symbol, side, amount, price, market_condition, urgency
        )

        # 4. 回避戦略実行
        result = self._execute_avoidance_strategy(
            strategy,
            symbol,
            side,
            amount,
            price,
            market_condition,
            urgency,
            max_slippage,
            start_time,
        )

        # 5. 統計更新
        self._update_avoidance_stats(result)

        # 6. 履歴記録
        self.avoidance_history.append(result)

        logger.info(
            "Avoidance result: %s - Success: %s",
            result.strategy_used.value,
            result.success,
        )
        logger.info(
            "Fee saved: %.6f, Time taken: %.2fs", result.fee_saved, result.time_taken
        )

        return result

    def _analyze_market_condition(self, symbol: str) -> MarketCondition:
        """市場状況分析"""
        try:
            # キャッシュチェック
            if symbol in self.market_data_cache:
                cache_data = self.market_data_cache[symbol]
                if time.time() - cache_data["timestamp"] < self.cache_expiry:
                    return cache_data["condition"]

            # 市場データ取得
            # ticker = self.bitbank_client.fetch_ticker(symbol)
            ohlcv = self.bitbank_client.fetch_ohlcv(symbol, "1m", limit=20)

            # ボラティリティ計算
            prices = np.array([candle[4] for candle in ohlcv])  # 終値
            volatility = np.std(prices) / np.mean(prices)

            # 出来高分析
            volumes = np.array([candle[5] for candle in ohlcv])  # 出来高
            avg_volume = np.mean(volumes)
            current_volume = volumes[-1]

            # 価格変動分析
            price_change = (prices[-1] - prices[0]) / prices[0]

            # 市場状況判定
            if volatility > self.avoidance_config.volatility_threshold:
                condition = MarketCondition.HIGH_VOLATILITY
            elif (
                current_volume
                > avg_volume * self.avoidance_config.volume_threshold_multiplier
            ):
                condition = MarketCondition.HIGH_VOLUME
            elif abs(price_change) > 0.01:  # 1%以上の変動
                condition = MarketCondition.TRENDING
            elif volatility < self.avoidance_config.volatility_threshold * 0.5:
                condition = MarketCondition.LOW_VOLATILITY
            else:
                condition = MarketCondition.RANGING

            # キャッシュ更新
            self.market_data_cache[symbol] = {
                "condition": condition,
                "timestamp": time.time(),
                "volatility": volatility,
                "volume_ratio": current_volume / avg_volume,
            }

            return condition

        except Exception as e:
            logger.error(f"Failed to analyze market condition: {e}")
            return MarketCondition.RANGING

    def _select_avoidance_strategy(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        urgency: float,
    ) -> AvoidanceStrategy:
        """回避戦略選択"""
        # 市場状況別戦略選択
        if market_condition == MarketCondition.HIGH_VOLATILITY:
            # 高ボラティリティ時は時間遅延を短縮
            if urgency < 0.3:
                return AvoidanceStrategy.WAIT_FOR_FILL
            else:
                return AvoidanceStrategy.PRICE_IMPROVEMENT

        elif market_condition == MarketCondition.LOW_VOLATILITY:
            # 低ボラティリティ時は待機戦略が有効
            return AvoidanceStrategy.WAIT_FOR_FILL

        elif market_condition == MarketCondition.TRENDING:
            # トレンド相場では価格改善が困難
            if amount > 0.01:  # 大口注文
                return AvoidanceStrategy.SPLIT_ORDER
            else:
                return AvoidanceStrategy.TIME_DELAY

        elif market_condition == MarketCondition.HIGH_VOLUME:
            # 高出来高時は約定しやすい
            return AvoidanceStrategy.WAIT_FOR_FILL

        else:  # RANGING, LOW_VOLUME
            # レンジ相場では価格改善が有効
            return AvoidanceStrategy.PRICE_IMPROVEMENT

    def _execute_avoidance_strategy(
        self,
        strategy: AvoidanceStrategy,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        urgency: float,
        max_slippage: float,
        start_time: float,
    ) -> AvoidanceResult:
        """回避戦略実行"""
        self.avoidance_stats["strategy_usage"][strategy.value] += 1

        try:
            if strategy == AvoidanceStrategy.WAIT_FOR_FILL:
                return self._wait_for_fill_strategy(
                    symbol, side, amount, price, market_condition, start_time
                )

            elif strategy == AvoidanceStrategy.PRICE_IMPROVEMENT:
                return self._price_improvement_strategy(
                    symbol, side, amount, price, market_condition, start_time
                )

            elif strategy == AvoidanceStrategy.SPLIT_ORDER:
                return self._split_order_strategy(
                    symbol, side, amount, price, market_condition, start_time
                )

            elif strategy == AvoidanceStrategy.TIME_DELAY:
                return self._time_delay_strategy(
                    symbol, side, amount, price, market_condition, urgency, start_time
                )

            elif strategy == AvoidanceStrategy.CANCEL_AND_REORDER:
                return self._cancel_and_reorder_strategy(
                    symbol, side, amount, price, market_condition, start_time
                )

            else:
                # デフォルト戦略
                return self._wait_for_fill_strategy(
                    symbol, side, amount, price, market_condition, start_time
                )

        except Exception as e:
            logger.error(f"Avoidance strategy failed: {e}")
            return AvoidanceResult(
                strategy_used=strategy,
                success=False,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason=f"Strategy execution failed: {e}",
                market_condition=market_condition,
            )

    def _wait_for_fill_strategy(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        start_time: float,
    ) -> AvoidanceResult:
        """約定待機戦略"""
        logger.info("Executing wait-for-fill strategy")

        # 指値注文で開始
        try:
            order = self.bitbank_client.create_order(
                symbol=symbol,
                side=side,
                type="limit",
                amount=amount,
                price=price,
                params={"post_only": True},
            )

            order_id = order["id"]

            # 約定待機
            wait_time = 0
            check_interval = 5  # 5秒間隔

            while wait_time < self.avoidance_config.max_wait_time_seconds:
                time.sleep(check_interval)
                wait_time += check_interval

                # 注文状況確認
                order_status = self.bitbank_client.fetch_order(order_id, symbol)

                if order_status["status"] == "closed":
                    # 約定完了
                    fee_saved = self._calculate_fee_saved(amount, price)

                    return AvoidanceResult(
                        strategy_used=AvoidanceStrategy.WAIT_FOR_FILL,
                        success=True,
                        original_order_type=OrderType.TAKER,
                        final_order_type=OrderType.MAKER,
                        fee_saved=fee_saved,
                        time_taken=time.time() - start_time,
                        execution_price=float(order_status["price"]),
                        reason="Successfully filled as maker order",
                        market_condition=market_condition,
                    )

            # タイムアウト - 注文キャンセル
            self.bitbank_client.cancel_order(order_id, symbol)

            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.WAIT_FOR_FILL,
                success=False,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason="Timeout waiting for fill",
                market_condition=market_condition,
            )

        except Exception as e:
            logger.error(f"Wait-for-fill strategy failed: {e}")
            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.WAIT_FOR_FILL,
                success=False,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason=f"Strategy failed: {e}",
                market_condition=market_condition,
            )

    def _price_improvement_strategy(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        start_time: float,
    ) -> AvoidanceResult:
        """価格改善戦略"""
        logger.info("Executing price improvement strategy")

        try:
            # 現在のオーダーブック取得
            orderbook = self.bitbank_client.fetch_order_book(symbol)

            # 価格改善計算
            if side == "buy":
                best_bid = orderbook["bids"][0][0]
                improved_price = best_bid + (
                    0.01 * self.avoidance_config.price_improvement_ticks
                )
            else:
                best_ask = orderbook["asks"][0][0]
                improved_price = best_ask - (
                    0.01 * self.avoidance_config.price_improvement_ticks
                )

            # 改善された価格で指値注文
            order = self.bitbank_client.create_order(
                symbol=symbol,
                side=side,
                type="limit",
                amount=amount,
                price=improved_price,
                params={"post_only": True},
            )

            # 短時間待機
            time.sleep(30)  # 30秒待機

            order_status = self.bitbank_client.fetch_order(order["id"], symbol)

            if order_status["status"] == "closed":
                fee_saved = self._calculate_fee_saved(amount, improved_price)

                return AvoidanceResult(
                    strategy_used=AvoidanceStrategy.PRICE_IMPROVEMENT,
                    success=True,
                    original_order_type=OrderType.TAKER,
                    final_order_type=OrderType.MAKER,
                    fee_saved=fee_saved,
                    time_taken=time.time() - start_time,
                    execution_price=improved_price,
                    reason="Price improvement successful",
                    market_condition=market_condition,
                )
            else:
                # 約定しなかった場合はキャンセル
                self.bitbank_client.cancel_order(order["id"], symbol)

                return AvoidanceResult(
                    strategy_used=AvoidanceStrategy.PRICE_IMPROVEMENT,
                    success=False,
                    original_order_type=OrderType.TAKER,
                    final_order_type=OrderType.TAKER,
                    fee_saved=0.0,
                    time_taken=time.time() - start_time,
                    execution_price=price,
                    reason="Price improvement did not fill",
                    market_condition=market_condition,
                )

        except Exception as e:
            logger.error(f"Price improvement strategy failed: {e}")
            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.PRICE_IMPROVEMENT,
                success=False,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason=f"Strategy failed: {e}",
                market_condition=market_condition,
            )

    def _split_order_strategy(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        start_time: float,
    ) -> AvoidanceResult:
        """分割注文戦略"""
        logger.info("Executing split order strategy")

        try:
            # 注文分割
            split_size = amount / min(self.avoidance_config.max_split_parts, 3)
            filled_amount = 0.0
            total_fee_saved = 0.0

            for _i in range(min(self.avoidance_config.max_split_parts, 3)):
                current_amount = min(split_size, amount - filled_amount)

                # 分割注文実行
                order = self.bitbank_client.create_order(
                    symbol=symbol,
                    side=side,
                    type="limit",
                    amount=current_amount,
                    price=price,
                    params={"post_only": True},
                )

                # 短時間待機
                time.sleep(20)  # 20秒待機

                order_status = self.bitbank_client.fetch_order(order["id"], symbol)

                if order_status["status"] == "closed":
                    filled_amount += current_amount
                    total_fee_saved += self._calculate_fee_saved(current_amount, price)
                else:
                    # 約定しなかった場合はキャンセル
                    self.bitbank_client.cancel_order(order["id"], symbol)

                if filled_amount >= amount:
                    break

            success = filled_amount >= amount * 0.8  # 80%以上約定で成功

            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.SPLIT_ORDER,
                success=success,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.MAKER if success else OrderType.TAKER,
                fee_saved=total_fee_saved,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason=f"Split order filled {filled_amount}/{amount}",
                market_condition=market_condition,
            )

        except Exception as e:
            logger.error(f"Split order strategy failed: {e}")
            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.SPLIT_ORDER,
                success=False,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason=f"Strategy failed: {e}",
                market_condition=market_condition,
            )

    def _time_delay_strategy(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        urgency: float,
        start_time: float,
    ) -> AvoidanceResult:
        """時間遅延戦略"""
        logger.info("Executing time delay strategy")

        # 緊急度に応じた遅延時間
        delay_time = max(30, int(180 * (1 - urgency)))  # 30秒～180秒

        time.sleep(delay_time)

        # 遅延後に指値注文
        try:
            order = self.bitbank_client.create_order(
                symbol=symbol,
                side=side,
                type="limit",
                amount=amount,
                price=price,
                params={"post_only": True},
            )

            # 短時間待機
            time.sleep(30)

            order_status = self.bitbank_client.fetch_order(order["id"], symbol)

            if order_status["status"] == "closed":
                fee_saved = self._calculate_fee_saved(amount, price)

                return AvoidanceResult(
                    strategy_used=AvoidanceStrategy.TIME_DELAY,
                    success=True,
                    original_order_type=OrderType.TAKER,
                    final_order_type=OrderType.MAKER,
                    fee_saved=fee_saved,
                    time_taken=time.time() - start_time,
                    execution_price=price,
                    reason="Time delay strategy successful",
                    market_condition=market_condition,
                )
            else:
                self.bitbank_client.cancel_order(order["id"], symbol)

                return AvoidanceResult(
                    strategy_used=AvoidanceStrategy.TIME_DELAY,
                    success=False,
                    original_order_type=OrderType.TAKER,
                    final_order_type=OrderType.TAKER,
                    fee_saved=0.0,
                    time_taken=time.time() - start_time,
                    execution_price=price,
                    reason="Time delay did not result in fill",
                    market_condition=market_condition,
                )

        except Exception as e:
            logger.error(f"Time delay strategy failed: {e}")
            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.TIME_DELAY,
                success=False,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason=f"Strategy failed: {e}",
                market_condition=market_condition,
            )

    def _cancel_and_reorder_strategy(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        start_time: float,
    ) -> AvoidanceResult:
        """キャンセル・再注文戦略"""
        logger.info("Executing cancel and reorder strategy")

        for attempt in range(self.avoidance_config.reorder_attempts):
            try:
                # 指値注文
                order = self.bitbank_client.create_order(
                    symbol=symbol,
                    side=side,
                    type="limit",
                    amount=amount,
                    price=price,
                    params={"post_only": True},
                )

                # 短時間待機
                time.sleep(45)  # 45秒待機

                order_status = self.bitbank_client.fetch_order(order["id"], symbol)

                if order_status["status"] == "closed":
                    fee_saved = self._calculate_fee_saved(amount, price)

                    return AvoidanceResult(
                        strategy_used=AvoidanceStrategy.CANCEL_AND_REORDER,
                        success=True,
                        original_order_type=OrderType.TAKER,
                        final_order_type=OrderType.MAKER,
                        fee_saved=fee_saved,
                        time_taken=time.time() - start_time,
                        execution_price=price,
                        reason=f"Reorder successful on attempt {attempt + 1}",
                        market_condition=market_condition,
                    )
                else:
                    # キャンセルして次の試行へ
                    self.bitbank_client.cancel_order(order["id"], symbol)

                    if attempt < self.avoidance_config.reorder_attempts - 1:
                        time.sleep(30)  # 次の試行前に待機

            except Exception as e:
                logger.error(f"Reorder attempt {attempt + 1} failed: {e}")
                if attempt < self.avoidance_config.reorder_attempts - 1:
                    time.sleep(30)

        return AvoidanceResult(
            strategy_used=AvoidanceStrategy.CANCEL_AND_REORDER,
            success=False,
            original_order_type=OrderType.TAKER,
            final_order_type=OrderType.TAKER,
            fee_saved=0.0,
            time_taken=time.time() - start_time,
            execution_price=price,
            reason="All reorder attempts failed",
            market_condition=market_condition,
        )

    def _execute_emergency_taker(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        market_condition: MarketCondition,
        start_time: float,
    ) -> AvoidanceResult:
        """緊急時テイカー実行"""
        logger.warning("Executing emergency taker order")

        self.avoidance_stats["emergency_taker_executions"] += 1

        try:
            order = self.bitbank_client.create_order(
                symbol=symbol, side=side, type="market", amount=amount
            )

            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.WAIT_FOR_FILL,  # 便宜上
                success=False,  # 回避失敗
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=float(order["price"]),
                reason="Emergency taker execution due to high urgency",
                market_condition=market_condition,
            )

        except Exception as e:
            logger.error(f"Emergency taker execution failed: {e}")
            return AvoidanceResult(
                strategy_used=AvoidanceStrategy.WAIT_FOR_FILL,
                success=False,
                original_order_type=OrderType.TAKER,
                final_order_type=OrderType.TAKER,
                fee_saved=0.0,
                time_taken=time.time() - start_time,
                execution_price=price,
                reason=f"Emergency execution failed: {e}",
                market_condition=market_condition,
            )

    def _calculate_fee_saved(self, amount: float, price: float) -> float:
        """手数料節約額計算"""
        notional = amount * price
        taker_fee = notional * 0.0012  # 0.12%
        maker_fee = notional * -0.0002  # -0.02%
        return taker_fee - maker_fee  # 実際には taker_fee + abs(maker_fee)

    def _update_avoidance_stats(self, result: AvoidanceResult) -> None:
        """統計情報更新"""
        if result.success:
            self.avoidance_stats["successful_avoidances"] += 1
            self.avoidance_stats["total_fees_saved"] += result.fee_saved
        else:
            self.avoidance_stats["failed_avoidances"] += 1

        # 平均待機時間更新
        total_attempts = self.avoidance_stats["total_attempts"]
        current_avg = self.avoidance_stats["average_wait_time"]
        self.avoidance_stats["average_wait_time"] = (
            current_avg * (total_attempts - 1) + result.time_taken
        ) / total_attempts

    def get_avoidance_statistics(self) -> Dict[str, Any]:
        """回避統計取得"""
        total_attempts = self.avoidance_stats["total_attempts"]
        success_rate = (
            (self.avoidance_stats["successful_avoidances"] / total_attempts)
            if total_attempts > 0
            else 0
        )

        return {
            "summary": {
                "total_attempts": total_attempts,
                "successful_avoidances": self.avoidance_stats["successful_avoidances"],
                "failed_avoidances": self.avoidance_stats["failed_avoidances"],
                "emergency_taker_executions": self.avoidance_stats[
                    "emergency_taker_executions"
                ],
                "success_rate": success_rate,
                "average_wait_time": self.avoidance_stats["average_wait_time"],
            },
            "fee_impact": {
                "total_fees_saved": self.avoidance_stats["total_fees_saved"],
                "average_fee_saved_per_success": (
                    self.avoidance_stats["total_fees_saved"]
                    / max(self.avoidance_stats["successful_avoidances"], 1)
                ),
                "estimated_monthly_savings": self.avoidance_stats["total_fees_saved"]
                * 30,
            },
            "strategy_usage": self.avoidance_stats["strategy_usage"],
            "performance_by_condition": self._analyze_performance_by_condition(),
        }

    def _analyze_performance_by_condition(self) -> Dict[str, Dict]:
        """市場状況別パフォーマンス分析"""
        condition_stats = {}

        for result in self.avoidance_history:
            condition = result.market_condition.value

            if condition not in condition_stats:
                condition_stats[condition] = {
                    "attempts": 0,
                    "successes": 0,
                    "total_fee_saved": 0.0,
                    "average_time": 0.0,
                }

            stats = condition_stats[condition]
            stats["attempts"] += 1

            if result.success:
                stats["successes"] += 1
                stats["total_fee_saved"] += result.fee_saved

            # 平均時間更新
            stats["average_time"] = (
                stats["average_time"] * (stats["attempts"] - 1) + result.time_taken
            ) / stats["attempts"]

        # 成功率計算
        for _condition, stats in condition_stats.items():
            stats["success_rate"] = (
                stats["successes"] / stats["attempts"] if stats["attempts"] > 0 else 0
            )

        return condition_stats

    def reset_statistics(self) -> None:
        """統計情報リセット"""
        self.avoidance_stats = {
            "total_attempts": 0,
            "successful_avoidances": 0,
            "failed_avoidances": 0,
            "emergency_taker_executions": 0,
            "total_fees_saved": 0.0,
            "average_wait_time": 0.0,
            "strategy_usage": {strategy.value: 0 for strategy in AvoidanceStrategy},
        }

        self.avoidance_history.clear()
        self.market_data_cache.clear()

        logger.info("Taker avoidance statistics reset")
