"""
Bitbank日次取引戦略
日次0.04%金利回避・日をまたがない戦略・自動決済期限管理
"""

import logging
import threading
import time as time_module
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pytz

from ..execution.bitbank_fee_guard import BitbankFeeGuard
from ..execution.bitbank_fee_optimizer import BitbankFeeOptimizer, OrderType
from ..execution.bitbank_order_manager import BitbankOrderManager

logger = logging.getLogger(__name__)


class PositionStatus(Enum):
    """ポジション状態"""

    OPEN = "open"
    PENDING_CLOSE = "pending_close"
    CLOSED = "closed"
    EXPIRED = "expired"
    FORCE_CLOSED = "force_closed"


class DayTradingPhase(Enum):
    """デイトレード フェーズ"""

    PRE_MARKET = "pre_market"  # 市場前（8:00-9:00）
    EARLY_TRADING = "early_trading"  # 早期取引（9:00-12:00）
    MIDDAY_TRADING = "midday_trading"  # 中間取引（12:00-15:00）
    LATE_TRADING = "late_trading"  # 後期取引（15:00-18:00）
    CLOSING_PHASE = "closing_phase"  # 決済フェーズ（18:00-23:00）
    MARKET_CLOSED = "market_closed"  # 市場終了（23:00-8:00）


@dataclass
class Position:
    """ポジション情報"""

    position_id: str
    symbol: str
    side: str  # buy/sell
    amount: float
    entry_price: float
    entry_time: datetime
    status: PositionStatus = PositionStatus.OPEN
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    expected_exit_time: Optional[datetime] = None
    profit_loss: float = 0.0
    fees_paid: float = 0.0
    order_ids: List[str] = field(default_factory=list)

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """未実現損益計算"""
        if self.side == "buy":
            return (current_price - self.entry_price) * self.amount
        else:
            return (self.entry_price - current_price) * self.amount

    def get_holding_time(self) -> timedelta:
        """保有時間取得"""
        end_time = self.exit_time if self.exit_time else datetime.now()
        return end_time - self.entry_time


@dataclass
class DayTradingConfig:
    """デイトレード設定"""

    timezone: str = "Asia/Tokyo"
    market_open_time: time = time(9, 0)  # 9:00
    market_close_time: time = time(23, 0)  # 23:00
    force_close_time: time = time(22, 30)  # 22:30 強制決済
    position_timeout_hours: int = 8  # ポジション最大保有時間
    max_positions: int = 5  # 最大同時ポジション数
    daily_interest_rate: float = 0.0004  # 0.04%
    min_profit_threshold: float = 0.001  # 0.1% 最小利益閾値
    max_loss_threshold: float = -0.02  # -2.0% 最大損失閾値


