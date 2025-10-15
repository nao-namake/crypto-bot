#!/usr/bin/env python3
"""
Phase 40統合最適化スクリプト

Phase 40.1-40.5の最適化を統合実行：
- メニュー駆動型インターフェース
- 全Phase一括実行（40.1→40.2→40.3→40.4→40.5）
- 個別Phase実行
- 進捗チェックポイント機能
- DRY RUNモード

使用方法:
  # 対話式メニュー
  python3 scripts/optimization/run_phase40_optimization.py

  # 全Phase一括実行
  python3 scripts/optimization/run_phase40_optimization.py --all

  # DRY RUNモード
  python3 scripts/optimization/run_phase40_optimization.py --all --dry-run

  # 特定Phaseから再開
  python3 scripts/optimization/run_phase40_optimization.py --resume phase40_2
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Phase別最適化スクリプトインポート
from scripts.optimization.integrate_and_deploy import IntegrationDeployer
from scripts.optimization.optimize_ml_hyperparameters import MLHyperparameterOptimizer
from scripts.optimization.optimize_ml_integration import MLIntegrationOptimizer
from scripts.optimization.optimize_risk_management import RiskManagementOptimizer
from scripts.optimization.optimize_strategy_parameters import StrategyParameterOptimizer
from src.core.logger import CryptoBotLogger


class Phase40UnifiedOptimizer:
    """Phase 40統合最適化クラス"""

    def __init__(self, logger: CryptoBotLogger, dry_run: bool = False):
        """
        初期化

        Args:
            logger: ログシステム
            dry_run: DRY RUNモード（True: 実際の更新なし）
        """
        self.logger = logger
        self.dry_run = dry_run
        self.checkpoint_file = Path("config/optuna_results/.checkpoint.json")
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        # Phase定義（実行順序）
        self.phases = [
            {
                "id": "phase40_1",
                "name": "Phase 40.1: リスク管理パラメータ最適化",
                "params": 12,
                "n_trials": 50,
                "timeout": 3600,  # 1時間
                "optimizer_class": RiskManagementOptimizer,
            },
            {
                "id": "phase40_2",
                "name": "Phase 40.2: 戦略パラメータ最適化",
                "params": 30,
                "n_trials": 300,
                "timeout": 10800,  # 3時間
                "optimizer_class": StrategyParameterOptimizer,
            },
            {
                "id": "phase40_3",
                "name": "Phase 40.3: ML統合パラメータ最適化",
                "params": 7,
                "n_trials": 150,
                "timeout": 7200,  # 2時間
                "optimizer_class": MLIntegrationOptimizer,
            },
            {
                "id": "phase40_4",
                "name": "Phase 40.4: MLハイパーパラメータ最適化",
                "params": 30,
                "n_trials": 250,
                "timeout": 10800,  # 3時間
                "optimizer_class": MLHyperparameterOptimizer,
            },
            {
                "id": "phase40_5",
                "name": "Phase 40.5: 最適化結果統合・デプロイ",
                "params": 79,
                "n_trials": 0,
                "timeout": 0,
                "optimizer_class": IntegrationDeployer,
            },
        ]

    def load_checkpoint(self) -> Dict[str, Any]:
        """
        チェックポイント読み込み

        Returns:
            Dict: チェックポイントデータ
        """
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"completed_phases": [], "current_phase": None, "start_time": None}

    def save_checkpoint(self, checkpoint: Dict[str, Any]):
        """
        チェックポイント保存

        Args:
            checkpoint: 保存するチェックポイントデータ
        """
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)

    def clear_checkpoint(self):
        """チェックポイントクリア"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()

    def display_menu(self) -> str:
        """
        メニュー表示

        Returns:
            str: ユーザー選択
        """
        print("\n" + "=" * 80)
        print("🎯 Phase 40統合最適化スクリプト")
        print("=" * 80)
        print("\nメニュー:")
        print("  [1] 全Phase一括実行（Phase 40.1→40.5、13-19時間）")
        print("  [2] Phase 40.1: リスク管理パラメータ最適化（12パラメータ、1時間）")
        print("  [3] Phase 40.2: 戦略パラメータ最適化（30パラメータ、3時間）")
        print("  [4] Phase 40.3: ML統合パラメータ最適化（7パラメータ、2時間）")
        print("  [5] Phase 40.4: MLハイパーパラメータ最適化（30パラメータ、3時間）")
        print("  [6] Phase 40.5: 最適化結果統合・デプロイのみ（即座）")
        print("  [7] チェックポイントから再開")
        print("  [8] チェックポイントクリア")
        print("  [0] 終了")

        checkpoint = self.load_checkpoint()
        if checkpoint["completed_phases"]:
            print(f"\n💾 チェックポイント検出: {len(checkpoint['completed_phases'])} Phase完了")

        print("\n" + "=" * 80)
        choice = input("選択してください [0-8]: ").strip()
        return choice

    def run_single_phase(self, phase: Dict[str, Any]) -> bool:
        """
        単一Phase実行

        Args:
            phase: Phase定義

        Returns:
            bool: 成功/失敗
        """
        phase_id = phase["id"]
        phase_name = phase["name"]

        try:
            self.logger.warning(f"🚀 {phase_name} 開始")

            if phase_id == "phase40_5":
                # Phase 40.5: 統合デプロイ
                deployer = IntegrationDeployer(self.logger)
                success = deployer.deploy(dry_run=self.dry_run)
            else:
                # Phase 40.1-40.4: 最適化実行
                optimizer_class = phase["optimizer_class"]
                optimizer = optimizer_class(self.logger)
                results = optimizer.optimize(n_trials=phase["n_trials"], timeout=phase["timeout"])
                success = results.get("best_value", -10.0) > -5.0

            if success:
                self.logger.warning(f"✅ {phase_name} 完了", discord_notify=True)
            else:
                self.logger.error(f"❌ {phase_name} 失敗")

            return success

        except Exception as e:
            self.logger.error(f"❌ {phase_name} エラー: {e}")
            return False

    def run_all_phases(self, resume_from: Optional[str] = None) -> bool:
        """
        全Phase一括実行

        Args:
            resume_from: 再開Phase ID（None: 最初から）

        Returns:
            bool: 成功/失敗
        """
        checkpoint = self.load_checkpoint()
        start_time = time.time()

        # 再開Phase判定
        start_index = 0
        if resume_from:
            for i, phase in enumerate(self.phases):
                if phase["id"] == resume_from:
                    start_index = i
                    break
            self.logger.info(f"🔄 {self.phases[start_index]['name']} から再開")
        elif checkpoint["completed_phases"]:
            # 最後の完了Phaseの次から再開
            last_completed = checkpoint["completed_phases"][-1]
            for i, phase in enumerate(self.phases):
                if phase["id"] == last_completed:
                    start_index = i + 1
                    break
            if start_index < len(self.phases):
                self.logger.info(f"🔄 チェックポイントから再開: {self.phases[start_index]['name']}")

        # チェックポイント初期化
        if not checkpoint["start_time"]:
            checkpoint["start_time"] = datetime.now().isoformat()

        # Phase実行
        for i in range(start_index, len(self.phases)):
            phase = self.phases[i]
            checkpoint["current_phase"] = phase["id"]
            self.save_checkpoint(checkpoint)

            success = self.run_single_phase(phase)

            if not success:
                self.logger.error(f"❌ {phase['name']} 失敗により中断")
                return False

            # 完了記録
            checkpoint["completed_phases"].append(phase["id"])
            self.save_checkpoint(checkpoint)

        duration = time.time() - start_time
        self.print_summary(duration)

        # チェックポイントクリア
        self.clear_checkpoint()

        return True

    def run_phase_by_id(self, phase_id: str) -> bool:
        """
        Phase ID指定で実行

        Args:
            phase_id: Phase ID

        Returns:
            bool: 成功/失敗
        """
        for phase in self.phases:
            if phase["id"] == phase_id:
                return self.run_single_phase(phase)

        self.logger.error(f"❌ 無効なPhase ID: {phase_id}")
        return False

    def print_summary(self, duration: float):
        """
        実行サマリー表示

        Args:
            duration: 実行時間（秒）
        """
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)

        print("\n" + "=" * 80)
        print("🎉 Phase 40統合最適化完了")
        print("=" * 80)
        print(f"\n実行時間: {hours}時間{minutes}分")
        print(f"最適化パラメータ総数: 79")
        print("\n完了Phase:")
        for phase in self.phases:
            print(f"  ✅ {phase['name']}")

        if self.dry_run:
            print("\n⚠️ DRY RUNモードで実行（実際の更新なし）")
        else:
            print("\n📁 結果ファイル: config/optuna_results/")
            print("📁 設定ファイル: config/core/thresholds.yaml")
            print("📁 バックアップ: config/core/backups/")

        print("\n🚀 次のステップ:")
        print("  1. bash scripts/testing/checks.sh で品質チェック")
        print("  2. バックテスト実行で性能検証")
        print("  3. ペーパーテスト実行で動作確認")
        print("  4. 本番デプロイ")

        print("\n" + "=" * 80)

    def interactive_menu(self) -> bool:
        """
        対話式メニュー実行

        Returns:
            bool: 成功/失敗
        """
        while True:
            choice = self.display_menu()

            if choice == "0":
                print("終了します。")
                return True

            elif choice == "1":
                # 全Phase一括実行
                return self.run_all_phases()

            elif choice in ["2", "3", "4", "5", "6"]:
                # 個別Phase実行
                phase_index = int(choice) - 2
                return self.run_single_phase(self.phases[phase_index])

            elif choice == "7":
                # チェックポイントから再開
                checkpoint = self.load_checkpoint()
                if not checkpoint["completed_phases"]:
                    print("⚠️ チェックポイントが存在しません。")
                    continue
                return self.run_all_phases()

            elif choice == "8":
                # チェックポイントクリア
                self.clear_checkpoint()
                print("✅ チェックポイントをクリアしました。")

            else:
                print("⚠️ 無効な選択です。0-8を入力してください。")


