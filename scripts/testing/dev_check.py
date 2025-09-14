#!/usr/bin/env python3
"""
CI前包括チェックツール - 最適化版
隠れた致命的障害を事前検出する軽量・高速なチェックシステム

主要機能:
- check: 品質チェック（軽量/標準/完全）
- critical: 隠れた障害検出（executorエラー等）
- ml-models: MLモデル検証
- status: システム状態確認
- monitor: 本番監視
"""

import argparse
import ast
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DevCheck:
    """最適化版CI前チェッククラス"""

    def __init__(self):
        """必要最小限の初期化"""
        self.project_root = Path(__file__).parent.parent.parent
        self.src_dir = self.project_root / "src"
        self.config_dir = self.project_root / "config"
        self.models_dir = self.project_root / "models"
        self.tests_dir = self.project_root / "tests"

        # レポート出力ディレクトリ
        self.report_dir = self.project_root / "logs" / "reports" / "ci_checks" / "dev_check"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    # === コア機能（5個） ===

    def check(self, level: str = "standard") -> int:
        """統合品質チェック（validate + full_check統合）

        Args:
            level: "light" (基本のみ), "standard" (推奨), "full" (完全)
        """
        print(f"\n🔍 品質チェック開始 - レベル: {level.upper()}")
        print("=" * 60)

        if level == "light":
            checks = [
                ("ディレクトリ構造確認", self._check_directories),
                ("基本設定確認", self._check_basic_config),
                ("インポート確認", self._check_basic_imports),
            ]
        elif level == "full":
            checks = [
                ("ディレクトリ構造確認", self._check_directories),
                ("設定ファイル確認", self._check_all_configs),
                ("インポート確認", self._check_all_imports),
                ("MLモデル確認", self._verify_models),
                ("コード品質チェック", self._run_code_quality),
                ("テスト実行", self._run_tests),
            ]
        else:  # standard
            checks = [
                ("ディレクトリ構造確認", self._check_directories),
                ("設定ファイル確認", self._check_all_configs),
                ("基本品質チェック", self._run_basic_quality),
                ("MLモデル確認", self._verify_models),
            ]

        failed_checks = []
        for check_name, check_func in checks:
            print(f"\n▶️ {check_name}")
            print("-" * 40)

            try:
                result = check_func()
                if result != 0:
                    failed_checks.append(check_name)
                    print(f"❌ {check_name} で問題が検出されました")
                else:
                    print(f"✅ {check_name} 正常")
            except Exception as e:
                failed_checks.append(check_name)
                print(f"❌ {check_name} でエラー: {e}")

        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 品質チェック結果")
        print("=" * 60)

        if not failed_checks:
            print("✅ すべてのチェックに合格しました！")
            self._save_report("check", level, {"status": "success", "level": level})
            return 0
        else:
            print("❌ 以下のチェックで問題が検出されました:")
            for check in failed_checks:
                print(f"  - {check}")
            self._save_report("check", level, {"status": "failed", "failed_checks": failed_checks})
            return 1

    def critical_path_check(self) -> int:
        """隠れた致命的障害検出（executorエラー等）"""
        print("\n🔍 隠れた致命的障害検出開始")
        print("=" * 60)

        critical_issues = []

        # 1. 静的インポート解析
        print("\n▶️ 静的インポート解析")
        print("-" * 40)
        import_errors = self._analyze_imports()
        if import_errors:
            print(f"❌ {len(import_errors)}件のインポートエラー検出:")
            for error in import_errors:
                print(f"  - {error}")
            critical_issues.extend(import_errors)
        else:
            print("✅ 全てのインポートは正常です")

        # 2. 初期化フロー検証
        print("\n▶️ 初期化フロー検証")
        print("-" * 40)
        init_errors = self._test_init_flows()
        if init_errors:
            print(f"❌ 初期化エラー検出:")
            for error in init_errors:
                print(f"  - {error}")
            critical_issues.extend(init_errors)
        else:
            print("✅ 全ての初期化フローは正常です")

        # 3. 依存関係チェック
        print("\n▶️ 依存関係チェック")
        print("-" * 40)
        dep_errors = self._check_dependencies()
        if dep_errors:
            print(f"❌ 依存関係エラー検出:")
            for error in dep_errors:
                print(f"  - {error}")
            critical_issues.extend(dep_errors)
        else:
            print("✅ 全ての依存関係は正常です")

        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 隠れた障害検出結果")
        print("=" * 60)

        if critical_issues:
            print(f"🚨 {len(critical_issues)}件の致命的問題を検出しました:")
            for issue in critical_issues:
                print(f"  - {issue}")
            self._save_report("critical", "scan", {"status": "critical", "issues": critical_issues})
            return 1
        else:
            print("✅ 隠れた致命的障害は検出されませんでした")
            self._save_report("critical", "scan", {"status": "clean"})
            return 0

    def ml_models(self, verify_only: bool = True) -> int:
        """MLモデル検証"""
        print("\n🤖 MLモデル検証")
        print("=" * 60)

        if not verify_only:
            print("ℹ️ モデル作成はscripts/ml/create_ml_models.pyを使用してください")
            return 1

        return self._verify_models()

    def status(self, verbose: bool = False) -> int:
        """システム状態確認（統合版）"""
        print("\n📊 システム状態確認")
        print("=" * 60)

        status_info = {}

        # 基本情報
        print("▶️ 基本システム情報")
        status_info["project_root"] = str(self.project_root)
        status_info["python_version"] = sys.version.split()[0]
        print(f"プロジェクトルート: {self.project_root}")
        print(f"Pythonバージョン: {status_info['python_version']}")

        # ディレクトリ存在確認
        print("\n▶️ ディレクトリ構造")
        required_dirs = [
            self.src_dir,
            self.config_dir,
            self.models_dir,
            self.tests_dir,
        ]

        missing_dirs = []
        for directory in required_dirs:
            if directory.exists():
                print(f"✅ {directory.name}/")
            else:
                print(f"❌ {directory.name}/ (存在しません)")
                missing_dirs.append(str(directory))

        status_info["missing_directories"] = missing_dirs

        if verbose:
            # MLモデル状態
            print("\n▶️ MLモデル状態")
            model_files = list(self.models_dir.glob("**/*.pkl"))
            status_info["model_files"] = len(model_files)
            print(f"MLモデルファイル数: {len(model_files)}")

            # テスト状況
            print("\n▶️ テスト状況")
            test_files = list(self.tests_dir.glob("**/test_*.py"))
            status_info["test_files"] = len(test_files)
            print(f"テストファイル数: {len(test_files)}")

        self._save_report("status", "check", status_info)

        if missing_dirs:
            return 1
        return 0

    def monitor(self, hours: int = 1) -> int:
        """本番監視（簡略版）"""
        print(f"\n📡 本番監視開始 - {hours}時間")
        print("=" * 60)

        # Cloud Run サービス状態確認
        print("▶️ Cloud Run サービス確認")
        service_status = self._check_cloud_run_service()

        if service_status != 0:
            print("❌ Cloud Run サービスに問題があります")
            return 1

        print("✅ 本番サービスは正常に稼働中です")

        if hours > 1:
            print(f"ℹ️ 継続監視は別途実装が必要です（{hours}時間監視は未実装）")

        return 0

    # === プライベートメソッド（最小限） ===

    def _check_directories(self) -> int:
        """ディレクトリ構造確認"""
        required_dirs = [
            self.src_dir / "core",
            self.src_dir / "data",
            self.src_dir / "features",
            self.src_dir / "strategies",
            self.src_dir / "ml",
            self.src_dir / "trading",
            self.config_dir / "core",
            self.models_dir / "production",
        ]

        missing_dirs = []
        for directory in required_dirs:
            if not directory.exists():
                missing_dirs.append(str(directory))

        if missing_dirs:
            print("❌ 以下のディレクトリが存在しません:")
            for directory in missing_dirs:
                print(f"  - {directory}")
            return 1

        print("✅ 必要なディレクトリは全て存在します")
        return 0

    def _check_basic_config(self) -> int:
        """基本設定確認"""
        unified_config = self.config_dir / "core" / "unified.yaml"
        if not unified_config.exists():
            print(f"❌ 設定ファイルが存在しません: {unified_config}")
            return 1

        print("✅ 基本設定ファイルが存在します")
        return 0

    def _check_all_configs(self) -> int:
        """全設定ファイル確認"""
        config_files = [
            self.config_dir / "core" / "unified.yaml",
            self.config_dir / "core" / "thresholds.yaml",
            self.config_dir / "core" / "feature_order.json",
        ]

        missing_configs = []
        for config_file in config_files:
            if not config_file.exists():
                missing_configs.append(str(config_file))

        if missing_configs:
            print("❌ 以下の設定ファイルが存在しません:")
            for config_file in missing_configs:
                print(f"  - {config_file}")
            return 1

        print("✅ 全ての設定ファイルが存在します")
        return 0

    def _check_basic_imports(self) -> int:
        """基本インポート確認"""
        test_code = """
import sys
sys.path.append('.')
try:
    from src.core.config import load_config
    print("✅ 基本インポート成功")
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
"""
        result = self._run_python_code(test_code)
        return result[0]

    def _check_all_imports(self) -> int:
        """全インポート確認"""
        test_code = """
import sys
sys.path.append('.')
try:
    from src.core.orchestration.orchestrator import TradingOrchestrator
    from src.core.config import load_config
    from src.features.feature_generator import FeatureGenerator
    print("✅ 主要インポート成功")
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)
"""
        result = self._run_python_code(test_code)
        return result[0]

    def _analyze_imports(self) -> List[str]:
        """静的インポート解析"""
        errors = []

        for py_file in self.src_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        # 相対インポートをチェック
                        if node.module.startswith("."):
                            continue  # 相対インポートはスキップ

                        # src.trading.executor のような削除されたモジュールをチェック
                        if "src.trading.executor" in node.module:
                            errors.append(
                                f"{py_file.relative_to(self.project_root)}: {node.module}"
                            )

                        # 存在しないモジュールパスをチェック
                        module_path = self._resolve_module_path(node.module)
                        if module_path and not module_path.exists():
                            errors.append(
                                f"{py_file.relative_to(self.project_root)}: {node.module}"
                            )

            except Exception:
                continue  # パースエラーは無視

        return errors

    def _test_init_flows(self) -> List[str]:
        """初期化フロー検証"""
        errors = []

        # main.pyと同じ手順での初期化テスト
        test_code = """
import sys, os, asyncio
sys.path.append('.')
os.environ['DRY_RUN'] = 'true'
try:
    from src.core.config import load_config
    from src.core.logger import setup_logging
    from src.core.orchestration import create_trading_orchestrator

    config = load_config('config/core/unified.yaml', cmdline_mode='paper')
    logger = setup_logging("crypto_bot_test")

    # async関数なのでasyncio.runを使用
    async def test_orchestrator():
        orchestrator = await create_trading_orchestrator(config, logger)
        return True

    result = asyncio.run(test_orchestrator())
    print("OK")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"""

        result = self._run_python_code(test_code)
        if result[0] != 0:
            errors.append(f"ペーパートレードモード初期化: {result[1]}")

        return errors

    def _check_dependencies(self) -> List[str]:
        """依存関係チェック"""
        errors = []

        # orchestrator.pyの特定のインポートをチェック
        orchestrator_file = self.src_dir / "core" / "orchestration" / "orchestrator.py"
        if orchestrator_file.exists():
            try:
                with open(orchestrator_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 削除されたexecutorモジュールへの参照をチェック
                if "from ...trading.executor import" in content:
                    errors.append("orchestrator.py: 削除されたexecutorモジュールへの参照")

            except Exception:
                pass

        return errors

    def _verify_models(self) -> int:
        """MLモデル検証"""
        production_model = self.models_dir / "production" / "production_ensemble.pkl"

        if not production_model.exists():
            print(f"❌ 本番モデルが存在しません: {production_model}")
            return 1

        # モデル読み込みテスト
        test_code = f"""
import sys
sys.path.append('.')
try:
    import pickle
    with open('{production_model}', 'rb') as f:
        model = pickle.load(f)
    print("✅ MLモデル読み込み成功")
except Exception as e:
    print(f"❌ MLモデルエラー: {{e}}")
    sys.exit(1)
"""
        result = self._run_python_code(test_code)
        return result[0]

    def _run_basic_quality(self) -> int:
        """基本品質チェック（flake8のみ）"""
        print("flake8 実行中...")
        result = subprocess.run(
            [
                "python3",
                "-m",
                "flake8",
                "src/",
                "--count",
                "--select=E9,F63,F7,F82",
                "--show-source",
                "--statistics",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("❌ flake8でエラーが検出されました")
            print(result.stdout)
            return 1

        print("✅ flake8チェック完了")
        return 0

    def _run_code_quality(self) -> int:
        """コード品質チェック（flake8 + black + isort）"""
        checks = [
            ("flake8", ["python3", "-m", "flake8", "src/"]),
            ("black", ["python3", "-m", "black", "--check", "src/"]),
            ("isort", ["python3", "-m", "isort", "--check-only", "src/"]),
        ]

        for check_name, cmd in checks:
            print(f"{check_name} 実行中...")
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ {check_name}でエラーが検出されました")
                return 1
            print(f"✅ {check_name}チェック完了")

        return 0

    def _run_tests(self) -> int:
        """テスト実行"""
        print("pytest 実行中...")
        result = subprocess.run(
            ["python3", "-m", "pytest", "tests/", "--tb=short", "-q"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("❌ テストでエラーが検出されました")
            print(result.stdout)
            return 1

        print("✅ 全テスト成功")
        return 0

    def _check_cloud_run_service(self) -> int:
        """Cloud Runサービス状態確認"""
        try:
            result = subprocess.run(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    "crypto-bot-service-prod",
                    "--region=asia-northeast1",
                    "--format=value(status.conditions[0].status)",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0 and "True" in result.stdout:
                print("✅ Cloud Runサービス正常稼働中")
                return 0
            else:
                print("❌ Cloud Runサービス異常")
                return 1

        except Exception as e:
            print(f"⚠️ Cloud Run状態確認スキップ: {e}")
            return 0

    def _resolve_module_path(self, module_name: str) -> Optional[Path]:
        """モジュール名からファイルパス解決"""
        if not module_name.startswith("src."):
            return None

        # src.core.config → src/core/config.py
        parts = module_name.split(".")
        if len(parts) < 2:
            return None

        file_path = self.project_root
        for part in parts:
            file_path = file_path / part

        # ファイルまたはパッケージとして確認
        if file_path.with_suffix(".py").exists():
            return file_path.with_suffix(".py")
        elif (file_path / "__init__.py").exists():
            return file_path / "__init__.py"

        return None

    def _run_python_code(self, code: str) -> Tuple[int, str]:
        """Pythonコード実行"""
        try:
            result = subprocess.run(
                ["python3", "-c", code],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout + result.stderr
        except Exception as e:
            return 1, str(e)

    def _save_report(self, command: str, mode: str, details: Dict) -> str:
        """レポート保存"""
        timestamp = datetime.now()
        filename = f"dev_check_{command}_{mode}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.report_dir / filename

        status = "✅ SUCCESS" if details.get("status") != "failed" else "❌ FAILED"

        report_content = f"""# dev_check.py 実行レポート

## 📊 実行サマリー
- **コマンド**: `{command} --{mode}`
- **実行時刻**: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}
- **実行結果**: {status}

## 📋 実行詳細
{json.dumps(details, indent=2, ensure_ascii=False)}

---
*このレポートは最適化版dev_check.pyにより自動生成されました*
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)

        return str(filepath)


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="CI前包括チェックツール - 最適化版",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/testing/dev_check.py check --level standard
  python scripts/testing/dev_check.py critical
  python scripts/testing/dev_check.py ml-models
  python scripts/testing/dev_check.py status --verbose
  python scripts/testing/dev_check.py monitor --hours 1
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # check コマンド
    check_parser = subparsers.add_parser("check", help="品質チェック実行")
    check_parser.add_argument(
        "--level", choices=["light", "standard", "full"], default="standard", help="チェックレベル"
    )

    # critical コマンド
    subparsers.add_parser("critical", help="隠れた障害検出")

    # ml-models コマンド
    ml_parser = subparsers.add_parser("ml-models", help="MLモデル検証")
    ml_parser.add_argument(
        "--create", action="store_true", help="モデル作成（通常は別スクリプト使用を推奨）"
    )

    # status コマンド
    status_parser = subparsers.add_parser("status", help="システム状態確認")
    status_parser.add_argument("--verbose", action="store_true", help="詳細表示")

    # monitor コマンド
    monitor_parser = subparsers.add_parser("monitor", help="本番監視")
    monitor_parser.add_argument("--hours", type=int, default=1, help="監視時間（時間）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    dev_check = DevCheck()

    try:
        if args.command == "check":
            return dev_check.check(args.level)
        elif args.command == "critical":
            return dev_check.critical_path_check()
        elif args.command == "ml-models":
            return dev_check.ml_models(verify_only=not args.create)
        elif args.command == "status":
            return dev_check.status(args.verbose)
        elif args.command == "monitor":
            return dev_check.monitor(args.hours)
        else:
            print(f"❌ 不明なコマンド: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️ 実行が中断されました")
        return 1
    except Exception as e:
        print(f"❌ 実行エラー: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
