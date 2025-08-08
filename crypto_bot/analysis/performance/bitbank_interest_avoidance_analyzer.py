"""
Bitbank金利回避効果分析システム
金利節約効果計算・ROI改善測定・統計レポート生成
"""

import logging
import math
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class InterestCalculationMethod(Enum):
    """金利計算方法"""

    SIMPLE = "simple"  # 単利計算
    COMPOUND = "compound"  # 複利計算
    DAILY = "daily"  # 日次計算
    CONTINUOUS = "continuous"  # 継続計算


class ComparisonPeriod(Enum):
    """比較期間"""

    DAILY = "daily"  # 日次比較
    WEEKLY = "weekly"  # 週次比較
    MONTHLY = "monthly"  # 月次比較
    QUARTERLY = "quarterly"  # 四半期比較
    YEARLY = "yearly"  # 年次比較


@dataclass
class InterestSavingRecord:
    """金利節約記録"""

    timestamp: datetime
    symbol: str
    position_id: str
    position_size: float
    position_value: float
    holding_time_hours: float
    interest_rate: float
    avoided_interest: float
    total_profit: float
    net_profit: float
    roi_improvement: float
    avoidance_method: str
    market_phase: str


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""

    total_trades: int = 0
    total_avoided_interest: float = 0.0
    total_profit: float = 0.0
    total_net_profit: float = 0.0
    average_holding_time: float = 0.0
    average_roi_improvement: float = 0.0
    success_rate: float = 0.0
    interest_avoidance_rate: float = 0.0

    # 比較指標
    hypothetical_with_interest: float = 0.0
    actual_without_interest: float = 0.0
    improvement_percentage: float = 0.0

    # リスク指標
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    profit_factor: float = 0.0


@dataclass
class InterestAvoidanceReport:
    """金利回避レポート"""

    period_start: datetime
    period_end: datetime
    total_savings: float
    average_daily_savings: float
    roi_improvement: float
    positions_analyzed: int
    avoidance_success_rate: float

    # 詳細分析
    by_symbol: Dict[str, PerformanceMetrics]
    by_time_period: Dict[str, PerformanceMetrics]
    by_strategy: Dict[str, PerformanceMetrics]

    # 統計情報
    statistical_analysis: Dict[str, Any]
    recommendations: List[str]


