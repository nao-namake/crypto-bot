"""
取引ログサービス - Phase 14-B リファクタリング

orchestrator.pyから分離した取引関連ログ機能。
取引決定・実行結果・統計情報のログ出力を担当。
"""

from ..logger import CryptoBotLogger


class TradingLoggerService:
    """取引ログ機能クラス"""

    def __init__(self, orchestrator_ref, logger: CryptoBotLogger):
        """
        取引ログサービス初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        self.orchestrator = orchestrator_ref
        self.logger = logger

        # 決定マッピング
        self.decision_map = {
            "approved": "🟢 取引承認",
            "conditional": "🟡 条件付き承認",
            "denied": "🔴 取引拒否",
        }

    async def log_trade_decision(self, evaluation, cycle_id: str):
        """
        取引判定ログ出力（高レベルサマリーのみ）

        Args:
            evaluation: 取引評価結果
            cycle_id: サイクルID
        """
        try:
            decision_str = getattr(evaluation, "decision", "unknown")
            decision_label = self.decision_map.get(str(decision_str).lower(), "❓ 不明")

            self.logger.info(
                f"{decision_label} - サイクル: {cycle_id}, "
                f"リスクスコア: {getattr(evaluation, 'risk_score', 0):.3f}",
                discord_notify=(str(decision_str).lower() in ["approved", "denied"]),
            )

        except Exception as e:
            self.logger.error(f"❌ 取引決定ログエラー: {e}")

    async def log_execution_result(self, execution_result, cycle_id: str, is_stop: bool = False):
        """
        注文実行結果ログ出力

        Args:
            execution_result: 実行結果
            cycle_id: サイクルID
            is_stop: ストップ注文フラグ
        """
        if execution_result is None:
            return

        try:
            success_emoji = "✅" if execution_result.success else "❌"
            stop_prefix = "🛑 自動決済: " if is_stop else ""

            if execution_result.success:
                # 成功時の詳細ログ
                await self._log_successful_execution(
                    execution_result, cycle_id, stop_prefix, success_emoji
                )
            else:
                # 失敗時のログ
                await self._log_failed_execution(
                    execution_result, cycle_id, stop_prefix, success_emoji
                )

        except (KeyError, AttributeError) as e:
            # 実行結果データアクセスエラー
            self.logger.error(f"実行結果ログデータアクセスエラー: {e}")
        except (ValueError, TypeError) as e:
            # データ型・値変換エラー
            self.logger.error(f"実行結果ログデータ変換エラー: {e}")
        except Exception as e:
            # その他の予期しないエラー（ログ出力失敗は致命的でない）
            self.logger.error(f"実行結果ログ出力予期しないエラー: {e}")

    async def _log_successful_execution(
        self, execution_result, cycle_id: str, stop_prefix: str, success_emoji: str
    ):
        """成功時実行ログ"""
        try:
            side_emoji = "📈" if execution_result.side == "buy" else "📉"

            log_message = (
                f"{stop_prefix}{success_emoji} {side_emoji} 注文実行成功 - "
                f"サイクル: {cycle_id}, "
                f"サイド: {execution_result.side.upper()}, "
                f"数量: {execution_result.amount:.4f} BTC, "
                f"価格: ¥{execution_result.price:,.0f}"
            )

            # PnL情報追加
            if hasattr(execution_result, "paper_pnl") and execution_result.paper_pnl is not None:
                pnl_emoji = "💰" if execution_result.paper_pnl > 0 else "💸"
                log_message += f", PnL: {pnl_emoji}¥{execution_result.paper_pnl:,.0f}"

            # 手数料情報追加
            if hasattr(execution_result, "fee") and execution_result.fee is not None:
                log_message += f", 手数料: ¥{execution_result.fee:,.0f}"

            # 成功した取引は必ずDiscord通知
            self.logger.info(log_message, discord_notify=True)

            # 統計情報ログ（定期的）
            await self._check_and_log_statistics()

        except Exception as e:
            self.logger.error(f"❌ 成功時実行ログエラー: {e}")

    async def _log_failed_execution(
        self, execution_result, cycle_id: str, stop_prefix: str, success_emoji: str
    ):
        """失敗時実行ログ"""
        try:
            error_message = (
                f"{stop_prefix}{success_emoji} 注文実行失敗 - "
                f"サイクル: {cycle_id}, "
                f"エラー: {execution_result.error_message or '不明'}"
            )

            # 実行失敗はWarningレベル・Discord通知
            self.logger.warning(error_message, discord_notify=True)

        except Exception as e:
            self.logger.error(f"❌ 失敗時実行ログエラー: {e}")

    async def _check_and_log_statistics(self):
        """統計情報チェック・ログ出力"""
        try:
            if (
                hasattr(self.orchestrator, "execution_service")
                and self.orchestrator.execution_service
            ):
                stats = self.orchestrator.execution_service.get_trading_statistics()

                # 10回毎に統計出力
                total_trades = stats.get("statistics", {}).get("total_trades", 0)
                if total_trades % 10 == 0 and total_trades > 0:
                    await self.log_trading_statistics(stats)

        except Exception as e:
            self.logger.error(f"❌ 統計チェックエラー: {e}")

    async def log_trading_statistics(self, stats: dict):
        """
        取引統計ログ出力

        Args:
            stats: 統計情報辞書
        """
        try:
            statistics = stats.get("statistics", {})

            total_trades = statistics.get("total_trades", 0)
            winning_trades = statistics.get("winning_trades", 0)
            win_rate = statistics.get("win_rate", 0) * 100
            current_balance = stats.get("current_balance", 0)
            initial_balance = stats.get("initial_balance", 1000000)
            return_rate = stats.get("return_rate", 0) * 100

            stats_message = (
                f"📊 取引統計サマリー\n"
                f"・総取引数: {total_trades}回\n"
                f"・勝ち取引: {winning_trades}回\n"
                f"・勝率: {win_rate:.1f}%\n"
                f"・現在残高: ¥{current_balance:,.0f}\n"
                f"・リターン率: {return_rate:+.2f}%"
            )

            # 統計情報は Info レベル・Discord通知
            self.logger.info(stats_message, discord_notify=True)

        except (KeyError, AttributeError) as e:
            # 統計データアクセスエラー
            self.logger.error(f"統計ログデータアクセスエラー: {e}")
        except (ValueError, TypeError) as e:
            # 統計データ型・値変換エラー
            self.logger.error(f"統計ログデータ変換エラー: {e}")
        except (ZeroDivisionError, ArithmeticError) as e:
            # 統計計算エラー
            self.logger.error(f"統計ログ計算エラー: {e}")
        except Exception as e:
            # その他の予期しないエラー（統計ログ出力失敗は致命的でない）
            self.logger.error(f"統計ログ出力予期しないエラー: {e}")

    def format_performance_summary(self, stats: dict) -> dict:
        """
        パフォーマンスサマリーフォーマット

        Args:
            stats: 統計情報

        Returns:
            フォーマット済みサマリー
        """
        try:
            statistics = stats.get("statistics", {})

            return {
                "total_trades": statistics.get("total_trades", 0),
                "winning_trades": statistics.get("winning_trades", 0),
                "win_rate_percent": statistics.get("win_rate", 0) * 100,
                "current_balance": stats.get("current_balance", 0),
                "return_rate_percent": stats.get("return_rate", 0) * 100,
                "profit_loss": stats.get("current_balance", 0)
                - stats.get("initial_balance", 1000000),
            }

        except Exception as e:
            self.logger.error(f"❌ パフォーマンスサマリーフォーマットエラー: {e}")
            return {}

    async def log_cycle_start(self, cycle_id: str):
        """
        サイクル開始ログ

        Args:
            cycle_id: サイクルID
        """
        try:
            self.logger.debug(f"🔄 取引サイクル開始 - ID: {cycle_id}")

        except Exception as e:
            self.logger.error(f"❌ サイクル開始ログエラー: {e}")

    async def log_cycle_end(self, cycle_id: str, duration_seconds: float):
        """
        サイクル終了ログ

        Args:
            cycle_id: サイクルID
            duration_seconds: 実行時間（秒）
        """
        try:
            self.logger.debug(
                f"✅ 取引サイクル完了 - ID: {cycle_id}, 実行時間: {duration_seconds:.2f}秒"
            )

        except Exception as e:
            self.logger.error(f"❌ サイクル終了ログエラー: {e}")