class BitbankDayTradingStrategy:
    """
    Bitbank日次取引戦略

    日次0.04%金利回避・日をまたがない戦略実装
    自動決済期限管理・ポジション管理統合
    """

    def __init__(
        self,
        bitbank_client,
        fee_optimizer: BitbankFeeOptimizer,
        fee_guard: BitbankFeeGuard,
        order_manager: BitbankOrderManager,
        config: Optional[Dict] = None,
    ):

        self.bitbank_client = bitbank_client
        self.fee_optimizer = fee_optimizer
        self.fee_guard = fee_guard
        self.order_manager = order_manager
        self.config = config or {}

        # デイトレード設定
        day_trading_config = self.config.get("bitbank_day_trading", {})
        self.day_config = DayTradingConfig(
            timezone=day_trading_config.get("timezone", "Asia/Tokyo"),
            market_open_time=time(*day_trading_config.get("market_open_time", [9, 0])),
            market_close_time=time(
                *day_trading_config.get("market_close_time", [23, 0])
            ),
            force_close_time=time(
                *day_trading_config.get("force_close_time", [22, 30])
            ),
            position_timeout_hours=day_trading_config.get("position_timeout_hours", 8),
            max_positions=day_trading_config.get("max_positions", 5),
            daily_interest_rate=day_trading_config.get("daily_interest_rate", 0.0004),
            min_profit_threshold=day_trading_config.get("min_profit_threshold", 0.001),
            max_loss_threshold=day_trading_config.get("max_loss_threshold", -0.02),
        )

        # タイムゾーン設定
        self.timezone = pytz.timezone(self.day_config.timezone)

        # ポジション管理
        self.active_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.position_counter = 0

        # 統計情報
        self.daily_stats = {
            "total_trades": 0,
            "profitable_trades": 0,
            "total_profit": 0.0,
            "total_fees": 0.0,
            "max_drawdown": 0.0,
            "positions_force_closed": 0,
            "interest_avoided": 0.0,
        }

        # 監視スレッド
        self.monitoring_thread = None
        self.stop_monitoring = False

        logger.info("BitbankDayTradingStrategy initialized")
        logger.info(
            "Market hours: %s - %s",
            self.day_config.market_open_time,
            self.day_config.market_close_time,
        )
        logger.info(f"Force close time: {self.day_config.force_close_time}")
        logger.info(f"Daily interest rate: {self.day_config.daily_interest_rate:.4f}")

    def get_current_phase(self) -> DayTradingPhase:
        """現在の取引フェーズ取得"""
        now = datetime.now(self.timezone).time()

        if time(8, 0) <= now < time(9, 0):
            return DayTradingPhase.PRE_MARKET
        elif time(9, 0) <= now < time(12, 0):
            return DayTradingPhase.EARLY_TRADING
        elif time(12, 0) <= now < time(15, 0):
            return DayTradingPhase.MIDDAY_TRADING
        elif time(15, 0) <= now < time(18, 0):
            return DayTradingPhase.LATE_TRADING
        elif time(18, 0) <= now < time(23, 0):
            return DayTradingPhase.CLOSING_PHASE
        else:
            return DayTradingPhase.MARKET_CLOSED

    def is_market_open(self) -> bool:
        """市場開放時間判定"""
        now = datetime.now(self.timezone).time()
        return (
            self.day_config.market_open_time <= now <= self.day_config.market_close_time
        )

    def can_open_position(self) -> bool:
        """ポジション開設可能判定"""
        if not self.is_market_open():
            return False

        # 強制決済時間に近い場合は新規ポジション禁止
        now = datetime.now(self.timezone).time()
        if now >= self.day_config.force_close_time:
            return False

        # 最大ポジション数チェック
        if len(self.active_positions) >= self.day_config.max_positions:
            return False

        return True

    def open_position(
        self, symbol: str, side: str, amount: float, price: float, reason: str = ""
    ) -> Tuple[bool, str, Optional[str]]:
        """
        ポジション開設

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 価格
            reason: 開設理由

        Returns:
            (成功/失敗, メッセージ, ポジションID)
        """
        # 開設可能性チェック
        if not self.can_open_position():
            return False, "Cannot open position: market closed or limit reached", None

        # 最適注文タイプ計算
        optimal_type, fee_calc = self.fee_optimizer.calculate_optimal_order_type(
            symbol, side, amount, price
        )

        # 手数料リスク評価
        risk_assessment = self.fee_guard.evaluate_trade_risk(
            symbol,
            side,
            amount,
            price,
            expected_profit=amount * price * 0.005,  # 仮の予想利益 0.5%
            order_type=optimal_type,
        )

        # リスクが高い場合は拒否
        if risk_assessment.recommended_action.value in ["reject"]:
            return False, f"Risk too high: {risk_assessment.reasons}", None

        # ポジションID生成
        self.position_counter += 1
        position_id = f"pos_{symbol}_{self.position_counter}_{int(time_module.time())}"

        # 注文実行
        try:
            success, message, order_id = self.order_manager.submit_order(
                symbol=symbol,
                side=side,
                type="limit" if optimal_type == OrderType.MAKER else "market",
                amount=amount,
                price=price if optimal_type == OrderType.MAKER else None,
            )

            if not success:
                return False, f"Order failed: {message}", None

            # ポジション作成
            expected_exit = datetime.now(self.timezone) + timedelta(
                hours=self.day_config.position_timeout_hours
            )

            # 強制決済時間を超えないように調整
            force_close_datetime = datetime.combine(
                datetime.now(self.timezone).date(), self.day_config.force_close_time
            )
            force_close_datetime = self.timezone.localize(force_close_datetime)

            if expected_exit > force_close_datetime:
                expected_exit = force_close_datetime

            position = Position(
                position_id=position_id,
                symbol=symbol,
                side=side,
                amount=amount,
                entry_price=price,
                entry_time=datetime.now(self.timezone),
                expected_exit_time=expected_exit,
                order_ids=[order_id],
            )

            self.active_positions[position_id] = position

            # 統計更新
            self.daily_stats["total_trades"] += 1

            logger.info(
                f"Position opened: {position_id} - {symbol} {side} {amount} @ {price}"
            )
            logger.info(f"Expected exit: {expected_exit.strftime('%H:%M:%S')}")
            logger.info(f"Reason: {reason}")

            # 監視スレッド開始
            if self.monitoring_thread is None or not self.monitoring_thread.is_alive():
                self.start_monitoring()

            return True, f"Position opened: {position_id}", position_id

        except Exception as e:
            logger.error(f"Failed to open position: {e}")
            return False, f"Exception: {e}", None

    def close_position(
        self, position_id: str, reason: str = "manual", force: bool = False
    ) -> Tuple[bool, str]:
        """
        ポジション決済

        Args:
            position_id: ポジションID
            reason: 決済理由
            force: 強制決済フラグ

        Returns:
            (成功/失敗, メッセージ)
        """
        if position_id not in self.active_positions:
            return False, "Position not found"

        position = self.active_positions[position_id]

        if position.status != PositionStatus.OPEN:
            return False, f"Position not open: {position.status.value}"

        try:
            # 現在価格取得
            current_price = self._get_current_price(position.symbol)
            if current_price is None:
                return False, "Failed to get current price"

            # 反対売買注文
            close_side = "sell" if position.side == "buy" else "buy"

            # 最適注文タイプ計算
            optimal_type, fee_calc = self.fee_optimizer.calculate_optimal_order_type(
                position.symbol,
                close_side,
                position.amount,
                current_price,
                urgency_level=0.8 if force else 0.3,
            )

            # 注文実行
            success, message, order_id = self.order_manager.submit_order(
                symbol=position.symbol,
                side=close_side,
                type=(
                    "market"
                    if force
                    else ("limit" if optimal_type == OrderType.MAKER else "market")
                ),
                amount=position.amount,
                price=(
                    None
                    if force
                    else (current_price if optimal_type == OrderType.MAKER else None)
                ),
            )

            if not success:
                return False, f"Close order failed: {message}"

            # ポジション更新
            position.status = (
                PositionStatus.FORCE_CLOSED if force else PositionStatus.CLOSED
            )
            position.exit_price = current_price
            position.exit_time = datetime.now(self.timezone)
            position.profit_loss = position.calculate_unrealized_pnl(current_price)
            position.order_ids.append(order_id)

            # 手数料記録
            estimated_fee = abs(fee_calc.expected_fee)
            position.fees_paid += estimated_fee

            # アクティブポジションから削除、履歴に追加
            self.active_positions.pop(position_id)
            self.closed_positions.append(position)

            # 統計更新
            if position.profit_loss > 0:
                self.daily_stats["profitable_trades"] += 1

            self.daily_stats["total_profit"] += position.profit_loss
            self.daily_stats["total_fees"] += position.fees_paid

            if force:
                self.daily_stats["positions_force_closed"] += 1

            # 金利回避効果計算
            avoided_interest = (
                position.amount
                * position.entry_price
                * self.day_config.daily_interest_rate
            )
            self.daily_stats["interest_avoided"] += avoided_interest

            logger.info(f"Position closed: {position_id}")
            logger.info(
                f"P&L: {position.profit_loss:.6f}, Fees: {position.fees_paid:.6f}"
            )
            logger.info(f"Interest avoided: {avoided_interest:.6f}")
            logger.info(f"Reason: {reason}")

            # 手数料パフォーマンス記録
            self.fee_optimizer.track_fee_performance(
                position.symbol,
                close_side,
                position.amount,
                current_price,
                estimated_fee,
                optimal_type,
            )

            return True, f"Position closed: P&L={position.profit_loss:.6f}"

        except Exception as e:
            logger.error(f"Failed to close position {position_id}: {e}")
            return False, f"Exception: {e}"

    def close_all_positions(self, reason: str = "end_of_day") -> Dict[str, bool]:
        """
        全ポジション決済

        Args:
            reason: 決済理由

        Returns:
            ポジションID別成功/失敗
        """
        results = {}

        for position_id in list(self.active_positions.keys()):
            success, message = self.close_position(position_id, reason, force=True)
            results[position_id] = success

            if not success:
                logger.error(f"Failed to close position {position_id}: {message}")

        logger.info(f"Closed {len(results)} positions. Reason: {reason}")
        return results

    def check_position_timeouts(self) -> None:
        """ポジションタイムアウトチェック"""
        now = datetime.now(self.timezone)

        for position_id, position in list(self.active_positions.items()):
            # 期限切れチェック
            if position.expected_exit_time and now >= position.expected_exit_time:
                logger.warning(f"Position {position_id} timeout, force closing")
                self.close_position(position_id, "timeout", force=True)
                continue

            # 損失制限チェック
            current_price = self._get_current_price(position.symbol)
            if current_price:
                unrealized_pnl_ratio = position.calculate_unrealized_pnl(
                    current_price
                ) / (position.amount * position.entry_price)

                if unrealized_pnl_ratio <= self.day_config.max_loss_threshold:
                    logger.warning(
                        "Position %s hit loss limit: %.4f",
                        position_id,
                        unrealized_pnl_ratio,
                    )
                    self.close_position(position_id, "stop_loss", force=True)

    def check_force_close_time(self) -> None:
        """強制決済時間チェック"""
        now = datetime.now(self.timezone).time()

        if now >= self.day_config.force_close_time and self.active_positions:
            logger.warning(f"Force close time reached: {now}")
            self.close_all_positions("force_close_eod")

    def start_monitoring(self) -> None:
        """監視スレッド開始"""
        if self.monitoring_thread is not None and self.monitoring_thread.is_alive():
            return

        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        logger.info("Day trading monitoring started")

    def stop_monitoring(self) -> None:
        """監視スレッド停止"""
        self.stop_monitoring = True

        if self.monitoring_thread is not None:
            self.monitoring_thread.join(timeout=5)

        logger.info("Day trading monitoring stopped")

    def _monitoring_loop(self) -> None:
        """監視ループ"""
        while not self.stop_monitoring:
            try:
                # ポジションタイムアウトチェック
                self.check_position_timeouts()

                # 強制決済時間チェック
                self.check_force_close_time()

                # 1分間隔でチェック
                time_module.sleep(60)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time_module.sleep(60)

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """現在価格取得"""
        try:
            ticker = self.bitbank_client.fetch_ticker(symbol)
            return ticker["last"]
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None

    def get_position_status(self) -> Dict[str, any]:
        """ポジション状況取得"""
        current_phase = self.get_current_phase()

        # アクティブポジション詳細
        active_positions_detail = []
        total_unrealized_pnl = 0.0

        for position_id, position in self.active_positions.items():
            current_price = self._get_current_price(position.symbol)
            unrealized_pnl = (
                position.calculate_unrealized_pnl(current_price)
                if current_price
                else 0.0
            )
            total_unrealized_pnl += unrealized_pnl

            active_positions_detail.append(
                {
                    "position_id": position_id,
                    "symbol": position.symbol,
                    "side": position.side,
                    "amount": position.amount,
                    "entry_price": position.entry_price,
                    "current_price": current_price,
                    "unrealized_pnl": unrealized_pnl,
                    "holding_time": str(position.get_holding_time()),
                    "expected_exit": (
                        position.expected_exit_time.strftime("%H:%M:%S")
                        if position.expected_exit_time
                        else None
                    ),
                }
            )

        return {
            "current_phase": current_phase.value,
            "market_open": self.is_market_open(),
            "can_open_position": self.can_open_position(),
            "active_positions": {
                "count": len(self.active_positions),
                "max_allowed": self.day_config.max_positions,
                "total_unrealized_pnl": total_unrealized_pnl,
                "details": active_positions_detail,
            },
            "daily_stats": self.daily_stats.copy(),
            "next_force_close": self.day_config.force_close_time.strftime("%H:%M"),
            "monitoring_active": self.monitoring_thread is not None
            and self.monitoring_thread.is_alive(),
        }

    def get_daily_summary(self) -> Dict[str, any]:
        """日次サマリー取得"""
        total_positions = len(self.closed_positions)
        win_rate = (
            (self.daily_stats["profitable_trades"] / total_positions)
            if total_positions > 0
            else 0
        )

        avg_profit = (
            self.daily_stats["total_profit"] / total_positions
            if total_positions > 0
            else 0
        )
        net_profit = self.daily_stats["total_profit"] - self.daily_stats["total_fees"]

        return {
            "trading_date": datetime.now(self.timezone).strftime("%Y-%m-%d"),
            "summary": {
                "total_positions": total_positions,
                "profitable_positions": self.daily_stats["profitable_trades"],
                "win_rate": win_rate,
                "total_profit": self.daily_stats["total_profit"],
                "total_fees": self.daily_stats["total_fees"],
                "net_profit": net_profit,
                "interest_avoided": self.daily_stats["interest_avoided"],
                "positions_force_closed": self.daily_stats["positions_force_closed"],
            },
            "performance": {
                "average_profit_per_trade": avg_profit,
                "profit_factor": abs(
                    self.daily_stats["total_profit"]
                    / max(abs(self.daily_stats["total_fees"]), 0.001)
                ),
                "interest_avoidance_effect": self.daily_stats["interest_avoided"],
                "fee_efficiency": net_profit
                / max(abs(self.daily_stats["total_fees"]), 0.001),
            },
        }

    def reset_daily_stats(self) -> None:
        """日次統計リセット"""
        self.daily_stats = {
            "total_trades": 0,
            "profitable_trades": 0,
            "total_profit": 0.0,
            "total_fees": 0.0,
            "max_drawdown": 0.0,
            "positions_force_closed": 0,
            "interest_avoided": 0.0,
        }

        self.closed_positions.clear()
        logger.info("Daily stats reset")

    def __del__(self):
        """デストラクタ"""
        self.stop_monitoring()
