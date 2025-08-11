#!/usr/bin/env python
"""
エラーログ分析・自動修復提案システム

Phase 3: ChatGPT提案採用
エラーパターンを学習し、過去の解決策から修復提案を生成
デプロイ後のトラブルシューティング時間を大幅削減
"""

import json
import logging
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ErrorAnalyzer:
    """エラーログ分析・修復提案クラス"""

    def __init__(
        self,
        solutions_db_path: str = "data/error_solutions.json",
        report_dir: str = "logs/error_analysis",
    ):
        self.solutions_db_path = Path(solutions_db_path)
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True, parents=True)

        # エラーパターンと解決策のデータベース
        self.error_patterns = self.load_solutions_db()

        # 分析結果
        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "errors": [],
            "patterns": {},
            "suggestions": [],
            "statistics": {},
        }

    def load_solutions_db(self) -> Dict:
        """エラー解決策データベースをロード"""
        if self.solutions_db_path.exists():
            with open(self.solutions_db_path) as f:
                return json.load(f)
        else:
            # デフォルトのパターンと解決策
            return {
                "patterns": [
                    {
                        "id": "api_auth_error",
                        "pattern": r"(401|403|Unauthorized|API key|authentication)",
                        "category": "Authentication",
                        "severity": "CRITICAL",
                        "solutions": [
                            "Check if API keys are properly set in environment variables",
                            "Verify API key permissions on Bitbank",
                            "Check if secrets are properly configured in GCP Secret Manager",
                            "Run: gcloud secrets versions list --secret=bitbank-api-key",
                        ],
                        "success_rate": 0.85,
                    },
                    {
                        "id": "model_not_found",
                        "pattern": r"(FileNotFoundError.*model\.pkl|No such file.*model|Model file not found)",
                        "category": "Model",
                        "severity": "HIGH",
                        "solutions": [
                            "Create model file: python scripts/create_proper_ensemble_model.py",
                            "Check if model exists: ls -la models/production/",
                            "For CI environment: python scripts/create_ci_model.py",
                            "Verify model path in config file",
                        ],
                        "success_rate": 0.92,
                    },
                    {
                        "id": "data_fetch_error",
                        "pattern": r"(HTTPError|Connection.*refused|timeout|rate limit)",
                        "category": "Network",
                        "severity": "MEDIUM",
                        "solutions": [
                            "Check network connectivity",
                            "Verify API rate limits",
                            "Add retry logic with exponential backoff",
                            "Check if exchange is under maintenance",
                        ],
                        "success_rate": 0.78,
                    },
                    {
                        "id": "feature_mismatch",
                        "pattern": r"(feature.*mismatch|expected.*features|shape.*mismatch)",
                        "category": "Features",
                        "severity": "HIGH",
                        "solutions": [
                            "Verify feature order: python scripts/validate_97_features_optimization.py",
                            "Check feature_order.json integrity",
                            "Retrain model with current features",
                            "Run feature consistency check",
                        ],
                        "success_rate": 0.88,
                    },
                    {
                        "id": "memory_error",
                        "pattern": r"(MemoryError|Out of memory|Cannot allocate memory)",
                        "category": "Resources",
                        "severity": "HIGH",
                        "solutions": [
                            "Increase Cloud Run memory allocation",
                            "Reduce batch size in configuration",
                            "Implement data streaming instead of loading all at once",
                            "Clear cache: rm -rf cache/*",
                        ],
                        "success_rate": 0.75,
                    },
                    {
                        "id": "import_error",
                        "pattern": r"(ImportError|ModuleNotFoundError|No module named)",
                        "category": "Dependencies",
                        "severity": "CRITICAL",
                        "solutions": [
                            "Install missing dependencies: pip install -r requirements/prod.txt",
                            "Check Python version compatibility",
                            "Verify PYTHONPATH settings",
                            "Rebuild Docker image if using containers",
                        ],
                        "success_rate": 0.90,
                    },
                    {
                        "id": "confidence_threshold",
                        "pattern": r"(confidence.*threshold|No trades|confidence.*low)",
                        "category": "Trading",
                        "severity": "LOW",
                        "solutions": [
                            "Check current threshold in config: grep confidence config/production/production.yml",
                            "Consider lowering threshold if no trades",
                            "Verify model predictions: check confidence values in logs",
                            "Review market conditions",
                        ],
                        "success_rate": 0.70,
                    },
                    {
                        "id": "database_connection",
                        "pattern": r"(psycopg2|connection.*database|PostgreSQL|MySQL)",
                        "category": "Database",
                        "severity": "HIGH",
                        "solutions": [
                            "Check database connection string",
                            "Verify database is running",
                            "Check network connectivity to database",
                            "Review database credentials",
                        ],
                        "success_rate": 0.82,
                    },
                    {
                        "id": "pandas_error",
                        "pattern": r"(KeyError.*DataFrame|AttributeError.*pandas|ValueError.*DataFrame)",
                        "category": "Data Processing",
                        "severity": "MEDIUM",
                        "solutions": [
                            "Check DataFrame column names",
                            "Verify data preprocessing pipeline",
                            "Add error handling for missing columns",
                            "Check data types consistency",
                        ],
                        "success_rate": 0.76,
                    },
                    {
                        "id": "timezone_error",
                        "pattern": r"(timezone|tzinfo|UTC|pytz|Cannot compare.*offset)",
                        "category": "Datetime",
                        "severity": "MEDIUM",
                        "solutions": [
                            "Ensure all timestamps are timezone-aware",
                            "Use pd.to_datetime with utc=True",
                            "Standardize to UTC across the system",
                            "Check timezone settings in config",
                        ],
                        "success_rate": 0.85,
                    },
                ],
                "metadata": {
                    "version": "1.0.0",
                    "last_updated": datetime.now().isoformat(),
                    "total_patterns": 10,
                },
            }

    def fetch_gcp_logs(self, hours: int = 24) -> List[Dict]:
        """GCP Cloud Runのエラーログを取得"""
        errors = []
        try:
            # 時間範囲を指定
            since = datetime.now() - timedelta(hours=hours)
            timestamp = since.strftime("%Y-%m-%dT%H:%M:%S")

            # GCPログを取得
            cmd = [
                "gcloud",
                "logging",
                "read",
                f'resource.type="cloud_run_revision" AND severity>=ERROR AND timestamp>="{timestamp}"',
                "--limit=100",
                "--format=json",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and result.stdout:
                logs = json.loads(result.stdout)
                for log in logs:
                    errors.append(
                        {
                            "timestamp": log.get("timestamp", ""),
                            "severity": log.get("severity", "ERROR"),
                            "message": log.get("textPayload", log.get("jsonPayload", {})),
                            "resource": log.get("resource", {}),
                        }
                    )
                logger.info(f"Fetched {len(errors)} error logs from GCP")
            else:
                logger.warning("No error logs found or failed to fetch")

        except subprocess.TimeoutExpired:
            logger.error("GCP log fetch timed out")
        except Exception as e:
            logger.error(f"Failed to fetch GCP logs: {e}")

        return errors

    def fetch_local_logs(self, log_dir: str = "logs") -> List[Dict]:
        """ローカルログファイルからエラーを抽出"""
        errors = []
        log_path = Path(log_dir)

        if not log_path.exists():
            return errors

        # ログファイルを検索
        for log_file in log_path.glob("**/*.log"):
            try:
                with open(log_file) as f:
                    for line in f:
                        if any(
                            level in line.upper()
                            for level in ["ERROR", "CRITICAL", "EXCEPTION"]
                        ):
                            errors.append(
                                {
                                    "timestamp": datetime.now().isoformat(),
                                    "severity": "ERROR",
                                    "message": line.strip(),
                                    "source": str(log_file),
                                }
                            )
            except Exception as e:
                logger.warning(f"Failed to read {log_file}: {e}")

        logger.info(f"Found {len(errors)} errors in local logs")
        return errors

    def analyze_error_patterns(self, errors: List[Dict]) -> Dict:
        """エラーパターンを分析"""
        pattern_matches = defaultdict(list)
        unmatched_errors = []

        for error in errors:
            message = str(error.get("message", ""))
            matched = False

            # 既知のパターンとマッチング
            for pattern_def in self.error_patterns["patterns"]:
                if re.search(pattern_def["pattern"], message, re.IGNORECASE):
                    pattern_matches[pattern_def["id"]].append(error)
                    matched = True
                    break

            if not matched:
                unmatched_errors.append(error)

        # 統計情報を計算
        statistics = {
            "total_errors": len(errors),
            "matched_errors": sum(len(matches) for matches in pattern_matches.values()),
            "unmatched_errors": len(unmatched_errors),
            "unique_patterns": len(pattern_matches),
            "top_patterns": Counter(
                {pid: len(matches) for pid, matches in pattern_matches.items()}
            ).most_common(5),
        }

        return {
            "pattern_matches": dict(pattern_matches),
            "unmatched_errors": unmatched_errors,
            "statistics": statistics,
        }

    def generate_suggestions(self, pattern_matches: Dict) -> List[Dict]:
        """エラーパターンに基づいて修復提案を生成"""
        suggestions = []

        for pattern_id, errors in pattern_matches.items():
            # パターン定義を取得
            pattern_def = next(
                (p for p in self.error_patterns["patterns"] if p["id"] == pattern_id),
                None,
            )

            if pattern_def:
                suggestion = {
                    "pattern_id": pattern_id,
                    "category": pattern_def["category"],
                    "severity": pattern_def["severity"],
                    "error_count": len(errors),
                    "solutions": pattern_def["solutions"],
                    "success_rate": pattern_def["success_rate"],
                    "priority": self._calculate_priority(
                        pattern_def["severity"], len(errors)
                    ),
                }
                suggestions.append(suggestion)

        # 優先度でソート
        suggestions.sort(key=lambda x: x["priority"], reverse=True)
        return suggestions

    def _calculate_priority(self, severity: str, count: int) -> int:
        """優先度を計算"""
        severity_scores = {"CRITICAL": 100, "HIGH": 75, "MEDIUM": 50, "LOW": 25}
        base_score = severity_scores.get(severity, 0)
        # エラー数に応じてスコアを調整
        return base_score + min(count * 5, 50)

    def learn_from_resolution(
        self, pattern_id: str, solution_index: int, success: bool
    ):
        """解決結果から学習"""
        # パターンを見つける
        for pattern in self.error_patterns["patterns"]:
            if pattern["id"] == pattern_id:
                # 成功率を更新（簡単な移動平均）
                old_rate = pattern["success_rate"]
                new_rate = 1.0 if success else 0.0
                pattern["success_rate"] = old_rate * 0.9 + new_rate * 0.1

                # データベースを保存
                self.save_solutions_db()
                logger.info(
                    f"Updated success rate for {pattern_id}: {pattern['success_rate']:.2f}"
                )
                break

    def save_solutions_db(self):
        """解決策データベースを保存"""
        self.solutions_db_path.parent.mkdir(exist_ok=True, parents=True)
        self.error_patterns["metadata"]["last_updated"] = datetime.now().isoformat()

        with open(self.solutions_db_path, "w") as f:
            json.dump(self.error_patterns, f, indent=2)

    def generate_report(self, analysis: Dict, suggestions: List[Dict]) -> Path:
        """分析レポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = self.report_dir / f"error_analysis_{timestamp}.html"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Error Analysis Report - {timestamp}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #d32f2f; color: white; padding: 25px; border-radius: 8px; }}
        .section {{ background-color: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .suggestion {{ padding: 15px; margin: 10px 0; border-left: 4px solid; background-color: #f9f9f9; border-radius: 4px; }}
        .CRITICAL {{ border-color: #d32f2f; background-color: #ffebee; }}
        .HIGH {{ border-color: #f57c00; background-color: #fff3e0; }}
        .MEDIUM {{ border-color: #fbc02d; background-color: #fffde7; }}
        .LOW {{ border-color: #388e3c; background-color: #e8f5e9; }}
        .solution {{ padding: 8px; margin: 5px 0; background-color: #e3f2fd; border-radius: 3px; font-family: monospace; }}
        .metric {{ display: inline-block; padding: 10px 20px; margin: 10px; background-color: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #34495e; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Error Analysis & Recovery Suggestions</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="section">
        <h2>📊 Error Statistics</h2>
        <div>
            <span class="metric">Total Errors: {analysis['statistics']['total_errors']}</span>
            <span class="metric">Matched: {analysis['statistics']['matched_errors']}</span>
            <span class="metric">Unmatched: {analysis['statistics']['unmatched_errors']}</span>
            <span class="metric">Unique Patterns: {analysis['statistics']['unique_patterns']}</span>
        </div>
    </div>

    <div class="section">
        <h2>🏆 Top Error Patterns</h2>
        <table>
            <tr>
                <th>Pattern</th>
                <th>Count</th>
                <th>Category</th>
            </tr>
"""

        # トップエラーパターンを表示
        for pattern_id, count in analysis["statistics"].get("top_patterns", []):
            pattern_def = next(
                (p for p in self.error_patterns["patterns"] if p["id"] == pattern_id),
                {},
            )
            html_content += f"""
            <tr>
                <td>{pattern_id}</td>
                <td>{count}</td>
                <td>{pattern_def.get('category', 'Unknown')}</td>
            </tr>
"""

        html_content += """
        </table>
    </div>

    <div class="section">
        <h2>💡 Recovery Suggestions</h2>
"""

        # 修復提案を表示
        for suggestion in suggestions[:10]:  # 上位10件
            html_content += f"""
        <div class="suggestion {suggestion['severity']}">
            <h3>{suggestion['category']} - {suggestion['pattern_id']}</h3>
            <p>Severity: <strong>{suggestion['severity']}</strong> |
               Occurrences: <strong>{suggestion['error_count']}</strong> |
               Success Rate: <strong>{suggestion['success_rate']*100:.0f}%</strong></p>
            <h4>Recommended Solutions:</h4>
"""
            for solution in suggestion["solutions"]:
                html_content += f'            <div class="solution">{solution}</div>\n'

            html_content += "        </div>\n"

        html_content += """
    </div>

    <div class="section">
        <h2>🔧 Quick Actions</h2>
        <div class="solution">
            # Run comprehensive validation<br>
            bash scripts/validate_all.sh<br><br>

            # Check recent logs<br>
            gcloud logging read "severity>=ERROR" --limit=10<br><br>

            # Restart service<br>
            gcloud run services update crypto-bot-service-prod --region=asia-northeast1
        </div>
    </div>
</body>
</html>
"""

        with open(html_path, "w") as f:
            f.write(html_content)

        logger.info(f"Report saved: {html_path}")
        return html_path

    def run_analysis(
        self, source: str = "both", hours: int = 24
    ) -> Tuple[Dict, List[Dict]]:
        """エラー分析を実行"""
        logger.info("=" * 50)
        logger.info("🔍 Starting Error Analysis")
        logger.info("=" * 50)

        # エラーログを収集
        errors = []
        if source in ["gcp", "both"]:
            errors.extend(self.fetch_gcp_logs(hours))
        if source in ["local", "both"]:
            errors.extend(self.fetch_local_logs())

        if not errors:
            logger.warning("No errors found to analyze")
            return {}, []

        # パターン分析
        analysis = self.analyze_error_patterns(errors)

        # 修復提案生成
        suggestions = self.generate_suggestions(analysis["pattern_matches"])

        # レポート生成
        report_path = self.generate_report(analysis, suggestions)

        # 結果をログ
        logger.info("=" * 50)
        logger.info("📊 Analysis Complete")
        logger.info(f"Total Errors: {analysis['statistics']['total_errors']}")
        logger.info(f"Patterns Found: {analysis['statistics']['unique_patterns']}")
        logger.info(f"Top Suggestions: {len(suggestions)}")
        logger.info(f"Report: {report_path}")
        logger.info("=" * 50)

        return analysis, suggestions


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze error logs and suggest fixes")
    parser.add_argument(
        "--source",
        choices=["gcp", "local", "both"],
        default="both",
        help="Error log source",
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="Hours of logs to analyze"
    )
    parser.add_argument(
        "--update-db",
        action="store_true",
        help="Update solutions database with new patterns",
    )

    args = parser.parse_args()

    # エラー分析実行
    analyzer = ErrorAnalyzer()
    analysis, suggestions = analyzer.run_analysis(args.source, args.hours)

    # 最優先の提案を表示
    if suggestions:
        top_suggestion = suggestions[0]
        print("\n🎯 Top Priority Fix:")
        print(f"Pattern: {top_suggestion['pattern_id']}")
        print(f"Category: {top_suggestion['category']}")
        print("Solutions:")
        for i, solution in enumerate(top_suggestion["solutions"][:3], 1):
            print(f"  {i}. {solution}")


if __name__ == "__main__":
    main()
