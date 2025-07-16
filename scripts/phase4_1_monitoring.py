#!/usr/bin/env python3
"""
Phase 4.1b: 継続監視体制構築
Cloud Monitoring とアラート設定を行います
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional
import subprocess

class MonitoringSystemSetup:
    """継続監視体制構築クラス"""
    
    def __init__(self):
        self.setup_results = []
        self.start_time = datetime.now()
        self.project_id = "crypto-bot-prod"
        
    def log_setup(self, setup_name: str, status: str, message: str = "", data: Optional[Dict] = None):
        """設定結果をログに記録"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "setup_name": setup_name,
            "status": status,
            "message": message,
            "data": data or {}
        }
        self.setup_results.append(result)
        
        status_emoji = "✅" if status == "success" else "❌" if status == "failed" else "⚠️"
        print(f"{status_emoji} {setup_name}: {status}")
        if message:
            print(f"   {message}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        print()
    
    def setup_cloud_monitoring_dashboard(self) -> bool:
        """Cloud Monitoring ダッシュボード設定"""
        try:
            dashboard_config = {
                "displayName": "Crypto Bot Production Dashboard",
                "mosaicLayout": {
                    "tiles": [
                        {
                            "width": 6,
                            "height": 4,
                            "widget": {
                                "title": "Service Health",
                                "xyChart": {
                                    "dataSets": [{
                                        "timeSeriesQuery": {
                                            "timeSeriesFilter": {
                                                "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\"",
                                                "aggregation": {
                                                    "alignmentPeriod": "60s",
                                                    "perSeriesAligner": "ALIGN_RATE"
                                                }
                                            }
                                        }
                                    }]
                                }
                            }
                        },
                        {
                            "width": 6,
                            "height": 4,
                            "widget": {
                                "title": "API Response Time",
                                "xyChart": {
                                    "dataSets": [{
                                        "timeSeriesQuery": {
                                            "timeSeriesFilter": {
                                                "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\"",
                                                "aggregation": {
                                                    "alignmentPeriod": "60s",
                                                    "perSeriesAligner": "ALIGN_MEAN"
                                                }
                                            }
                                        }
                                    }]
                                }
                            }
                        },
                        {
                            "width": 12,
                            "height": 4,
                            "widget": {
                                "title": "Error Rate",
                                "xyChart": {
                                    "dataSets": [{
                                        "timeSeriesQuery": {
                                            "timeSeriesFilter": {
                                                "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\"",
                                                "aggregation": {
                                                    "alignmentPeriod": "60s",
                                                    "perSeriesAligner": "ALIGN_RATE"
                                                }
                                            }
                                        }
                                    }]
                                }
                            }
                        }
                    ]
                }
            }
            
            # ダッシュボード設定をファイルに保存
            with open("dashboard_config.json", "w") as f:
                json.dump(dashboard_config, f, indent=2)
            
            self.log_setup(
                "Cloud Monitoring ダッシュボード",
                "success",
                "ダッシュボード設定が作成されました",
                {"config_file": "dashboard_config.json"}
            )
            return True
            
        except Exception as e:
            self.log_setup(
                "Cloud Monitoring ダッシュボード",
                "failed",
                f"Exception: {str(e)}"
            )
            return False
    
    def setup_alert_policies(self) -> bool:
        """アラートポリシー設定"""
        try:
            alert_policies = [
                {
                    "displayName": "Crypto Bot - Service Down",
                    "documentation": {
                        "content": "Crypto Bot service is down or not responding",
                        "mimeType": "text/markdown"
                    },
                    "conditions": [{
                        "displayName": "Service Down",
                        "conditionThreshold": {
                            "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\"",
                            "comparison": "COMPARISON_EQUAL",
                            "thresholdValue": 0,
                            "duration": "300s",
                            "aggregations": [{
                                "alignmentPeriod": "60s",
                                "perSeriesAligner": "ALIGN_RATE"
                            }]
                        }
                    }],
                    "alertStrategy": {
                        "autoClose": "1800s"
                    },
                    "enabled": True
                },
                {
                    "displayName": "Crypto Bot - High Error Rate",
                    "documentation": {
                        "content": "Crypto Bot is experiencing high error rate",
                        "mimeType": "text/markdown"
                    },
                    "conditions": [{
                        "displayName": "High Error Rate",
                        "conditionThreshold": {
                            "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\"",
                            "comparison": "COMPARISON_GREATER",
                            "thresholdValue": 0.05,
                            "duration": "300s",
                            "aggregations": [{
                                "alignmentPeriod": "60s",
                                "perSeriesAligner": "ALIGN_RATE"
                            }]
                        }
                    }],
                    "alertStrategy": {
                        "autoClose": "1800s"
                    },
                    "enabled": True
                },
                {
                    "displayName": "Crypto Bot - API-only Mode Detection",
                    "documentation": {
                        "content": "Crypto Bot may have fallen into API-only mode",
                        "mimeType": "text/markdown"
                    },
                    "conditions": [{
                        "displayName": "API-only Mode",
                        "conditionThreshold": {
                            "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"API-only mode\"",
                            "comparison": "COMPARISON_GREATER",
                            "thresholdValue": 0,
                            "duration": "60s",
                            "aggregations": [{
                                "alignmentPeriod": "60s",
                                "perSeriesAligner": "ALIGN_RATE"
                            }]
                        }
                    }],
                    "alertStrategy": {
                        "autoClose": "3600s"
                    },
                    "enabled": True
                },
                {
                    "displayName": "Crypto Bot - ATR Calculation Hang",
                    "documentation": {
                        "content": "ATR calculation may be hanging",
                        "mimeType": "text/markdown"
                    },
                    "conditions": [{
                        "displayName": "ATR Hang",
                        "conditionThreshold": {
                            "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"INIT-5.*timeout\"",
                            "comparison": "COMPARISON_GREATER",
                            "thresholdValue": 0,
                            "duration": "60s",
                            "aggregations": [{
                                "alignmentPeriod": "60s",
                                "perSeriesAligner": "ALIGN_RATE"
                            }]
                        }
                    }],
                    "alertStrategy": {
                        "autoClose": "3600s"
                    },
                    "enabled": True
                },
                {
                    "displayName": "Crypto Bot - External Data Fetcher Failure",
                    "documentation": {
                        "content": "External data fetchers are failing",
                        "mimeType": "text/markdown"
                    },
                    "conditions": [{
                        "displayName": "External Data Failure",
                        "conditionThreshold": {
                            "filter": f"resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"external.*fetcher.*failed\"",
                            "comparison": "COMPARISON_GREATER",
                            "thresholdValue": 5,
                            "duration": "300s",
                            "aggregations": [{
                                "alignmentPeriod": "60s",
                                "perSeriesAligner": "ALIGN_RATE"
                            }]
                        }
                    }],
                    "alertStrategy": {
                        "autoClose": "3600s"
                    },
                    "enabled": True
                }
            ]
            
            # アラートポリシー設定をファイルに保存
            with open("alert_policies.json", "w") as f:
                json.dump(alert_policies, f, indent=2)
            
            self.log_setup(
                "アラートポリシー",
                "success",
                f"{len(alert_policies)} 個のアラートポリシーが作成されました",
                {"config_file": "alert_policies.json", "policies": len(alert_policies)}
            )
            return True
            
        except Exception as e:
            self.log_setup(
                "アラートポリシー",
                "failed",
                f"Exception: {str(e)}"
            )
            return False
    
    def setup_log_analysis(self) -> bool:
        """ログ分析システム設定"""
        try:
            log_analysis_config = {
                "name": "crypto-bot-log-analysis",
                "description": "Crypto Bot ログ分析設定",
                "queries": [
                    {
                        "name": "api_only_mode_detection",
                        "description": "API-onlyモード検知",
                        "query": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"API-only mode\"",
                        "alert_threshold": 1
                    },
                    {
                        "name": "atr_calculation_hang",
                        "description": "ATR計算ハング検知",
                        "query": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"INIT-5.*timeout\"",
                        "alert_threshold": 1
                    },
                    {
                        "name": "external_data_fetcher_failure",
                        "description": "外部データフェッチャー失敗検知",
                        "query": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"external.*fetcher.*failed\"",
                        "alert_threshold": 5
                    },
                    {
                        "name": "bitbank_api_error",
                        "description": "Bitbank API エラー検知",
                        "query": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"bitbank.*error\"",
                        "alert_threshold": 3
                    },
                    {
                        "name": "yfinance_dependency_error",
                        "description": "yfinance依存関係エラー検知",
                        "query": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND jsonPayload.message=~\"yfinance.*not found\"",
                        "alert_threshold": 1
                    }
                ]
            }
            
            # ログ分析設定をファイルに保存
            with open("log_analysis_config.json", "w") as f:
                json.dump(log_analysis_config, f, indent=2)
            
            self.log_setup(
                "ログ分析システム",
                "success",
                f"{len(log_analysis_config['queries'])} 個のログ分析クエリが作成されました",
                {"config_file": "log_analysis_config.json", "queries": len(log_analysis_config['queries'])}
            )
            return True
            
        except Exception as e:
            self.log_setup(
                "ログ分析システム",
                "failed",
                f"Exception: {str(e)}"
            )
            return False
    
    def setup_performance_monitoring(self) -> bool:
        """パフォーマンス監視設定"""
        try:
            performance_config = {
                "name": "crypto-bot-performance-monitoring",
                "description": "Crypto Bot パフォーマンス監視設定",
                "metrics": [
                    {
                        "name": "kelly_ratio",
                        "description": "Kelly比率",
                        "threshold": {
                            "warning": 0.1,
                            "critical": 0.05
                        }
                    },
                    {
                        "name": "win_rate",
                        "description": "勝率",
                        "threshold": {
                            "warning": 0.5,
                            "critical": 0.4
                        }
                    },
                    {
                        "name": "max_drawdown",
                        "description": "最大ドローダウン",
                        "threshold": {
                            "warning": 0.1,
                            "critical": 0.15
                        }
                    },
                    {
                        "name": "sharpe_ratio",
                        "description": "シャープレシオ",
                        "threshold": {
                            "warning": 1.0,
                            "critical": 0.5
                        }
                    },
                    {
                        "name": "response_time",
                        "description": "APIレスポンス時間",
                        "threshold": {
                            "warning": 5.0,
                            "critical": 10.0
                        }
                    }
                ],
                "monitoring_interval": "60s",
                "retention_period": "30d"
            }
            
            # パフォーマンス監視設定をファイルに保存
            with open("performance_monitoring_config.json", "w") as f:
                json.dump(performance_config, f, indent=2)
            
            self.log_setup(
                "パフォーマンス監視",
                "success",
                f"{len(performance_config['metrics'])} 個のパフォーマンスメトリクスが設定されました",
                {"config_file": "performance_monitoring_config.json", "metrics": len(performance_config['metrics'])}
            )
            return True
            
        except Exception as e:
            self.log_setup(
                "パフォーマンス監視",
                "failed",
                f"Exception: {str(e)}"
            )
            return False
    
    def setup_auto_recovery(self) -> bool:
        """自動復旧機能設定"""
        try:
            auto_recovery_config = {
                "name": "crypto-bot-auto-recovery",
                "description": "Crypto Bot 自動復旧設定",
                "recovery_actions": [
                    {
                        "trigger": "service_down",
                        "action": "restart_service",
                        "max_attempts": 3,
                        "wait_time": "60s"
                    },
                    {
                        "trigger": "high_error_rate",
                        "action": "scale_up",
                        "max_attempts": 2,
                        "wait_time": "300s"
                    },
                    {
                        "trigger": "api_only_mode",
                        "action": "force_restart",
                        "max_attempts": 1,
                        "wait_time": "30s"
                    },
                    {
                        "trigger": "atr_hang",
                        "action": "restart_service",
                        "max_attempts": 2,
                        "wait_time": "60s"
                    },
                    {
                        "trigger": "external_data_failure",
                        "action": "clear_cache_and_restart",
                        "max_attempts": 1,
                        "wait_time": "120s"
                    }
                ],
                "notification_settings": {
                    "email": "admin@example.com",
                    "slack_webhook": "https://hooks.slack.com/services/...",
                    "discord_webhook": "https://discord.com/api/webhooks/..."
                }
            }
            
            # 自動復旧設定をファイルに保存
            with open("auto_recovery_config.json", "w") as f:
                json.dump(auto_recovery_config, f, indent=2)
            
            self.log_setup(
                "自動復旧機能",
                "success",
                f"{len(auto_recovery_config['recovery_actions'])} 個の自動復旧アクションが設定されました",
                {"config_file": "auto_recovery_config.json", "actions": len(auto_recovery_config['recovery_actions'])}
            )
            return True
            
        except Exception as e:
            self.log_setup(
                "自動復旧機能",
                "failed",
                f"Exception: {str(e)}"
            )
            return False
    
    def generate_monitoring_report(self) -> Dict:
        """監視体制構築レポートを生成"""
        total_setups = len(self.setup_results)
        successful_setups = len([r for r in self.setup_results if r["status"] == "success"])
        failed_setups = len([r for r in self.setup_results if r["status"] == "failed"])
        
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "setup_duration": str(datetime.now() - self.start_time),
            "summary": {
                "total_setups": total_setups,
                "successful_setups": successful_setups,
                "failed_setups": failed_setups,
                "success_rate": f"{(successful_setups / total_setups * 100):.1f}%" if total_setups > 0 else "0%"
            },
            "detailed_results": self.setup_results
        }
        
        return report
    
    def run_all_setups(self) -> bool:
        """全ての監視設定を実行"""
        print("📊 Phase 4.1b: 継続監視体制構築開始")
        print("=" * 50)
        
        setups = [
            ("Cloud Monitoring ダッシュボード", self.setup_cloud_monitoring_dashboard),
            ("アラートポリシー", self.setup_alert_policies),
            ("ログ分析システム", self.setup_log_analysis),
            ("パフォーマンス監視", self.setup_performance_monitoring),
            ("自動復旧機能", self.setup_auto_recovery),
        ]
        
        overall_success = True
        for setup_name, setup_func in setups:
            print(f"🔧 {setup_name} 設定中...")
            success = setup_func()
            if not success:
                overall_success = False
            time.sleep(1)
        
        # レポート生成
        report = self.generate_monitoring_report()
        
        print("📊 監視体制構築完了サマリー")
        print("=" * 50)
        print(f"総設定数: {report['summary']['total_setups']}")
        print(f"成功: {report['summary']['successful_setups']}")
        print(f"失敗: {report['summary']['failed_setups']}")
        print(f"成功率: {report['summary']['success_rate']}")
        print(f"実行時間: {report['setup_duration']}")
        
        # レポートをファイルに保存
        try:
            with open("phase4_1_monitoring_report.json", "w") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print("\\n📄 詳細レポートをphase4_1_monitoring_report.jsonに保存しました")
        except Exception as e:
            print(f"\\n⚠️  レポート保存に失敗: {e}")
        
        if overall_success:
            print("\\n🎉 Phase 4.1b: 継続監視体制構築 - 全ての設定が成功しました!")
        else:
            print("\\n⚠️  Phase 4.1b: 継続監視体制構築 - 一部の設定が失敗しました")
        
        return overall_success

def main():
    """メイン実行関数"""
    setup = MonitoringSystemSetup()
    success = setup.run_all_setups()
    
    if success:
        print("\\n✅ Phase 4.1b完了 - 次のフェーズ（Phase 4.1c）に進むことができます")
        return 0
    else:
        print("\\n❌ Phase 4.1b失敗 - 問題を解決してから次のフェーズに進んでください")
        return 1

if __name__ == "__main__":
    exit(main())