"""
ペーパートレードランナー - Phase 38.4完了版

orchestrator.pyから分離したペーパートレード実行機能。
ペーパートレードモードの専用処理・セッション管理を担当。

Phase 28-29最適化: ペーパートレードモード専用処理・レポート生成確立
Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了
"""

import asyncio
from datetime import datetime

from ..config import get_threshold
from .base_runner import BaseRunner


class PaperTradingRunner(BaseRunner):
    """ペーパートレードモード実行クラス"""

    def __init__(self, orchestrator_ref, logger):
        """
        ペーパートレードランナー初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        super().__init__(orchestrator_ref, logger)
        self.session_start = None
        self.cycle_count = 0
        self.session_stats = {}

    async def run(self) -> bool:
        """
        ペーパートレードモード実行

        Returns:
            実行成功・失敗
        """
        try:
            self.logger.info("📝 ペーパートレードモード開始")

            # セッション開始
            self.session_start = datetime.now()
            self.cycle_count = 0

            # 定期的な取引サイクル実行
            await self._run_continuous_trading()

            return True

        except KeyboardInterrupt:
            # 終了時にもレポート生成
            await self._generate_final_report()
            self.logger.info("📝 ペーパートレード終了・最終レポート保存完了")
            raise

        except Exception as e:
            self.logger.error(f"❌ ペーパートレード実行エラー: {e}", discord_notify=True)
            await self._save_error_report(str(e))
            raise

    async def _run_continuous_trading(self):
        """連続取引実行"""
        try:
            while True:
                # 取引サイクル実行
                await self._execute_trading_cycle()
                self.cycle_count += 1

                # 定期レポート生成（Phase 22: ハードコード排除）
                report_interval = get_threshold("execution.paper_report_interval", 10)
                if self.cycle_count % report_interval == 0:
                    await self._generate_periodic_report()

                # ペーパートレード実行間隔（外部化）
                interval = get_threshold("execution.paper_mode_interval_seconds", 60)
                await asyncio.sleep(interval)

        except Exception as e:
            self.logger.error(f"❌ 連続取引実行エラー: {e}")
            raise

    async def _execute_trading_cycle(self):
        """取引サイクル実行"""
        try:
            await self.orchestrator.run_trading_cycle()

        except Exception as e:
            self.logger.error(f"❌ 取引サイクル実行エラー: {e}")
            raise

    async def _generate_periodic_report(self):
        """定期レポート生成"""
        try:
            # セッション統計収集
            session_stats = self._collect_session_stats()

            # レポート保存（Phase 22 ハードコード排除対応）
            await self.orchestrator.paper_trading_reporter.generate_session_report(session_stats)

        except Exception as e:
            self.logger.error(f"❌ 定期レポート生成エラー: {e}")
            raise

    async def _generate_final_report(self):
        """最終レポート生成"""
        try:
            final_stats = {
                "start_time": self.session_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cycles_completed": self.cycle_count,
                "total_signals": getattr(self.orchestrator.execution_service, "total_signals", 0),
                "executed_trades": getattr(
                    self.orchestrator.execution_service, "executed_trades", 0
                ),
                "current_balance": getattr(
                    self.orchestrator.execution_service,
                    "current_balance",
                    get_threshold("execution.default_balance_jpy", 1000000),
                ),
                "session_pnl": getattr(self.orchestrator.execution_service, "session_pnl", 0),
                "recent_trades": getattr(self.orchestrator.execution_service, "recent_trades", []),
            }

            await self.orchestrator.paper_trading_reporter.generate_session_report(final_stats)

        except Exception as e:
            self.logger.error(f"❌ 最終レポート生成エラー: {e}")
            raise

    def _collect_session_stats(self) -> dict:
        """セッション統計収集"""
        return {
            "start_time": self.session_start.strftime("%Y-%m-%d %H:%M:%S"),
            "cycles_completed": self.cycle_count,
            "total_signals": getattr(self.orchestrator.execution_service, "total_signals", 0),
            "executed_trades": getattr(self.orchestrator.execution_service, "executed_trades", 0),
            "current_balance": getattr(
                self.orchestrator.execution_service,
                "current_balance",
                get_threshold("execution.default_balance_jpy", 1000000),
            ),  # デフォルト値を設定から取得
            "session_pnl": getattr(self.orchestrator.execution_service, "session_pnl", 0),
            "recent_trades": getattr(self.orchestrator.execution_service, "recent_trades", []),
        }

    async def _save_error_report(self, error_message: str):
        """エラーレポート保存"""
        try:
            session_stats = self._collect_session_stats() if self.session_start else None

            await self.orchestrator.paper_trading_reporter.save_session_error_report(
                error_message, session_stats
            )

        except Exception as e:
            self.logger.error(f"❌ ペーパートレードエラーレポート保存失敗: {e}")

    async def _cleanup_resources(self):
        """リソースクリーンアップ（オーバーライド）"""
        try:
            await super()._cleanup_resources()

            # ペーパートレード固有のクリーンアップ
            self.session_start = None
            self.cycle_count = 0
            self.session_stats = {}

            self.logger.info("🧹 ペーパートレードリソースクリーンアップ完了")

        except Exception as e:
            self.logger.error(f"❌ ペーパートレードリソースクリーンアップエラー: {e}")

    async def _save_final_statistics(self):
        """最終統計保存（オーバーライド）"""
        try:
            final_stats = {
                "mode": "paper_trading",
                "session_duration": {
                    "start": (
                        self.session_start.strftime("%Y-%m-%d %H:%M:%S")
                        if self.session_start
                        else "N/A"
                    ),
                    "end": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                "performance": {
                    "cycles_completed": self.cycle_count,
                    "total_signals": getattr(
                        self.orchestrator.execution_service, "total_signals", 0
                    ),
                    "executed_trades": getattr(
                        self.orchestrator.execution_service, "executed_trades", 0
                    ),
                    "session_pnl": getattr(self.orchestrator.execution_service, "session_pnl", 0),
                },
                "completion_status": "completed",
            }

            self.logger.info("📊 ペーパートレード最終統計", extra_data=final_stats)

        except Exception as e:
            self.logger.error(f"❌ ペーパートレード最終統計保存エラー: {e}")
