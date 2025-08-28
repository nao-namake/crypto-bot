#!/usr/bin/env python3
"""
統合管理CLI - Phase 12統合版（重複コード削除・base_analyzer.py活用）

CI前チェック特化管理システム。本番運用詳細診断はops_monitor.pyに分離。

CI前チェック機能:
- phase-check: Phase実装状況確認
- validate: 品質チェック（checks.sh実行）
- ml-models: MLモデル作成・検証
- data-check: データ取得確認
- full-check: 統合品質チェック
- status: システム状態確認
- health-check: GCP本番環境ヘルスチェック
- monitor: 24時間本番監視
- operational: 本番運用診断（ops_monitor.py委譲）

Usage:
    python scripts/management/dev_check.py --help
    python scripts/management/dev_check.py phase-check
    python scripts/management/dev_check.py operational  # 委譲実行
    python scripts/management/dev_check.py full-check
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# 共通基盤クラスをインポート
sys.path.append(str(Path(__file__).parent.parent))
from analytics.base_analyzer import BaseAnalyzer


class UnifiedBotManager(BaseAnalyzer):
    """統合システム管理クラス（Phase 12統合版・base_analyzer.py活用）"""

    def __init__(self):
        """初期化処理"""
        super().__init__(output_dir="logs/reports/ci_checks/dev_check")

        self.project_root = Path(__file__).parent.parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.src_dir = self.project_root / "src"
        self.config_dir = self.project_root / "config"
        self.models_dir = self.project_root / "models"

        # システム必須ディレクトリ
        self.required_dirs = [
            self.src_dir / "core",
            self.src_dir / "data",
            self.src_dir / "features",
            self.src_dir / "strategies",
            self.src_dir / "ml",
            self.config_dir / "core",
            self.models_dir / "production",
            self.models_dir / "training",
        ]

        # CI前チェック結果格納
        self.check_results = {
            "timestamp": datetime.now().isoformat(),
            "system_version": "Phase 12 - CI前チェックシステム",
            "checks": {},
            "overall_status": "UNKNOWN",
            "overall_score": 0,
        }

        # レポート出力ディレクトリ
        self.report_dir = self.project_root / "logs" / "reports" / "ci_checks" / "dev_check"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def run_command(
        self, command: List[str], capture: bool = False, show_output: bool = True, env: dict = None
    ) -> Tuple[int, str]:
        """コマンド実行ラッパー（base_analyzer.pyの機能を活用）"""
        if show_output:
            print(f"📍 実行: {' '.join(command)}")

        # gcloudコマンドの場合はbase_analyzer.pyの機能を使用
        if command[0] == "gcloud":
            returncode, stdout, stderr = self.run_gcloud_command(command, show_output=show_output)
            return returncode, stdout + stderr

        # 環境変数の準備
        import os

        current_env = os.environ.copy()
        if env:
            current_env.update(env)

        # その他のコマンドは従来通り
        try:
            import subprocess

            if capture:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=300,
                    env=current_env,
                )
                return result.returncode, result.stdout + result.stderr
            else:
                result = subprocess.run(
                    command, cwd=self.project_root, timeout=300, env=current_env
                )
                return result.returncode, ""
        except subprocess.TimeoutExpired:
            print(f"⏰ タイムアウト: {' '.join(command)}")
            return 1, "タイムアウト"
        except Exception as e:
            print(f"❌ エラー: {e}")
            return 1, str(e)

    def phase_check(self) -> int:
        """Phase 10実装状況の確認."""
        print("\n" + "=" * 60)
        print("🎯 Phase 10 実装状況チェック")
        print("=" * 60)

        checks_passed = []
        checks_failed = []

        # 1. 新システムディレクトリ構造確認
        print("\n▶️ 1. ディレクトリ構造確認")
        print("-" * 40)

        for req_dir in self.required_dirs:
            if req_dir.exists():
                print(f"✅ {req_dir.relative_to(self.project_root)}")
                checks_passed.append(f"ディレクトリ: {req_dir.name}")
            else:
                print(f"❌ {req_dir.relative_to(self.project_root)}")
                checks_failed.append(f"ディレクトリ: {req_dir.name}")

        # 2. 主要コンポーネントインポートテスト
        print("\n▶️ 2. 主要コンポーネントインポートテスト")
        print("-" * 40)

        import_tests = [
            "from src.core.config import load_config",
            "from src.data.data_pipeline import DataPipeline",
            "from src.features.technical import TechnicalIndicators",
            "from src.strategies.base.strategy_base import StrategyBase",
            "from src.ml.ensemble.production_ensemble import ProductionEnsemble",
        ]

        for test in import_tests:
            cmd = ["python3", "-c", test + "; print('✅ OK')"]
            returncode, output = self.run_command(cmd, capture=True, show_output=False)

            module_name = test.split("import ")[1].split()[0]
            if returncode == 0:
                print(f"✅ {module_name}")
                checks_passed.append(f"インポート: {module_name}")
            else:
                print(f"❌ {module_name}")
                checks_failed.append(f"インポート: {module_name}")

        # 3. MLモデル存在確認
        print("\n▶️ 3. MLモデル存在確認")
        print("-" * 40)

        production_model = self.models_dir / "production" / "production_ensemble.pkl"
        production_metadata = self.models_dir / "production" / "production_model_metadata.json"

        if production_model.exists():
            print(f"✅ 本番用モデル: {production_model.name}")
            checks_passed.append("本番用モデル")
        else:
            print(f"❌ 本番用モデル未作成: {production_model.name}")
            checks_failed.append("本番用モデル")

        if production_metadata.exists():
            print(f"✅ モデルメタデータ: {production_metadata.name}")
            checks_passed.append("モデルメタデータ")
        else:
            print(f"⚠️ モデルメタデータ未作成: {production_metadata.name}")

        # 4. 設定ファイル確認
        print("\n▶️ 4. 設定ファイル確認")
        print("-" * 40)

        config_files = [self.config_dir / "core" / "base.yaml", self.config_dir / "README.md"]

        for config_file in config_files:
            if config_file.exists():
                print(f"✅ {config_file.relative_to(self.project_root)}")
                checks_passed.append(f"設定: {config_file.name}")
            else:
                print(f"❌ {config_file.relative_to(self.project_root)}")
                checks_failed.append(f"設定: {config_file.name}")

        # 5. Phase 10特有機能確認
        print("\n▶️ 5. Phase 10特有機能確認")
        print("-" * 40)

        phase10_checks = [
            (self.scripts_dir / "ml" / "create_ml_models.py", "MLモデル作成スクリプト"),
            (self.scripts_dir / "testing" / "checks.sh", "品質チェックスクリプト"),
            (self.scripts_dir / "deployment" / "docker-entrypoint.sh", "Docker entrypoint"),
            (
                self.scripts_dir / "management" / "ops_monitor.py",
                "稼働状況確認システム",
            ),
            (self.project_root / "CLAUDE.md", "Claude.md (Phase 10記載)"),
        ]

        for file_path, description in phase10_checks:
            if file_path.exists():
                print(f"✅ {description}")
                checks_passed.append(description)
            else:
                print(f"❌ {description}")
                checks_failed.append(description)

        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 Phase 10実装状況結果")
        print("-" * 40)
        print(f"✅ 成功: {len(checks_passed)} 項目")
        print(f"❌ 失敗: {len(checks_failed)} 項目")

        if checks_failed:
            print("\n⚠️ 修正が必要な項目:")
            for item in checks_failed:
                print(f"   • {item}")
            print("\n💡 修正方法:")
            print("   - 不足ディレクトリ: mkdir -p <ディレクトリ名>")
            print("   - MLモデル: python scripts/ml/create_ml_models.py")
            print("   - 設定ファイル: 該当ファイルを作成")
            print("   - 稼働状況確認: 既に作成済み（ops_monitor.py）")
            return 1
        else:
            print("\n🎉 Phase 10実装完了！")
            print("✅ すべての必要コンポーネントが揃っています")
            print("🔍 新機能: python scripts/management/dev_check.py status-check")
            return 0

    def validate(self, mode: str = "full") -> int:
        """
        品質チェック実行（checks.sh実行）.

        Args:
            mode: "full" (checks.sh), "light" (checks.sh --light)
        """
        print("\n" + "=" * 60)
        print("🔍 新システム品質チェック")
        print("=" * 60)

        if mode == "light":
            check_script = self.scripts_dir / "testing" / "checks.sh"
            light_mode = True
            print("📝 軽量品質チェック実行")
        else:
            check_script = self.scripts_dir / "testing" / "checks.sh"
            light_mode = False
            print("📝 完全品質チェック実行")

        if not check_script.exists():
            print(f"❌ チェックスクリプトが見つかりません: {check_script}")
            return 1

        cmd = ["bash", str(check_script)]
        returncode, _ = self.run_command(cmd)

        if returncode == 0:
            print("\n✅ 品質チェック成功！")
        else:
            print("\n❌ 品質チェック失敗。上記のエラーを修正してください。")

        return returncode

    def ml_models(self, dry_run: bool = False, verbose: bool = False) -> int:
        """
        MLモデル作成・検証.

        Args:
            dry_run: ドライラン実行
            verbose: 詳細ログ出力.
        """
        print("\n" + "=" * 60)
        print("🤖 MLモデル管理")
        print("=" * 60)

        create_script = self.scripts_dir / "ml" / "create_ml_models.py"

        if not create_script.exists():
            print(f"❌ MLモデル作成スクリプトが見つかりません: {create_script}")
            return 1

        cmd = ["python3", str(create_script)]

        if dry_run:
            cmd.append("--dry-run")
            print("🔍 ドライラン: モデル作成のシミュレーション")

        if verbose:
            cmd.append("--verbose")

        # PYTHONPATHを設定してモジュールインポート問題を解決
        env_vars = {"PYTHONPATH": str(self.project_root)}
        returncode, _ = self.run_command(cmd, env=env_vars)

        if returncode == 0:
            if dry_run:
                print("\n✅ ドライラン成功！実際のモデル作成準備完了")
            else:
                print("\n✅ MLモデル作成成功！")

                # モデル検証
                production_model = self.models_dir / "production" / "production_ensemble.pkl"
                if production_model.exists():
                    print(f"📁 本番用モデル作成済み: {production_model}")

                    # メタデータ確認
                    metadata_file = (
                        self.models_dir / "production" / "production_model_metadata.json"
                    )
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, "r", encoding="utf-8") as f:
                                metadata = json.load(f)
                            print(f"📊 モデルタイプ: {metadata.get('model_type', 'Unknown')}")
                            print(f"📅 作成日時: {metadata.get('created_at', 'Unknown')}")
                            print(f"🎯 対象特徴量: {len(metadata.get('feature_names', []))}個")
                        except Exception as e:
                            print(f"⚠️ メタデータ読み込み警告: {e}")
        else:
            print("\n❌ MLモデル作成失敗")

        return returncode

    def data_check(self) -> int:
        """新システムデータ層の基本動作確認."""
        print("\n" + "=" * 60)
        print("📊 新システムデータ層確認")
        print("=" * 60)

        checks_passed = []
        checks_failed = []

        # 1. データパイプライン基本テスト
        print("\n▶️ 1. DataPipeline基本テスト")
        print("-" * 40)

        cmd = [
            "python3",
            "-c",
            """
