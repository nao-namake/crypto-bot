# =============================================================================
# ファイル名: crypto_bot/monitoring/performance_monitor.py
# 説明:
# Phase C2: リアルタイムパフォーマンス監視システム
# 勝率・収益性・リスク指標監視・劣化検知・異常アラート・統計的検定
# DynamicWeightAdjusterとの統合・取引システム監視特化
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd
from collections import deque, defaultdict
from scipy import stats
import threading
import time

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """アラートレベル"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PerformanceAlert:
    """パフォーマンスアラート"""
    timestamp: datetime
    alert_id: str
    level: AlertLevel
    metric_name: str
    current_value: float
    threshold_value: float
    message: str
    context: Dict[str, Any]


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標"""
    timestamp: datetime
    timeframe: str
    
    # 精度指標
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    
    # 収益性指標
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    
    # リスク指標
    max_drawdown: float
    volatility: float
    var_95: float  # Value at Risk 95%
    expected_shortfall: float
    
    # 取引指標
    total_trades: int
    avg_trade_duration: float
    consecutive_losses: int
    consecutive_wins: int


class PerformanceMonitor:
    """
    Phase C2: リアルタイムパフォーマンス監視システム
    
    機能:
    - リアルタイム勝率・収益性・リスク指標監視
    - 統計的性能劣化検知（t-test・Mann-Whitney U検定等）
    - 閾値ベースアラートシステム・緊急停止機能
    - 予測精度追跡・動的重み調整支援
    - A/Bテスト・性能比較・統計的検証
    - 取引システム特化監視・リアルタイムダッシュボード
    """

    def __init__(self, config: Dict[str, Any]):
        """
        パフォーマンス監視システム初期化
        
        Parameters:
        -----------
        config : Dict[str, Any]
            監視設定辞書
        """
        self.config = config
        
        # 基本監視設定
        monitor_config = config.get("performance_monitoring", {})
        self.timeframes = monitor_config.get("timeframes", ["15m", "1h", "4h"])
        self.monitoring_interval = monitor_config.get("monitoring_interval", 60)  # 秒
        self.history_window = monitor_config.get("history_window", 1000)
        self.enable_alerts = monitor_config.get("enable_alerts", True)
        self.enable_auto_stop = monitor_config.get("enable_auto_stop", True)
        
        # 閾値設定
        thresholds = monitor_config.get("thresholds", {})
        self.accuracy_threshold = thresholds.get("min_accuracy", 0.55)
        self.win_rate_threshold = thresholds.get("min_win_rate", 0.52)
        self.sharpe_threshold = thresholds.get("min_sharpe_ratio", 0.5)
        self.max_drawdown_threshold = thresholds.get("max_drawdown", -0.15)
        self.consecutive_loss_threshold = thresholds.get("max_consecutive_losses", 5)
        
        # 劣化検知設定
        degradation_config = monitor_config.get("degradation_detection", {})
        self.degradation_window = degradation_config.get("window", 50)
        self.degradation_significance = degradation_config.get("significance", 0.05)
        self.min_samples_for_test = degradation_config.get("min_samples", 30)
        
        # アラート設定
        alert_config = monitor_config.get("alerts", {})
        self.alert_cooldown = alert_config.get("cooldown_minutes", 15)
        self.email_alerts = alert_config.get("email_enabled", False)
        self.webhook_alerts = alert_config.get("webhook_enabled", False)
        self.webhook_url = alert_config.get("webhook_url", "")
        
        # データ構造初期化
        self.performance_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.history_window)
        )
        self.trade_history: deque = deque(maxlen=self.history_window)
        self.alert_history: deque = deque(maxlen=500)
        self.last_alert_times: Dict[str, datetime] = {}
        
        # 統計検定用データ
        self.baseline_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=200)
        )
        self.recent_metrics: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=100)
        )
        
        # 監視統計
        self.monitor_stats = {
            "monitoring_cycles": 0,
            "alerts_generated": 0,
            "critical_alerts": 0,
            "emergency_stops": 0,
            "degradation_detections": 0,
            "statistical_tests_performed": 0,
            "uptime_hours": 0.0,
            "last_update": datetime.now(),
        }
        
        # 現在の監視状態
        self.current_status = "healthy"
        self.monitoring_active = False
        self.auto_stop_triggered = False
        self.emergency_stop_callback: Optional[Callable] = None
        
        # スレッド管理
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        logger.info("📊 PerformanceMonitor initialized")
        logger.info(f"   Timeframes: {self.timeframes}")
        logger.info(f"   Monitoring interval: {self.monitoring_interval}s")
        logger.info(f"   Alerts enabled: {self.enable_alerts}")

    def start_monitoring(self, emergency_stop_callback: Optional[Callable] = None):
        """監視開始"""
        try:
            if self.monitoring_active:
                logger.warning("Performance monitoring already active")
                return
                
            self.emergency_stop_callback = emergency_stop_callback
            self.monitoring_active = True
            self.stop_monitoring.clear()
            
            # 監視スレッド開始
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="PerformanceMonitor"
            )
            self.monitor_thread.start()
            
            logger.info("🚀 Performance monitoring started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start performance monitoring: {e}")

    def stop_monitoring(self):
        """監視停止"""
        try:
            if not self.monitoring_active:
                return
                
            self.stop_monitoring.set()
            self.monitoring_active = False
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5.0)
                
            logger.info("🛑 Performance monitoring stopped")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop performance monitoring: {e}")

    def _monitoring_loop(self):
        """監視メインループ"""
        try:
            logger.info("📊 Performance monitoring loop started")
            
            while not self.stop_monitoring.wait(self.monitoring_interval):
                try:
                    self._perform_monitoring_cycle()
                    self.monitor_stats["monitoring_cycles"] += 1
                    
                except Exception as e:
                    logger.error(f"Monitoring cycle error: {e}")
                    
            logger.info("📊 Performance monitoring loop ended")
            
        except Exception as e:
            logger.error(f"❌ Monitoring loop failed: {e}")

    def _perform_monitoring_cycle(self):
        """監視サイクル実行"""
        try:
            # 1. 現在のパフォーマンス指標計算
            current_metrics = self._calculate_current_performance_metrics()
            
            # 2. 閾値チェック・アラート生成
            threshold_alerts = self._check_performance_thresholds(current_metrics)
            
            # 3. 統計的劣化検知
            degradation_alerts = self._detect_statistical_degradation(current_metrics)
            
            # 4. アラート処理
            all_alerts = threshold_alerts + degradation_alerts
            for alert in all_alerts:
                self._process_alert(alert)
                
            # 5. 自動停止判定
            if self.enable_auto_stop:
                self._evaluate_emergency_stop(all_alerts)
                
            # 6. 統計更新
            self._update_monitoring_statistics(current_metrics)
            
        except Exception as e:
            logger.error(f"Monitoring cycle execution failed: {e}")

    def record_prediction_result(
        self,
        timeframe: str,
        prediction: Any,
        actual_result: Any,
        confidence: float,
        market_context: Optional[Dict[str, Any]] = None
    ):
        """予測結果記録"""
        try:
            result_record = {
                "timestamp": datetime.now(),
                "timeframe": timeframe,
                "prediction": prediction,
                "actual_result": actual_result,
                "confidence": confidence,
                "market_context": market_context or {},
                "correct": prediction == actual_result,
            }
            
            self.performance_history[f"{timeframe}_predictions"].append(result_record)
            
            # リアルタイム精度更新
            self._update_realtime_accuracy(timeframe, result_record)
            
        except Exception as e:
            logger.error(f"Prediction result recording failed: {e}")

    def record_trade_result(
        self,
        trade_id: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
        duration_minutes: float,
        pnl: float,
        timeframe: str,
        strategy_info: Optional[Dict[str, Any]] = None
    ):
        """取引結果記録"""
        try:
            trade_record = {
                "timestamp": datetime.now(),
                "trade_id": trade_id,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "quantity": quantity,
                "duration_minutes": duration_minutes,
                "pnl": pnl,
                "pnl_percentage": (exit_price - entry_price) / entry_price,
                "timeframe": timeframe,
                "strategy_info": strategy_info or {},
                "profitable": pnl > 0,
            }
            
            self.trade_history.append(trade_record)
            
            # リアルタイム収益性更新
            self._update_realtime_profitability(trade_record)
            
        except Exception as e:
            logger.error(f"Trade result recording failed: {e}")

    def _calculate_current_performance_metrics(self) -> Dict[str, PerformanceMetrics]:
        """現在のパフォーマンス指標計算"""
        try:
            metrics = {}
            
            for timeframe in self.timeframes:
                # 予測精度指標計算
                predictions = list(self.performance_history[f"{timeframe}_predictions"])
                trades = [t for t in self.trade_history if t["timeframe"] == timeframe]
                
                if len(predictions) >= 10:  # 最低10件の予測が必要
                    accuracy = np.mean([p["correct"] for p in predictions])
                    
                    # その他の精度指標
                    true_positives = sum(1 for p in predictions 
                                       if p["prediction"] == 1 and p["actual_result"] == 1)
                    false_positives = sum(1 for p in predictions 
                                        if p["prediction"] == 1 and p["actual_result"] == 0)
                    false_negatives = sum(1 for p in predictions 
                                        if p["prediction"] == 0 and p["actual_result"] == 1)
                    
                    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
                    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
                    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                else:
                    accuracy = precision = recall = f1_score = 0.5
                    
                # 取引収益性指標計算
                if len(trades) >= 5:  # 最低5件の取引が必要
                    total_return = sum(t["pnl_percentage"] for t in trades)
                    returns = np.array([t["pnl_percentage"] for t in trades])
                    
                    # シャープレシオ・ソルティノレシオ
                    if np.std(returns) > 0:
                        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
                        negative_returns = returns[returns < 0]
                        if len(negative_returns) > 0:
                            sortino_ratio = np.mean(returns) / np.std(negative_returns) * np.sqrt(252)
                        else:
                            sortino_ratio = sharpe_ratio
                    else:
                        sharpe_ratio = sortino_ratio = 0.0
                        
                    win_rate = np.mean([t["profitable"] for t in trades])
                    
                    # プロフィットファクター
                    gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
                    gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))
                    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                    
                    # ドローダウン計算
                    cumulative_returns = np.cumsum(returns)
                    running_max = np.maximum.accumulate(cumulative_returns)
                    drawdown = cumulative_returns - running_max
                    max_drawdown = np.min(drawdown)
                    
                    # リスク指標
                    volatility = np.std(returns) * np.sqrt(252)
                    var_95 = np.percentile(returns, 5)
                    expected_shortfall = np.mean(returns[returns <= var_95])
                    
                    # 取引統計
                    avg_trade_duration = np.mean([t["duration_minutes"] for t in trades])
                    consecutive_losses = self._calculate_consecutive_losses(trades)
                    consecutive_wins = self._calculate_consecutive_wins(trades)
                    
                else:
                    total_return = sharpe_ratio = sortino_ratio = 0.0
                    win_rate = profit_factor = 0.5
                    max_drawdown = volatility = var_95 = expected_shortfall = 0.0
                    avg_trade_duration = consecutive_losses = consecutive_wins = 0
                    
                metrics[timeframe] = PerformanceMetrics(
                    timestamp=datetime.now(),
                    timeframe=timeframe,
                    accuracy=accuracy,
                    precision=precision,
                    recall=recall,
                    f1_score=f1_score,
                    total_return=total_return,
                    sharpe_ratio=sharpe_ratio,
                    sortino_ratio=sortino_ratio,
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    max_drawdown=max_drawdown,
                    volatility=volatility,
                    var_95=var_95,
                    expected_shortfall=expected_shortfall,
                    total_trades=len(trades),
                    avg_trade_duration=avg_trade_duration,
                    consecutive_losses=consecutive_losses,
                    consecutive_wins=consecutive_wins,
                )
                
            return metrics
            
        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {}

    def _check_performance_thresholds(
        self, current_metrics: Dict[str, PerformanceMetrics]
    ) -> List[PerformanceAlert]:
        """パフォーマンス閾値チェック"""
        alerts = []
        
        try:
            for timeframe, metrics in current_metrics.items():
                # 精度閾値チェック
                if metrics.accuracy < self.accuracy_threshold:
                    alerts.append(PerformanceAlert(
                        timestamp=datetime.now(),
                        alert_id=f"accuracy_low_{timeframe}",
                        level=AlertLevel.WARNING,
                        metric_name="accuracy",
                        current_value=metrics.accuracy,
                        threshold_value=self.accuracy_threshold,
                        message=f"{timeframe} accuracy below threshold: {metrics.accuracy:.3f} < {self.accuracy_threshold}",
                        context={"timeframe": timeframe, "total_predictions": len(self.performance_history[f"{timeframe}_predictions"])}
                    ))
                    
                # 勝率閾値チェック
                if metrics.win_rate < self.win_rate_threshold:
                    alerts.append(PerformanceAlert(
                        timestamp=datetime.now(),
                        alert_id=f"win_rate_low_{timeframe}",
                        level=AlertLevel.WARNING,
                        metric_name="win_rate",
                        current_value=metrics.win_rate,
                        threshold_value=self.win_rate_threshold,
                        message=f"{timeframe} win rate below threshold: {metrics.win_rate:.3f} < {self.win_rate_threshold}",
                        context={"timeframe": timeframe, "total_trades": metrics.total_trades}
                    ))
                    
                # シャープレシオ閾値チェック
                if metrics.sharpe_ratio < self.sharpe_threshold:
                    alerts.append(PerformanceAlert(
                        timestamp=datetime.now(),
                        alert_id=f"sharpe_low_{timeframe}",
                        level=AlertLevel.WARNING,
                        metric_name="sharpe_ratio",
                        current_value=metrics.sharpe_ratio,
                        threshold_value=self.sharpe_threshold,
                        message=f"{timeframe} Sharpe ratio below threshold: {metrics.sharpe_ratio:.3f} < {self.sharpe_threshold}",
                        context={"timeframe": timeframe, "volatility": metrics.volatility}
                    ))
                    
                # ドローダウン閾値チェック
                if metrics.max_drawdown < self.max_drawdown_threshold:
                    alert_level = AlertLevel.CRITICAL if metrics.max_drawdown < self.max_drawdown_threshold * 1.5 else AlertLevel.WARNING
                    alerts.append(PerformanceAlert(
                        timestamp=datetime.now(),
                        alert_id=f"drawdown_high_{timeframe}",
                        level=alert_level,
                        metric_name="max_drawdown",
                        current_value=metrics.max_drawdown,
                        threshold_value=self.max_drawdown_threshold,
                        message=f"{timeframe} max drawdown exceeded: {metrics.max_drawdown:.3f} < {self.max_drawdown_threshold}",
                        context={"timeframe": timeframe, "total_return": metrics.total_return}
                    ))
                    
                # 連続損失チェック
                if metrics.consecutive_losses >= self.consecutive_loss_threshold:
                    alert_level = AlertLevel.CRITICAL if metrics.consecutive_losses >= self.consecutive_loss_threshold * 1.5 else AlertLevel.WARNING
                    alerts.append(PerformanceAlert(
                        timestamp=datetime.now(),
                        alert_id=f"consecutive_losses_{timeframe}",
                        level=alert_level,
                        metric_name="consecutive_losses",
                        current_value=metrics.consecutive_losses,
                        threshold_value=self.consecutive_loss_threshold,
                        message=f"{timeframe} consecutive losses: {metrics.consecutive_losses} >= {self.consecutive_loss_threshold}",
                        context={"timeframe": timeframe, "recent_win_rate": metrics.win_rate}
                    ))
                    
        except Exception as e:
            logger.error(f"Threshold checking failed: {e}")
            
        return alerts

    def _detect_statistical_degradation(
        self, current_metrics: Dict[str, PerformanceMetrics]
    ) -> List[PerformanceAlert]:
        """統計的性能劣化検知"""
        alerts = []
        
        try:
            self.monitor_stats["statistical_tests_performed"] += 1
            
            for timeframe, metrics in current_metrics.items():
                # 最近の性能データ更新
                self.recent_metrics[f"{timeframe}_accuracy"].append(metrics.accuracy)
                self.recent_metrics[f"{timeframe}_win_rate"].append(metrics.win_rate)
                self.recent_metrics[f"{timeframe}_sharpe"].append(metrics.sharpe_ratio)
                
                # ベースライン性能データ更新（初期期間）
                if len(self.baseline_metrics[f"{timeframe}_accuracy"]) < 100:
                    self.baseline_metrics[f"{timeframe}_accuracy"].append(metrics.accuracy)
                    self.baseline_metrics[f"{timeframe}_win_rate"].append(metrics.win_rate)
                    self.baseline_metrics[f"{timeframe}_sharpe"].append(metrics.sharpe_ratio)
                    continue
                    
                # 十分なデータがある場合のみ統計検定実行
                if len(self.recent_metrics[f"{timeframe}_accuracy"]) < self.min_samples_for_test:
                    continue
                    
                # t-検定による性能劣化検知
                for metric_name in ["accuracy", "win_rate", "sharpe"]:
                    baseline_data = list(self.baseline_metrics[f"{timeframe}_{metric_name}"])
                    recent_data = list(self.recent_metrics[f"{timeframe}_{metric_name}"])[-self.degradation_window:]
                    
                    if len(baseline_data) >= self.min_samples_for_test and len(recent_data) >= self.min_samples_for_test:
                        try:
                            # Welchのt検定（分散が等しくない場合に対応）
                            t_stat, p_value = stats.ttest_ind(recent_data, baseline_data, equal_var=False)
                            
                            # 性能劣化（recent < baseline）の検定
                            if t_stat < 0 and p_value < self.degradation_significance:
                                current_mean = np.mean(recent_data)
                                baseline_mean = np.mean(baseline_data)
                                degradation_magnitude = (baseline_mean - current_mean) / baseline_mean
                                
                                alert_level = AlertLevel.CRITICAL if degradation_magnitude > 0.1 else AlertLevel.WARNING
                                
                                alerts.append(PerformanceAlert(
                                    timestamp=datetime.now(),
                                    alert_id=f"degradation_{timeframe}_{metric_name}",
                                    level=alert_level,
                                    metric_name=f"{metric_name}_degradation",
                                    current_value=current_mean,
                                    threshold_value=baseline_mean,
                                    message=f"{timeframe} {metric_name} statistically degraded: "
                                           f"{current_mean:.3f} vs {baseline_mean:.3f} "
                                           f"(p={p_value:.4f}, magnitude={degradation_magnitude:.2%})",
                                    context={
                                        "timeframe": timeframe,
                                        "p_value": p_value,
                                        "t_statistic": t_stat,
                                        "degradation_magnitude": degradation_magnitude,
                                        "sample_sizes": {"recent": len(recent_data), "baseline": len(baseline_data)}
                                    }
                                ))
                                
                                self.monitor_stats["degradation_detections"] += 1
                                
                        except Exception as test_error:
                            logger.warning(f"Statistical test failed for {timeframe} {metric_name}: {test_error}")
                            
        except Exception as e:
            logger.error(f"Statistical degradation detection failed: {e}")
            
        return alerts

    def _process_alert(self, alert: PerformanceAlert):
        """アラート処理"""
        try:
            # クールダウンチェック
            if alert.alert_id in self.last_alert_times:
                time_since_last = datetime.now() - self.last_alert_times[alert.alert_id]
                if time_since_last < timedelta(minutes=self.alert_cooldown):
                    return
                    
            # アラート記録
            self.alert_history.append(alert)
            self.last_alert_times[alert.alert_id] = alert.timestamp
            self.monitor_stats["alerts_generated"] += 1
            
            if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
                self.monitor_stats["critical_alerts"] += 1
                
            # ログ出力
            log_level = {
                AlertLevel.INFO: logging.INFO,
                AlertLevel.WARNING: logging.WARNING,
                AlertLevel.CRITICAL: logging.CRITICAL,
                AlertLevel.EMERGENCY: logging.CRITICAL
            }[alert.level]
            
            logger.log(log_level, f"🚨 Performance Alert [{alert.level.value.upper()}]: {alert.message}")
            
            # 外部アラート送信
            if self.enable_alerts:
                self._send_external_alert(alert)
                
        except Exception as e:
            logger.error(f"Alert processing failed: {e}")

    def _send_external_alert(self, alert: PerformanceAlert):
        """外部アラート送信"""
        try:
            # Webhook アラート
            if self.webhook_alerts and self.webhook_url:
                import requests
                
                payload = {
                    "alert_id": alert.alert_id,
                    "level": alert.level.value,
                    "message": alert.message,
                    "metric": alert.metric_name,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold_value,
                    "timestamp": alert.timestamp.isoformat(),
                    "context": alert.context
                }
                
                try:
                    response = requests.post(
                        self.webhook_url,
                        json=payload,
                        timeout=10
                    )
                    logger.info(f"Webhook alert sent: {response.status_code}")
                except Exception as webhook_error:
                    logger.error(f"Webhook alert failed: {webhook_error}")
                    
        except Exception as e:
            logger.error(f"External alert sending failed: {e}")

    def _evaluate_emergency_stop(self, alerts: List[PerformanceAlert]):
        """緊急停止評価"""
        try:
            # 緊急停止条件チェック
            emergency_conditions = [
                # 複数の重大アラート
                len([a for a in alerts if a.level == AlertLevel.CRITICAL]) >= 2,
                
                # 極端な劣化
                any(a.level == AlertLevel.EMERGENCY for a in alerts),
                
                # 複数タイムフレームで同時劣化
                len(set(a.context.get("timeframe") for a in alerts if a.level in [AlertLevel.CRITICAL, AlertLevel.WARNING])) >= 2
            ]
            
            if any(emergency_conditions) and not self.auto_stop_triggered:
                self._trigger_emergency_stop(alerts)
                
        except Exception as e:
            logger.error(f"Emergency stop evaluation failed: {e}")

    def _trigger_emergency_stop(self, alerts: List[PerformanceAlert]):
        """緊急停止実行"""
        try:
            logger.critical("🚨 EMERGENCY STOP TRIGGERED - Trading system halted")
            
            self.auto_stop_triggered = True
            self.current_status = "emergency_stopped"
            self.monitor_stats["emergency_stops"] += 1
            
            # 緊急停止アラート生成
            emergency_alert = PerformanceAlert(
                timestamp=datetime.now(),
                alert_id="emergency_stop",
                level=AlertLevel.EMERGENCY,
                metric_name="system_status",
                current_value=0.0,
                threshold_value=1.0,
                message=f"Emergency stop triggered due to {len(alerts)} critical performance issues",
                context={
                    "trigger_alerts": [a.alert_id for a in alerts],
                    "stop_reason": "multiple_critical_alerts"
                }
            )
            
            self.alert_history.append(emergency_alert)
            
            # コールバック実行（取引システム停止）
            if self.emergency_stop_callback:
                try:
                    self.emergency_stop_callback()
                    logger.info("Emergency stop callback executed successfully")
                except Exception as callback_error:
                    logger.error(f"Emergency stop callback failed: {callback_error}")
                    
            # 外部通知
            if self.enable_alerts:
                self._send_external_alert(emergency_alert)
                
        except Exception as e:
            logger.error(f"Emergency stop execution failed: {e}")

    def _calculate_consecutive_losses(self, trades: List[Dict]) -> int:
        """連続損失数計算"""
        if not trades:
            return 0
            
        consecutive = 0
        for trade in reversed(trades):
            if not trade["profitable"]:
                consecutive += 1
            else:
                break
                
        return consecutive

    def _calculate_consecutive_wins(self, trades: List[Dict]) -> int:
        """連続勝利数計算"""
        if not trades:
            return 0
            
        consecutive = 0
        for trade in reversed(trades):
            if trade["profitable"]:
                consecutive += 1
            else:
                break
                
        return consecutive

    def _update_realtime_accuracy(self, timeframe: str, result_record: Dict):
        """リアルタイム精度更新"""
        try:
            # 直近の精度計算
            recent_predictions = list(self.performance_history[f"{timeframe}_predictions"])[-50:]
            if len(recent_predictions) >= 10:
                recent_accuracy = np.mean([p["correct"] for p in recent_predictions])
                
                # 精度低下の即座検知
                if recent_accuracy < self.accuracy_threshold * 0.9:
                    logger.warning(
                        f"⚠️ Real-time accuracy drop detected for {timeframe}: {recent_accuracy:.3f}"
                    )
                    
        except Exception as e:
            logger.error(f"Real-time accuracy update failed: {e}")

    def _update_realtime_profitability(self, trade_record: Dict):
        """リアルタイム収益性更新"""
        try:
            timeframe = trade_record["timeframe"]
            recent_trades = [t for t in list(self.trade_history)[-20:] 
                           if t["timeframe"] == timeframe]
            
            if len(recent_trades) >= 5:
                recent_win_rate = np.mean([t["profitable"] for t in recent_trades])
                
                # 勝率低下の即座検知
                if recent_win_rate < self.win_rate_threshold * 0.9:
                    logger.warning(
                        f"⚠️ Real-time win rate drop detected for {timeframe}: {recent_win_rate:.3f}"
                    )
                    
        except Exception as e:
            logger.error(f"Real-time profitability update failed: {e}")

    def _update_monitoring_statistics(self, current_metrics: Dict[str, PerformanceMetrics]):
        """監視統計更新"""
        try:
            # 稼働時間計算
            time_diff = datetime.now() - self.monitor_stats["last_update"]
            self.monitor_stats["uptime_hours"] += time_diff.total_seconds() / 3600
            self.monitor_stats["last_update"] = datetime.now()
            
            # 現在のシステム状態評価
            if not self.auto_stop_triggered:
                critical_metrics = sum(1 for metrics in current_metrics.values() 
                                     if (metrics.accuracy < self.accuracy_threshold * 0.8 or
                                         metrics.win_rate < self.win_rate_threshold * 0.8))
                
                if critical_metrics == 0:
                    self.current_status = "healthy"
                elif critical_metrics < len(self.timeframes) / 2:
                    self.current_status = "warning"
                else:
                    self.current_status = "critical"
                    
        except Exception as e:
            logger.error(f"Monitoring statistics update failed: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリー取得"""
        try:
            current_metrics = self._calculate_current_performance_metrics()
            
            summary = {
                "timestamp": datetime.now(),
                "monitoring_status": self.current_status,
                "monitoring_active": self.monitoring_active,
                "auto_stop_triggered": self.auto_stop_triggered,
                "monitor_stats": self.monitor_stats.copy(),
            }
            
            # タイムフレーム別サマリー
            timeframe_summary = {}
            for timeframe, metrics in current_metrics.items():
                timeframe_summary[timeframe] = {
                    "accuracy": metrics.accuracy,
                    "win_rate": metrics.win_rate,
                    "sharpe_ratio": metrics.sharpe_ratio,
                    "max_drawdown": metrics.max_drawdown,
                    "total_trades": metrics.total_trades,
                    "consecutive_losses": metrics.consecutive_losses,
                }
                
            summary["timeframe_performance"] = timeframe_summary
            
            # 最近のアラート
            recent_alerts = list(self.alert_history)[-10:]
            summary["recent_alerts"] = [
                {
                    "timestamp": alert.timestamp.isoformat(),
                    "level": alert.level.value,
                    "message": alert.message,
                    "metric": alert.metric_name,
                }
                for alert in recent_alerts
            ]
            
            return summary
            
        except Exception as e:
            logger.error(f"Performance summary generation failed: {e}")
            return {"error": str(e)}

    def get_degradation_analysis(self) -> Dict[str, Any]:
        """劣化分析結果取得"""
        try:
            analysis = {
                "timestamp": datetime.now(),
                "degradation_detection_active": len(self.baseline_metrics) > 0,
            }
            
            # タイムフレーム別劣化分析
            degradation_analysis = {}
            
            for timeframe in self.timeframes:
                for metric_name in ["accuracy", "win_rate", "sharpe"]:
                    baseline_key = f"{timeframe}_{metric_name}"
                    recent_key = f"{timeframe}_{metric_name}"
                    
                    if (baseline_key in self.baseline_metrics and 
                        recent_key in self.recent_metrics and
                        len(self.baseline_metrics[baseline_key]) >= self.min_samples_for_test and
                        len(self.recent_metrics[recent_key]) >= self.min_samples_for_test):
                        
                        baseline_data = list(self.baseline_metrics[baseline_key])
                        recent_data = list(self.recent_metrics[recent_key])[-self.degradation_window:]
                        
                        baseline_mean = np.mean(baseline_data)
                        recent_mean = np.mean(recent_data)
                        
                        if baseline_mean > 0:
                            change_percentage = (recent_mean - baseline_mean) / baseline_mean
                        else:
                            change_percentage = 0.0
                            
                        degradation_analysis[f"{timeframe}_{metric_name}"] = {
                            "baseline_mean": baseline_mean,
                            "recent_mean": recent_mean,
                            "change_percentage": change_percentage,
                            "baseline_samples": len(baseline_data),
                            "recent_samples": len(recent_data),
                        }
                        
            analysis["degradation_analysis"] = degradation_analysis
            return analysis
            
        except Exception as e:
            logger.error(f"Degradation analysis failed: {e}")
            return {"error": str(e)}

    def reset_statistics(self):
        """統計リセット"""
        try:
            # データ履歴クリア
            for timeframe in self.timeframes:
                self.performance_history[f"{timeframe}_predictions"].clear()
                self.baseline_metrics[f"{timeframe}_accuracy"].clear()
                self.baseline_metrics[f"{timeframe}_win_rate"].clear()
                self.baseline_metrics[f"{timeframe}_sharpe"].clear()
                self.recent_metrics[f"{timeframe}_accuracy"].clear()
                self.recent_metrics[f"{timeframe}_win_rate"].clear()
                self.recent_metrics[f"{timeframe}_sharpe"].clear()
                
            self.trade_history.clear()
            self.alert_history.clear()
            self.last_alert_times.clear()
            
            # 統計リセット
            for key in self.monitor_stats:
                if isinstance(self.monitor_stats[key], (int, float)):
                    self.monitor_stats[key] = 0 if isinstance(self.monitor_stats[key], int) else 0.0
                    
            self.monitor_stats["last_update"] = datetime.now()
            
            # 状態リセット
            self.current_status = "healthy"
            self.auto_stop_triggered = False
            
            logger.info("📊 Performance monitor statistics reset")
            
        except Exception as e:
            logger.error(f"Statistics reset failed: {e}")


# ファクトリー関数

def create_performance_monitor(config: Dict[str, Any]) -> PerformanceMonitor:
    """
    パフォーマンス監視システム作成
    
    Parameters:
    -----------
    config : Dict[str, Any]
        設定辞書
        
    Returns:
    --------
    PerformanceMonitor
        初期化済みパフォーマンス監視システム
    """
    return PerformanceMonitor(config)