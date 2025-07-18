"""
Bitbank XRP/JPY特化戦略
最高流動性（37%シェア）活用・高ボラティリティ対応・頻繁売買最適化
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..execution.bitbank_fee_guard import BitbankFeeGuard
from ..execution.bitbank_fee_optimizer import BitbankFeeOptimizer
from ..execution.bitbank_order_manager import BitbankOrderManager
from .bitbank_enhanced_position_manager import BitbankEnhancedPositionManager

logger = logging.getLogger(__name__)


class XRPTradingPhase(Enum):
    """XRP取引フェーズ"""

    VOLATILITY_EXPANSION = "volatility_expansion"  # ボラティリティ拡大期
    CONSOLIDATION = "consolidation"  # 保合い期
    BREAKOUT = "breakout"  # ブレイクアウト期
    REVERSAL = "reversal"  # リバーサル期
    HIGH_LIQUIDITY = "high_liquidity"  # 高流動性期
    LOW_LIQUIDITY = "low_liquidity"  # 低流動性期


class XRPTradingStrategy(Enum):
    """XRP取引戦略"""

    SCALPING = "scalping"  # スキャルピング
    MOMENTUM = "momentum"  # モメンタム
    RANGE_TRADING = "range_trading"  # レンジ取引
    LIQUIDITY_PROVISIONING = "liquidity_provisioning"  # 流動性提供
    VOLATILITY_HARVESTING = "volatility_harvesting"  # ボラティリティ収穫


@dataclass
class XRPMarketContext:
    """XRP市場コンテキスト"""

    symbol: str = "XRP/JPY"
    current_price: float = 0.0
    bid_ask_spread: float = 0.0
    volume_24h: float = 0.0
    volatility: float = 0.0
    liquidity_score: float = 0.0
    market_share: float = 0.37  # 37%シェア

    # 技術指標
    rsi_14: float = 0.0
    macd_signal: float = 0.0
    bollinger_position: float = 0.0

    # 流動性指標
    order_book_depth: float = 0.0
    order_imbalance: float = 0.0
    market_impact: float = 0.0

    # ボラティリティ指標
    intraday_volatility: float = 0.0
    volatility_regime: str = "normal"
    volatility_trend: str = "stable"


@dataclass
class XRPTradingConfig:
    """XRP取引設定"""

    min_order_size: float = 1.0  # 最小注文サイズ
    max_order_size: float = 10000.0  # 最大注文サイズ
    max_position_size: float = 50000.0  # 最大ポジションサイズ

    # スキャルピング設定
    scalping_profit_target: float = 0.0015  # 0.15%利益目標
    scalping_stop_loss: float = 0.0010  # 0.10%ストップロス
    scalping_max_holding_time: int = 300  # 5分最大保有

    # モメンタム設定
    momentum_threshold: float = 0.003  # 0.3%モメンタム閾値
    momentum_profit_target: float = 0.005  # 0.5%利益目標
    momentum_stop_loss: float = 0.002  # 0.2%ストップロス

    # レンジ取引設定
    range_detection_period: int = 20  # 20期間でレンジ検出
    range_profit_target: float = 0.002  # 0.2%利益目標
    range_boundary_buffer: float = 0.0005  # 0.05%境界バッファ

    # 流動性提供設定
    liquidity_spread_offset: float = 0.0001  # 0.01%スプレッドオフセット
    liquidity_refresh_interval: int = 30  # 30秒更新間隔
    liquidity_max_inventory: float = 20000.0  # 最大在庫

    # リスク管理
    daily_loss_limit: float = 0.01  # 1%日次損失制限
    position_concentration_limit: float = 0.7  # 70%ポジション集中制限
    volatility_adjustment_factor: float = 1.5  # ボラティリティ調整係数


class BitbankXRPJPYStrategy(BitbankEnhancedPositionManager):
    """
    Bitbank XRP/JPY特化戦略

    最高流動性（37%シェア）活用・高ボラティリティ対応・頻繁売買最適化
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

        # XRP特化設定
        xrp_config = self.config.get("bitbank_xrp_jpy", {})
        self.xrp_config = XRPTradingConfig(
            min_order_size=xrp_config.get("min_order_size", 1.0),
            max_order_size=xrp_config.get("max_order_size", 10000.0),
            max_position_size=xrp_config.get("max_position_size", 50000.0),
            scalping_profit_target=xrp_config.get("scalping_profit_target", 0.0015),
            scalping_stop_loss=xrp_config.get("scalping_stop_loss", 0.0010),
            scalping_max_holding_time=xrp_config.get("scalping_max_holding_time", 300),
            momentum_threshold=xrp_config.get("momentum_threshold", 0.003),
            momentum_profit_target=xrp_config.get("momentum_profit_target", 0.005),
            momentum_stop_loss=xrp_config.get("momentum_stop_loss", 0.002),
            range_detection_period=xrp_config.get("range_detection_period", 20),
            range_profit_target=xrp_config.get("range_profit_target", 0.002),
            range_boundary_buffer=xrp_config.get("range_boundary_buffer", 0.0005),
            liquidity_spread_offset=xrp_config.get("liquidity_spread_offset", 0.0001),
            liquidity_refresh_interval=xrp_config.get("liquidity_refresh_interval", 30),
            liquidity_max_inventory=xrp_config.get("liquidity_max_inventory", 20000.0),
            daily_loss_limit=xrp_config.get("daily_loss_limit", 0.01),
            position_concentration_limit=xrp_config.get(
                "position_concentration_limit", 0.7
            ),
            volatility_adjustment_factor=xrp_config.get(
                "volatility_adjustment_factor", 1.5
            ),
        )

        # 市場コンテキスト
        self.market_context = XRPMarketContext()

        # 取引統計
        self.xrp_stats = {
            "total_xrp_trades": 0,
            "profitable_xrp_trades": 0,
            "xrp_profit": 0.0,
            "xrp_volume": 0.0,
            "scalping_trades": 0,
            "momentum_trades": 0,
            "range_trades": 0,
            "liquidity_trades": 0,
            "avg_holding_time": 0.0,
            "max_intraday_drawdown": 0.0,
            "liquidity_utilization": 0.0,
            "volatility_capture": 0.0,
        }

        # 価格履歴（技術指標計算用）
        self.price_history: List[float] = []
        self.volume_history: List[float] = []
        self.spread_history: List[float] = []
        self.max_history_length = 100

        # 流動性プール管理
        self.liquidity_orders: Dict[str, Dict] = {}
        self.inventory_management = {
            "xrp_inventory": 0.0,
            "jpy_inventory": 0.0,
            "target_ratio": 0.5,
            "rebalance_threshold": 0.1,
        }

        # 監視スレッド
        self.xrp_monitoring_thread = None
        self.xrp_stop_monitoring = False

        logger.info("BitbankXRPJPYStrategy initialized")
        logger.info(f"XRP/JPY market share: {self.market_context.market_share:.1%}")
        logger.info(
            f"Scalping profit target: {self.xrp_config.scalping_profit_target:.2%}"
        )
        logger.info(
            f"Maximum position size: {self.xrp_config.max_position_size:,.0f} XRP"
        )

    def analyze_market_context(self) -> XRPMarketContext:
        """市場コンテキスト分析"""
        try:
            # 市場データ取得
            ticker = self.bitbank_client.fetch_ticker("XRP/JPY")
            orderbook = self.bitbank_client.fetch_order_book("XRP/JPY")

            # 基本指標更新
            self.market_context.current_price = ticker["last"]
            self.market_context.bid_ask_spread = ticker["ask"] - ticker["bid"]
            self.market_context.volume_24h = ticker["quoteVolume"]

            # 価格履歴更新
            self.price_history.append(self.market_context.current_price)
            self.volume_history.append(self.market_context.volume_24h)
            self.spread_history.append(self.market_context.bid_ask_spread)

            # 履歴長制限
            if len(self.price_history) > self.max_history_length:
                self.price_history.pop(0)
                self.volume_history.pop(0)
                self.spread_history.pop(0)

            # 技術指標計算
            if len(self.price_history) >= 14:
                self.market_context.rsi_14 = self._calculate_rsi(self.price_history, 14)

            if len(self.price_history) >= 20:
                self.market_context.bollinger_position = (
                    self._calculate_bollinger_position(self.price_history, 20)
                )

            # ボラティリティ計算
            if len(self.price_history) >= 20:
                returns = np.diff(np.log(self.price_history[-20:]))
                self.market_context.volatility = np.std(returns) * np.sqrt(
                    24 * 60
                )  # 日次ボラティリティ
                self.market_context.intraday_volatility = np.std(returns) * np.sqrt(
                    60
                )  # 時間ボラティリティ

            # 流動性スコア計算
            self.market_context.liquidity_score = self._calculate_liquidity_score(
                orderbook
            )

            # 注文不均衡計算
            self.market_context.order_imbalance = self._calculate_order_imbalance(
                orderbook
            )

            # 市場インパクト推定
            self.market_context.market_impact = self._estimate_market_impact(orderbook)

            # ボラティリティ体制判定
            self.market_context.volatility_regime = self._determine_volatility_regime()

            logger.debug(
                f"Market context updated: "
                f"price={self.market_context.current_price:.3f}, "
                f"volatility={self.market_context.volatility:.4f}, "
                f"liquidity_score={self.market_context.liquidity_score:.3f}"
            )

            return self.market_context

        except Exception as e:
            logger.error(f"Failed to analyze market context: {e}")
            return self.market_context

    def determine_trading_phase(self) -> XRPTradingPhase:
        """取引フェーズ判定"""
        try:
            # ボラティリティベース判定
            if self.market_context.volatility > 0.05:  # 5%以上
                if self.market_context.volatility_trend == "increasing":
                    return XRPTradingPhase.VOLATILITY_EXPANSION
                else:
                    return XRPTradingPhase.BREAKOUT
            elif self.market_context.volatility < 0.01:  # 1%未満
                return XRPTradingPhase.CONSOLIDATION

            # 流動性ベース判定
            if self.market_context.liquidity_score > 0.8:
                return XRPTradingPhase.HIGH_LIQUIDITY
            elif self.market_context.liquidity_score < 0.3:
                return XRPTradingPhase.LOW_LIQUIDITY

            # テクニカル指標ベース判定
            if abs(self.market_context.order_imbalance) > 0.3:
                return XRPTradingPhase.BREAKOUT

            if (
                self.market_context.bollinger_position > 0.8
                or self.market_context.bollinger_position < 0.2
            ):
                return XRPTradingPhase.REVERSAL

            return XRPTradingPhase.CONSOLIDATION

        except Exception as e:
            logger.error(f"Failed to determine trading phase: {e}")
            return XRPTradingPhase.CONSOLIDATION

    def select_optimal_strategy(self, phase: XRPTradingPhase) -> XRPTradingStrategy:
        """最適戦略選択"""
        strategy_map = {
            XRPTradingPhase.VOLATILITY_EXPANSION: (
                XRPTradingStrategy.VOLATILITY_HARVESTING
            ),
            XRPTradingPhase.CONSOLIDATION: XRPTradingStrategy.RANGE_TRADING,
            XRPTradingPhase.BREAKOUT: XRPTradingStrategy.MOMENTUM,
            XRPTradingPhase.REVERSAL: XRPTradingStrategy.SCALPING,
            XRPTradingPhase.HIGH_LIQUIDITY: XRPTradingStrategy.LIQUIDITY_PROVISIONING,
            XRPTradingPhase.LOW_LIQUIDITY: XRPTradingStrategy.SCALPING,
        }

        optimal_strategy = strategy_map.get(phase, XRPTradingStrategy.SCALPING)

        # 追加条件チェック
        if self.market_context.bid_ask_spread < 0.001:  # 0.1%未満のスプレッド
            optimal_strategy = XRPTradingStrategy.SCALPING

        if self.market_context.volume_24h > 1000000:  # 高出来高
            if optimal_strategy == XRPTradingStrategy.RANGE_TRADING:
                optimal_strategy = XRPTradingStrategy.MOMENTUM

        logger.info(
            f"Selected strategy: {optimal_strategy.value} for phase: {phase.value}"
        )
        return optimal_strategy

    def execute_scalping_strategy(self) -> Tuple[bool, str]:
        """スキャルピング戦略実行"""
        try:
            # 市場状況確認
            if self.market_context.bid_ask_spread > 0.002:  # 0.2%以上のスプレッド
                return False, "Spread too wide for scalping"

            # 注文サイズ決定
            order_size = min(
                self.xrp_config.min_order_size * 10,  # 基本サイズ
                self.xrp_config.max_order_size * 0.1,  # 最大サイズの10%
                self.market_context.volume_24h * 0.001,  # 24時間出来高の0.1%
            )

            # 方向性判定
            if self.market_context.rsi_14 < 30:  # 売られすぎ
                side = "buy"
                target_price = self.market_context.current_price * (
                    1 + self.xrp_config.scalping_profit_target
                )
            elif self.market_context.rsi_14 > 70:  # 買われすぎ
                side = "sell"
                target_price = self.market_context.current_price * (
                    1 - self.xrp_config.scalping_profit_target
                )
            else:
                # 中立時はスプレッドの中間を狙う
                if self.market_context.order_imbalance > 0:
                    side = "sell"
                    target_price = self.market_context.current_price * (
                        1 + self.xrp_config.scalping_profit_target
                    )
                else:
                    side = "buy"
                    target_price = self.market_context.current_price * (
                        1 + self.xrp_config.scalping_profit_target
                    )

            # ポジション開設
            success, message, position_id = self.open_position(
                "XRP/JPY", side, order_size, target_price, reason="scalping_strategy"
            )

            if success:
                self.xrp_stats["scalping_trades"] += 1

                # 短期決済タイマー設定
                self._schedule_scalping_exit(position_id)

                logger.info(
                    f"Scalping position opened: {position_id} - {side} "
                    f"{order_size} @ {target_price}"
                )

            return success, message

        except Exception as e:
            logger.error(f"Scalping strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_momentum_strategy(self) -> Tuple[bool, str]:
        """モメンタム戦略実行"""
        try:
            # モメンタム検出
            if len(self.price_history) < 5:
                return False, "Insufficient price history"

            # 短期価格変動率計算
            recent_returns = (
                np.diff(self.price_history[-5:]) / self.price_history[-6:-1]
            )
            momentum_score = np.mean(recent_returns)

            # モメンタム閾値チェック
            if abs(momentum_score) < self.xrp_config.momentum_threshold:
                return False, "Insufficient momentum"

            # 注文サイズ決定（ボラティリティ調整）
            base_size = self.xrp_config.min_order_size * 20
            volatility_adjustment = min(
                self.xrp_config.volatility_adjustment_factor,
                1.0 / max(self.market_context.volatility, 0.01),
            )
            order_size = base_size * volatility_adjustment

            # 方向性決定
            if momentum_score > 0:
                side = "buy"
                target_price = self.market_context.current_price * (
                    1 + self.xrp_config.momentum_profit_target
                )
            else:
                side = "sell"
                target_price = self.market_context.current_price * (
                    1 - self.xrp_config.momentum_profit_target
                )

            # ポジション開設
            success, message, position_id = self.open_position(
                "XRP/JPY", side, order_size, target_price, reason="momentum_strategy"
            )

            if success:
                self.xrp_stats["momentum_trades"] += 1
                logger.info(
                    f"Momentum position opened: {position_id} - "
                    f"momentum_score={momentum_score:.4f}"
                )

            return success, message

        except Exception as e:
            logger.error(f"Momentum strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_range_trading_strategy(self) -> Tuple[bool, str]:
        """レンジ取引戦略実行"""
        try:
            # レンジ検出
            if len(self.price_history) < self.xrp_config.range_detection_period:
                return False, "Insufficient price history for range detection"

            recent_prices = self.price_history[
                -self.xrp_config.range_detection_period :
            ]
            range_high = max(recent_prices)
            range_low = min(recent_prices)
            range_size = range_high - range_low

            # レンジ有効性チェック
            if range_size < self.market_context.current_price * 0.005:  # 0.5%未満
                return False, "Range too narrow"

            # 現在価格の位置判定
            current_position = (
                self.market_context.current_price - range_low
            ) / range_size

            # 取引判定
            if current_position < 0.2:  # 下位20%
                side = "buy"
                target_price = range_high * (1 - self.xrp_config.range_boundary_buffer)
            elif current_position > 0.8:  # 上位20%
                side = "sell"
                target_price = range_low * (1 + self.xrp_config.range_boundary_buffer)
            else:
                return False, "Price in middle of range"

            # 注文サイズ決定
            order_size = min(
                self.xrp_config.min_order_size * 15,
                self.xrp_config.max_order_size * 0.2,
            )

            # ポジション開設
            success, message, position_id = self.open_position(
                "XRP/JPY",
                side,
                order_size,
                target_price,
                reason="range_trading_strategy",
            )

            if success:
                self.xrp_stats["range_trades"] += 1
                logger.info(
                    f"Range trading position opened: {position_id} - "
                    f"range_position={current_position:.2f}"
                )

            return success, message

        except Exception as e:
            logger.error(f"Range trading strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_liquidity_provisioning_strategy(self) -> Tuple[bool, str]:
        """流動性提供戦略実行"""
        try:
            # 在庫管理チェック
            if (
                abs(self.inventory_management["xrp_inventory"])
                > self.xrp_config.liquidity_max_inventory
            ):
                return False, "Inventory limit exceeded"

            # 両建て注文作成
            bid_price = self.market_context.current_price * (
                1 - self.xrp_config.liquidity_spread_offset
            )
            ask_price = self.market_context.current_price * (
                1 + self.xrp_config.liquidity_spread_offset
            )

            order_size = min(
                self.xrp_config.min_order_size * 5, self.xrp_config.max_order_size * 0.1
            )

            # 買い注文
            buy_success, buy_message, buy_position_id = self.open_position(
                "XRP/JPY",
                "buy",
                order_size,
                bid_price,
                reason="liquidity_provisioning_buy",
            )

            # 売り注文
            sell_success, sell_message, sell_position_id = self.open_position(
                "XRP/JPY",
                "sell",
                order_size,
                ask_price,
                reason="liquidity_provisioning_sell",
            )

            if buy_success or sell_success:
                self.xrp_stats["liquidity_trades"] += 1

                # 注文ペア管理
                if buy_success and sell_success:
                    self.liquidity_orders[buy_position_id] = {
                        "paired_order": sell_position_id,
                        "order_type": "buy",
                        "created_at": datetime.now(),
                    }
                    self.liquidity_orders[sell_position_id] = {
                        "paired_order": buy_position_id,
                        "order_type": "sell",
                        "created_at": datetime.now(),
                    }

                logger.info(
                    f"Liquidity provisioning orders: buy={buy_success}, "
                    f"sell={sell_success}"
                )

            return (
                buy_success or sell_success,
                f"Buy: {buy_message}, Sell: {sell_message}",
            )

        except Exception as e:
            logger.error(f"Liquidity provisioning strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def execute_volatility_harvesting_strategy(self) -> Tuple[bool, str]:
        """ボラティリティ収穫戦略実行"""
        try:
            # 高ボラティリティ確認
            if self.market_context.volatility < 0.03:  # 3%未満
                return False, "Volatility too low for harvesting"

            # 注文サイズ決定（ボラティリティ逆調整）
            volatility_factor = min(2.0, self.market_context.volatility * 50)
            order_size = self.xrp_config.min_order_size * volatility_factor

            # 複数ポジション戦略
            positions_opened = 0
            messages = []

            # 方向性を分散
            directions = [
                ("buy", 0.003),  # 0.3%上昇狙い
                ("sell", 0.003),  # 0.3%下落狙い
                ("buy", 0.005),  # 0.5%上昇狙い
                ("sell", 0.005),  # 0.5%下落狙い
            ]

            for side, profit_target in directions:
                if side == "buy":
                    target_price = self.market_context.current_price * (
                        1 + profit_target
                    )
                else:
                    target_price = self.market_context.current_price * (
                        1 - profit_target
                    )

                success, message, position_id = self.open_position(
                    "XRP/JPY",
                    side,
                    order_size / 4,
                    target_price,
                    reason="volatility_harvesting",
                )

                if success:
                    positions_opened += 1
                    messages.append(f"{side}: {message}")

                    # 短期決済スケジュール
                    self._schedule_volatility_exit(position_id, profit_target)

            if positions_opened > 0:
                logger.info(
                    f"Volatility harvesting: {positions_opened} positions opened"
                )
                return (
                    True,
                    f"Opened {positions_opened} positions: {', '.join(messages)}",
                )
            else:
                return False, "No positions opened"

        except Exception as e:
            logger.error(f"Volatility harvesting strategy execution failed: {e}")
            return False, f"Exception: {e}"

    def _schedule_scalping_exit(self, position_id: str) -> None:
        """スキャルピング決済スケジュール"""

        def exit_timer():
            time.sleep(self.xrp_config.scalping_max_holding_time)
            if position_id in self.active_positions:
                self.close_position(position_id, "scalping_timeout", force=True)

        timer_thread = threading.Thread(target=exit_timer)
        timer_thread.daemon = True
        timer_thread.start()

    def _schedule_volatility_exit(self, position_id: str, profit_target: float) -> None:
        """ボラティリティ決済スケジュール"""

        def exit_timer():
            # 利益目標達成監視
            for _ in range(30):  # 30秒間監視
                if position_id not in self.active_positions:
                    break

                position = self.active_positions[position_id]
                current_price = self._get_current_price("XRP/JPY")

                if current_price:
                    unrealized_pnl_ratio = position.calculate_unrealized_pnl(
                        current_price
                    ) / (position.amount * position.entry_price)

                    if unrealized_pnl_ratio >= profit_target * 0.8:  # 80%達成で決済
                        self.close_position(
                            position_id, "volatility_target_reached", force=True
                        )
                        break

                time.sleep(1)

            # タイムアウト決済
            if position_id in self.active_positions:
                self.close_position(position_id, "volatility_timeout", force=True)

        timer_thread = threading.Thread(target=exit_timer)
        timer_thread.daemon = True
        timer_thread.start()

    def _calculate_rsi(self, prices: List[float], period: int) -> float:
        """RSI計算"""
        if len(prices) < period + 1:
            return 50.0

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

    def _calculate_bollinger_position(self, prices: List[float], period: int) -> float:
        """ボリンジャーバンド内位置計算"""
        if len(prices) < period:
            return 0.5

        recent_prices = prices[-period:]
        mean_price = np.mean(recent_prices)
        std_price = np.std(recent_prices)

        current_price = prices[-1]
        upper_band = mean_price + (2 * std_price)
        lower_band = mean_price - (2 * std_price)

        if upper_band == lower_band:
            return 0.5

        position = (current_price - lower_band) / (upper_band - lower_band)
        return max(0.0, min(1.0, position))

    def _calculate_liquidity_score(self, orderbook: Dict) -> float:
        """流動性スコア計算"""
        try:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return 0.0

            # 上位5レベルの流動性
            bid_depth = sum(bid[1] for bid in bids[:5])
            ask_depth = sum(ask[1] for ask in asks[:5])

            # スプレッド
            spread = asks[0][0] - bids[0][0]
            spread_ratio = spread / bids[0][0]

            # 流動性スコア計算
            depth_score = min(1.0, (bid_depth + ask_depth) / 100000)  # 10万XRP基準
            spread_score = max(0.0, 1.0 - spread_ratio * 1000)  # 0.1%基準

            return (depth_score + spread_score) / 2

        except Exception as e:
            logger.error(f"Failed to calculate liquidity score: {e}")
            return 0.5

    def _calculate_order_imbalance(self, orderbook: Dict) -> float:
        """注文不均衡計算"""
        try:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return 0.0

            bid_volume = sum(bid[1] for bid in bids[:10])
            ask_volume = sum(ask[1] for ask in asks[:10])

            total_volume = bid_volume + ask_volume
            if total_volume == 0:
                return 0.0

            # +1: 買い圧力, -1: 売り圧力
            imbalance = (bid_volume - ask_volume) / total_volume
            return imbalance

        except Exception as e:
            logger.error(f"Failed to calculate order imbalance: {e}")
            return 0.0

    def _estimate_market_impact(self, orderbook: Dict) -> float:
        """市場インパクト推定"""
        try:
            bids = orderbook.get("bids", [])
            asks = orderbook.get("asks", [])

            if not bids or not asks:
                return 0.0

            # 1000XRP注文のインパクト推定
            test_amount = 1000.0

            # 買い注文インパクト
            buy_impact = 0.0
            remaining_amount = test_amount
            for ask in asks:
                if remaining_amount <= 0:
                    break

                trade_amount = min(remaining_amount, ask[1])
                buy_impact += trade_amount * ask[0]
                remaining_amount -= trade_amount

            # 売り注文インパクト
            sell_impact = 0.0
            remaining_amount = test_amount
            for bid in bids:
                if remaining_amount <= 0:
                    break

                trade_amount = min(remaining_amount, bid[1])
                sell_impact += trade_amount * bid[0]
                remaining_amount -= trade_amount

            # 平均インパクト
            mid_price = (bids[0][0] + asks[0][0]) / 2
            avg_impact = abs(buy_impact - sell_impact) / (2 * test_amount * mid_price)

            return avg_impact

        except Exception as e:
            logger.error(f"Failed to estimate market impact: {e}")
            return 0.0

    def _determine_volatility_regime(self) -> str:
        """ボラティリティ体制判定"""
        if self.market_context.volatility > 0.05:
            return "high"
        elif self.market_context.volatility < 0.01:
            return "low"
        else:
            return "normal"

    def get_xrp_strategy_status(self) -> Dict[str, any]:
        """XRP戦略状況取得"""
        current_phase = self.determine_trading_phase()
        optimal_strategy = self.select_optimal_strategy(current_phase)

        return {
            "symbol": "XRP/JPY",
            "market_context": {
                "current_price": self.market_context.current_price,
                "volatility": self.market_context.volatility,
                "liquidity_score": self.market_context.liquidity_score,
                "bid_ask_spread": self.market_context.bid_ask_spread,
                "order_imbalance": self.market_context.order_imbalance,
                "market_impact": self.market_context.market_impact,
                "volatility_regime": self.market_context.volatility_regime,
            },
            "trading_phase": current_phase.value,
            "optimal_strategy": optimal_strategy.value,
            "xrp_statistics": self.xrp_stats.copy(),
            "inventory_management": self.inventory_management.copy(),
            "liquidity_orders": len(self.liquidity_orders),
            "configuration": {
                "min_order_size": self.xrp_config.min_order_size,
                "max_order_size": self.xrp_config.max_order_size,
                "scalping_profit_target": self.xrp_config.scalping_profit_target,
                "momentum_threshold": self.xrp_config.momentum_threshold,
                "liquidity_spread_offset": self.xrp_config.liquidity_spread_offset,
            },
        }

    def get_xrp_performance_report(self) -> Dict[str, any]:
        """XRPパフォーマンスレポート取得"""
        total_trades = self.xrp_stats["total_xrp_trades"]
        win_rate = (
            (self.xrp_stats["profitable_xrp_trades"] / total_trades)
            if total_trades > 0
            else 0
        )

        return {
            "trading_pair": "XRP/JPY",
            "performance_summary": {
                "total_trades": total_trades,
                "profitable_trades": self.xrp_stats["profitable_xrp_trades"],
                "win_rate": win_rate,
                "total_profit": self.xrp_stats["xrp_profit"],
                "total_volume": self.xrp_stats["xrp_volume"],
                "avg_holding_time": self.xrp_stats["avg_holding_time"],
                "max_intraday_drawdown": self.xrp_stats["max_intraday_drawdown"],
            },
            "strategy_breakdown": {
                "scalping_trades": self.xrp_stats["scalping_trades"],
                "momentum_trades": self.xrp_stats["momentum_trades"],
                "range_trades": self.xrp_stats["range_trades"],
                "liquidity_trades": self.xrp_stats["liquidity_trades"],
            },
            "market_utilization": {
                "liquidity_utilization": self.xrp_stats["liquidity_utilization"],
                "volatility_capture": self.xrp_stats["volatility_capture"],
                "market_share_utilized": self.market_context.market_share,
            },
            "risk_metrics": {
                "position_concentration": sum(
                    abs(pos.amount) for pos in self.active_positions.values()
                )
                / self.xrp_config.max_position_size,
                "inventory_risk": abs(self.inventory_management["xrp_inventory"])
                / self.xrp_config.liquidity_max_inventory,
                "daily_loss_ratio": abs(min(0, self.xrp_stats["xrp_profit"]))
                / self.xrp_config.daily_loss_limit,
            },
        }

    def start_xrp_monitoring(self) -> None:
        """XRP監視開始"""
        if (
            self.xrp_monitoring_thread is not None
            and self.xrp_monitoring_thread.is_alive()
        ):
            return

        self.xrp_stop_monitoring = False
        self.xrp_monitoring_thread = threading.Thread(target=self._xrp_monitoring_loop)
        self.xrp_monitoring_thread.daemon = True
        self.xrp_monitoring_thread.start()

        logger.info("XRP/JPY specialized monitoring started")

    def stop_xrp_monitoring(self) -> None:
        """XRP監視停止"""
        self.xrp_stop_monitoring = True

        if self.xrp_monitoring_thread is not None:
            self.xrp_monitoring_thread.join(timeout=5)

        logger.info("XRP/JPY specialized monitoring stopped")

    def _xrp_monitoring_loop(self) -> None:
        """XRP監視ループ"""
        while not self.xrp_stop_monitoring:
            try:
                # 市場コンテキスト分析
                self.analyze_market_context()

                # 取引フェーズ判定
                current_phase = self.determine_trading_phase()

                # 最適戦略選択
                optimal_strategy = self.select_optimal_strategy(current_phase)

                # 戦略実行
                if optimal_strategy == XRPTradingStrategy.SCALPING:
                    self.execute_scalping_strategy()
                elif optimal_strategy == XRPTradingStrategy.MOMENTUM:
                    self.execute_momentum_strategy()
                elif optimal_strategy == XRPTradingStrategy.RANGE_TRADING:
                    self.execute_range_trading_strategy()
                elif optimal_strategy == XRPTradingStrategy.LIQUIDITY_PROVISIONING:
                    self.execute_liquidity_provisioning_strategy()
                elif optimal_strategy == XRPTradingStrategy.VOLATILITY_HARVESTING:
                    self.execute_volatility_harvesting_strategy()

                # 在庫管理
                self._manage_inventory()

                # 流動性注文管理
                self._manage_liquidity_orders()

                # 30秒間隔でチェック
                time.sleep(30)

            except Exception as e:
                logger.error(f"Error in XRP monitoring loop: {e}")
                time.sleep(30)

    def _manage_inventory(self) -> None:
        """在庫管理"""
        try:
            # 在庫不均衡チェック
            total_inventory = abs(self.inventory_management["xrp_inventory"])

            if total_inventory > self.xrp_config.liquidity_max_inventory * 0.8:
                # 在庫削減必要
                excess_inventory = total_inventory - (
                    self.xrp_config.liquidity_max_inventory * 0.5
                )

                if self.inventory_management["xrp_inventory"] > 0:
                    # XRP過多 -> 売却
                    self.open_position(
                        "XRP/JPY",
                        "sell",
                        excess_inventory,
                        self.market_context.current_price * 0.999,
                        reason="inventory_rebalancing",
                    )
                else:
                    # XRP不足 -> 購入
                    self.open_position(
                        "XRP/JPY",
                        "buy",
                        excess_inventory,
                        self.market_context.current_price * 1.001,
                        reason="inventory_rebalancing",
                    )

        except Exception as e:
            logger.error(f"Failed to manage inventory: {e}")

    def _manage_liquidity_orders(self) -> None:
        """流動性注文管理"""
        try:
            # 期限切れ注文削除
            expired_orders = []
            for order_id, order_info in self.liquidity_orders.items():
                if datetime.now() - order_info["created_at"] > timedelta(minutes=5):
                    expired_orders.append(order_id)

            for order_id in expired_orders:
                if order_id in self.active_positions:
                    self.close_position(order_id, "liquidity_order_expired")
                self.liquidity_orders.pop(order_id, None)

            # 流動性注文更新
            if len(self.liquidity_orders) < 4:  # 最小流動性維持
                self.execute_liquidity_provisioning_strategy()

        except Exception as e:
            logger.error(f"Failed to manage liquidity orders: {e}")

    def __del__(self):
        """デストラクタ"""
        self.stop_xrp_monitoring()
        super().__del__()