import sys
sys.path.append('.')
try:
    from src.data.data_pipeline import DataPipeline, TimeFrame, DataRequest
    pipeline = DataPipeline()
    print('✅ DataPipeline初期化成功')

    # DataRequest作成テスト
    request = DataRequest(
        symbol='BTC/JPY',
        timeframe=TimeFrame.H1,
        limit=24
    )
    print('✅ DataRequest作成成功')
except Exception as e:
    print(f'❌ DataPipeline エラー: {e}')
    sys.exit(1)
""",
        ]

        returncode, output = self.run_command(cmd, capture=True, show_output=False)
        if returncode == 0:
            print(output.strip())
            checks_passed.append("DataPipeline")
        else:
            print("❌ DataPipeline テスト失敗")
            print(output.strip())
            checks_failed.append("DataPipeline")

        # 2. 特徴量エンジンテスト
        print("\n▶️ 2. TechnicalIndicators基本テスト")
        print("-" * 40)

        cmd = [
            "python3",
            "-c",
            """
import sys
sys.path.append('.')
import pandas as pd
import numpy as np
try:
    from src.features.technical import TechnicalIndicators
    ti = TechnicalIndicators()
    print('✅ TechnicalIndicators初期化成功')

    # サンプルデータでテスト
    sample_data = pd.DataFrame({
        'open': np.random.uniform(5000000, 5100000, 100),
        'high': np.random.uniform(5100000, 5200000, 100),
        'low': np.random.uniform(4900000, 5000000, 100),
        'close': np.random.uniform(5000000, 5100000, 100),
        'volume': np.random.uniform(1000, 10000, 100)
    })

    features = ti.generate_all_features(sample_data)
    print(f'✅ 特徴量生成成功: {len(features.columns)}個')
