"""
暗号資産取引Bot - エントリーポイント

Phase 22完了版・設定最適化完了・統一システム最適化対応の薄いエントリーポイント。
具体的なビジネスロジックはTradingOrchestratorに委譲し、
ここでは引数解析と基本設定のみを担当。

設計原則:
- エントリーポイント特化（120行以内）
- ビジネスロジックはsrc/core/orchestration/に委譲
- テスト不要なレベルまで薄く設計・625テスト対応
- 保守性とシンプルさの両立・設定最適化完了対応
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

# .env環境変数の読み込み（優先順位: .env > 環境変数）
try:
    from dotenv import load_dotenv
    # config/secrets/.envファイルを読み込み（Discord Webhook URL等）
    env_path = Path(__file__).parent / "config/secrets/.env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 環境変数読み込み: {env_path}")
    else:
        print("⚠️ .envファイルが見つかりません（オプション）")
except ImportError:
    print("⚠️ python-dotenvが利用できません（オプション）")

try:
    from src.core.config import load_config
    from src.core.logger import setup_logging
    from src.core.orchestration import create_trading_orchestrator
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
        lock_file = open(lock_file_path, 'w')

        # 排他ロック試行（非ブロッキング）
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        # プロセス情報書き込み
        lock_file.write(f"{os.getpid()}\n{time.time()}\n")
        lock_file.flush()

        print(f"✅ プロセスロック取得: {lock_file_path}")

        # ロックファイルオブジェクトを保持（プロセス終了時に自動解除）
        # グローバル変数として保持しないとGCで削除される可能性
        globals()['_lock_file'] = lock_file

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
        sys.exit(0)

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    print(f"⏰ 自動タイムアウト設定: {timeout_seconds}秒")


def setup_signal_handlers():
    """
    シグナルハンドリング設定
    """
    def signal_handler(signum, frame):
        signal_name = signal.Signals(signum).name
        print(f"🛑 シグナル受信: {signal_name} - 正常終了中...")

        # ログ出力（logger初期化前の場合はprint）
        try:
            import logging
            logger = logging.getLogger("crypto_bot")
            logger.info(f"シグナル受信により終了: {signal_name}")
        except:
            pass

        sys.exit(0)

    # SIGINT（Ctrl+C）とSIGTERM（kill）の処理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def parse_arguments():
    """コマンドライン引数解析"""
    parser = argparse.ArgumentParser(
        description="暗号資産取引Bot - Phase 22完了版・設定最適化完了・統一システム最適化",
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
        "--config", default="config/core/unified.yaml", help="設定ファイルパス (default: config/core/unified.yaml)"
    )

    return parser.parse_args()


async def main():
    """メイン処理 - エントリーポイント"""
    # 0. プロセス管理初期化
    environment = setup_process_management()

    # 1. 引数解析
    args = parse_arguments()

    # 2. 基本設定読み込み（モード設定一元化対応）
    try:
        config = load_config(args.config, cmdline_mode=args.mode)
        logger = setup_logging("crypto_bot")
    except Exception as e:
        print(f"❌ 基本設定エラー: {e}")
        sys.exit(1)

    # 3. TradingOrchestratorに実行を委譲
    try:
        logger.info(f"🚀 暗号資産取引Bot v22.0・設定最適化完了・統一システム最適化 起動 - モード: {config.mode.upper()}")

        # 依存性組み立て済みOrchestratorを取得
        orchestrator = await create_trading_orchestrator(config, logger)

        # 初期化確認
        if not await orchestrator.initialize():
            logger.error("システム初期化失敗")
            sys.exit(1)

        # 実行（モードはConfigから自動取得）
        await orchestrator.run()

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
