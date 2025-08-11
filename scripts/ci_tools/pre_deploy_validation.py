#!/usr/bin/env python
"""
本番デプロイ前統合検証スクリプト

Phase 2-3統合: ChatGPT提案実装
1. 未来データリーク検出
2. ペーパートレード実行
3. シグナルモニタリング

本番デプロイ前にこのスクリプトを実行することで、
包括的な検証を行い、エラーを事前に発見できます。
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PreDeployValidator:
    """本番デプロイ前の統合検証クラス"""

    def __init__(self, config_path: str = "config/production/production.yml"):
        self.config_path = config_path
        self.report_dir = Path("logs/pre_deploy_validation")
        self.report_dir.mkdir(exist_ok=True, parents=True)

        # 検証結果
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "config": config_path,
            "checks": [],
            "overall_status": "PENDING",
            "deployment_ready": False,
        }

    def run_future_leak_detection(self) -> Tuple[bool, Dict]:
        """未来データリーク検出を実行"""
        logger.info("=" * 60)
        logger.info("🔍 STEP 1/4: Future Data Leak Detection")
        logger.info("=" * 60)

        try:
            # 未来リーク検出器を実行
            cmd = [
                "python",
                "scripts/utilities/future_leak_detector.py",
                "--project-root",
                ".",
                "--html",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            # 終了コードで判定
            # 0: 問題なし, 1: HIGH issues, 2: CRITICAL issues
            status = "PASS" if result.returncode == 0 else "FAIL"

            # 出力から問題数を抽出
            issues_count = 0
            for line in result.stdout.split("\n"):
                if "Total issues:" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        issues_count = int(parts[-1].strip())

            check_result = {
                "name": "Future Leak Detection",
                "status": status,
                "issues_count": issues_count,
                "exit_code": result.returncode,
                "message": f"Found {issues_count} potential future data leaks",
            }

            if result.returncode == 0:
                logger.info(f"✅ No critical future data leaks detected")
            elif result.returncode == 1:
                logger.warning(f"⚠️ Found {issues_count} HIGH priority issues")
            else:
                logger.error(f"❌ Found CRITICAL future data leak issues")

            self.validation_results["checks"].append(check_result)
            return result.returncode == 0, check_result

        except subprocess.TimeoutExpired:
            logger.error("❌ Future leak detection timed out")
            check_result = {
                "name": "Future Leak Detection",
                "status": "ERROR",
                "message": "Detection timed out after 60 seconds",
            }
            self.validation_results["checks"].append(check_result)
            return False, check_result

        except Exception as e:
            logger.error(f"❌ Future leak detection failed: {e}")
            check_result = {
                "name": "Future Leak Detection",
                "status": "ERROR",
                "message": str(e),
            }
            self.validation_results["checks"].append(check_result)
            return False, check_result

    def run_paper_trading(self, duration_minutes: int = 5) -> Tuple[bool, Dict]:
        """ペーパートレードを実行"""
        logger.info("=" * 60)
        logger.info("📈 STEP 2/4: Paper Trading Test")
        logger.info("=" * 60)

        try:
            # ペーパートレードを起動
            cmd = [
                "python",
                "-m",
                "crypto_bot.main",
                "live-bitbank",
                "--config",
                self.config_path,
                "--paper-trade",
            ]

            logger.info(f"Starting {duration_minutes} minute paper trading test...")

            # バックグラウンドで実行
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            # 指定時間実行
            time.sleep(duration_minutes * 60)

            # プロセスを終了
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()

            # 結果ファイルを確認
            results_path = Path("logs/paper_trading_results.json")
            if results_path.exists():
                with open(results_path) as f:
                    paper_results = json.load(f)

                total_trades = paper_results.get("total_trades", 0)
                win_rate = paper_results.get("win_rate", 0)
                final_balance = paper_results.get("final_balance", 0)

                # 成功判定：エラーなく実行でき、取引が発生
                status = "PASS" if total_trades > 0 else "WARNING"

                check_result = {
                    "name": "Paper Trading",
                    "status": status,
                    "duration_minutes": duration_minutes,
                    "total_trades": total_trades,
                    "win_rate": win_rate,
                    "final_balance": final_balance,
                    "message": f"Executed {total_trades} trades in {duration_minutes} minutes",
                }

                if total_trades > 0:
                    logger.info(
                        f"✅ Paper trading successful: {total_trades} trades executed"
                    )
                else:
                    logger.warning(f"⚠️ No trades executed during paper trading")

            else:
                # 結果ファイルがない場合
                check_result = {
                    "name": "Paper Trading",
                    "status": "WARNING",
                    "duration_minutes": duration_minutes,
                    "message": "No results file generated",
                }
                logger.warning("⚠️ Paper trading results file not found")

            self.validation_results["checks"].append(check_result)
            return check_result["status"] == "PASS", check_result

        except Exception as e:
            logger.error(f"❌ Paper trading failed: {e}")
            check_result = {
                "name": "Paper Trading",
                "status": "ERROR",
                "message": str(e),
            }
            self.validation_results["checks"].append(check_result)
            return False, check_result

    def run_signal_monitoring(self) -> Tuple[bool, Dict]:
        """シグナルモニタリングを実行"""
        logger.info("=" * 60)
        logger.info("🔔 STEP 3/4: Signal Monitoring Check")
        logger.info("=" * 60)

        try:
            # シグナルモニタリングを実行
            cmd = [
                "python",
                "scripts/utilities/signal_monitor.py",
                "--hours",
                "1",  # 直近1時間分をチェック
                "--threshold-alert",
                "60",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # 終了コードで判定
            status = "PASS" if result.returncode == 0 else "WARNING"

            # 出力からヘルススコアを抽出
            health_score = 0
            for line in result.stdout.split("\n"):
                if "Health Score:" in line:
                    parts = line.split(":")
                    if len(parts) > 1:
                        score_part = parts[-1].strip().split("/")[0]
                        health_score = int(score_part)

            check_result = {
                "name": "Signal Monitoring",
                "status": status,
                "health_score": health_score,
                "exit_code": result.returncode,
                "message": f"Signal health score: {health_score}/100",
            }

            if health_score >= 80:
                logger.info(f"✅ Signal generation healthy: {health_score}/100")
            elif health_score >= 60:
                logger.warning(f"⚠️ Signal generation warning: {health_score}/100")
            else:
                logger.error(f"❌ Signal generation unhealthy: {health_score}/100")

            self.validation_results["checks"].append(check_result)
            return health_score >= 60, check_result

        except subprocess.TimeoutExpired:
            logger.error("❌ Signal monitoring timed out")
            check_result = {
                "name": "Signal Monitoring",
                "status": "ERROR",
                "message": "Monitoring timed out after 30 seconds",
            }
            self.validation_results["checks"].append(check_result)
            return False, check_result

        except Exception as e:
            logger.error(f"❌ Signal monitoring failed: {e}")
            check_result = {
                "name": "Signal Monitoring",
                "status": "ERROR",
                "message": str(e),
            }
            self.validation_results["checks"].append(check_result)
            return False, check_result

    def run_unit_tests(self) -> Tuple[bool, Dict]:
        """ユニットテストを実行"""
        logger.info("=" * 60)
        logger.info("🧪 STEP 4/4: Unit Tests")
        logger.info("=" * 60)

        try:
            # 主要なテストを実行
            cmd = [
                "pytest",
                "tests/unit/ml/",
                "tests/unit/strategy/",
                "-v",
                "--tb=short",
                "--timeout=60",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            # 結果を解析
            passed = 0
            failed = 0
            for line in result.stdout.split("\n"):
                if "passed" in line:
                    # "5 passed in 2.34s" のような行を解析
                    parts = line.split()
                    if len(parts) > 0 and parts[0].isdigit():
                        passed = int(parts[0])
                if "failed" in line:
                    parts = line.split()
                    if len(parts) > 0 and parts[0].isdigit():
                        failed = int(parts[0])

            status = "PASS" if result.returncode == 0 else "FAIL"

            check_result = {
                "name": "Unit Tests",
                "status": status,
                "passed": passed,
                "failed": failed,
                "exit_code": result.returncode,
                "message": f"Tests: {passed} passed, {failed} failed",
            }

            if result.returncode == 0:
                logger.info(f"✅ All unit tests passed: {passed} tests")
            else:
                logger.error(f"❌ Unit tests failed: {failed} failures")

            self.validation_results["checks"].append(check_result)
            return result.returncode == 0, check_result

        except subprocess.TimeoutExpired:
            logger.error("❌ Unit tests timed out")
            check_result = {
                "name": "Unit Tests",
                "status": "ERROR",
                "message": "Tests timed out after 120 seconds",
            }
            self.validation_results["checks"].append(check_result)
            return False, check_result

        except Exception as e:
            logger.error(f"❌ Unit tests failed: {e}")
            check_result = {
                "name": "Unit Tests",
                "status": "ERROR",
                "message": str(e),
            }
            self.validation_results["checks"].append(check_result)
            return False, check_result

    def generate_html_report(self) -> Path:
        """HTMLレポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = self.report_dir / f"validation_{timestamp}.html"

        # 全体の状態を判定
        all_passed = all(
            check["status"] == "PASS" for check in self.validation_results["checks"]
        )
        has_errors = any(
            check["status"] == "ERROR" for check in self.validation_results["checks"]
        )

        if has_errors:
            overall_color = "red"
            overall_status = "FAILED - Errors Detected"
        elif all_passed:
            overall_color = "green"
            overall_status = "PASSED - Ready for Deployment"
        else:
            overall_color = "orange"
            overall_status = "WARNING - Review Required"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Pre-Deployment Validation Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #2c3e50; color: white; padding: 30px; border-radius: 8px; }}
        .status {{ font-size: 36px; color: {overall_color}; font-weight: bold; margin: 20px 0; }}
        .section {{ background-color: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .check {{ padding: 15px; margin: 10px 0; border-left: 5px solid; background-color: #f9f9f9; border-radius: 4px; }}
        .PASS {{ border-color: #27ae60; background-color: #e8f6e8; }}
        .WARNING {{ border-color: #f39c12; background-color: #fef5e7; }}
        .FAIL {{ border-color: #e74c3c; background-color: #fadbd8; }}
        .ERROR {{ border-color: #c0392b; background-color: #f2d7d5; }}
        .metric {{ display: inline-block; padding: 10px 20px; margin: 10px; background-color: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #34495e; color: white; }}
        .recommendation {{ background-color: #d5f4e6; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .command {{ font-family: 'Courier New', monospace; background-color: #2c3e50; color: #ecf0f1; padding: 10px; border-radius: 4px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Pre-Deployment Validation Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <div class="status">{overall_status}</div>
    </div>
    
    <div class="section">
        <h2>📋 Validation Summary</h2>
        <table>
            <tr>
                <th>Check</th>
                <th>Status</th>
                <th>Details</th>
            </tr>
"""

        for check in self.validation_results["checks"]:
            status_icon = {
                "PASS": "✅",
                "WARNING": "⚠️",
                "FAIL": "❌",
                "ERROR": "🔴",
            }.get(check["status"], "❓")

            html_content += f"""
            <tr>
                <td>{check['name']}</td>
                <td>{status_icon} {check['status']}</td>
                <td>{check.get('message', 'N/A')}</td>
            </tr>
"""

        html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>📊 Detailed Results</h2>
"""

        for check in self.validation_results["checks"]:
            html_content += f"""
        <div class="check {check['status']}">
            <h3>{check['name']}</h3>
            <p>{check.get('message', '')}</p>
"""

            # 詳細情報を表示
            for key, value in check.items():
                if key not in ["name", "status", "message"]:
                    html_content += (
                        f"            <p><strong>{key}:</strong> {value}</p>\n"
                    )

            html_content += "        </div>\n"

        # デプロイ判定と推奨事項
        deployment_ready = all_passed and not has_errors
        self.validation_results["deployment_ready"] = deployment_ready

        html_content += f"""
    </div>
    
    <div class="section">
        <h2>🎯 Deployment Recommendation</h2>
        <div class="recommendation">
"""

        if deployment_ready:
            html_content += """
            <h3 style="color: green;">✅ READY FOR DEPLOYMENT</h3>
            <p>All validation checks passed successfully. The system is ready for production deployment.</p>
            <div class="command">
                git push origin main
            </div>
"""
        else:
            html_content += """
            <h3 style="color: orange;">⚠️ REVIEW REQUIRED</h3>
            <p>Some validation checks failed or require attention. Please review the issues before deployment:</p>
            <ul>
"""
            for check in self.validation_results["checks"]:
                if check["status"] != "PASS":
                    html_content += f"                <li>{check['name']}: {check.get('message', 'Check failed')}</li>\n"

            html_content += """
            </ul>
            <p>Fix the issues and run validation again:</p>
            <div class="command">
                python scripts/pre_deploy_validation.py
            </div>
"""

        html_content += """
        </div>
    </div>
    
    <div class="section">
        <h2>📚 Next Steps</h2>
        <ol>
            <li>Review all warnings and errors in this report</li>
            <li>Fix any identified issues</li>
            <li>Run validation again until all checks pass</li>
            <li>Deploy to production using CI/CD pipeline</li>
            <li>Monitor production logs after deployment</li>
        </ol>
    </div>
</body>
</html>
"""

        with open(html_path, "w") as f:
            f.write(html_content)

        return html_path

    def run_validation(self, skip_paper_trade: bool = False) -> bool:
        """全検証を実行"""
        logger.info("=" * 60)
        logger.info("🚀 Starting Pre-Deployment Validation")
        logger.info("=" * 60)
        logger.info(f"Config: {self.config_path}")
        logger.info(f"Timestamp: {datetime.now()}")
        logger.info("=" * 60)

        # 各検証を実行
        checks_passed = []

        # 1. 未来データリーク検出
        passed, _ = self.run_future_leak_detection()
        checks_passed.append(passed)

        # 2. ペーパートレード（オプション）
        if not skip_paper_trade:
            passed, _ = self.run_paper_trading(duration_minutes=2)  # 短時間テスト
            checks_passed.append(passed)

        # 3. シグナルモニタリング
        passed, _ = self.run_signal_monitoring()
        checks_passed.append(passed)

        # 4. ユニットテスト
        passed, _ = self.run_unit_tests()
        checks_passed.append(passed)

        # 全体の判定
        all_passed = all(checks_passed)
        self.validation_results["overall_status"] = "PASS" if all_passed else "FAIL"

        # JSONレポート保存
        json_path = (
            self.report_dir
            / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(json_path, "w") as f:
            json.dump(self.validation_results, f, indent=2)

        # HTMLレポート生成
        html_path = self.generate_html_report()

        # 結果サマリー
        logger.info("=" * 60)
        logger.info("📊 VALIDATION SUMMARY")
        logger.info("=" * 60)

        for check in self.validation_results["checks"]:
            status_icon = "✅" if check["status"] == "PASS" else "❌"
            logger.info(f"{status_icon} {check['name']}: {check['status']}")

        logger.info("=" * 60)

        if all_passed:
            logger.info("✅ ALL VALIDATION CHECKS PASSED")
            logger.info("🚀 System is ready for deployment!")
            logger.info(f"📁 Report: {html_path}")
            return True
        else:
            logger.error("❌ VALIDATION FAILED")
            logger.error("🔧 Please fix the issues before deployment")
            logger.error(f"📁 Report: {html_path}")
            return False


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="Pre-deployment validation for crypto-bot"
    )
    parser.add_argument(
        "--config",
        default="config/production/production.yml",
        help="Configuration file path",
    )
    parser.add_argument(
        "--skip-paper-trade",
        action="store_true",
        help="Skip paper trading test",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick validation (skip time-consuming tests)",
    )

    args = parser.parse_args()

    # バリデーター初期化
    validator = PreDeployValidator(args.config)

    # 検証実行
    success = validator.run_validation(
        skip_paper_trade=args.skip_paper_trade or args.quick
    )

    # 終了コード
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
