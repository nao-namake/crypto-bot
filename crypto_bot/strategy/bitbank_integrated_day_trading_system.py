"""
Bitbank統合デイトレードシステム
日中取引最適化・市場時間帯別戦略・強制決済システム
"""

import logging
import math
import threading
import time as time_module
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..execution.bitbank_fee_guard import BitbankFeeGuard
from ..execution.bitbank_fee_optimizer import BitbankFeeOptimizer
from ..execution.bitbank_order_manager import BitbankOrderManager
from ..strategy.bitbank_enhanced_position_manager import (
    BitbankEnhancedPositionManager,
    PositionPriority,
)

logger = logging.getLogger(__name__)


class MarketPhase(Enum):
    """市場フェーズ"""

    PRE_MARKET = "pre_market"  # 市場前 (8:00-9:00)
    OPENING = "opening"  # 開場 (9:00-10:00)
    MORNING_SESSION = "morning_session"  # 午前 (10:00-12:00)
    LUNCH_BREAK = "lunch_break"  # 昼休み (12:00-13:00)
    AFTERNOON_SESSION = "afternoon_session"  # 午後 (13:00-15:00)
    LATE_TRADING = "late_trading"  # 後場 (15:00-18:00)
    EVENING_SESSION = "evening_session"  # 夕方 (18:00-21:00)
    CLOSING_PHASE = "closing_phase"  # 決済フェーズ (21:00-23:00)
    AFTER_HOURS = "after_hours"  # 時間外 (23:00-8:00)


class TradingStrategy(Enum):
    """取引戦略"""

    MOMENTUM = "momentum"  # モメンタム戦略
    MEAN_REVERSION = "mean_reversion"  # 平均回帰戦略
    BREAKOUT = "breakout"  # ブレイクアウト戦略
    SCALPING = "scalping"  # スキャルピング戦略
    CONSERVATIVE = "conservative"  # 保守的戦略
    DEFENSIVE = "defensive"  # 防御的戦略
    AGGRESSIVE = "aggressive"  # 積極的戦略


class MarketCondition(Enum):
    """市場状況"""

    BULLISH = "bullish"  # 強気
    BEARISH = "bearish"  # 弱気
    SIDEWAYS = "sideways"  # 横ばい
    VOLATILE = "volatile"  # 高ボラティリティ
    QUIET = "quiet"  # 静穏
    TRENDING = "trending"  # トレンド
    RANGING = "ranging"  # レンジ


@dataclass
class TimeBasedConfig:
    """時間帯別設定"""

    phase: MarketPhase
    start_time: time
    end_time: time
    preferred_strategy: TradingStrategy
    position_size_multiplier: float = 1.0
    risk_tolerance: float = 1.0
    max_positions: int = 3
    force_close_before_end: bool = False
    allowed_new_positions: bool = True
    priority_adjustment: int = 0  # 優先度調整 (-2 to +2)


@dataclass
class StrategyPerformance:
    """戦略パフォーマンス"""

    strategy: TradingStrategy
    phase: MarketPhase
    total_trades: int = 0
    profitable_trades: int = 0
    total_profit: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    avg_holding_time: float = 0.0
    risk_adjusted_return: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class MarketAnalysis:
    """市場分析"""

    symbol: str
    current_phase: MarketPhase
    market_condition: MarketCondition
    volatility: float
    momentum: float
    trend_strength: float
    support_level: float
    resistance_level: float
    volume_ratio: float
    analysis_time: datetime = field(default_factory=datetime.now)


