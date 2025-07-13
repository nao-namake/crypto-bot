#!/usr/bin/env python3
# =============================================================================
# スクリプト: scripts/monitoring_alert_system.py
# 説明:
# アンサンブル学習システムのリアルタイム監視・アラートシステム
# パフォーマンス劣化検知・自動通知・異常対応システム
# =============================================================================

import sys
import os
import json
import logging
import threading
import time
import smtplib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import yaml
import requests

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertType(Enum):
    """アラートタイプ"""
    PERFORMANCE_DEGRADATION = "performance_degradation"
    CONFIDENCE_DROP = "confidence_drop"
    ERROR_RATE_SPIKE = "error_rate_spike"
    DRAWDOWN_LIMIT = "drawdown_limit"
    MODEL_DRIFT = "model_drift"
    SYSTEM_ERROR = "system_error"
    DATA_QUALITY = "data_quality"
    ENSEMBLE_DISAGREEMENT = "ensemble_disagreement"


@dataclass
class MonitoringMetrics:
    """監視メトリクス"""
    timestamp: datetime
    strategy_type: str
    
    # パフォーマンス指標
    win_rate: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    
    # リアルタイム指標
    recent_trades: int
    error_count: int
    avg_confidence: float
    signal_frequency: float
    
    # システム指標
    response_time: float
    memory_usage: float
    cpu_usage: float
    
    # アンサンブル指標
    model_agreement: Optional[float] = None
    ensemble_diversity: Optional[float] = None
    prediction_stability: Optional[float] = None


@dataclass
class Alert:
    """アラート"""
    alert_id: str
    timestamp: datetime
    level: AlertLevel
    alert_type: AlertType
    title: str
    message: str
    metrics: Dict[str, Any]
    suggested_actions: List[str]
    is_resolved: bool = False
    resolution_time: Optional[datetime] = None
    resolution_notes: Optional[str] = None


@dataclass
class MonitoringConfig:
    """監視設定"""
    # パフォーマンス閾値
    min_win_rate: float = 0.5
    max_drawdown_limit: float = -0.1
    min_sharpe_ratio: float = 0.5
    
    # システム閾値
    max_error_rate: float = 0.05
    min_confidence: float = 0.6
    max_response_time: float = 5.0
    
    # アンサンブル閾値
    min_model_agreement: float = 0.7
    min_ensemble_diversity: float = 0.3
    
    # 監視間隔
    monitoring_interval: int = 60  # 秒
    alert_cooldown: int = 300  # 秒
    
    # 通知設定
    email_notifications: bool = True
    slack_notifications: bool = True
    webhook_notifications: bool = True


