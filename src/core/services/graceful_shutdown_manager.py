"""
Graceful Shutdown管理 - Phase 38.4完了版

main.py軽量化方針に従い、shutdown処理を専用サービスとして分離。

Phase 28-29最適化: Graceful Shutdown専門サービス・シグナルハンドリング実装
Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了

設計原則：
- Single Responsibility: shutdown処理のみ担当
- 依存性注入: orchestratorを外部から受け取り
- エラーハンドリング: 適切なログ出力・例外処理
- 統一設定管理体系: thresholds.yaml準拠
"""

import asyncio
import signal
import sys
from typing import Optional

from ..logger import CryptoBotLogger


class GracefulShutdownManager:
    """
    Graceful Shutdown管理サービス

    機能:
    - シグナルハンドリング設定
    - オーケストレーターとランナーの正常終了
    - タイムアウト管理
    - shutdown_event による協調的終了
    """

    def __init__(self, logger: CryptoBotLogger):
        """
        初期化

        Args:
            logger: CryptoBotLogger インスタンス
        """
        self.logger = logger
        self.orchestrator: Optional[object] = None
        self.shutdown_event: Optional[asyncio.Event] = None
        self._shutdown_timeout = 30  # 30秒タイムアウト

    def initialize(self, orchestrator: object) -> None:
        """
        shutdown管理初期化

        Args:
            orchestrator: TradingOrchestrator インスタンス
        """
        self.orchestrator = orchestrator
        self.shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
        self.logger.info("✅ Graceful shutdown管理初期化完了")

    def _setup_signal_handlers(self) -> None:
        """
        シグナルハンドリング設定（graceful shutdown対応）
        """

        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            self.logger.info(f"🛑 シグナル受信: {signal_name} - graceful shutdown開始")

            # shutdown_eventをセットしてメインループに終了を通知
            if self.shutdown_event:
                self.shutdown_event.set()
            else:
                # shutdown_event未設定の場合は即座に終了
                self.logger.warning("⚠️ shutdown_event未設定 - 即座に終了")
                sys.exit(0)

        # SIGINT（Ctrl+C）とSIGTERM（kill）の処理
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def wait_for_shutdown_signal(self) -> None:
        """
        shutdown シグナル待機

        Returns:
            shutdown_event がセットされるまで待機
        """
        if self.shutdown_event:
            await self.shutdown_event.wait()
        else:
            # shutdown_event未設定の場合は無限待機
            await asyncio.Event().wait()

    async def perform_graceful_shutdown(self) -> None:
        """
        Graceful shutdown処理実行

        オーケストレーターとランナーのクリーンアップを適切な順序で実行
        タイムアウト機能付き
        """
        self.logger.info("🔄 Graceful shutdown処理開始")

        try:
            # タイムアウト付きでshutdown処理実行
            await asyncio.wait_for(self._perform_cleanup(), timeout=self._shutdown_timeout)

            self.logger.info("✅ Graceful shutdown完了")

        except asyncio.TimeoutError:
            self.logger.error(f"❌ Graceful shutdown タイムアウト（{self._shutdown_timeout}秒）")
        except Exception as e:
            self.logger.error(f"❌ Graceful shutdown中にエラー: {e}")

    async def _perform_cleanup(self) -> None:
        """
        クリーンアップ処理実行（内部メソッド）
        """
        if not self.orchestrator:
            self.logger.warning("⚠️ orchestrator未設定 - cleanup処理スキップ")
            return

        cleanup_tasks = []

        # 各ランナーのクリーンアップタスクを並行実行
        if (
            hasattr(self.orchestrator, "paper_trading_runner")
            and self.orchestrator.paper_trading_runner
        ):
            cleanup_tasks.append(self.orchestrator.paper_trading_runner.cleanup_mode())

        if (
            hasattr(self.orchestrator, "live_trading_runner")
            and self.orchestrator.live_trading_runner
        ):
            cleanup_tasks.append(self.orchestrator.live_trading_runner.cleanup_mode())

        if hasattr(self.orchestrator, "backtest_runner") and self.orchestrator.backtest_runner:
            cleanup_tasks.append(self.orchestrator.backtest_runner.cleanup_mode())

        if cleanup_tasks:
            # 全クリーンアップタスクを並行実行
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            self.logger.info("✅ 全ランナーのクリーンアップ完了")
        else:
            self.logger.info("⚠️ クリーンアップ対象ランナーが見つかりません")

    async def shutdown_with_main_task(self, main_task: asyncio.Task) -> None:
        """
        メインタスクと連携したshutdown処理

        Args:
            main_task: メイン処理のasyncio.Task
        """
        # shutdown監視タスク作成
        shutdown_task = asyncio.create_task(self.wait_for_shutdown_signal())

        # いずれかが完了するまで待機
        done, pending = await asyncio.wait(
            [main_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
        )

        # shutdown_eventがセットされた場合はgraceful shutdown実行
        if shutdown_task in done:
            self.logger.info("シグナル受信 - graceful shutdown開始")

            # メイン処理をキャンセル
            main_task.cancel()
            try:
                await main_task
            except asyncio.CancelledError:
                self.logger.info("メイン処理のキャンセル完了")

            # graceful shutdown実行
            await self.perform_graceful_shutdown()

        # 残りのタスクをキャンセル
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