def main():
    """メイン実行"""
    parser = argparse.ArgumentParser(description="Phase 40統合最適化スクリプト")
    parser.add_argument("--all", action="store_true", help="全Phase一括実行（Phase 40.1→40.5）")
    parser.add_argument(
        "--phase",
        type=str,
        choices=["phase40_1", "phase40_2", "phase40_3", "phase40_4", "phase40_5"],
        help="個別Phase実行",
    )
    parser.add_argument(
        "--resume",
        type=str,
        choices=["phase40_1", "phase40_2", "phase40_3", "phase40_4", "phase40_5"],
        help="指定Phaseから再開",
    )
    parser.add_argument("--dry-run", action="store_true", help="DRY RUNモード（実際の更新なし）")
    args = parser.parse_args()

    # ログシステム初期化
    logger = CryptoBotLogger()

    # 統合最適化実行
    optimizer = Phase40UnifiedOptimizer(logger, dry_run=args.dry_run)

    try:
        if args.all:
            # 全Phase一括実行
            success = optimizer.run_all_phases()
        elif args.phase:
            # 個別Phase実行
            success = optimizer.run_phase_by_id(args.phase)
        elif args.resume:
            # 指定Phaseから再開
            success = optimizer.run_all_phases(resume_from=args.resume)
        else:
            # 対話式メニュー
            success = optimizer.interactive_menu()

        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.warning("\n⚠️ ユーザーによる中断（Ctrl+C）")
        print("\n💾 進捗はチェックポイントに保存されています。")
        print("次回実行時に --resume または [7]チェックポイントから再開 で再開できます。")
        sys.exit(1)


if __name__ == "__main__":
    main()
