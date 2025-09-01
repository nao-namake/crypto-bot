"""
HealthChecker テスト - カバレッジ向上対応

Phase 14-B で分離されたヘルスチェック機能のテストを実装。
カバレッジ60%達成のための追加テスト。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import HealthCheckError
from src.core.logger import CryptoBotLogger
from src.core.services.health_checker import HealthChecker


class TestHealthChecker:
    """HealthChecker メインテストクラス"""

    @pytest.fixture
    def mock_logger(self):
        """モックロガー"""
        return MagicMock(spec=CryptoBotLogger)

    @pytest.fixture
    def mock_orchestrator(self):
        """モックオーケストレーター"""
        orchestrator = MagicMock()
        orchestrator.data_service = MagicMock()
        orchestrator.feature_service = MagicMock()
        orchestrator.strategy_service = MagicMock()
        orchestrator.ml_service = MagicMock()
        orchestrator.risk_service = MagicMock()
        orchestrator.execution_service = MagicMock()
        return orchestrator

    @pytest.fixture
    def health_checker(self, mock_orchestrator, mock_logger):
        """HealthCheckerインスタンス"""
        return HealthChecker(mock_orchestrator, mock_logger)

    def test_init(self, mock_orchestrator, mock_logger):
        """初期化テスト"""
        checker = HealthChecker(mock_orchestrator, mock_logger)

        assert checker.orchestrator == mock_orchestrator
        assert checker.logger == mock_logger

    @pytest.mark.asyncio
    async def test_check_all_services_success(self, health_checker):
        """全サービスヘルスチェック成功テスト"""
        with patch.object(health_checker, "_check_service_initialization") as mock_service_check:
            with patch.object(health_checker, "_check_system_resources") as mock_resource_check:
                mock_service_check.return_value = None
                mock_resource_check.return_value = None

                result = await health_checker.check_all_services()

                assert result is True
                mock_service_check.assert_called_once()
                mock_resource_check.assert_called_once()
                health_checker.logger.info.assert_called_with("✅ 全サービス健全性確認完了")

    @pytest.mark.asyncio
    async def test_check_all_services_attribute_error(self, health_checker):
        """AttributeError時のテスト"""
        with patch.object(health_checker, "_check_service_initialization") as mock_check:
            mock_check.side_effect = AttributeError("service not found")

            with pytest.raises(HealthCheckError) as exc_info:
                await health_checker.check_all_services()

            assert "サービス未初期化" in str(exc_info.value)
            assert exc_info.value.service_name == "unknown"
            health_checker.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_check_all_services_runtime_error(self, health_checker):
        """RuntimeError時のテスト"""
        with patch.object(health_checker, "_check_service_initialization") as mock_check:
            mock_check.side_effect = RuntimeError("system error")

            with pytest.raises(HealthCheckError) as exc_info:
                await health_checker.check_all_services()

            assert "システムヘルスチェック失敗" in str(exc_info.value)
            assert exc_info.value.service_name == "system"
            health_checker.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_check_all_services_unexpected_error(self, health_checker):
        """予期しないエラー時のテスト"""
        with patch.object(health_checker, "_check_service_initialization") as mock_check:
            mock_check.side_effect = ValueError("unexpected error")

            with pytest.raises(HealthCheckError) as exc_info:
                await health_checker.check_all_services()

            assert "予期しないヘルスチェック失敗" in str(exc_info.value)
            assert exc_info.value.service_name == "unknown"
            health_checker.logger.critical.assert_called()

    @pytest.mark.asyncio
    async def test_check_service_initialization_success(self, health_checker):
        """サービス初期化確認成功テスト"""
        # 全サービスが正常に初期化されている状態
        await health_checker._check_service_initialization()

        health_checker.logger.debug.assert_called_with("🔍 サービス初期化確認完了")

    @pytest.mark.asyncio
    async def test_check_service_initialization_missing_service(self, health_checker):
        """サービス未初期化エラーテスト"""
        # data_serviceをNoneに設定
        health_checker.orchestrator.data_service = None

        with pytest.raises(HealthCheckError) as exc_info:
            await health_checker._check_service_initialization()

        assert "data_serviceが未初期化" in str(exc_info.value)
        assert exc_info.value.service_name == "data_service"

    @pytest.mark.asyncio
    async def test_check_system_resources_import_error(self, health_checker):
        """psutil ImportError時のテスト"""
        with patch("builtins.__import__", side_effect=ImportError("psutil not found")):
            await health_checker._check_system_resources()

            health_checker.logger.debug.assert_called_with(
                "psutilが利用できないため、システムリソース確認をスキップ"
            )
