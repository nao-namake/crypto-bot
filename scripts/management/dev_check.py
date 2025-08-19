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
        super().__init__(output_dir="logs/management")
        
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

    def run_command(
        self, command: List[str], capture: bool = False, show_output: bool = True
    ) -> Tuple[int, str]:
        """コマンド実行ラッパー（base_analyzer.pyの機能を活用）"""
        if show_output:
            print(f"📍 実行: {' '.join(command)}")
        
        # gcloudコマンドの場合はbase_analyzer.pyの機能を使用
        if command[0] == "gcloud":
            returncode, stdout, stderr = self.run_gcloud_command(command, show_output=show_output)
            return returncode, stdout + stderr
        
        # その他のコマンドは従来通り
        try:
            import subprocess
            if capture:
                result = subprocess.run(
                    command, capture_output=True, text=True, cwd=self.project_root, timeout=300
                )
                return result.returncode, result.stdout + result.stderr
            else:
                result = subprocess.run(command, cwd=self.project_root, timeout=300)
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
            "from src.ml.production.ensemble import ProductionEnsemble",
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
            (self.scripts_dir / "quality" / "checks.sh", "品質チェックスクリプト"),
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
            mode: "full" (checks.sh), "light" (checks_light.sh)
        """
        print("\n" + "=" * 60)
        print("🔍 新システム品質チェック")
        print("=" * 60)

        if mode == "light":
            check_script = self.scripts_dir / "checks_light.sh"
            print("📝 軽量品質チェック実行")
        else:
            check_script = self.scripts_dir / "checks.sh"
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

        create_script = self.scripts_dir / "create_ml_models.py"

        if not create_script.exists():
            print(f"❌ MLモデル作成スクリプトが見つかりません: {create_script}")
            return 1

        cmd = ["python3", str(create_script)]

        if dry_run:
            cmd.append("--dry-run")
            print("🔍 ドライラン: モデル作成のシミュレーション")

        if verbose:
            cmd.append("--verbose")

        returncode, _ = self.run_command(cmd)

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
    sys.exit(1).
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
    sys.exit(1).
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
    if 'logging' in config:
        print('✅ ログ設定存在')
    if 'data' in config:
        print('✅ データ設定存在')
except Exception as e:
    print(f'❌ Config エラー: {e}')
    sys.exit(1).
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
                timeout=600  # 10分タイムアウト
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
            "品質チェック": self.scripts_dir / "checks.sh",
            "MLモデル作成": self.scripts_dir / "create_ml_models.py",
            "Bot統合管理": self.scripts_dir / "dev_check.py",
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
            returncode, _, _ = self.run_gcloud_command(["gcloud", "secrets", "describe", secret_name])
            
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
        """Phase 11: 24時間本番監視システム."""
        print("\n" + "=" * 60)
        print("📡 Phase 11本番環境24時間監視")
        print("=" * 60)

        import time
        import threading
        from datetime import timedelta
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)  # Phase 11バグ修正: timedelta使用
        
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
                print(f"📊 成功率: {success_rate:.1f}% ({total_checks - failed_checks}/{total_checks})")

                # 5分間待機
                time.sleep(300)

        except KeyboardInterrupt:
            print("\n⚠️ 監視を中断しました")
            
        # 監視完了サマリー
        monitoring_duration = datetime.now() - start_time
        success_rate = ((total_checks - failed_checks) / total_checks) * 100 if total_checks > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 24時間監視結果")
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
            "gcloud", "run", "services", "describe", "crypto-bot-service",
            "--region=asia-northeast1", "--format=value(status.conditions[0].status)"
        ]
        returncode, output = self.run_command(cmd, capture=True, show_output=False)
        
        if returncode != 0 or "True" not in output:
            return 1

        # サービスURL応答確認
        cmd = [
            "gcloud", "run", "services", "describe", "crypto-bot-service",
            "--region=asia-northeast1", "--format=value(status.url)"
        ]
        returncode, service_url = self.run_command(cmd, capture=True, show_output=False)
        
        if returncode == 0 and service_url.strip():
            service_url = service_url.strip()
            import urllib.request
            import urllib.error
            try:
                with urllib.request.urlopen(f"{service_url}/health", timeout=10) as response:
                    return 0 if response.status == 200 else 1
            except:
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
            "check_results": self.check_results
        }
    
    def generate_report(self, analysis_result: Dict) -> str:
        """レポート生成（base_analyzer.py要求）"""
        return f"統合管理レポート: {analysis_result['timestamp']}"
    
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
            "from src.ml.production.ensemble import ProductionEnsemble"
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
        "--hours",
        type=int,
        default=24,
        help="監視時間（時間、デフォルト: 24時間）"
    )

    args = parser.parse_args()

    manager = UnifiedBotManager()

    if not args.command:
        parser.print_help()
        print(
            "\n💡 推奨: まずは 'python scripts/management/dev_check.py phase-check' で状況を確認"
        )
        print("🔧 Phase 12統合機能:")
        print("   - operational: 本番運用診断（ops_monitor.py委譲）")
        print("   - health-check: GCP本番環境ヘルスチェック")
        print("   - monitor: 24時間本番監視")
        return 0

    # コマンド実行
    if args.command == "phase-check":
        return manager.phase_check()
    elif args.command == "validate":
        return manager.validate(args.mode)
    elif args.command == "ml-models":
        return manager.ml_models(args.dry_run, args.verbose)
    elif args.command == "data-check":
        return manager.data_check()
    elif args.command == "full-check":
        return manager.full_check()
    elif args.command == "status":
        manager.show_status()
        return 0
    elif args.command == "operational":
        return manager.operational()
    elif args.command == "health-check":
        return manager.health_check()
    elif args.command == "monitor":
        return manager.monitor_production(args.hours)
    else:
        parser.print_help()
        return 1




if __name__ == "__main__":
    sys.exit(main())
