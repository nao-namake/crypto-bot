"""
基底ランナークラス - Phase 49完了

実行モードの共通機能・インターフェースを提供。
orchestrator.pyから分離した実行モード機能の基盤。

Phase 49完了:
- 共通インターフェース定義（run・initialize_mode・cleanup_mode抽象メソッド）
- 3モード共通機能（orchestrator参照・logger統合・config取得・モード名自動設定）
- ABC（Abstract Base Class）型安全設計

Phase 28-29: 実行モード基底クラス設計・共通機能抽出完了
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..config import Config, get_threshold
from ..logger import CryptoBotLogger


class BaseRunner(ABC):
    """実行モードの基底クラス"""

    def __init__(self, orchestrator_ref, logger: CryptoBotLogger):
        """
        基底ランナー初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        self.orchestrator = orchestrator_ref
        self.logger = logger
        self.config: Config = orchestrator_ref.config
        self.is_running = False
        self.mode_name = self.__class__.__name__.replace("Runner", "").lower()

    @abstractmethod
    async def run(self) -> bool:
        """
        実行モード共通インターフェース（サブクラスで実装）

        Returns:
            実行成功・失敗
        """
        pass

    async def initialize_mode(self) -> bool:
        """
        モード初期化（共通処理）

        Returns:
            初期化成功・失敗
        """
        try:
            self.logger.info(f"🚀 {self.mode_name}モード初期化開始")

            # 共通初期化処理
            if not await self._validate_dependencies():
                return False

            if not await self._setup_mode_configuration():
                return False

            self.is_running = True
            self.logger.info(f"✅ {self.mode_name}モード初期化完了")
            return True

        except Exception as e:
            self.logger.error(f"❌ {self.mode_name}モード初期化失敗: {e}")
            return False

    async def cleanup_mode(self):
        """モード終了処理（共通処理）"""
        try:
            self.logger.info(f"🔄 {self.mode_name}モード終了処理開始")

            # 共通終了処理
            await self._save_final_statistics()
            await self._cleanup_resources()

            self.is_running = False
            self.logger.info(f"✅ {self.mode_name}モード終了処理完了")

        except Exception as e:
            self.logger.error(f"❌ {self.mode_name}モード終了処理エラー: {e}")

    async def _validate_dependencies(self) -> bool:
        """依存性検証（共通処理）"""
        try:
            # 基本サービス確認
            required_services = [
                self.orchestrator.data_service,
                self.orchestrator.feature_service,
                self.orchestrator.ml_service,
            ]

            for service in required_services:
                if service is None:
                    self.logger.error(f"❌ 必須サービスが未初期化: {service}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"❌ 依存性検証エラー: {e}")
            return False

    async def _setup_mode_configuration(self) -> bool:
        """モード設定セットアップ（共通処理）"""
        try:
            # Phase 22 設定外部化・ハードコード排除
            interval = self.get_mode_interval()
            self.logger.info(f"⚙️ {self.mode_name}モード実行間隔: {interval}秒")

            return True

        except Exception as e:
            self.logger.error(f"❌ モード設定エラー: {e}")
            return False

    def get_mode_interval(self) -> int:
        """モード別実行間隔取得（Phase 22 設定外部化・ハードコード排除）"""
        if self.config.mode == "paper":
            return get_threshold("execution.paper_mode_interval_seconds", 60)
        elif self.config.mode == "live":
            return get_threshold("execution.live_mode_interval_seconds", 180)
        else:
            return 1  # バックテスト用

    async def _save_final_statistics(self):
        """最終統計保存（共通処理）"""
        try:
            final_stats = {
                "mode": self.mode_name,
                "execution_time": "統計は各サブクラスで実装",
                "completion_status": "completed",
            }

            self.logger.info(f"📊 {self.mode_name}最終統計", extra_data=final_stats)

        except Exception as e:
            self.logger.error(f"❌ 最終統計保存エラー: {e}")

    async def _cleanup_resources(self):
        """リソースクリーンアップ（共通処理）

        Phase 89 H11: WebSocket クライアントの切断 + cross_asset history 永続化.
        各サブクラスは super()._cleanup_resources() を呼んだ後に固有処理を行う。
        """
        try:
            # Phase 89 H11: WebSocket クライアントを切断（SIGTERM 時のリソースリーク防止）
            try:
                bitbank_client = getattr(
                    self.orchestrator.execution_service, "bitbank_client", None
                )
                if bitbank_client is not None and hasattr(bitbank_client, "disconnect_websocket"):
                    await bitbank_client.disconnect_websocket()
                    self.logger.info("✅ Phase 89 H11: WebSocket クライアント切断完了")
            except Exception as ws_err:
                self.logger.warning(f"Phase 89 H11: WebSocket 切断失敗（無視して続行）: {ws_err}")

            # Phase 89 H3: cross_asset history を pickle 保存（再起動跨ぎ保持）
            try:
                feature_service = getattr(self.orchestrator, "feature_service", None)
                if feature_service is not None and hasattr(
                    feature_service, "save_cross_asset_history"
                ):
                    feature_service.save_cross_asset_history()
            except Exception as save_err:
                self.logger.warning(
                    f"Phase 89 H3: cross_asset history 保存失敗（無視して続行）: {save_err}"
                )

        except Exception as e:
            self.logger.error(f"❌ リソースクリーンアップエラー: {e}")

    async def handle_keyboard_interrupt(self):
        """キーボード割り込み処理（共通処理）"""
        self.logger.info(f"⚠️ {self.mode_name}モード: キーボード割り込みを検出")
        await self.cleanup_mode()

    async def run_with_error_handling(self) -> bool:
        """
        エラーハンドリング付き実行（共通処理）

        Returns:
            実行成功・失敗
        """
        try:
            # 初期化
            if not await self.initialize_mode():
                return False

            # 実行（サブクラスで実装）
            result = await self.run()

            return result

        except KeyboardInterrupt:
            await self.handle_keyboard_interrupt()
            return False

        except Exception as e:
            self.logger.error(f"❌ {self.mode_name}モード実行エラー: {e}")
            return False

        finally:
            # 終了処理
            await self.cleanup_mode()
