#!/usr/bin/env python
"""
未来データリーク検出システム

Phase 2-3: ChatGPT提案採用
特徴量計算やバックテストで未来のデータを参照していないか検証
デプロイ前に潜在的バグを発見し、実運用での失敗を防止
"""

import ast
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FutureLeakDetector:
    """未来データリーク検出クラス"""

    def __init__(self, report_dir: str = "logs/leak_detection"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True, parents=True)

        # 検出パターン定義
        self.suspicious_patterns = {
            # 危険なパターン
            "future_indexing": [
                r"iloc\[i\s*\+",  # iloc[i + n] は未来参照の可能性
                r"iloc\[.*:\s*i\s*\+",  # iloc[:i+n] は未来を含む
                r"shift\(-\d+\)",  # shift(-n) は未来へのシフト
                r"rolling\(.*center=True",  # center=Trueは前後のデータを使用
            ],
            # 要確認パターン
            "needs_review": [
                r"iloc\[i:",  # iloc[i:] は未来全体を含む可能性
                r"\.tail\(",  # tail()は最新データ（未来の可能性）
                r"\.last\(",  # last()も同様
                r"future",  # "future"という変数名は疑わしい
                r"forward",  # "forward"も要確認
            ],
            # 安全なパターン（ホワイトリスト）
            "safe_patterns": [
                r"iloc\[max\(0,\s*i\s*-",  # iloc[max(0, i - n)] は過去参照
                r"shift\([1-9]",  # shift(n) where n > 0 は過去参照
                r"rolling\(\d+\)(?!.*center=True)",  # rolling without center
                r"iloc\[:i\]",  # iloc[:i] は現在までのデータ
            ],
        }

        self.issues_found = []
        self.safe_operations = []

    def analyze_feature_code(self, file_path: str) -> List[Dict]:
        """特徴量計算コードを分析"""
        issues = []
        file_path = Path(file_path)

        if not file_path.exists():
            logger.warning(f"File not found: {file_path}")
            return issues

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # 各行をチェック
            for line_num, line in enumerate(lines, 1):
                # コメント行はスキップ
                if line.strip().startswith("#"):
                    continue

                # 危険なパターンチェック
                for pattern_type, patterns in self.suspicious_patterns.items():
                    if pattern_type == "safe_patterns":
                        continue

                    for pattern in patterns:
                        if re.search(pattern, line):
                            # 安全なパターンに該当するか確認
                            is_safe = False
                            for safe_pattern in self.suspicious_patterns[
                                "safe_patterns"
                            ]:
                                if re.search(safe_pattern, line):
                                    is_safe = True
                                    break

                            if not is_safe:
                                severity = (
                                    "HIGH"
                                    if pattern_type == "future_indexing"
                                    else "MEDIUM"
                                )
                                issues.append(
                                    {
                                        "file": str(file_path),
                                        "line": line_num,
                                        "code": line.strip(),
                                        "pattern": pattern,
                                        "type": pattern_type,
                                        "severity": severity,
                                        "message": f"Potential future data leak: {pattern}",
                                    }
                                )

            logger.info(f"Analyzed {file_path}: {len(issues)} issues found")

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

        return issues

    def validate_dataframe_operations(
        self, df: pd.DataFrame, operations: List[str]
    ) -> Dict:
        """DataFrameの操作を実行して未来データリークを検証"""
        validation_results = {
            "safe": [],
            "unsafe": [],
            "errors": [],
        }

        # テスト用のインデックスを設定
        test_index = len(df) // 2  # 中間点でテスト

        for operation in operations:
            try:
                # 操作を安全に評価
                if "rolling" in operation:
                    # rolling操作の検証
                    window_match = re.search(r"rolling\((\d+)", operation)
                    if window_match:
                        window_size = int(window_match.group(1))
                        if "center=True" in operation:
                            validation_results["unsafe"].append(
                                {
                                    "operation": operation,
                                    "reason": "center=True uses future data",
                                }
                            )
                        else:
                            validation_results["safe"].append(
                                {"operation": operation, "reason": "Backward looking only"}
                            )

                elif "shift" in operation:
                    # shift操作の検証
                    shift_match = re.search(r"shift\(([-\d]+)\)", operation)
                    if shift_match:
                        shift_value = int(shift_match.group(1))
                        if shift_value < 0:
                            validation_results["unsafe"].append(
                                {
                                    "operation": operation,
                                    "reason": f"shift({shift_value}) references future",
                                }
                            )
                        else:
                            validation_results["safe"].append(
                                {
                                    "operation": operation,
                                    "reason": f"shift({shift_value}) references past",
                                }
                            )

                elif "iloc" in operation:
                    # iloc操作の検証
                    if re.search(r"iloc\[i\s*\+", operation):
                        validation_results["unsafe"].append(
                            {
                                "operation": operation,
                                "reason": "iloc[i+n] may reference future",
                            }
                        )
                    elif re.search(r"iloc\[:i\]", operation):
                        validation_results["safe"].append(
                            {
                                "operation": operation,
                                "reason": "iloc[:i] only uses past data",
                            }
                        )

            except Exception as e:
                validation_results["errors"].append(
                    {"operation": operation, "error": str(e)}
                )

        return validation_results

    def check_backtest_data_split(
        self, train_data: pd.DataFrame, test_data: pd.DataFrame
    ) -> Dict:
        """バックテストのデータ分割を検証"""
        issues = []

        # タイムスタンプがある場合の検証
        if "timestamp" in train_data.columns and "timestamp" in test_data.columns:
            train_max = pd.to_datetime(train_data["timestamp"]).max()
            test_min = pd.to_datetime(test_data["timestamp"]).min()

            if train_max >= test_min:
                issues.append(
                    {
                        "type": "DATA_OVERLAP",
                        "severity": "CRITICAL",
                        "message": f"Train data overlaps with test data: train_max={train_max}, test_min={test_min}",
                    }
                )

        # インデックスベースの検証
        if hasattr(train_data.index, "max") and hasattr(test_data.index, "min"):
            if train_data.index.max() >= test_data.index.min():
                issues.append(
                    {
                        "type": "INDEX_OVERLAP",
                        "severity": "HIGH",
                        "message": "Train indices overlap with test indices",
                    }
                )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "train_shape": train_data.shape,
            "test_shape": test_data.shape,
        }

    def validate_feature_pipeline(
        self, feature_function, sample_data: pd.DataFrame
    ) -> Dict:
        """特徴量パイプライン全体を検証"""
        validation_report = {
            "timestamp": datetime.now().isoformat(),
            "function_name": feature_function.__name__ if feature_function else "unknown",
            "data_shape": sample_data.shape,
            "checks": [],
        }

        # 1. 入力データの時系列順序確認
        if "timestamp" in sample_data.columns:
            timestamps = pd.to_datetime(sample_data["timestamp"])
            is_sorted = timestamps.is_monotonic_increasing
            validation_report["checks"].append(
                {
                    "check": "timestamp_order",
                    "passed": is_sorted,
                    "message": "Data is chronologically sorted"
                    if is_sorted
                    else "Data is NOT chronologically sorted",
                }
            )

        # 2. 特徴量生成をステップごとに実行
        try:
            # データの半分で特徴量生成
            half_data = sample_data.iloc[: len(sample_data) // 2].copy()
            features_half = feature_function(half_data)

            # 全データで特徴量生成
            features_full = feature_function(sample_data.copy())

            # 3. 一貫性チェック
            # 前半のデータで生成した特徴量が、全データで生成した特徴量の前半と一致するか
            common_cols = set(features_half.columns) & set(features_full.columns)
            
            inconsistent_features = []
            for col in common_cols:
                if col in ["timestamp", "date", "index"]:
                    continue
                    
                half_values = features_half[col].dropna()
                full_values = features_full[col].iloc[: len(features_half)].dropna()
                
                if len(half_values) > 0 and len(full_values) > 0:
                    # 値の比較（浮動小数点誤差を考慮）
                    if not np.allclose(
                        half_values.values[:min(len(half_values), len(full_values))],
                        full_values.values[:min(len(half_values), len(full_values))],
                        rtol=1e-5,
                        equal_nan=True
                    ):
                        inconsistent_features.append(col)

            validation_report["checks"].append(
                {
                    "check": "feature_consistency",
                    "passed": len(inconsistent_features) == 0,
                    "message": f"Features are consistent"
                    if len(inconsistent_features) == 0
                    else f"Inconsistent features found: {inconsistent_features}",
                    "details": {
                        "total_features": len(common_cols),
                        "inconsistent_count": len(inconsistent_features),
                    },
                }
            )

        except Exception as e:
            validation_report["checks"].append(
                {
                    "check": "feature_generation",
                    "passed": False,
                    "message": f"Error during feature generation: {str(e)}",
                }
            )

        # 4. 結果の評価
        all_passed = all(check["passed"] for check in validation_report["checks"])
        validation_report["overall_status"] = "PASS" if all_passed else "FAIL"

        return validation_report

    def scan_project(self, project_root: str) -> Dict:
        """プロジェクト全体をスキャン"""
        project_root = Path(project_root)
        all_issues = []

        # スキャン対象ディレクトリ
        scan_dirs = ["crypto_bot/ml", "crypto_bot/backtest", "crypto_bot/strategy"]

        for scan_dir in scan_dirs:
            dir_path = project_root / scan_dir
            if not dir_path.exists():
                continue

            # Pythonファイルを検索
            for py_file in dir_path.rglob("*.py"):
                issues = self.analyze_feature_code(py_file)
                all_issues.extend(issues)

        # 重要度でソート
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 4))

        return {
            "scan_time": datetime.now().isoformat(),
            "total_files_scanned": len(list(project_root.rglob("*.py"))),
            "total_issues": len(all_issues),
            "issues_by_severity": self._count_by_severity(all_issues),
            "issues": all_issues[:50],  # 最初の50件のみ
        }

    def _count_by_severity(self, issues: List[Dict]) -> Dict:
        """重要度別にカウント"""
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for issue in issues:
            severity = issue.get("severity", "LOW")
            counts[severity] = counts.get(severity, 0) + 1
        return counts

    def generate_report(self, scan_results: Dict) -> str:
        """HTMLレポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = self.report_dir / f"leak_detection_{timestamp}.html"

        # 全体のステータス判定
        total_issues = scan_results["total_issues"]
        critical_count = scan_results["issues_by_severity"]["CRITICAL"]
        high_count = scan_results["issues_by_severity"]["HIGH"]

        if critical_count > 0:
            status_color = "red"
            status_text = "CRITICAL ISSUES FOUND"
        elif high_count > 0:
            status_color = "orange"
            status_text = "HIGH PRIORITY ISSUES"
        elif total_issues > 0:
            status_color = "yellow"
            status_text = "MEDIUM PRIORITY ISSUES"
        else:
            status_color = "green"
            status_text = "NO ISSUES DETECTED"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Future Data Leak Detection Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #2c3e50; color: white; padding: 25px; border-radius: 8px; }}
        .status {{ font-size: 36px; color: {status_color}; font-weight: bold; margin: 20px 0; }}
        .section {{ background-color: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .issue {{ padding: 15px; margin: 10px 0; border-left: 4px solid; background-color: #f9f9f9; }}
        .CRITICAL {{ border-color: #e74c3c; background-color: #ffe6e6; }}
        .HIGH {{ border-color: #e67e22; background-color: #fff4e6; }}
        .MEDIUM {{ border-color: #f39c12; background-color: #fffae6; }}
        .LOW {{ border-color: #3498db; background-color: #e6f3ff; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #34495e; color: white; }}
        .code {{ font-family: 'Courier New', monospace; background-color: #2c3e50; color: #ecf0f1; padding: 3px 6px; border-radius: 3px; }}
        .recommendation {{ background-color: #d4edda; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .metric {{ display: inline-block; padding: 10px 20px; margin: 10px; background-color: white; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Future Data Leak Detection Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <div class="status">{status_text}</div>
    </div>
    
    <div class="section">
        <h2>📊 Scan Summary</h2>
        <div>
            <span class="metric">📁 Files Scanned: {scan_results['total_files_scanned']}</span>
            <span class="metric">⚠️ Total Issues: {total_issues}</span>
            <span class="metric">🔴 Critical: {critical_count}</span>
            <span class="metric">🟠 High: {high_count}</span>
            <span class="metric">🟡 Medium: {scan_results['issues_by_severity']['MEDIUM']}</span>
        </div>
    </div>
    
    <div class="section">
        <h2>⚠️ Issues Found</h2>
"""

        if scan_results["issues"]:
            for issue in scan_results["issues"][:20]:  # 最初の20件を表示
                html_content += f"""
        <div class="issue {issue.get('severity', 'LOW')}">
            <strong>{issue.get('severity', 'LOW')}</strong>: {issue.get('message', '')}
            <br>📁 File: {issue.get('file', 'unknown')}
            <br>📍 Line {issue.get('line', '?')}: <span class="code">{issue.get('code', '')[:100]}</span>
        </div>
"""
        else:
            html_content += """
        <div class="recommendation">
            ✅ No future data leak issues detected! Your code appears to be safe from look-ahead bias.
        </div>
"""

        html_content += """
    </div>
    
    <div class="section">
        <h2>💡 Recommendations</h2>
        <div class="recommendation">
            <h3>Best Practices to Prevent Future Data Leaks:</h3>
            <ul>
                <li>✅ Always use <code>shift(1)</code> or higher for past data, never negative values</li>
                <li>✅ Use <code>rolling(window)</code> without <code>center=True</code></li>
                <li>✅ When using <code>iloc</code>, ensure indices reference past data only</li>
                <li>✅ Split train/test data chronologically with no overlap</li>
                <li>✅ Validate feature consistency: features computed on partial data should match when computed on full data</li>
                <li>✅ Add timestamp checks in production to ensure no future data access</li>
            </ul>
        </div>
    </div>
    
    <div class="section">
        <h2>📈 Common Patterns Detected</h2>
        <table>
            <tr>
                <th>Pattern</th>
                <th>Risk Level</th>
                <th>Example</th>
                <th>Safe Alternative</th>
            </tr>
            <tr>
                <td>Future Shift</td>
                <td style="color: red;">HIGH</td>
                <td><code>df.shift(-1)</code></td>
                <td><code>df.shift(1)</code></td>
            </tr>
            <tr>
                <td>Center Rolling</td>
                <td style="color: orange;">MEDIUM</td>
                <td><code>df.rolling(5, center=True)</code></td>
                <td><code>df.rolling(5)</code></td>
            </tr>
            <tr>
                <td>Future Indexing</td>
                <td style="color: red;">HIGH</td>
                <td><code>df.iloc[i:i+10]</code></td>
                <td><code>df.iloc[max(0,i-10):i]</code></td>
            </tr>
        </table>
    </div>
</body>
</html>
"""

        with open(html_path, "w") as f:
            f.write(html_content)

        logger.info(f"HTML report saved: {html_path}")
        return str(html_path)

    def save_json_report(self, scan_results: Dict) -> str:
        """JSON形式でレポートを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"leak_detection_{timestamp}.json"

        with open(json_path, "w") as f:
            json.dump(scan_results, f, indent=2, default=str)

        logger.info(f"JSON report saved: {json_path}")
        return str(json_path)


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect future data leaks in ML pipeline"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root directory to scan",
    )
    parser.add_argument(
        "--report-dir",
        default="logs/leak_detection",
        help="Directory for detection reports",
    )
    parser.add_argument(
        "--file",
        help="Specific file to analyze",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML report",
    )

    args = parser.parse_args()

    # 検出器初期化
    detector = FutureLeakDetector(args.report_dir)

    if args.file:
        # 特定ファイルの分析
        issues = detector.analyze_feature_code(args.file)
        
        if issues:
            logger.warning(f"⚠️ Found {len(issues)} potential issues in {args.file}")
            for issue in issues:
                logger.warning(
                    f"  Line {issue['line']} [{issue['severity']}]: {issue['message']}"
                )
            sys.exit(1)
        else:
            logger.info(f"✅ No issues found in {args.file}")
            sys.exit(0)
    else:
        # プロジェクト全体のスキャン
        logger.info(f"🔍 Scanning project: {args.project_root}")
        scan_results = detector.scan_project(args.project_root)

        # レポート保存
        json_path = detector.save_json_report(scan_results)
        
        if args.html:
            html_path = detector.generate_report(scan_results)
            logger.info(f"📊 HTML report: {html_path}")

        # サマリー出力
        logger.info("=" * 50)
        logger.info("📊 Scan Complete")
        logger.info(f"📁 Files scanned: {scan_results['total_files_scanned']}")
        logger.info(f"⚠️ Total issues: {scan_results['total_issues']}")
        
        for severity, count in scan_results["issues_by_severity"].items():
            if count > 0:
                logger.info(f"  {severity}: {count}")

        logger.info("=" * 50)

        # 終了コード
        if scan_results["issues_by_severity"]["CRITICAL"] > 0:
            sys.exit(2)  # Critical issues
        elif scan_results["issues_by_severity"]["HIGH"] > 0:
            sys.exit(1)  # High priority issues
        else:
            sys.exit(0)  # Success or only medium/low issues


if __name__ == "__main__":
    main()