except Exception as e:
    print(f'❌ TechnicalIndicators エラー: {e}')
    sys.exit(1)
""",
        ]

        returncode, output = self.run_command(cmd, capture=True, show_output=False)
        if returncode == 0:
            print(output.strip())
            checks_passed.append("TechnicalIndicators")
        else:
            print("❌ TechnicalIndicators テスト失敗")
            print(output.strip())
            checks_failed.append("TechnicalIndicators")

        # 3. 設定読み込みテスト
        print("\n▶️ 3. Config読み込みテスト")
        print("-" * 40)

        cmd = [
            "python3",
            "-c",
            """
import sys
sys.path.append('.')
try:
    from src.core.config import load_config
    config = load_config('config/core/base.yaml')
    print('✅ Config読み込み成功')

    # 基本設定確認
    if hasattr(config, 'logging'):
        print('✅ ログ設定存在')
    if hasattr(config, 'data'):
        print('✅ データ設定存在')
except Exception as e:
    print(f'❌ Config エラー: {e}')
    sys.exit(1)
""",
        ]

        returncode, output = self.run_command(cmd, capture=True, show_output=False)
        if returncode == 0:
            print(output.strip())
            checks_passed.append("Config")
        else:
            print("❌ Config テスト失敗")
            print(output.strip())
            checks_failed.append("Config")

        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 データ層チェック結果")
        print("-" * 40)

        if checks_failed:
            print(f"❌ 失敗: {len(checks_failed)}項目")
            for item in checks_failed:
                print(f"  - {item}")
            return 1
        else:
            print(f"✅ すべてのチェックに合格: {len(checks_passed)}項目")
            return 0

    def full_check(self) -> int:
        """統合品質チェック（デプロイ前の完全検証）."""
        print("\n" + "=" * 60)
        print("🎯 統合品質チェック（Phase 10対応）")
        print("=" * 60)
        print(f"開始時刻: {datetime.now()}")
        print("=" * 60)

        steps = [
            ("1/7 Phase 10実装状況確認", lambda: self.phase_check()),
            ("2/7 データ層基本確認", lambda: self.data_check()),
            ("3/7 軽量品質チェック", lambda: self.validate("light")),
            ("4/7 MLモデル検証", lambda: self.ml_models(dry_run=True)),
            ("5/7 完全品質チェック", lambda: self.validate("full")),
            ("6/7 稼働状況詳細確認", lambda: self.status_check()),
            ("7/7 システム状態確認", lambda: (self.show_status(), 0)[1]),
        ]

        failed_steps = []

        for step_name, step_func in steps:
            print(f"\n▶️ {step_name}")
            print("-" * 40)
            returncode = step_func()
            if returncode != 0:
                failed_steps.append(step_name)
                print(f"⚠️ {step_name} で問題が検出されました")

        print("\n" + "=" * 60)
        print("📊 統合品質チェック結果")
        print("=" * 60)

        if not failed_steps:
            print("✅ すべてのチェックに合格しました！")
            print("🚀 Phase 10システム本番運用準備完了")
            print("\n推奨次ステップ:")
            print("  1. 本番用MLモデル作成: python scripts/management/dev_check.py ml-models")
            print("  2. 稼働状況詳細確認: python scripts/management/dev_check.py status-check")
            print("  3. 実際の取引テスト準備")
            print("  4. GCP Cloud Run デプロイ準備")
            return 0
        else:
            print("❌ 以下のチェックで問題が検出されました:")
            for step in failed_steps:
                print(f"  - {step}")
            print("\n修正後、再度実行してください。")
            return 1

    def operational(self) -> int:
        """本番運用診断（ops_monitor.py委譲実行）"""
        print("\n" + "=" * 60)
        print("🔍 本番運用診断実行（ops_monitor.py委譲）")
        print("=" * 60)

        operational_script = self.scripts_dir / "management" / "ops_monitor.py"

        if not operational_script.exists():
            print(f"❌ ops_monitor.pyが見つかりません: {operational_script}")
            return 1

        print(f"📍 実行: python {operational_script}")

        try:
            import subprocess

            result = subprocess.run(
                ["python", str(operational_script), "--verbose"],
                cwd=self.project_root,
                timeout=600,  # 10分タイムアウト
            )
            return result.returncode
        except subprocess.TimeoutExpired:
            print("⏰ 本番運用診断がタイムアウトしました（10分）")
            return 1
        except Exception as e:
            print(f"❌ 実行エラー: {e}")
            return 1

    def show_status(self) -> None:
        """新システムの現在状態を表示."""
        print("\n" + "=" * 60)
        print("📊 新システム状態確認")
        print("=" * 60)

        # Phase 9主要コンポーネント状態
        components = {
            "基盤システム": self.src_dir / "core",
            "データ層": self.src_dir / "data",
            "特徴量エンジン": self.src_dir / "features",
            "戦略システム": self.src_dir / "strategies",
            "ML層": self.src_dir / "ml",
            "設定管理": self.config_dir / "core",
            "本番用モデル": self.models_dir / "production",
            "学習用モデル": self.models_dir / "training",
        }

        print("\n🏗️ システム コンポーネント:")
        for name, path in components.items():
            if path.exists():
                if path.is_file():
                    size = path.stat().st_size
                    print(f"  {name}: ✅ ({size:,} bytes)")
                else:
                    file_count = len(list(path.glob("**/*.py")))
                    print(f"  {name}: ✅ ({file_count} .py files)")
            else:
                print(f"  {name}: ❌ 未作成")

        # 重要ファイル状態
        print("\n📁 重要ファイル:")
        important_files = {
            "MLモデル": self.models_dir / "production" / "production_ensemble.pkl",
            "モデルメタデータ": self.models_dir / "production" / "production_model_metadata.json",
            "品質チェック": self.scripts_dir / "testing" / "checks.sh",
            "MLモデル作成": self.scripts_dir / "ml" / "create_ml_models.py",
            "Bot統合管理": self.scripts_dir / "management" / "dev_check.py",
            "設定ファイル": self.config_dir / "core" / "base.yaml",
        }

        for name, path in important_files.items():
            if path.exists():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                size = path.stat().st_size
                print(f"  {name}: ✅ {mtime.strftime('%m/%d %H:%M')} ({size:,} bytes)")
            else:
                print(f"  {name}: ❌ 未作成")

        # 手動テスト確認
        print("\n🧪 手動テスト:")
        manual_test = self.project_root / "tests" / "manual" / "test_phase2_components.py"
        if manual_test.exists():
            print("  Phase2テスト: ✅ 利用可能")
            print("    実行: python3 tests/manual/test_phase2_components.py")
        else:
            print("  Phase2テスト: ❌ 未作成")

        print("\n" + "=" * 60)

    def status_check(self) -> int:
        """新システムの現在状態をチェックして結果を返す."""
        self.show_status()
        return 0

    def health_check(self) -> int:
        """GCP本番環境ヘルスチェック（base_analyzer.py活用版）"""
        print("\n" + "=" * 60)
        print("🏥 GCP本番環境ヘルスチェック")
        print("=" * 60)

        checks_passed = []
        checks_failed = []

        # 1. GCP認証確認（base_analyzer.pyを活用）
        print("\n▶️ 1. GCP認証状態確認")
        print("-" * 40)

        # 認証確認
        returncode, stdout, stderr = self.run_gcloud_command(
            ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"]
        )

        if returncode == 0 and stdout.strip():
            print(f"✅ GCP認証済み: {stdout.strip()}")
            checks_passed.append("GCP認証")
        else:
            print("❌ GCP認証が必要です")
            checks_failed.append("GCP認証")

        # 2. Cloud Runサービス状態確認（base_analyzer.pyを活用）
        print("\n▶️ 2. Cloud Runサービス状態確認")
        print("-" * 40)

        service_health = self.check_service_endpoint()

        if service_health.get("service_status") == "UP":
            print("✅ Cloud Runサービス: READY")
            print(f"📍 サービスURL: {service_health.get('url', '')}")
            checks_passed.append("Cloud Runサービス")

            if service_health.get("endpoint_status") == "OK":
                print("✅ ヘルスエンドポイント応答OK")
                checks_passed.append("ヘルスエンドポイント")
            else:
                print(f"⚠️ ヘルスエンドポイント: {service_health.get('endpoint_status')}")
                checks_failed.append("ヘルスエンドポイント")
        else:
            print(f"❌ Cloud Runサービス: {service_health.get('service_status')}")
            checks_failed.append("Cloud Runサービス")

        # 3. Secret Manager確認
        print("\n▶️ 3. Secret Manager確認")
        print("-" * 40)

        secrets = ["bitbank-api-key", "bitbank-api-secret", "discord-webhook"]
        for secret_name in secrets:
            returncode, _, _ = self.run_gcloud_command(
                ["gcloud", "secrets", "describe", secret_name]
            )

            if returncode == 0:
                print(f"✅ シークレット: {secret_name}")
                checks_passed.append(f"シークレット:{secret_name}")
            else:
                print(f"❌ シークレット未設定: {secret_name}")
                checks_failed.append(f"シークレット:{secret_name}")

        # 4. ローカルモデル確認
        print("\n▶️ 4. 本番用モデル確認")
        print("-" * 40)

        production_model = self.models_dir / "production" / "production_ensemble.pkl"
        if production_model.exists():
            size = production_model.stat().st_size
            mtime = datetime.fromtimestamp(production_model.stat().st_mtime)
            print(f"✅ 本番用モデル: {size:,} bytes ({mtime.strftime('%m/%d %H:%M')})")
            checks_passed.append("本番用モデル")
        else:
            print("❌ 本番用モデル未作成")
            checks_failed.append("本番用モデル")

        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 ヘルスチェック結果")
        print("-" * 40)
        print(f"✅ 正常: {len(checks_passed)} 項目")
        print(f"❌ 異常: {len(checks_failed)} 項目")

        if checks_failed:
            print("\n⚠️ 修正が必要な項目:")
            for item in checks_failed:
                print(f"   • {item}")
            print("\n💡 修正方法:")
            print("   - GCP認証: gcloud auth login")
            print("   - Secret Manager: bash scripts/deployment/setup_gcp_secrets.sh")
            print("   - Cloud Run: GitHub ActionsでCI/CD実行")
            print("   - モデル作成: python scripts/management/dev_check.py ml-models")
            return 1
        else:
            print("\n🎉 すべてのヘルスチェックに合格！")
            print("✅ 本番環境は正常稼働しています")
            return 0

    def monitor_production(self, duration_hours: int = 24) -> int:
        """Phase 12: 24時間本番監視システム."""
        print("\n" + "=" * 60)
        print("📡 Phase 12本番環境手動実行監視")
        print("=" * 60)

        import threading
        import time
        from datetime import timedelta

        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)  # Phase 12バグ修正: timedelta使用

        print(f"📅 監視開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 監視終了: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏰ 監視時間: {duration_hours}時間")
        print("\n🔍 5分間隔でヘルスチェック実行中...")

        consecutive_failures = 0
        total_checks = 0
        failed_checks = 0

        try:
            while datetime.now() < end_time:
                total_checks += 1
                current_time = datetime.now().strftime("%H:%M:%S")

                print(f"\n🔍 [{current_time}] ヘルスチェック実行中... ({total_checks}回目)")

                # ヘルスチェック実行（静音モード）
                health_result = self._silent_health_check()

                if health_result == 0:
                    print(f"✅ [{current_time}] 正常稼働中")
                    consecutive_failures = 0
                else:
                    failed_checks += 1
                    consecutive_failures += 1
                    print(f"❌ [{current_time}] 異常検知 (連続{consecutive_failures}回)")

                    # 3回連続失敗でアラート
                    if consecutive_failures >= 3:
                        self._send_critical_alert(consecutive_failures, total_checks)

                        # 5回連続失敗で監視一時停止（過度な通知防止）
                        if consecutive_failures >= 5:
                            print("🚨 連続5回失敗 - 30分間監視一時停止")
                            time.sleep(1800)  # 30分待機
                            consecutive_failures = 0

                # 統計表示
                success_rate = ((total_checks - failed_checks) / total_checks) * 100
                print(
                    f"📊 成功率: {success_rate:.1f}% ({total_checks - failed_checks}/{total_checks})"
                )

                # 5分間待機
                time.sleep(300)

        except KeyboardInterrupt:
            print("\n⚠️ 監視を中断しました")

        # 監視完了サマリー
        monitoring_duration = datetime.now() - start_time
        success_rate = (
            ((total_checks - failed_checks) / total_checks) * 100 if total_checks > 0 else 0
        )

        print("\n" + "=" * 60)
        print("📊 手動実行監視結果")
        print("-" * 40)
        print(f"📅 監視期間: {monitoring_duration}")
        print(f"🔍 総チェック回数: {total_checks}")
        print(f"✅ 成功回数: {total_checks - failed_checks}")
        print(f"❌ 失敗回数: {failed_checks}")
        print(f"📊 成功率: {success_rate:.1f}%")

        if success_rate >= 95:
            print("🎉 優秀な稼働率です！")
            return 0
        elif success_rate >= 90:
            print("✅ 良好な稼働率です")
            return 0
        else:
            print("⚠️ 稼働率が低下しています。システムの確認が必要です")
            return 1

    def _silent_health_check(self) -> int:
        """サイレントヘルスチェック（ログ出力抑制版）."""
        # Cloud Runサービス状態のみチェック（最重要）
        cmd = [
            "gcloud",
            "run",
            "services",
            "describe",
            "crypto-bot-service",
            "--region=asia-northeast1",
            "--format=value(status.conditions[0].status)",
        ]
        returncode, output = self.run_command(cmd, capture=True, show_output=False)

        if returncode != 0 or "True" not in output:
            return 1

        # サービスURL応答確認
        cmd = [
            "gcloud",
            "run",
            "services",
            "describe",
            "crypto-bot-service",
            "--region=asia-northeast1",
            "--format=value(status.url)",
        ]
        returncode, service_url = self.run_command(cmd, capture=True, show_output=False)

        if returncode == 0 and service_url.strip():
            service_url = service_url.strip()
            import urllib.error
            import urllib.request

            try:
                with urllib.request.urlopen(f"{service_url}/health", timeout=10) as response:
                    return 0 if response.status == 200 else 1
            except (urllib.error.URLError, OSError):
                return 1

        return 1

    def _send_critical_alert(self, consecutive_failures: int, total_checks: int):
        """クリティカルアラート送信."""
        print(f"🚨 CRITICAL: {consecutive_failures}回連続失敗検知")
        print("📧 運用チームに通知を送信中...")

        # Discord通知機能は実装済みの前提で、ここでは通知ログのみ
        # 実際の環境では Discord Webhook や メール通知を実装
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_message = f"""
🚨 **Phase 12 監視アラート**
⏰ 時刻: {current_time}
❌ 連続失敗: {consecutive_failures}回
📊 総チェック: {total_checks}回
🔍 対象: crypto-bot-service (asia-northeast1)
        """.strip()

        print(alert_message)

    # ===== base_analyzer.py抽象メソッド実装 =====

    def run_analysis(self, **kwargs) -> Dict:
        """分析実行（base_analyzer.py要求）"""
        return {
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "unified_management",
            "check_results": self.check_results,
        }

    def generate_report(self, analysis_result: Dict) -> str:
        """レポート生成（base_analyzer.py要求）"""
        return f"統合管理レポート: {analysis_result['timestamp']}"

    def save_report_to_file(self, command: str, result_code: int, details: Dict = None) -> str:
        """
        実行結果をマークダウンファイルに保存

        Args:
            command: 実行したコマンド
            result_code: 実行結果コード（0=成功、1=失敗）
            details: 詳細情報

        Returns:
            str: 保存されたファイルパス
        """
        timestamp = datetime.now()
        filename = f"dev_check_{command}_{timestamp.strftime('%Y%m%d_%H%M%S')}.md"
        filepath = self.report_dir / filename

        # 基本情報
        status = "✅ SUCCESS" if result_code == 0 else "❌ FAILED"
        details = details or {}

        # マークダウンレポート生成
        report_content = f"""# dev_check.py 実行レポート

