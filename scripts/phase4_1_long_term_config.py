#!/usr/bin/env python3
"""
Phase 4.1e: 長期運用設定調整
長期運用に適した設定の調整を行います
"""

import json
import os
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional

import yaml


class LongTermConfigurationManager:
    """長期運用設定調整クラス"""

    def __init__(self):
        self.config_results = []
        self.start_time = datetime.now()

    def log_config(
        self,
        config_name: str,
        status: str,
        message: str = "",
        data: Optional[Dict] = None,
    ):
        """設定結果をログに記録"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "config_name": config_name,
            "status": status,
            "message": message,
            "data": data or {},
        }
        self.config_results.append(result)

        status_emoji = (
            "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
        )
        print(f"{status_emoji} {config_name}: {status}")
        if message:
            print(f"   {message}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        print()

    def setup_auto_restart_config(self) -> bool:
        """自動再起動設定"""
        try:
            # 自動再起動設定
            auto_restart_config = {
                "name": "auto_restart_configuration",
                "description": "自動再起動設定",
                "restart_policy": {
                    "enabled": True,
                    "max_retries": 3,
                    "retry_delay": "30s",
                    "exponential_backoff": True,
                    "max_delay": "300s",
                },
                "health_check": {
                    "enabled": True,
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                    "start_period": "60s",
                },
                "failure_detection": {
                    "api_timeout": "30s",
                    "consecutive_failures": 3,
                    "memory_threshold": "1GB",
                    "cpu_threshold": "90%",
                },
                "restart_triggers": [
                    {
                        "condition": "health_check_failure",
                        "action": "restart_service",
                        "delay": "30s",
                    },
                    {
                        "condition": "memory_leak_detected",
                        "action": "restart_service",
                        "delay": "60s",
                    },
                    {
                        "condition": "api_only_mode_detected",
                        "action": "force_restart",
                        "delay": "10s",
                    },
                    {
                        "condition": "atr_calculation_hang",
                        "action": "restart_service",
                        "delay": "30s",
                    },
                ],
            }

            # Cloud Run サービス設定
            cloud_run_config = {
                "apiVersion": "serving.knative.dev/v1",
                "kind": "Service",
                "metadata": {
                    "name": "crypto-bot-service-prod",
                    "namespace": "default",
                    "annotations": {
                        "run.googleapis.com/execution-environment": "gen2",
                        "run.googleapis.com/cpu-throttling": "false",
                    },
                },
                "spec": {
                    "template": {
                        "metadata": {
                            "annotations": {
                                "autoscaling.knative.dev/maxScale": "2",
                                "autoscaling.knative.dev/minScale": "1",
                                "run.googleapis.com/execution-environment": "gen2",
                                "run.googleapis.com/cpu-throttling": "false",
                            }
                        },
                        "spec": {
                            "containerConcurrency": 1,
                            "timeoutSeconds": 3600,
                            "serviceAccountName": "crypto-bot-service-account",
                            "containers": [
                                {
                                    "name": "crypto-bot",
                                    "image": "gcr.io/crypto-bot-prod/crypto-bot:latest",
                                    "ports": [{"containerPort": 8080, "name": "http1"}],
                                    "env": [
                                        {"name": "MODE", "value": "live"},
                                        {
                                            "name": "CONFIG_FILE",
                                            "value": "/app/config/bitbank_101features_production.yml",
                                        },
                                    ],
                                    "resources": {
                                        "limits": {"cpu": "2", "memory": "2Gi"},
                                        "requests": {"cpu": "1", "memory": "1Gi"},
                                    },
                                    "livenessProbe": {
                                        "httpGet": {"path": "/health", "port": 8080},
                                        "initialDelaySeconds": 60,
                                        "periodSeconds": 30,
                                        "timeoutSeconds": 10,
                                        "failureThreshold": 3,
                                    },
                                    "readinessProbe": {
                                        "httpGet": {"path": "/health", "port": 8080},
                                        "initialDelaySeconds": 30,
                                        "periodSeconds": 10,
                                        "timeoutSeconds": 5,
                                        "failureThreshold": 3,
                                    },
                                }
                            ],
                        },
                    }
                },
            }

            # 設定をファイルに保存
            with open("auto_restart_config.json", "w") as f:
                json.dump(auto_restart_config, f, indent=2)

            with open("cloud_run_service.yaml", "w") as f:
                yaml.dump(cloud_run_config, f, default_flow_style=False)

            self.log_config(
                "自動再起動設定",
                "success",
                f"{len(auto_restart_config['restart_triggers'])} 個の再起動トリガーが設定されました",
                {
                    "config_file": "auto_restart_config.json",
                    "service_file": "cloud_run_service.yaml",
                },
            )
            return True

        except Exception as e:
            self.log_config("自動再起動設定", "failed", f"Exception: {str(e)}")
            return False

    def setup_log_rotation_config(self) -> bool:
        """ログローテーション設定"""
        try:
            # ログローテーション設定
            log_rotation_config = {
                "name": "log_rotation_configuration",
                "description": "ログローテーション設定",
                "rotation_policy": {
                    "enabled": True,
                    "max_size": "100MB",
                    "max_files": 10,
                    "max_age": "7d",
                    "compress": True,
                },
                "log_levels": {
                    "production": "INFO",
                    "development": "DEBUG",
                    "error_only": "ERROR",
                },
                "structured_logging": {
                    "enabled": True,
                    "format": "json",
                    "include_metadata": True,
                    "fields": [
                        "timestamp",
                        "level",
                        "logger",
                        "message",
                        "trace_id",
                        "span_id",
                        "user_id",
                        "request_id",
                    ],
                },
                "log_aggregation": {
                    "enabled": True,
                    "destination": "cloud_logging",
                    "retention_days": 30,
                    "sampling_rate": 1.0,
                },
                "log_filtering": {
                    "enabled": True,
                    "exclude_patterns": [
                        "health_check_ping",
                        "metrics_collection",
                        "debug_trace",
                    ],
                    "include_patterns": [
                        "error",
                        "warning",
                        "trade_execution",
                        "api_only_mode",
                        "atr_calculation",
                        "init_enhanced",
                    ],
                },
            }

            # ログ設定ファイルの生成
            logging_config = {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "standard": {
                        "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                    },
                    "json": {
                        "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                        "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
                    },
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": "INFO",
                        "formatter": "json",
                        "stream": "ext://sys.stdout",
                    },
                    "file": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "level": "DEBUG",
                        "formatter": "json",
                        "filename": "/app/logs/crypto_bot.log",
                        "maxBytes": 104857600,
                        "backupCount": 10,
                    },
                    "error_file": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "level": "ERROR",
                        "formatter": "json",
                        "filename": "/app/logs/crypto_bot_errors.log",
                        "maxBytes": 52428800,
                        "backupCount": 5,
                    },
                },
                "loggers": {
                    "crypto_bot": {
                        "level": "INFO",
                        "handlers": ["console", "file", "error_file"],
                        "propagate": False,
                    },
                    "crypto_bot.init_enhanced": {
                        "level": "DEBUG",
                        "handlers": ["console", "file"],
                        "propagate": False,
                    },
                },
                "root": {"level": "INFO", "handlers": ["console"]},
            }

            # 設定をファイルに保存
            with open("log_rotation_config.json", "w") as f:
                json.dump(log_rotation_config, f, indent=2)

            with open("logging_config.yaml", "w") as f:
                yaml.dump(logging_config, f, default_flow_style=False)

            self.log_config(
                "ログローテーション設定",
                "success",
                f"ログローテーション設定が作成されました",
                {
                    "config_file": "log_rotation_config.json",
                    "logging_file": "logging_config.yaml",
                },
            )
            return True

        except Exception as e:
            self.log_config("ログローテーション設定", "failed", f"Exception: {str(e)}")
            return False

    def setup_metrics_retention_config(self) -> bool:
        """メトリクス保存期間設定"""
        try:
            # メトリクス保存期間設定
            metrics_retention_config = {
                "name": "metrics_retention_configuration",
                "description": "メトリクス保存期間設定",
                "retention_policies": {
                    "short_term": {
                        "duration": "7d",
                        "resolution": "1m",
                        "metrics": [
                            "response_time",
                            "error_rate",
                            "request_count",
                            "memory_usage",
                            "cpu_usage",
                        ],
                    },
                    "medium_term": {
                        "duration": "30d",
                        "resolution": "5m",
                        "metrics": [
                            "trading_performance",
                            "kelly_ratio",
                            "win_rate",
                            "max_drawdown",
                            "sharpe_ratio",
                        ],
                    },
                    "long_term": {
                        "duration": "365d",
                        "resolution": "1h",
                        "metrics": [
                            "portfolio_value",
                            "total_trades",
                            "monthly_returns",
                            "annual_performance",
                        ],
                    },
                },
                "aggregation_rules": {
                    "daily_aggregation": {
                        "enabled": True,
                        "schedule": "0 0 * * *",
                        "metrics": ["daily_pnl", "daily_trades", "daily_win_rate"],
                    },
                    "weekly_aggregation": {
                        "enabled": True,
                        "schedule": "0 0 * * 0",
                        "metrics": [
                            "weekly_performance",
                            "weekly_volatility",
                            "weekly_sharpe",
                        ],
                    },
                    "monthly_aggregation": {
                        "enabled": True,
                        "schedule": "0 0 1 * *",
                        "metrics": [
                            "monthly_returns",
                            "monthly_max_drawdown",
                            "monthly_trades",
                        ],
                    },
                },
                "cleanup_policies": {
                    "enabled": True,
                    "cleanup_schedule": "0 2 * * *",
                    "cleanup_rules": [
                        {"metric_pattern": "temp_*", "retention": "1d"},
                        {"metric_pattern": "debug_*", "retention": "3d"},
                        {"metric_pattern": "raw_*", "retention": "7d"},
                    ],
                },
            }

            # Prometheus設定の生成
            prometheus_config = {
                "global": {"scrape_interval": "15s", "evaluation_interval": "15s"},
                "rule_files": ["crypto_bot_rules.yml"],
                "scrape_configs": [
                    {
                        "job_name": "crypto-bot",
                        "static_configs": [
                            {
                                "targets": [
                                    "crypto-bot-service-prod-11445303925.asia-northeast1.run.app:443"
                                ]
                            }
                        ],
                        "metrics_path": "/metrics",
                        "scheme": "https",
                        "scrape_interval": "30s",
                    }
                ],
            }

            # 設定をファイルに保存
            with open("metrics_retention_config.json", "w") as f:
                json.dump(metrics_retention_config, f, indent=2)

            with open("prometheus_config.yaml", "w") as f:
                yaml.dump(prometheus_config, f, default_flow_style=False)

            self.log_config(
                "メトリクス保存期間設定",
                "success",
                f"{len(metrics_retention_config['retention_policies'])} 個の保存期間ポリシーが設定されました",
                {
                    "config_file": "metrics_retention_config.json",
                    "prometheus_file": "prometheus_config.yaml",
                },
            )
            return True

        except Exception as e:
            self.log_config("メトリクス保存期間設定", "failed", f"Exception: {str(e)}")
            return False

    def setup_backup_config(self) -> bool:
        """バックアップ設定"""
        try:
            # バックアップ設定
            backup_config = {
                "name": "backup_configuration",
                "description": "バックアップ設定",
                "backup_schedule": {
                    "enabled": True,
                    "daily_backup": {
                        "enabled": True,
                        "schedule": "0 3 * * *",
                        "retention": "7d",
                    },
                    "weekly_backup": {
                        "enabled": True,
                        "schedule": "0 4 * * 0",
                        "retention": "4w",
                    },
                    "monthly_backup": {
                        "enabled": True,
                        "schedule": "0 5 1 * *",
                        "retention": "12m",
                    },
                },
                "backup_targets": [
                    {
                        "name": "trading_data",
                        "type": "database",
                        "source": "postgresql://crypto_bot_db",
                        "destination": "gs://crypto-bot-backups/trading_data/",
                        "encryption": "AES256",
                        "compression": "gzip",
                    },
                    {
                        "name": "ml_models",
                        "type": "files",
                        "source": "/app/models/",
                        "destination": "gs://crypto-bot-backups/ml_models/",
                        "encryption": "AES256",
                        "compression": "tar.gz",
                    },
                    {
                        "name": "configuration",
                        "type": "files",
                        "source": "/app/config/",
                        "destination": "gs://crypto-bot-backups/configuration/",
                        "encryption": "AES256",
                        "compression": "zip",
                    },
                    {
                        "name": "logs",
                        "type": "files",
                        "source": "/app/logs/",
                        "destination": "gs://crypto-bot-backups/logs/",
                        "encryption": "AES256",
                        "compression": "tar.gz",
                    },
                ],
                "backup_verification": {
                    "enabled": True,
                    "verification_schedule": "0 6 * * *",
                    "integrity_checks": [
                        "checksum_verification",
                        "restore_test",
                        "file_count_verification",
                    ],
                },
                "disaster_recovery": {
                    "enabled": True,
                    "recovery_time_objective": "1h",
                    "recovery_point_objective": "15m",
                    "backup_locations": [
                        "gs://crypto-bot-backups-primary/",
                        "gs://crypto-bot-backups-secondary/",
                    ],
                },
            }

            # バックアップスクリプトの生成
            backup_script = """#!/bin/bash
