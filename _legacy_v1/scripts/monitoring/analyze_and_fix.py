#!/usr/bin/env python
"""
エラー分析・修復統合スクリプト

Phase 3: ChatGPT提案採用
エラーログの収集、分析、修復提案を一括実行
インタラクティブな修復実行サポート
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# エラー分析器をインポート
sys.path.insert(0, str(Path(__file__).parent / "utilities"))
from error_analyzer import ErrorAnalyzer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ErrorFixer:
    """エラー修復実行クラス"""

    def __init__(self):
        self.analyzer = ErrorAnalyzer()
        self.fix_history = []

    def execute_fix(self, solution: str) -> bool:
        """修復コマンドを実行"""
        # コマンドラインとして実行可能な解決策を検出
        if solution.startswith(("python ", "pip ", "gcloud ", "bash ", "git ")):
            logger.info(f"Executing: {solution}")
            try:
                # 安全のため、危険なコマンドをブロック
                dangerous_commands = ["rm -rf", "sudo rm", "format", "delete"]
                if any(cmd in solution.lower() for cmd in dangerous_commands):
                    logger.warning(f"⚠️ Blocked dangerous command: {solution}")
                    return False

                # コマンド実行
                result = subprocess.run(
                    solution, shell=True, capture_output=True, text=True, timeout=60
                )

                if result.returncode == 0:
                    logger.info(f"✅ Successfully executed: {solution}")
                    return True
                else:
                    logger.error(f"❌ Failed to execute: {solution}")
                    logger.error(f"Error: {result.stderr}")
                    return False

            except subprocess.TimeoutExpired:
                logger.error(f"⏱️ Command timed out: {solution}")
                return False
            except Exception as e:
                logger.error(f"❌ Error executing command: {e}")
                return False
        else:
            # 手動実行が必要な解決策
            logger.info(f"📝 Manual action required: {solution}")
            return None

    def interactive_fix(self, suggestions: List[Dict]):
        """インタラクティブな修復プロセス"""
        if not suggestions:
            logger.info("No suggestions available")
            return

        print("\n" + "=" * 60)
        print("🔧 Interactive Error Fix Mode")
        print("=" * 60)

        for i, suggestion in enumerate(suggestions[:5], 1):
            print(f"\n{i}. {suggestion['category']} - {suggestion['pattern_id']}")
            print(f"   Severity: {suggestion['severity']}")
            print(f"   Occurrences: {suggestion['error_count']}")
            print(f"   Success Rate: {suggestion['success_rate']*100:.0f}%")

        # ユーザー選択
        try:
            choice = input("\nSelect pattern to fix (1-5, or 0 to skip): ")
            choice = int(choice)

            if choice == 0:
                return
            if 1 <= choice <= min(5, len(suggestions)):
                selected = suggestions[choice - 1]
                self.apply_fixes(selected)
            else:
                print("Invalid choice")

        except (ValueError, KeyboardInterrupt):
            print("\nSkipping interactive fix")

    def apply_fixes(self, suggestion: Dict):
        """選択された修復案を適用"""
        print(f"\n🎯 Applying fixes for: {suggestion['pattern_id']}")
        print("Solutions:")

        for i, solution in enumerate(suggestion["solutions"], 1):
            print(f"\n{i}. {solution}")

            # 実行可能なコマンドか判定
            if solution.startswith(("python ", "pip ", "gcloud ", "bash ", "git ")):
                response = input("Execute this command? (y/n): ")
                if response.lower() == "y":
                    success = self.execute_fix(solution)
                    if success:
                        # 成功を記録
                        self.analyzer.learn_from_resolution(
                            suggestion["pattern_id"], i - 1, True
                        )
                        self.fix_history.append(
                            {
                                "pattern": suggestion["pattern_id"],
                                "solution": solution,
                                "success": True,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                        print("✅ Fix applied successfully")
                        break
                    elif success is False:
                        # 失敗を記録
                        self.analyzer.learn_from_resolution(
                            suggestion["pattern_id"], i - 1, False
                        )
                        print("❌ Fix failed")
            else:
                print("ℹ️ Manual action required")

    def auto_fix_critical(self, suggestions: List[Dict]) -> int:
        """CRITICALエラーを自動修復"""
        fixed_count = 0
        critical_suggestions = [s for s in suggestions if s["severity"] == "CRITICAL"]

        if not critical_suggestions:
            logger.info("No critical errors to fix")
            return 0

        logger.info(f"Found {len(critical_suggestions)} critical error patterns")

        for suggestion in critical_suggestions:
            logger.info(f"Attempting to fix: {suggestion['pattern_id']}")

            # 最も成功率の高い解決策を試す
            for solution in suggestion["solutions"]:
                if solution.startswith(("python scripts/create_", "pip install")):
                    # 安全なコマンドのみ自動実行
                    success = self.execute_fix(solution)
                    if success:
                        fixed_count += 1
                        self.analyzer.learn_from_resolution(
                            suggestion["pattern_id"], 0, True
                        )
                        break

        return fixed_count

    def generate_fix_script(self, suggestions: List[Dict]) -> Path:
        """修復スクリプトを生成"""
        script_path = Path("fix_errors.sh")

        with open(script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("# Auto-generated error fix script\n")
            f.write(f"# Generated: {datetime.now()}\n\n")
            f.write("set -e\n\n")

            for suggestion in suggestions[:10]:
                f.write(f"# Fix for: {suggestion['pattern_id']}\n")
                f.write(f"# Severity: {suggestion['severity']}\n")

                for solution in suggestion["solutions"]:
                    if solution.startswith(("python ", "pip ", "gcloud ", "git ")):
                        f.write(f"echo 'Executing: {solution}'\n")
                        f.write(f"{solution} || echo 'Failed: {solution}'\n")
                        f.write("\n")

            f.write("\necho 'Fix script completed'\n")

        script_path.chmod(0o755)
        logger.info(f"Fix script generated: {script_path}")
        return script_path


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="Analyze errors and apply fixes automatically"
    )
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
        "--auto-fix",
        action="store_true",
        help="Automatically fix critical errors",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive fix mode",
    )
    parser.add_argument(
        "--generate-script",
        action="store_true",
        help="Generate fix script",
    )

    args = parser.parse_args()

    # エラー分析実行
    fixer = ErrorFixer()
    analysis, suggestions = fixer.analyzer.run_analysis(args.source, args.hours)

    if not suggestions:
        logger.info("No errors found or no suggestions available")
        return

    # 自動修復
    if args.auto_fix:
        fixed = fixer.auto_fix_critical(suggestions)
        logger.info(f"Auto-fixed {fixed} critical issues")

    # インタラクティブモード
    if args.interactive:
        fixer.interactive_fix(suggestions)

    # 修復スクリプト生成
    if args.generate_script:
        script_path = fixer.generate_fix_script(suggestions)
        print(f"\n📝 Fix script generated: {script_path}")
        print("Review and run: bash fix_errors.sh")

    # 修復履歴を保存
    if fixer.fix_history:
        history_path = Path("logs/fix_history.json")
        history_path.parent.mkdir(exist_ok=True, parents=True)

        existing_history = []
        if history_path.exists():
            with open(history_path) as f:
                existing_history = json.load(f)

        existing_history.extend(fixer.fix_history)

        with open(history_path, "w") as f:
            json.dump(existing_history, f, indent=2)

        logger.info(f"Fix history saved: {history_path}")


if __name__ == "__main__":
    main()
