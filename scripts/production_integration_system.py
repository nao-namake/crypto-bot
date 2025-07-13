#!/usr/bin/env python3
# =============================================================================
# スクリプト: scripts/production_integration_system.py
# 説明:
# アンサンブル学習の本番統合・段階的導入システム
# 安全性を重視した段階的ロールアウト・A/Bテスト・フォールバック機能
# =============================================================================

import json
import logging
import os
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import yaml

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DeploymentPhase(Enum):
    """デプロイメントフェーズ"""

    MONITORING_ONLY = "monitoring_only"  # フェーズ1: 監視のみ
    SHADOW_TESTING = "shadow_testing"  # フェーズ2: シャドウテスト
    PARTIAL_DEPLOYMENT = "partial_deployment"  # フェーズ3: 部分デプロイ
    FULL_DEPLOYMENT = "full_deployment"  # フェーズ4: 全面デプロイ
    EMERGENCY_FALLBACK = "emergency_fallback"  # 緊急フォールバック


@dataclass
class DeploymentConfig:
    """デプロイメント設定"""

    phase: DeploymentPhase
    ensemble_enabled: bool
    traffic_split: float  # アンサンブルに送るトラフィックの割合 (0.0-1.0)
    confidence_threshold: float
    max_drawdown_limit: float
    min_win_rate: float
    monitoring_window_hours: int
    auto_rollback_enabled: bool
    emergency_stop_enabled: bool

    # フェーズ移行条件
    phase_advance_conditions: Dict[str, float]
    phase_rollback_conditions: Dict[str, float]


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""

    timestamp: datetime
    strategy_type: str  # "traditional" or "ensemble"
    win_rate: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    avg_confidence: float
    signal_count: int
    error_count: int


@dataclass
class ABTestResult:
    """A/Bテスト結果"""

    start_time: datetime
    end_time: datetime
    traditional_metrics: PerformanceMetrics
    ensemble_metrics: PerformanceMetrics
    statistical_significance: float
    improvement_confidence: float
    recommendation: str  # "deploy", "continue_testing", "rollback"


