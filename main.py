"""
暗号資産取引Bot - エントリーポイント

Phase 52.4-B完了・6戦略55特徴量システム対応の薄いエントリーポイント。
具体的なビジネスロジックはTradingOrchestratorに委譲し、
ここでは引数解析と基本設定のみを担当。

Phase 52.4-B完了成果:
- コード品質改善（Phase参照統一67%削減・ハードコード値削減）
- 6戦略55特徴量システム（ATRBased・DonchianChannel・ADXTrendStrength・BBReversal・StochasticReversal・MACDEMACrossover）
- 真の3クラス分類ML（BUY/SELL/HOLD・F1改善+9.7%）
- Registry Pattern動的戦略管理（影響範囲93%削減）

設計原則:
- エントリーポイント特化（薄い設計）
- ビジネスロジックはsrc/core/orchestration/に委譲
- テスト不要なレベルまで薄く設計
- 保守性とシンプルさの両立
"""

import argparse
import asyncio
import fcntl
import os
import signal
import sys
import time
from pathlib import Path

# srcディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

# .env環境変数の読み込み（python-dotenv不要版）
env_path = Path(__file__).parent / "config/secrets/.env"
if env_path.exists():
    print(f"✅ 環境変数読み込み: {env_path}")

    # .envファイルから直接読み込んで環境変数に設定
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    try:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
                    except ValueError:
                        print(f"⚠️ 環境変数解析エラー (行{line_no}): {line}")
    except Exception as e:
        print(f"❌ .envファイル読み込みエラー: {e}")

    # 重要な環境変数の設定確認
    required_vars = ["BITBANK_API_KEY", "BITBANK_API_SECRET", "DISCORD_WEBHOOK_URL"]
    for var in required_vars:
        if var in os.environ and os.environ[var]:
            print(f"✅ {var}: 設定済み（{len(os.environ[var])}文字）")
        else:
            print(f"⚠️ {var}: 未設定または空")
else:
    print("⚠️ .envファイルが見つかりません（オプション）")

try:
    from src.core.config import load_config
    from src.core.logger import setup_logging
    from src.core.orchestration import create_trading_orchestrator
    from src.core.services import GracefulShutdownManager
except ImportError as e:
    print(f"❌ 必要なモジュールのインポートに失敗: {e}")
    print("srcディレクトリの構造を確認してください。")
    sys.exit(1)


def setup_process_management():
    """
    プロセス管理機能の初期化

    機能:
    - プロセス重複防止
    - 環境変数による実行制御
    - 自動タイムアウト設定（GCP環境）
    - シグナルハンドリング
    """
    # 1. プロセス重複防止
    if not check_single_instance():
        print("❌ 既に実行中のプロセスが存在します")
        sys.exit(1)

    # 2. 環境変数による実行制御
    environment = detect_environment()
    print(f"🌍 実行環境: {environment}")

    # 3. GCP環境での自動タイムアウト設定
    if environment == "gcp":
        setup_auto_shutdown()

    # 4. シグナルハンドリング設定
    setup_signal_handlers()

    return environment


def check_single_instance():
    """
    プロセスの重複起動防止

    Returns:
        bool: 実行可否（True=実行可能、False=重複）
    """
    # ユーザー固有のロックファイル名
    lock_file_path = Path(f"/tmp/crypto_bot_{os.getenv('USER', 'default')}.lock")

    try:
        # ロックファイルを開く
        lock_file = open(lock_file_path, "w")

        # 排他ロック試行（非ブロッキング）
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # プロセス情報書き込み
        lock_file.write(f"{os.getpid()}\n{time.time()}\n")
        lock_file.flush()

        print(f"✅ プロセスロック取得: {lock_file_path}")

        # ロックファイルオブジェクトを保持（プロセス終了時に自動解除）
        # グローバル変数として保持しないとGCで削除される可能性
        globals()["_lock_file"] = lock_file

        return True

    except (OSError, IOError):
        print(f"🔒 他のプロセスが実行中: {lock_file_path}")
        return False


def detect_environment():
    """
    実行環境の自動検出

    Returns:
        str: 環境名（"local" | "gcp"）
    """
    # GCP環境の判定
    gcp_indicators = [
        os.getenv("RUNNING_ON_GCP") == "true",
        os.getenv("K_SERVICE") is not None,  # Cloud Run
        os.getenv("GOOGLE_CLOUD_PROJECT") is not None,
        Path("/var/secrets/google").exists(),  # Cloud Run secrets
    ]

    if any(gcp_indicators):
        return "gcp"
    else:
        return "local"