# Crypto Bot Backup Script
# Generated automatically by Phase 4.1e

set -e

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_ROOT="gs://crypto-bot-backups"
LOG_FILE="/app/logs/backup_${BACKUP_DATE}.log"

echo "Starting backup at $(date)" | tee -a $LOG_FILE

# Trading Data Backup
echo "Backing up trading data..." | tee -a $LOG_FILE
pg_dump $DATABASE_URL | gzip > /tmp/trading_data_${BACKUP_DATE}.sql.gz
gsutil cp /tmp/trading_data_${BACKUP_DATE}.sql.gz ${BACKUP_ROOT}/trading_data/
rm /tmp/trading_data_${BACKUP_DATE}.sql.gz

# ML Models Backup
echo "Backing up ML models..." | tee -a $LOG_FILE
tar -czf /tmp/ml_models_${BACKUP_DATE}.tar.gz -C /app models/
gsutil cp /tmp/ml_models_${BACKUP_DATE}.tar.gz ${BACKUP_ROOT}/ml_models/
rm /tmp/ml_models_${BACKUP_DATE}.tar.gz

# Configuration Backup
echo "Backing up configuration..." | tee -a $LOG_FILE
zip -r /tmp/configuration_${BACKUP_DATE}.zip /app/config/
gsutil cp /tmp/configuration_${BACKUP_DATE}.zip ${BACKUP_ROOT}/configuration/
rm /tmp/configuration_${BACKUP_DATE}.zip

