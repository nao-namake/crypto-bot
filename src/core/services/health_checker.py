"""
ヘルスチェッカー - Phase 22 リファクタリング

orchestrator.pyから分離したヘルスチェック機能。
各サービスの健全性確認・システム状態監視を担当。
"""

from ..config import get_monitoring_config
from ..exceptions import HealthCheckError
from ..logger import CryptoBotLogger


class HealthChecker:
    """ヘルスチェック機能クラス"""

    def __init__(self, orchestrator_ref, logger: CryptoBotLogger):
        """
        ヘルスチェッカー初期化

        Args:
            orchestrator_ref: TradingOrchestratorへの参照
            logger: ログシステム
        """
        self.orchestrator = orchestrator_ref
        self.logger = logger

    async def check_all_services(self) -> bool:
        """
        全サービスヘルスチェック

        Returns:
            ヘルスチェック成功・失敗
        """
        try:
            # 基本的な接続性確認のみ（具体的な初期化は各サービスで実施済み）
            await self._check_service_initialization()
            await self._check_system_resources()

            self.logger.info("✅ 全サービス健全性確認完了")
            return True

        except AttributeError as e:
            self.logger.error(f"サービス未初期化エラー: {e}")
            raise HealthCheckError(f"サービス未初期化: {e}", service_name="unknown")
        except (RuntimeError, SystemError) as e:
            self.logger.error(f"システムレベルヘルスチェックエラー: {e}")
            raise HealthCheckError(f"システムヘルスチェック失敗: {e}", service_name="system")
        except Exception as e:
            # 予期しないヘルスチェックエラー
            self.logger.critical(f"予期しないヘルスチェックエラー: {e}")
            raise HealthCheckError(f"予期しないヘルスチェック失敗: {e}", service_name="unknown")

    async def _check_service_initialization(self):
        """サービス初期化確認"""
        try:
            required_services = [
                ("data_service", self.orchestrator.data_service),
                ("feature_service", self.orchestrator.feature_service),
                ("strategy_service", self.orchestrator.strategy_service),
                ("ml_service", self.orchestrator.ml_service),
                ("risk_service", self.orchestrator.risk_service),
                ("execution_service", self.orchestrator.execution_service),
            ]

            for service_name, service in required_services:
                if service is None:
                    raise HealthCheckError(f"{service_name}が未初期化", service_name=service_name)

            self.logger.debug("🔍 サービス初期化確認完了")

        except Exception as e:
            self.logger.error(f"❌ サービス初期化確認エラー: {e}")
            raise

    async def _check_system_resources(self):
        """システムリソース確認"""
        try:
            # メモリ・CPU使用量の簡易チェック
            import psutil

            memory_usage = psutil.virtual_memory().percent
            cpu_check_interval = get_monitoring_config("health_check.cpu_check_interval", 1)
            cpu_usage = psutil.cpu_percent(interval=cpu_check_interval)

            # 警告レベル設定（thresholds.yamlから取得）
            memory_warning_threshold = get_monitoring_config(
                "health_check.memory_threshold_percent", 85
            )
            cpu_warning_threshold = get_monitoring_config("health_check.cpu_threshold_percent", 80)

            if memory_usage > memory_warning_threshold:
                self.logger.warning(f"⚠️ メモリ使用量高: {memory_usage:.1f}%")

            if cpu_usage > cpu_warning_threshold:
                self.logger.warning(f"⚠️ CPU使用量高: {cpu_usage:.1f}%")

            self.logger.debug(
                f"🔍 システムリソース確認完了 - Memory: {memory_usage:.1f}%, CPU: {cpu_usage:.1f}%"
            )

        except ImportError:
            # psutilがない場合はスキップ
            self.logger.debug("psutilが利用できないため、システムリソース確認をスキップ")
        except Exception as e:
            self.logger.error(f"❌ システムリソース確認エラー: {e}")
            raise

    async def check_service_status(self, service_name: str) -> bool:
        """
        個別サービスステータス確認

        Args:
            service_name: サービス名

        Returns:
            サービス正常・異常
        """
        try:
            service = getattr(self.orchestrator, service_name, None)

            if service is None:
                self.logger.error(f"❌ サービス未初期化: {service_name}")
                return False

            # サービス固有のヘルスチェック（可能な場合）
            if hasattr(service, "health_check"):
                health_result = await service.health_check()
                if not health_result:
                    self.logger.error(f"❌ サービスヘルスチェック失敗: {service_name}")
                    return False

            self.logger.debug(f"✅ サービス正常: {service_name}")
            return True

        except Exception as e:
            self.logger.error(f"❌ サービスステータス確認エラー ({service_name}): {e}")
            return False

    def get_health_summary(self) -> dict:
        """
        ヘルスチェックサマリー取得

        Returns:
            システム健全性サマリー
        """
        try:
            services_status = {}

            service_names = [
                "data_service",
                "feature_service",
                "strategy_service",
                "ml_service",
                "risk_service",
                "execution_service",
            ]

            for service_name in service_names:
                service = getattr(self.orchestrator, service_name, None)
                services_status[service_name] = service is not None

            return {
                "all_services_initialized": all(services_status.values()),
                "services_status": services_status,
                "orchestrator_initialized": self.orchestrator._initialized,
                "timestamp": "N/A",  # 実際の使用時は datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"❌ ヘルスサマリー取得エラー: {e}")
            return {
                "all_services_initialized": False,
                "error": str(e),
                "timestamp": "N/A",
            }
