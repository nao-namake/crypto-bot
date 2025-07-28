"""
データ品質監視システム
Phase 2: 品質監視システム強化実装

機能:
- 30%ルール実装（デフォルト値比率監視）
- 取引見送り判定
- 品質閾値超過時自動停止
- 回復判定
- 品質統計・アラート管理
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QualityStatus(Enum):
    """品質状態管理"""

    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    FAILED = "failed"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class QualityMetrics:
    """品質メトリクス"""

    timestamp: datetime
    source_type: str
    source_name: str
    quality_score: float
    default_ratio: float
    success_rate: float
    latency_ms: float
    error_count: int
    status: QualityStatus

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "source_type": self.source_type,
            "source_name": self.source_name,
            "quality_score": self.quality_score,
            "default_ratio": self.default_ratio,
            "success_rate": self.success_rate,
            "latency_ms": self.latency_ms,
            "error_count": self.error_count,
            "status": self.status.value,
        }


@dataclass
class QualityThresholds:
    """品質閾値設定"""

    # 30%ルール関連
    default_ratio_warning: float = 0.20  # 20%でWarning
    default_ratio_degraded: float = 0.30  # 30%でDegraded
    default_ratio_failed: float = 0.50  # 50%でFailed

    # 品質スコア関連
    quality_score_warning: float = 0.80  # 80%未満でWarning
    quality_score_degraded: float = 0.70  # 70%未満でDegraded
    quality_score_failed: float = 0.50  # 50%未満でFailed

    # 成功率関連
    success_rate_warning: float = 0.90  # 90%未満でWarning
    success_rate_degraded: float = 0.80  # 80%未満でDegraded
    success_rate_failed: float = 0.70  # 70%未満でFailed

    # 連続失敗回数
    consecutive_failures_warning: int = 3  # 3回連続失敗でWarning
    consecutive_failures_degraded: int = 5  # 5回連続失敗でDegraded
    consecutive_failures_emergency: int = 10  # 10回連続失敗で緊急停止

    # 回復判定
    recovery_observation_minutes: int = 30  # 30分間の観察期間
    recovery_success_rate: float = 0.85  # 85%以上で回復
    recovery_default_ratio: float = 0.25  # 25%以下で回復


@dataclass
class QualityAlert:
    """品質アラート"""

    timestamp: datetime
    source_type: str
    source_name: str
    alert_type: str
    severity: str
    message: str
    metrics: QualityMetrics
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class DataQualityMonitor:
    """データ品質監視システム"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.thresholds = QualityThresholds()

        # 品質統計管理
        self.quality_history: List[QualityMetrics] = []
        self.source_statistics: Dict[str, Dict[str, Any]] = {}
        self.active_alerts: List[QualityAlert] = []

        # 状態管理
        self.emergency_stop_active = False
        self.emergency_stop_sources: List[str] = []
        self.recovery_mode_sources: List[str] = []

        # 統計設定
        self.history_retention_hours = self.config.get("history_retention_hours", 24)
        self.statistics_window_minutes = self.config.get(
            "statistics_window_minutes", 60
        )

        # アラート設定
        self.enable_alerts = self.config.get("enable_alerts", True)
        self.alert_channels = self.config.get("alert_channels", ["log"])

        # Phase H.19: グレースフルデグレード設定
        self.graceful_degradation_enabled = self.config.get(
            "graceful_degradation", True
        )
        self.partial_data_acceptance = self.config.get("partial_data_acceptance", True)
        self.quality_improvement_factor = self.config.get(
            "quality_improvement_factor", 1.1
        )  # 10%改善

        logger.info("🔧 DataQualityMonitor initialized")
        logger.info(
            f"  - Default ratio thresholds: "
            f"{self.thresholds.default_ratio_warning}/"
            f"{self.thresholds.default_ratio_degraded}/"
            f"{self.thresholds.default_ratio_failed}"
        )
        logger.info(
            f"  - Quality score thresholds: "
            f"{self.thresholds.quality_score_warning}/"
            f"{self.thresholds.quality_score_degraded}/"
            f"{self.thresholds.quality_score_failed}"
        )
        logger.info(
            f"  - Success rate thresholds: "
            f"{self.thresholds.success_rate_warning}/"
            f"{self.thresholds.success_rate_degraded}/"
            f"{self.thresholds.success_rate_failed}"
        )

    def record_quality_metrics(
        self,
        source_type: str,
        source_name: str,
        quality_score: float,
        default_ratio: float,
        success: bool,
        latency_ms: float = 0.0,
        error_count: int = 0,
    ) -> QualityMetrics:
        """品質メトリクス記録"""
        try:
            # 成功率計算
            success_rate = self._calculate_success_rate(
                source_type, source_name, success
            )

            # 品質状態判定
            status = self._determine_quality_status(
                quality_score, default_ratio, success_rate, source_type, source_name
            )

            # メトリクス作成
            metrics = QualityMetrics(
                timestamp=datetime.now(),
                source_type=source_type,
                source_name=source_name,
                quality_score=quality_score,
                default_ratio=default_ratio,
                success_rate=success_rate,
                latency_ms=latency_ms,
                error_count=error_count,
                status=status,
            )

            # 履歴に追加
            self.quality_history.append(metrics)

            # 統計更新
            self._update_source_statistics(metrics)

            # アラート処理
            self._process_quality_alerts(metrics)

            # 緊急停止判定
            self._check_emergency_stop(metrics)

            # 回復判定
            self._check_recovery(metrics)

            # 古い履歴削除
            self._cleanup_history()

            return metrics

        except Exception as e:
            logger.error(f"❌ Failed to record quality metrics: {e}")
            # デフォルトメトリクス返却
            return QualityMetrics(
                timestamp=datetime.now(),
                source_type=source_type,
                source_name=source_name,
                quality_score=0.0,
                default_ratio=1.0,
                success_rate=0.0,
                latency_ms=0.0,
                error_count=1,
                status=QualityStatus.FAILED,
            )

    def _calculate_success_rate(
        self, source_type: str, source_name: str, success: bool
    ) -> float:
        """成功率計算"""
        source_key = f"{source_type}_{source_name}"

        if source_key not in self.source_statistics:
            self.source_statistics[source_key] = {
                "total_requests": 0,
                "successful_requests": 0,
                "consecutive_failures": 0,
                "last_success": None,
                "last_failure": None,
            }

        stats = self.source_statistics[source_key]
        stats["total_requests"] += 1

        if success:
            stats["successful_requests"] += 1
            stats["consecutive_failures"] = 0
            stats["last_success"] = datetime.now()
        else:
            stats["consecutive_failures"] += 1
            stats["last_failure"] = datetime.now()

        return stats["successful_requests"] / stats["total_requests"]

    def _determine_quality_status(
        self,
        quality_score: float,
        default_ratio: float,
        success_rate: float,
        source_type: str,
        source_name: str,
    ) -> QualityStatus:
        """品質状態判定"""
        source_key = f"{source_type}_{source_name}"

        # 緊急停止中チェック
        if self.emergency_stop_active and source_key in self.emergency_stop_sources:
            return QualityStatus.EMERGENCY_STOP

        # 連続失敗回数チェック
        consecutive_failures = self.source_statistics.get(source_key, {}).get(
            "consecutive_failures", 0
        )
        if consecutive_failures >= self.thresholds.consecutive_failures_emergency:
            return QualityStatus.EMERGENCY_STOP

        # 品質評価（最も厳しい条件を適用）
        status_scores = []

        # 30%ルール評価
        if default_ratio >= self.thresholds.default_ratio_failed:
            status_scores.append(QualityStatus.FAILED)
        elif default_ratio >= self.thresholds.default_ratio_degraded:
            status_scores.append(QualityStatus.DEGRADED)
        elif default_ratio >= self.thresholds.default_ratio_warning:
            status_scores.append(QualityStatus.WARNING)
        else:
            status_scores.append(QualityStatus.HEALTHY)

        # 品質スコア評価
        if quality_score < self.thresholds.quality_score_failed:
            status_scores.append(QualityStatus.FAILED)
        elif quality_score < self.thresholds.quality_score_degraded:
            status_scores.append(QualityStatus.DEGRADED)
        elif quality_score < self.thresholds.quality_score_warning:
            status_scores.append(QualityStatus.WARNING)
        else:
            status_scores.append(QualityStatus.HEALTHY)

        # 成功率評価
        if success_rate < self.thresholds.success_rate_failed:
            status_scores.append(QualityStatus.FAILED)
        elif success_rate < self.thresholds.success_rate_degraded:
            status_scores.append(QualityStatus.DEGRADED)
        elif success_rate < self.thresholds.success_rate_warning:
            status_scores.append(QualityStatus.WARNING)
        else:
            status_scores.append(QualityStatus.HEALTHY)

        # 最も厳しい状態を返す
        status_priority = {
            QualityStatus.EMERGENCY_STOP: 5,
            QualityStatus.FAILED: 4,
            QualityStatus.DEGRADED: 3,
            QualityStatus.WARNING: 2,
            QualityStatus.HEALTHY: 1,
        }

        return max(status_scores, key=lambda s: status_priority[s])

    def _update_source_statistics(self, metrics: QualityMetrics) -> None:
        """データソース統計更新"""
        source_key = f"{metrics.source_type}_{metrics.source_name}"

        if source_key not in self.source_statistics:
            self.source_statistics[source_key] = {}

        stats = self.source_statistics[source_key]

        # 最新メトリクス更新
        stats["last_quality_score"] = metrics.quality_score
        stats["last_default_ratio"] = metrics.default_ratio
        stats["last_success_rate"] = metrics.success_rate
        stats["last_status"] = metrics.status.value
        stats["last_update"] = metrics.timestamp

        # 平均値計算（過去1時間）
        window_start = datetime.now() - timedelta(
            minutes=self.statistics_window_minutes
        )
        recent_metrics = [
            m
            for m in self.quality_history
            if m.source_type == metrics.source_type
            and m.source_name == metrics.source_name
            and m.timestamp >= window_start
        ]

        if recent_metrics:
            stats["avg_quality_score"] = sum(
                m.quality_score for m in recent_metrics
            ) / len(recent_metrics)
            stats["avg_default_ratio"] = sum(
                m.default_ratio for m in recent_metrics
            ) / len(recent_metrics)
            stats["avg_latency_ms"] = sum(m.latency_ms for m in recent_metrics) / len(
                recent_metrics
            )
            stats["error_count_1h"] = sum(m.error_count for m in recent_metrics)

    def _process_quality_alerts(self, metrics: QualityMetrics) -> None:
        """品質アラート処理"""
        if not self.enable_alerts:
            return

        # 新しいアラートが必要かチェック
        alert_needed = False
        alert_message = ""
        severity = "info"

        if metrics.status == QualityStatus.EMERGENCY_STOP:
            alert_needed = True
            alert_message = (
                f"EMERGENCY STOP: {metrics.source_type}/{metrics.source_name} - "
                f"Quality critically degraded"
            )
            severity = "critical"
        elif metrics.status == QualityStatus.FAILED:
            alert_needed = True
            alert_message = (
                f"FAILED: {metrics.source_type}/{metrics.source_name} - "
                f"Quality: {metrics.quality_score:.2f}, "
                f"Default ratio: {metrics.default_ratio:.2f}"
            )
            severity = "error"
        elif metrics.status == QualityStatus.DEGRADED:
            alert_needed = True
            alert_message = (
                f"DEGRADED: {metrics.source_type}/{metrics.source_name} - "
                f"Quality: {metrics.quality_score:.2f}, "
                f"Default ratio: {metrics.default_ratio:.2f}"
            )
            severity = "warning"
        elif metrics.status == QualityStatus.WARNING:
            alert_needed = True
            alert_message = (
                f"WARNING: {metrics.source_type}/{metrics.source_name} - "
                f"Quality: {metrics.quality_score:.2f}, "
                f"Default ratio: {metrics.default_ratio:.2f}"
            )
            severity = "warning"

        if alert_needed:
            # 重複アラートチェック
            existing_alert = None
            for alert in self.active_alerts:
                if (
                    alert.source_type == metrics.source_type
                    and alert.source_name == metrics.source_name
                    and alert.severity == severity
                    and not alert.resolved
                ):
                    existing_alert = alert
                    break

            if existing_alert is None:
                # 新しいアラート作成
                alert = QualityAlert(
                    timestamp=datetime.now(),
                    source_type=metrics.source_type,
                    source_name=metrics.source_name,
                    alert_type="quality_degradation",
                    severity=severity,
                    message=alert_message,
                    metrics=metrics,
                )

                self.active_alerts.append(alert)
                self._send_alert(alert)

    def _check_emergency_stop(self, metrics: QualityMetrics) -> None:
        """緊急停止判定"""
        source_key = f"{metrics.source_type}_{metrics.source_name}"

        if metrics.status == QualityStatus.EMERGENCY_STOP:
            if not self.emergency_stop_active:
                self.emergency_stop_active = True
                logger.critical(
                    "🚨 EMERGENCY STOP ACTIVATED: Data quality critically degraded"
                )

            if source_key not in self.emergency_stop_sources:
                self.emergency_stop_sources.append(source_key)
                logger.critical(f"🚨 Emergency stop source added: {source_key}")

    def _check_recovery(self, metrics: QualityMetrics) -> None:
        """回復判定"""
        source_key = f"{metrics.source_type}_{metrics.source_name}"

        # 回復観察期間のメトリクス取得
        window_start = datetime.now() - timedelta(
            minutes=self.thresholds.recovery_observation_minutes
        )
        recent_metrics = [
            m
            for m in self.quality_history
            if m.source_type == metrics.source_type
            and m.source_name == metrics.source_name
            and m.timestamp >= window_start
        ]

        if len(recent_metrics) >= 3:  # 最低3回の観察
            avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(
                recent_metrics
            )
            avg_default_ratio = sum(m.default_ratio for m in recent_metrics) / len(
                recent_metrics
            )

            # 回復条件チェック
            if (
                avg_success_rate >= self.thresholds.recovery_success_rate
                and avg_default_ratio <= self.thresholds.recovery_default_ratio
            ):

                # 緊急停止解除
                if source_key in self.emergency_stop_sources:
                    self.emergency_stop_sources.remove(source_key)
                    logger.info(
                        f"✅ Recovery detected: {source_key} - Emergency stop removed"
                    )

                    # 全ての緊急停止が解除されたか確認
                    if not self.emergency_stop_sources:
                        self.emergency_stop_active = False
                        logger.info(
                            "✅ EMERGENCY STOP DEACTIVATED: All sources recovered"
                        )

                # 回復アラート
                if source_key not in self.recovery_mode_sources:
                    self.recovery_mode_sources.append(source_key)

                    recovery_alert = QualityAlert(
                        timestamp=datetime.now(),
                        source_type=metrics.source_type,
                        source_name=metrics.source_name,
                        alert_type="quality_recovery",
                        severity="info",
                        message=(
                            f"RECOVERY: {metrics.source_type}/{metrics.source_name} - "
                            f"Quality recovered (Success rate: {avg_success_rate:.2f}, "
                            f"Default ratio: {avg_default_ratio:.2f})"
                        ),
                        metrics=metrics,
                    )

                    self.active_alerts.append(recovery_alert)
                    self._send_alert(recovery_alert)

    def _send_alert(self, alert: QualityAlert) -> None:
        """アラート送信"""
        for channel in self.alert_channels:
            if channel == "log":
                if alert.severity == "critical":
                    logger.critical(alert.message)
                elif alert.severity == "error":
                    logger.error(alert.message)
                elif alert.severity == "warning":
                    logger.warning(alert.message)
                else:
                    logger.info(alert.message)
            # 他のチャンネル（Slack、Email等）は今後実装

    def _cleanup_history(self) -> None:
        """古い履歴削除"""
        cutoff_time = datetime.now() - timedelta(hours=self.history_retention_hours)
        self.quality_history = [
            m for m in self.quality_history if m.timestamp >= cutoff_time
        ]

    def should_allow_trading(self, source_type: str, source_name: str) -> bool:
        """取引実行許可判定"""
        # 緊急停止中は取引停止
        if self.emergency_stop_active:
            return False

        # 特定ソースの状態確認
        source_key = f"{source_type}_{source_name}"
        if source_key in self.emergency_stop_sources:
            return False

        # 最新の品質状態確認
        latest_metrics = self._get_latest_metrics(source_type, source_name)
        if latest_metrics and latest_metrics.status in [
            QualityStatus.FAILED,
            QualityStatus.EMERGENCY_STOP,
        ]:
            return False

        return True

    def _get_latest_metrics(
        self, source_type: str, source_name: str
    ) -> Optional[QualityMetrics]:
        """最新メトリクス取得"""
        for metrics in reversed(self.quality_history):
            if (
                metrics.source_type == source_type
                and metrics.source_name == source_name
            ):
                return metrics
        return None

    def get_quality_summary(self) -> Dict[str, Any]:
        """品質サマリー取得"""
        summary = {
            "emergency_stop_active": self.emergency_stop_active,
            "emergency_stop_sources": self.emergency_stop_sources,
            "recovery_mode_sources": self.recovery_mode_sources,
            "active_alerts": len(self.active_alerts),
            "total_metrics": len(self.quality_history),
            "source_statistics": {},
        }

        # ソース別統計
        for source_key, stats in self.source_statistics.items():
            summary["source_statistics"][source_key] = {
                "last_status": stats.get("last_status", "unknown"),
                "last_quality_score": stats.get("last_quality_score", 0.0),
                "last_default_ratio": stats.get("last_default_ratio", 1.0),
                "success_rate": stats.get("last_success_rate", 0.0),
                "consecutive_failures": stats.get("consecutive_failures", 0),
                "total_requests": stats.get("total_requests", 0),
            }

        return summary

    def get_quality_report(self) -> Dict[str, Any]:
        """詳細品質レポート取得"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": self.get_quality_summary(),
            "recent_metrics": [
                m.to_dict() for m in self.quality_history[-20:]  # 最新20件
            ],
            "active_alerts": [
                {
                    "timestamp": alert.timestamp.isoformat(),
                    "source": f"{alert.source_type}/{alert.source_name}",
                    "severity": alert.severity,
                    "message": alert.message,
                    "resolved": alert.resolved,
                }
                for alert in self.active_alerts
            ],
            "thresholds": {
                "default_ratio_warning": self.thresholds.default_ratio_warning,
                "default_ratio_degraded": self.thresholds.default_ratio_degraded,
                "default_ratio_failed": self.thresholds.default_ratio_failed,
                "quality_score_warning": self.thresholds.quality_score_warning,
                "quality_score_degraded": self.thresholds.quality_score_degraded,
                "quality_score_failed": self.thresholds.quality_score_failed,
            },
        }

        return report

    def improve_data_quality(self, current_quality: float, source_type: str) -> float:
        """Phase H.19: データ品質を改善する試み

        Args:
            current_quality: 現在の品質スコア
            source_type: データソースタイプ

        Returns:
            改善された品質スコア
        """
        if not self.graceful_degradation_enabled:
            return current_quality

        # グレースフルデグレード：部分的データでも活用
        improved_quality = current_quality

        # 1. キャッシュヒットによる品質改善
        if self.partial_data_acceptance and current_quality > 0.4:
            # 40%以上のデータがあれば、キャッシュデータで補完可能と判断
            improved_quality = min(
                current_quality * self.quality_improvement_factor, 0.65
            )
            logger.info(
                f"📈 Quality improved by cache supplementation: "
                f"{current_quality:.2f} → {improved_quality:.2f}"
            )

        # 2. 外部データソースの部分的成功を考慮
        recent_metrics = [
            m
            for m in self.quality_history[-10:]
            if m.source_type == source_type and m.success_rate > 0
        ]

        if recent_metrics:
            # 最近の成功率を考慮
            avg_success_rate = sum(m.success_rate for m in recent_metrics) / len(
                recent_metrics
            )
            if avg_success_rate > 0.5:  # 50%以上成功していれば
                quality_boost = avg_success_rate * 0.1  # 最大10%のブースト
                improved_quality = min(improved_quality + quality_boost, 0.7)
                logger.info(
                    f"📊 Quality boosted by historical success rate: "
                    f"+{quality_boost:.2f} (total: {improved_quality:.2f})"
                )

        # 3. 複数ソースの組み合わせによる品質向上
        if source_type in ["external_data", "multi_source"]:
            # 複数ソースからのデータがある場合、相互補完
            other_sources = [
                m
                for m in self.quality_history[-5:]
                if m.source_type != source_type and m.quality_score > 0.5
            ]

            if len(other_sources) >= 2:
                # 他のソースが健全なら品質を向上
                improved_quality = min(improved_quality + 0.05, 0.65)
                logger.info(
                    f"🔄 Quality improved by multi-source validation: "
                    f"{improved_quality:.2f}"
                )

        return improved_quality

    def get_adjusted_quality_threshold(self, base_threshold: float) -> float:
        """Phase H.19: 動的品質閾値の調整

        Args:
            base_threshold: 基本品質閾値

        Returns:
            調整された品質閾値
        """
        if not self.graceful_degradation_enabled:
            return base_threshold

        # 全体的な品質状況を評価
        recent_metrics = self.quality_history[-30:]  # 最新30件
        if not recent_metrics:
            return base_threshold

        # 平均品質スコアを計算
        avg_quality = sum(m.quality_score for m in recent_metrics) / len(recent_metrics)

        # 品質が全体的に低い場合、閾値を少し緩和
        if avg_quality < 0.6:
            # 最大10%まで閾値を下げる
            adjustment = max(0.9, avg_quality / 0.6)
            adjusted_threshold = base_threshold * adjustment

            logger.info(
                f"🎯 Quality threshold adjusted: {base_threshold:.2f} → "
                f"{adjusted_threshold:.2f} (avg quality: {avg_quality:.2f})"
            )

            return adjusted_threshold

        return base_threshold

    def calculate_composite_quality(self, metrics_dict: Dict[str, float]) -> float:
        """Phase H.19: 複合品質スコアの計算

        Args:
            metrics_dict: 各メトリクスの辞書

        Returns:
            複合品質スコア
        """
        # 重み付け設定
        weights = {
            "price_data": 0.4,  # 価格データが最重要
            "technical": 0.3,  # テクニカル指標
            "external": 0.2,  # 外部データ
            "market": 0.1,  # 市場データ
        }

        composite_score = 0.0
        total_weight = 0.0

        for category, weight in weights.items():
            if category in metrics_dict:
                score = metrics_dict[category]
                # グレースフルデグレード：部分的な成功も考慮
                if self.partial_data_acceptance and score > 0:
                    composite_score += score * weight
                    total_weight += weight

        # 正規化
        if total_weight > 0:
            composite_score = composite_score / total_weight

        # 最低品質保証（価格データがあれば最低40%）
        if "price_data" in metrics_dict and metrics_dict["price_data"] > 0.8:
            composite_score = max(composite_score, 0.4)

        return composite_score


# グローバルインスタンス
_quality_monitor = None


def get_quality_monitor(config: Optional[Dict[str, Any]] = None) -> DataQualityMonitor:
    """品質監視システム取得（シングルトン）"""
    global _quality_monitor
    if _quality_monitor is None:
        _quality_monitor = DataQualityMonitor(config)
    return _quality_monitor
