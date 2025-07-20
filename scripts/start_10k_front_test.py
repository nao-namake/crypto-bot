#!/usr/bin/env python3
"""
1万円フロントテスト実行スクリプト
Phase 8統計システム実動作検証・126特徴量・外部APIエラー確認
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.utils.enhanced_status_manager import EnhancedStatusManager
from crypto_bot.utils.trading_integration_service import TradingIntegrationService


class FrontTestManager:
    """1万円フロントテスト管理クラス"""

    def __init__(self):
        self.test_config = "config/development/bitbank_10k_front_test.yml"
        self.test_duration_hours = 24
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=self.test_duration_hours)

        # ログ設定
        self._setup_logging()

        # 統計システム初期化
        self.integration_service = TradingIntegrationService(
            base_dir=str(project_root), initial_balance=10000.0
        )

        self.logger.info("1万円フロントテスト管理システムを初期化しました")

    def _setup_logging(self):
        """ログ設定"""
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = (
            log_dir / f"10k_front_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )

        self.logger = logging.getLogger(__name__)

    def pre_test_verification(self) -> bool:
        """事前検証"""
        self.logger.info("🔍 事前検証を開始します...")

        verification_steps = [
            self._verify_config_file,
            self._verify_api_credentials,
            self._verify_external_apis,
            self._verify_statistics_system,
            self._verify_risk_management,
        ]

        for step in verification_steps:
            try:
                success = step()
                if not success:
                    self.logger.error(f"事前検証失敗: {step.__name__}")
                    return False

            except Exception as e:
                self.logger.error(f"事前検証エラー {step.__name__}: {e}")
                return False

        self.logger.info("✅ 事前検証完了 - フロントテスト実行準備完了")
        return True

    def _verify_config_file(self) -> bool:
        """設定ファイル検証"""
        self.logger.info("📄 設定ファイル検証中...")

        config_path = project_root / self.test_config
        if not config_path.exists():
            self.logger.error(f"設定ファイルが見つかりません: {config_path}")
            return False

        # 設定内容検証（基本項目チェック）
        try:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # 必須設定項目チェック
            required_sections = ["data", "strategy", "risk", "live", "ml"]
            for section in required_sections:
                if section not in config:
                    self.logger.error(f"必須設定セクションが不足: {section}")
                    return False

            # 外部データ設定チェック
            if not config.get("ml", {}).get("external_data", {}).get("enabled", False):
                self.logger.warning("外部データが無効化されています")

            # フロントテスト設定チェック
            front_test = config.get("live", {}).get("front_test_settings", {})
            if not front_test.get("enabled", False):
                self.logger.error("フロントテスト設定が無効化されています")
                return False

            self.logger.info("✅ 設定ファイル検証完了")
            return True

        except Exception as e:
            self.logger.error(f"設定ファイル読み込みエラー: {e}")
            return False

    def _verify_api_credentials(self) -> bool:
        """API認証情報検証"""
        self.logger.info("🔑 API認証情報検証中...")

        required_env_vars = ["BITBANK_API_KEY", "BITBANK_API_SECRET"]

        for env_var in required_env_vars:
            if not os.getenv(env_var):
                self.logger.error(f"環境変数が設定されていません: {env_var}")
                return False

        self.logger.info("✅ API認証情報検証完了")
        return True

    def _verify_external_apis(self) -> bool:
        """外部API接続検証"""
        self.logger.info("🌐 外部API接続検証中...")

        try:
            # VIX指数取得テスト
            from crypto_bot.data.vix_fetcher import VIXFetcher

            vix_fetcher = VIXFetcher()
            vix_data = vix_fetcher.fetch_vix_data()
            if vix_data is None:
                self.logger.warning("VIX指数取得に失敗（フォールバック値使用）")
            else:
                self.logger.info(f"VIX指数取得成功: {vix_data}")

            # Fear&Greed指数取得テスト
            from crypto_bot.data.fear_greed_fetcher import FearGreedFetcher

            fg_fetcher = FearGreedFetcher()
            fg_data = fg_fetcher.fetch_fear_greed_index()
            if fg_data is None:
                self.logger.warning("Fear&Greed指数取得に失敗（フォールバック値使用）")
            else:
                self.logger.info(f"Fear&Greed指数取得成功: {fg_data}")

            # マクロ経済データ取得テスト
            from crypto_bot.data.macro_fetcher import MacroDataFetcher

            macro_fetcher = MacroDataFetcher()
            macro_data = macro_fetcher.fetch_macro_data()
            if not macro_data:
                self.logger.warning(
                    "マクロ経済データ取得に失敗（フォールバック値使用）"
                )
            else:
                self.logger.info(f"マクロ経済データ取得成功: {len(macro_data)}項目")

            self.logger.info("✅ 外部API接続検証完了")
            return True

        except Exception as e:
            self.logger.error(f"外部API検証エラー: {e}")
            self.logger.warning("外部APIエラーは許容範囲内（フォールバック機能で継続）")
            return True  # 外部APIエラーは許容（フォールバック機能あり）

    def _verify_statistics_system(self) -> bool:
        """統計システム検証"""
        self.logger.info("📊 統計システム検証中...")

        try:
            # TradingIntegrationService動作確認
            status = self.integration_service.get_trading_status()

            if "comprehensive_status" not in status:
                self.logger.error("統計システム初期化エラー")
                return False

            # テストシグナル記録
            signal_id = self.integration_service.record_trade_signal(
                signal="test",
                confidence=0.8,
                strategy_type="PreTestVerification",
                expected_profit=0.0,
                risk_level="low",
            )

            if not signal_id:
                self.logger.error("シグナル記録機能エラー")
                return False

            self.logger.info("✅ 統計システム検証完了")
            return True

        except Exception as e:
            self.logger.error(f"統計システム検証エラー: {e}")
            return False

    def _verify_risk_management(self) -> bool:
        """リスク管理検証"""
        self.logger.info("⚠️ リスク管理検証中...")

        try:
            # 緊急停止機能確認
            # ここでは設定ファイルの値を確認
            import yaml

            config_path = project_root / self.test_config

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            risk_config = config.get("risk", {})
            emergency_stop = risk_config.get("emergency_stop", {})

            if not emergency_stop.get("enabled", False):
                self.logger.error("緊急停止機能が無効化されています")
                return False

            # 保守的設定確認
            risk_per_trade = risk_config.get("risk_per_trade", 0)
            if risk_per_trade > 0.002:  # 0.2%以上は危険
                self.logger.error(f"リスク設定が過大です: {risk_per_trade}")
                return False

            self.logger.info("✅ リスク管理検証完了")
            return True

        except Exception as e:
            self.logger.error(f"リスク管理検証エラー: {e}")
            return False

    def execute_front_test(self) -> bool:
        """フロントテスト実行"""
        self.logger.info("🚀 1万円フロントテスト実行開始")
        self.logger.info(f"テスト期間: {self.start_time} ～ {self.end_time}")

        try:
            # フロントテスト用ファイル作成
            self._create_test_status_file()

            # メインプロセス実行
            cmd = [
                sys.executable,
                "-m",
                "crypto_bot.main",
                "live-bitbank",
                "--config",
                self.test_config,
            ]

            self.logger.info(f"実行コマンド: {' '.join(cmd)}")

            # プロセス開始
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=project_root,
            )

            # プロセス監視
            return self._monitor_test_process(process)

        except Exception as e:
            self.logger.error(f"フロントテスト実行エラー: {e}")
            return False

    def _create_test_status_file(self):
        """テスト用ステータスファイル作成"""
        status_file = project_root / "status_10k_test.json"

        initial_status = {
            "test_info": {
                "test_type": "10k_front_test",
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "config_used": self.test_config,
            },
            "last_updated": datetime.now().isoformat(),
            "system_status": "starting",
            "initial_balance": 10000.0,
            "current_balance": 10000.0,
            "total_trades": 0,
        }

        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(initial_status, f, indent=2, ensure_ascii=False)

        self.logger.info(f"テスト用ステータスファイル作成: {status_file}")

    def _monitor_test_process(self, process) -> bool:
        """テストプロセス監視"""
        self.logger.info("📡 テストプロセス監視開始")

        check_interval = 60  # 1分間隔で監視
        last_check = datetime.now()

        try:
            while datetime.now() < self.end_time:
                # プロセス状態確認
                if process.poll() is not None:
                    self.logger.error("プロセスが予期せず終了しました")
                    return False

                # 定期レポート生成
                if (datetime.now() - last_check).seconds >= check_interval:
                    self._generate_progress_report()
                    last_check = datetime.now()

                time.sleep(30)  # 30秒待機

            # テスト完了
            self.logger.info("✅ フロントテスト時間満了 - プロセス終了")
            process.terminate()

            # 最終レポート生成
            self._generate_final_report()

            return True

        except KeyboardInterrupt:
            self.logger.info("ユーザーによるテスト中断")
            process.terminate()
            return False

        except Exception as e:
            self.logger.error(f"プロセス監視エラー: {e}")
            process.terminate()
            return False

    def _generate_progress_report(self):
        """進捗レポート生成"""
        try:
            elapsed_time = datetime.now() - self.start_time
            remaining_time = self.end_time - datetime.now()

            status = self.integration_service.get_trading_status()

            self.logger.info("=" * 60)
            self.logger.info("📊 フロントテスト進捗レポート")
            self.logger.info("=" * 60)
            self.logger.info(f"経過時間: {elapsed_time}")
            self.logger.info(f"残り時間: {remaining_time}")
            self.logger.info(f"アクティブ取引数: {status.get('active_trades', 0)}")

            perf_summary = status.get("performance_summary", {})
            self.logger.info(f"総取引数: {perf_summary.get('total_trades', 0)}")
            self.logger.info(f"勝率: {perf_summary.get('win_rate', 0.0):.2%}")
            self.logger.info(f"純利益: ¥{perf_summary.get('net_profit', 0.0):.2f}")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"進捗レポート生成エラー: {e}")

    def _generate_final_report(self):
        """最終レポート生成"""
        try:
            final_report = self.integration_service.get_performance_report()

            # ファイル保存
            report_file = (
                project_root
                / f"front_test_final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )

            with open(report_file, "w", encoding="utf-8") as f:
                f.write(final_report)

            self.logger.info("🎯 最終レポート生成完了")
            self.logger.info(f"レポートファイル: {report_file}")
            self.logger.info("\n" + final_report)

        except Exception as e:
            self.logger.error(f"最終レポート生成エラー: {e}")


def main():
    """メイン実行"""
    print("🎯 1万円フロントテスト開始")
    print("=" * 80)

    manager = FrontTestManager()

    # 事前検証
    if not manager.pre_test_verification():
        print("❌ 事前検証失敗 - フロントテスト中止")
        sys.exit(1)

    # フロントテスト実行
    success = manager.execute_front_test()

    if success:
        print("✅ 1万円フロントテスト完了")
        sys.exit(0)
    else:
        print("❌ 1万円フロントテスト失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()
"""
1万円フロントテスト実行スクリプト
超保守的リスク設定での実資金テスト
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("/tmp/bitbank_10k_front_test.log"),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger(__name__)