class ProductionIntegrationSystem:
    """本番統合システム"""

    def __init__(self, config_path: str = None):
        """
        本番統合システム初期化

        Parameters:
        -----------
        config_path : str
            設定ファイルパス
        """
        self.config_path = config_path or str(
            project_root / "config" / "production_integration.yml"
        )
        self.deployment_config = self._load_deployment_config()

        # 状態管理
        self.current_phase = self.deployment_config.phase
        self.is_running = False
        self.emergency_stop = False

        # メトリクス収集
        self.traditional_metrics = []
        self.ensemble_metrics = []
        self.ab_test_results = []

        # 監視スレッド
        self.monitoring_thread = None
        self.performance_lock = threading.Lock()

        # ステータスファイル
        self.status_file = project_root / "status_integration.json"

        logger.info(
            f"Production Integration System initialized - Phase: {self.current_phase.value}"
        )

    def _load_deployment_config(self) -> DeploymentConfig:
        """デプロイメント設定読み込み"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = yaml.safe_load(f)
            else:
                config_data = self._get_default_deployment_config()
                self._save_deployment_config(config_data)

            return DeploymentConfig(
                phase=DeploymentPhase(config_data.get("phase", "monitoring_only")),
                ensemble_enabled=config_data.get("ensemble_enabled", False),
                traffic_split=config_data.get("traffic_split", 0.0),
                confidence_threshold=config_data.get("confidence_threshold", 0.65),
                max_drawdown_limit=config_data.get("max_drawdown_limit", -0.05),
                min_win_rate=config_data.get("min_win_rate", 0.55),
                monitoring_window_hours=config_data.get("monitoring_window_hours", 24),
                auto_rollback_enabled=config_data.get("auto_rollback_enabled", True),
                emergency_stop_enabled=config_data.get("emergency_stop_enabled", True),
                phase_advance_conditions=config_data.get(
                    "phase_advance_conditions",
                    {
                        "min_improvement": 0.02,  # 2%以上の改善
                        "min_confidence": 0.8,  # 80%以上の信頼度
                        "max_drawdown": -0.03,  # 3%以下のドローダウン
                        "min_trades": 10,  # 最低10取引
                    },
                ),
                phase_rollback_conditions=config_data.get(
                    "phase_rollback_conditions",
                    {
                        "max_drawdown": -0.08,  # 8%以上のドローダウンで緊急停止
                        "min_win_rate": 0.4,  # 勝率40%以下で停止
                        "max_error_rate": 0.05,  # エラー率5%以上で停止
                    },
                ),
            )
        except Exception as e:
            logger.error(f"Failed to load deployment config: {e}")
            return self._get_default_deployment_config_object()

    def _get_default_deployment_config(self) -> Dict:
        """デフォルトデプロイメント設定"""
        return {
            "phase": "monitoring_only",
            "ensemble_enabled": False,
            "traffic_split": 0.0,
            "confidence_threshold": 0.65,
            "max_drawdown_limit": -0.05,
            "min_win_rate": 0.55,
            "monitoring_window_hours": 24,
            "auto_rollback_enabled": True,
            "emergency_stop_enabled": True,
            "phase_advance_conditions": {
                "min_improvement": 0.02,
                "min_confidence": 0.8,
                "max_drawdown": -0.03,
                "min_trades": 10,
            },
            "phase_rollback_conditions": {
                "max_drawdown": -0.08,
                "min_win_rate": 0.4,
                "max_error_rate": 0.05,
            },
        }

    def _get_default_deployment_config_object(self) -> DeploymentConfig:
        """デフォルトデプロイメント設定オブジェクト"""
        config_data = self._get_default_deployment_config()
        return DeploymentConfig(**config_data)

    def _save_deployment_config(self, config_data: Dict):
        """デプロイメント設定保存"""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Failed to save deployment config: {e}")

    def start_integration(self):
        """統合プロセス開始"""
        logger.info("Starting production integration process...")

        if self.is_running:
            logger.warning("Integration process already running")
            return

        self.is_running = True
        self.emergency_stop = False

        # 監視スレッド開始
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.monitoring_thread.start()

        # 現在のフェーズに応じた処理開始
        self._execute_current_phase()

        logger.info(f"Integration started in phase: {self.current_phase.value}")

    def stop_integration(self):
        """統合プロセス停止"""
        logger.info("Stopping production integration process...")

        self.is_running = False

        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)

        self._update_status()
        logger.info("Integration process stopped")

    def emergency_stop_system(self, reason: str = "Manual trigger"):
        """緊急停止"""
        logger.critical(f"EMERGENCY STOP triggered: {reason}")

        self.emergency_stop = True
        self.current_phase = DeploymentPhase.EMERGENCY_FALLBACK

        # 設定を安全な状態に戻す
        self.deployment_config.ensemble_enabled = False
        self.deployment_config.traffic_split = 0.0

        # 本番設定ファイル更新
        self._update_production_config(ensemble_enabled=False)

        # ステータス更新
        self._update_status(
            {
                "emergency_stop": True,
                "stop_reason": reason,
                "stop_time": datetime.now().isoformat(),
            }
        )

        logger.critical("System switched to emergency fallback mode")

    def advance_to_next_phase(self):
        """次のフェーズに進む"""
        phase_sequence = [
            DeploymentPhase.MONITORING_ONLY,
            DeploymentPhase.SHADOW_TESTING,
            DeploymentPhase.PARTIAL_DEPLOYMENT,
            DeploymentPhase.FULL_DEPLOYMENT,
        ]

        try:
            current_index = phase_sequence.index(self.current_phase)
            if current_index < len(phase_sequence) - 1:
                next_phase = phase_sequence[current_index + 1]

                # 進歩条件チェック
                if self._check_advance_conditions():
                    self._transition_to_phase(next_phase)
                    logger.info(f"Advanced to phase: {next_phase.value}")
                else:
                    logger.warning(
                        "Advance conditions not met, staying in current phase"
                    )
            else:
                logger.info("Already in final deployment phase")

        except ValueError:
            logger.error(f"Unknown current phase: {self.current_phase}")

    def rollback_to_previous_phase(self, reason: str = "Performance degradation"):
        """前のフェーズにロールバック"""
        phase_sequence = [
            DeploymentPhase.MONITORING_ONLY,
            DeploymentPhase.SHADOW_TESTING,
            DeploymentPhase.PARTIAL_DEPLOYMENT,
            DeploymentPhase.FULL_DEPLOYMENT,
        ]

        try:
            current_index = phase_sequence.index(self.current_phase)
            if current_index > 0:
                previous_phase = phase_sequence[current_index - 1]
                self._transition_to_phase(previous_phase)
                logger.warning(
                    f"Rolled back to phase: {previous_phase.value} - Reason: {reason}"
                )
            else:
                logger.warning("Already in initial phase, cannot rollback further")

        except ValueError:
            logger.error(f"Unknown current phase for rollback: {self.current_phase}")

    def _transition_to_phase(self, new_phase: DeploymentPhase):
        """フェーズ移行"""
        old_phase = self.current_phase
        self.current_phase = new_phase

        # フェーズ別設定更新
        phase_configs = {
            DeploymentPhase.MONITORING_ONLY: {
                "ensemble_enabled": False,
                "traffic_split": 0.0,
            },
            DeploymentPhase.SHADOW_TESTING: {
                "ensemble_enabled": True,  # バックグラウンドで実行
                "traffic_split": 0.0,  # まだ本番トラフィックは送らない
            },
            DeploymentPhase.PARTIAL_DEPLOYMENT: {
                "ensemble_enabled": True,
                "traffic_split": 0.1,  # 10%のトラフィック
            },
            DeploymentPhase.FULL_DEPLOYMENT: {
                "ensemble_enabled": True,
                "traffic_split": 1.0,  # 100%のトラフィック
            },
            DeploymentPhase.EMERGENCY_FALLBACK: {
                "ensemble_enabled": False,
                "traffic_split": 0.0,
            },
        }

        if new_phase in phase_configs:
            config = phase_configs[new_phase]
            self.deployment_config.ensemble_enabled = config["ensemble_enabled"]
            self.deployment_config.traffic_split = config["traffic_split"]

            # 本番設定更新
            self._update_production_config(
                ensemble_enabled=config["ensemble_enabled"],
                traffic_split=config["traffic_split"],
            )

        # ステータス更新
        self._update_status(
            {
                "phase_transition": {
                    "from": old_phase.value,
                    "to": new_phase.value,
                    "timestamp": datetime.now().isoformat(),
                }
            }
        )

        logger.info(f"Phase transition: {old_phase.value} -> {new_phase.value}")

    def _execute_current_phase(self):
        """現在フェーズの実行"""
        if self.current_phase == DeploymentPhase.MONITORING_ONLY:
            self._execute_monitoring_phase()
        elif self.current_phase == DeploymentPhase.SHADOW_TESTING:
            self._execute_shadow_testing_phase()
        elif self.current_phase == DeploymentPhase.PARTIAL_DEPLOYMENT:
            self._execute_partial_deployment_phase()
        elif self.current_phase == DeploymentPhase.FULL_DEPLOYMENT:
            self._execute_full_deployment_phase()
        elif self.current_phase == DeploymentPhase.EMERGENCY_FALLBACK:
            self._execute_emergency_fallback_phase()

    def _execute_monitoring_phase(self):
        """監視フェーズ実行"""
        logger.info("Executing monitoring only phase...")

        # 従来システムのみ稼働、メトリクス収集
        self._update_production_config(ensemble_enabled=False, monitoring_enhanced=True)

        # ベースライン性能測定
        self._start_baseline_measurement()

    def _execute_shadow_testing_phase(self):
        """シャドウテストフェーズ実行"""
        logger.info("Executing shadow testing phase...")

        # アンサンブルをバックグラウンドで実行（実際の取引には使用しない）
        self._update_production_config(
            ensemble_enabled=True,
            ensemble_mode="shadow",  # シャドウモード
            traffic_split=0.0,
        )

        # A/Bテスト開始
        self._start_ab_test()

    def _execute_partial_deployment_phase(self):
        """部分デプロイフェーズ実行"""
        logger.info("Executing partial deployment phase...")

        # 10%のトラフィックをアンサンブルに送る
        self._update_production_config(
            ensemble_enabled=True, ensemble_mode="live", traffic_split=0.1
        )

        # リアルタイム比較監視
        self._start_real_time_comparison()

    def _execute_full_deployment_phase(self):
        """全面デプロイフェーズ実行"""
        logger.info("Executing full deployment phase...")

        # 100%のトラフィックをアンサンブルに送る
        self._update_production_config(
            ensemble_enabled=True, ensemble_mode="live", traffic_split=1.0
        )

        # 継続監視
        self._start_continuous_monitoring()

    def _execute_emergency_fallback_phase(self):
        """緊急フォールバックフェーズ実行"""
        logger.critical("Executing emergency fallback phase...")

        # 従来システムに完全復帰
        self._update_production_config(ensemble_enabled=False, emergency_mode=True)

        # 緊急通知
        self._send_emergency_notification()

    def _monitoring_loop(self):
        """監視ループ"""
        while self.is_running and not self.emergency_stop:
            try:
                # パフォーマンス監視
                self._check_performance_metrics()

                # 自動フェーズ移行チェック
                if self.deployment_config.auto_rollback_enabled:
                    self._check_auto_transitions()

                # ステータス更新
                self._update_status()

                time.sleep(60)  # 1分間隔

            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)

    def _check_performance_metrics(self):
        """パフォーマンスメトリクス確認"""
        try:
            # 現在のメトリクス取得（実際の実装では本番システムから取得）
            current_metrics = self._get_current_metrics()

            if current_metrics:
                # メトリクス記録
                with self.performance_lock:
                    if current_metrics.strategy_type == "traditional":
                        self.traditional_metrics.append(current_metrics)
                    elif current_metrics.strategy_type == "ensemble":
                        self.ensemble_metrics.append(current_metrics)

                # 異常検知
                self._check_performance_anomalies(current_metrics)

        except Exception as e:
            logger.error(f"Performance metrics check failed: {e}")

    def _get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """現在のメトリクス取得（模擬実装）"""
        # 実際の実装では本番システムのメトリクス収集APIを呼び出し

        # 模擬データ生成
        if np.random.random() < 0.1:  # 10%の確率でメトリクス更新
            strategy_type = (
                "ensemble" if self.deployment_config.ensemble_enabled else "traditional"
            )

            # ベースライン性能
            base_win_rate = 0.58
            base_return = 0.02
            base_sharpe = 1.2

            # アンサンブル効果（改善）
            if strategy_type == "ensemble":
                base_win_rate += 0.05  # 5%改善
                base_return += 0.01  # 1%改善
                base_sharpe += 0.3  # 0.3改善

            return PerformanceMetrics(
                timestamp=datetime.now(),
                strategy_type=strategy_type,
                win_rate=base_win_rate + np.random.normal(0, 0.02),
                total_return=base_return + np.random.normal(0, 0.005),
                sharpe_ratio=base_sharpe + np.random.normal(0, 0.1),
                max_drawdown=np.random.uniform(-0.08, -0.01),
                total_trades=np.random.randint(50, 150),
                avg_confidence=np.random.uniform(0.6, 0.85),
                signal_count=np.random.randint(100, 300),
                error_count=np.random.randint(0, 5),
            )

        return None

    def _check_performance_anomalies(self, metrics: PerformanceMetrics):
        """パフォーマンス異常検知"""
        rollback_conditions = self.deployment_config.phase_rollback_conditions

        # 緊急停止条件チェック
        if (
            metrics.max_drawdown < rollback_conditions["max_drawdown"]
            or metrics.win_rate < rollback_conditions["min_win_rate"]
            or metrics.error_count / max(metrics.signal_count, 1)
            > rollback_conditions["max_error_rate"]
        ):

            self.emergency_stop_system(
                f"Performance anomaly detected: WinRate={metrics.win_rate:.2%}, "
                f"Drawdown={metrics.max_drawdown:.2%}, ErrorRate={metrics.error_count/max(metrics.signal_count, 1):.2%}"
            )

    def _check_advance_conditions(self) -> bool:
        """進歩条件チェック"""
        if len(self.traditional_metrics) < 10 or len(self.ensemble_metrics) < 10:
            return False

        # 最新メトリクス比較
        recent_traditional = self.traditional_metrics[-10:]
        recent_ensemble = self.ensemble_metrics[-10:]

        avg_traditional_return = np.mean([m.total_return for m in recent_traditional])
        avg_ensemble_return = np.mean([m.total_return for m in recent_ensemble])

        improvement = avg_ensemble_return - avg_traditional_return

        advance_conditions = self.deployment_config.phase_advance_conditions

        return (
            improvement >= advance_conditions["min_improvement"]
            and len(recent_ensemble) >= advance_conditions["min_trades"]
        )

    def _check_auto_transitions(self):
        """自動移行チェック"""
        # ロールバック条件チェック
        if self._should_rollback():
            self.rollback_to_previous_phase(
                "Automatic rollback due to performance degradation"
            )

        # 進歩条件チェック（自動進歩は慎重に）
        elif (
            self.current_phase in [DeploymentPhase.SHADOW_TESTING]
            and self._check_advance_conditions()
        ):
            self.advance_to_next_phase()

    def _should_rollback(self) -> bool:
        """ロールバック必要性判定"""
        if not self.ensemble_metrics:
            return False

        recent_metrics = self.ensemble_metrics[-5:]  # 最新5つのメトリクス

        # 連続的な性能低下チェック
        poor_performance_count = 0
        for metrics in recent_metrics:
            if (
                metrics.win_rate < self.deployment_config.min_win_rate
                or metrics.max_drawdown < self.deployment_config.max_drawdown_limit
            ):
                poor_performance_count += 1

        return poor_performance_count >= 3  # 3回以上連続で基準以下

    def _start_baseline_measurement(self):
        """ベースライン測定開始"""
        logger.info("Starting baseline performance measurement...")
        # 実装: 従来システムの性能測定

    def _start_ab_test(self):
        """A/Bテスト開始"""
        logger.info("Starting A/B test between traditional and ensemble strategies...")
        # 実装: 両戦略の並行実行・比較

    def _start_real_time_comparison(self):
        """リアルタイム比較開始"""
        logger.info("Starting real-time performance comparison...")
        # 実装: リアルタイム性能比較

    def _start_continuous_monitoring(self):
        """継続監視開始"""
        logger.info("Starting continuous performance monitoring...")
        # 実装: 継続的な性能監視

    def _update_production_config(self, **kwargs):
        """本番設定更新"""
        logger.info(f"Updating production config: {kwargs}")

        # 実際の実装では本番設定ファイルを更新
        # 例: bitbank_101features_production.yml の ml.ensemble セクション更新

        try:
            production_config_path = (
                project_root / "config" / "bitbank_101features_production.yml"
            )

            if production_config_path.exists():
                with open(production_config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                # アンサンブル設定更新
                if "ml" not in config:
                    config["ml"] = {}
                if "ensemble" not in config["ml"]:
                    config["ml"]["ensemble"] = {}

                for key, value in kwargs.items():
                    if key in ["ensemble_enabled", "traffic_split", "ensemble_mode"]:
                        config["ml"]["ensemble"][key] = value
                    else:
                        config[key] = value

                # 設定保存
                with open(production_config_path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

                logger.info(f"Production config updated: {production_config_path}")

        except Exception as e:
            logger.error(f"Failed to update production config: {e}")

    def _update_status(self, additional_info: Dict = None):
        """ステータス更新"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "current_phase": self.current_phase.value,
            "is_running": self.is_running,
            "emergency_stop": self.emergency_stop,
            "deployment_config": {
                "ensemble_enabled": self.deployment_config.ensemble_enabled,
                "traffic_split": self.deployment_config.traffic_split,
                "confidence_threshold": self.deployment_config.confidence_threshold,
            },
            "metrics_summary": {
                "traditional_metrics_count": len(self.traditional_metrics),
                "ensemble_metrics_count": len(self.ensemble_metrics),
                "ab_test_results_count": len(self.ab_test_results),
            },
        }

        if additional_info:
            status.update(additional_info)

        try:
            with open(self.status_file, "w", encoding="utf-8") as f:
                json.dump(status, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to update status: {e}")

    def _send_emergency_notification(self):
        """緊急通知送信"""
        logger.critical("Sending emergency notification...")

        # 実際の実装では：
        # - Slack/Discord通知
        # - メール通知
        # - SMS通知
        # - 監視システムアラート

        notification_message = {
            "title": "EMERGENCY: Trading System Fallback Activated",
            "timestamp": datetime.now().isoformat(),
            "phase": self.current_phase.value,
            "reason": "Performance degradation detected",
            "action_taken": "Switched to traditional ML strategy",
            "requires_attention": True,
        }

        # 通知ファイル保存（実際の通知の代替）
        notification_file = project_root / "emergency_notification.json"
        with open(notification_file, "w", encoding="utf-8") as f:
            json.dump(notification_message, f, indent=2, ensure_ascii=False)

        logger.critical(f"Emergency notification saved: {notification_file}")

    def get_integration_status(self) -> Dict[str, Any]:
        """統合ステータス取得"""
        with self.performance_lock:
            return {
                "current_phase": self.current_phase.value,
                "is_running": self.is_running,
                "emergency_stop": self.emergency_stop,
                "deployment_config": asdict(self.deployment_config),
                "performance_summary": self._get_performance_summary(),
                "last_update": datetime.now().isoformat(),
            }

    def _get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンスサマリー取得"""
        summary = {
            "traditional_metrics_count": len(self.traditional_metrics),
            "ensemble_metrics_count": len(self.ensemble_metrics),
        }

        if self.traditional_metrics:
            recent_traditional = self.traditional_metrics[-10:]
            summary["traditional_avg_win_rate"] = np.mean(
                [m.win_rate for m in recent_traditional]
            )
            summary["traditional_avg_return"] = np.mean(
                [m.total_return for m in recent_traditional]
            )

        if self.ensemble_metrics:
            recent_ensemble = self.ensemble_metrics[-10:]
            summary["ensemble_avg_win_rate"] = np.mean(
                [m.win_rate for m in recent_ensemble]
            )
            summary["ensemble_avg_return"] = np.mean(
                [m.total_return for m in recent_ensemble]
            )

        return summary


def main():
    """メイン実行関数"""
    print("🚀 本番統合・段階的導入システム")
    print("=" * 50)

    try:
        # 統合システム初期化
        integration_system = ProductionIntegrationSystem()

        # 対話式メニュー
        while True:
            print("\n📋 利用可能なコマンド:")
            print("1. 統合プロセス開始")
            print("2. 次フェーズに進む")
            print("3. 前フェーズにロールバック")
            print("4. 緊急停止")
            print("5. ステータス確認")
            print("6. 統合プロセス停止")
            print("0. 終了")

            choice = input("\nコマンドを選択してください (0-6): ").strip()

            if choice == "1":
                integration_system.start_integration()
                print("✅ 統合プロセスを開始しました")

            elif choice == "2":
                integration_system.advance_to_next_phase()
                print("✅ 次フェーズに進みました")

            elif choice == "3":
                reason = input("ロールバック理由を入力してください: ").strip()
                integration_system.rollback_to_previous_phase(
                    reason or "Manual rollback"
                )
                print("✅ 前フェーズにロールバックしました")

            elif choice == "4":
                reason = input("緊急停止理由を入力してください: ").strip()
                integration_system.emergency_stop_system(
                    reason or "Manual emergency stop"
                )
                print("🚨 緊急停止を実行しました")

            elif choice == "5":
                status = integration_system.get_integration_status()
                print("\n📊 現在のステータス:")
                print(f"  フェーズ: {status['current_phase']}")
                print(f"  実行中: {status['is_running']}")
                print(f"  緊急停止: {status['emergency_stop']}")
                print(
                    f"  アンサンブル有効: {status['deployment_config']['ensemble_enabled']}"
                )
                print(
                    f"  トラフィック分割: {status['deployment_config']['traffic_split']:.1%}"
                )

                if "performance_summary" in status:
                    perf = status["performance_summary"]
                    print(f"  従来メトリクス: {perf['traditional_metrics_count']}件")
                    print(
                        f"  アンサンブルメトリクス: {perf['ensemble_metrics_count']}件"
                    )

            elif choice == "6":
                integration_system.stop_integration()
                print("✅ 統合プロセスを停止しました")

            elif choice == "0":
                if integration_system.is_running:
                    integration_system.stop_integration()
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
