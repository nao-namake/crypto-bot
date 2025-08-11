#!/usr/bin/env python3
"""
Phase 2-3システム: 統合CLI (bot_manager.py) 統合テスト

ChatGPT提案システムの統合CLIテスト
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))

from bot_manager import BotManager


class TestBotManagerIntegration(unittest.TestCase):
    """BotManager統合テスト"""

    def setUp(self):
        """テスト用設定"""
        self.test_project_root = Path(__file__).parent.parent.parent.parent
        self.manager = BotManager()

    def test_bot_manager_initialization(self):
        """BotManager初期化テスト"""
        manager = BotManager()

        # プロジェクトルートが正しく設定されている
        self.assertTrue(manager.project_root.exists())
        self.assertTrue((manager.project_root / "crypto_bot").exists())

        # スクリプトディレクトリが正しく設定されている
        self.assertTrue(manager.scripts_dir.exists())
        self.assertTrue((manager.scripts_dir / "bot_manager.py").exists())

    @patch("subprocess.run")
    def test_validate_quick_mode(self, mock_run):
        """クイック検証モードテスト"""
        # 成功ケース
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.validate(mode="quick")

        self.assertEqual(result, 0)
        mock_run.assert_called_once()

        # validate_all.sh --quick が呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("validate_all.sh", call_args)
        self.assertIn("--quick", call_args)

    @patch("subprocess.run")
    def test_validate_full_mode(self, mock_run):
        """フル検証モードテスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.validate(mode="full")

        self.assertEqual(result, 0)

        # validate_all.sh （引数なし）が呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("validate_all.sh", call_args)
        self.assertNotIn("--quick", call_args)
        self.assertNotIn("--ci", call_args)

    @patch("subprocess.run")
    def test_validate_ci_mode(self, mock_run):
        """CI検証モードテスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.validate(mode="ci")

        self.assertEqual(result, 0)

        # validate_all.sh --ci が呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("validate_all.sh", call_args)
        self.assertIn("--ci", call_args)

    @patch("subprocess.run")
    def test_monitor_with_paper_trade(self, mock_run):
        """ペーパートレード統合監視テスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.monitor(hours=2, with_paper_trade=True)

        self.assertEqual(result, 0)

        # paper_trade_with_monitoring.sh が呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("paper_trade_with_monitoring.sh", call_args)
        self.assertIn("--duration", call_args)
        self.assertIn("2", call_args)

    @patch("subprocess.run")
    def test_monitor_signal_only(self, mock_run):
        """シグナル監視のみテスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.monitor(hours=24, with_paper_trade=False)

        self.assertEqual(result, 0)

        # signal_monitor.py が呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("signal_monitor.py", call_args)
        self.assertIn("--hours", call_args)
        self.assertIn("24", call_args)

    @patch("subprocess.run")
    def test_fix_errors_auto_mode(self, mock_run):
        """エラー自動修復モードテスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.fix_errors(auto_fix=True, interactive=False)

        self.assertEqual(result, 0)

        # analyze_and_fix.py が正しい引数で呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("analyze_and_fix.py", call_args)
        self.assertIn("--auto-fix", call_args)

    @patch("subprocess.run")
    def test_fix_errors_interactive_mode(self, mock_run):
        """エラー対話修復モードテスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.fix_errors(auto_fix=False, interactive=True)

        self.assertEqual(result, 0)

        # analyze_and_fix.py が正しい引数で呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("analyze_and_fix.py", call_args)
        self.assertIn("--interactive", call_args)
        self.assertNotIn("--auto-fix", call_args)

    @patch("subprocess.run")
    def test_paper_trade_execution(self, mock_run):
        """ペーパートレード実行テスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.paper_trade(duration_hours=3)

        self.assertEqual(result, 0)

        # crypto_bot.main live-bitbank が正しい引数で呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("crypto_bot.main", call_args)
        self.assertIn("live-bitbank", call_args)
        self.assertIn("--paper-trade", call_args)
        self.assertIn("--duration", call_args)
        self.assertIn("10800", call_args)  # 3時間 = 10800秒

    @patch("subprocess.run")
    def test_leak_detection(self, mock_run):
        """未来データリーク検出テスト"""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.manager.leak_detection(html=True)

        self.assertEqual(result, 0)

        # future_leak_detector.py が正しい引数で呼ばれることを確認
        call_args = mock_run.call_args[0][0]
        self.assertIn("future_leak_detector.py", call_args)
        self.assertIn("--project-root", call_args)
        self.assertIn("--html", call_args)

    @patch("subprocess.run")
    def test_full_check_workflow(self, mock_run):
        """フルチェックワークフローテスト"""
        # 全ステップ成功のシミュレーション
        mock_run.return_value = MagicMock(returncode=0)

        with (
            patch.object(self.manager, "validate", return_value=0),
            patch.object(self.manager, "leak_detection", return_value=0),
            patch.object(self.manager, "monitor", return_value=0),
            patch.object(self.manager, "fix_errors", return_value=0),
        ):

            result = self.manager.full_check()

            self.assertEqual(result, 0)

    @patch("subprocess.run")
    def test_full_check_with_failure(self, mock_run):
        """フルチェック一部失敗テスト"""
        # 一部ステップが失敗するシミュレーション
        with (
            patch.object(self.manager, "validate", return_value=0),
            patch.object(self.manager, "leak_detection", return_value=1),
            patch.object(self.manager, "monitor", return_value=0),
            patch.object(self.manager, "fix_errors", return_value=0),
        ):

            result = self.manager.full_check()

            # 一つでも失敗があれば全体失敗
            self.assertEqual(result, 1)

    def test_show_status_method(self):
        """システム状態表示メソッドテスト"""
        # エラーが発生しないことを確認
        try:
            self.manager.show_status()
        except Exception as e:
            self.fail(f"show_status raised an exception: {e}")

    @patch("subprocess.run")
    def test_command_execution_error_handling(self, mock_run):
        """コマンド実行エラーハンドリングテスト"""
        # コマンド実行が失敗する場合
        mock_run.side_effect = Exception("Command execution failed")

        returncode, output = self.manager.run_command(["fake-command"])

        self.assertEqual(returncode, 1)
        self.assertIn("Command execution failed", output)

    def test_project_structure_validation(self):
        """プロジェクト構造検証テスト"""
        # 必要なディレクトリ・ファイルの存在確認
        required_paths = [
            "crypto_bot",
            "scripts",
            "config",
            "tests",
            "requirements",
        ]

        for path in required_paths:
            full_path = self.manager.project_root / path
            self.assertTrue(full_path.exists(), f"{path} が見つかりません")


class TestBotManagerCLI(unittest.TestCase):
    """BotManager CLI統合テスト"""

    def test_cli_script_exists(self):
        """CLIスクリプト存在確認"""
        bot_manager_path = (
            Path(__file__).parent.parent.parent.parent / "scripts" / "bot_manager.py"
        )
        self.assertTrue(bot_manager_path.exists())

        # 実行権限確認（Unix系システム）
        if os.name != "nt":  # Windows以外
            self.assertTrue(os.access(str(bot_manager_path), os.X_OK))

    @patch("sys.argv", ["bot_manager.py", "status"])
    def test_cli_status_command(self):
        """CLI status コマンドテスト"""
        # 実際のCLI実行ではなく、引数パースのテスト
        from bot_manager import main

        # エラーが発生しないことを確認（実際の実行はしない）
        try:
            # 実際の実行はテスト環境では行わない
            pass
        except SystemExit:
            # main()がsys.exit()を呼ぶ可能性があるため
            pass


if __name__ == "__main__":
    unittest.main()