def check_prerequisites():
    """前提条件チェック"""
    logger = logging.getLogger(__name__)

    # 環境変数チェック
    required_vars = ["BITBANK_API_KEY", "BITBANK_API_SECRET"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing environment variables: {missing_vars}")
        return False

    # 設定ファイルチェック
    config_path = (
        Path(__file__).parent.parent
        / "config"
        / "development"
        / "bitbank_10k_front_test.yml"
    )
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        return False

    logger.info("All prerequisites satisfied")
    return True


def create_test_status_file():
    """テスト状況ファイル作成"""
    status_data = {
        "test_start_time": datetime.now().isoformat(),
        "test_duration_hours": 24,
        "test_end_time": (datetime.now() + timedelta(hours=24)).isoformat(),
        "max_portfolio_value": 10000,
        "risk_per_trade": 0.001,
        "max_daily_trades": 5,
        "emergency_stop_enabled": True,
        "status": "starting",
        "trades_executed": 0,
        "current_pnl": 0.0,
        "max_drawdown": 0.0,
        "emergency_stops_triggered": 0,
        "notes": "1万円フロントテスト - 超保守的リスク設定",
    }

    status_path = Path("/tmp/status_10k_test.json")
    with open(status_path, "w") as f:
        json.dump(status_data, f, indent=2)

    print(f"Test status file created: {status_path}")
    return status_path


def display_test_summary():
    """テスト概要表示"""
    print("\n" + "=" * 60)
    print("🚀 1万円フロントテスト開始")
    print("=" * 60)
    print("テスト設定:")
    print("  - 最大ポートフォリオ価値: 1万円")
    print("  - 1取引あたりリスク: 0.1%")
    print("  - 最大注文サイズ: 0.0001 BTC")
    print("  - 1日最大取引数: 5回")
    print("  - テスト期間: 24時間")
    print("  - 緊急停止機能: 有効")
    print("  - 連続損失上限: 3回")
    print("  - 日次最大損失: 2%")
    print("  - 最大ドローダウン: 5%")
    print("\n安全機能:")
    print("  - 超保守的リスク設定")
    print("  - 最小注文サイズ固定")
    print("  - 複数の緊急停止条件")
    print("  - リアルタイム監視")
    print("  - 詳細ログ記録")
    print("=" * 60)


def confirm_test_execution():
    """テスト実行確認"""
    print("\n⚠️  実資金を使用したテストを開始します。")
    print("このテストは最大1万円の実資金を使用します。")
    print("極めて保守的な設定ですが、実際の損失が発生する可能性があります。")

    response = input("\n続行しますか？ (yes/no): ").strip().lower()
    return response == "yes"


def main():
    """メイン処理"""
    logger = setup_logging()

    try:
        # テスト概要表示
        display_test_summary()

        # ユーザー確認
        if not confirm_test_execution():
            print("テストをキャンセルしました。")
            return

        # 前提条件チェック
        if not check_prerequisites():
            print("前提条件が満たされていません。テストを中止します。")
            return

        # テスト状況ファイル作成
        status_path = create_test_status_file()

        # テスト実行
        print("\n🚀 1万円フロントテストを開始します...")
        print("Ctrl+Cでテストを停止できます。")

        # 実際のトレーディングボット実行
        config_path = (
            Path(__file__).parent.parent
            / "config"
            / "development"
            / "bitbank_10k_front_test.yml"
        )
        cmd = f"python -m crypto_bot.main live-bitbank --config {config_path}"

        logger.info(f"Executing command: {cmd}")
        print(f"\n実行コマンド: {cmd}")

        # 実行前に5秒待機
        for i in range(5, 0, -1):
            print(f"開始まで {i} 秒...")
            time.sleep(1)

        # 実際の実行
        os.system(cmd)

    except KeyboardInterrupt:
        print("\n\nテストが中断されました。")
        logger.info("Test interrupted by user")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        logger.error(f"Error in main: {e}")
    finally:
        print("\nテストを終了します。")
        logger.info("Test completed")


if __name__ == "__main__":
    main()
