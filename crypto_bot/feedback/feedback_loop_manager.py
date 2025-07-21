# =============================================================================
# ファイル名: crypto_bot/feedback/feedback_loop_manager.py
# 説明:
# Phase C2: フィードバックループ管理システム
# 予測結果収集・分析・パラメータ自動更新・継続的学習・適応最適化
# Phase C2全コンポーネント統合・自動改善サイクル実現
# =============================================================================

import logging
import os
import pickle
import threading
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """フィードバック種別"""

    PREDICTION_OUTCOME = "prediction_outcome"
    TRADE_RESULT = "trade_result"
    MARKET_ENVIRONMENT = "market_environment"
    WEIGHT_ADJUSTMENT = "weight_adjustment"
    PERFORMANCE_METRIC = "performance_metric"


@dataclass
class FeedbackEvent:
    """フィードバックイベント"""

    timestamp: datetime
    event_id: str
    feedback_type: FeedbackType
    timeframe: str

    # 予測関連
    prediction: Optional[Any] = None
    actual_outcome: Optional[Any] = None
    confidence: Optional[float] = None
    prediction_correct: Optional[bool] = None

    # 取引関連
    trade_id: Optional[str] = None
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    trade_successful: Optional[bool] = None

    # 市場関連
    market_context: Optional[Dict[str, Any]] = None
    market_regime: Optional[str] = None
    volatility_level: Optional[float] = None

    # パラメータ関連
    parameters_before: Optional[Dict[str, Any]] = None
    parameters_after: Optional[Dict[str, Any]] = None
    adjustment_reason: Optional[str] = None

    # メタデータ
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LearningInsight:
    """学習インサイト"""

    insight_id: str
    timestamp: datetime
    insight_type: str
    confidence_level: float
    description: str
    data_evidence: Dict[str, Any]
    recommended_actions: List[str]
    impact_assessment: str


