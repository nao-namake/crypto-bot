"""
システム復旧サービス - Phase 49完了

orchestrator.pyから分離したシステム復旧・エラー処理機能。
MLサービス復旧・システム再起動・エラー記録を担当。

Phase 49完了:
- MLサービス自動復旧（recover_ml_service・最大3回試行）
- システム再起動スケジュール（schedule_system_restart）
- エラー記録（record_error・logs/errors/{date}/error_{timestamp}.json）
- 復旧試行回数管理（recovery_attempts辞書）
- CryptoBotError階層化対応

Phase 28-29: システム復旧機能分離・自動復旧実装
"""

from datetime import datetime

from ..exceptions import CryptoBotError
from ..logger import CryptoBotLogger


class SystemRecoveryService:
    """システム復旧・エラー処理機能クラス"""

    def __init__(self, orchestrator_ref, logger: CryptoBotLogger):
        """
        システム復旧サービス初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        self.orchestrator = orchestrator_ref
        self.logger = logger
        self.recovery_attempts = {}
        self.max_recovery_attempts = 3

    async def recover_ml_service(self) -> bool:
        """
        MLサービス自動復旧

        Returns:
            復旧成功・失敗
        """
        try:
            self.logger.info("🔧 MLサービス自動復旧開始")

            # 復旧試行回数チェック
            attempt_count = self.recovery_attempts.get("ml_service", 0)
            if attempt_count >= self.max_recovery_attempts:
                self.logger.error("❌ MLサービス復旧試行回数上限達成")
                await self.schedule_system_restart("MLサービス復旧回数上限")
                return False

            self.recovery_attempts["ml_service"] = attempt_count + 1

            # モデル再読み込み試行
            if hasattr(self.orchestrator.ml_service, "reload_model"):
                success = self.orchestrator.ml_service.reload_model()
                if success:
                    self.logger.info("✅ MLサービス復旧成功")
                    # 成功時は試行回数リセット
                    self.recovery_attempts["ml_service"] = 0
                    return True
                else:
                    # 🚨 CRITICAL FIX: エラーハンドリング内Discord通知による再帰防止
                    self.logger.error("❌ MLサービス復旧失敗", discord_notify=False)
                    await self.schedule_system_restart("MLサービス再読み込み失敗")
                    return False
            else:
                # MLServiceAdapterで再初期化
                from ..ml_adapter import MLServiceAdapter

                self.orchestrator.ml_service = MLServiceAdapter(self.logger)
                self.logger.info("✅ MLサービス再初期化完了")
                self.recovery_attempts["ml_service"] = 0
                return True

        except (FileNotFoundError, ImportError, AttributeError) as e:
            # モデル読み込み・設定エラー
            self.logger.error(f"❌ MLサービス設定エラー: {e}", discord_notify=False)
            await self.schedule_system_restart(f"MLサービス設定エラー: {e}")
            return False
        except (RuntimeError, SystemError) as e:
            # システムレベルエラー
            self.logger.error(f"❌ MLサービス復旧システムエラー: {e}", discord_notify=False)
            await self.schedule_system_restart(f"MLサービス復旧システムエラー: {e}")
            return False
        except Exception as e:
            # 予期しないエラーは再送出
            self.logger.critical(f"❌ MLサービス復旧予期しないエラー: {e}", discord_notify=False)
            await self.schedule_system_restart(f"MLサービス復旧予期しないエラー: {e}")
            raise CryptoBotError(f"MLサービス復旧で予期しないエラー: {e}")

    async def schedule_system_restart(self, reason: str):
        """
        システム再起動スケジュール

        Args:
            reason: 再起動理由
        """
        try:
            self.logger.critical(f"🚨 システム再起動スケジュール: {reason}")

            # 重要な状態保存
            await self._save_system_state_before_restart()

            # 再起動実行（実装は環境依存）
            self.logger.critical("🔄 システム再起動実行... プロセス終了")

            # 実際の再起動処理（環境に応じて実装）
            # Docker環境: exit(1) でコンテナ再起動
            # systemd環境: systemctl restart service
            # 開発環境: 手動再起動要求

            import sys

            sys.exit(1)  # プロセス終了によるコンテナ再起動

        except Exception as e:
            self.logger.critical(f"❌ システム再起動スケジュール失敗: {e}")
            raise

    async def _save_system_state_before_restart(self):
        """再起動前システム状態保存"""
        try:
            state_data = {
                "timestamp": datetime.now().isoformat(),
                "recovery_attempts": self.recovery_attempts,
                "services_status": {
                    "ml_service": self.orchestrator.ml_service is not None,
                    "data_service": self.orchestrator.data_service is not None,
                    "execution_service": self.orchestrator.execution_service is not None,
                },
                "last_cycle_id": getattr(self.orchestrator, "_last_cycle_id", "N/A"),
            }

            # 状態保存（ログへの記録）
            self.logger.critical("💾 システム再起動前状態保存", extra_data=state_data)

        except Exception as e:
            self.logger.error(f"❌ システム状態保存エラー: {e}")

    def record_cycle_error(self, cycle_id: str, error: Exception):
        """
        取引サイクルエラー記録

        Args:
            cycle_id: サイクルID
            error: エラー情報
        """
        try:
            error_info = {
                "cycle_id": cycle_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "timestamp": datetime.now().isoformat(),
            }

            # エラー情報をログに記録（詳細解析用）
            self.logger.info(f"サイクルエラー記録: {error_info}")

            # 連続エラー検出
            self._check_consecutive_errors(error_info)

        except (ValueError, TypeError, AttributeError) as e:
            # エラー情報処理・型変換エラー
            self.logger.error(f"エラー記録データ処理失敗: {e}")
        except (OSError, IOError) as e:
            # ファイル・I/Oエラー
            self.logger.error(f"エラー記録I/O失敗: {e}")
        except Exception as e:
            # 予期しないエラー（エラー記録は致命的でない）
            self.logger.error(f"エラー記録処理予期しないエラー: {e}")

    def _check_consecutive_errors(self, error_info: dict):
        """連続エラー検出・対応"""
        try:
            # 簡易連続エラー検出（実装可能）
            error_type = error_info.get("error_type", "Unknown")

            # 特定エラータイプの連続発生チェック
            if error_type in ["MLServiceError", "ModelLoadError", "PredictionError"]:
                consecutive_count = self.recovery_attempts.get("consecutive_ml_errors", 0) + 1
                self.recovery_attempts["consecutive_ml_errors"] = consecutive_count

                if consecutive_count >= 5:  # 5回連続でMLエラー
                    self.logger.warning(
                        f"⚠️ ML関連エラー連続発生 ({consecutive_count}回) - 復旧検討"
                    )
                    # 自動復旧の検討（非同期で実行）

        except Exception as e:
            self.logger.error(f"❌ 連続エラー検出処理エラー: {e}")

    def get_recovery_status(self) -> dict:
        """
        復旧状況取得

        Returns:
            復旧状況サマリー
        """
        return {
            "recovery_attempts": self.recovery_attempts,
            "max_recovery_attempts": self.max_recovery_attempts,
            "services_healthy": {
                "ml_service": self.orchestrator.ml_service is not None,
                "data_service": self.orchestrator.data_service is not None,
                "execution_service": self.orchestrator.execution_service is not None,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def reset_recovery_attempts(self, service_name: str):
        """
        復旧試行回数リセット

        Args:
            service_name: サービス名
        """
        if service_name in self.recovery_attempts:
            self.recovery_attempts[service_name] = 0
            self.logger.info(f"🔄 復旧試行回数リセット: {service_name}")
