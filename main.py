"""
暗号資産取引Bot - エントリーポイント

Phase 1-13統合版・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応の薄いエントリーポイント。
具体的なビジネスロジックはTradingOrchestratorに委譲し、
ここでは引数解析と基本設定のみを担当。

設計原則:
- エントリーポイント特化（60行以内）
- ビジネスロジックはsrc/core/orchestrator.pyに委譲・GitHub Actions対応
- テスト不要なレベルまで薄く設計・CI/CDワークフロー最適化対応
- 保守性とシンプルさの両立・手動実行監視・段階的デプロイ対応
"""

import argparse
import asyncio
import sys
from pathlib import Path

# srcディレクトリをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.core.config import load_config
    from src.core.logger import setup_logging
    from src.core.orchestrator import create_trading_orchestrator
except ImportError as e:
    print(f"❌ 必要なモジュールのインポートに失敗: {e}")
    print("srcディレクトリの構造を確認してください。")
    sys.exit(1)


def parse_arguments():
    """コマンドライン引数解析"""
    parser = argparse.ArgumentParser(
        description="暗号資産取引Bot - Phase 1-13統合版・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python main.py --mode paper              # ペーパートレード（デフォルト）
  python main.py --mode live               # ライブトレード
  python main.py --mode backtest           # バックテスト（Phase 13完了・CI/CDワークフロー最適化対応）
  python main.py --config config/prod.yaml # 本番設定使用
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["backtest", "paper", "live"],
        default="paper",
        help="動作モード (default: paper)",
    )
    parser.add_argument(
        "--config", default="config/core/base.yaml", help="設定ファイルパス (default: config/core/base.yaml)"
    )

    return parser.parse_args()


async def main():
    """メイン処理 - エントリーポイント"""
    # 1. 引数解析
    args = parse_arguments()

    # 2. 基本設定読み込み
    try:
        config = load_config(args.config)
        logger = setup_logging("crypto_bot")
    except Exception as e:
        print(f"❌ 基本設定エラー: {e}")
        sys.exit(1)

    # 3. TradingOrchestratorに実行を委譲
    try:
        logger.info(f"🚀 暗号資産取引Bot v13.0・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応 起動 - モード: {args.mode.upper()}")

        # 依存性組み立て済みOrchestratorを取得
        orchestrator = await create_trading_orchestrator(config, logger)

        # 初期化確認
        if not await orchestrator.initialize():
            logger.error("システム初期化失敗")
            sys.exit(1)

        # 実行
        await orchestrator.run(args.mode)

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
