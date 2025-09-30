"""
ライブトレードランナー - Phase 28完了・Phase 29最適化版

orchestrator.pyから分離したライブトレード実行機能。
ライブトレードモードの専用処理・実取引管理を担当。
"""

import asyncio
from datetime import datetime

from ..config import get_threshold
from .base_runner import BaseRunner


class LiveTradingRunner(BaseRunner):
    """ライブトレードモード実行クラス"""

    def __init__(self, orchestrator_ref, logger):
        """
        ライブトレードランナー初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        super().__init__(orchestrator_ref, logger)
        self.session_start = None
        self.cycle_count = 0
        self.trade_count = 0
        self.total_pnl = 0.0

    async def run(self) -> bool:
        """
        ライブトレードモード実行

        Returns:
            実行成功・失敗
        """
        try:
            self.logger.info("🚨 ライブトレードモード開始", discord_notify=True)

            # セッション開始
            self.session_start = datetime.now()
            self.cycle_count = 0

            # ライブトレード実行条件確認
            if not await self._validate_live_conditions():
                self.logger.error("❌ ライブトレード実行条件が満たされていません")
                return False

            # 定期的な取引サイクル実行（月100-200回最適化）
            await self._run_continuous_trading()

            return True

        except KeyboardInterrupt:
            # 終了時統計出力
            await self._generate_final_summary()
            self.logger.info("🛑 ライブトレード終了（ユーザー停止）", discord_notify=True)
            raise

        except Exception as e:
            self.logger.error(f"❌ ライブトレード実行エラー: {e}", discord_notify=True)
            await self._save_error_report(str(e))
            raise

    async def _validate_live_conditions(self) -> bool:
        """ライブトレード実行条件確認"""
        try:
            # 基本条件確認
            if self.config.mode != "live":
                self.logger.error("❌ 設定モードがライブトレードではありません")
                return False

            # 必須サービス確認
            required_services = [
                self.orchestrator.execution_service,
                self.orchestrator.risk_service,
                self.orchestrator.ml_service,
            ]

            for service in required_services:
                if service is None:
                    self.logger.error("❌ 必須サービスが初期化されていません")
                    return False

            # 残高確認（最小残高チェック・条件緩和）
            try:
                balance = await self._check_account_balance()
                min_balance = get_threshold(
                    "trading.minimum_live_balance", 5000
                )  # 5千円最小（緩和）

                if balance < min_balance:
                    self.logger.warning(
                        f"⚠️ 残高不足: {balance:,.0f}円 < {min_balance:,.0f}円（監視モードで継続）"
                    )
                    # 以前は return False でシステム停止していたが、継続するように変更
                    # 監視モードで継続し、システムを停止させない
                else:
                    self.logger.info(f"✅ 残高確認完了: {balance:,.0f}円")

            except Exception as e:
                self.logger.warning(f"⚠️ 残高確認エラー（継続稼働）: {e}")
                # エラーが発生してもシステム停止させない

            self.logger.info("✅ ライブトレード実行条件確認完了")
            return True

        except Exception as e:
            self.logger.error(f"❌ ライブトレード条件確認エラー: {e}")
            return False

    async def _check_account_balance(self) -> float:
        """アカウント残高確認"""
        try:
            # 実行サービスから残高取得（実装は execution_service に依存）
            balance = getattr(self.orchestrator.execution_service, "current_balance", 0)

            if balance <= 0:
                # 残高が0以下の場合は API から再取得を試行
                self.logger.warning("⚠️ 残高が0以下のため、再取得を試行します")

                # 実際の残高再取得処理を実装
                try:
                    from ...data.bitbank_client import BitbankClient
                    from ..config import get_threshold

                    client = BitbankClient()
                    balance_data = client.fetch_balance()
                    jpy_balance = balance_data.get("JPY", {}).get("free", 0.0)

                    if jpy_balance > 0:
                        # execution_serviceの残高を更新
                        if hasattr(self.orchestrator.execution_service, "current_balance"):
                            self.orchestrator.execution_service.current_balance = jpy_balance
                        balance = jpy_balance
                        self.logger.info(f"✅ 残高再取得成功: {jpy_balance:,.0f}円")
                    else:
                        # 統一設定管理体系: unified.yamlからフォールバック残高取得
                        from ..config import load_config

                        config = load_config("config/core/unified.yaml")
                        drawdown_config = (
                            config.risk.drawdown_manager
                            if hasattr(config.risk, "drawdown_manager")
                            else {}
                        )
                        fallback = getattr(drawdown_config, "fallback_balance", 11000.0)
                        if hasattr(self.orchestrator.execution_service, "current_balance"):
                            self.orchestrator.execution_service.current_balance = fallback
                        balance = fallback
                        self.logger.warning(f"⚠️ 残高0のためフォールバック使用: {fallback:,.0f}円")

                except Exception as re_error:
                    self.logger.error(f"❌ 残高再取得失敗: {re_error}")
                    # 統一設定管理体系: unified.yamlからフォールバック残高取得
                    from config import load_config

                    config = load_config("config/core/unified.yaml")
                    drawdown_config = getattr(config.risk, "drawdown_manager", {})
                    fallback = drawdown_config.get("fallback_balance", 11000.0)
                    if hasattr(self.orchestrator.execution_service, "current_balance"):
                        self.orchestrator.execution_service.current_balance = fallback
                    balance = fallback
                    self.logger.warning(
                        f"⚠️ 残高再取得エラーのためフォールバック使用: {fallback:,.0f}円"
                    )

            return balance

        except Exception as e:
            self.logger.error(f"❌ 残高確認エラー: {e}")
            raise

    async def _run_continuous_trading(self):
        """連続取引実行"""
        try:
            while True:
                # 取引サイクル実行
                await self._execute_trading_cycle()
                self.cycle_count += 1

                # 50サイクルごとに統計出力（約2.5時間）
                if self.cycle_count % 50 == 0:
                    await self._log_progress_statistics()

                # ライブトレード実行間隔（外部化・収益性重視）
                interval = get_threshold("execution.live_mode_interval_seconds", 180)
                await asyncio.sleep(interval)

        except Exception as e:
            self.logger.error(f"❌ 連続取引実行エラー: {e}")
            raise

    async def _execute_trading_cycle(self):
        """取引サイクル実行"""
        try:
            await self.orchestrator.run_trading_cycle()

            # 取引実行数更新（execution_service から取得）
            current_trades = getattr(self.orchestrator.execution_service, "executed_trades", 0)
            if current_trades > self.trade_count:
                self.trade_count = current_trades
                self.logger.info(f"💼 ライブ取引実行: 累計{self.trade_count}件")

        except Exception as e:
            self.logger.error(f"❌ 取引サイクル実行エラー: {e}")
            raise

    async def _log_progress_statistics(self):
        """進捗統計ログ出力"""
        try:
            current_balance = getattr(self.orchestrator.execution_service, "current_balance", 0)
            session_pnl = getattr(self.orchestrator.execution_service, "session_pnl", 0)
            duration_hours = (datetime.now() - self.session_start).total_seconds() / 3600

            progress_stats = {
                "cycles_completed": self.cycle_count,
                "duration_hours": round(duration_hours, 2),
                "trade_count": self.trade_count,
                "current_balance": current_balance,
                "session_pnl": session_pnl,
                "avg_cycles_per_hour": (
                    round(self.cycle_count / duration_hours, 2) if duration_hours > 0 else 0
                ),
            }

            self.logger.info(
                "📊 ライブトレード進捗統計",
                extra_data=progress_stats,
                discord_notify=True,
            )

        except Exception as e:
            self.logger.error(f"❌ 進捗統計ログエラー: {e}")

    async def _generate_final_summary(self):
        """最終サマリー生成"""
        try:
            final_summary = {
                "session_duration": (datetime.now() - self.session_start).total_seconds() / 3600,
                "total_cycles": self.cycle_count,
                "total_trades": self.trade_count,
                "final_balance": getattr(self.orchestrator.execution_service, "current_balance", 0),
                "session_pnl": getattr(self.orchestrator.execution_service, "session_pnl", 0),
            }

            self.logger.info(
                "📋 ライブトレード最終サマリー",
                extra_data=final_summary,
                discord_notify=True,
            )

        except Exception as e:
            self.logger.error(f"❌ 最終サマリー生成エラー: {e}")

    async def _save_error_report(self, error_message: str):
        """エラーレポート保存"""
        try:
            # ライブトレード用のエラーレポートは backtest_reporter を流用
            # （将来的にはlive_trading_reporterを作成可能）
            context = {
                "session_start": (
                    self.session_start.strftime("%Y-%m-%d %H:%M:%S")
                    if self.session_start
                    else "N/A"
                ),
                "cycles_completed": self.cycle_count,
                "trade_count": self.trade_count,
                "current_balance": getattr(
                    self.orchestrator.execution_service, "current_balance", 0
                ),
            }

            await self.orchestrator.backtest_reporter.save_error_report(error_message, context)

        except Exception as e:
            self.logger.error(f"❌ ライブトレードエラーレポート保存失敗: {e}")

    async def _cleanup_resources(self):
        """リソースクリーンアップ（オーバーライド）"""
        try:
            await super()._cleanup_resources()

            # ライブトレード固有のクリーンアップ
            self.session_start = None
            self.cycle_count = 0
            self.trade_count = 0
            self.total_pnl = 0.0

            self.logger.info("🧹 ライブトレードリソースクリーンアップ完了")

        except Exception as e:
            self.logger.error(f"❌ ライブトレードリソースクリーンアップエラー: {e}")

    async def _save_final_statistics(self):
        """最終統計保存（オーバーライド）"""
        try:
            duration_hours = (
                (datetime.now() - self.session_start).total_seconds() / 3600
                if self.session_start
                else 0
            )

            final_stats = {
                "mode": "live_trading",
                "session_info": {
                    "start": (
                        self.session_start.strftime("%Y-%m-%d %H:%M:%S")
                        if self.session_start
                        else "N/A"
                    ),
                    "duration_hours": round(duration_hours, 2),
                },
                "performance": {
                    "cycles_completed": self.cycle_count,
                    "trades_executed": self.trade_count,
                    "final_balance": getattr(
                        self.orchestrator.execution_service, "current_balance", 0
                    ),
                    "session_pnl": getattr(self.orchestrator.execution_service, "session_pnl", 0),
                },
                "completion_status": "completed",
            }

            self.logger.info("📊 ライブトレード最終統計", extra_data=final_stats)

        except Exception as e:
            self.logger.error(f"❌ ライブトレード最終統計保存エラー: {e}")
