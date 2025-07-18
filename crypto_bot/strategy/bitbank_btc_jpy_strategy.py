"""
Bitbank BTC/JPY安定戦略
大口対応・予測性活用・安定トレンド戦略・スプレッド最小化
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from ..execution.bitbank_fee_guard import BitbankFeeGuard
from ..execution.bitbank_fee_optimizer import BitbankFeeOptimizer
from ..execution.bitbank_order_manager import BitbankOrderManager
from .bitbank_enhanced_position_manager import BitbankEnhancedPositionManager

logger = logging.getLogger(__name__)


class BTCTradingPhase(Enum):
    """BTC取引フェーズ"""

    UPTREND = "uptrend"  # 上昇トレンド
    DOWNTREND = "downtrend"  # 下降トレンド
    SIDEWAYS = "sideways"  # 横ばい
    ACCUMULATION = "accumulation"  # 蓄積期
    DISTRIBUTION = "distribution"  # 分散期
    CONSOLIDATION = "consolidation"  # 整理期
    BREAKOUT_UPWARD = "breakout_upward"  # 上方ブレイクアウト
    BREAKOUT_DOWNWARD = "breakout_downward"  # 下方ブレイクアウト


class BTCTradingStrategy(Enum):
    """BTC取引戦略"""

    TREND_FOLLOWING = "trend_following"  # トレンドフォロー
    MEAN_REVERSION = "mean_reversion"  # 平均回帰
    BREAKOUT = "breakout"  # ブレイクアウト
    SWING_TRADING = "swing_trading"  # スイングトレード
    POSITION_TRADING = "position_trading"  # ポジショントレード
    SPREAD_CAPTURE = "spread_capture"  # スプレッド獲得
    LARGE_ORDER_EXECUTION = "large_order_execution"  # 大口注文実行


@dataclass
class BTCMarketContext:
    """BTC市場コンテキスト"""

    symbol: str = "BTC/JPY"
    current_price: float = 0.0
    bid_ask_spread: float = 0.0
    spread_ratio: float = 0.0
    volume_24h: float = 0.0
    volatility: float = 0.0
    trend_strength: float = 0.0
    trend_direction: str = "neutral"

    # 技術指標
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    rsi_14: float = 0.0
    macd: float = 0.0
    macd_signal: float = 0.0
    bollinger_upper: float = 0.0
    bollinger_lower: float = 0.0
    bollinger_position: float = 0.0

    # 大口取引指標
    large_order_impact: float = 0.0
    market_depth: float = 0.0
    slippage_estimate: float = 0.0

    # 安定性指標
    price_stability: float = 0.0
    trend_consistency: float = 0.0
    predictability_score: float = 0.0


@dataclass
class BTCTradingConfig:
    """BTC取引設定"""

    min_order_size: float = 0.001  # 最小注文サイズ（BTC）
    max_order_size: float = 10.0  # 最大注文サイズ（BTC）
    large_order_threshold: float = 1.0  # 大口注文閾値（BTC）

    # トレンドフォロー設定
    trend_detection_period: int = 50  # トレンド検出期間
    trend_strength_threshold: float = 0.6  # トレンド強度閾値
    trend_profit_target: float = 0.02  # 2%利益目標
    trend_stop_loss: float = 0.01  # 1%ストップロス

    # 平均回帰設定
    reversion_detection_period: int = 20  # 回帰検出期間
    reversion_threshold: float = 2.0  # 2標準偏差
    reversion_profit_target: float = 0.01  # 1%利益目標
    reversion_stop_loss: float = 0.005  # 0.5%ストップロス

    # ブレイクアウト設定
    breakout_detection_period: int = 20  # ブレイクアウト検出期間
    breakout_volume_threshold: float = 1.5  # 出来高閾値（平均の1.5倍）
    breakout_profit_target: float = 0.03  # 3%利益目標
    breakout_stop_loss: float = 0.015  # 1.5%ストップロス

    # スプレッド獲得設定
    max_spread_ratio: float = 0.0005  # 0.05%最大スプレッド比率
    spread_profit_target: float = 0.001  # 0.1%利益目標
    spread_execution_timeout: int = 60  # 60秒実行タイムアウト

    # 大口注文設定
    large_order_slippage_limit: float = 0.001  # 0.1%スリッページ制限
    large_order_split_threshold: float = 5.0  # 5BTC分割閾値
    large_order_execution_interval: int = 30  # 30秒実行間隔

    # リスク管理
    daily_loss_limit: float = 0.02  # 2%日次損失制限
    position_size_limit: float = 50.0  # 50BTC最大ポジション
    volatility_adjustment_factor: float = 2.0  # ボラティリティ調整係数


class BitbankBTCJPYStrategy(BitbankEnhancedPositionManager):
    """
    Bitbank BTC/JPY安定戦略

    大口対応・予測性活用・安定トレンド戦略・スプレッド最小化
    """

    def __init__(
        self,
        bitbank_client,
        fee_optimizer: BitbankFeeOptimizer,
        fee_guard: BitbankFeeGuard,
        order_manager: BitbankOrderManager,
        config: Optional[Dict] = None,
    ):

        super().__init__(
            bitbank_client, fee_optimizer, fee_guard, order_manager, config
        )

        # BTC特化設定
        btc_config = self.config.get("bitbank_btc_jpy", {})
        self.btc_config = BTCTradingConfig(
            min_order_size=btc_config.get("min_order_size", 0.001),
            max_order_size=btc_config.get("max_order_size", 10.0),
            large_order_threshold=btc_config.get("large_order_threshold", 1.0),
            trend_detection_period=btc_config.get("trend_detection_period", 50),
            trend_strength_threshold=btc_config.get("trend_strength_threshold", 0.6),
            trend_profit_target=btc_config.get("trend_profit_target", 0.02),
            trend_stop_loss=btc_config.get("trend_stop_loss", 0.01),
            reversion_detection_period=btc_config.get("reversion_detection_period", 20),
            reversion_threshold=btc_config.get("reversion_threshold", 2.0),
            reversion_profit_target=btc_config.get("reversion_profit_target", 0.01),
            reversion_stop_loss=btc_config.get("reversion_stop_loss", 0.005),
            breakout_detection_period=btc_config.get("breakout_detection_period", 20),
            breakout_volume_threshold=btc_config.get("breakout_volume_threshold", 1.5),
            breakout_profit_target=btc_config.get("breakout_profit_target", 0.03),
            breakout_stop_loss=btc_config.get("breakout_stop_loss", 0.015),
            max_spread_ratio=btc_config.get("max_spread_ratio", 0.0005),
            spread_profit_target=btc_config.get("spread_profit_target", 0.001),
            spread_execution_timeout=btc_config.get("spread_execution_timeout", 60),
            large_order_slippage_limit=btc_config.get(
                "large_order_slippage_limit", 0.001
            ),
            large_order_split_threshold=btc_config.get(
                "large_order_split_threshold", 5.0
            ),
            large_order_execution_interval=btc_config.get(
                "large_order_execution_interval", 30
            ),
            daily_loss_limit=btc_config.get("daily_loss_limit", 0.02),
            position_size_limit=btc_config.get("position_size_limit", 50.0),
            volatility_adjustment_factor=btc_config.get(
                "volatility_adjustment_factor", 2.0
            ),
        )

        # 市場コンテキスト
        self.market_context = BTCMarketContext()

        # 取引統計
        self.btc_stats = {
            "total_btc_trades": 0,
            "profitable_btc_trades": 0,
            "btc_profit": 0.0,
            "btc_volume": 0.0,
            "trend_following_trades": 0,
            "mean_reversion_trades": 0,
            "breakout_trades": 0,
            "spread_capture_trades": 0,
            "large_order_trades": 0,
            "avg_holding_time": 0.0,
            "max_drawdown": 0.0,
            "trend_accuracy": 0.0,
            "spread_efficiency": 0.0,
        }

        # 価格・出来高履歴
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.spread_history: List[float] = []
        self.max_history_length = 200

        # トレンド分析
        self.trend_analysis = {
            "current_trend": "neutral",
            "trend_strength": 0.0,
            "trend_duration": 0,
            "trend_start_price": 0.0,
            "support_levels": [],
            "resistance_levels": [],
        }

        # 大口注文管理
        self.large_order_queue: List[Dict] = []
        self.large_order_execution_status: Dict[str, Dict] = {}

        # 監視スレッド
        self.btc_monitoring_thread = None
        self.btc_stop_monitoring = False

        logger.info("BitbankBTCJPYStrategy initialized")
        logger.info("BTC/JPY stable trading strategy")
        logger.info(
            f"Large order threshold: {self.btc_config.large_order_threshold} BTC"
        )
        logger.info(
            f"Trend following profit target: {self.btc_config.trend_profit_target:.1%}"
        )

    def analyze_market_context(self) -> BTCMarketContext:
        """市場コンテキスト分析"""
        try:
            # 市場データ取得
            ticker = self.bitbank_client.fetch_ticker("BTC/JPY")
            orderbook = self.bitbank_client.fetch_order_book("BTC/JPY")

            # 基本指標更新
            self.market_context.current_price = ticker["last"]
            self.market_context.bid_ask_spread = ticker["ask"] - ticker["bid"]
            self.market_context.spread_ratio = (
                self.market_context.bid_ask_spread / self.market_context.current_price
            )
            self.market_context.volume_24h = ticker["baseVolume"]

            # 履歴更新
            self.price_history.append(self.market_context.current_price)
            self.volume_history.append(self.market_context.volume_24h)
            self.spread_history.append(self.market_context.bid_ask_spread)

            # 履歴長制限
            if len(self.price_history) > self.max_history_length:
                self.price_history.pop(0)
                self.volume_history.pop(0)
                self.spread_history.pop(0)

            # 技術指標計算
            if len(self.price_history) >= 200:
                self._calculate_technical_indicators()

            # トレンド分析
            if len(self.price_history) >= 50:
                self._analyze_trend()

            # 市場深度分析
            self.market_context.market_depth = self._calculate_market_depth(orderbook)

            # 大口注文インパクト推定
            self.market_context.large_order_impact = self._estimate_large_order_impact(
                orderbook
            )

            # スリッページ推定
            self.market_context.slippage_estimate = self._estimate_slippage(orderbook)

            # 予測性スコア計算
            self.market_context.predictability_score = (
                self._calculate_predictability_score()
            )

            logger.debug(
                f"BTC market context updated: "
                f"price={self.market_context.current_price:.0f}, "
                f"trend={self.market_context.trend_direction}, "
                f"spread_ratio={self.market_context.spread_ratio:.4f}"
            )

            return self.market_context

        except Exception as e:
            logger.error(f"Failed to analyze BTC market context: {e}")
            return self.market_context

    def determine_trading_phase(self) -> BTCTradingPhase:
        """取引フェーズ判定"""
        try:
            # トレンド強度による判定
            if (
                self.market_context.trend_strength
                > self.btc_config.trend_strength_threshold
            ):
                if self.market_context.trend_direction == "upward":
                    return BTCTradingPhase.UPTREND
                elif self.market_context.trend_direction == "downward":
                    return BTCTradingPhase.DOWNTREND

            # ボラティリティによる判定
            if self.market_context.volatility < 0.01:  # 1%未満
                return BTCTradingPhase.CONSOLIDATION

            # ボリンジャーバンド位置による判定
            if self.market_context.bollinger_position > 0.9:
                return BTCTradingPhase.DISTRIBUTION
            elif self.market_context.bollinger_position < 0.1:
                return BTCTradingPhase.ACCUMULATION

            # MACD による判定
            if self.market_context.macd > self.market_context.macd_signal:
                if self.market_context.macd > 0:
                    return BTCTradingPhase.BREAKOUT_UPWARD
                else:
                    return BTCTradingPhase.SIDEWAYS
            else:
                if self.market_context.macd < 0:
                    return BTCTradingPhase.BREAKOUT_DOWNWARD
                else:
                    return BTCTradingPhase.SIDEWAYS

            return BTCTradingPhase.SIDEWAYS

        except Exception as e:
            logger.error(f"Failed to determine BTC trading phase: {e}")
            return BTCTradingPhase.SIDEWAYS

    def select_optimal_strategy(self, phase: BTCTradingPhase) -> BTCTradingStrategy:
        """最適戦略選択"""
        strategy_map = {
            BTCTradingPhase.UPTREND: BTCTradingStrategy.TREND_FOLLOWING,
            BTCTradingPhase.DOWNTREND: BTCTradingStrategy.TREND_FOLLOWING,
            BTCTradingPhase.SIDEWAYS: BTCTradingStrategy.MEAN_REVERSION,
            BTCTradingPhase.ACCUMULATION: BTCTradingStrategy.SWING_TRADING,
            BTCTradingPhase.DISTRIBUTION: BTCTradingStrategy.SWING_TRADING,
            BTCTradingPhase.CONSOLIDATION: BTCTradingStrategy.SPREAD_CAPTURE,
            BTCTradingPhase.BREAKOUT_UPWARD: BTCTradingStrategy.BREAKOUT,
            BTCTradingPhase.BREAKOUT_DOWNWARD: BTCTradingStrategy.BREAKOUT,
        }

        optimal_strategy = strategy_map.get(phase, BTCTradingStrategy.TREND_FOLLOWING)

        # 追加条件チェック
        if self.market_context.spread_ratio < self.btc_config.max_spread_ratio:
            optimal_strategy = BTCTradingStrategy.SPREAD_CAPTURE

        if self.market_context.predictability_score > 0.8:
            optimal_strategy = BTCTradingStrategy.POSITION_TRADING

        logger.info(
            f"Selected BTC strategy: {optimal_strategy.value} for phase: {phase.value}"
        )
        return optimal_strategy

    def execute_trend_following_strategy(self) -> Tuple[bool, str]:
        """トレンドフォロー戦略実行"""
        try:
            # トレンド確認
            if (
                self.market_context.trend_strength
                < self.btc_config.trend_strength_threshold
            ):
                return False, "Trend strength insufficient"

            # 注文サイズ決定（トレンド強度に応じて調整）
            base_size = self.btc_config.min_order_size * 10
            trend_adjustment = min(2.0, self.market_context.trend_strength * 2)
            order_size = base_size * trend_adjustment

            # 方向性決定
            if self.market_context.trend_direction == "upward":
                side = "buy"
                target_price = self.market_context.current_price * (
                    1 + self.btc_config.trend_profit_target
                )
                stop_loss_price = self.market_context.current_price * (
                    1 - self.btc_config.trend_stop_loss
                )
            elif self.market_context.trend_direction == "downward":
                side = "sell"
                target_price = self.market_context.current_price * (
                    1 - self.btc_config.trend_profit_target
                )
                stop_loss_price = self.market_context.current_price * (
                    1 + self.btc_config.trend_stop_loss
                )
            else:
                return False, "No clear trend direction"

            # ポジション開設
            success, message, position_id = self.open_position(
                "BTC/JPY",
                side,
                order_size,
                target_price,
                reason="trend_following_strategy",
            )

            if success:
                self.btc_stats["trend_following_trades"] += 1

                # ストップロス設定
                self._set_stop_loss(position_id, stop_loss_price)

                logger.info(
                    f"Trend following position opened: {position_id} - "
                    f"{side} {order_size} BTC"
                )
                logger.info(f"Target: {target_price:.0f}, Stop: {stop_loss_price:.0f}")

            return success, message

        except Exception as e:
            logger.error(f"Trend following strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_mean_reversion_strategy(self) -> Tuple[bool, str]:
        """平均回帰戦略実行"""
        try:
            # 平均からの乖離計算
            if len(self.price_history) < self.btc_config.reversion_detection_period:
                return False, "Insufficient price history"

            recent_prices = self.price_history[
                -self.btc_config.reversion_detection_period :
            ]
            mean_price = np.mean(recent_prices)
            std_price = np.std(recent_prices)

            # Z-score計算
            z_score = (self.market_context.current_price - mean_price) / std_price

            # 回帰条件チェック
            if abs(z_score) < self.btc_config.reversion_threshold:
                return False, "Price not sufficiently deviated from mean"

            # 注文サイズ決定（乖離度に応じて調整）
            base_size = self.btc_config.min_order_size * 5
            deviation_adjustment = min(2.0, abs(z_score) / 2)
            order_size = base_size * deviation_adjustment

            # 方向性決定
            if z_score > self.btc_config.reversion_threshold:  # 価格が高すぎる
                side = "sell"
                target_price = mean_price
            else:  # 価格が低すぎる
                side = "buy"
                target_price = mean_price

            # ポジション開設
            success, message, position_id = self.open_position(
                "BTC/JPY",
                side,
                order_size,
                target_price,
                reason="mean_reversion_strategy",
            )

            if success:
                self.btc_stats["mean_reversion_trades"] += 1
                logger.info(
                    f"Mean reversion position opened: {position_id} - "
                    f"z_score={z_score:.2f}"
                )

            return success, message

        except Exception as e:
            logger.error(f"Mean reversion strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_breakout_strategy(self) -> Tuple[bool, str]:
        """ブレイクアウト戦略実行"""
        try:
            # ブレイクアウト検出
            if len(self.price_history) < self.btc_config.breakout_detection_period:
                return False, "Insufficient price history"

            recent_prices = self.price_history[
                -self.btc_config.breakout_detection_period :
            ]
            resistance_level = max(recent_prices[:-1])  # 最新価格を除く最高値
            support_level = min(recent_prices[:-1])  # 最新価格を除く最安値

            current_price = self.market_context.current_price

            # 出来高確認
            if len(self.volume_history) >= 20:
                avg_volume = np.mean(self.volume_history[-20:])
                current_volume = self.market_context.volume_24h
                volume_ratio = current_volume / avg_volume

                if volume_ratio < self.btc_config.breakout_volume_threshold:
                    return False, "Insufficient volume for breakout"

            # ブレイクアウト方向判定
            if current_price > resistance_level * 1.001:  # 上方ブレイクアウト
                side = "buy"
                target_price = current_price * (
                    1 + self.btc_config.breakout_profit_target
                )
                stop_loss_price = resistance_level * 0.999
            elif current_price < support_level * 0.999:  # 下方ブレイクアウト
                side = "sell"
                target_price = current_price * (
                    1 - self.btc_config.breakout_profit_target
                )
                stop_loss_price = support_level * 1.001
            else:
                return False, "No clear breakout detected"

            # 注文サイズ決定
            order_size = self.btc_config.min_order_size * 15

            # ポジション開設
            success, message, position_id = self.open_position(
                "BTC/JPY", side, order_size, target_price, reason="breakout_strategy"
            )

            if success:
                self.btc_stats["breakout_trades"] += 1
                self._set_stop_loss(position_id, stop_loss_price)
                logger.info(
                    f"Breakout position opened: {position_id} - {side} breakout"
                )

            return success, message

        except Exception as e:
            logger.error(f"Breakout strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_spread_capture_strategy(self) -> Tuple[bool, str]:
        """スプレッド獲得戦略実行"""
        try:
            # スプレッド確認
            if self.market_context.spread_ratio > self.btc_config.max_spread_ratio:
                return False, "Spread too wide for capture strategy"

            # 両建て戦略
            mid_price = self.market_context.current_price + (
                self.market_context.current_price
                - self.market_context.bid_ask_spread / 2
            )

            buy_price = mid_price - (self.market_context.bid_ask_spread * 0.3)
            sell_price = mid_price + (self.market_context.bid_ask_spread * 0.3)

            order_size = self.btc_config.min_order_size * 3

            # 買い注文
            buy_success, buy_message, buy_position_id = self.open_position(
                "BTC/JPY", "buy", order_size, buy_price, reason="spread_capture_buy"
            )

            # 売り注文
            sell_success, sell_message, sell_position_id = self.open_position(
                "BTC/JPY", "sell", order_size, sell_price, reason="spread_capture_sell"
            )

            if buy_success or sell_success:
                self.btc_stats["spread_capture_trades"] += 1

                # タイムアウト設定
                self._schedule_spread_capture_exit(buy_position_id, sell_position_id)

                logger.info(
                    f"Spread capture orders: buy={buy_success}, sell={sell_success}"
                )

            return (
                buy_success or sell_success,
                f"Buy: {buy_message}, Sell: {sell_message}",
            )

        except Exception as e:
            logger.error(f"Spread capture strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_large_order(
        self, side: str, total_amount: float, target_price: float
    ) -> Tuple[bool, str]:
        """大口注文実行"""
        try:
            # 大口注文判定
            if total_amount < self.btc_config.large_order_threshold:
                return self.open_position(
                    "BTC/JPY", side, total_amount, target_price, reason="regular_order"
                )

            # スリッページ推定
            estimated_slippage = self._estimate_large_order_slippage(total_amount)
            if estimated_slippage > self.btc_config.large_order_slippage_limit:
                return (
                    False,
                    f"Estimated slippage {estimated_slippage:.4f} exceeds limit",
                )

            # 注文分割判定
            if total_amount > self.btc_config.large_order_split_threshold:
                return self._execute_split_order(side, total_amount, target_price)

            # 大口注文実行
            success, message, position_id = self.open_position(
                "BTC/JPY",
                side,
                total_amount,
                target_price,
                reason="large_order_execution",
            )

            if success:
                self.btc_stats["large_order_trades"] += 1
                logger.info(
                    f"Large order executed: {total_amount} BTC @ {target_price:.0f}"
                )

            return success, message

        except Exception as e:
            logger.error(f"Large order execution failed: {e}")
            return False, f"Exception: {e}"

    def _execute_split_order(
        self, side: str, total_amount: float, target_price: float
    ) -> Tuple[bool, str]:
        """分割注文実行"""
        try:
            # 分割数計算
            split_count = int(
                np.ceil(total_amount / self.btc_config.large_order_split_threshold)
            )
            chunk_size = total_amount / split_count

            executed_orders = []
            total_executed = 0.0

            for i in range(split_count):
                # 価格調整（TWAP戦略）
                adjusted_price = target_price * (1 + (i * 0.0001))  # 微調整

                success, message, position_id = self.open_position(
                    "BTC/JPY",
                    side,
                    chunk_size,
                    adjusted_price,
                    reason=f"split_order_{i+1}_{split_count}",
                )

                if success:
                    executed_orders.append(position_id)
                    total_executed += chunk_size

                # 実行間隔
                if i < split_count - 1:
                    time.sleep(self.btc_config.large_order_execution_interval)

            success_rate = len(executed_orders) / split_count

            logger.info(
                f"Split order completed: {len(executed_orders)}/{split_count} orders, "
                f"{total_executed:.4f}/{total_amount:.4f} BTC"
            )

            return (
                success_rate > 0.5,
                f"Split order: {len(executed_orders)}/{split_count} successful",
            )

        except Exception as e:
            logger.error(f"Split order execution failed: {e}")
            return False, f"Split order exception: {e}"

    def _calculate_technical_indicators(self) -> None:
        """技術指標計算"""
        try:
            prices = np.array(self.price_history)

            # 移動平均
            if len(prices) >= 20:
                self.market_context.sma_20 = np.mean(prices[-20:])
            if len(prices) >= 50:
                self.market_context.sma_50 = np.mean(prices[-50:])
            if len(prices) >= 200:
                self.market_context.sma_200 = np.mean(prices[-200:])

            # EMA計算
            if len(prices) >= 26:
                self.market_context.ema_12 = self._calculate_ema(prices, 12)
                self.market_context.ema_26 = self._calculate_ema(prices, 26)

            # MACD計算
            if self.market_context.ema_12 > 0 and self.market_context.ema_26 > 0:
                self.market_context.macd = (
                    self.market_context.ema_12 - self.market_context.ema_26
                )

                # MACD信号線（簡易版）
                if len(prices) >= 35:
                    macd_values = [self.market_context.macd]  # 簡略化
                    self.market_context.macd_signal = np.mean(macd_values)

            # RSI計算
            if len(prices) >= 15:
                self.market_context.rsi_14 = self._calculate_rsi(prices, 14)

            # ボリンジャーバンド
            if len(prices) >= 20:
                sma_20 = self.market_context.sma_20
                std_20 = np.std(prices[-20:])
                self.market_context.bollinger_upper = sma_20 + (2 * std_20)
                self.market_context.bollinger_lower = sma_20 - (2 * std_20)

                current_price = prices[-1]
                self.market_context.bollinger_position = (
                    current_price - self.market_context.bollinger_lower
                ) / (
                    self.market_context.bollinger_upper
                    - self.market_context.bollinger_lower
                )

            # ボラティリティ
            if len(prices) >= 20:
                returns = np.diff(np.log(prices[-20:]))
                self.market_context.volatility = np.std(returns) * np.sqrt(
                    24
                )  # 日次ボラティリティ

        except Exception as e:
            logger.error(f"Failed to calculate technical indicators: {e}")

    def _analyze_trend(self) -> None:
        """トレンド分析"""
        try:
            prices = np.array(self.price_history)

            # 線形回帰によるトレンド検出
            x = np.arange(len(prices))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)

            # トレンド強度
            self.market_context.trend_strength = abs(r_value)

            # トレンド方向
            if slope > 0 and p_value < 0.05:
                self.market_context.trend_direction = "upward"
            elif slope < 0 and p_value < 0.05:
                self.market_context.trend_direction = "downward"
            else:
                self.market_context.trend_direction = "neutral"

            # サポート・レジスタンス検出
            if len(prices) >= 50:
                self._detect_support_resistance()

        except Exception as e:
            logger.error(f"Failed to analyze trend: {e}")

    def _detect_support_resistance(self) -> None:
        """サポート・レジスタンス検出"""
        try:
            prices = np.array(self.price_history[-50:])  # 直近50期間

            # 局所最大・最小値検出
            from scipy.signal import argrelextrema

            # 局所最大値（レジスタンス）
            resistance_indices = argrelextrema(prices, np.greater, order=5)[0]
            resistance_levels = prices[resistance_indices]

            # 局所最小値（サポート）
            support_indices = argrelextrema(prices, np.less, order=5)[0]
            support_levels = prices[support_indices]

            # 重要なレベルのみ保持（複数回タッチされたレベル）
            self.trend_analysis["resistance_levels"] = self._filter_significant_levels(
                resistance_levels
            )
            self.trend_analysis["support_levels"] = self._filter_significant_levels(
                support_levels
            )

        except Exception as e:
            logger.error(f"Failed to detect support/resistance: {e}")

    def _filter_significant_levels(
        self, levels: np.ndarray, tolerance: float = 0.01
    ) -> List[float]:
        """重要なレベルフィルタリング"""
        if len(levels) == 0:
            return []

        significant_levels = []
        for level in levels:
            # 既存レベルとの近似チェック
            is_significant = True
            for existing_level in significant_levels:
                if abs(level - existing_level) / existing_level < tolerance:
                    is_significant = False
                    break

            if is_significant:
                significant_levels.append(float(level))

        return sorted(significant_levels)

    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """EMA計算"""
        alpha = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """RSI計算"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_market_depth(self, orderbook: Dict) -> float:
        """市場深度計算"""
        try:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return 0.0

            # 上位10レベルの深度
            bid_depth = sum(bid[1] for bid in bids[:10])
            ask_depth = sum(ask[1] for ask in asks[:10])

            total_depth = bid_depth + ask_depth
            return total_depth

        except Exception as e:
            logger.error(f"Failed to calculate market depth: {e}")
            return 0.0

    def _estimate_large_order_impact(self, orderbook: Dict) -> float:
        """大口注文インパクト推定"""
        try:
            test_amount = 10.0  # 10BTC
            return self._estimate_order_impact(orderbook, test_amount)

        except Exception as e:
            logger.error(f"Failed to estimate large order impact: {e}")
            return 0.0

    def _estimate_slippage(self, orderbook: Dict) -> float:
        """スリッページ推定"""
        try:
            test_amount = 1.0  # 1BTC
            return self._estimate_order_impact(orderbook, test_amount)

        except Exception as e:
            logger.error(f"Failed to estimate slippage: {e}")
            return 0.0

    def _estimate_order_impact(self, orderbook: Dict, amount: float) -> float:
        """注文インパクト推定"""
        try:
            asks = orderbook.get("asks", [])
            if not asks:
                return 0.0

            total_cost = 0.0
            remaining_amount = amount

            for ask in asks:
                if remaining_amount <= 0:
                    break

                trade_amount = min(remaining_amount, ask[1])
                total_cost += trade_amount * ask[0]
                remaining_amount -= trade_amount

            if amount == 0:
                return 0.0

            avg_price = total_cost / amount
            mid_price = asks[0][0]  # 最良売り価格

            impact = (avg_price - mid_price) / mid_price
            return impact

        except Exception as e:
            logger.error(f"Failed to estimate order impact: {e}")
            return 0.0

    def _estimate_large_order_slippage(self, amount: float) -> float:
        """大口注文スリッページ推定"""
        try:
            orderbook = self.bitbank_client.fetch_order_book("BTC/JPY")
            return self._estimate_order_impact(orderbook, amount)

        except Exception as e:
            logger.error(f"Failed to estimate large order slippage: {e}")
            return 0.01  # デフォルト1%

    def _calculate_predictability_score(self) -> float:
        """予測性スコア計算"""
        try:
            if len(self.price_history) < 50:
                return 0.0

            # トレンド一貫性
            trend_consistency = self.market_context.trend_strength

            # ボラティリティ安定性
            if len(self.price_history) >= 20:
                returns = np.diff(np.log(self.price_history[-20:]))
                volatility_stability = 1.0 / (1.0 + np.std(returns))
            else:
                volatility_stability = 0.5

            # 技術指標一貫性
            technical_consistency = 0.5
            if self.market_context.rsi_14 > 0:
                if 30 <= self.market_context.rsi_14 <= 70:
                    technical_consistency = 0.8
                else:
                    technical_consistency = 0.6

            predictability = (
                trend_consistency + volatility_stability + technical_consistency
            ) / 3
            return min(1.0, predictability)

        except Exception as e:
            logger.error(f"Failed to calculate predictability score: {e}")
            return 0.0

    def _set_stop_loss(self, position_id: str, stop_price: float) -> None:
        """ストップロス設定"""
        # 簡易実装（実際にはより詳細な実装が必要）
        def monitor_stop_loss():
            while position_id in self.active_positions:
                try:
                    current_price = self._get_current_price("BTC/JPY")
                    position = self.active_positions[position_id]

                    if current_price:
                        if (position.side == "buy" and current_price <= stop_price) or (
                            position.side == "sell" and current_price >= stop_price
                        ):
                            self.close_position(position_id, "stop_loss", force=True)
                            break

                    time.sleep(10)
                except Exception:
                    break

        stop_thread = threading.Thread(target=monitor_stop_loss)
        stop_thread.daemon = True
        stop_thread.start()

    def _schedule_spread_capture_exit(
        self, buy_position_id: str, sell_position_id: str
    ) -> None:
        """スプレッド獲得決済スケジュール"""

        def exit_timer():
            time.sleep(self.btc_config.spread_execution_timeout)

            if buy_position_id and buy_position_id in self.active_positions:
                self.close_position(
                    buy_position_id, "spread_capture_timeout", force=True
                )

            if sell_position_id and sell_position_id in self.active_positions:
                self.close_position(
                    sell_position_id, "spread_capture_timeout", force=True
                )

        timer_thread = threading.Thread(target=exit_timer)
        timer_thread.daemon = True
        timer_thread.start()

    def get_btc_strategy_status(self) -> Dict[str, any]:
        """BTC戦略状況取得"""
        current_phase = self.determine_trading_phase()
        optimal_strategy = self.select_optimal_strategy(current_phase)

        return {
            "symbol": "BTC/JPY",
            "market_context": {
                "current_price": self.market_context.current_price,
                "trend_direction": self.market_context.trend_direction,
                "trend_strength": self.market_context.trend_strength,
                "volatility": self.market_context.volatility,
                "spread_ratio": self.market_context.spread_ratio,
                "market_depth": self.market_context.market_depth,
                "predictability_score": self.market_context.predictability_score,
                "rsi_14": self.market_context.rsi_14,
                "bollinger_position": self.market_context.bollinger_position,
            },
            "trading_phase": current_phase.value,
            "optimal_strategy": optimal_strategy.value,
            "btc_statistics": self.btc_stats.copy(),
            "trend_analysis": self.trend_analysis.copy(),
            "large_order_queue": len(self.large_order_queue),
            "configuration": {
                "min_order_size": self.btc_config.min_order_size,
                "max_order_size": self.btc_config.max_order_size,
                "large_order_threshold": self.btc_config.large_order_threshold,
                "trend_profit_target": self.btc_config.trend_profit_target,
                "max_spread_ratio": self.btc_config.max_spread_ratio,
            },
        }

    def get_btc_performance_report(self) -> Dict[str, any]:
        """BTCパフォーマンスレポート取得"""
        total_trades = self.btc_stats["total_btc_trades"]
        win_rate = (
            (self.btc_stats["profitable_btc_trades"] / total_trades)
            if total_trades > 0
            else 0
        )

        return {
            "trading_pair": "BTC/JPY",
            "performance_summary": {
                "total_trades": total_trades,
                "profitable_trades": self.btc_stats["profitable_btc_trades"],
                "win_rate": win_rate,
                "total_profit": self.btc_stats["btc_profit"],
                "total_volume": self.btc_stats["btc_volume"],
                "avg_holding_time": self.btc_stats["avg_holding_time"],
                "max_drawdown": self.btc_stats["max_drawdown"],
            },
            "strategy_breakdown": {
                "trend_following_trades": self.btc_stats["trend_following_trades"],
                "mean_reversion_trades": self.btc_stats["mean_reversion_trades"],
                "breakout_trades": self.btc_stats["breakout_trades"],
                "spread_capture_trades": self.btc_stats["spread_capture_trades"],
                "large_order_trades": self.btc_stats["large_order_trades"],
            },
            "stability_metrics": {
                "trend_accuracy": self.btc_stats["trend_accuracy"],
                "spread_efficiency": self.btc_stats["spread_efficiency"],
                "predictability_utilization": self.market_context.predictability_score,
            },
            "risk_metrics": {
                "position_size_utilization": sum(
                    abs(pos.amount) for pos in self.active_positions.values()
                )
                / self.btc_config.position_size_limit,
                "daily_loss_ratio": abs(min(0, self.btc_stats["btc_profit"]))
                / self.btc_config.daily_loss_limit,
                "large_order_impact": self.market_context.large_order_impact,
            },
        }

    def start_btc_monitoring(self) -> None:
        """BTC監視開始"""
        if (
            self.btc_monitoring_thread is not None
            and self.btc_monitoring_thread.is_alive()
        ):
            return

        self.btc_stop_monitoring = False
        self.btc_monitoring_thread = threading.Thread(target=self._btc_monitoring_loop)
        self.btc_monitoring_thread.daemon = True
        self.btc_monitoring_thread.start()

        logger.info("BTC/JPY stable strategy monitoring started")

    def stop_btc_monitoring(self) -> None:
        """BTC監視停止"""
        self.btc_stop_monitoring = True

        if self.btc_monitoring_thread is not None:
            self.btc_monitoring_thread.join(timeout=5)

        logger.info("BTC/JPY stable strategy monitoring stopped")

    def _btc_monitoring_loop(self) -> None:
        """BTC監視ループ"""
        while not self.btc_stop_monitoring:
            try:
                # 市場コンテキスト分析
                self.analyze_market_context()

                # 取引フェーズ判定
                current_phase = self.determine_trading_phase()

                # 最適戦略選択
                optimal_strategy = self.select_optimal_strategy(current_phase)

                # 戦略実行
                if optimal_strategy == BTCTradingStrategy.TREND_FOLLOWING:
                    self.execute_trend_following_strategy()
                elif optimal_strategy == BTCTradingStrategy.MEAN_REVERSION:
                    self.execute_mean_reversion_strategy()
                elif optimal_strategy == BTCTradingStrategy.BREAKOUT:
                    self.execute_breakout_strategy()
                elif optimal_strategy == BTCTradingStrategy.SPREAD_CAPTURE:
                    self.execute_spread_capture_strategy()

                # 大口注文キュー処理
                self._process_large_order_queue()

                # 60秒間隔でチェック
                time.sleep(60)

            except Exception as e:
                logger.error(f"Error in BTC monitoring loop: {e}")
                time.sleep(60)

    def _process_large_order_queue(self) -> None:
        """大口注文キュー処理"""
        try:
            if not self.large_order_queue:
                return

            for order_info in self.large_order_queue[:]:
                success, message = self.execute_large_order(
                    order_info["side"], order_info["amount"], order_info["target_price"]
                )

                if success:
                    self.large_order_queue.remove(order_info)
                    logger.info(f"Large order from queue executed: {order_info}")

        except Exception as e:
            logger.error(f"Failed to process large order queue: {e}")

    def __del__(self):
        """デストラクタ"""
        self.stop_btc_monitoring()
        super().__del__()
