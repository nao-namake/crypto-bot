"""
TradingOrchestrator 包括テスト

Application Service Layerの統合制御機能をテスト。
依存性注入・エラーハンドリング・モード別実行・バックテスト制御をカバー。

カバー範囲:
- 依存性注入とコンストラクタ
- initialize() サービス初期化確認
- run() モード別実行制御（backtest/paper/live）
- run_trading_cycle() 取引サイクル制御
- _run_backtest_mode() バックテスト制御
- create_trading_orchestrator() ファクトリー関数
- _get_actual_balance() 残高取得（API/フォールバック）
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.exceptions import CryptoBotError, DataProcessingError, HealthCheckError
from src.core.logger import CryptoBotLogger
from src.core.orchestration.orchestrator import (
    TradingOrchestrator,
    _get_actual_balance,
    create_trading_orchestrator,
)


@pytest.fixture
def mock_config():
    """モックConfig"""
    config = Mock()
    config.mode = "paper"
    config.exchange.symbol = "BTC/JPY"
    return config


@pytest.fixture
def mock_logger():
    """モックCryptoBotLogger"""
    logger = Mock(spec=CryptoBotLogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    logger.logger = Mock()
    logger.logger.level = 20  # INFO
    logger.logger.handlers = []
    logger.logger.setLevel = Mock()
    return logger


@pytest.fixture
def mock_services():
    """モック依存サービス一式"""
    return {
        "data_service": Mock(),
        "feature_service": Mock(),
        "strategy_service": Mock(),
        "ml_service": Mock(),
        "risk_service": Mock(),
        "execution_service": Mock(),
    }


@pytest.fixture
def orchestrator(mock_config, mock_logger, mock_services):
    """テスト用TradingOrchestratorインスタンス"""
    return TradingOrchestrator(
        config=mock_config,
        logger=mock_logger,
        data_service=mock_services["data_service"],
        feature_service=mock_services["feature_service"],
        strategy_service=mock_services["strategy_service"],
        ml_service=mock_services["ml_service"],
        risk_service=mock_services["risk_service"],
        execution_service=mock_services["execution_service"],
    )


class TestOrchestratorInitialization:
    """TradingOrchestrator初期化テスト"""

    def test_constructor_dependency_injection(self, orchestrator, mock_config, mock_logger):
        """コンストラクタで依存性が正しく注入される"""
        assert orchestrator.config is mock_config
        assert orchestrator.logger is mock_logger
        assert orchestrator.data_service is not None
        assert orchestrator.feature_service is not None
        assert orchestrator.strategy_service is not None
        assert orchestrator.ml_service is not None
        assert orchestrator.risk_service is not None
        assert orchestrator.execution_service is not None
        assert orchestrator._initialized is False

    def test_constructor_initializes_subsystems(self, orchestrator):
        """コンストラクタでサブシステムが初期化される"""
        # サブシステムの存在確認
        assert hasattr(orchestrator, "backtest_reporter")
        assert hasattr(orchestrator, "paper_trading_reporter")
        assert hasattr(orchestrator, "backtest_runner")
        assert hasattr(orchestrator, "paper_trading_runner")
        assert hasattr(orchestrator, "live_trading_runner")
        assert hasattr(orchestrator, "health_checker")
        assert hasattr(orchestrator, "system_recovery")
        assert hasattr(orchestrator, "trading_logger")
        assert hasattr(orchestrator, "trading_cycle_manager")

    @pytest.mark.asyncio
    async def test_initialize_success(self, orchestrator):
        """初期化成功時の動作"""
        # health_checker.check_all_services() をモック
        orchestrator.health_checker.check_all_services = AsyncMock()

        result = await orchestrator.initialize()

        assert result is True
        assert orchestrator._initialized is True
        orchestrator.health_checker.check_all_services.assert_called_once()
        orchestrator.logger.info.assert_any_call("🚀 TradingOrchestrator初期化確認開始")

    @pytest.mark.asyncio
    async def test_initialize_attribute_error(self, orchestrator):
        """初期化時のAttributeErrorハンドリング"""
        orchestrator.health_checker.check_all_services = AsyncMock(
            side_effect=AttributeError("Service not initialized")
        )

        result = await orchestrator.initialize()

        assert result is False
        assert orchestrator._initialized is False
        orchestrator.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_initialize_runtime_error(self, orchestrator):
        """初期化時のRuntimeErrorハンドリング"""
        orchestrator.health_checker.check_all_services = AsyncMock(
            side_effect=RuntimeError("System initialization failed")
        )

        result = await orchestrator.initialize()

        assert result is False
        orchestrator.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_initialize_unexpected_error(self, orchestrator):
        """初期化時の予期しないエラーハンドリング"""
        orchestrator.health_checker.check_all_services = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )

        with pytest.raises(CryptoBotError, match="TradingOrchestrator初期化で予期しないエラー"):
            await orchestrator.initialize()

        orchestrator.logger.critical.assert_called()


class TestOrchestratorRun:
    """TradingOrchestrator実行テスト"""

    @pytest.mark.asyncio
    async def test_run_not_initialized_error(self, orchestrator):
        """未初期化状態でrun()を呼ぶとエラー"""
        with pytest.raises(CryptoBotError, match="初期化されていません"):
            await orchestrator.run()

    @pytest.mark.asyncio
    async def test_run_backtest_mode(self, orchestrator, mock_config):
        """バックテストモード実行"""
        orchestrator._initialized = True
        mock_config.mode = "backtest"
        orchestrator._run_backtest_mode = AsyncMock()

        await orchestrator.run()

        orchestrator._run_backtest_mode.assert_called_once()
        orchestrator.logger.info.assert_any_call(
            "TradingOrchestrator実行開始 - モード: BACKTEST（Configから取得）"
        )

    @pytest.mark.asyncio
    async def test_run_paper_mode(self, orchestrator, mock_config):
        """ペーパートレードモード実行"""
        orchestrator._initialized = True
        mock_config.mode = "paper"
        orchestrator.paper_trading_runner.run_with_error_handling = AsyncMock()

        await orchestrator.run()

        orchestrator.paper_trading_runner.run_with_error_handling.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_live_mode(self, orchestrator, mock_config):
        """ライブトレードモード実行"""
        orchestrator._initialized = True
        mock_config.mode = "live"
        orchestrator.live_trading_runner.run_with_error_handling = AsyncMock()

        await orchestrator.run()

        orchestrator.live_trading_runner.run_with_error_handling.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_invalid_mode(self, orchestrator, mock_config):
        """無効なモード指定時のエラーハンドリング"""
        orchestrator._initialized = True
        mock_config.mode = "invalid_mode"

        # ValueErrorはCryptoBotErrorでラップされる
        with pytest.raises(CryptoBotError, match="予期しないシステム実行エラー"):
            await orchestrator.run()

    @pytest.mark.asyncio
    async def test_run_keyboard_interrupt(self, orchestrator, mock_config):
        """KeyboardInterruptハンドリング"""
        orchestrator._initialized = True
        mock_config.mode = "paper"
        orchestrator.paper_trading_runner.run_with_error_handling = AsyncMock(
            side_effect=KeyboardInterrupt()
        )

        # KeyboardInterruptは握りつぶされる
        await orchestrator.run()

        orchestrator.logger.info.assert_any_call("ユーザーによる終了要求を受信")

    @pytest.mark.asyncio
    async def test_run_attribute_error(self, orchestrator, mock_config):
        """AttributeErrorハンドリング"""
        orchestrator._initialized = True
        mock_config.mode = "paper"
        orchestrator.paper_trading_runner.run_with_error_handling = AsyncMock(
            side_effect=AttributeError("Config error")
        )

        with pytest.raises(CryptoBotError, match="システム初期化エラー"):
            await orchestrator.run()


class TestTradingCycle:
    """取引サイクル実行テスト"""

    @pytest.mark.asyncio
    async def test_run_trading_cycle_success(self, orchestrator):
        """取引サイクル正常実行"""
        orchestrator.trading_cycle_manager.execute_trading_cycle = AsyncMock()

        await orchestrator.run_trading_cycle()

        orchestrator.trading_cycle_manager.execute_trading_cycle.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_trading_cycle_cryptobot_error(self, orchestrator):
        """取引サイクルでCryptoBotError発生時"""
        orchestrator.trading_cycle_manager.execute_trading_cycle = AsyncMock(
            side_effect=CryptoBotError("Trading error")
        )

        with pytest.raises(CryptoBotError):
            await orchestrator.run_trading_cycle()

    @pytest.mark.asyncio
    async def test_run_trading_cycle_unexpected_error(self, orchestrator):
        """取引サイクルで予期しないエラー発生時"""
        orchestrator.trading_cycle_manager.execute_trading_cycle = AsyncMock(
            side_effect=ValueError("Unexpected")
        )

        with pytest.raises(CryptoBotError, match="最上位で予期しないエラー"):
            await orchestrator.run_trading_cycle()

        orchestrator.logger.critical.assert_called()


class TestBacktestMode:
    """バックテストモード実行テスト"""

    @pytest.mark.asyncio
    @patch("src.core.orchestration.orchestrator.get_threshold")
    async def test_run_backtest_mode_success(self, mock_get_threshold, orchestrator, mock_services):
        """バックテストモード正常実行"""
        mock_get_threshold.side_effect = lambda key, default: default
        orchestrator.backtest_runner.run = AsyncMock(return_value=True)

        await orchestrator._run_backtest_mode()

        # データサービスがバックテストモードに設定される
        mock_services["data_service"].set_backtest_mode.assert_any_call(True)
        # バックテスト実行
        orchestrator.backtest_runner.run.assert_called_once()
        # バックテストモード解除
        mock_services["data_service"].set_backtest_mode.assert_any_call(False)
        mock_services["data_service"].clear_backtest_data.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.core.orchestration.orchestrator.get_threshold")
    async def test_run_backtest_mode_failure(self, mock_get_threshold, orchestrator, mock_services):
        """バックテスト実行失敗時"""
        mock_get_threshold.side_effect = lambda key, default: default
        orchestrator.backtest_runner.run = AsyncMock(return_value=False)

        await orchestrator._run_backtest_mode()

        orchestrator.logger.warning.assert_any_call(
            "⚠️ バックテスト実行で問題が発生しました", discord_notify=False
        )

    @pytest.mark.asyncio
    @patch("src.core.orchestration.orchestrator.get_threshold")
    async def test_run_backtest_mode_file_error(
        self, mock_get_threshold, orchestrator, mock_services
    ):
        """バックテスト時のファイルI/Oエラー"""
        mock_get_threshold.side_effect = lambda key, default: default
        orchestrator.backtest_runner.run = AsyncMock(
            side_effect=FileNotFoundError("Data file not found")
        )

        with pytest.raises(DataProcessingError, match="データ読み込みエラー"):
            await orchestrator._run_backtest_mode()

        # finallyブロックでクリーンアップが実行される
        mock_services["data_service"].set_backtest_mode.assert_any_call(False)

    @pytest.mark.asyncio
    @patch("src.core.orchestration.orchestrator.get_threshold")
    async def test_run_backtest_mode_value_error(
        self, mock_get_threshold, orchestrator, mock_services
    ):
        """バックテスト時のデータ形式エラー"""
        mock_get_threshold.side_effect = lambda key, default: default
        orchestrator.backtest_runner.run = AsyncMock(side_effect=ValueError("Invalid data format"))

        with pytest.raises(DataProcessingError, match="データ処理エラー"):
            await orchestrator._run_backtest_mode()

    @pytest.mark.asyncio
    @patch("src.core.orchestration.orchestrator.get_threshold")
    async def test_run_backtest_mode_import_error(
        self, mock_get_threshold, orchestrator, mock_services
    ):
        """バックテスト時のモジュールエラー"""
        mock_get_threshold.side_effect = lambda key, default: default
        orchestrator.backtest_runner.run = AsyncMock(side_effect=ImportError("Module not found"))

        with pytest.raises(HealthCheckError, match="依存モジュールエラー"):
            await orchestrator._run_backtest_mode()

    @pytest.mark.asyncio
    @patch("src.core.orchestration.orchestrator.get_threshold")
    async def test_run_backtest_mode_discord_disable(
        self, mock_get_threshold, orchestrator, mock_services
    ):
        """バックテスト時のDiscord無効化"""
        mock_get_threshold.side_effect = lambda key, default: {
            "backtest.log_level": "WARNING",
            "backtest.discord_enabled": False,
        }.get(key, default)

        # _discord_manager属性を設定
        mock_discord = Mock()
        orchestrator.logger._discord_manager = mock_discord
        orchestrator.backtest_runner.run = AsyncMock(return_value=True)

        await orchestrator._run_backtest_mode()

        # Discord通知が一時的にNoneに設定され、最後に復元される
        assert orchestrator.logger._discord_manager == mock_discord


class TestGetActualBalance:
    """残高取得機能テスト"""

    @pytest.mark.asyncio
    @patch("src.core.config.load_config")
    async def test_get_actual_balance_paper_mode(self, mock_load_config, mock_logger):
        """ペーパーモード時はAPI呼び出しスキップ"""
        mock_config = Mock()
        mock_config.mode = "paper"

        # unified.yamlモック
        unified_config = Mock()
        unified_config.mode_balances = {"paper": {"initial_balance": 100000.0}}
        mock_load_config.return_value = unified_config

        balance = await _get_actual_balance(mock_config, mock_logger)

        assert balance == 100000.0
        mock_logger.info.assert_any_call(
            "📝 ペーパーモード: API呼び出しをスキップ、mode_balances残高使用"
        )

    @pytest.mark.asyncio
    @patch("src.core.config.load_config")
    async def test_get_actual_balance_backtest_mode(self, mock_load_config, mock_logger):
        """バックテストモード時はAPI呼び出しスキップ"""
        mock_config = Mock()
        mock_config.mode = "backtest"

        # unified.yamlモック
        unified_config = Mock()
        unified_config.mode_balances = {"backtest": {"initial_balance": 10000.0}}
        mock_load_config.return_value = unified_config

        balance = await _get_actual_balance(mock_config, mock_logger)

        assert balance == 10000.0
        mock_logger.info.assert_any_call(
            "📝 バックテストモード: API呼び出しをスキップ、mode_balances残高使用"
        )

    @pytest.mark.asyncio
    @patch("src.core.config.load_config")
    @patch("src.data.bitbank_client.BitbankClient")
    async def test_get_actual_balance_live_mode_success(
        self, mock_bitbank_class, mock_load_config, mock_logger
    ):
        """ライブモード時のAPI残高取得成功"""
        mock_config = Mock()
        mock_config.mode = "live"

        # BitbankClient モック（Phase 53.6: async/await対応）
        mock_client = Mock()
        mock_client.fetch_balance = AsyncMock(
            return_value={"JPY": {"free": 15000.0, "total": 15000.0}}
        )
        mock_bitbank_class.return_value = mock_client

        balance = await _get_actual_balance(mock_config, mock_logger)

        assert balance == 15000.0
        mock_logger.info.assert_any_call("✅ Bitbank実残高取得成功: 15,000円")

    @pytest.mark.asyncio
    @patch("src.core.config.load_config")
    @patch("src.data.bitbank_client.BitbankClient")
    async def test_get_actual_balance_live_mode_zero_balance(
        self, mock_bitbank_class, mock_load_config, mock_logger
    ):
        """ライブモード時の残高0円時のフォールバック"""
        mock_config = Mock()
        mock_config.mode = "live"

        # unified.yamlモック
        unified_config = Mock()
        unified_config.mode_balances = {"live": {"initial_balance": 10000.0}}
        mock_load_config.return_value = unified_config

        # BitbankClient モック（Phase 53.6: async/await対応・残高0円）
        mock_client = Mock()
        mock_client.fetch_balance = AsyncMock(return_value={"JPY": {"free": 0.0, "total": 0.0}})
        mock_bitbank_class.return_value = mock_client

        balance = await _get_actual_balance(mock_config, mock_logger)

        assert balance == 10000.0
        mock_logger.warning.assert_any_call("⚠️ Bitbank残高が0円以下（0.0円）、mode_balances値使用")

    @pytest.mark.asyncio
    @patch("src.core.config.load_config")
    @patch("src.data.bitbank_client.BitbankClient")
    async def test_get_actual_balance_api_error(
        self, mock_bitbank_class, mock_load_config, mock_logger
    ):
        """API認証エラー時のフォールバック"""
        from src.core.exceptions import ExchangeAPIError

        mock_config = Mock()
        mock_config.mode = "live"

        # unified.yamlモック
        unified_config = Mock()
        unified_config.mode_balances = {"live": {"initial_balance": 10000.0}}
        mock_load_config.return_value = unified_config

        # BitbankClient モック（API Error）
        mock_client = Mock()
        mock_client.fetch_balance.side_effect = ExchangeAPIError("Auth failed")
        mock_bitbank_class.return_value = mock_client

        balance = await _get_actual_balance(mock_config, mock_logger)

        assert balance == 10000.0
        mock_logger.warning.assert_any_call("💰 認証エラーのためmode_balances残高使用: 10000.0円")


class TestCreateTradingOrchestrator:
    """create_trading_orchestrator() ファクトリー関数テスト"""

    @pytest.mark.asyncio
    @patch("src.core.orchestration.orchestrator._get_actual_balance")
    @patch("src.trading.create_risk_manager")
    @patch("src.trading.execution.ExecutionService")
    @patch("src.core.reporting.discord_notifier.DiscordManager")
    @patch("src.data.bitbank_client.BitbankClient")
    @patch("src.data.data_pipeline.DataPipeline")
    @patch("src.features.feature_generator.FeatureGenerator")
    @patch("src.strategies.base.strategy_manager.StrategyManager")
    @patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": "https://discord.com/webhook/test"})
    async def test_create_trading_orchestrator_success(
        self,
        mock_strategy_manager,
        mock_feature_generator,
        mock_data_pipeline,
        mock_bitbank_client,
        mock_discord_manager,
        mock_execution_service,
        mock_create_risk_manager,
        mock_get_balance,
        mock_config,
        mock_logger,
    ):
        """ファクトリー関数による正常なOrchestrator作成"""
        # モック設定
        mock_get_balance.return_value = asyncio.Future()
        mock_get_balance.return_value.set_result(10000.0)

        mock_discord = Mock()
        mock_discord.enabled = True
        mock_discord.test_connection.return_value = True
        mock_discord_manager.return_value = mock_discord

        mock_create_risk_manager.return_value = Mock()

        # ファクトリー実行
        orchestrator = await create_trading_orchestrator(mock_config, mock_logger)

        # Orchestratorが正常に作成される
        assert isinstance(orchestrator, TradingOrchestrator)
        assert orchestrator.config is mock_config
        assert orchestrator.logger is mock_logger

        mock_logger.info.assert_any_call("🏗️ TradingOrchestrator依存性組み立て開始")
        mock_logger.info.assert_any_call("🎉 TradingOrchestrator依存性組み立て完了")

    @pytest.mark.asyncio
    @patch("src.core.reporting.discord_notifier.DiscordManager")
    async def test_create_trading_orchestrator_import_error(
        self, mock_discord_manager, mock_config, mock_logger
    ):
        """依存モジュール読み込みエラー"""
        # ImportErrorを引き起こす
        with patch(
            "src.data.bitbank_client.BitbankClient", side_effect=ImportError("Module error")
        ):
            with pytest.raises(CryptoBotError, match="依存モジュール読み込みエラー"):
                await create_trading_orchestrator(mock_config, mock_logger)

        mock_logger.error.assert_called()