def setup_auto_shutdown():
    """
    GCP環境での自動シャットダウン設定
    """
    # 15分（900秒）でタイムアウト
    timeout_seconds = 900

    def timeout_handler(signum, frame):
        print(f"⏰ タイムアウト（{timeout_seconds}秒）によりシステムを終了します")
        sys.exit(1)  # Phase 53.6: 再起動促進・Logger競合回避

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    print(f"⏰ 自動タイムアウト設定: {timeout_seconds}秒")


def setup_signal_handlers():
    """
    シグナルハンドリング設定（基本設定のみ）

    Note: Graceful shutdown処理はGracefulShutdownManagerに委譲
    """

    def signal_handler(signum, frame):
        signal_name = signal.Signals(signum).name
        print(f"🛑 シグナル受信: {signal_name} - 正常終了中...")
        sys.exit(0)

    # SIGINT（Ctrl+C）とSIGTERM（kill）の処理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def parse_arguments():
    """コマンドライン引数解析"""
    parser = argparse.ArgumentParser(
        description="暗号資産取引Bot - Phase 52.4-B完了・6戦略55特徴量システム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py --mode paper              # ペーパートレード（デフォルト）
  python main.py --mode live               # ライブトレード
  python main.py --mode backtest           # バックテスト
  python main.py --config config/core/unified.yaml # 統一設定使用
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["backtest", "paper", "live"],
        default="paper",
        help="動作モード (default: paper)",
    )
    parser.add_argument(
        "--config",
        default="config/core/unified.yaml",
        help="設定ファイルパス (default: config/core/unified.yaml)",
    )

    return parser.parse_args()


async def main():
    """メイン処理 - エントリーポイント（GracefulShutdownManager使用）"""
    # 0. プロセス管理初期化
    environment = setup_process_management()

    # 1. 引数解析
    args = parse_arguments()

    # 2. 基本設定読み込み（モード設定一元化対応）
    try:
        config = load_config(args.config, cmdline_mode=args.mode)

        # バックテストモード時の最適化設定（Phase 52.4-B完了）
        if config.mode == "backtest":
            # thresholds.yamlからログレベルを取得（動的設定対応）
            from src.core.config.threshold_manager import get_threshold

            log_level = get_threshold("backtest.log_level", "ERROR")

            # 環境変数でログレベルを制御（全コンポーネントに影響）
            os.environ["LOG_LEVEL"] = log_level
            os.environ["BACKTEST_MODE"] = "true"
            print(f"🎯 バックテストモード検出: ログレベル{log_level}、API呼び出しモック化")

            # グローバルフラグ設定（全コンポーネントで参照可能）
            from src.core.config import set_backtest_mode, set_backtest_log_level

            set_backtest_mode(True)
            set_backtest_log_level(log_level)

        logger = setup_logging("crypto_bot")
    except Exception as e:
        print(f"❌ 基本設定エラー: {e}")
        sys.exit(1)

    # 3. TradingOrchestratorに実行を委譲
    try:
        logger.info(
            f"🚀 暗号資産取引Bot Phase 52.4-B完了・6戦略55特徴量システム 起動 - モード: {config.mode.upper()}"
        )

        # 依存性組み立て済みOrchestratorを取得
        orchestrator = await create_trading_orchestrator(config, logger)

        # 初期化確認
        if not await orchestrator.initialize():
            logger.error("システム初期化失敗")
            sys.exit(1)

        # GracefulShutdownManager初期化・シグナルハンドリング設定
        shutdown_manager = GracefulShutdownManager(logger)
        shutdown_manager.initialize(orchestrator)

        # メイン処理とshutdown監視を並行実行
        main_task = asyncio.create_task(orchestrator.run())
        await shutdown_manager.shutdown_with_main_task(main_task)

    except KeyboardInterrupt:
        logger.info("ユーザーによる終了要求を受信")
    except Exception as e:
        logger.error(f"実行エラー: {e}", discord_notify=True)
        sys.exit(1)

    logger.info("システム終了")


if __name__ == "__main__":
    # Windows環境対応
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 実行
    asyncio.run(main())