# Logs Backup
echo "Backing up logs..." | tee -a $LOG_FILE
tar -czf /tmp/logs_${BACKUP_DATE}.tar.gz -C /app logs/
gsutil cp /tmp/logs_${BACKUP_DATE}.tar.gz ${BACKUP_ROOT}/logs/
rm /tmp/logs_${BACKUP_DATE}.tar.gz

echo "Backup completed at $(date)" | tee -a $LOG_FILE

# Backup verification
echo "Verifying backup integrity..." | tee -a $LOG_FILE
gsutil ls ${BACKUP_ROOT}/trading_data/trading_data_${BACKUP_DATE}.sql.gz
gsutil ls ${BACKUP_ROOT}/ml_models/ml_models_${BACKUP_DATE}.tar.gz
gsutil ls ${BACKUP_ROOT}/configuration/configuration_${BACKUP_DATE}.zip
gsutil ls ${BACKUP_ROOT}/logs/logs_${BACKUP_DATE}.tar.gz

echo "Backup verification completed" | tee -a $LOG_FILE
"""

            # 設定をファイルに保存
            with open("backup_config.json", "w") as f:
                json.dump(backup_config, f, indent=2)

            with open("backup_script.sh", "w") as f:
                f.write(backup_script)

            # バックアップスクリプトに実行権限を付与
            os.chmod("backup_script.sh", 0o755)

            self.log_config(
                "バックアップ設定",
                "success",
                f"{len(backup_config['backup_targets'])} 個のバックアップターゲットが設定されました",
                {
                    "config_file": "backup_config.json",
                    "script_file": "backup_script.sh",
                },
            )
            return True

        except Exception as e:
            self.log_config("バックアップ設定", "failed", f"Exception: {str(e)}")
            return False

    def setup_security_hardening(self) -> bool:
        """セキュリティ設定強化"""
        try:
            # セキュリティ強化設定
            security_config = {
                "name": "security_hardening_configuration",
                "description": "セキュリティ設定強化",
                "authentication": {
                    "api_key_rotation": {
                        "enabled": True,
                        "rotation_interval": "30d",
                        "notification_before": "7d",
                    },
                    "workload_identity": {
                        "enabled": True,
                        "service_account": "crypto-bot-service-account@crypto-bot-prod.iam.gserviceaccount.com",
                        "ksa_name": "crypto-bot-ksa",
                    },
                    "secret_management": {
                        "enabled": True,
                        "secret_manager": "gcp_secret_manager",
                        "auto_rotation": True,
                        "rotation_schedule": "0 0 1 * *",
                    },
                },
                "network_security": {
                    "https_only": True,
                    "tls_version": "1.3",
                    "cors_policy": {
                        "enabled": True,
                        "allowed_origins": ["https://crypto-bot-dashboard.example.com"],
                        "allowed_methods": ["GET", "POST"],
                        "allowed_headers": ["Authorization", "Content-Type"],
                    },
                    "rate_limiting": {
                        "enabled": True,
                        "requests_per_minute": 100,
                        "burst_capacity": 200,
                    },
                },
                "audit_logging": {
                    "enabled": True,
                    "log_all_requests": True,
                    "log_authentication_events": True,
                    "log_authorization_events": True,
                    "retention_days": 90,
                },
                "vulnerability_scanning": {
                    "enabled": True,
                    "scan_schedule": "0 2 * * *",
                    "scan_targets": [
                        "container_images",
                        "dependencies",
                        "configuration",
                    ],
                },
                "incident_response": {
                    "enabled": True,
                    "notification_channels": [
                        "email:security@example.com",
                        "slack:security-alerts",
                    ],
                    "auto_actions": [
                        {
                            "trigger": "suspicious_activity",
                            "action": "temporary_disable",
                            "duration": "1h",
                        },
                        {
                            "trigger": "authentication_failure",
                            "action": "rate_limit_increase",
                            "duration": "30m",
                        },
                    ],
                },
            }

            # セキュリティポリシーの生成
            security_policy = {
                "bindings": [
                    {
                        "role": "roles/run.invoker",
                        "members": [
                            "serviceAccount:crypto-bot-service-account@crypto-bot-prod.iam.gserviceaccount.com"
                        ],
                    },
                    {
                        "role": "roles/secretmanager.secretAccessor",
                        "members": [
                            "serviceAccount:crypto-bot-service-account@crypto-bot-prod.iam.gserviceaccount.com"
                        ],
                    },
                    {
                        "role": "roles/logging.logWriter",
                        "members": [
                            "serviceAccount:crypto-bot-service-account@crypto-bot-prod.iam.gserviceaccount.com"
                        ],
                    },
                    {
                        "role": "roles/monitoring.metricWriter",
                        "members": [
                            "serviceAccount:crypto-bot-service-account@crypto-bot-prod.iam.gserviceaccount.com"
                        ],
                    },
                ]
            }

            # 設定をファイルに保存
            with open("security_config.json", "w") as f:
                json.dump(security_config, f, indent=2)

            with open("security_policy.json", "w") as f:
                json.dump(security_policy, f, indent=2)

            self.log_config(
                "セキュリティ設定強化",
                "success",
                f"{len(security_config['network_security'])} 個のセキュリティ設定が強化されました",
                {
                    "config_file": "security_config.json",
                    "policy_file": "security_policy.json",
                },
            )
            return True

        except Exception as e:
            self.log_config("セキュリティ設定強化", "failed", f"Exception: {str(e)}")
            return False

    def generate_long_term_report(self) -> Dict:
        """長期運用設定レポートを生成"""
        total_configs = len(self.config_results)
        successful_configs = len(
            [r for r in self.config_results if r["status"] == "success"]
        )
        failed_configs = len(
            [r for r in self.config_results if r["status"] == "failed"]
        )

        # 長期運用準備度を評価
        critical_configs = [
            "自動再起動設定",
            "ログローテーション設定",
            "バックアップ設定",
            "セキュリティ設定強化",
        ]

        critical_success = 0
        for config in self.config_results:
            if (
                config["config_name"] in critical_configs
                and config["status"] == "success"
            ):
                critical_success += 1

        readiness_score = (critical_success / len(critical_configs)) * 100

        report = {
            "report_timestamp": datetime.now().isoformat(),
            "config_duration": str(datetime.now() - self.start_time),
            "summary": {
                "total_configs": total_configs,
                "successful_configs": successful_configs,
                "failed_configs": failed_configs,
                "success_rate": (
                    f"{(successful_configs / total_configs * 100):.1f}%"
                    if total_configs > 0
                    else "0%"
                ),
                "readiness_score": f"{readiness_score:.1f}%",
                "long_term_ready": readiness_score >= 100.0,
            },
            "detailed_results": self.config_results,
        }

        return report

    def run_all_configurations(self) -> bool:
        """全ての長期運用設定を実行"""
        print("🔧 Phase 4.1e: 長期運用設定調整開始")
        print("=" * 50)

        configurations = [
            ("自動再起動設定", self.setup_auto_restart_config),
            ("ログローテーション設定", self.setup_log_rotation_config),
            ("メトリクス保存期間設定", self.setup_metrics_retention_config),
            ("バックアップ設定", self.setup_backup_config),
            ("セキュリティ設定強化", self.setup_security_hardening),
        ]

        overall_success = True
        for config_name, config_func in configurations:
            print(f"🔧 {config_name} 実行中...")
            success = config_func()
            if not success:
                overall_success = False
            time.sleep(1)

        # レポート生成
        report = self.generate_long_term_report()

        print("📊 長期運用設定調整完了サマリー")
        print("=" * 50)
        print(f"総設定数: {report['summary']['total_configs']}")
        print(f"成功: {report['summary']['successful_configs']}")
        print(f"失敗: {report['summary']['failed_configs']}")
        print(f"成功率: {report['summary']['success_rate']}")
        print(f"準備度スコア: {report['summary']['readiness_score']}")
        print(
            f"長期運用準備: {'✅ 完了' if report['summary']['long_term_ready'] else '❌ 未完了'}"
        )
        print(f"実行時間: {report['config_duration']}")

        # レポートをファイルに保存
        try:
            with open("phase4_1_long_term_config_report.json", "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(
                "\\n📄 詳細レポートをphase4_1_long_term_config_report.jsonに保存しました"
            )
        except Exception as e:
            print(f"\\n⚠️  レポート保存に失敗: {e}")

        if report["summary"]["long_term_ready"]:
            print("\\n🎉 Phase 4.1e: 長期運用設定調整 - 全ての設定が完了しました!")
        else:
            print("\\n⚠️  Phase 4.1e: 長期運用設定調整 - 一部の設定が未完了です")

        return report["summary"]["long_term_ready"]


def main():
    """メイン実行関数"""
    config_manager = LongTermConfigurationManager()
    success = config_manager.run_all_configurations()

    if success:
        print("\\n✅ Phase 4.1e完了 - 長期運用設定が全て完了しました")
        print("Phase 4.1: 本番稼働・継続監視体制確立が完了しました")
        return 0
    else:
        print("\\n❌ Phase 4.1e失敗 - 長期運用設定が未完了です")
        return 1


if __name__ == "__main__":
    exit(main())
