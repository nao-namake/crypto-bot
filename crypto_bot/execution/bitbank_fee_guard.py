"""
Bitbank手数料負け防止システム
累積手数料監視・最小利益閾値設定・高頻度取引対応・緊急時回避機能
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .bitbank_fee_optimizer import OrderType

logger = logging.getLogger(__name__)


class FeeRiskLevel(Enum):
    """手数料リスクレベル"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TradeDecision(Enum):
    """取引判定"""

    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"
    DELAY = "delay"


@dataclass
class FeeRiskAssessment:
    """手数料リスク評価"""

    risk_level: FeeRiskLevel
    risk_score: float
    cumulative_fee_impact: float
    recommended_action: TradeDecision
    reasons: List[str]
    suggested_modifications: Dict[str, any]


@dataclass
class FeeThresholds:
    """手数料閾値設定"""

    min_profit_margin: float = 0.0015  # 0.15% minimum profit
    max_daily_fee_loss: float = 0.01  # 1.0% maximum daily fee loss
    max_session_fee_loss: float = 0.005  # 0.5% maximum session fee loss
    taker_cost_warning: float = 0.008  # 0.8% warning threshold
    cumulative_warning: float = 0.02  # 2.0% cumulative warning
    emergency_stop: float = 0.05  # 5.0% emergency stop