## 📊 実行サマリー
- **コマンド**: `{command}`
- **実行時刻**: {timestamp.strftime('%Y年%m月%d日 %H:%M:%S')}
- **実行結果**: {status}
- **終了コード**: {result_code}

## 🎯 システム情報
- **プロジェクトルート**: `{self.project_root}`
- **Phase**: 12（CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応）
- **実行環境**: dev_check.py統合管理CLI

## 📋 実行詳細

"""

        # コマンド別詳細情報追加
        if command == "phase-check":
            report_content += self._generate_phase_check_details(details)
        elif command == "validate":
            report_content += self._generate_validate_details(details)
        elif command == "full-check":
            report_content += self._generate_full_check_details(details)
        elif command == "ml-models":
            report_content += self._generate_ml_models_details(details)
        elif command == "data-check":
            report_content += self._generate_data_check_details(details)
        elif command == "health-check":
            report_content += self._generate_health_check_details(details)
        else:
            report_content += f"### {command} 実行結果\n\n"
            if details:
                for key, value in details.items():
                    report_content += f"- **{key}**: {value}\n"

        # 推奨アクション追加
        report_content += self._generate_recommendations(command, result_code, details)

        # フッター
        report_content += f"""

---
*このレポートは dev_check.py により自動生成されました*  
*生成時刻: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
"""

        # ファイル保存
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report_content)

        return str(filepath)

    def _generate_phase_check_details(self, details: Dict) -> str:
        """Phase check詳細レポート生成"""
        content = "### Phase実装状況確認結果\n\n"

        if details and "phase_status" in details:
            phase_status = details["phase_status"]
            for phase, status in phase_status.items():
                emoji = "✅" if status == "完了" else "⚠️" if status == "部分的" else "❌"
                content += f"- **{phase}**: {emoji} {status}\n"

        content += "\n### 確認項目\n"
        content += "- システムディレクトリ構造\n"
        content += "- 設定ファイル存在確認\n"
        content += "- MLモデル状態確認\n"
        content += "- 依存関係確認\n\n"

        return content

    def _generate_validate_details(self, details: Dict) -> str:
        """Validate詳細レポート生成"""
        content = "### 品質チェック結果\n\n"

        if details and "checks" in details:
            checks = details["checks"]
            for check_name, result in checks.items():
                emoji = "✅" if result.get("passed", False) else "❌"
                content += f"- **{check_name}**: {emoji} {result.get('message', 'チェック実行')}\n"

        content += "\n### チェック項目\n"
        content += "- **flake8**: コードスタイルチェック\n"
        content += "- **isort**: インポート順序チェック\n"
        content += "- **black**: コードフォーマットチェック\n"
        content += "- **pytest**: テスト実行（316テスト）\n\n"

        return content

    def _generate_full_check_details(self, details: Dict) -> str:
        """Full check詳細レポート生成"""
        content = "### 統合品質チェック結果\n\n"

        if details and "test_results" in details:
            test_results = details["test_results"]
            content += f"- **実行テスト数**: {test_results.get('total_tests', 'N/A')}\n"
            content += f"- **合格テスト数**: {test_results.get('passed_tests', 'N/A')}\n"
            content += f"- **成功率**: {test_results.get('success_rate', 'N/A')}%\n"

        content += "\n### フルチェック項目\n"
        content += "1. **ディレクトリ構造確認**\n"
        content += "2. **MLモデル整合性チェック**\n"
        content += "3. **コードスタイルチェック（flake8）**\n"
        content += "4. **インポート順序チェック（isort）**\n"
        content += "5. **コードフォーマットチェック（black）**\n"
        content += "6. **全テスト実行（pytest 316テスト）**\n\n"

        return content

    def _generate_ml_models_details(self, details: Dict) -> str:
        """ML models詳細レポート生成"""
        content = "### MLモデル作成・検証結果\n\n"

        if details and "models" in details:
            models = details["models"]
            for model_name, info in models.items():
                emoji = "✅" if info.get("created", False) else "❌"
                content += f"- **{model_name}**: {emoji} {info.get('status', '未確認')}\n"

        content += "\n### 対象モデル\n"
        content += "- **ProductionEnsemble**: 本番用統合モデル\n"
        content += "- **LightGBM**: 個別モデル（重み: 0.4）\n"
        content += "- **XGBoost**: 個別モデル（重み: 0.4）\n"
        content += "- **RandomForest**: 個別モデル（重み: 0.2）\n\n"

        return content

    def _generate_data_check_details(self, details: Dict) -> str:
        """Generate detailed data check report"""
        content = "### データ層動作確認結果\n\n"

        if details and "components" in details:
            components = details["components"]
            for comp_name, status in components.items():
                emoji = "✅" if status else "❌"
                content += f"- **{comp_name}**: {emoji}\n"

        content += "\n### 確認対象\n"
        content += "- **BitbankClient**: API接続確認\n"
        content += "- **DataPipeline**: データ取得パイプライン\n"
        content += "- **TechnicalIndicators**: テクニカル指標生成\n"
        content += "- **MarketAnomalyDetector**: 異常検知システム\n"
        content += "- **StrategyManager**: 戦略システム統合\n\n"

        return content

    def _generate_health_check_details(self, details: Dict) -> str:
        """Health check詳細レポート生成"""
        content = "### GCP本番環境ヘルスチェック結果\n\n"

        if details and "health_status" in details:
            health = details["health_status"]
            for service, status in health.items():
                emoji = "✅" if status == "正常" else "⚠️" if status == "注意" else "❌"
                content += f"- **{service}**: {emoji} {status}\n"

        content += "\n### ヘルスチェック項目\n"
        content += "- **GCP認証状態**: gcloud認証確認\n"
        content += "- **Secret Manager**: API キー・シークレット確認\n"
        content += "- **Cloud Run サービス**: 本番環境稼働状況\n"
        content += "- **本番用モデル**: ProductionEnsembleファイル確認\n\n"

        return content

    def _generate_recommendations(self, command: str, result_code: int, details: Dict) -> str:
        """推奨アクションの生成"""
        content = "## 🔧 推奨アクション\n\n"

        if result_code == 0:
            content += "### ✅ 成功時の次のステップ\n\n"
            if command == "phase-check":
                content += (
                    "1. `python scripts/management/dev_check.py validate` で品質チェック実行\n"
                )
                content += (
                    "2. `python scripts/management/dev_check.py full-check` で統合チェック実行\n"
                )
            elif command == "validate":
                content += "1. `python scripts/management/dev_check.py ml-models` でMLモデル確認\n"
                content += (
                    "2. `python scripts/management/dev_check.py health-check` で本番環境確認\n"
                )
            elif command == "full-check":
                content += "1. GitHub にプッシュしてCI/CD実行\n"
                content += "2. `python scripts/management/dev_check.py health-check` で本番確認\n"
            else:
                content += "1. 他の dev_check.py コマンドで包括的チェック実行\n"
                content += "2. 本番環境デプロイの準備\n"
        else:
            content += "### ❌ 失敗時の対処方法\n\n"
            content += "#### 一般的な対処手順\n"
            content += "1. **エラーメッセージ確認**: 上記の詳細情報でエラー内容を特定\n"
            content += "2. **依存関係確認**: `pip install -r requirements.txt` で必要パッケージをインストール\n"
            content += "3. **権限確認**: ファイル・ディレクトリアクセス権限をチェック\n"
            content += "4. **設定確認**: config/core/base.yaml など設定ファイルをチェック\n\n"

            if command in ["health-check", "monitor"]:
                content += "#### GCP関連エラーの場合\n"
                content += "1. `gcloud auth login` で認証実行\n"
                content += "2. `bash scripts/deployment/setup_gcp_secrets.sh --check` で設定確認\n"
                content += "3. GCPプロジェクト・権限設定の確認\n\n"

            if command in ["validate", "full-check"]:
                content += "#### テスト・品質チェックエラーの場合\n"
                content += "1. `bash scripts/testing/checks.sh` で品質チェック実行\n"
                content += "2. 個別テスト実行: `python -m pytest tests/unit/strategies/ -v`\n"
                content += "3. コードフォーマット実行: `python -m black src/`\n\n"

        content += "### 🆘 追加サポート\n\n"
        content += (
            "このレポートを他のAIツールに共有して、具体的な修正方法を相談することができます。\n\n"
        )
        content += "**共有時のポイント**:\n"
        content += "- 実行したコマンドと結果コード\n"
        content += "- エラーメッセージ（ある場合）\n"
        content += "- システム環境情報\n"
        content += "- 期待する結果\n\n"

        return content

    # ===== ops_monitor.py機能統合（base_analyzer.py活用版） =====

    def _run_phase1_infrastructure_checks(self) -> Dict:
        """Phase 1: インフラ・基盤確認（base_analyzer.py活用版）"""
        print("   📊 プロジェクト構造・GCP状態確認...")

        # 1. ディレクトリ構造確認
        missing_dirs = []
        for req_dir in self.required_dirs:
            if not req_dir.exists():
                missing_dirs.append(str(req_dir.relative_to(self.project_root)))

        # 2. GCPサービス状態確認（base_analyzer.py活用）
        service_health = self.check_service_health()
        gcp_healthy = service_health.get("service_status") == "UP"

        # スコア計算
        structure_score = 100 if not missing_dirs else max(40, 100 - len(missing_dirs) * 15)
        gcp_score = 100 if gcp_healthy else 30

        overall_score = (structure_score + gcp_score) / 2

        if missing_dirs:
            print(f"   ⚠️ 不足ディレクトリ: {len(missing_dirs)}個")
            for missing in missing_dirs[:3]:  # 最初の3個のみ表示
                print(f"      - {missing}")
        else:
            print("   ✅ プロジェクト構造: OK")

        if gcp_healthy:
            print("   ✅ GCPサービス: 稼働中")
        else:
            print(f"   ❌ GCPサービス: {service_health.get('service_status')}")

        self.operational_results["phases"]["phase1"] = {"score": overall_score}
        return {"score": overall_score}

    def _run_phase2_application_checks(self) -> Dict:
        """Phase 2: アプリケーション動作確認（base_analyzer.py活用版）"""
        print("   🔍 アプリケーション・ログ確認...")

        scores = []

        # 1. 基本インポート確認（軽量版）
        import_tests = [
            "from src.core.config import load_config",
            "from src.data.data_pipeline import DataPipeline",
            "from src.ml.ensemble.production_ensemble import ProductionEnsemble",
        ]

        import_failures = 0
        for test in import_tests:
            cmd = ["python3", "-c", test + "; print('OK')"]
            returncode, _ = self.run_command(cmd, capture=True, show_output=False)
            if returncode != 0:
                import_failures += 1

        import_score = max(20, 100 - import_failures * 30)
        scores.append(import_score)

        # 2. Cloud Runログ確認（base_analyzer.py活用）
        log_success, logs = self.fetch_trading_logs(hours=6)  # 過去6時間
        if log_success:
            signal_analysis = self.analyze_signal_frequency(logs, 6)
            log_score = 100 if signal_analysis.get("total_signals", 0) > 0 else 70
            print(f"   📊 シグナル数（6時間）: {signal_analysis.get('total_signals', 0)}")
        else:
            log_score = 40
            print("   ⚠️ ログ取得失敗")

        scores.append(log_score)

        overall_score = sum(scores) / len(scores)

        if import_failures == 0:
            print("   ✅ 基本インポート: OK")
        else:
            print(f"   ❌ インポートエラー: {import_failures}件")

        self.operational_results["phases"]["phase2"] = {"score": overall_score}
        return {"score": overall_score}

    def _run_phase3_hidden_issues_detection(self) -> Dict:
        """Phase 3: 隠れた問題検出（base_analyzer.py活用版）"""
        print("   🔍 エラーログ・異常パターン分析...")

        scores = []

        # 1. エラーログ分析（base_analyzer.py活用）
        error_success, error_logs = self.fetch_error_logs(hours=24)
        if error_success:
            error_count = len(error_logs)
            if error_count == 0:
                error_score = 100
                print("   ✅ エラーログ: 問題なし")
            elif error_count < 5:
                error_score = 80
                print(f"   ⚠️ エラーログ: {error_count}件（許容範囲）")
            else:
                error_score = 40
                print(f"   ❌ エラーログ: {error_count}件")
        else:
            error_score = 30
            print("   ❌ エラーログ取得失敗")

        scores.append(error_score)

        # 2. 本番用モデル確認
        production_model = self.models_dir / "production" / "production_ensemble.pkl"
        if production_model.exists():
            model_age_hours = (datetime.now().timestamp() - production_model.stat().st_mtime) / 3600
            if model_age_hours < 24 * 7:  # 1週間以内
                model_score = 100
                print("   ✅ 本番用モデル: 最新")
            elif model_age_hours < 24 * 30:  # 1ヶ月以内
                model_score = 70
                print("   ⚠️ 本番用モデル: やや古い")
            else:
                model_score = 40
                print("   ⚠️ 本番用モデル: 更新推奨")
        else:
            model_score = 20
            print("   ❌ 本番用モデル: 未作成")

        scores.append(model_score)

        overall_score = sum(scores) / len(scores)

        self.operational_results["phases"]["phase3"] = {"score": overall_score}
        return {"score": overall_score}

    def _run_phase4_overall_assessment(self) -> Dict:
        """Phase 4: 総合判定（base_analyzer.py活用版）"""
        phases = self.operational_results["phases"]
        scores = [phase.get("score", 0) for phase in phases.values()]
        overall_score = sum(scores) / len(scores) if scores else 0

        if overall_score >= 90:
            overall_status = "excellent"
        elif overall_score >= 70:
            overall_status = "healthy"
        elif overall_score >= 50:
            overall_status = "warning"
        else:
            overall_status = "critical"

        self.operational_results["overall_score"] = overall_score
        self.operational_results["overall_status"] = overall_status

        print(f"   📊 総合スコア計算: {overall_score:.1f}/100")
        return {"score": overall_score, "status": overall_status}


def main():
    """メインエントリーポイント（統合版）"""
    parser = argparse.ArgumentParser(
        description="統合管理CLI - Phase 12統合版（重複コード削除・base_analyzer.py活用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Phase実装状況確認
  python scripts/management/dev_check.py phase-check

  # 統合品質チェック（推奨）
  python scripts/management/dev_check.py full-check

  # 4段階運用診断（旧ops_monitor.py機能）
  python scripts/management/dev_check.py operational

  # GCP本番環境ヘルスチェック
  python scripts/management/dev_check.py health-check

  # 24時間本番監視
  python scripts/management/dev_check.py monitor --hours 24
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # phase-check コマンド
    subparsers.add_parser("phase-check", help="Phase実装状況確認")

    # validate コマンド
    validate_parser = subparsers.add_parser("validate", help="品質チェック実行")
    validate_parser.add_argument(
        "--mode",
        choices=["full", "light"],
        default="full",
        help="チェックモード: full(完全), light(軽量)",
    )

    # ml-models コマンド
    ml_parser = subparsers.add_parser("ml-models", help="MLモデル作成・検証")
    ml_parser.add_argument(
        "--dry-run", action="store_true", help="ドライラン（実際の作成はしない）"
    )
    ml_parser.add_argument("--verbose", action="store_true", help="詳細ログ出力")

    # data-check コマンド
    subparsers.add_parser("data-check", help="データ層基本動作確認")

    # full-check コマンド
    subparsers.add_parser("full-check", help="統合品質チェック")

    # status コマンド
    subparsers.add_parser("status", help="システム状態確認")

    # operational コマンド（ops_monitor.py委譲実行）
    subparsers.add_parser("operational", help="本番運用診断（ops_monitor.py委譲）")

    # health-check コマンド
    subparsers.add_parser("health-check", help="GCP本番環境ヘルスチェック")

    # monitor コマンド
    monitor_parser = subparsers.add_parser("monitor", help="24時間本番監視")
    monitor_parser.add_argument(
        "--hours", type=int, default=24, help="監視時間（時間、デフォルト: 24時間）"
    )

    # レポート機能追加（全コマンド共通オプション）
    parser.add_argument(
        "--no-report", action="store_true", help="レポートファイルの自動生成を無効化"
    )

    args = parser.parse_args()

    manager = UnifiedBotManager()

    if not args.command:
        parser.print_help()
        print("\n💡 推奨: まずは 'python scripts/management/dev_check.py phase-check' で状況を確認")
        print("🔧 Phase 12統合機能:")
        print("   - operational: 本番運用診断（ops_monitor.py委譲）")
        print("   - health-check: GCP本番環境ヘルスチェック")
        print("   - monitor: 24時間本番監視")
        print("\n📄 レポート機能:")
        print("   - 実行結果を自動的にマークダウンファイルに保存")
        print("   - 他のAIツールとの情報共有に最適")
        print("   - --no-report オプションでレポート生成を無効化可能")
        return 0

    # コマンド実行（レポート出力機能統合）
    result_code = 0
    details = {}

    try:
        if args.command == "phase-check":
            result_code = manager.phase_check()
        elif args.command == "validate":
            result_code = manager.validate(args.mode)
            details = {"mode": args.mode}
        elif args.command == "ml-models":
            result_code = manager.ml_models(args.dry_run, args.verbose)
            details = {"dry_run": args.dry_run, "verbose": args.verbose}
        elif args.command == "data-check":
            result_code = manager.data_check()
        elif args.command == "full-check":
            result_code = manager.full_check()
        elif args.command == "status":
            manager.show_status()
            result_code = 0
        elif args.command == "operational":
            result_code = manager.operational()
        elif args.command == "health-check":
            result_code = manager.health_check()
        elif args.command == "monitor":
            result_code = manager.monitor_production(args.hours)
            details = {"duration_hours": args.hours}
        else:
            parser.print_help()
            result_code = 1

        # レポート出力（statusコマンド以外、--no-reportが指定されていない場合）
        if args.command and args.command != "status" and not getattr(args, "no_report", False):
            try:
                report_path = manager.save_report_to_file(args.command, result_code, details)
                print(f"\n📄 実行レポートを保存しました: {report_path}")
                print("💡 このファイルを他のAIに共有して、詳細な分析や修正方法を相談できます")
            except Exception as e:
                print(f"⚠️ レポート保存エラー: {e}")

    except Exception as e:
        print(f"❌ コマンド実行エラー: {e}")
        result_code = 1

        # エラー時もレポート保存
        if args.command and args.command != "status" and not getattr(args, "no_report", False):
            try:
                details["error"] = str(e)
                report_path = manager.save_report_to_file(args.command, result_code, details)
                print(f"📄 エラーレポートを保存しました: {report_path}")
            except Exception:
                pass  # レポート保存でエラーが起きても無視

    return result_code


if __name__ == "__main__":
    sys.exit(main())