class BitbankIntegratedDayTradingSystem(BitbankEnhancedPositionManager):
    """
    Bitbank統合デイトレードシステム

    日中取引最適化・市場時間帯別戦略・強制決済システムの統合実装
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

        # 統合デイトレード設定
        day_trading_config = self.config.get("bitbank_integrated_day_trading", {})
        # 時間帯別設定
        self.time_based_configs = self._initialize_time_based_configs(
            day_trading_config
        )

        # 戦略パフォーマンス追跡
        self.strategy_performance: Dict[str, StrategyPerformance] = {}
        self._initialize_strategy_performance()

        # 市場分析キャッシュ
        self.market_analysis_cache: Dict[str, MarketAnalysis] = {}

        # フォース決済システム
        self.force_close_active = False
        self.force_close_thread = None

        # 統合メトリクス
        self.integrated_metrics = {
            "phase_transitions": 0,
            "strategy_switches": 0,
            "forced_closures": 0,
            "phase_optimizations": 0,
            "time_based_profits": 0.0,
            "market_adaptation_score": 0.0,
        }

        # 実行状態管理
        self.current_phase = MarketPhase.PRE_MARKET
        self.active_strategy = TradingStrategy.CONSERVATIVE
        self.phase_start_time = datetime.now(self.timezone)

        logger.info("BitbankIntegratedDayTradingSystem initialized")
        logger.info(f"Configured {len(self.time_based_configs)} time-based phases")

        # 統合システム開始
        self.start_integrated_system()

    def _initialize_time_based_configs(
        self, config: Dict
    ) -> Dict[MarketPhase, TimeBasedConfig]:
        """時間帯別設定初期化"""
        default_configs = {
            MarketPhase.PRE_MARKET: TimeBasedConfig(
                phase=MarketPhase.PRE_MARKET,
                start_time=time(8, 0),
                end_time=time(9, 0),
                preferred_strategy=TradingStrategy.CONSERVATIVE,
                position_size_multiplier=0.5,
                risk_tolerance=0.6,
                max_positions=2,
                allowed_new_positions=False,
            ),
            MarketPhase.OPENING: TimeBasedConfig(
                phase=MarketPhase.OPENING,
                start_time=time(9, 0),
                end_time=time(10, 0),
                preferred_strategy=TradingStrategy.MOMENTUM,
                position_size_multiplier=1.2,
                risk_tolerance=1.3,
                max_positions=4,
                priority_adjustment=1,
            ),
            MarketPhase.MORNING_SESSION: TimeBasedConfig(
                phase=MarketPhase.MORNING_SESSION,
                start_time=time(10, 0),
                end_time=time(12, 0),
                preferred_strategy=TradingStrategy.BREAKOUT,
                position_size_multiplier=1.0,
                risk_tolerance=1.0,
                max_positions=3,
            ),
            MarketPhase.LUNCH_BREAK: TimeBasedConfig(
                phase=MarketPhase.LUNCH_BREAK,
                start_time=time(12, 0),
                end_time=time(13, 0),
                preferred_strategy=TradingStrategy.SCALPING,
                position_size_multiplier=0.8,
                risk_tolerance=0.8,
                max_positions=2,
            ),
            MarketPhase.AFTERNOON_SESSION: TimeBasedConfig(
                phase=MarketPhase.AFTERNOON_SESSION,
                start_time=time(13, 0),
                end_time=time(15, 0),
                preferred_strategy=TradingStrategy.MOMENTUM,
                position_size_multiplier=1.1,
                risk_tolerance=1.2,
                max_positions=4,
            ),
            MarketPhase.LATE_TRADING: TimeBasedConfig(
                phase=MarketPhase.LATE_TRADING,
                start_time=time(15, 0),
                end_time=time(18, 0),
                preferred_strategy=TradingStrategy.MEAN_REVERSION,
                position_size_multiplier=0.9,
                risk_tolerance=0.9,
                max_positions=3,
            ),
            MarketPhase.EVENING_SESSION: TimeBasedConfig(
                phase=MarketPhase.EVENING_SESSION,
                start_time=time(18, 0),
                end_time=time(21, 0),
                preferred_strategy=TradingStrategy.CONSERVATIVE,
                position_size_multiplier=0.7,
                risk_tolerance=0.7,
                max_positions=2,
            ),
            MarketPhase.CLOSING_PHASE: TimeBasedConfig(
                phase=MarketPhase.CLOSING_PHASE,
                start_time=time(21, 0),
                end_time=time(23, 0),
                preferred_strategy=TradingStrategy.DEFENSIVE,
                position_size_multiplier=0.5,
                risk_tolerance=0.5,
                max_positions=1,
                force_close_before_end=True,
                allowed_new_positions=False,
                priority_adjustment=2,
            ),
            MarketPhase.AFTER_HOURS: TimeBasedConfig(
                phase=MarketPhase.AFTER_HOURS,
                start_time=time(23, 0),
                end_time=time(8, 0),
                preferred_strategy=TradingStrategy.DEFENSIVE,
                position_size_multiplier=0.3,
                risk_tolerance=0.3,
                max_positions=0,
                allowed_new_positions=False,
            ),
        }

        # 設定のカスタマイズ適用
        for phase, default_config in default_configs.items():
            phase_config = config.get(phase.value, {})

            # カスタム設定を適用
            if "position_size_multiplier" in phase_config:
                default_config.position_size_multiplier = phase_config[
                    "position_size_multiplier"
                ]
            if "risk_tolerance" in phase_config:
                default_config.risk_tolerance = phase_config["risk_tolerance"]
            if "max_positions" in phase_config:
                default_config.max_positions = phase_config["max_positions"]
            if "preferred_strategy" in phase_config:
                default_config.preferred_strategy = TradingStrategy(
                    phase_config["preferred_strategy"]
                )

        return default_configs

    def _initialize_strategy_performance(self) -> None:
        """戦略パフォーマンス初期化"""
        for strategy in TradingStrategy:
            for phase in MarketPhase:
                key = f"{strategy.value}_{phase.value}"
                self.strategy_performance[key] = StrategyPerformance(
                    strategy=strategy, phase=phase
                )

    def get_current_market_phase(self) -> MarketPhase:
        """現在の市場フェーズ取得"""
        now = datetime.now(self.timezone).time()

        # 各フェーズの時間帯をチェック
        for phase, config in self.time_based_configs.items():
            if config.start_time <= config.end_time:
                # 同日内の時間帯
                if config.start_time <= now <= config.end_time:
                    return phase
            else:
                # 日をまたぐ時間帯 (AFTER_HOURS)
                if now >= config.start_time or now <= config.end_time:
                    return phase

        # デフォルト
        return MarketPhase.AFTER_HOURS

    def analyze_market_condition(self, symbol: str) -> MarketAnalysis:
        """市場状況分析"""
        try:
            # 市場データ取得
            # ticker = self.bitbank_client.fetch_ticker(symbol)
            ohlcv = self.bitbank_client.fetch_ohlcv(symbol, "5m", limit=50)
            # orderbook = self.bitbank_client.fetch_order_book(symbol)

            # 価格データ分析
            prices = [candle[4] for candle in ohlcv]  # 終値
            volumes = [candle[5] for candle in ohlcv]  # 出来高

            # ボラティリティ計算
            returns = [
                math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))
            ]
            volatility = np.std(returns) * math.sqrt(288)  # 日次ボラティリティ

            # モメンタム計算
            momentum = (prices[-1] - prices[0]) / prices[0]

            # トレンド強度計算
            trend_strength = abs(momentum) * (1 - volatility)

            # サポート・レジスタンス計算
            recent_prices = prices[-20:]
            support_level = min(recent_prices)
            resistance_level = max(recent_prices)

            # 出来高比率計算
            avg_volume = sum(volumes[-10:]) / 10
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

            # 市場状況判定
            market_condition = self._determine_market_condition(
                momentum, volatility, trend_strength, volume_ratio
            )

            analysis = MarketAnalysis(
                symbol=symbol,
                current_phase=self.get_current_market_phase(),
                market_condition=market_condition,
                volatility=volatility,
                momentum=momentum,
                trend_strength=trend_strength,
                support_level=support_level,
                resistance_level=resistance_level,
                volume_ratio=volume_ratio,
            )

            # キャッシュ更新
            self.market_analysis_cache[symbol] = analysis

            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze market condition for {symbol}: {e}")

            # フォールバック分析
            return MarketAnalysis(
                symbol=symbol,
                current_phase=self.get_current_market_phase(),
                market_condition=MarketCondition.SIDEWAYS,
                volatility=0.01,
                momentum=0.0,
                trend_strength=0.0,
                support_level=0.0,
                resistance_level=0.0,
                volume_ratio=1.0,
            )

    def _determine_market_condition(
        self,
        momentum: float,
        volatility: float,
        trend_strength: float,
        volume_ratio: float,
    ) -> MarketCondition:
        """市場状況判定"""
        # 高ボラティリティ判定
        if volatility > 0.03:
            return MarketCondition.VOLATILE

        # 静穏判定
        if volatility < 0.005 and abs(momentum) < 0.01:
            return MarketCondition.QUIET

        # トレンド判定
        if trend_strength > 0.02:
            return MarketCondition.TRENDING

        # 方向性判定
        if momentum > 0.02 and volume_ratio > 1.2:
            return MarketCondition.BULLISH
        elif momentum < -0.02 and volume_ratio > 1.2:
            return MarketCondition.BEARISH
        elif abs(momentum) < 0.01:
            return MarketCondition.SIDEWAYS
        else:
            return MarketCondition.RANGING

    def select_optimal_strategy(self, symbol: str) -> TradingStrategy:
        """最適戦略選択"""
        # 1. 現在のフェーズ設定取得
        current_phase = self.get_current_market_phase()
        phase_config = self.time_based_configs[current_phase]

        # 2. 市場分析
        market_analysis = self.analyze_market_condition(symbol)

        # 3. 基本戦略（フェーズ推奨）
        base_strategy = phase_config.preferred_strategy

        # 4. 市場状況による調整
        adjusted_strategy = self._adjust_strategy_for_market_condition(
            base_strategy, market_analysis
        )

        # 5. パフォーマンス履歴による調整
        performance_adjusted_strategy = self._adjust_strategy_for_performance(
            adjusted_strategy, current_phase
        )

        # 6. 戦略変更検出
        if performance_adjusted_strategy != self.active_strategy:
            self.integrated_metrics["strategy_switches"] += 1
            logger.info(
                f"Strategy switch: {self.active_strategy.value} → "
                f"{performance_adjusted_strategy.value}"
            )

        self.active_strategy = performance_adjusted_strategy

        return performance_adjusted_strategy

    def _adjust_strategy_for_market_condition(
        self, base_strategy: TradingStrategy, market_analysis: MarketAnalysis
    ) -> TradingStrategy:
        """市場状況による戦略調整"""
        condition = market_analysis.market_condition

        # 市場状況別の戦略マッピング
        strategy_mapping = {
            MarketCondition.BULLISH: TradingStrategy.MOMENTUM,
            MarketCondition.BEARISH: TradingStrategy.MOMENTUM,
            MarketCondition.SIDEWAYS: TradingStrategy.MEAN_REVERSION,
            MarketCondition.VOLATILE: TradingStrategy.SCALPING,
            MarketCondition.QUIET: TradingStrategy.BREAKOUT,
            MarketCondition.TRENDING: TradingStrategy.MOMENTUM,
            MarketCondition.RANGING: TradingStrategy.MEAN_REVERSION,
        }

        # 市場状況に応じた戦略
        market_preferred = strategy_mapping.get(condition, base_strategy)

        # 基本戦略と市場推奨戦略の重み付け
        if market_analysis.trend_strength > 0.03:
            return market_preferred  # 強トレンド時は市場推奨優先
        elif market_analysis.volatility > 0.02:
            return market_preferred  # 高ボラティリティ時は市場推奨優先
        else:
            return base_strategy  # 通常時は基本戦略

    def _adjust_strategy_for_performance(
        self, strategy: TradingStrategy, phase: MarketPhase
    ) -> TradingStrategy:
        """パフォーマンス履歴による戦略調整"""
        key = f"{strategy.value}_{phase.value}"
        performance = self.strategy_performance.get(key)

        if not performance or performance.total_trades < 5:
            return strategy  # 十分なデータがない場合は変更しない

        # パフォーマンスが悪い場合は代替戦略を検討
        if performance.win_rate < 0.4 or performance.risk_adjusted_return < 0:

            # 代替戦略候補
            alternative_strategies = [
                TradingStrategy.CONSERVATIVE,
                TradingStrategy.DEFENSIVE,
                TradingStrategy.MEAN_REVERSION,
            ]

            # 最もパフォーマンスの良い代替戦略を選択
            best_alternative = strategy
            best_performance = performance.risk_adjusted_return

            for alt_strategy in alternative_strategies:
                alt_key = f"{alt_strategy.value}_{phase.value}"
                alt_performance = self.strategy_performance.get(alt_key)

                if alt_performance and alt_performance.total_trades >= 3:
                    if alt_performance.risk_adjusted_return > best_performance:
                        best_alternative = alt_strategy
                        best_performance = alt_performance.risk_adjusted_return

            return best_alternative

        return strategy

    def open_position(
        self, symbol: str, side: str, amount: float, price: float, reason: str = ""
    ) -> Tuple[bool, str, Optional[str]]:
        """
        統合ポジション開設

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文量
            price: 価格
            reason: 開設理由

        Returns:
            (成功/失敗, メッセージ, ポジションID)
        """
        # 1. 現在フェーズ確認
        current_phase = self.get_current_market_phase()
        phase_config = self.time_based_configs[current_phase]

        # 2. 新規ポジション開設許可チェック
        if not phase_config.allowed_new_positions:
            return False, f"New positions not allowed in {current_phase.value}", None

        # 3. フェーズ別ポジション数制限
        if len(self.active_positions) >= phase_config.max_positions:
            return (
                False,
                f"Max positions reached for {current_phase.value}: "
                f"{phase_config.max_positions}",
                None,
            )

        # 4. 最適戦略選択
        optimal_strategy = self.select_optimal_strategy(symbol)

        # 5. フェーズ別ポジションサイズ調整
        adjusted_amount = amount * phase_config.position_size_multiplier

        # 6. 市場分析に基づく追加調整
        market_analysis = self.analyze_market_condition(symbol)

        # ボラティリティ調整
        if market_analysis.volatility > 0.03:
            adjusted_amount *= 0.8  # 高ボラティリティ時は削減
        elif market_analysis.volatility < 0.01:
            adjusted_amount *= 1.2  # 低ボラティリティ時は増加

        # 7. 基底クラスでポジション開設
        success, message, position_id = super().open_position(
            symbol,
            side,
            adjusted_amount,
            price,
            f"{reason} | Phase: {current_phase.value} | "
            f"Strategy: {optimal_strategy.value}",
        )

        if success and position_id:
            # 8. 戦略固有の追加処理
            self._apply_strategy_specific_logic(
                position_id, optimal_strategy, market_analysis
            )

            # 9. フェーズ別優先度調整
            if position_id in self.position_priorities:
                current_priority = self.position_priorities[position_id]
                adjusted_priority = self._adjust_priority_for_phase(
                    current_priority, phase_config
                )
                self.position_priorities[position_id] = adjusted_priority

            # 10. メトリクス更新
            self.integrated_metrics["phase_optimizations"] += 1

        return success, message, position_id

    def _apply_strategy_specific_logic(
        self,
        position_id: str,
        strategy: TradingStrategy,
        market_analysis: MarketAnalysis,
    ) -> None:
        """戦略固有ロジック適用"""
        if position_id not in self.active_positions:
            return

        # position = self.active_positions[position_id]

        # 戦略別の特別処理
        if strategy == TradingStrategy.SCALPING:
            # スキャルピング: 短期決済設定
            if position_id in self.interest_schedules:
                schedule = self.interest_schedules[position_id]
                # 15分で決済
                schedule.avoidance_deadline = datetime.now(self.timezone) + timedelta(
                    minutes=15
                )

        elif strategy == TradingStrategy.MOMENTUM:
            # モメンタム: トレンド方向の利益目標拡大
            if abs(market_analysis.momentum) > 0.02:
                # 利益目標を1.5倍に拡大
                pass  # 実装は省略

        elif strategy == TradingStrategy.MEAN_REVERSION:
            # 平均回帰: タイトな損切り設定
            if position_id in self.position_priorities:
                # 優先度を上げてタイトな管理
                self.position_priorities[position_id] = PositionPriority.HIGH

        elif strategy == TradingStrategy.DEFENSIVE:
            # 防御的: 早期決済指向
            if position_id in self.position_priorities:
                self.position_priorities[position_id] = PositionPriority.HIGH

    def _adjust_priority_for_phase(
        self, base_priority: PositionPriority, phase_config: TimeBasedConfig
    ) -> PositionPriority:
        """フェーズ別優先度調整"""
        adjustment = phase_config.priority_adjustment

        # 優先度数値化
        priority_values = {
            PositionPriority.LOW: 1,
            PositionPriority.MEDIUM: 2,
            PositionPriority.HIGH: 3,
            PositionPriority.CRITICAL: 4,
            PositionPriority.MONITORING: 0,
        }

        reverse_mapping = {v: k for k, v in priority_values.items()}

        current_value = priority_values.get(base_priority, 2)
        adjusted_value = max(0, min(4, current_value + adjustment))

        return reverse_mapping.get(adjusted_value, base_priority)

    def process_phase_transition(self, new_phase: MarketPhase) -> None:
        """フェーズ遷移処理"""
        old_phase = self.current_phase

        if old_phase == new_phase:
            return

        logger.info(f"Phase transition: {old_phase.value} → {new_phase.value}")

        # 1. フェーズ更新
        self.current_phase = new_phase
        self.phase_start_time = datetime.now(self.timezone)

        # 2. 新フェーズ設定取得
        new_config = self.time_based_configs[new_phase]

        # 3. 既存ポジションの優先度調整
        for position_id, current_priority in self.position_priorities.items():
            adjusted_priority = self._adjust_priority_for_phase(
                current_priority, new_config
            )
            self.position_priorities[position_id] = adjusted_priority

        # 4. 強制決済チェック
        if new_config.force_close_before_end:
            self.schedule_force_close(new_phase)

        # 5. 新規ポジション制限チェック
        if not new_config.allowed_new_positions:
            logger.warning(f"New positions disabled in {new_phase.value}")

        # 6. ポジション数制限チェック
        if len(self.active_positions) > new_config.max_positions:
            excess_positions = len(self.active_positions) - new_config.max_positions
            logger.warning(
                f"Excess positions: {excess_positions}, consider closing some"
            )

        # 7. メトリクス更新
        self.integrated_metrics["phase_transitions"] += 1

        # 8. 戦略選択（次回の取引で使用）
        if self.active_positions:
            symbol = list(self.active_positions.values())[0].symbol
            self.select_optimal_strategy(symbol)

    def schedule_force_close(self, phase: MarketPhase) -> None:
        """強制決済スケジュール"""
        phase_config = self.time_based_configs[phase]

        # 強制決済時刻計算
        now = datetime.now(self.timezone)
        force_close_time = datetime.combine(now.date(), phase_config.end_time)
        force_close_time = self.timezone.localize(force_close_time)

        # 30分前に強制決済開始
        actual_close_time = force_close_time - timedelta(minutes=30)

        if actual_close_time <= now:
            # 即座に実行
            self.execute_force_close("immediate_phase_end")
        else:
            # スケジュール実行
            delay_seconds = (actual_close_time - now).total_seconds()

            def delayed_force_close():
                time_module.sleep(delay_seconds)
                self.execute_force_close("scheduled_phase_end")

            if (
                self.force_close_thread is None
                or not self.force_close_thread.is_alive()
            ):
                self.force_close_thread = threading.Thread(target=delayed_force_close)
                self.force_close_thread.daemon = True
                self.force_close_thread.start()

    def execute_force_close(self, reason: str) -> Dict[str, bool]:
        """強制決済実行"""
        if not self.active_positions:
            return {}

        logger.warning(f"Executing force close: {reason}")

        # 全ポジション決済
        results = self.close_all_positions(reason)

        # メトリクス更新
        self.integrated_metrics["forced_closures"] += len(results)

        return results

    def update_strategy_performance(
        self,
        position_id: str,
        strategy: TradingStrategy,
        phase: MarketPhase,
        profit: float,
        holding_time: float,
    ) -> None:
        """戦略パフォーマンス更新"""
        key = f"{strategy.value}_{phase.value}"
        performance = self.strategy_performance.get(key)

        if not performance:
            return

        # 統計更新
        performance.total_trades += 1
        performance.total_profit += profit

        if profit > 0:
            performance.profitable_trades += 1

        performance.win_rate = performance.profitable_trades / performance.total_trades

        # 平均保有時間更新
        total_holding_time = performance.avg_holding_time * (
            performance.total_trades - 1
        )
        performance.avg_holding_time = (
            total_holding_time + holding_time
        ) / performance.total_trades

        # リスク調整リターン計算（簡易版）
        if performance.total_trades > 5:
            avg_profit = performance.total_profit / performance.total_trades
            profit_volatility = 0.02  # 簡易値
            performance.risk_adjusted_return = avg_profit / max(
                profit_volatility, 0.001
            )

        performance.last_updated = datetime.now()

        # 統合メトリクス更新
        if profit > 0:
            self.integrated_metrics["time_based_profits"] += profit

    def close_position(
        self, position_id: str, reason: str = "manual", force: bool = False
    ) -> Tuple[bool, str]:
        """
        統合ポジション決済

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

        # 基底クラスで決済実行
        success, message = super().close_position(position_id, reason, force)

        if success:
            # 戦略パフォーマンス更新
            holding_time = (
                position.get_holding_time().total_seconds() / 3600
            )  # 時間単位

            self.update_strategy_performance(
                position_id,
                self.active_strategy,
                self.current_phase,
                position.profit_loss,
                holding_time,
            )

        return success, message

    def start_integrated_system(self) -> None:
        """統合システム開始"""
        # 基底クラスのシステム開始
        self.start_optimization()

        # フェーズ監視スレッド開始
        self.start_phase_monitoring()

        logger.info("Integrated day trading system started")

    def start_phase_monitoring(self) -> None:
        """フェーズ監視開始"""

        def phase_monitoring_loop():
            while self.optimization_active:
                try:
                    # 現在フェーズ確認
                    current_phase = self.get_current_market_phase()

                    # フェーズ変更チェック
                    if current_phase != self.current_phase:
                        self.process_phase_transition(current_phase)

                    # 30秒間隔でチェック
                    time_module.sleep(30)

                except Exception as e:
                    logger.error(f"Error in phase monitoring: {e}")
                    time_module.sleep(60)

        # 監視スレッド開始
        phase_thread = threading.Thread(target=phase_monitoring_loop)
        phase_thread.daemon = True
        phase_thread.start()

    def get_integrated_status(self) -> Dict[str, Any]:
        """統合ステータス取得"""
        base_status = self.get_enhanced_position_status()

        # 統合情報追加
        current_phase = self.get_current_market_phase()
        phase_config = self.time_based_configs[current_phase]

        # 市場分析（アクティブポジションがある場合）
        market_analyses = {}
        for position in self.active_positions.values():
            if position.symbol not in market_analyses:
                analysis = self.analyze_market_condition(position.symbol)
                market_analyses[position.symbol] = {
                    "condition": analysis.market_condition.value,
                    "volatility": analysis.volatility,
                    "momentum": analysis.momentum,
                    "trend_strength": analysis.trend_strength,
                }

        # 戦略パフォーマンス統計
        strategy_stats = {}
        for strategy in TradingStrategy:
            key = f"{strategy.value}_{current_phase.value}"
            performance = self.strategy_performance.get(key)
            if performance and performance.total_trades > 0:
                strategy_stats[strategy.value] = {
                    "total_trades": performance.total_trades,
                    "win_rate": performance.win_rate,
                    "total_profit": performance.total_profit,
                    "avg_holding_time": performance.avg_holding_time,
                }

        # 統合ステータス
        integrated_status = {
            "current_phase": {
                "phase": current_phase.value,
                "start_time": phase_config.start_time.strftime("%H:%M"),
                "end_time": phase_config.end_time.strftime("%H:%M"),
                "preferred_strategy": phase_config.preferred_strategy.value,
                "max_positions": phase_config.max_positions,
                "allowed_new_positions": phase_config.allowed_new_positions,
                "force_close_before_end": phase_config.force_close_before_end,
            },
            "active_strategy": self.active_strategy.value,
            "market_analyses": market_analyses,
            "strategy_performance": strategy_stats,
            "integrated_metrics": self.integrated_metrics.copy(),
            "force_close_scheduled": self.force_close_thread is not None
            and self.force_close_thread.is_alive(),
        }

        base_status["integrated_day_trading"] = integrated_status

        return base_status

    def get_day_trading_report(self) -> Dict[str, Any]:
        """デイトレードレポート取得"""
        # 基本レポート
        base_report = self.get_daily_summary()

        # 時間帯別パフォーマンス
        phase_performance = {}
        for phase in MarketPhase:
            phase_stats = {
                "total_trades": 0,
                "total_profit": 0.0,
                "win_rate": 0.0,
                "avg_holding_time": 0.0,
            }

            for strategy in TradingStrategy:
                key = f"{strategy.value}_{phase.value}"
                performance = self.strategy_performance.get(key)
                if performance and performance.total_trades > 0:
                    phase_stats["total_trades"] += performance.total_trades
                    phase_stats["total_profit"] += performance.total_profit
                    phase_stats["win_rate"] += (
                        performance.win_rate * performance.total_trades
                    )
                    phase_stats["avg_holding_time"] += (
                        performance.avg_holding_time * performance.total_trades
                    )

            if phase_stats["total_trades"] > 0:
                phase_stats["win_rate"] /= phase_stats["total_trades"]
                phase_stats["avg_holding_time"] /= phase_stats["total_trades"]

            phase_performance[phase.value] = phase_stats

        # 戦略効果分析
        strategy_effectiveness = {}
        for strategy in TradingStrategy:
            total_trades = sum(
                self.strategy_performance.get(
                    f"{strategy.value}_{phase.value}",
                    StrategyPerformance(strategy, phase),
                ).total_trades
                for phase in MarketPhase
            )

            total_profit = sum(
                self.strategy_performance.get(
                    f"{strategy.value}_{phase.value}",
                    StrategyPerformance(strategy, phase),
                ).total_profit
                for phase in MarketPhase
            )

            if total_trades > 0:
                strategy_effectiveness[strategy.value] = {
                    "total_trades": total_trades,
                    "total_profit": total_profit,
                    "avg_profit_per_trade": total_profit / total_trades,
                }

        # 統合レポート
        integrated_report = {
            "base_performance": base_report,
            "phase_performance": phase_performance,
            "strategy_effectiveness": strategy_effectiveness,
            "integrated_metrics": self.integrated_metrics.copy(),
            "system_health": {
                "phase_transitions_today": self.integrated_metrics["phase_transitions"],
                "strategy_switches_today": self.integrated_metrics["strategy_switches"],
                "forced_closures_today": self.integrated_metrics["forced_closures"],
                "market_adaptation_score": self.integrated_metrics[
                    "market_adaptation_score"
                ],
            },
            "recommendations": self._generate_integrated_recommendations(),
        }

        return integrated_report

    def _generate_integrated_recommendations(self) -> List[str]:
        """統合推奨事項生成"""
        recommendations = []

        # フェーズ別パフォーマンス分析
        worst_phase = None
        worst_performance = float("inf")

        for phase in MarketPhase:
            phase_profit = sum(
                self.strategy_performance.get(
                    f"{strategy.value}_{phase.value}",
                    StrategyPerformance(strategy, phase),
                ).total_profit
                for strategy in TradingStrategy
            )

            if phase_profit < worst_performance:
                worst_performance = phase_profit
                worst_phase = phase

        if worst_phase and worst_performance < -0.01:
            recommendations.append(
                f"{worst_phase.value}フェーズのパフォーマンスが悪いです。戦略見直しを検討してください。"
            )

        # 強制決済頻度チェック
        if self.integrated_metrics["forced_closures"] > 10:
            recommendations.append(
                "強制決済が多発しています。ポジション保有時間の最適化が必要です。"
            )

        # 戦略切り替え頻度チェック
        if self.integrated_metrics["strategy_switches"] > 20:
            recommendations.append(
                "戦略切り替えが頻繁です。戦略選択アルゴリズムの調整を検討してください。"
            )

        # 全体的な収益性チェック
        if self.integrated_metrics["time_based_profits"] < 0:
            recommendations.append(
                "時間帯別最適化の効果が出ていません。設定の見直しが必要です。"
            )

        if len(recommendations) == 0:
            recommendations.append("統合デイトレードシステムは良好に動作しています。")

        return recommendations

    def __del__(self):
        """デストラクタ"""
        if self.force_close_thread is not None:
            self.force_close_active = False

        super().__del__()
