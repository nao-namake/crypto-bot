#!/usr/bin/env python
"""
Crypto-Bot 統合管理CLI

すべての検証・監視・修復機能を1つのCLIで管理
使い忘れ防止と作業効率化を実現

Usage:
    python scripts/bot_manager.py --help
    python scripts/bot_manager.py validate [options]
    python scripts/bot_manager.py monitor [options]
    python scripts/bot_manager.py fix-errors [options]
    python scripts/bot_manager.py paper-trade [options]
    python scripts/bot_manager.py full-check
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


class BotManager:
    """Crypto-Bot統合管理クラス"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.scripts_dir = self.project_root / "scripts"
        self.utilities_dir = self.scripts_dir / "utilities"

    def run_command(self, command: List[str], capture: bool = False) -> Tuple[int, str]:
        """コマンド実行のラッパー"""
        print(f"📍 実行: {' '.join(command)}")
        try:
            if capture:
                result = subprocess.run(
                    command, capture_output=True, text=True, cwd=self.project_root
                )
                return result.returncode, result.stdout + result.stderr
            else:
                result = subprocess.run(command, cwd=self.project_root)
                return result.returncode, ""
        except Exception as e:
            print(f"❌ エラー: {e}")
            return 1, str(e)

    def validate(self, mode: str = "full") -> int:
        """
        検証実行（3段階検証システム）

        Args:
            mode: "full" (全検証), "quick" (Level 1のみ), "ci" (Level 1+2)
        """
        print("\n" + "=" * 60)
        print("🔍 Validation Pipeline")
        print("=" * 60)

        validate_script = self.scripts_dir / "ci_tools" / "validate_all.sh"

        if mode == "quick":
            cmd = ["bash", str(validate_script), "--quick"]
        elif mode == "ci":
            cmd = ["bash", str(validate_script), "--ci"]
        else:
            cmd = ["bash", str(validate_script)]

        returncode, _ = self.run_command(cmd)

        if returncode == 0:
            print("\n✅ 検証成功！デプロイ可能です。")
        else:
            print("\n❌ 検証失敗。上記のエラーを修正してください。")
            print(
                "💡 ヒント: 'python scripts/bot_manager.py fix-errors' で自動修復を試してください"
            )

        return returncode

    def monitor(self, hours: int = 24, with_paper_trade: bool = False) -> int:
        """
        監視実行

        Args:
            hours: 監視時間
            with_paper_trade: ペーパートレードと統合実行
        """
        print("\n" + "=" * 60)
        print("📊 Monitoring System")
        print("=" * 60)

        if with_paper_trade:
            # ペーパートレード＋監視の統合実行
            cmd = [
                "bash",
                str(self.scripts_dir / "monitoring" / "paper_trade_with_monitoring.sh"),
                "--duration",
                str(hours),
            ]
            print(f"🎯 ペーパートレード＋シグナル監視を{hours}時間実行")
        else:
            # シグナル監視のみ
            cmd = [
                "python",
                str(self.scripts_dir / "monitoring" / "signal_monitor.py"),
                "--hours",
                str(hours),
            ]
            print(f"📈 シグナル監視を過去{hours}時間分実行")

        returncode, _ = self.run_command(cmd)

        if returncode == 0:
            print("\n✅ 監視完了。レポートを確認してください。")
        else:
            print("\n⚠️ 監視中に問題が検出されました。")

        return returncode

    def fix_errors(
        self, source: str = "both", auto_fix: bool = False, interactive: bool = True
    ) -> int:
        """
        エラー分析と修復

        Args:
            source: "gcp", "local", "both"
            auto_fix: CRITICALエラーの自動修復
            interactive: インタラクティブモード
        """
        print("\n" + "=" * 60)
        print("🔧 Error Analysis & Fix")
        print("=" * 60)

        cmd = [
            "python",
            str(self.scripts_dir / "monitoring" / "analyze_and_fix.py"),
            "--source",
            source,
            "--hours",
            "24",
        ]

        if auto_fix:
            cmd.append("--auto-fix")
            print("🤖 自動修復モード有効")

        if interactive:
            cmd.append("--interactive")
            print("💬 インタラクティブモード有効")

        returncode, _ = self.run_command(cmd)

        if returncode == 0:
            print("\n✅ エラー分析完了")
        else:
            print("\n❌ エラー分析中に問題が発生しました")

        return returncode

    def paper_trade(self, duration_hours: int = 1) -> int:
        """
        ペーパートレード実行

        Args:
            duration_hours: 実行時間（時間）
        """
        print("\n" + "=" * 60)
        print("📝 Paper Trading")
        print("=" * 60)
        print(f"⏱️ {duration_hours}時間のペーパートレードを実行")

        # CLIコマンドで実行
        cmd = [
            "python",
            "-m",
            "crypto_bot.main",
            "live-bitbank",
            "--paper-trade",
            "--duration",
            str(duration_hours * 3600),  # 秒に変換
        ]

        returncode, _ = self.run_command(cmd)

        if returncode == 0:
            print("\n✅ ペーパートレード完了")
            print("📊 結果: logs/paper_trades.csv を確認してください")
        else:
            print("\n❌ ペーパートレード実行中にエラーが発生しました")

        return returncode

    def leak_detection(self, html: bool = True) -> int:
        """
        未来データリーク検出

        Args:
            html: HTMLレポート生成
        """
        print("\n" + "=" * 60)
        print("🔍 Future Data Leak Detection")
        print("=" * 60)

        cmd = [
            "python",
            str(self.scripts_dir / "monitoring" / "future_leak_detector.py"),
            "--project-root",
            str(self.project_root),
        ]

        if html:
            cmd.append("--html")

        returncode, _ = self.run_command(cmd)

        if returncode == 0:
            print("\n✅ リーク検出完了。問題は見つかりませんでした。")
        else:
            print("\n⚠️ 潜在的なデータリークが検出されました。")

        return returncode

    def full_check(self) -> int:
        """
        フルチェック（デプロイ前の完全検証）
        """
        print("\n" + "=" * 60)
        print("🎯 Full Pre-deployment Check")
        print("=" * 60)
        print(f"開始時刻: {datetime.now()}")
        print("=" * 60)

        steps = [
            ("1/5 品質チェック", lambda: self.validate("quick")),
            ("2/5 未来データリーク検出", lambda: self.leak_detection()),
            ("3/5 シグナル監視", lambda: self.monitor(hours=1)),
            (
                "4/5 エラー分析",
                lambda: self.fix_errors(auto_fix=False, interactive=False),
            ),
            ("5/5 完全検証", lambda: self.validate("full")),
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
        print("📊 Full Check Results")
        print("=" * 60)

        if not failed_steps:
            print("✅ すべてのチェックに合格しました！")
            print("🚀 デプロイ準備完了です。")
            print("\n推奨コマンド:")
            print("  git add -A")
            print("  git commit -m 'feat: your commit message'")
            print("  git push origin main")
            return 0
        else:
            print("❌ 以下のチェックで問題が検出されました:")
            for step in failed_steps:
                print(f"  - {step}")
            print("\n修正後、再度実行してください。")
            return 1

    def show_status(self) -> None:
        """現在のシステム状態を表示"""
        print("\n" + "=" * 60)
        print("📊 System Status")
        print("=" * 60)

        # 最新のログファイルをチェック
        log_files = {
            "シグナルログ": "logs/trading_signals.csv",
            "ペーパートレードログ": "logs/paper_trades.csv",
            "エラーレポート": "logs/error_analysis/*.html",
            "リーク検出レポート": "logs/leak_detection/*.html",
        }

        for name, path in log_files.items():
            full_path = self.project_root / path
            if "*" in str(full_path):
                # ワイルドカードパターン
                parent = full_path.parent
                pattern = full_path.name
                if parent.exists():
                    files = list(parent.glob(pattern))
                    if files:
                        latest = max(files, key=lambda p: p.stat().st_mtime)
                        print(f"  {name}: ✅ {latest.name}")
                    else:
                        print(f"  {name}: ⚪ 未生成")
                else:
                    print(f"  {name}: ⚪ 未生成")
            else:
                if full_path.exists():
                    mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
                    print(f"  {name}: ✅ {mtime.strftime('%Y-%m-%d %H:%M')}")
                else:
                    print(f"  {name}: ⚪ 未生成")

        print("\n" + "=" * 60)


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="Crypto-Bot 統合管理CLI - すべての検証・監視・修復機能を統合",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # デプロイ前の完全チェック
  python scripts/bot_manager.py full-check
  
  # 高速検証のみ
  python scripts/bot_manager.py validate --mode quick
  
  # エラー分析と自動修復
  python scripts/bot_manager.py fix-errors --auto-fix
  
  # ペーパートレード実行
  python scripts/bot_manager.py paper-trade --hours 2
  
  # シグナル監視
  python scripts/bot_manager.py monitor --hours 24
  
  # システム状態確認
  python scripts/bot_manager.py status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # validate コマンド
    validate_parser = subparsers.add_parser("validate", help="検証実行（3段階検証）")
    validate_parser.add_argument(
        "--mode",
        choices=["full", "quick", "ci"],
        default="full",
        help="検証モード: full(全検証), quick(Level 1のみ), ci(Level 1+2)",
    )

    # monitor コマンド
    monitor_parser = subparsers.add_parser("monitor", help="監視実行")
    monitor_parser.add_argument(
        "--hours", type=int, default=24, help="監視時間（デフォルト: 24時間）"
    )
    monitor_parser.add_argument(
        "--with-paper-trade", action="store_true", help="ペーパートレードと統合実行"
    )

    # fix-errors コマンド
    fix_parser = subparsers.add_parser("fix-errors", help="エラー分析と修復")
    fix_parser.add_argument(
        "--source", choices=["gcp", "local", "both"], default="both", help="ログソース"
    )
    fix_parser.add_argument(
        "--auto-fix", action="store_true", help="CRITICALエラーを自動修復"
    )
    fix_parser.add_argument(
        "--no-interactive", action="store_true", help="インタラクティブモードを無効化"
    )

    # paper-trade コマンド
    paper_parser = subparsers.add_parser("paper-trade", help="ペーパートレード実行")
    paper_parser.add_argument(
        "--hours", type=int, default=1, help="実行時間（デフォルト: 1時間）"
    )

    # leak-detect コマンド
    leak_parser = subparsers.add_parser("leak-detect", help="未来データリーク検出")
    leak_parser.add_argument(
        "--no-html", action="store_true", help="HTMLレポートを生成しない"
    )

    # full-check コマンド
    subparsers.add_parser("full-check", help="デプロイ前の完全チェック")

    # status コマンド
    subparsers.add_parser("status", help="システム状態確認")

    args = parser.parse_args()

    manager = BotManager()

    if not args.command:
        parser.print_help()
        print(
            "\n💡 ヒント: まずは 'python scripts/bot_manager.py status' でシステム状態を確認"
        )
        return 0

    # コマンド実行
    if args.command == "validate":
        return manager.validate(args.mode)
    elif args.command == "monitor":
        return manager.monitor(args.hours, args.with_paper_trade)
    elif args.command == "fix-errors":
        return manager.fix_errors(args.source, args.auto_fix, not args.no_interactive)
    elif args.command == "paper-trade":
        return manager.paper_trade(args.hours)
    elif args.command == "leak-detect":
        return manager.leak_detection(not args.no_html)
    elif args.command == "full-check":
        return manager.full_check()
    elif args.command == "status":
        manager.show_status()
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
