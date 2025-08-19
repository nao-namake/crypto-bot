#!/usr/bin/env python3
"""
crypto-bot 完璧稼働状況確認システム

毎回固定された手法で確実にシステム状態・隠れたエラーを検出
表面上の稼働と実際の動作状態を区別し、過去の問題パターンを網羅的にチェック

使用方法:
    python scripts/operational_status_checker.py [--verbose] [--save-report] [--phase PHASE_NAME]

統合される既存ツール:
    - system_health_check.py
    - signal_monitor.py
    - error_analyzer.py
    - future_leak_detector.py
    - unified_status_checker.py (GCP log analysis)
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
import re
import requests

# プロジェクトルート設定
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/operational_status.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


class OperationalStatusChecker:
    """完璧稼働状況確認システム"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(
            PROJECT_ROOT / "scripts/status_config.json"
        )
        self.config = self.load_config()
        self.report_dir = Path("logs/operational_reports")
        self.report_dir.mkdir(exist_ok=True, parents=True)

        # 実行結果保存
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "phases": {},
            "overall_status": "UNKNOWN",
            "overall_score": 0,
            "critical_issues": [],
            "recommendations": [],
        }

        # GCP/API設定
        self.base_url = (
            "https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app"
        )

    def load_config(self) -> Dict:
        """設定ファイルを読み込み"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                logger.info(f"✅ Configuration loaded from {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return {
                "check_phases": {},
                "thresholds": {},
                "hidden_error_patterns": {"patterns": []},
            }

    # ===== Phase 1: インフラ・基盤確認システム =====

    def check_gcp_cloud_run_status(self) -> Dict[str, Any]:
        """GCP Cloud Run稼働状況確認"""
        logger.info("🔍 Checking GCP Cloud Run status...")

        try:
            # サービス基本情報取得
            cmd = [
                "gcloud",
                "run",
                "services",
                "describe",
                "crypto-bot-service-prod",
                "--region=asia-northeast1",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                service_info = json.loads(result.stdout)
                status = service_info.get("status", {})

                # 現在のリビジョン情報
                traffic = status.get("traffic", [])
                active_revision = None
                for t in traffic:
                    if t.get("percent", 0) == 100:
                        active_revision = t.get("revisionName", "unknown")
                        break

                # 最新リビジョン取得
                latest_revision = status.get("latestCreatedRevisionName", "unknown")

                # リビジョン作成時刻確認
                cmd_revisions = [
                    "gcloud",
                    "run",
                    "revisions",
                    "list",
                    "--service=crypto-bot-service-prod",
                    "--region=asia-northeast1",
                    "--limit=3",
                    "--format=json",
                ]
                rev_result = subprocess.run(
                    cmd_revisions, capture_output=True, text=True, timeout=20
                )

                revision_age_hours = 0
                if rev_result.returncode == 0:
                    revisions = json.loads(rev_result.stdout)
                    if revisions:
                        latest_rev = revisions[0]
                        creation_time = latest_rev.get("metadata", {}).get(
                            "creationTimestamp"
                        )
                        if creation_time:
                            created_at = datetime.fromisoformat(
                                creation_time.replace("Z", "+00:00")
                            )
                            revision_age_hours = (
                                datetime.now().astimezone() - created_at
                            ).total_seconds() / 3600

                return {
                    "status": "healthy",
                    "active_revision": active_revision,
                    "latest_revision": latest_revision,
                    "revision_switch_ok": active_revision == latest_revision,
                    "revision_age_hours": revision_age_hours,
                    "service_url": status.get("url", "unknown"),
                    "details": f"Active: {active_revision}, Age: {revision_age_hours:.1f}h",
                }
            else:
                return {
                    "status": "error",
                    "error": f"gcloud command failed: {result.stderr}",
                    "details": "Cloud Run service not accessible",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "GCP command timeout",
                "details": "Cloud Run status check timed out",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Unexpected error: {type(e).__name__}",
            }

    def check_api_connectivity(self) -> Dict[str, Any]:
        """API接続性・認証確認"""
        logger.info("🔍 Checking API connectivity...")

        checks = {
            "basic_health": self._check_basic_health(),
            "detailed_health": self._check_detailed_health(),
            "response_time": None,
        }

        # レスポンス時間測定
        start_time = time.time()
        try:
            requests.get(f"{self.base_url}/health", timeout=10)
            checks["response_time"] = time.time() - start_time
        except Exception:
            checks["response_time"] = -1

        # 総合評価
        all_healthy = all(
            check.get("status") == "healthy"
            for check in checks.values()
            if isinstance(check, dict) and "status" in check
        )

        return {
            "status": "healthy" if all_healthy else "degraded",
            "checks": checks,
            "details": (
                f"Response time: {checks['response_time']:.2f}s"
                if checks["response_time"] and checks["response_time"] > 0
                else "Response time unavailable"
            ),
        }

    def _check_basic_health(self) -> Dict[str, Any]:
        """基本ヘルスチェック"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "healthy",
                    "mode": data.get("mode", "unknown"),
                    "details": f"HTTP 200, Mode: {data.get('mode', 'unknown')}",
                }
            else:
                return {
                    "status": "error",
                    "http_code": response.status_code,
                    "details": f"HTTP {response.status_code}",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Connection failed: {type(e).__name__}",
            }

    def _check_detailed_health(self) -> Dict[str, Any]:
        """詳細ヘルスチェック"""
        try:
            response = requests.get(f"{self.base_url}/health/detailed", timeout=15)
            if response.status_code == 200:
                data = response.json()

                # API認証状況
                api_status = data.get("dependencies", {}).get("api_credentials", {})
                api_healthy = api_status.get("status") == "healthy"

                # 信用取引モード
                margin_mode = api_status.get("margin_mode", False)

                return {
                    "status": "healthy" if api_healthy else "degraded",
                    "api_auth": api_healthy,
                    "margin_mode": margin_mode,
                    "trading_status": data.get("trading", {}).get("status", "unknown"),
                    "details": f"Auth: {api_healthy}, Margin: {margin_mode}",
                }
            else:
                return {
                    "status": "error",
                    "http_code": response.status_code,
                    "details": f"HTTP {response.status_code}",
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Detailed health failed: {type(e).__name__}",
            }

    def check_system_health(self) -> Dict[str, Any]:
        """システムヘルス状況（既存tool活用）"""
        logger.info("🔍 Running system health checks...")

        try:
            # system_health_check.pyを呼び出し
            health_script = PROJECT_ROOT / "scripts/system_tools/system_health_check.py"
            if not health_script.exists():
                return {
                    "status": "error",
                    "error": "system_health_check.py not found",
                    "details": "Required health check script missing",
                }

            cmd = ["python", str(health_script), "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                # JSON出力を解析
                output_lines = result.stdout.strip().split("\n")
                json_output = None

                # JSON部分を特定
                for i, line in enumerate(output_lines):
                    if line.strip().startswith("{"):
                        json_str = "\n".join(output_lines[i:])
                        try:
                            json_output = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            continue

                if json_output:
                    success_rate = json_output.get("success_rate", 0)
                    critical_issues = json_output.get("critical_issues", 0)

                    status = (
                        "healthy"
                        if success_rate >= 80 and critical_issues == 0
                        else "degraded"
                    )

                    return {
                        "status": status,
                        "success_rate": success_rate,
                        "critical_issues": critical_issues,
                        "warning_issues": json_output.get("warning_issues", 0),
                        "details": f"Success: {success_rate:.1f}%, Critical: {critical_issues}",
                    }
                else:
                    return {
                        "status": "healthy",
                        "success_rate": 100,
                        "details": "Health checks passed (no JSON output)",
                    }
            else:
                return {
                    "status": "degraded",
                    "error": "Health check script failed",
                    "return_code": result.returncode,
                    "stderr": result.stderr[:200],
                    "details": f"Exit code: {result.returncode}",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Health check timeout",
                "details": "System health check took too long",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Health check error: {type(e).__name__}",
            }

    def check_resource_usage(self) -> Dict[str, Any]:
        """リソース使用状況確認"""
        logger.info("🔍 Checking resource usage...")

        try:
            # GCPメトリクス取得（簡易版）
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"memory"',
                "--limit=3",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            memory_info = {"status": "unknown", "details": "No memory info available"}

            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)

                for log in logs[:3]:
                    text = str(log.get("textPayload", ""))

                    # メモリ使用量パターン検索
                    memory_match = re.search(
                        r"memory.*?(\d+).*?MB", text, re.IGNORECASE
                    )
                    if memory_match:
                        memory_mb = int(memory_match.group(1))

                        if memory_mb > 1500:  # 1.5GB閾値
                            memory_info = {
                                "status": "warning",
                                "memory_mb": memory_mb,
                                "details": f"High memory usage: {memory_mb}MB",
                            }
                        else:
                            memory_info = {
                                "status": "healthy",
                                "memory_mb": memory_mb,
                                "details": f"Memory usage: {memory_mb}MB",
                            }
                        break

            # CPU情報は現在取得困難なため省略
            return {
                "status": memory_info.get("status", "unknown"),
                "memory": memory_info,
                "cpu": {"status": "unknown", "details": "CPU metrics not available"},
                "details": memory_info.get("details", "Resource info limited"),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Resource check failed: {type(e).__name__}",
            }

    def run_phase1_infrastructure_checks(self) -> Dict[str, Any]:
        """Phase 1: インフラ・基盤確認を実行"""
        logger.info("🚀 === Phase 1: インフラ・基盤確認 ===")

        phase1_results = {
            "phase_name": "インフラ・基盤確認",
            "weight": self.config["check_phases"]["phase1"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "gcp_cloud_run_status": self.check_gcp_cloud_run_status(),
            "api_connectivity": self.check_api_connectivity(),
            "system_health": self.check_system_health(),
            "resource_usage": self.check_resource_usage(),
        }

        phase1_results["checks"] = checks

        # Phase 1スコア計算
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "degraded":
                score = 70
            elif status == "warning":
                score = 60
            elif status == "timeout":
                score = 40
            else:  # error
                score = 0

            check_scores.append(score)

            # 重大な問題を記録
            if score < 50:
                phase1_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": "CRITICAL" if score == 0 else "HIGH",
                        "message": check_result.get(
                            "error", check_result.get("details", "Unknown issue")
                        ),
                        "score": score,
                    }
                )

        # Phase 1総合スコア
        phase1_results["score"] = (
            sum(check_scores) / len(check_scores) if check_scores else 0
        )

        # Phase 1ステータス判定
        if phase1_results["score"] >= 80:
            phase1_results["status"] = "healthy"
        elif phase1_results["score"] >= 60:
            phase1_results["status"] = "warning"
        else:
            phase1_results["status"] = "critical"

        logger.info(
            f"✅ Phase 1 完了: スコア {phase1_results['score']:.1f}/100 ({phase1_results['status']})"
        )

        self.results["phases"]["phase1"] = phase1_results
        return phase1_results

    # ===== メイン実行・レポート生成 =====

    # ===== Phase 2: アプリケーション動作確認システム =====

    def check_log_analysis(self) -> Dict[str, Any]:
        """ログ分析・エラー検出（既存tool活用）"""
        logger.info("🔍 Analyzing application logs...")

        try:
            # error_analyzer.pyを活用
            error_script = PROJECT_ROOT / "scripts/monitoring/error_analyzer.py"
            if not error_script.exists():
                return {
                    "status": "error",
                    "error": "error_analyzer.py not found",
                    "details": "Error analysis tool missing",
                }

            cmd = ["python", str(error_script), "--source", "gcp", "--hours", "4"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)

            # エラー分析結果の簡易解析（正常終了=問題なし、異常終了=エラー検出）
            if result.returncode == 0:
                return {
                    "status": "healthy",
                    "error_count": 0,
                    "details": "No significant errors detected",
                }
            elif result.returncode == 1:
                return {
                    "status": "warning",
                    "error_count": "some",
                    "details": "Some errors detected (medium priority)",
                }
            else:
                return {
                    "status": "critical",
                    "error_count": "many",
                    "details": "Critical errors detected",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Error analysis timeout",
                "details": "Log analysis took too long",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Log analysis failed: {type(e).__name__}",
            }

    def check_data_fetching_efficiency(self) -> Dict[str, Any]:
        """データ取得効率性・48/300停滞問題検出"""
        logger.info("🔍 Checking data fetching efficiency...")

        try:
            # 最近のデータ取得ログを確認
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"Progress:"',
                "--limit=5",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)

                # データ取得状況を解析
                fetch_issues = []
                latest_progress = None

                for log in logs:
                    text = str(log.get("textPayload", ""))

                    # "Progress: current=48/300" のようなパターンを検索
                    progress_match = re.search(r"Progress:.*?current=(\d+)/(\d+)", text)
                    if progress_match:
                        current = int(progress_match.group(1))
                        total = int(progress_match.group(2))
                        latest_progress = {
                            "current": current,
                            "total": total,
                            "ratio": current / total if total > 0 else 0,
                        }

                        # 48/300停滞問題チェック（過去の隠れたエラーパターン）
                        if current == 48 and total == 300:
                            fetch_issues.append(
                                {
                                    "type": "data_fetch_stagnation",
                                    "severity": "CRITICAL",
                                    "message": f"48/300停滞問題検出: current={current}/{total}",
                                }
                            )

                    # Empty batch連続発生チェック
                    empty_batch_match = re.search(r"Empty batch (\d+)/8", text)
                    if empty_batch_match:
                        batch_num = int(empty_batch_match.group(1))
                        if batch_num >= 7:  # 8回中7回以上Empty
                            fetch_issues.append(
                                {
                                    "type": "empty_batch_excess",
                                    "severity": "HIGH",
                                    "message": f"Empty batch過多: {batch_num}/8",
                                }
                            )

                # 評価
                if fetch_issues:
                    critical_issues = [
                        i for i in fetch_issues if i["severity"] == "CRITICAL"
                    ]
                    if critical_issues:
                        return {
                            "status": "critical",
                            "issues": fetch_issues,
                            "latest_progress": latest_progress,
                            "details": f"{len(critical_issues)} critical data fetch issues",
                        }
                    else:
                        return {
                            "status": "warning",
                            "issues": fetch_issues,
                            "latest_progress": latest_progress,
                            "details": f"{len(fetch_issues)} data fetch issues",
                        }
                else:
                    return {
                        "status": "healthy",
                        "issues": [],
                        "latest_progress": latest_progress,
                        "details": "Data fetching appears normal",
                    }
            else:
                return {
                    "status": "unknown",
                    "error": "No data fetch logs found",
                    "details": "Unable to verify data fetching status",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Data fetch check failed: {type(e).__name__}",
            }

    def check_signal_generation_health(self) -> Dict[str, Any]:
        """シグナル生成状況確認（既存tool活用）"""
        logger.info("🔍 Checking signal generation health...")

        try:
            # signal_monitor.pyを活用
            signal_script = PROJECT_ROOT / "scripts/monitoring/signal_monitor.py"
            if not signal_script.exists():
                return {
                    "status": "error",
                    "error": "signal_monitor.py not found",
                    "details": "Signal monitoring tool missing",
                }

            cmd = [
                "python",
                str(signal_script),
                "--hours",
                "4",
                "--threshold-alert",
                "60",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # signal_monitor結果解析
            if result.returncode == 0:
                # ヘルススコア抽出
                health_match = re.search(r"System health OK: (\d+)/100", result.stdout)
                if health_match:
                    health_score = int(health_match.group(1))
                    return {
                        "status": "healthy",
                        "health_score": health_score,
                        "details": f"Signal health score: {health_score}/100",
                    }
                else:
                    return {
                        "status": "healthy",
                        "health_score": 80,  # 推定値
                        "details": "Signal monitoring passed",
                    }
            elif result.returncode == 1:
                # アラート閾値以下
                alert_match = re.search(
                    r"Health score (\d+) below threshold", result.stdou
                )
                if alert_match:
                    health_score = int(alert_match.group(1))
                    return {
                        "status": "warning",
                        "health_score": health_score,
                        "details": f"Signal health below threshold: {health_score}/100",
                    }
                else:
                    return {
                        "status": "warning",
                        "health_score": 50,  # 推定値
                        "details": "Signal health issues detected",
                    }
            else:
                return {
                    "status": "error",
                    "error": "Signal monitor failed",
                    "return_code": result.returncode,
                    "details": f"Signal monitor exit code: {result.returncode}",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Signal monitor timeout",
                "details": "Signal monitoring took too long",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Signal check failed: {type(e).__name__}",
            }

    def check_main_loop_status(self) -> Dict[str, Any]:
        """メインループ状態・初期化段階での停止チェック"""
        logger.info("🔍 Checking main loop and initialization status...")

        try:
            # 初期化段階のログ確認
            init_stages = ["INIT-5", "INIT-6", "INIT-7", "INIT-8"]

            init_status = {}
            stuck_in_init = False

            for stage in init_stages:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND textPayload:"{stage}"',
                    "--limit=3",
                    "--format=json",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

                if result.returncode == 0 and result.stdout:
                    logs = json.loads(result.stdout)

                    success_found = False
                    stuck_found = False

                    for log in logs:
                        text = str(log.get("textPayload", ""))
                        if "success" in text.lower() or "complete" in text.lower():
                            success_found = True
                        elif "停止" in text or "stuck" in text.lower():
                            stuck_found = True

                    if stuck_found:
                        stuck_in_init = True
                        init_status[stage] = "stuck"
                    elif success_found:
                        init_status[stage] = "success"
                    else:
                        init_status[stage] = "unknown"
                else:
                    init_status[stage] = "no_logs"

            # メインループ実行確認
            main_loop_cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"main loop" OR textPayload:"Main loop"',
                "--limit=2",
                "--format=json",
            ]

            main_result = subprocess.run(
                main_loop_cmd, capture_output=True, text=True, timeout=15
            )
            main_loop_reached = (
                main_result.returncode == 0 and main_result.stdout.strip()
            )

            # 評価
            if stuck_in_init:
                return {
                    "status": "critical",
                    "init_status": init_status,
                    "main_loop_reached": main_loop_reached,
                    "details": "Stuck in initialization phase",
                }
            elif not main_loop_reached:
                return {
                    "status": "warning",
                    "init_status": init_status,
                    "main_loop_reached": main_loop_reached,
                    "details": "Main loop not reached (may be initializing)",
                }
            else:
                return {
                    "status": "healthy",
                    "init_status": init_status,
                    "main_loop_reached": main_loop_reached,
                    "details": "Initialization and main loop normal",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Main loop check failed: {type(e).__name__}",
            }

    def run_phase2_application_checks(self) -> Dict[str, Any]:
        """Phase 2: アプリケーション動作確認を実行"""
        logger.info("🚀 === Phase 2: アプリケーション動作確認 ===")

        phase2_results = {
            "phase_name": "アプリケーション動作確認",
            "weight": self.config["check_phases"]["phase2"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "log_analysis": self.check_log_analysis(),
            "data_fetching_efficiency": self.check_data_fetching_efficiency(),
            "signal_generation_health": self.check_signal_generation_health(),
            "main_loop_status": self.check_main_loop_status(),
        }

        phase2_results["checks"] = checks

        # Phase 2スコア計算
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "warning":
                score = 60
            elif status == "critical":
                score = 20
            elif status in ["timeout", "unknown"]:
                score = 50
            else:  # error
                score = 0

            check_scores.append(score)

            # 重大な問題を記録
            if score < 60:
                phase2_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": "CRITICAL" if score <= 20 else "HIGH",
                        "message": check_result.get(
                            "error", check_result.get("details", "Unknown issue")
                        ),
                        "score": score,
                    }
                )

        # Phase 2総合スコア
        phase2_results["score"] = (
            sum(check_scores) / len(check_scores) if check_scores else 0
        )

        # Phase 2ステータス判定
        if phase2_results["score"] >= 80:
            phase2_results["status"] = "healthy"
        elif phase2_results["score"] >= 60:
            phase2_results["status"] = "warning"
        else:
            phase2_results["status"] = "critical"

        logger.info(
            f"✅ Phase 2 完了: スコア {phase2_results['score']:.1f}/100 ({phase2_results['status']})"
        )

        self.results["phases"]["phase2"] = phase2_results
        return phase2_results

    # ===== Phase 3: 隠れた問題検出システム =====

    def check_hidden_error_patterns(self) -> Dict[str, Any]:
        """隠れたエラーパターン検出（過去事例ベース）"""
        logger.info("🔍 Detecting hidden error patterns...")

        detected_patterns = []
        patterns = self.config.get("hidden_error_patterns", {}).get("patterns", [])

        for pattern_def in patterns:
            pattern_id = pattern_def.get("id", "unknown")
            logger.debug(f"Checking pattern: {pattern_id}")

            try:
                if pattern_id == "data_fetch_stagnation":
                    detected = self._check_data_fetch_stagnation_pattern()
                elif pattern_id == "surface_healthy_actually_stopped":
                    detected = self._check_surface_healthy_stopped_pattern()
                elif pattern_id == "timezone_confusion":
                    detected = self._check_timezone_confusion_pattern()
                elif pattern_id == "main_loop_not_reached":
                    detected = self._check_main_loop_not_reached_pattern()
                elif pattern_id == "revision_switch_failure":
                    detected = self._check_revision_switch_failure_pattern()
                elif pattern_id == "infinite_retry_loop":
                    detected = self._check_infinite_retry_loop_pattern()
                elif pattern_id == "model_prediction_anomaly":
                    detected = self._check_model_prediction_anomaly_pattern()
                elif pattern_id == "module_not_found_critical":
                    detected = self._check_module_not_found_critical_pattern()
                elif pattern_id == "import_error_hidden":
                    detected = self._check_import_error_hidden_pattern()
                else:
                    # その他のパターンは基本的なログ検索
                    detected = self._check_generic_log_pattern(pattern_def)

                if detected:
                    detected_pattern = {
                        "id": pattern_id,
                        "name": pattern_def.get("name", pattern_id),
                        "severity": pattern_def.get("severity", "MEDIUM"),
                        "description": pattern_def.get("description", ""),
                        "detection_details": detected,
                        "past_solutions": pattern_def.get("past_solutions", []),
                    }
                    detected_patterns.append(detected_pattern)

            except Exception as e:
                logger.warning(f"Error checking pattern {pattern_id}: {e}")

        if detected_patterns:
            critical_count = len(
                [p for p in detected_patterns if p["severity"] == "CRITICAL"]
            )
            high_count = len([p for p in detected_patterns if p["severity"] == "HIGH"])

            if critical_count > 0:
                status = "critical"
            elif high_count > 0:
                status = "warning"
            else:
                status = "info"

            return {
                "status": status,
                "patterns_detected": len(detected_patterns),
                "critical_patterns": critical_count,
                "high_patterns": high_count,
                "detected_patterns": detected_patterns,
                "details": f"{len(detected_patterns)} hidden patterns detected",
            }
        else:
            return {
                "status": "healthy",
                "patterns_detected": 0,
                "detected_patterns": [],
                "details": "No hidden error patterns detected",
            }

    def _check_data_fetch_stagnation_pattern(self) -> Optional[Dict]:
        """48/300データ取得停滞パターン検出"""
        try:
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"current=48/300"',
                "--limit=3",
                "--format=json",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)
                if logs:
                    return {
                        "detected": True,
                        "evidence": f"Found {len(logs)} instances of 48/300 stagnation",
                        "latest_timestamp": logs[0].get("timestamp", "unknown"),
                    }
        except Exception as e:
            logger.debug(f"Error checking data fetch stagnation: {e}")
        return None

    def _check_surface_healthy_stopped_pattern(self) -> Optional[Dict]:
        """表面稼働・実際停止問題検出"""
        try:
            # ヘルスチェックは200だが、実際のログが数時間前で停止
            health_response = requests.get(f"{self.base_url}/health", timeout=10)

            if health_response.status_code == 200:
                # 最新ログの時刻確認
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    'resource.type="cloud_run_revision"',
                    "--limit=3",
                    "--format=json",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

                if result.returncode == 0 and result.stdout:
                    logs = json.loads(result.stdout)
                    if logs:
                        latest_log = logs[0]
                        log_timestamp = latest_log.get("timestamp", "")

                        # タイムスタンプ解析
                        if log_timestamp:
                            try:
                                log_time = datetime.fromisoformat(
                                    log_timestamp.replace("Z", "+00:00")
                                )
                                hours_ago = (
                                    datetime.now().astimezone() - log_time
                                ).total_seconds() / 3600

                                if hours_ago > 4:  # 4時間以上前
                                    return {
                                        "detected": True,
                                        "evidence": f"Health OK but last log {hours_ago:.1f}h ago",
                                        "hours_since_last_log": hours_ago,
                                    }
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Error checking surface healthy pattern: {e}")
        return None

    def _check_timezone_confusion_pattern(self) -> Optional[Dict]:
        """UTC/JST時刻混在パターン検出"""
        # このパターンは主に監視・分析時の混乱なので、現在は検出困難
        # プレースホルダーとして実装
        return None

    def _check_main_loop_not_reached_pattern(self) -> Optional[Dict]:
        """メインループ未到達パターン検出（INIT段階停止）"""
        try:
            # INIT段階のログは存在するが、メインループログがない
            init_cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"INIT-"',
                "--limit=5",
                "--format=json",
            ]

            main_cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"main loop"',
                "--limit=2",
                "--format=json",
            ]

            init_result = subprocess.run(
                init_cmd, capture_output=True, text=True, timeout=15
            )
            main_result = subprocess.run(
                main_cmd, capture_output=True, text=True, timeout=15
            )

            init_logs_exist = init_result.returncode == 0 and init_result.stdout.strip()
            main_logs_exist = main_result.returncode == 0 and main_result.stdout.strip()

            if init_logs_exist and not main_logs_exist:
                return {
                    "detected": True,
                    "evidence": "INIT logs present but main loop logs missing",
                    "init_logs_found": True,
                    "main_logs_found": False,
                }

        except Exception as e:
            logger.debug(f"Error checking main loop pattern: {e}")
        return None

    def _check_revision_switch_failure_pattern(self) -> Optional[Dict]:
        """リビジョン切替失敗パターン検出"""
        try:
            cmd = [
                "gcloud",
                "run",
                "revisions",
                "list",
                "--service=crypto-bot-service-prod",
                "--region=asia-northeast1",
                "--limit=3",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

            if result.returncode == 0:
                revisions = json.loads(result.stdout)

                if len(revisions) >= 2:
                    latest = revisions[0]
                    active = None

                    # ACTIVEリビジョンを特定
                    for rev in revisions:
                        traffic = rev.get("status", {}).get("traffic", [])
                        for t in traffic:
                            if t.get("percent", 0) == 100:
                                active = rev
                                break
                        if active:
                            break

                    if active and latest != active:
                        return {
                            "detected": True,
                            "evidence": "Latest revision != active revision",
                            "latest_revision": latest.get("metadata", {}).get(
                                "name", "unknown"
                            ),
                            "active_revision": active.get("metadata", {}).get(
                                "name", "unknown"
                            ),
                        }

        except Exception as e:
            logger.debug(f"Error checking revision switch pattern: {e}")
        return None

    def _check_infinite_retry_loop_pattern(self) -> Optional[Dict]:
        """無限リトライループパターン検出"""
        try:
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"Attempt"',
                "--limit=10",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)

                high_attempt_count = 0
                for log in logs:
                    text = str(log.get("textPayload", ""))

                    # "Attempt 15/20" のようなパターンを検索
                    attempt_match = re.search(r"Attempt (\d+)/\d+", text)
                    if attempt_match:
                        attempt_num = int(attempt_match.group(1))
                        if attempt_num >= 10:
                            high_attempt_count += 1

                if high_attempt_count >= 3:
                    return {
                        "detected": True,
                        "evidence": f"{high_attempt_count} high attempt count entries",
                        "high_attempts": high_attempt_count,
                    }

        except Exception as e:
            logger.debug(f"Error checking retry loop pattern: {e}")
        return None

    def _check_model_prediction_anomaly_pattern(self) -> Optional[Dict]:
        """モデル予測値異常パターン検出"""
        try:
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"confidence"',
                "--limit=10",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)

                confidence_values = []
                consecutive_holds = 0

                for log in logs:
                    text = str(log.get("textPayload", ""))

                    # confidence値抽出
                    conf_match = re.search(r"confidence[:\s]+([0-9.]+)", text)
                    if conf_match:
                        confidence_values.append(float(conf_match.group(1)))

                    # 連続HOLDカウント
                    if "HOLD" in text:
                        consecutive_holds += 1

                # 異常パターン検出
                if len(confidence_values) >= 5:
                    if len(set(confidence_values)) == 1:  # 全て同じ値
                        return {
                            "detected": True,
                            "evidence": f"Static confidence: all values = {confidence_values[0]}",
                            "anomaly_type": "static_confidence",
                        }
                    elif all(c < 0.1 for c in confidence_values):  # 全て極端に低い
                        return {
                            "detected": True,
                            "evidence": f"Extremely low confidence: avg = {sum(confidence_values)/len(confidence_values):.3f}",
                            "anomaly_type": "low_confidence",
                        }

                if consecutive_holds >= 8:  # 連続HOLD過多
                    return {
                        "detected": True,
                        "evidence": f"Excessive consecutive HOLDs: {consecutive_holds}",
                        "anomaly_type": "excessive_holds",
                    }

        except Exception as e:
            logger.debug(f"Error checking model prediction pattern: {e}")
        return None

    def _check_module_not_found_critical_pattern(self) -> Optional[Dict]:
        """ModuleNotFoundError・起動完全阻害パターンの検出"""
        try:
            # CI/CD実行結果をチェック（GitHub Actions）
            cmd = [
                "gh",
                "run",
                "list",
                "--limit=3",
                "--json=conclusion,createdAt,displayTitle",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0 and result.stdout:
                runs = json.loads(result.stdout)

                # 最近の失敗したCIをチェック
                for run in runs:
                    if run.get("conclusion") == "failure":
                        # 失敗したCIの詳細を取得
                        title = run.get("displayTitle", "")
                        if "ModuleNotFoundError" in title or "import" in title.lower():
                            return {
                                "detected": True,
                                "evidence": f"CI failure with import issues: {title}",
                                "severity": "CRITICAL",
                            }

                # GCP Cloud Runログからも検索
                log_patterns = [
                    "ModuleNotFoundError: No module named 'engine",
                    "from engine.backtest_engine import.*failed",
                    "crypto_bot.cli.backtest.*ModuleNotFoundError",
                ]

                for pattern in log_patterns:
                    cmd_log = [
                        "gcloud",
                        "logging",
                        "read",
                        f'resource.type="cloud_run_revision" AND textPayload:"{pattern}"',
                        "--limit=1",
                        "--format=json",
                    ]

                    log_result = subprocess.run(
                        cmd_log, capture_output=True, text=True, timeout=10
                    )
                    if log_result.returncode == 0 and log_result.stdout:
                        logs = json.loads(log_result.stdout)
                        if logs:
                            return {
                                "detected": True,
                                "evidence": f"ModuleNotFoundError in production logs: {pattern}",
                                "severity": "CRITICAL",
                            }

        except Exception as e:
            logger.debug(f"Error checking ModuleNotFoundError pattern: {e}")
        return None

    def _check_import_error_hidden_pattern(self) -> Optional[Dict]:
        """隠れたインポート・メソッド不在エラーの検出"""
        try:
            # 複数のログパターンをチェック
            patterns = [
                "ImportError.*BitbankCoreExecutor",
                "AttributeError.*fetch_ticker",
                "cannot import name.*from",
            ]

            for pattern in patterns:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND textPayload:"{pattern}"',
                    "--limit=1",
                    "--format=json",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout:
                    logs = json.loads(result.stdout)
                    if logs:
                        return {
                            "detected": True,
                            "evidence": f"Import error detected: {pattern}",
                            "severity": "HIGH",
                        }

        except Exception as e:
            logger.debug(f"Error checking import error pattern: {e}")
        return None

    def _check_generic_log_pattern(self, pattern_def: Dict) -> Optional[Dict]:
        """汎用ログパターン検出"""
        try:
            log_patterns = pattern_def.get("detection", {}).get("log_patterns", [])

            if not log_patterns:
                return None

            for pattern in log_patterns:
                cmd = [
                    "gcloud",
                    "logging",
                    "read",
                    f'resource.type="cloud_run_revision" AND textPayload:"{pattern}"',
                    "--limit=2",
                    "--format=json",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

                if result.returncode == 0 and result.stdout:
                    logs = json.loads(result.stdout)
                    if logs:
                        return {
                            "detected": True,
                            "evidence": f"Pattern '{pattern}' found in logs",
                            "matches": len(logs),
                        }
        except Exception as e:
            logger.debug(f"Error checking generic pattern: {e}")
        return None

    def check_performance_anomalies(self) -> Dict[str, Any]:
        """パフォーマンス異常検出"""
        logger.info("🔍 Checking performance anomalies...")

        anomalies = []

        try:
            # メモリ使用量トレンド確認
            memory_anomaly = self._check_memory_trend()
            if memory_anomaly:
                anomalies.append(memory_anomaly)

            # レスポンス時間劣化確認
            response_anomaly = self._check_response_time_degradation()
            if response_anomaly:
                anomalies.append(response_anomaly)

            if anomalies:
                critical_count = len(
                    [a for a in anomalies if a.get("severity") == "CRITICAL"]
                )

                return {
                    "status": "critical" if critical_count > 0 else "warning",
                    "anomalies": anomalies,
                    "anomaly_count": len(anomalies),
                    "details": f"{len(anomalies)} performance anomalies detected",
                }
            else:
                return {
                    "status": "healthy",
                    "anomalies": [],
                    "anomaly_count": 0,
                    "details": "No performance anomalies detected",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Performance check failed: {type(e).__name__}",
            }

    def _check_memory_trend(self) -> Optional[Dict]:
        """メモリ使用量トレンド確認"""
        try:
            cmd = [
                "gcloud",
                "logging",
                "read",
                'resource.type="cloud_run_revision" AND textPayload:"memory"',
                "--limit=10",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)
                memory_values = []

                for log in logs:
                    text = str(log.get("textPayload", ""))
                    memory_match = re.search(
                        r"memory.*?(\d+).*?MB", text, re.IGNORECASE
                    )

                    if memory_match:
                        memory_mb = int(memory_match.group(1))
                        memory_values.append(memory_mb)

                if len(memory_values) >= 5:
                    # 増加トレンド確認
                    avg_early = sum(memory_values[-5:-2]) / 3
                    avg_recent = sum(memory_values[:3]) / 3

                    if avg_recent > avg_early * 1.2:  # 20%以上の増加
                        return {
                            "type": "memory_growth",
                            "severity": "HIGH",
                            "evidence": f"Memory growth detected: {avg_early:.0f}MB → {avg_recent:.0f}MB",
                            "growth_percent": (avg_recent - avg_early)
                            / avg_early
                            * 100,
                        }

                    # 高メモリ使用量確認
                    if avg_recent > 1500:  # 1.5GB閾値
                        return {
                            "type": "high_memory_usage",
                            "severity": "MEDIUM",
                            "evidence": f"High memory usage: {avg_recent:.0f}MB",
                            "memory_mb": avg_recent,
                        }

        except Exception as e:
            logger.debug(f"Error checking memory trend: {e}")
        return None

    def _check_response_time_degradation(self) -> Optional[Dict]:
        """レスポンス時間劣化確認"""
        try:
            # 複数回のレスポンス時間測定
            response_times = []

            for _ in range(3):
                start_time = time.time()
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=10)
                    if response.status_code == 200:
                        response_times.append(time.time() - start_time)
                except Exception:
                    pass
                time.sleep(1)

            if len(response_times) >= 2:
                avg_response_time = sum(response_times) / len(response_times)

                if avg_response_time > 5.0:  # 5秒以上
                    return {
                        "type": "slow_response",
                        "severity": "HIGH",
                        "evidence": f"Slow response time: {avg_response_time:.2f}s",
                        "avg_response_time": avg_response_time,
                    }
                elif avg_response_time > 3.0:  # 3秒以上
                    return {
                        "type": "moderate_slow_response",
                        "severity": "MEDIUM",
                        "evidence": f"Moderate slow response: {avg_response_time:.2f}s",
                        "avg_response_time": avg_response_time,
                    }

        except Exception as e:
            logger.debug(f"Error checking response time: {e}")
        return None

    def check_future_data_leaks(self) -> Dict[str, Any]:
        """未来データリーク検出（既存tool活用）"""
        logger.info("🔍 Checking for future data leaks...")

        try:
            # future_leak_detector.pyを活用
            leak_script = PROJECT_ROOT / "scripts/monitoring/future_leak_detector.py"
            if not leak_script.exists():
                return {
                    "status": "error",
                    "error": "future_leak_detector.py not found",
                    "details": "Future leak detector missing",
                }

            cmd = ["python", str(leak_script), "--project-root", str(PROJECT_ROOT)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # future_leak_detector結果解析
            if result.returncode == 0:
                return {
                    "status": "healthy",
                    "leak_count": 0,
                    "details": "No future data leaks detected",
                }
            elif result.returncode == 1:
                # High priority issues
                return {
                    "status": "warning",
                    "leak_count": "some",
                    "details": "Medium priority future leak issues",
                }
            elif result.returncode == 2:
                # Critical issues
                return {
                    "status": "critical",
                    "leak_count": "many",
                    "details": "Critical future data leak issues",
                }
            else:
                return {
                    "status": "error",
                    "error": "Future leak detector failed",
                    "return_code": result.returncode,
                    "details": f"Exit code: {result.returncode}",
                }

        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "error": "Future leak detection timeout",
                "details": "Leak detection took too long",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Leak detection failed: {type(e).__name__}",
            }

    def check_config_integrity(self) -> Dict[str, Any]:
        """設定整合性チェック"""
        logger.info("🔍 Checking configuration integrity...")

        issues = []

        try:
            # 本番設定ファイル存在確認
            prod_config = PROJECT_ROOT / "config/production/production.yml"
            if not prod_config.exists():
                issues.append(
                    {
                        "type": "missing_prod_config",
                        "severity": "CRITICAL",
                        "message": "Production config file missing",
                    }
                )

            # 本番モデル存在確認
            prod_model = PROJECT_ROOT / "models/production/model.pkl"
            if not prod_model.exists():
                issues.append(
                    {
                        "type": "missing_prod_model",
                        "severity": "HIGH",
                        "message": "Production model file missing",
                    }
                )

            # 重要な設定値確認（本番設定ファイルから）
            if prod_config.exists():
                try:
                    import yaml

                    with open(prod_config, "r") as f:
                        config = yaml.safe_load(f)

                    # 重要設定の検証
                    # confidence_thresholdは複数箇所にある可能性があるため、全てチェック
                    ml_config = config.get("ml", {})
                    strategy_config = config.get("strategy", {})
                    ensemble_config = ml_config.get("ensemble", {})

                    # いずれかの場所から値を取得（優先順位: strategy > ensemble > ml）
                    confidence_threshold = (
                        strategy_config.get("confidence_threshold")
                        or ensemble_config.get("confidence_threshold")
                        or ml_config.get("confidence_threshold")
                        or 0
                    )

                    if confidence_threshold < 0.1:
                        issues.append(
                            {
                                "type": "low_confidence_threshold",
                                "severity": "MEDIUM",
                                "message": f"Very low confidence threshold: {confidence_threshold}",
                            }
                        )
                except Exception as e:
                    issues.append(
                        {
                            "type": "config_parse_error",
                            "severity": "HIGH",
                            "message": f"Failed to parse config: {str(e)}",
                        }
                    )

            if issues:
                critical_count = len([i for i in issues if i["severity"] == "CRITICAL"])

                return {
                    "status": "critical" if critical_count > 0 else "warning",
                    "issues": issues,
                    "issue_count": len(issues),
                    "details": f"{len(issues)} configuration issues found",
                }
            else:
                return {
                    "status": "healthy",
                    "issues": [],
                    "issue_count": 0,
                    "details": "Configuration integrity OK",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Config check failed: {type(e).__name__}",
            }

    def run_phase3_hidden_issues_detection(self) -> Dict[str, Any]:
        """Phase 3: 隠れた問題検出を実行"""
        logger.info("🚀 === Phase 3: 隠れた問題検出 ===")

        phase3_results = {
            "phase_name": "隠れた問題検出",
            "weight": self.config["check_phases"]["phase3"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "hidden_error_patterns": self.check_hidden_error_patterns(),
            "performance_anomalies": self.check_performance_anomalies(),
            "future_data_leaks": self.check_future_data_leaks(),
            "config_integrity": self.check_config_integrity(),
        }

        phase3_results["checks"] = checks

        # Phase 3スコア計算
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "info":
                score = 85
            elif status == "warning":
                score = 50
            elif status == "critical":
                score = 10
            elif status in ["timeout", "unknown"]:
                score = 60
            else:  # error
                score = 0

            check_scores.append(score)

            # 重大な問題を記録
            if score < 70:
                severity = (
                    "CRITICAL" if score <= 20 else "HIGH" if score <= 50 else "MEDIUM"
                )
                phase3_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": severity,
                        "message": check_result.get(
                            "error", check_result.get("details", "Unknown issue")
                        ),
                        "score": score,
                    }
                )

        # Phase 3総合スコア
        phase3_results["score"] = (
            sum(check_scores) / len(check_scores) if check_scores else 0
        )

        # Phase 3ステータス判定
        if phase3_results["score"] >= 80:
            phase3_results["status"] = "healthy"
        elif phase3_results["score"] >= 60:
            phase3_results["status"] = "warning"
        else:
            phase3_results["status"] = "critical"

        logger.info(
            f"✅ Phase 3 完了: スコア {phase3_results['score']:.1f}/100 ({phase3_results['status']})"
        )

        self.results["phases"]["phase3"] = phase3_results
        return phase3_results

    # ===== Phase 4: 総合判定・レポート生成システム =====

    def calculate_overall_scoring(self) -> Dict[str, Any]:
        """全体スコアリング計算"""
        logger.info("🔍 Calculating overall scoring...")

        try:
            phase_scores = {}
            total_score = 0
            total_weight = 0

            # 各フェーズのスコア収集
            for phase_name, phase_data in self.results["phases"].items():
                if phase_name != "phase4":  # Phase 4は除く
                    weight = phase_data.get("weight", 25)
                    score = phase_data.get("score", 0)
                    status = phase_data.get("status", "unknown")

                    phase_scores[phase_name] = {
                        "score": score,
                        "weight": weight,
                        "status": status,
                        "weighted_score": score * weight,
                    }

                    total_score += score * weight
                    total_weight += weight

            overall_score = total_score / total_weight if total_weight > 0 else 0

            # 総合ステータス判定
            if overall_score >= 90:
                overall_status = "excellent"
            elif overall_score >= 80:
                overall_status = "healthy"
            elif overall_score >= 60:
                overall_status = "warning"
            elif overall_score >= 40:
                overall_status = "degraded"
            else:
                overall_status = "critical"

            return {
                "status": "healthy",
                "overall_score": overall_score,
                "overall_status": overall_status,
                "phase_scores": phase_scores,
                "total_weight": total_weight,
                "details": f"Overall score: {overall_score:.1f}/100 ({overall_status})",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Scoring calculation failed: {type(e).__name__}",
            }

    def assess_risk_levels(self) -> Dict[str, Any]:
        """リスク評価・分析"""
        logger.info("🔍 Assessing risk levels...")

        try:
            all_issues = []

            # 全フェーズから問題を収集
            for phase_name, phase_data in self.results["phases"].items():
                if phase_name != "phase4":
                    phase_issues = phase_data.get("issues", [])
                    for issue in phase_issues:
                        issue["phase"] = phase_name
                        all_issues.append(issue)

            # 重要度別分析
            critical_issues = [i for i in all_issues if i.get("severity") == "CRITICAL"]
            high_issues = [i for i in all_issues if i.get("severity") == "HIGH"]
            medium_issues = [i for i in all_issues if i.get("severity") == "MEDIUM"]

            # リスクレベル判定
            if len(critical_issues) >= 3:
                risk_level = "EXTREME"
            elif len(critical_issues) >= 1:
                risk_level = "HIGH"
            elif len(high_issues) >= 3:
                risk_level = "MEDIUM"
            elif len(high_issues) >= 1 or len(medium_issues) >= 5:
                risk_level = "LOW"
            else:
                risk_level = "MINIMAL"

            # 問題カテゴリ分析
            problem_categories = {}
            for issue in all_issues:
                check = issue.get("check", "unknown")
                category = self._categorize_check(check)
                if category not in problem_categories:
                    problem_categories[category] = 0
                problem_categories[category] += 1

            return {
                "status": "healthy",
                "risk_level": risk_level,
                "total_issues": len(all_issues),
                "critical_count": len(critical_issues),
                "high_count": len(high_issues),
                "medium_count": len(medium_issues),
                "problem_categories": problem_categories,
                "critical_issues": critical_issues[:5],  # 最重要5件
                "details": f"Risk level: {risk_level} ({len(all_issues)} total issues)",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Risk assessment failed: {type(e).__name__}",
            }

    def _categorize_check(self, check_name: str) -> str:
        """チェック名からカテゴリを特定"""
        if "gcp" in check_name or "cloud" in check_name:
            return "Infrastructure"
        elif "api" in check_name or "connectivity" in check_name:
            return "API/Connectivity"
        elif "data" in check_name or "fetch" in check_name:
            return "Data Processing"
        elif "signal" in check_name or "model" in check_name:
            return "ML/Trading"
        elif "hidden" in check_name or "pattern" in check_name:
            return "Hidden Issues"
        elif "performance" in check_name or "memory" in check_name:
            return "Performance"
        elif "config" in check_name:
            return "Configuration"
        else:
            return "Other"

    def generate_action_recommendations(self) -> Dict[str, Any]:
        """アクション提案生成"""
        logger.info("🔍 Generating action recommendations...")

        try:
            recommendations = []
            urgent_actions = []

            # Phase別の問題から推奨アクションを生成
            for phase_name, phase_data in self.results["phases"].items():
                if phase_name == "phase4":
                    continue

                phase_issues = phase_data.get("issues", [])

                for issue in phase_issues:
                    check = issue.get("check", "")
                    severity = issue.get("severity", "")

                    actions = self._generate_actions_for_issue(
                        check, severity, issue.get("message", "")
                    )

                    for action in actions:
                        if severity == "CRITICAL":
                            action["priority"] = "IMMEDIATE"
                            urgent_actions.append(action)
                        else:
                            action["priority"] = severity
                            recommendations.append(action)

            # 重複排除
            unique_recommendations = self._deduplicate_recommendations(recommendations)
            unique_urgent = self._deduplicate_recommendations(urgent_actions)

            return {
                "status": "healthy",
                "urgent_actions": unique_urgent,
                "recommendations": unique_recommendations,
                "total_actions": len(unique_urgent) + len(unique_recommendations),
                "details": f"{len(unique_urgent)} urgent actions, {len(unique_recommendations)} recommendations",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Recommendation generation failed: {type(e).__name__}",
            }

    def _generate_actions_for_issue(
        self, check: str, severity: str, message: str
    ) -> List[Dict]:
        """問題に対する具体的アクション生成"""
        actions = []

        # インフラ系問題
        if "gcp" in check or "cloud_run" in check:
            actions.append(
                {
                    "action": "Restart GCP Cloud Run service",
                    "command": "gcloud run services update crypto-bot-service-prod --region=asia-northeast1",
                    "category": "Infrastructure",
                }
            )

        # API接続問題
        elif "api_connectivity" in check:
            actions.append(
                {
                    "action": "Check API credentials and connectivity",
                    "command": "curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health",
                    "category": "API",
                }
            )

        # データ取得問題
        elif "data_fetch" in check:
            if "48/300" in message:
                actions.append(
                    {
                        "action": "Fix data fetch stagnation (48/300 issue)",
                        "command": "Check API rate limits and reconnect to exchange",
                        "category": "Data",
                    }
                )

        # シグナル生成問題
        elif "signal_generation" in check:
            actions.append(
                {
                    "action": "Check ML model and feature pipeline",
                    "command": "python scripts/validate_97_features_optimization.py",
                    "category": "ML",
                }
            )

        # パフォーマンス問題
        elif "performance" in check or "memory" in check:
            actions.append(
                {
                    "action": "Monitor resource usage and restart if needed",
                    "command": "Check memory usage and consider scaling up",
                    "category": "Performance",
                }
            )

        # 隠れた問題
        elif "hidden" in check:
            actions.append(
                {
                    "action": "Address detected hidden error patterns",
                    "command": "Review specific pattern and apply past solutions",
                    "category": "Hidden Issues",
                }
            )

        # デフォルトアクション
        if not actions:
            actions.append(
                {
                    "action": f"Review {check} issue",
                    "command": f"Investigate: {message[:50]}...",
                    "category": "General",
                }
            )

        return actions

    def _deduplicate_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """重複する推奨事項を除去"""
        seen = set()
        unique = []

        for rec in recommendations:
            key = (rec.get("action", ""), rec.get("category", ""))
            if key not in seen:
                seen.add(key)
                unique.append(rec)

        return unique

    def generate_detailed_report(self) -> Dict[str, Any]:
        """詳細レポート生成"""
        logger.info("🔍 Generating detailed report...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # HTMLレポート生成
            html_report = self._generate_html_report()
            html_path = self.report_dir / f"operational_status_{timestamp}.html"

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_report)

            return {
                "status": "healthy",
                "html_report_path": str(html_path),
                "json_report_path": f"logs/operational_reports/operational_status_{timestamp}.json",
                "report_timestamp": timestamp,
                "details": f"Detailed report generated: {html_path}",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "details": f"Report generation failed: {type(e).__name__}",
            }

    def _generate_html_report(self) -> str:
        """HTML詳細レポート生成"""
        overall_score = self.results.get("overall_score", 0)
        overall_status = self.results.get("overall_status", "unknown")

        # ステータスに応じた色設定
        if overall_status == "critical":
            score_color = "#d32f2f"
        elif overall_status == "warning":
            score_color = "#f57c00"
        else:
            score_color = "#388e3c"

        html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>crypto-bot 完璧稼働状況確認レポート</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background: #f5f7fa; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 30px; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header .subtitle {{ opacity: 0.9; margin-top: 10px; }}
        .score-display {{ background: white; padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .score-number {{ font-size: 4em; font-weight: bold; color: {score_color}; }}
        .score-status {{ font-size: 1.5em; color: #666; margin-top: 10px; }}
        .phases {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .phase {{ background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .phase h3 {{ margin-top: 0; color: #333; }}
        .check {{ display: flex; align-items: center; margin: 10px 0; }}
        .check-icon {{ margin-right: 10px; font-size: 1.2em; }}
        .issues {{ background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; }}
        .issue {{ padding: 12px; margin: 8px 0; border-left: 4px solid #e74c3c; background: #fff5f5; border-radius: 4px; }}
        .issue.HIGH {{ border-color: #f39c12; background: #fffcf0; }}
        .issue.MEDIUM {{ border-color: #3498db; background: #f0f8ff; }}
        .recommendations {{ background: white; padding: 20px; border-radius: 12px; }}
        .recommendation {{ padding: 12px; margin: 8px 0; background: #e8f5e9; border-radius: 4px; border-left: 4px solid #4caf50; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 crypto-bot 完璧稼働状況確認レポート</h1>
            <div class="subtitle">生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S JST')}</div>
        </div>

        <div class="score-display">
            <div class="score-number">{overall_score:.1f}</div>
            <div class="score-status">/ 100 ({overall_status})</div>
        </div>

        <div class="phases">
"""

        # 各フェーズの結果表示
        for phase_name, phase_data in self.results["phases"].items():
            if phase_name == "phase4":
                continue

            phase_title = phase_data.get("phase_name", phase_name)
            phase_score = phase_data.get("score", 0)
            phase_status = phase_data.get("status", "unknown")

            html += f"""
            <div class="phase">
                <h3>{phase_title}</h3>
                <div style="font-size: 2em; color: {score_color};">{phase_score:.1f}/100</div>
                <div style="color: #666; margin-bottom: 15px;">Status: {phase_status}</div>
"""

            # チェック結果表示
            checks = phase_data.get("checks", {})
            for check_name, check_result in checks.items():
                status = check_result.get("status", "unknown")
                if status == "healthy":
                    icon = "✅"
                elif status in ["warning", "degraded", "info"]:
                    icon = "⚠️"
                else:
                    icon = "❌"

                details = check_result.get("details", "No details")
                html += f"""
                <div class="check">
                    <span class="check-icon">{icon}</span>
                    <div>
                        <strong>{check_name.replace('_', ' ').title()}</strong><br>
                        <small>{details}</small>
                    </div>
                </div>
"""

            html += "</div>"

        html += "</div>"

        # 問題一覧
        all_issues = []
        for phase_name, phase_data in self.results["phases"].items():
            if phase_name != "phase4":
                all_issues.extend(phase_data.get("issues", []))

        if all_issues:
            html += '<div class="issues"><h2>🚨 検出された問題</h2>'
            for issue in all_issues[:10]:  # 最初の10件
                severity = issue.get("severity", "MEDIUM")
                message = issue.get("message", "Unknown issue")
                check = issue.get("check", "unknown")

                html += f"""
                <div class="issue {severity}">
                    <strong>[{severity}] {check.replace('_', ' ').title()}</strong><br>
                    {message}
                </div>
"""
            html += "</div>"

        # 推奨事項（Phase 4結果から取得）
        phase4_data = self.results["phases"].get("phase4", {})
        action_recs = phase4_data.get("checks", {}).get("action_recommendations", {})
        urgent_actions = action_recs.get("urgent_actions", [])
        recommendations = action_recs.get("recommendations", [])

        if urgent_actions or recommendations:
            html += '<div class="recommendations"><h2>💡 推奨アクション</h2>'

            if urgent_actions:
                html += "<h3>🚨 緊急アクション</h3>"
                for action in urgent_actions[:5]:
                    html += f"""
                    <div class="recommendation" style="border-color: #e74c3c; background: #fff5f5;">
                        <strong>{action.get("action", "Unknown action")}</strong><br>
                        <code>{action.get("command", "")}</code>
                    </div>
"""

            if recommendations:
                html += "<h3>📋 推奨事項</h3>"
                for rec in recommendations[:8]:
                    html += f"""
                    <div class="recommendation">
                        <strong>{rec.get("action", "Unknown action")}</strong><br>
                        <code>{rec.get("command", "")}</code>
                    </div>
"""

            html += "</div>"

        html += """
    </div>
</body>
</html>
"""

        return html

    def run_phase4_overall_assessment(self) -> Dict[str, Any]:
        """Phase 4: 総合判定・レポート生成を実行"""
        logger.info("🚀 === Phase 4: 総合判定・レポート生成 ===")

        phase4_results = {
            "phase_name": "総合判定・レポート生成",
            "weight": self.config["check_phases"]["phase4"]["weight"],
            "checks": {},
            "score": 0,
            "status": "unknown",
            "issues": [],
        }

        # 各チェック実行
        checks = {
            "overall_scoring": self.calculate_overall_scoring(),
            "risk_assessment": self.assess_risk_levels(),
            "action_recommendations": self.generate_action_recommendations(),
            "report_generation": self.generate_detailed_report(),
        }

        phase4_results["checks"] = checks

        # Phase 4スコア計算（他のフェーズとは異なり、分析品質ベース）
        check_scores = []
        for check_name, check_result in checks.items():
            status = check_result.get("status", "error")

            if status == "healthy":
                score = 100
            elif status == "warning":
                score = 70
            elif status == "critical":
                score = 30
            else:  # error
                score = 50  # 分析エラーでも部分的にスコア付与

            check_scores.append(score)

            # 分析に問題がある場合のみissuesに追加
            if score < 80:
                phase4_results["issues"].append(
                    {
                        "check": check_name,
                        "severity": "MEDIUM",
                        "message": check_result.get(
                            "error", check_result.get("details", "Analysis issue")
                        ),
                        "score": score,
                    }
                )

        # Phase 4総合スコア
        phase4_results["score"] = (
            sum(check_scores) / len(check_scores) if check_scores else 0
        )

        # Phase 4ステータス判定
        if phase4_results["score"] >= 90:
            phase4_results["status"] = "healthy"
        elif phase4_results["score"] >= 70:
            phase4_results["status"] = "warning"
        else:
            phase4_results["status"] = "degraded"

        logger.info(
            f"✅ Phase 4 完了: スコア {phase4_results['score']:.1f}/100 ({phase4_results['status']})"
        )

        self.results["phases"]["phase4"] = phase4_results
        return phase4_results

    def run_comprehensive_check(
        self, target_phases: List[str] = None
    ) -> Dict[str, Any]:
        """包括的稼働状況確認を実行"""
        logger.info("🎯 === crypto-bot 完璧稼働状況確認開始 ===")
        logger.info(f"📅 実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S JST')}")

        # Phase 1実行
        if not target_phases or "phase1" in target_phases:
            self.run_phase1_infrastructure_checks()

        # Phase 2実行
        if not target_phases or "phase2" in target_phases:
            self.run_phase2_application_checks()

        # Phase 3実行
        if not target_phases or "phase3" in target_phases:
            self.run_phase3_hidden_issues_detection()

        # Phase 4実行
        if not target_phases or "phase4" in target_phases:
            self.run_phase4_overall_assessment()

        # 総合評価（全フェーズの重み付き平均）
        total_score = 0
        total_weight = 0

        for phase_name, phase_data in self.results["phases"].items():
            weight = phase_data.get("weight", 25)
            score = phase_data.get("score", 0)
            total_score += score * weight
            total_weight += weight

        if total_weight > 0:
            self.results["overall_score"] = total_score / total_weight

            if self.results["overall_score"] >= 80:
                self.results["overall_status"] = "healthy"
            elif self.results["overall_score"] >= 60:
                self.results["overall_status"] = "warning"
            else:
                self.results["overall_status"] = "critical"

        self._generate_final_report()

        logger.info("🎊 === 稼働状況確認完了 ===")
        return self.results

    def _generate_final_report(self):
        """最終レポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # コンソール出力
        print("\n" + "=" * 60)
        print("📊 crypto-bot 稼働状況確認結果")
        print("=" * 60)
        print(f"🕐 実行時刻: {self.results['timestamp']}")
        print(f"🎯 総合スコア: {self.results['overall_score']:.1f}/100")
        print(f"🔍 総合状態: {self.results['overall_status']}")

        # Phase 1結果表示
        if "phase1" in self.results["phases"]:
            phase1 = self.results["phases"]["phase1"]
            print(
                f"\n📋 Phase 1 (インフラ・基盤): {phase1['score']:.1f}/100 ({phase1['status']})"
            )

            for check_name, check_result in phase1["checks"].items():
                status_icon = (
                    "✅"
                    if check_result.get("status") == "healthy"
                    else (
                        "⚠️"
                        if check_result.get("status") in ["warning", "degraded"]
                        else "❌"
                    )
                )
                print(
                    f"  {status_icon} {check_name}: {check_result.get('details', 'No details')}"
                )

        # Phase 2結果表示
        if "phase2" in self.results["phases"]:
            phase2 = self.results["phases"]["phase2"]
            print(
                f"\n📋 Phase 2 (アプリケーション動作): {phase2['score']:.1f}/100 ({phase2['status']})"
            )

            for check_name, check_result in phase2["checks"].items():
                status_icon = (
                    "✅"
                    if check_result.get("status") == "healthy"
                    else (
                        "⚠️"
                        if check_result.get("status") in ["warning", "degraded"]
                        else "❌"
                    )
                )
                print(
                    f"  {status_icon} {check_name}: {check_result.get('details', 'No details')}"
                )

        # Phase 3結果表示
        if "phase3" in self.results["phases"]:
            phase3 = self.results["phases"]["phase3"]
            print(
                f"\n📋 Phase 3 (隠れた問題検出): {phase3['score']:.1f}/100 ({phase3['status']})"
            )

            for check_name, check_result in phase3["checks"].items():
                status_icon = (
                    "✅"
                    if check_result.get("status") == "healthy"
                    else (
                        "⚠️"
                        if check_result.get("status") in ["warning", "info"]
                        else "❌"
                    )
                )
                print(
                    f"  {status_icon} {check_name}: {check_result.get('details', 'No details')}"
                )

        # Phase 4結果表示
        if "phase4" in self.results["phases"]:
            phase4 = self.results["phases"]["phase4"]
            print(
                f"\n📋 Phase 4 (総合判定・レポート): {phase4['score']:.1f}/100 ({phase4['status']})"
            )

            for check_name, check_result in phase4["checks"].items():
                status_icon = (
                    "✅"
                    if check_result.get("status") == "healthy"
                    else (
                        "⚠️"
                        if check_result.get("status") in ["warning", "degraded"]
                        else "❌"
                    )
                )
                print(
                    f"  {status_icon} {check_name}: {check_result.get('details', 'No details')}"
                )

            # HTMLレポートパス表示（特別扱い）
            report_gen = phase4["checks"].get("report_generation", {})
            if report_gen.get("html_report_path"):
                print(f"  📄 HTML詳細レポート: {report_gen['html_report_path']}")

        # 問題がある場合は表示
        all_issues = []
        for phase_name, phase_data in self.results["phases"].items():
            all_issues.extend(phase_data.get("issues", []))

        if all_issues:
            print(f"\n⚠️ 検出された問題 ({len(all_issues)}件):")
            for issue in all_issues:
                print(
                    f"  🔸 [{issue['severity']}] {issue['check']}: {issue['message']}"
                )
        else:
            print("\n✅ 問題は検出されませんでした")

        print("=" * 60)

        # JSONレポート保存
        json_path = self.report_dir / f"operational_status_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"📁 詳細レポート保存: {json_path}")


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="crypto-bot 完璧稼働状況確認システム")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細ログ出力")
    parser.add_argument(
        "--save-report", "-s", action="store_true", help="レポートファイル保存"
    )
    parser.add_argument(
        "--phase",
        choices=["phase1", "phase2", "phase3", "phase4"],
        help="特定フェーズのみ実行",
    )
    parser.add_argument("--config", help="設定ファイルパス")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # システム実行
    checker = OperationalStatusChecker(config_path=args.config)

    target_phases = [args.phase] if args.phase else None
    results = checker.run_comprehensive_check(target_phases)

    # 終了コード設定
    if results["overall_status"] == "critical":
        sys.exit(2)  # Critical issues
    elif results["overall_status"] == "warning":
        sys.exit(1)  # Warning issues
    else:
        sys.exit(0)  # Success


if __name__ == "__main__":
    main()