class BitbankInterestAvoidanceAnalyzer:
    """
    Bitbank金利回避効果分析システム

    金利節約効果計算・ROI改善測定・統計レポート生成の統合システム
    """

    def __init__(self, config: Optional[Dict] = None):

        self.config = config or {}

        # 分析設定
        analyzer_config = self.config.get("interest_avoidance_analyzer", {})
        self.daily_interest_rate = analyzer_config.get(
            "daily_interest_rate", 0.0004
        )  # 0.04%
        self.calculation_method = InterestCalculationMethod(
            analyzer_config.get("calculation_method", "daily")
        )
        self.analysis_window_days = analyzer_config.get("analysis_window_days", 30)
        self.benchmark_periods = analyzer_config.get(
            "benchmark_periods", ["daily", "weekly", "monthly"]
        )

        # データ保存
        self.saving_records: List[InterestSavingRecord] = []
        self.performance_history: Dict[str, List[PerformanceMetrics]] = defaultdict(
            list
        )

        # 分析キャッシュ
        self.analysis_cache: Dict[str, Any] = {}
        self.last_analysis_time: Optional[datetime] = None

        # 統計計算用
        self.rolling_windows = {
            "daily": deque(maxlen=30),
            "weekly": deque(maxlen=12),
            "monthly": deque(maxlen=6),
        }

        # ベンチマーク設定
        self.benchmark_scenarios = {
            "no_avoidance": {
                "description": "金利回避なし",
                "interest_rate": self.daily_interest_rate,
                "holding_time_multiplier": 1.0,
            },
            "partial_avoidance": {
                "description": "部分的回避",
                "interest_rate": self.daily_interest_rate * 0.5,
                "holding_time_multiplier": 0.7,
            },
            "full_avoidance": {
                "description": "完全回避",
                "interest_rate": 0.0,
                "holding_time_multiplier": 0.8,
            },
        }

        logger.info("BitbankInterestAvoidanceAnalyzer initialized")
        logger.info(f"Daily interest rate: {self.daily_interest_rate:.4f}")
        logger.info(f"Analysis window: {self.analysis_window_days} days")

    def record_position_closure(
        self,
        position_id: str,
        symbol: str,
        position_size: float,
        position_value: float,
        entry_time: datetime,
        exit_time: datetime,
        total_profit: float,
        fees_paid: float,
        avoidance_method: str,
        market_phase: str = "unknown",
    ) -> InterestSavingRecord:
        """
        ポジション決済記録・金利回避効果計算

        Args:
            position_id: ポジションID
            symbol: 通貨ペア
            position_size: ポジションサイズ
            position_value: ポジション価値
            entry_time: 開始時刻
            exit_time: 終了時刻
            total_profit: 総利益
            fees_paid: 手数料
            avoidance_method: 回避方法
            market_phase: 市場フェーズ

        Returns:
            金利節約記録
        """
        # 保有時間計算
        holding_time = (exit_time - entry_time).total_seconds() / 3600  # 時間単位

        # 金利回避効果計算
        avoided_interest = self.calculate_avoided_interest(
            position_value, holding_time, self.daily_interest_rate
        )

        # 実質利益計算
        net_profit = total_profit - fees_paid

        # ROI改善計算
        roi_improvement = self.calculate_roi_improvement(
            position_value, net_profit, avoided_interest
        )

        # 記録作成
        record = InterestSavingRecord(
            timestamp=exit_time,
            symbol=symbol,
            position_id=position_id,
            position_size=position_size,
            position_value=position_value,
            holding_time_hours=holding_time,
            interest_rate=self.daily_interest_rate,
            avoided_interest=avoided_interest,
            total_profit=total_profit,
            net_profit=net_profit,
            roi_improvement=roi_improvement,
            avoidance_method=avoidance_method,
            market_phase=market_phase,
        )

        # 記録保存
        self.saving_records.append(record)

        # 記録数制限
        if len(self.saving_records) > 10000:
            self.saving_records = self.saving_records[-5000:]

        # 統計更新
        self._update_rolling_statistics(record)

        logger.info(f"Interest avoidance recorded: {position_id}")
        logger.info(
            f"Avoided interest: {avoided_interest:.6f}, "
            f"ROI improvement: {roi_improvement:.4f}"
        )

        return record

    def calculate_avoided_interest(
        self, position_value: float, holding_time_hours: float, daily_rate: float
    ) -> float:
        """
        金利回避額計算

        Args:
            position_value: ポジション価値
            holding_time_hours: 保有時間（時間）
            daily_rate: 日次金利率

        Returns:
            回避した金利額
        """
        if self.calculation_method == InterestCalculationMethod.SIMPLE:
            # 単利計算
            daily_interest = position_value * daily_rate
            avoided_interest = daily_interest * (holding_time_hours / 24)

        elif self.calculation_method == InterestCalculationMethod.COMPOUND:
            # 複利計算
            days = holding_time_hours / 24
            compound_factor = (1 + daily_rate) ** days
            avoided_interest = position_value * (compound_factor - 1)

        elif self.calculation_method == InterestCalculationMethod.DAILY:
            # 日次計算（日をまたぐ場合のみ）
            if holding_time_hours > 24:
                full_days = int(holding_time_hours / 24)
                avoided_interest = position_value * daily_rate * full_days
            else:
                avoided_interest = 0.0

        elif self.calculation_method == InterestCalculationMethod.CONTINUOUS:
            # 継続計算
            annual_rate = daily_rate * 365
            avoided_interest = position_value * (
                math.exp(annual_rate * holding_time_hours / 8760) - 1
            )

        else:
            # デフォルト: 単利計算
            daily_interest = position_value * daily_rate
            avoided_interest = daily_interest * (holding_time_hours / 24)

        return max(0.0, avoided_interest)

    def calculate_roi_improvement(
        self, position_value: float, net_profit: float, avoided_interest: float
    ) -> float:
        """
        ROI改善計算

        Args:
            position_value: ポジション価値
            net_profit: 実質利益
            avoided_interest: 回避した金利

        Returns:
            ROI改善率
        """
        if position_value <= 0:
            return 0.0

        # 金利回避なしの場合のROI
        roi_without_avoidance = (net_profit - avoided_interest) / position_value

        # 金利回避ありの場合のROI
        roi_with_avoidance = net_profit / position_value

        # 改善率計算
        roi_improvement = roi_with_avoidance - roi_without_avoidance

        return roi_improvement

    def _update_rolling_statistics(self, record: InterestSavingRecord) -> None:
        """ローリング統計更新"""
        # 日次統計
        daily_data = {
            "timestamp": record.timestamp,
            "avoided_interest": record.avoided_interest,
            "roi_improvement": record.roi_improvement,
            "net_profit": record.net_profit,
        }
        self.rolling_windows["daily"].append(daily_data)

        # 週次統計（日曜日に更新）
        if record.timestamp.weekday() == 6:  # 日曜日
            weekly_avg = self._calculate_period_average("daily", 7)
            self.rolling_windows["weekly"].append(weekly_avg)

        # 月次統計（月末に更新）
        if record.timestamp.day == 1:  # 月初
            monthly_avg = self._calculate_period_average("daily", 30)
            self.rolling_windows["monthly"].append(monthly_avg)

    def _calculate_period_average(
        self, source_window: str, days: int
    ) -> Dict[str, Any]:
        """期間平均計算"""
        window_data = list(self.rolling_windows[source_window])
        if len(window_data) < days:
            recent_data = window_data
        else:
            recent_data = window_data[-days:]

        if not recent_data:
            return {
                "timestamp": datetime.now(),
                "avoided_interest": 0.0,
                "roi_improvement": 0.0,
                "net_profit": 0.0,
            }

        return {
            "timestamp": recent_data[-1]["timestamp"],
            "avoided_interest": sum(d["avoided_interest"] for d in recent_data)
            / len(recent_data),
            "roi_improvement": sum(d["roi_improvement"] for d in recent_data)
            / len(recent_data),
            "net_profit": sum(d["net_profit"] for d in recent_data) / len(recent_data),
        }

    def generate_performance_metrics(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> PerformanceMetrics:
        """
        パフォーマンス指標生成

        Args:
            period_start: 開始時刻
            period_end: 終了時刻

        Returns:
            パフォーマンス指標
        """
        # 期間設定
        if period_end is None:
            period_end = datetime.now()
        if period_start is None:
            period_start = period_end - timedelta(days=self.analysis_window_days)

        # 期間内のレコードフィルター
        period_records = [
            r for r in self.saving_records if period_start <= r.timestamp <= period_end
        ]

        if not period_records:
            return PerformanceMetrics()

        # 基本統計
        total_trades = len(period_records)
        total_avoided_interest = sum(r.avoided_interest for r in period_records)
        total_profit = sum(r.total_profit for r in period_records)
        total_net_profit = sum(r.net_profit for r in period_records)

        # 平均値計算
        average_holding_time = (
            sum(r.holding_time_hours for r in period_records) / total_trades
        )
        average_roi_improvement = (
            sum(r.roi_improvement for r in period_records) / total_trades
        )

        # 成功率計算
        profitable_trades = sum(1 for r in period_records if r.net_profit > 0)
        success_rate = profitable_trades / total_trades

        # 金利回避率計算
        avoided_trades = sum(1 for r in period_records if r.avoided_interest > 0)
        interest_avoidance_rate = avoided_trades / total_trades

        # 比較指標計算
        hypothetical_with_interest = self._calculate_hypothetical_performance(
            period_records, include_interest=True
        )
        actual_without_interest = total_net_profit

        if hypothetical_with_interest != 0:
            improvement_percentage = (
                (actual_without_interest - hypothetical_with_interest)
                / abs(hypothetical_with_interest)
                * 100
            )
        else:
            improvement_percentage = 0.0

        # リスク指標計算
        max_drawdown = self._calculate_max_drawdown(period_records)
        sharpe_ratio = self._calculate_sharpe_ratio(period_records)
        profit_factor = self._calculate_profit_factor(period_records)

        return PerformanceMetrics(
            total_trades=total_trades,
            total_avoided_interest=total_avoided_interest,
            total_profit=total_profit,
            total_net_profit=total_net_profit,
            average_holding_time=average_holding_time,
            average_roi_improvement=average_roi_improvement,
            success_rate=success_rate,
            interest_avoidance_rate=interest_avoidance_rate,
            hypothetical_with_interest=hypothetical_with_interest,
            actual_without_interest=actual_without_interest,
            improvement_percentage=improvement_percentage,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor,
        )

    def _calculate_hypothetical_performance(
        self, records: List[InterestSavingRecord], include_interest: bool = True
    ) -> float:
        """仮想パフォーマンス計算"""
        total_performance = 0.0

        for record in records:
            if include_interest:
                # 金利を含む場合
                performance = record.net_profit - record.avoided_interest
            else:
                # 金利を含まない場合
                performance = record.net_profit

            total_performance += performance

        return total_performance

    def _calculate_max_drawdown(self, records: List[InterestSavingRecord]) -> float:
        """最大ドローダウン計算"""
        if not records:
            return 0.0

        cumulative_profit = 0.0
        peak_profit = 0.0
        max_drawdown = 0.0

        for record in sorted(records, key=lambda x: x.timestamp):
            cumulative_profit += record.net_profit

            if cumulative_profit > peak_profit:
                peak_profit = cumulative_profit

            drawdown = (peak_profit - cumulative_profit) / max(peak_profit, 1)
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def _calculate_sharpe_ratio(self, records: List[InterestSavingRecord]) -> float:
        """シャープレシオ計算"""
        if len(records) < 2:
            return 0.0

        returns = [r.net_profit / max(r.position_value, 1) for r in records]

        if not returns:
            return 0.0

        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.0

        if std_return == 0:
            return 0.0

        # リスクフリーレート（簡易版）
        risk_free_rate = 0.001  # 0.1%

        return (avg_return - risk_free_rate) / std_return

    def _calculate_profit_factor(self, records: List[InterestSavingRecord]) -> float:
        """プロフィットファクター計算"""
        if not records:
            return 0.0

        total_profit = sum(r.net_profit for r in records if r.net_profit > 0)
        total_loss = abs(sum(r.net_profit for r in records if r.net_profit < 0))

        if total_loss == 0:
            return float("inf") if total_profit > 0 else 0.0

        return total_profit / total_loss

    def generate_comprehensive_report(
        self,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
    ) -> InterestAvoidanceReport:
        """
        包括的レポート生成

        Args:
            period_start: 開始時刻
            period_end: 終了時刻

        Returns:
            金利回避レポート
        """
        # 期間設定
        if period_end is None:
            period_end = datetime.now()
        if period_start is None:
            period_start = period_end - timedelta(days=self.analysis_window_days)

        # 期間内のレコードフィルター
        period_records = [
            r for r in self.saving_records if period_start <= r.timestamp <= period_end
        ]

        if not period_records:
            return InterestAvoidanceReport(
                period_start=period_start,
                period_end=period_end,
                total_savings=0.0,
                average_daily_savings=0.0,
                roi_improvement=0.0,
                positions_analyzed=0,
                avoidance_success_rate=0.0,
                by_symbol={},
                by_time_period={},
                by_strategy={},
                statistical_analysis={},
                recommendations=["データが不足しています"],
            )

        # 基本統計
        total_savings = sum(r.avoided_interest for r in period_records)
        period_days = (period_end - period_start).days
        average_daily_savings = total_savings / max(period_days, 1)

        overall_roi_improvement = sum(r.roi_improvement for r in period_records) / len(
            period_records
        )
        positions_analyzed = len(period_records)

        successful_avoidances = sum(1 for r in period_records if r.avoided_interest > 0)
        avoidance_success_rate = successful_avoidances / positions_analyzed

        # 通貨ペア別分析
        by_symbol = self._analyze_by_dimension(period_records, "symbol")

        # 時間帯別分析
        by_time_period = self._analyze_by_time_period(period_records)

        # 戦略別分析
        by_strategy = self._analyze_by_dimension(period_records, "avoidance_method")

        # 統計分析
        statistical_analysis = self._perform_statistical_analysis(period_records)

        # 推奨事項生成
        recommendations = self._generate_recommendations(
            period_records, statistical_analysis
        )

        return InterestAvoidanceReport(
            period_start=period_start,
            period_end=period_end,
            total_savings=total_savings,
            average_daily_savings=average_daily_savings,
            roi_improvement=overall_roi_improvement,
            positions_analyzed=positions_analyzed,
            avoidance_success_rate=avoidance_success_rate,
            by_symbol=by_symbol,
            by_time_period=by_time_period,
            by_strategy=by_strategy,
            statistical_analysis=statistical_analysis,
            recommendations=recommendations,
        )

    def _analyze_by_dimension(
        self, records: List[InterestSavingRecord], dimension: str
    ) -> Dict[str, PerformanceMetrics]:
        """次元別分析"""
        dimension_groups = defaultdict(list)

        for record in records:
            key = getattr(record, dimension)
            dimension_groups[key].append(record)

        dimension_metrics = {}

        for key, group_records in dimension_groups.items():
            if not group_records:
                continue

            # 基本統計
            total_trades = len(group_records)
            total_avoided_interest = sum(r.avoided_interest for r in group_records)
            total_profit = sum(r.total_profit for r in group_records)
            total_net_profit = sum(r.net_profit for r in group_records)

            # 平均値
            average_holding_time = (
                sum(r.holding_time_hours for r in group_records) / total_trades
            )
            average_roi_improvement = (
                sum(r.roi_improvement for r in group_records) / total_trades
            )

            # 成功率
            profitable_trades = sum(1 for r in group_records if r.net_profit > 0)
            success_rate = profitable_trades / total_trades

            # 金利回避率
            avoided_trades = sum(1 for r in group_records if r.avoided_interest > 0)
            interest_avoidance_rate = avoided_trades / total_trades

            dimension_metrics[key] = PerformanceMetrics(
                total_trades=total_trades,
                total_avoided_interest=total_avoided_interest,
                total_profit=total_profit,
                total_net_profit=total_net_profit,
                average_holding_time=average_holding_time,
                average_roi_improvement=average_roi_improvement,
                success_rate=success_rate,
                interest_avoidance_rate=interest_avoidance_rate,
            )

        return dimension_metrics

    def _analyze_by_time_period(
        self, records: List[InterestSavingRecord]
    ) -> Dict[str, PerformanceMetrics]:
        """時間帯別分析"""
        time_groups = defaultdict(list)

        for record in records:
            hour = record.timestamp.hour

            if 9 <= hour < 12:
                time_period = "morning"
            elif 12 <= hour < 15:
                time_period = "afternoon"
            elif 15 <= hour < 18:
                time_period = "evening"
            elif 18 <= hour < 21:
                time_period = "night"
            else:
                time_period = "off_hours"

            time_groups[time_period].append(record)

        return self._analyze_by_dimension_groups(time_groups)

    def _analyze_by_dimension_groups(
        self, groups: Dict[str, List[InterestSavingRecord]]
    ) -> Dict[str, PerformanceMetrics]:
        """グループ別分析"""
        metrics = {}

        for key, group_records in groups.items():
            if not group_records:
                continue

            # 基本統計計算
            total_trades = len(group_records)
            total_avoided_interest = sum(r.avoided_interest for r in group_records)
            total_net_profit = sum(r.net_profit for r in group_records)

            # 平均値計算
            average_holding_time = (
                sum(r.holding_time_hours for r in group_records) / total_trades
            )
            average_roi_improvement = (
                sum(r.roi_improvement for r in group_records) / total_trades
            )

            # 成功率計算
            profitable_trades = sum(1 for r in group_records if r.net_profit > 0)
            success_rate = profitable_trades / total_trades

            # 金利回避率計算
            avoided_trades = sum(1 for r in group_records if r.avoided_interest > 0)
            interest_avoidance_rate = avoided_trades / total_trades

            metrics[key] = PerformanceMetrics(
                total_trades=total_trades,
                total_avoided_interest=total_avoided_interest,
                total_net_profit=total_net_profit,
                average_holding_time=average_holding_time,
                average_roi_improvement=average_roi_improvement,
                success_rate=success_rate,
                interest_avoidance_rate=interest_avoidance_rate,
            )

        return metrics

    def _perform_statistical_analysis(
        self, records: List[InterestSavingRecord]
    ) -> Dict[str, Any]:
        """統計分析実行"""
        if not records:
            return {}

        # 基本統計
        avoided_interests = [r.avoided_interest for r in records]
        roi_improvements = [r.roi_improvement for r in records]
        holding_times = [r.holding_time_hours for r in records]
        net_profits = [r.net_profit for r in records]

        analysis = {
            "avoided_interest": {
                "mean": statistics.mean(avoided_interests),
                "median": statistics.median(avoided_interests),
                "std": (
                    statistics.stdev(avoided_interests)
                    if len(avoided_interests) > 1
                    else 0
                ),
                "min": min(avoided_interests),
                "max": max(avoided_interests),
                "total": sum(avoided_interests),
            },
            "roi_improvement": {
                "mean": statistics.mean(roi_improvements),
                "median": statistics.median(roi_improvements),
                "std": (
                    statistics.stdev(roi_improvements)
                    if len(roi_improvements) > 1
                    else 0
                ),
                "min": min(roi_improvements),
                "max": max(roi_improvements),
            },
            "holding_time": {
                "mean": statistics.mean(holding_times),
                "median": statistics.median(holding_times),
                "std": statistics.stdev(holding_times) if len(holding_times) > 1 else 0,
                "min": min(holding_times),
                "max": max(holding_times),
            },
            "net_profit": {
                "mean": statistics.mean(net_profits),
                "median": statistics.median(net_profits),
                "std": statistics.stdev(net_profits) if len(net_profits) > 1 else 0,
                "min": min(net_profits),
                "max": max(net_profits),
                "total": sum(net_profits),
            },
        }

        # 相関分析
        if len(records) > 10:
            analysis["correlations"] = {
                "avoided_interest_vs_roi": np.corrcoef(
                    avoided_interests, roi_improvements
                )[0, 1],
                "holding_time_vs_avoided_interest": np.corrcoef(
                    holding_times, avoided_interests
                )[0, 1],
                "holding_time_vs_profit": np.corrcoef(holding_times, net_profits)[0, 1],
            }

        # 効率性分析
        total_avoided = sum(avoided_interests)
        total_profit = sum(net_profits)

        if total_profit != 0:
            analysis["efficiency"] = {
                "interest_to_profit_ratio": total_avoided / total_profit,
                "average_avoidance_per_trade": total_avoided / len(records),
                "avoidance_efficiency": total_avoided
                / sum(r.position_value for r in records),
            }

        return analysis

    def _generate_recommendations(
        self, records: List[InterestSavingRecord], analysis: Dict[str, Any]
    ) -> List[str]:
        """推奨事項生成"""
        recommendations = []

        if not records:
            return [
                "データが不足しています。取引を行って分析データを蓄積してください。"
            ]

        # 金利回避効果の評価
        total_avoided = sum(r.avoided_interest for r in records)
        total_profit = sum(r.net_profit for r in records)

        if total_avoided > 0:
            avoidance_ratio = total_avoided / max(abs(total_profit), 1)

            if avoidance_ratio > 0.1:
                recommendations.append(
                    f"優秀な金利回避効果です。総利益の{avoidance_ratio:.1%}に相当する金利を回避しています。"
                )
            elif avoidance_ratio > 0.05:
                recommendations.append(
                    "適度な金利回避効果です。さらなる改善の余地があります。"
                )
            else:
                recommendations.append(
                    "金利回避効果が限定的です。保有時間の短縮を検討してください。"
                )

        # 保有時間の分析
        avg_holding_time = sum(r.holding_time_hours for r in records) / len(records)

        if avg_holding_time > 20:
            recommendations.append(
                "平均保有時間が長すぎます。デイトレード戦略の見直しが必要です。"
            )
        elif avg_holding_time > 12:
            recommendations.append(
                "保有時間を短縮することで、金利回避効果が向上します。"
            )
        else:
            recommendations.append("適切な保有時間を維持しています。")

        # 成功率の分析
        successful_trades = sum(1 for r in records if r.net_profit > 0)
        success_rate = successful_trades / len(records)

        if success_rate < 0.6:
            recommendations.append("取引成功率が低いです。リスク管理の改善が必要です。")
        elif success_rate > 0.8:
            recommendations.append(
                "高い成功率を維持しています。現在の戦略を継続してください。"
            )

        # ROI改善の分析
        avg_roi_improvement = sum(r.roi_improvement for r in records) / len(records)

        if avg_roi_improvement > 0.01:
            recommendations.append(
                f"ROI改善が顕著です（平均{avg_roi_improvement:.2%}）。金利回避戦略が効果的です。"
            )
        elif avg_roi_improvement > 0.005:
            recommendations.append("ROI改善が確認できます。戦略の継続をお勧めします。")
        else:
            recommendations.append(
                "ROI改善が限定的です。金利回避戦略の見直しが必要です。"
            )

        # 統計分析に基づく推奨
        if "correlations" in analysis:
            corr_avoided_roi = analysis["correlations"]["avoided_interest_vs_roi"]
            if corr_avoided_roi > 0.5:
                recommendations.append(
                    "金利回避とROI改善に強い正の相関があります。金利回避戦略を強化してください。"
                )

        if len(recommendations) == 0:
            recommendations.append("分析結果は良好です。現在の戦略を継続してください。")

        return recommendations

    def export_report_to_dict(self, report: InterestAvoidanceReport) -> Dict[str, Any]:
        """レポートを辞書形式でエクスポート"""
        return {
            "summary": {
                "period": {
                    "start": report.period_start.isoformat(),
                    "end": report.period_end.isoformat(),
                    "days": (report.period_end - report.period_start).days,
                },
                "total_savings": report.total_savings,
                "average_daily_savings": report.average_daily_savings,
                "roi_improvement": report.roi_improvement,
                "positions_analyzed": report.positions_analyzed,
                "avoidance_success_rate": report.avoidance_success_rate,
            },
            "detailed_analysis": {
                "by_symbol": {
                    symbol: {
                        "total_trades": metrics.total_trades,
                        "total_avoided_interest": metrics.total_avoided_interest,
                        "total_net_profit": metrics.total_net_profit,
                        "success_rate": metrics.success_rate,
                        "interest_avoidance_rate": metrics.interest_avoidance_rate,
                        "average_roi_improvement": metrics.average_roi_improvement,
                    }
                    for symbol, metrics in report.by_symbol.items()
                },
                "by_time_period": {
                    period: {
                        "total_trades": metrics.total_trades,
                        "total_avoided_interest": metrics.total_avoided_interest,
                        "average_holding_time": metrics.average_holding_time,
                        "success_rate": metrics.success_rate,
                    }
                    for period, metrics in report.by_time_period.items()
                },
                "by_strategy": {
                    strategy: {
                        "total_trades": metrics.total_trades,
                        "total_avoided_interest": metrics.total_avoided_interest,
                        "average_roi_improvement": metrics.average_roi_improvement,
                        "interest_avoidance_rate": metrics.interest_avoidance_rate,
                    }
                    for strategy, metrics in report.by_strategy.items()
                },
            },
            "statistical_analysis": report.statistical_analysis,
            "recommendations": report.recommendations,
        }

    def get_real_time_metrics(self) -> Dict[str, Any]:
        """リアルタイムメトリクス取得"""
        if not self.saving_records:
            return {"status": "no_data", "message": "金利回避データがありません"}

        # 直近24時間のデータ
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        recent_records = [r for r in self.saving_records if r.timestamp >= yesterday]

        if not recent_records:
            return {
                "status": "no_recent_data",
                "message": "直近24時間のデータがありません",
            }

        # リアルタイム統計
        total_avoided_24h = sum(r.avoided_interest for r in recent_records)
        total_profit_24h = sum(r.net_profit for r in recent_records)
        trades_24h = len(recent_records)

        avg_roi_improvement_24h = (
            sum(r.roi_improvement for r in recent_records) / trades_24h
        )

        return {
            "status": "active",
            "period": "24h",
            "metrics": {
                "total_avoided_interest": total_avoided_24h,
                "total_net_profit": total_profit_24h,
                "trades_count": trades_24h,
                "average_roi_improvement": avg_roi_improvement_24h,
                "avoidance_per_trade": total_avoided_24h / trades_24h,
                "profit_to_avoidance_ratio": total_profit_24h
                / max(total_avoided_24h, 0.000001),
            },
            "rolling_averages": {
                "daily": (
                    list(self.rolling_windows["daily"])[-1]
                    if self.rolling_windows["daily"]
                    else None
                ),
                "weekly": (
                    list(self.rolling_windows["weekly"])[-1]
                    if self.rolling_windows["weekly"]
                    else None
                ),
                "monthly": (
                    list(self.rolling_windows["monthly"])[-1]
                    if self.rolling_windows["monthly"]
                    else None
                ),
            },
        }

    def reset_analysis_data(self) -> None:
        """分析データリセット"""
        self.saving_records.clear()
        self.performance_history.clear()
        self.analysis_cache.clear()
        self.last_analysis_time = None

        for window in self.rolling_windows.values():
            window.clear()

        logger.info("Interest avoidance analysis data reset")

    def get_analysis_summary(self) -> Dict[str, Any]:
        """分析サマリー取得"""
        if not self.saving_records:
            return {"status": "no_data", "total_records": 0, "analysis_period": "N/A"}

        oldest_record = min(self.saving_records, key=lambda x: x.timestamp)
        newest_record = max(self.saving_records, key=lambda x: x.timestamp)

        total_avoided_interest = sum(r.avoided_interest for r in self.saving_records)
        total_net_profit = sum(r.net_profit for r in self.saving_records)

        return {
            "status": "active",
            "total_records": len(self.saving_records),
            "analysis_period": {
                "start": oldest_record.timestamp.isoformat(),
                "end": newest_record.timestamp.isoformat(),
                "days": (newest_record.timestamp - oldest_record.timestamp).days,
            },
            "cumulative_metrics": {
                "total_avoided_interest": total_avoided_interest,
                "total_net_profit": total_net_profit,
                "average_avoidance_per_trade": total_avoided_interest
                / len(self.saving_records),
                "interest_to_profit_ratio": total_avoided_interest
                / max(abs(total_net_profit), 1),
            },
            "configuration": {
                "daily_interest_rate": self.daily_interest_rate,
                "calculation_method": self.calculation_method.value,
                "analysis_window_days": self.analysis_window_days,
            },
        }