class AlertManager:
    """アラート管理"""
    
    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.active_alerts = {}
        self.alert_history = []
        self.cooldown_timers = {}
        
    def create_alert(self, alert_type: AlertType, level: AlertLevel, 
                    title: str, message: str, metrics: Dict[str, Any],
                    suggested_actions: List[str] = None) -> Alert:
        """アラート作成"""
        alert_id = f"{alert_type.value}_{int(time.time())}"
        
        # クールダウンチェック
        cooldown_key = f"{alert_type.value}_{level.value}"
        if cooldown_key in self.cooldown_timers:
            last_alert_time = self.cooldown_timers[cooldown_key]
            if (datetime.now() - last_alert_time).seconds < self.config.alert_cooldown:
                logger.debug(f"Alert {alert_type.value} in cooldown period")
                return None
        
        alert = Alert(
            alert_id=alert_id,
            timestamp=datetime.now(),
            level=level,
            alert_type=alert_type,
            title=title,
            message=message,
            metrics=metrics,
            suggested_actions=suggested_actions or []
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        self.cooldown_timers[cooldown_key] = datetime.now()
        
        logger.warning(f"Alert created: {title} ({level.value})")
        return alert
    
    def resolve_alert(self, alert_id: str, resolution_notes: str = None):
        """アラート解決"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.is_resolved = True
            alert.resolution_time = datetime.now()
            alert.resolution_notes = resolution_notes
            
            del self.active_alerts[alert_id]
            logger.info(f"Alert resolved: {alert.title}")
    
    def get_active_alerts(self) -> List[Alert]:
        """アクティブアラート取得"""
        return list(self.active_alerts.values())
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """アラートサマリー取得"""
        active_by_level = {}
        for alert in self.active_alerts.values():
            level = alert.level.value
            active_by_level[level] = active_by_level.get(level, 0) + 1
        
        return {
            'total_active': len(self.active_alerts),
            'by_level': active_by_level,
            'total_history': len(self.alert_history),
            'last_24h': len([a for a in self.alert_history 
                           if (datetime.now() - a.timestamp).days < 1])
        }


class NotificationService:
    """通知サービス"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.email_config = config.get('email', {})
        self.slack_config = config.get('slack', {})
        self.webhook_config = config.get('webhook', {})
    
    async def send_alert_notification(self, alert: Alert):
        """アラート通知送信"""
        notification_tasks = []
        
        if self.config.get('email_notifications', False):
            notification_tasks.append(self._send_email_notification(alert))
        
        if self.config.get('slack_notifications', False):
            notification_tasks.append(self._send_slack_notification(alert))
        
        if self.config.get('webhook_notifications', False):
            notification_tasks.append(self._send_webhook_notification(alert))
        
        if notification_tasks:
            await asyncio.gather(*notification_tasks, return_exceptions=True)
    
    async def _send_email_notification(self, alert: Alert):
        """メール通知送信"""
        try:
            if not self.email_config:
                return
            
            smtp_server = self.email_config.get('smtp_server', 'localhost')
            smtp_port = self.email_config.get('smtp_port', 587)
            username = self.email_config.get('username')
            password = self.email_config.get('password')
            from_email = self.email_config.get('from_email')
            to_emails = self.email_config.get('to_emails', [])
            
            if not all([username, password, from_email, to_emails]):
                logger.warning("Email configuration incomplete")
                return
            
            # メール作成
            subject = f"[{alert.level.value.upper()}] {alert.title}"
            body = self._format_alert_email(alert)
            
            msg = MimeMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            msg.attach(MimeText(body, 'plain', 'utf-8'))
            
            # SMTP送信
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for alert: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_slack_notification(self, alert: Alert):
        """Slack通知送信"""
        try:
            webhook_url = self.slack_config.get('webhook_url')
            if not webhook_url:
                return
            
            # Slack用フォーマット
            color = {
                AlertLevel.INFO: "#36a64f",
                AlertLevel.WARNING: "#ff9500", 
                AlertLevel.CRITICAL: "#ff0000",
                AlertLevel.EMERGENCY: "#8B0000"
            }.get(alert.level, "#808080")
            
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"[{alert.level.value.upper()}] {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "アラートタイプ",
                                "value": alert.alert_type.value,
                                "short": True
                            },
                            {
                                "title": "発生時刻",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True
                            }
                        ],
                        "footer": "アンサンブル学習監視システム",
                        "ts": int(alert.timestamp.timestamp())
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent for alert: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    async def _send_webhook_notification(self, alert: Alert):
        """Webhook通知送信"""
        try:
            webhook_url = self.webhook_config.get('url')
            if not webhook_url:
                return
            
            payload = {
                'alert_id': alert.alert_id,
                'timestamp': alert.timestamp.isoformat(),
                'level': alert.level.value,
                'type': alert.alert_type.value,
                'title': alert.title,
                'message': alert.message,
                'metrics': alert.metrics,
                'suggested_actions': alert.suggested_actions
            }
            
            headers = self.webhook_config.get('headers', {})
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent for alert: {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
    
    def _format_alert_email(self, alert: Alert) -> str:
        """アラートメール フォーマット"""
        lines = []
        lines.append(f"アンサンブル学習システム アラート通知")
        lines.append("=" * 50)
        lines.append(f"アラートレベル: {alert.level.value.upper()}")
        lines.append(f"アラートタイプ: {alert.alert_type.value}")
        lines.append(f"発生時刻: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"タイトル: {alert.title}")
        lines.append("")
        lines.append("詳細:")
        lines.append(alert.message)
        lines.append("")
        
        if alert.metrics:
            lines.append("関連メトリクス:")
            for key, value in alert.metrics.items():
                lines.append(f"  {key}: {value}")
            lines.append("")
        
        if alert.suggested_actions:
            lines.append("推奨アクション:")
            for action in alert.suggested_actions:
                lines.append(f"  • {action}")
        
        lines.append("")
        lines.append("アラートID: " + alert.alert_id)
        
        return "\n".join(lines)


class PerformanceMonitor:
    """パフォーマンス監視"""
    
    def __init__(self, config: MonitoringConfig, alert_manager: AlertManager):
        self.config = config
        self.alert_manager = alert_manager
        self.metrics_history = []
        self.baseline_metrics = None
        
    def analyze_metrics(self, metrics: MonitoringMetrics) -> List[Alert]:
        """メトリクス分析・アラート生成"""
        alerts = []
        
        # 勝率監視
        if metrics.win_rate < self.config.min_win_rate:
            alert = self.alert_manager.create_alert(
                AlertType.PERFORMANCE_DEGRADATION,
                AlertLevel.WARNING if metrics.win_rate > 0.45 else AlertLevel.CRITICAL,
                "勝率低下検知",
                f"勝率が閾値を下回りました: {metrics.win_rate:.2%} (閾値: {self.config.min_win_rate:.2%})",
                {"current_win_rate": metrics.win_rate, "threshold": self.config.min_win_rate},
                [
                    "モデル再学習の検討",
                    "特徴量の見直し",
                    "市場環境変化の確認"
                ]
            )
            if alert:
                alerts.append(alert)
        
        # ドローダウン監視
        if metrics.max_drawdown < self.config.max_drawdown_limit:
            alert = self.alert_manager.create_alert(
                AlertType.DRAWDOWN_LIMIT,
                AlertLevel.CRITICAL,
                "ドローダウン限界超過",
                f"ドローダウンが限界を超えました: {metrics.max_drawdown:.2%} (限界: {self.config.max_drawdown_limit:.2%})",
                {"current_drawdown": metrics.max_drawdown, "limit": self.config.max_drawdown_limit},
                [
                    "緊急停止の検討",
                    "ポジションサイズ縮小",
                    "リスク管理パラメータ見直し"
                ]
            )
            if alert:
                alerts.append(alert)
        
        # エラー率監視
        error_rate = metrics.error_count / max(metrics.recent_trades, 1)
        if error_rate > self.config.max_error_rate:
            alert = self.alert_manager.create_alert(
                AlertType.ERROR_RATE_SPIKE,
                AlertLevel.WARNING,
                "エラー率上昇",
                f"エラー率が上昇しています: {error_rate:.2%} (閾値: {self.config.max_error_rate:.2%})",
                {"current_error_rate": error_rate, "threshold": self.config.max_error_rate},
                [
                    "ログ確認",
                    "API接続状況確認",
                    "システムリソース確認"
                ]
            )
            if alert:
                alerts.append(alert)
        
        # 信頼度監視
        if metrics.avg_confidence < self.config.min_confidence:
            alert = self.alert_manager.create_alert(
                AlertType.CONFIDENCE_DROP,
                AlertLevel.WARNING,
                "予測信頼度低下",
                f"平均信頼度が低下しています: {metrics.avg_confidence:.3f} (閾値: {self.config.min_confidence:.3f})",
                {"current_confidence": metrics.avg_confidence, "threshold": self.config.min_confidence},
                [
                    "市場環境確認",
                    "モデル精度検証",
                    "閾値調整検討"
                ]
            )
            if alert:
                alerts.append(alert)
        
        # アンサンブル特有監視
        if metrics.model_agreement and metrics.model_agreement < self.config.min_model_agreement:
            alert = self.alert_manager.create_alert(
                AlertType.ENSEMBLE_DISAGREEMENT,
                AlertLevel.WARNING,
                "モデル間合意度低下",
                f"モデル間の合意度が低下しています: {metrics.model_agreement:.3f} (閾値: {self.config.min_model_agreement:.3f})",
                {"current_agreement": metrics.model_agreement, "threshold": self.config.min_model_agreement},
                [
                    "個別モデル性能確認",
                    "特徴量品質確認",
                    "モデル更新検討"
                ]
            )
            if alert:
                alerts.append(alert)
        
        # システムパフォーマンス監視
        if metrics.response_time > self.config.max_response_time:
            alert = self.alert_manager.create_alert(
                AlertType.SYSTEM_ERROR,
                AlertLevel.WARNING,
                "応答時間遅延",
                f"システム応答時間が遅延しています: {metrics.response_time:.2f}秒 (閾値: {self.config.max_response_time:.2f}秒)",
                {"current_response_time": metrics.response_time, "threshold": self.config.max_response_time},
                [
                    "システムリソース確認",
                    "データベース最適化",
                    "キャッシュ確認"
                ]
            )
            if alert:
                alerts.append(alert)
        
        self.metrics_history.append(metrics)
        return alerts
    
    def detect_performance_trends(self) -> List[Alert]:
        """パフォーマンストレンド検知"""
        alerts = []
        
        if len(self.metrics_history) < 10:
            return alerts
        
        recent_metrics = self.metrics_history[-10:]
        
        # 勝率トレンド
        win_rates = [m.win_rate for m in recent_metrics]
        if len(win_rates) >= 5:
            trend_slope = np.polyfit(range(len(win_rates)), win_rates, 1)[0]
            if trend_slope < -0.01:  # 1%/期間の下降トレンド
                alert = self.alert_manager.create_alert(
                    AlertType.PERFORMANCE_DEGRADATION,
                    AlertLevel.WARNING,
                    "勝率下降トレンド検知",
                    f"勝率の継続的な下降トレンドを検知しました (傾き: {trend_slope:.4f})",
                    {"trend_slope": trend_slope, "recent_win_rates": win_rates},
                    [
                        "トレンド原因分析",
                        "モデル適応性確認",
                        "市場環境変化調査"
                    ]
                )
                if alert:
                    alerts.append(alert)
        
        return alerts


class MonitoringDashboard:
    """監視ダッシュボード"""
    
    def __init__(self, alert_manager: AlertManager, performance_monitor: PerformanceMonitor):
        self.alert_manager = alert_manager
        self.performance_monitor = performance_monitor
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """ダッシュボードデータ生成"""
        current_time = datetime.now()
        
        # アラートサマリー
        alert_summary = self.alert_manager.get_alert_summary()
        
        # 最新メトリクス
        latest_metrics = None
        if self.performance_monitor.metrics_history:
            latest_metrics = self.performance_monitor.metrics_history[-1]
        
        # 過去24時間のトレンド
        recent_metrics = [
            m for m in self.performance_monitor.metrics_history
            if (current_time - m.timestamp).total_seconds() < 86400
        ]
        
        dashboard_data = {
            'timestamp': current_time.isoformat(),
            'status': self._determine_overall_status(),
            'alert_summary': alert_summary,
            'active_alerts': [asdict(alert) for alert in self.alert_manager.get_active_alerts()],
            'latest_metrics': asdict(latest_metrics) if latest_metrics else None,
            'trend_data': self._calculate_trend_data(recent_metrics),
            'system_health': self._calculate_system_health(recent_metrics)
        }
        
        return dashboard_data
    
    def _determine_overall_status(self) -> str:
        """全体ステータス判定"""
        active_alerts = self.alert_manager.get_active_alerts()
        
        if any(alert.level == AlertLevel.EMERGENCY for alert in active_alerts):
            return "EMERGENCY"
        elif any(alert.level == AlertLevel.CRITICAL for alert in active_alerts):
            return "CRITICAL"
        elif any(alert.level == AlertLevel.WARNING for alert in active_alerts):
            return "WARNING"
        else:
            return "HEALTHY"
    
    def _calculate_trend_data(self, recent_metrics: List[MonitoringMetrics]) -> Dict[str, Any]:
        """トレンドデータ計算"""
        if not recent_metrics:
            return {}
        
        timestamps = [m.timestamp.isoformat() for m in recent_metrics]
        win_rates = [m.win_rate for m in recent_metrics]
        returns = [m.total_return for m in recent_metrics]
        confidences = [m.avg_confidence for m in recent_metrics]
        
        return {
            'timestamps': timestamps,
            'win_rates': win_rates,
            'returns': returns,
            'confidences': confidences,
            'trend_summary': {
                'avg_win_rate': np.mean(win_rates),
                'avg_return': np.mean(returns),
                'avg_confidence': np.mean(confidences),
                'win_rate_trend': np.polyfit(range(len(win_rates)), win_rates, 1)[0] if len(win_rates) > 1 else 0
            }
        }
    
    def _calculate_system_health(self, recent_metrics: List[MonitoringMetrics]) -> Dict[str, Any]:
        """システムヘルス計算"""
        if not recent_metrics:
            return {"status": "NO_DATA"}
        
        latest = recent_metrics[-1]
        
        health_score = 100
        issues = []
        
        # パフォーマンスチェック
        if latest.win_rate < 0.5:
            health_score -= 20
            issues.append("低勝率")
        
        if latest.max_drawdown < -0.08:
            health_score -= 15
            issues.append("高ドローダウン")
        
        if latest.avg_confidence < 0.6:
            health_score -= 10
            issues.append("低信頼度")
        
        # システムチェック
        if latest.response_time > 3.0:
            health_score -= 10
            issues.append("応答遅延")
        
        if latest.error_count > 5:
            health_score -= 15
            issues.append("エラー多発")
        
        return {
            "health_score": max(0, health_score),
            "status": "HEALTHY" if health_score > 80 else "DEGRADED" if health_score > 50 else "UNHEALTHY",
            "issues": issues
        }


class MonitoringAlertSystem:
    """メイン監視アラートシステム"""
    
    def __init__(self, config_path: str = None):
        """
        監視アラートシステム初期化
        
        Parameters:
        -----------
        config_path : str
            設定ファイルパス
        """
        self.config = self._load_config(config_path)
        self.monitoring_config = MonitoringConfig(**self.config.get('monitoring', {}))
        
        # コンポーネント初期化
        self.alert_manager = AlertManager(self.monitoring_config)
        self.performance_monitor = PerformanceMonitor(self.monitoring_config, self.alert_manager)
        self.notification_service = NotificationService(self.config.get('notifications', {}))
        self.dashboard = MonitoringDashboard(self.alert_manager, self.performance_monitor)
        
        # 監視状態
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # 状態ファイル
        self.status_file = project_root / "status_monitoring.json"
        
        logger.info("Monitoring Alert System initialized")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """設定ファイル読み込み"""
        if config_path is None:
            config_path = project_root / "config" / "monitoring_alert.yml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Monitoring config loaded from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load monitoring config: {e}")
            return self._get_default_monitoring_config()
    
    def _get_default_monitoring_config(self) -> Dict:
        """デフォルト監視設定"""
        return {
            'monitoring': {
                'min_win_rate': 0.5,
                'max_drawdown_limit': -0.1,
                'min_sharpe_ratio': 0.5,
                'max_error_rate': 0.05,
                'min_confidence': 0.6,
                'max_response_time': 5.0,
                'min_model_agreement': 0.7,
                'min_ensemble_diversity': 0.3,
                'monitoring_interval': 60,
                'alert_cooldown': 300,
                'email_notifications': False,
                'slack_notifications': False,
                'webhook_notifications': False
            },
            'notifications': {
                'email': {
                    'smtp_server': 'localhost',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'from_email': '',
                    'to_emails': []
                },
                'slack': {
                    'webhook_url': ''
                },
                'webhook': {
                    'url': '',
                    'headers': {}
                }
            }
        }
    
    def start_monitoring(self):
        """監視開始"""
        if self.is_monitoring:
            logger.warning("Monitoring already running")
            return
        
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Monitoring started")
    
    def stop_monitoring(self):
        """監視停止"""
        self.is_monitoring = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        logger.info("Monitoring stopped")
    
    def _monitoring_loop(self):
        """監視ループ"""
        while self.is_monitoring:
            try:
                # メトリクス収集
                current_metrics = self._collect_current_metrics()
                
                if current_metrics:
                    # パフォーマンス分析
                    alerts = self.performance_monitor.analyze_metrics(current_metrics)
                    
                    # トレンド分析
                    trend_alerts = self.performance_monitor.detect_performance_trends()
                    alerts.extend(trend_alerts)
                    
                    # 通知送信
                    for alert in alerts:
                        asyncio.run(self.notification_service.send_alert_notification(alert))
                
                # ダッシュボード更新
                self._update_dashboard()
                
                # ステータス保存
                self._save_monitoring_status()
                
                time.sleep(self.monitoring_config.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)
    
    def _collect_current_metrics(self) -> Optional[MonitoringMetrics]:
        """現在のメトリクス収集"""
        try:
            # 実際の実装では本番システムからメトリクス収集
            # ここでは模擬データ生成
            
            current_time = datetime.now()
            
            # 基本パフォーマンス（時間に応じて変化）
            base_win_rate = 0.58 + 0.05 * np.sin(current_time.hour / 24 * 2 * np.pi)
            base_return = 0.02 + 0.01 * np.random.normal()
            
            metrics = MonitoringMetrics(
                timestamp=current_time,
                strategy_type="ensemble" if np.random.random() > 0.5 else "traditional",
                win_rate=max(0, min(1, base_win_rate + np.random.normal(0, 0.02))),
                total_return=base_return,
                sharpe_ratio=1.2 + np.random.normal(0, 0.2),
                max_drawdown=np.random.uniform(-0.15, -0.02),
                recent_trades=np.random.randint(10, 50),
                error_count=np.random.randint(0, 3),
                avg_confidence=np.random.uniform(0.55, 0.85),
                signal_frequency=np.random.uniform(2, 8),
                response_time=np.random.uniform(0.5, 3.0),
                memory_usage=np.random.uniform(60, 85),
                cpu_usage=np.random.uniform(20, 70),
                model_agreement=np.random.uniform(0.6, 0.9),
                ensemble_diversity=np.random.uniform(0.3, 0.8),
                prediction_stability=np.random.uniform(0.7, 0.95)
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return None
    
    def _update_dashboard(self):
        """ダッシュボード更新"""
        try:
            dashboard_data = self.dashboard.generate_dashboard_data()
            
            # ダッシュボードファイル保存
            dashboard_file = project_root / "monitoring_dashboard.json"
            with open(dashboard_file, 'w', encoding='utf-8') as f:
                json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)
                
        except Exception as e:
            logger.error(f"Failed to update dashboard: {e}")
    
    def _save_monitoring_status(self):
        """監視ステータス保存"""
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'is_monitoring': self.is_monitoring,
                'alert_summary': self.alert_manager.get_alert_summary(),
                'system_status': self.dashboard._determine_overall_status(),
                'metrics_count': len(self.performance_monitor.metrics_history)
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Failed to save monitoring status: {e}")
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """監視ステータス取得"""
        return {
            'is_monitoring': self.is_monitoring,
            'alert_summary': self.alert_manager.get_alert_summary(),
            'active_alerts': [asdict(alert) for alert in self.alert_manager.get_active_alerts()],
            'dashboard_data': self.dashboard.generate_dashboard_data()
        }
    
    def force_alert_test(self):
        """アラートテスト実行"""
        test_alert = self.alert_manager.create_alert(
            AlertType.SYSTEM_ERROR,
            AlertLevel.INFO,
            "監視システムテスト",
            "これは監視アラートシステムのテスト通知です。",
            {"test": True},
            ["テスト完了確認"]
        )
        
        if test_alert:
            asyncio.run(self.notification_service.send_alert_notification(test_alert))
            logger.info("Test alert sent successfully")
        
        return test_alert


def main():
    """メイン実行関数"""
    print("🔔 アンサンブル学習システム 監視・アラートシステム")
    print("=" * 60)
    
    try:
        # 監視システム初期化
        monitoring_system = MonitoringAlertSystem()
        
        # 対話式メニュー
        while True:
            print("\n📋 利用可能なコマンド:")
            print("1. 監視開始")
            print("2. 監視停止") 
            print("3. ステータス確認")
            print("4. アクティブアラート表示")
            print("5. テストアラート送信")
            print("6. ダッシュボード表示")
            print("0. 終了")
            
            choice = input("\nコマンドを選択してください (0-6): ").strip()
            
            if choice == '1':
                monitoring_system.start_monitoring()
                print("✅ 監視を開始しました")
                
            elif choice == '2':
                monitoring_system.stop_monitoring()
                print("✅ 監視を停止しました")
                
            elif choice == '3':
                status = monitoring_system.get_monitoring_status()
                print(f"\n📊 監視ステータス:")
                print(f"  監視実行中: {status['is_monitoring']}")
                print(f"  アクティブアラート数: {status['alert_summary']['total_active']}")
                print(f"  システム状態: {status['dashboard_data']['status']}")
                
            elif choice == '4':
                active_alerts = monitoring_system.alert_manager.get_active_alerts()
                print(f"\n🚨 アクティブアラート ({len(active_alerts)}件):")
                for alert in active_alerts:
                    print(f"  [{alert.level.value}] {alert.title}")
                    print(f"    時刻: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"    内容: {alert.message}")
                
            elif choice == '5':
                test_alert = monitoring_system.force_alert_test()
                if test_alert:
                    print("✅ テストアラートを送信しました")
                else:
                    print("❌ テストアラート送信に失敗しました")
                
            elif choice == '6':
                dashboard_data = monitoring_system.dashboard.generate_dashboard_data()
                print(f"\n📈 ダッシュボード:")
                print(f"  システム状態: {dashboard_data['status']}")
                print(f"  ヘルススコア: {dashboard_data['system_health']['health_score']}/100")
                
                if dashboard_data['trend_data']:
                    trend = dashboard_data['trend_data']['trend_summary']
                    print(f"  平均勝率: {trend['avg_win_rate']:.2%}")
                    print(f"  平均リターン: {trend['avg_return']:.2%}")
                    print(f"  平均信頼度: {trend['avg_confidence']:.3f}")
                
            elif choice == '0':
                if monitoring_system.is_monitoring:
                    monitoring_system.stop_monitoring()
                print("👋 プログラムを終了します")
                break
                
            else:
                print("❌ 無効な選択です")
        
    except KeyboardInterrupt:
        print("\n\n🛑 プログラムが中断されました")
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        print(f"\n❌ エラーが発生しました: {e}")


if __name__ == "__main__":
    main()