class FeedbackLoopManager:
    """
    Phase C2: フィードバックループ管理システム

    機能:
    - 包括的予測結果・取引結果・市場環境フィードバック収集
    - 統計的分析・パターン認識・学習インサイト生成
    - 自動パラメータ調整・モデル更新・戦略最適化
    - 継続的学習サイクル・適応的改善システム
    - Phase C2コンポーネント統合・最適化フィードバック
    - A/Bテスト・実験計画・効果測定支援
    """

    def __init__(self, config: Dict[str, Any]):
        """
        フィードバックループ管理システム初期化

        Parameters:
        -----------
        config : Dict[str, Any]
            フィードバック設定辞書
        """
        self.config = config

        # 基本設定
        feedback_config = config.get("feedback_loop", {})
        self.timeframes = feedback_config.get("timeframes", ["15m", "1h", "4h"])
        self.learning_enabled = feedback_config.get("learning_enabled", True)
        self.auto_parameter_adjustment = feedback_config.get("auto_adjustment", True)
        self.feedback_window = feedback_config.get("feedback_window", 200)
        self.analysis_interval = feedback_config.get("analysis_interval", 300)  # 秒

        # 学習設定
        learning_config = feedback_config.get("learning", {})
        self.min_samples_for_learning = learning_config.get("min_samples", 50)
        self.learning_threshold = learning_config.get("threshold", 0.6)
        self.insight_confidence_threshold = learning_config.get(
            "insight_confidence", 0.7
        )
        self.max_parameter_change = learning_config.get("max_parameter_change", 0.2)

        # パターン認識設定
        pattern_config = feedback_config.get("pattern_recognition", {})
        self.pattern_detection_enabled = pattern_config.get("enabled", True)
        self.pattern_min_occurrences = pattern_config.get("min_occurrences", 10)
        self.pattern_significance_level = pattern_config.get("significance_level", 0.05)

        # データストレージ
        self.feedback_events: deque = deque(maxlen=self.feedback_window * 5)
        self.learning_insights: deque = deque(maxlen=100)
        self.parameter_history: deque = deque(maxlen=200)

        # 分析データ構造
        self.prediction_analysis = {
            timeframe: {
                "correct_predictions": deque(maxlen=self.feedback_window),
                "incorrect_predictions": deque(maxlen=self.feedback_window),
                "confidence_scores": deque(maxlen=self.feedback_window),
                "market_contexts": deque(maxlen=self.feedback_window),
            }
            for timeframe in self.timeframes
        }

        self.trade_analysis = {
            timeframe: {
                "successful_trades": deque(maxlen=self.feedback_window),
                "failed_trades": deque(maxlen=self.feedback_window),
                "trade_durations": deque(maxlen=self.feedback_window),
                "pnl_history": deque(maxlen=self.feedback_window),
            }
            for timeframe in self.timeframes
        }

        # パターン追跡
        self.discovered_patterns = {}
        self.pattern_performance = defaultdict(list)

        # 統計追跡
        self.feedback_stats = {
            "total_events": 0,
            "prediction_events": 0,
            "trade_events": 0,
            "parameter_adjustments": 0,
            "insights_generated": 0,
            "patterns_discovered": 0,
            "learning_cycles": 0,
            "automatic_improvements": 0,
        }

        # コンポーネント参照（外部から設定）
        self.dynamic_weight_adjuster = None
        self.performance_monitor = None
        self.market_analyzer = None

        # 学習スレッド管理
        self.learning_thread: Optional[threading.Thread] = None
        self.stop_learning = threading.Event()
        self.learning_active = False

        # パラメータ更新コールバック
        self.parameter_update_callbacks: List[Callable] = []

        # データ永続化
        self.enable_persistence = feedback_config.get("persistence", {}).get(
            "enabled", False
        )
        self.persistence_path = feedback_config.get("persistence", {}).get(
            "path", "data/feedback_history"
        )

        logger.info("🔄 FeedbackLoopManager initialized")
        logger.info(f"   Learning enabled: {self.learning_enabled}")
        logger.info(f"   Auto parameter adjustment: {self.auto_parameter_adjustment}")
        logger.info(f"   Feedback window: {self.feedback_window}")

    def set_components(
        self,
        dynamic_weight_adjuster=None,
        performance_monitor=None,
        market_analyzer=None,
    ):
        """Phase C2コンポーネント設定"""
        self.dynamic_weight_adjuster = dynamic_weight_adjuster
        self.performance_monitor = performance_monitor
        self.market_analyzer = market_analyzer

        logger.info("🔗 Feedback loop components connected")

    def start_learning_cycle(self):
        """継続的学習サイクル開始"""
        try:
            if self.learning_active:
                logger.warning("Learning cycle already active")
                return

            self.learning_active = True
            self.stop_learning.clear()

            self.learning_thread = threading.Thread(
                target=self._learning_loop, daemon=True, name="FeedbackLearning"
            )
            self.learning_thread.start()

            logger.info("🚀 Feedback learning cycle started")

        except Exception as e:
            logger.error(f"❌ Failed to start learning cycle: {e}")

    def stop_learning_cycle(self):
        """継続的学習サイクル停止"""
        try:
            if not self.learning_active:
                return

            self.stop_learning.set()
            self.learning_active = False

            if self.learning_thread and self.learning_thread.is_alive():
                self.learning_thread.join(timeout=10.0)

            logger.info("🛑 Feedback learning cycle stopped")

        except Exception as e:
            logger.error(f"❌ Failed to stop learning cycle: {e}")

    def _learning_loop(self):
        """学習メインループ"""
        try:
            logger.info("🧠 Feedback learning loop started")

            while not self.stop_learning.wait(self.analysis_interval):
                try:
                    if self.learning_enabled:
                        self._perform_learning_cycle()
                        self.feedback_stats["learning_cycles"] += 1

                except Exception as e:
                    logger.error(f"Learning cycle error: {e}")

            logger.info("🧠 Feedback learning loop ended")

        except Exception as e:
            logger.error(f"❌ Learning loop failed: {e}")

    def _perform_learning_cycle(self):
        """学習サイクル実行"""
        try:
            # 1. データ分析・インサイト生成
            insights = self._analyze_feedback_data()

            # 2. パターン発見・認識
            if self.pattern_detection_enabled:
                patterns = self._discover_patterns()
                insights.extend(patterns)

            # 3. 学習インサイト評価・フィルタリング
            validated_insights = self._validate_insights(insights)

            # 4. 自動パラメータ調整
            if self.auto_parameter_adjustment:
                adjustments = self._generate_parameter_adjustments(validated_insights)
                self._apply_parameter_adjustments(adjustments)

            # 5. インサイト記録
            for insight in validated_insights:
                self.learning_insights.append(insight)
                self.feedback_stats["insights_generated"] += 1

            if validated_insights:
                logger.info(f"🧠 Generated {len(validated_insights)} learning insights")

        except Exception as e:
            logger.error(f"Learning cycle execution failed: {e}")

    def record_prediction_feedback(
        self,
        timeframe: str,
        prediction: Any,
        actual_outcome: Any,
        confidence: float,
        market_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """予測フィードバック記録"""
        try:
            prediction_correct = prediction == actual_outcome

            event = FeedbackEvent(
                timestamp=datetime.now(),
                event_id=f"pred_{timeframe}_{datetime.now().timestamp()}",
                feedback_type=FeedbackType.PREDICTION_OUTCOME,
                timeframe=timeframe,
                prediction=prediction,
                actual_outcome=actual_outcome,
                confidence=confidence,
                prediction_correct=prediction_correct,
                market_context=market_context,
                metadata=metadata,
            )

            self._record_feedback_event(event)

            # 分析データ更新
            if prediction_correct:
                self.prediction_analysis[timeframe]["correct_predictions"].append(event)
            else:
                self.prediction_analysis[timeframe]["incorrect_predictions"].append(
                    event
                )

            self.prediction_analysis[timeframe]["confidence_scores"].append(confidence)
            if market_context:
                self.prediction_analysis[timeframe]["market_contexts"].append(
                    market_context
                )

            self.feedback_stats["prediction_events"] += 1

        except Exception as e:
            logger.error(f"Prediction feedback recording failed: {e}")

    def record_trade_feedback(
        self,
        timeframe: str,
        trade_id: str,
        entry_price: float,
        exit_price: float,
        pnl: float,
        market_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """取引フィードバック記録"""
        try:
            trade_successful = pnl > 0

            event = FeedbackEvent(
                timestamp=datetime.now(),
                event_id=f"trade_{timeframe}_{trade_id}",
                feedback_type=FeedbackType.TRADE_RESULT,
                timeframe=timeframe,
                trade_id=trade_id,
                entry_price=entry_price,
                exit_price=exit_price,
                pnl=pnl,
                trade_successful=trade_successful,
                market_context=market_context,
                metadata=metadata,
            )

            self._record_feedback_event(event)

            # 分析データ更新
            if trade_successful:
                self.trade_analysis[timeframe]["successful_trades"].append(event)
            else:
                self.trade_analysis[timeframe]["failed_trades"].append(event)

            self.trade_analysis[timeframe]["pnl_history"].append(pnl)

            self.feedback_stats["trade_events"] += 1

        except Exception as e:
            logger.error(f"Trade feedback recording failed: {e}")

    def record_parameter_adjustment(
        self,
        component_name: str,
        parameters_before: Dict[str, Any],
        parameters_after: Dict[str, Any],
        adjustment_reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """パラメータ調整フィードバック記録"""
        try:
            event = FeedbackEvent(
                timestamp=datetime.now(),
                event_id=f"param_{component_name}_{datetime.now().timestamp()}",
                feedback_type=FeedbackType.WEIGHT_ADJUSTMENT,
                timeframe="all",
                parameters_before=parameters_before,
                parameters_after=parameters_after,
                adjustment_reason=adjustment_reason,
                metadata=metadata,
            )

            self._record_feedback_event(event)
            self.parameter_history.append(event)

            self.feedback_stats["parameter_adjustments"] += 1

        except Exception as e:
            logger.error(f"Parameter adjustment recording failed: {e}")

    def _record_feedback_event(self, event: FeedbackEvent):
        """フィードバックイベント記録"""
        try:
            self.feedback_events.append(event)
            self.feedback_stats["total_events"] += 1

            # 永続化
            if self.enable_persistence:
                self._persist_feedback_event(event)

        except Exception as e:
            logger.error(f"Feedback event recording failed: {e}")

    def _analyze_feedback_data(self) -> List[LearningInsight]:
        """フィードバックデータ分析"""
        insights = []

        try:
            for timeframe in self.timeframes:
                # 予測精度分析
                prediction_insights = self._analyze_prediction_performance(timeframe)
                insights.extend(prediction_insights)

                # 取引成果分析
                trade_insights = self._analyze_trade_performance(timeframe)
                insights.extend(trade_insights)

                # 市場環境関連分析
                market_insights = self._analyze_market_context_patterns(timeframe)
                insights.extend(market_insights)

        except Exception as e:
            logger.error(f"Feedback data analysis failed: {e}")

        return insights

    def _analyze_prediction_performance(self, timeframe: str) -> List[LearningInsight]:
        """予測性能分析"""
        insights = []

        try:
            correct_preds = list(
                self.prediction_analysis[timeframe]["correct_predictions"]
            )
            incorrect_preds = list(
                self.prediction_analysis[timeframe]["incorrect_predictions"]
            )

            if (
                len(correct_preds) + len(incorrect_preds)
                < self.min_samples_for_learning
            ):
                return insights

            # 1. 信頼度vs正確性分析
            correct_confidences = [
                pred.confidence for pred in correct_preds if pred.confidence is not None
            ]
            incorrect_confidences = [
                pred.confidence
                for pred in incorrect_preds
                if pred.confidence is not None
            ]

            if len(correct_confidences) >= 10 and len(incorrect_confidences) >= 10:
                # t-検定による有意差分析
                t_stat, p_value = stats.ttest_ind(
                    correct_confidences, incorrect_confidences
                )

                if p_value < 0.05:
                    avg_correct_conf = np.mean(correct_confidences)
                    avg_incorrect_conf = np.mean(incorrect_confidences)

                    if avg_correct_conf > avg_incorrect_conf:
                        insight = LearningInsight(
                            insight_id=f"confidence_calibration_{timeframe}",
                            timestamp=datetime.now(),
                            insight_type="confidence_analysis",
                            confidence_level=1 - p_value,
                            description=f"{timeframe}: High confidence predictions are more accurate",
                            data_evidence={
                                "correct_confidence_avg": avg_correct_conf,
                                "incorrect_confidence_avg": avg_incorrect_conf,
                                "p_value": p_value,
                                "t_statistic": t_stat,
                            },
                            recommended_actions=[
                                "Increase confidence threshold for trading signals",
                                "Apply higher weights to high-confidence predictions",
                            ],
                            impact_assessment="high",
                        )
                        insights.append(insight)

            # 2. 最近のパフォーマンストレンド分析
            recent_correct = len(
                [
                    pred
                    for pred in correct_preds
                    if pred.timestamp > datetime.now() - timedelta(hours=24)
                ]
            )
            recent_total = len(
                [
                    pred
                    for pred in correct_preds + incorrect_preds
                    if pred.timestamp > datetime.now() - timedelta(hours=24)
                ]
            )

            if recent_total >= 20:
                recent_accuracy = recent_correct / recent_total

                # 全体平均と比較
                total_correct = len(correct_preds)
                total_all = len(correct_preds) + len(incorrect_preds)
                overall_accuracy = total_correct / total_all if total_all > 0 else 0

                if abs(recent_accuracy - overall_accuracy) > 0.1:  # 10%以上の差
                    trend_direction = (
                        "improving"
                        if recent_accuracy > overall_accuracy
                        else "declining"
                    )

                    insight = LearningInsight(
                        insight_id=f"accuracy_trend_{timeframe}",
                        timestamp=datetime.now(),
                        insight_type="performance_trend",
                        confidence_level=0.8,
                        description=(
                            f"{timeframe}: Prediction accuracy {trend_direction}"
                        ),
                        data_evidence={
                            "recent_accuracy": recent_accuracy,
                            "overall_accuracy": overall_accuracy,
                            "trend_direction": trend_direction,
                            "recent_samples": recent_total,
                        },
                        recommended_actions=[
                            ("Maintain" if trend_direction == "improving" else "Review")
                            + " current prediction strategy",
                            "Monitor prediction accuracy more closely",
                        ],
                        impact_assessment="medium",
                    )
                    insights.append(insight)

        except Exception as e:
            logger.error(f"Prediction performance analysis failed for {timeframe}: {e}")

        return insights

    def _analyze_trade_performance(self, timeframe: str) -> List[LearningInsight]:
        """取引成果分析"""
        insights = []

        try:
            successful_trades = list(
                self.trade_analysis[timeframe]["successful_trades"]
            )
            failed_trades = list(self.trade_analysis[timeframe]["failed_trades"])
            pnl_history = list(self.trade_analysis[timeframe]["pnl_history"])

            if len(successful_trades) + len(failed_trades) < 20:
                return insights

            # 1. PnL分布分析
            if len(pnl_history) >= 30:
                win_rate = len(successful_trades) / (
                    len(successful_trades) + len(failed_trades)
                )
                avg_win = np.mean([trade.pnl for trade in successful_trades])
                avg_loss = np.mean([trade.pnl for trade in failed_trades])

                # リスク・リワード比
                if avg_loss < 0:
                    risk_reward_ratio = abs(avg_win / avg_loss)

                    if win_rate < 0.5 and risk_reward_ratio < 1.5:
                        insight = LearningInsight(
                            insight_id=f"risk_reward_{timeframe}",
                            timestamp=datetime.now(),
                            insight_type="risk_analysis",
                            confidence_level=0.9,
                            description=f"{timeframe}: Poor risk-reward profile detected",
                            data_evidence={
                                "win_rate": win_rate,
                                "risk_reward_ratio": risk_reward_ratio,
                                "avg_win": avg_win,
                                "avg_loss": avg_loss,
                            },
                            recommended_actions=[
                                "Tighten stop-loss levels",
                                "Extend take-profit targets",
                                "Improve entry signal quality",
                            ],
                            impact_assessment="high",
                        )
                        insights.append(insight)

                # 2. 連続損失パターン分析
                consecutive_losses = 0
                max_consecutive_losses = 0

                for trade in list(reversed(failed_trades + successful_trades))[-50:]:
                    if not trade.trade_successful:
                        consecutive_losses += 1
                        max_consecutive_losses = max(
                            max_consecutive_losses, consecutive_losses
                        )
                    else:
                        consecutive_losses = 0

                if max_consecutive_losses >= 5:
                    insight = LearningInsight(
                        insight_id=f"consecutive_losses_{timeframe}",
                        timestamp=datetime.now(),
                        insight_type="risk_management",
                        confidence_level=0.85,
                        description=f"{timeframe}: High consecutive loss streaks detected",
                        data_evidence={
                            "max_consecutive_losses": max_consecutive_losses,
                            "current_streak": consecutive_losses,
                        },
                        recommended_actions=[
                            "Implement position sizing reduction after consecutive losses",
                            "Review entry signal criteria",
                            "Add market regime filters",
                        ],
                        impact_assessment="medium",
                    )
                    insights.append(insight)

        except Exception as e:
            logger.error(f"Trade performance analysis failed for {timeframe}: {e}")

        return insights

    def _analyze_market_context_patterns(self, timeframe: str) -> List[LearningInsight]:
        """市場環境パターン分析"""
        insights = []

        try:
            market_contexts = list(
                self.prediction_analysis[timeframe]["market_contexts"]
            )
            correct_preds = list(
                self.prediction_analysis[timeframe]["correct_predictions"]
            )

            if len(market_contexts) < 30:
                return insights

            # VIX レベル別パフォーマンス分析
            vix_performance = {"low": [], "medium": [], "high": []}

            for i, context in enumerate(market_contexts):
                if "vix_level" in context and i < len(correct_preds):
                    vix = context["vix_level"]
                    correct = correct_preds[i].prediction_correct

                    if vix < 20:
                        vix_performance["low"].append(correct)
                    elif vix < 30:
                        vix_performance["medium"].append(correct)
                    else:
                        vix_performance["high"].append(correct)

            # 各VIXレベルでの精度比較
            vix_accuracies = {}
            for level, results in vix_performance.items():
                if len(results) >= 10:
                    vix_accuracies[level] = np.mean(results)

            if len(vix_accuracies) >= 2:
                best_vix_level = max(vix_accuracies, key=vix_accuracies.get)
                worst_vix_level = min(vix_accuracies, key=vix_accuracies.get)

                if (
                    vix_accuracies[best_vix_level] - vix_accuracies[worst_vix_level]
                    > 0.15
                ):  # 15%以上の差
                    insight = LearningInsight(
                        insight_id=f"vix_performance_{timeframe}",
                        timestamp=datetime.now(),
                        insight_type="market_environment",
                        confidence_level=0.8,
                        description=f"{timeframe}: Performance varies significantly with VIX levels",
                        data_evidence={
                            "vix_accuracies": vix_accuracies,
                            "best_vix_level": best_vix_level,
                            "worst_vix_level": worst_vix_level,
                        },
                        recommended_actions=[
                            f"Increase confidence threshold during {worst_vix_level} VIX periods",
                            f"Optimize strategy parameters for {best_vix_level} VIX conditions",
                        ],
                        impact_assessment="medium",
                    )
                    insights.append(insight)

        except Exception as e:
            logger.error(f"Market context analysis failed for {timeframe}: {e}")

        return insights

    def _discover_patterns(self) -> List[LearningInsight]:
        """パターン発見"""
        insights = []

        try:
            # 時間帯別パフォーマンスパターン
            hourly_performance = self._analyze_hourly_patterns()
            if hourly_performance:
                insights.extend(hourly_performance)

            # 曜日別パフォーマンスパターン
            daily_performance = self._analyze_daily_patterns()
            if daily_performance:
                insights.extend(daily_performance)

            self.feedback_stats["patterns_discovered"] += len(insights)

        except Exception as e:
            logger.error(f"Pattern discovery failed: {e}")

        return insights

    def _analyze_hourly_patterns(self) -> List[LearningInsight]:
        """時間帯パターン分析"""
        insights = []

        try:
            # 過去のイベントから時間帯別成功率を計算
            hourly_success = defaultdict(list)

            recent_events = [
                e
                for e in self.feedback_events
                if e.timestamp > datetime.now() - timedelta(days=7)
            ]

            for event in recent_events:
                if (
                    event.feedback_type == FeedbackType.PREDICTION_OUTCOME
                    and event.prediction_correct is not None
                ):
                    hour = event.timestamp.hour
                    hourly_success[hour].append(event.prediction_correct)

            # 各時間帯の成功率計算
            hourly_rates = {}
            for hour, successes in hourly_success.items():
                if len(successes) >= self.pattern_min_occurrences:
                    hourly_rates[hour] = np.mean(successes)

            if len(hourly_rates) >= 6:  # 最低6時間のデータが必要
                best_hours = sorted(
                    hourly_rates.items(), key=lambda x: x[1], reverse=True
                )[:3]
                worst_hours = sorted(hourly_rates.items(), key=lambda x: x[1])[:3]

                best_rate = np.mean([rate for _, rate in best_hours])
                worst_rate = np.mean([rate for _, rate in worst_hours])

                if best_rate - worst_rate > 0.2:  # 20%以上の差
                    insight = LearningInsight(
                        insight_id="hourly_performance_pattern",
                        timestamp=datetime.now(),
                        insight_type="temporal_pattern",
                        confidence_level=0.75,
                        description="Significant hourly performance variation detected",
                        data_evidence={
                            "best_hours": dict(best_hours),
                            "worst_hours": dict(worst_hours),
                            "performance_gap": best_rate - worst_rate,
                        },
                        recommended_actions=[
                            f"Increase trading activity during hours: {[h for h, _ in best_hours]}",
                            f"Reduce or avoid trading during hours: {[h for h, _ in worst_hours]}",
                        ],
                        impact_assessment="medium",
                    )
                    insights.append(insight)

        except Exception as e:
            logger.error(f"Hourly pattern analysis failed: {e}")

        return insights

    def _analyze_daily_patterns(self) -> List[LearningInsight]:
        """曜日パターン分析"""
        insights = []

        try:
            # 曜日別成功率分析
            daily_success = defaultdict(list)

            recent_events = [
                e
                for e in self.feedback_events
                if e.timestamp > datetime.now() - timedelta(days=30)
            ]

            for event in recent_events:
                if (
                    event.feedback_type == FeedbackType.TRADE_RESULT
                    and event.trade_successful is not None
                ):
                    weekday = event.timestamp.weekday()  # 0=月曜日
                    daily_success[weekday].append(event.trade_successful)

            # 各曜日の成功率計算
            daily_rates = {}
            weekday_names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]

            for day, successes in daily_success.items():
                if len(successes) >= self.pattern_min_occurrences:
                    daily_rates[weekday_names[day]] = np.mean(successes)

            if len(daily_rates) >= 5:  # 平日データが必要
                best_day = max(daily_rates, key=daily_rates.get)
                worst_day = min(daily_rates, key=daily_rates.get)

                if daily_rates[best_day] - daily_rates[worst_day] > 0.15:  # 15%以上の差
                    insight = LearningInsight(
                        insight_id="daily_performance_pattern",
                        timestamp=datetime.now(),
                        insight_type="temporal_pattern",
                        confidence_level=0.7,
                        description="Significant daily performance variation detected",
                        data_evidence={
                            "daily_rates": daily_rates,
                            "best_day": best_day,
                            "worst_day": worst_day,
                        },
                        recommended_actions=[
                            f"Optimize strategy for {best_day} trading",
                            f"Review strategy performance on {worst_day}",
                        ],
                        impact_assessment="low",
                    )
                    insights.append(insight)

        except Exception as e:
            logger.error(f"Daily pattern analysis failed: {e}")

        return insights

    def _validate_insights(
        self, insights: List[LearningInsight]
    ) -> List[LearningInsight]:
        """インサイト検証・フィルタリング"""
        validated = []

        try:
            for insight in insights:
                # 信頼度閾値チェック
                if insight.confidence_level >= self.insight_confidence_threshold:

                    # 重複チェック
                    existing_ids = [
                        existing.insight_id for existing in self.learning_insights
                    ]
                    if insight.insight_id not in existing_ids:
                        validated.append(insight)

        except Exception as e:
            logger.error(f"Insight validation failed: {e}")

        return validated

    def _generate_parameter_adjustments(
        self, insights: List[LearningInsight]
    ) -> List[Dict[str, Any]]:
        """パラメータ調整生成"""
        adjustments = []

        try:
            for insight in insights:
                if insight.impact_assessment in ["high", "medium"]:

                    # インサイト別調整戦略
                    if insight.insight_type == "confidence_analysis":
                        # 信頼度閾値調整
                        adjustment = {
                            "component": "ensemble_confidence",
                            "parameter": "confidence_threshold",
                            "current_value": 0.65,
                            "adjustment_factor": 1.1,
                            "reason": f"Confidence calibration insight: {insight.insight_id}",
                        }
                        adjustments.append(adjustment)

                    elif insight.insight_type == "risk_analysis":
                        # リスク管理パラメータ調整
                        adjustment = {
                            "component": "risk_management",
                            "parameter": "position_sizing",
                            "current_value": 1.0,
                            "adjustment_factor": 0.9,
                            "reason": f"Risk analysis insight: {insight.insight_id}",
                        }
                        adjustments.append(adjustment)

                    elif insight.insight_type == "market_environment":
                        # 市場環境重み調整
                        adjustment = {
                            "component": "market_weights",
                            "parameter": "vix_sensitivity",
                            "current_value": 1.0,
                            "adjustment_factor": 1.2,
                            "reason": f"Market environment insight: {insight.insight_id}",
                        }
                        adjustments.append(adjustment)

        except Exception as e:
            logger.error(f"Parameter adjustment generation failed: {e}")

        return adjustments

    def _apply_parameter_adjustments(self, adjustments: List[Dict[str, Any]]):
        """パラメータ調整適用"""
        try:
            for adjustment in adjustments:
                # 調整幅制限
                factor = adjustment["adjustment_factor"]
                limited_factor = max(
                    1 - self.max_parameter_change,
                    min(1 + self.max_parameter_change, factor),
                )

                # コンポーネント別調整適用
                component = adjustment["component"]
                success = False

                if (
                    component == "dynamic_weight_adjuster"
                    and self.dynamic_weight_adjuster
                ):
                    # 動的重み調整器パラメータ更新
                    success = self._update_weight_adjuster_parameters(
                        adjustment, limited_factor
                    )

                elif component == "performance_monitor" and self.performance_monitor:
                    # 性能監視システムパラメータ更新
                    success = self._update_monitor_parameters(
                        adjustment, limited_factor
                    )

                if success:
                    self.feedback_stats["automatic_improvements"] += 1
                    logger.info(
                        f"✅ Applied parameter adjustment: {adjustment['reason']}"
                    )

        except Exception as e:
            logger.error(f"Parameter adjustment application failed: {e}")

    def _update_weight_adjuster_parameters(
        self, adjustment: Dict[str, Any], factor: float
    ) -> bool:
        """重み調整器パラメータ更新"""
        try:
            # パラメータ更新ロジック（実装は具体的なパラメータに依存）
            # ここでは例として学習率を調整
            if hasattr(self.dynamic_weight_adjuster, "learning_rate"):
                old_value = self.dynamic_weight_adjuster.learning_rate
                new_value = old_value * factor
                self.dynamic_weight_adjuster.learning_rate = new_value

                logger.info(
                    f"🔧 Updated learning_rate: {old_value:.4f} → {new_value:.4f}"
                )
                return True

        except Exception as e:
            logger.error(f"Weight adjuster parameter update failed: {e}")

        return False

    def _update_monitor_parameters(
        self, adjustment: Dict[str, Any], factor: float
    ) -> bool:
        """監視システムパラメータ更新"""
        try:
            # パラメータ更新ロジック（実装は具体的なパラメータに依存）
            # ここでは例として閾値を調整
            if hasattr(self.performance_monitor, "accuracy_threshold"):
                old_value = self.performance_monitor.accuracy_threshold
                new_value = old_value * factor
                self.performance_monitor.accuracy_threshold = new_value

                logger.info(
                    f"🔧 Updated accuracy_threshold: {old_value:.4f} → {new_value:.4f}"
                )
                return True

        except Exception as e:
            logger.error(f"Monitor parameter update failed: {e}")

        return False

    def _persist_feedback_event(self, event: FeedbackEvent):
        """フィードバックイベント永続化"""
        try:
            if not os.path.exists(self.persistence_path):
                os.makedirs(self.persistence_path)

            # 日付別ファイル保存
            date_str = event.timestamp.strftime("%Y%m%d")
            file_path = os.path.join(self.persistence_path, f"feedback_{date_str}.pkl")

            # 既存データ読み込み
            daily_events = []
            if os.path.exists(file_path):
                try:
                    with open(file_path, "rb") as f:
                        daily_events = pickle.load(f)
                except Exception:
                    daily_events = []

            # 新イベント追加・保存
            daily_events.append(asdict(event))
            with open(file_path, "wb") as f:
                pickle.dump(daily_events, f)

        except Exception as e:
            logger.error(f"Feedback event persistence failed: {e}")

    def get_learning_summary(self) -> Dict[str, Any]:
        """学習サマリー取得"""
        try:
            summary = {
                "timestamp": datetime.now(),
                "learning_active": self.learning_active,
                "feedback_stats": self.feedback_stats.copy(),
            }

            # 最近のインサイト
            recent_insights = list(self.learning_insights)[-10:]
            summary["recent_insights"] = [
                {
                    "insight_id": insight.insight_id,
                    "timestamp": insight.timestamp.isoformat(),
                    "insight_type": insight.insight_type,
                    "confidence_level": insight.confidence_level,
                    "description": insight.description,
                    "impact_assessment": insight.impact_assessment,
                }
                for insight in recent_insights
            ]

            # タイムフレーム別統計
            timeframe_stats = {}
            for timeframe in self.timeframes:
                correct_count = len(
                    self.prediction_analysis[timeframe]["correct_predictions"]
                )
                incorrect_count = len(
                    self.prediction_analysis[timeframe]["incorrect_predictions"]
                )
                total_predictions = correct_count + incorrect_count

                successful_trades = len(
                    self.trade_analysis[timeframe]["successful_trades"]
                )
                failed_trades = len(self.trade_analysis[timeframe]["failed_trades"])
                total_trades = successful_trades + failed_trades

                timeframe_stats[timeframe] = {
                    "prediction_accuracy": (
                        correct_count / total_predictions
                        if total_predictions > 0
                        else 0
                    ),
                    "total_predictions": total_predictions,
                    "trade_win_rate": (
                        successful_trades / total_trades if total_trades > 0 else 0
                    ),
                    "total_trades": total_trades,
                }

            summary["timeframe_statistics"] = timeframe_stats

            return summary

        except Exception as e:
            logger.error(f"Learning summary generation failed: {e}")
            return {"error": str(e)}

    def add_parameter_update_callback(self, callback: Callable):
        """パラメータ更新コールバック追加"""
        self.parameter_update_callbacks.append(callback)

    def reset_statistics(self):
        """統計リセット"""
        try:
            # 統計リセット
            for key in self.feedback_stats:
                self.feedback_stats[key] = 0

            # データクリア
            self.feedback_events.clear()
            self.learning_insights.clear()
            self.parameter_history.clear()

            for timeframe in self.timeframes:
                for category in self.prediction_analysis[timeframe]:
                    self.prediction_analysis[timeframe][category].clear()
                for category in self.trade_analysis[timeframe]:
                    self.trade_analysis[timeframe][category].clear()

            logger.info("📊 Feedback loop manager statistics reset")

        except Exception as e:
            logger.error(f"Statistics reset failed: {e}")


# ファクトリー関数


def create_feedback_loop_manager(config: Dict[str, Any]) -> FeedbackLoopManager:
    """
    フィードバックループ管理システム作成

    Parameters:
    -----------
    config : Dict[str, Any]
        設定辞書

    Returns:
    --------
    FeedbackLoopManager
        初期化済みフィードバックループ管理システム
    """
    return FeedbackLoopManager(config)