class BitbankFeeGuard:
    """
    Bitbank手数料負け防止システム

    累積手数料監視・リスク評価・緊急時対応により
    手数料負けによる損失を防止
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # 手数料設定
        self.MAKER_FEE_RATE = -0.0002  # -0.02%
        self.TAKER_FEE_RATE = 0.0012  # 0.12%

        # 閾値設定
        fee_guard_config = self.config.get("bitbank_fee_guard", {})
        self.thresholds = FeeThresholds(
            min_profit_margin=fee_guard_config.get("min_profit_margin", 0.0015),
            max_daily_fee_loss=fee_guard_config.get("max_daily_fee_loss", 0.01),
            max_session_fee_loss=fee_guard_config.get("max_session_fee_loss", 0.005),
            taker_cost_warning=fee_guard_config.get("taker_cost_warning", 0.008),
            cumulative_warning=fee_guard_config.get("cumulative_warning", 0.02),
            emergency_stop=fee_guard_config.get("emergency_stop", 0.05),
        )

        # 高頻度取引対応設定
        self.high_frequency_mode = fee_guard_config.get("high_frequency_mode", False)
        self.trade_count_threshold = fee_guard_config.get("trade_count_threshold", 50)
        self.time_window_minutes = fee_guard_config.get("time_window_minutes", 60)

        # 監視データ
        self.session_start_time = datetime.now()
        self.trade_history: List[Dict] = []
        self.fee_accumulation: Dict[str, float] = {
            "session_maker_rebates": 0.0,
            "session_taker_costs": 0.0,
            "daily_maker_rebates": 0.0,
            "daily_taker_costs": 0.0,
            "total_trades": 0,
            "rejected_trades": 0,
        }

        # 緊急停止状態
        self.emergency_stop_active = False
        self.emergency_stop_reason = None
        self.emergency_stop_timestamp = None

        logger.info("BitbankFeeGuard initialized")
        logger.info(f"Min profit margin: {self.thresholds.min_profit_margin:.4f}")
        logger.info(f"Emergency stop threshold: {self.thresholds.emergency_stop:.4f}")

    def evaluate_trade_risk(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        expected_profit: float,
        order_type: OrderType,
        urgency_level: float = 0.0,
    ) -> FeeRiskAssessment:
        """
        取引の手数料リスク評価

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 価格
            expected_profit: 予想利益
            order_type: 注文タイプ
            urgency_level: 緊急度

        Returns:
            手数料リスク評価結果
        """
        # 緊急停止チェック
        if self.emergency_stop_active:
            return FeeRiskAssessment(
                risk_level=FeeRiskLevel.CRITICAL,
                risk_score=1.0,
                cumulative_fee_impact=0.0,
                recommended_action=TradeDecision.REJECT,
                reasons=["Emergency stop is active"],
                suggested_modifications={},
            )

        notional_value = amount * price

        # 手数料計算
        if order_type == OrderType.MAKER:
            fee_amount = notional_value * self.MAKER_FEE_RATE
        else:
            fee_amount = notional_value * self.TAKER_FEE_RATE

        # リスク評価
        risk_reasons = []
        risk_score = 0.0

        # 1. 利益マージンチェック
        if order_type == OrderType.TAKER:
            required_margin = notional_value * self.thresholds.min_profit_margin
            if expected_profit < required_margin:
                risk_reasons.append(
                    f"Insufficient profit margin: {expected_profit:.6f} < "
                    f"{required_margin:.6f}"
                )
                risk_score += 0.3

        # 2. 手数料負けチェック
        if order_type == OrderType.TAKER and expected_profit < abs(fee_amount) * 1.2:
            risk_reasons.append(
                f"Potential fee loss: profit={expected_profit:.6f}, "
                f"fee={fee_amount:.6f}"
            )
            risk_score += 0.4

        # 3. 累積手数料チェック
        cumulative_impact = self._calculate_cumulative_impact(fee_amount)
        if cumulative_impact > self.thresholds.cumulative_warning:
            risk_reasons.append(f"High cumulative fee impact: {cumulative_impact:.4f}")
            risk_score += 0.2

        # 4. 高頻度取引チェック
        if self.high_frequency_mode:
            trade_frequency = self._calculate_trade_frequency()
            if trade_frequency > self.trade_count_threshold:
                risk_reasons.append(
                    f"High frequency trading: {trade_frequency} trades/hour"
                )
                risk_score += 0.1

        # 5. セッション手数料チェック
        session_fee_impact = self._calculate_session_fee_impact(fee_amount)
        if session_fee_impact > self.thresholds.max_session_fee_loss:
            risk_reasons.append(f"Session fee limit exceeded: {session_fee_impact:.4f}")
            risk_score += 0.3

        # リスクレベル判定
        if risk_score >= 0.8:
            risk_level = FeeRiskLevel.CRITICAL
            recommended_action = TradeDecision.REJECT
        elif risk_score >= 0.6:
            risk_level = FeeRiskLevel.HIGH
            recommended_action = TradeDecision.MODIFY
        elif risk_score >= 0.3:
            risk_level = FeeRiskLevel.MEDIUM
            recommended_action = (
                TradeDecision.DELAY if urgency_level < 0.7 else TradeDecision.APPROVE
            )
        else:
            risk_level = FeeRiskLevel.LOW
            recommended_action = TradeDecision.APPROVE

        # 修正提案
        suggested_modifications = self._generate_modifications(
            order_type, risk_level, expected_profit, fee_amount, notional_value
        )

        return FeeRiskAssessment(
            risk_level=risk_level,
            risk_score=risk_score,
            cumulative_fee_impact=cumulative_impact,
            recommended_action=recommended_action,
            reasons=risk_reasons,
            suggested_modifications=suggested_modifications,
        )

    def should_block_trade(
        self,
        symbol: str,
        expected_profit: float,
        fee_amount: float,
        order_type: OrderType,
    ) -> Tuple[bool, str]:
        """
        取引をブロックすべきかを判定

        Args:
            symbol: 通貨ペア
            expected_profit: 予想利益
            fee_amount: 手数料
            order_type: 注文タイプ

        Returns:
            (ブロック判定, 理由)
        """
        # 緊急停止チェック
        if self.emergency_stop_active:
            return True, f"Emergency stop active: {self.emergency_stop_reason}"

        # 手数料負けチェック
        if order_type == OrderType.TAKER:
            if expected_profit < abs(fee_amount):
                return (
                    True,
                    f"Fee loss: profit={expected_profit:.6f} < "
                    f"fee={abs(fee_amount):.6f}",
                )

        # 累積手数料チェック
        cumulative_impact = self._calculate_cumulative_impact(fee_amount)
        if cumulative_impact > self.thresholds.emergency_stop:
            self._activate_emergency_stop("Cumulative fee limit exceeded")
            return (
                True,
                f"Emergency stop activated: cumulative_impact={cumulative_impact:.4f}",
            )

        # セッション手数料チェック
        session_impact = self._calculate_session_fee_impact(fee_amount)
        if session_impact > self.thresholds.max_session_fee_loss:
            return (
                True,
                f"Session fee limit: {session_impact:.4f} > "
                f"{self.thresholds.max_session_fee_loss:.4f}",
            )

        return False, ""

    def record_trade_execution(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        actual_fee: float,
        order_type: OrderType,
        profit: float,
    ) -> None:
        """
        取引実行を記録

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 価格
            actual_fee: 実際の手数料
            order_type: 注文タイプ
            profit: 実際の利益
        """
        # 取引記録
        trade_record = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "price": price,
            "notional_value": amount * price,
            "actual_fee": actual_fee,
            "order_type": order_type.value,
            "profit": profit,
            "net_profit": profit - abs(actual_fee),
        }

        self.trade_history.append(trade_record)

        # 累積データ更新
        self.fee_accumulation["total_trades"] += 1

        if order_type == OrderType.MAKER:
            self.fee_accumulation["session_maker_rebates"] += abs(actual_fee)
            self.fee_accumulation["daily_maker_rebates"] += abs(actual_fee)
        else:
            self.fee_accumulation["session_taker_costs"] += abs(actual_fee)
            self.fee_accumulation["daily_taker_costs"] += abs(actual_fee)

        # 警告チェック
        self._check_warning_conditions()

        logger.info(f"Trade recorded: {symbol} {side} {amount} @ {price}")
        logger.info(
            f"Fee: {actual_fee:.6f}, Net profit: {profit - abs(actual_fee):.6f}"
        )

    def get_fee_status(self) -> Dict[str, any]:
        """
        手数料状況取得

        Returns:
            手数料状況の詳細
        """
        session_duration = (
            datetime.now() - self.session_start_time
        ).total_seconds() / 3600

        # 純手数料結果
        session_net_fee = (
            self.fee_accumulation["session_maker_rebates"]
            - self.fee_accumulation["session_taker_costs"]
        )
        daily_net_fee = (
            self.fee_accumulation["daily_maker_rebates"]
            - self.fee_accumulation["daily_taker_costs"]
        )

        # 取引頻度
        trade_frequency = self.fee_accumulation["total_trades"] / max(
            session_duration, 0.1
        )

        # リスク評価
        current_risk_level = self._assess_current_risk_level()

        return {
            "session_info": {
                "duration_hours": session_duration,
                "total_trades": self.fee_accumulation["total_trades"],
                "rejected_trades": self.fee_accumulation["rejected_trades"],
                "trade_frequency": trade_frequency,
            },
            "fee_summary": {
                "session_maker_rebates": self.fee_accumulation["session_maker_rebates"],
                "session_taker_costs": self.fee_accumulation["session_taker_costs"],
                "session_net_fee": session_net_fee,
                "daily_maker_rebates": self.fee_accumulation["daily_maker_rebates"],
                "daily_taker_costs": self.fee_accumulation["daily_taker_costs"],
                "daily_net_fee": daily_net_fee,
            },
            "risk_assessment": {
                "current_risk_level": current_risk_level.value,
                "cumulative_impact": self._calculate_cumulative_impact(0),
                "session_impact": self._calculate_session_fee_impact(0),
                "emergency_stop_active": self.emergency_stop_active,
                "emergency_stop_reason": self.emergency_stop_reason,
            },
            "thresholds": {
                "min_profit_margin": self.thresholds.min_profit_margin,
                "max_session_fee_loss": self.thresholds.max_session_fee_loss,
                "emergency_stop": self.thresholds.emergency_stop,
            },
        }

    def reset_emergency_stop(self) -> bool:
        """
        緊急停止をリセット

        Returns:
            リセット成功/失敗
        """
        if not self.emergency_stop_active:
            return False

        # 安全性チェック
        current_impact = self._calculate_cumulative_impact(0)
        if current_impact > self.thresholds.emergency_stop * 0.8:
            logger.warning(
                f"Emergency stop reset denied: impact={current_impact:.4f} still high"
            )
            return False

        self.emergency_stop_active = False
        self.emergency_stop_reason = None
        self.emergency_stop_timestamp = None

        logger.info("Emergency stop reset successfully")
        return True

    def _calculate_cumulative_impact(self, additional_fee: float) -> float:
        """
        累積手数料影響度計算

        Args:
            additional_fee: 追加手数料

        Returns:
            累積影響度
        """
        total_costs = self.fee_accumulation["session_taker_costs"] + abs(additional_fee)
        total_rebates = self.fee_accumulation["session_maker_rebates"]

        net_impact = (total_costs - total_rebates) / 10000  # 1万円あたり
        return max(0, net_impact)

    def _calculate_session_fee_impact(self, additional_fee: float) -> float:
        """
        セッション手数料影響度計算

        Args:
            additional_fee: 追加手数料

        Returns:
            セッション影響度
        """
        session_costs = self.fee_accumulation["session_taker_costs"] + abs(
            additional_fee
        )
        session_rebates = self.fee_accumulation["session_maker_rebates"]

        net_impact = (session_costs - session_rebates) / 10000  # 1万円あたり
        return max(0, net_impact)

    def _calculate_trade_frequency(self) -> float:
        """
        取引頻度計算

        Returns:
            1時間あたりの取引数
        """
        if not self.trade_history:
            return 0.0

        # 過去1時間の取引数を計算
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_trades = [
            trade for trade in self.trade_history if trade["timestamp"] > cutoff_time
        ]

        return len(recent_trades)

    def _assess_current_risk_level(self) -> FeeRiskLevel:
        """
        現在のリスクレベル評価

        Returns:
            現在のリスクレベル
        """
        if self.emergency_stop_active:
            return FeeRiskLevel.CRITICAL

        cumulative_impact = self._calculate_cumulative_impact(0)

        if cumulative_impact > self.thresholds.emergency_stop * 0.8:
            return FeeRiskLevel.CRITICAL
        elif cumulative_impact > self.thresholds.cumulative_warning:
            return FeeRiskLevel.HIGH
        elif cumulative_impact > self.thresholds.cumulative_warning * 0.5:
            return FeeRiskLevel.MEDIUM
        else:
            return FeeRiskLevel.LOW

    def _activate_emergency_stop(self, reason: str) -> None:
        """
        緊急停止を発動

        Args:
            reason: 停止理由
        """
        self.emergency_stop_active = True
        self.emergency_stop_reason = reason
        self.emergency_stop_timestamp = datetime.now()

        logger.critical(f"Emergency stop activated: {reason}")

    def _check_warning_conditions(self) -> None:
        """
        警告条件チェック
        """
        cumulative_impact = self._calculate_cumulative_impact(0)

        if cumulative_impact > self.thresholds.cumulative_warning:
            logger.warning(
                f"Cumulative fee warning: {cumulative_impact:.4f} > "
                f"{self.thresholds.cumulative_warning:.4f}"
            )

        session_impact = self._calculate_session_fee_impact(0)
        if session_impact > self.thresholds.max_session_fee_loss * 0.8:
            logger.warning(
                f"Session fee warning: {session_impact:.4f} approaching limit"
            )

    def _generate_modifications(
        self,
        order_type: OrderType,
        risk_level: FeeRiskLevel,
        expected_profit: float,
        fee_amount: float,
        notional_value: float,
    ) -> Dict[str, any]:
        """
        修正提案生成

        Args:
            order_type: 注文タイプ
            risk_level: リスクレベル
            expected_profit: 予想利益
            fee_amount: 手数料
            notional_value: 想定元本

        Returns:
            修正提案
        """
        modifications = {}

        if risk_level in [FeeRiskLevel.HIGH, FeeRiskLevel.CRITICAL]:
            if order_type == OrderType.TAKER:
                modifications["order_type"] = "limit"
                modifications["strategy"] = "maker_priority"
                modifications["reason"] = "Switch to maker order to avoid fee"

        if risk_level == FeeRiskLevel.MEDIUM:
            modifications["delay_seconds"] = 30
            modifications["reason"] = "Delay to reduce frequency"

        if expected_profit < abs(fee_amount) * 1.5:
            modifications["min_profit_adjustment"] = abs(fee_amount) * 1.5
            modifications["reason"] = "Increase profit target"

        return modifications
