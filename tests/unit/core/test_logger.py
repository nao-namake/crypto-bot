"""
CryptoBotLoggerのテスト - Phase 62

ログシステムの基本動作、フォーマッター、ハンドラー、
バックテストモード対応をテスト。
カバレッジ90%以上を目標。
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.logger import (
    JST,
    ColorFormatter,
    CryptoBotLogger,
    JSONFormatter,
    LogLevel,
    get_logger,
    setup_logging,
)


class TestLogLevel:
    """LogLevel enumのテスト"""

    def test_log_level_debug(self):
        """DEBUGレベル確認"""
        assert LogLevel.DEBUG.value == "DEBUG"

    def test_log_level_info(self):
        """INFOレベル確認"""
        assert LogLevel.INFO.value == "INFO"

    def test_log_level_warning(self):
        """WARNINGレベル確認"""
        assert LogLevel.WARNING.value == "WARNING"

    def test_log_level_error(self):
        """ERRORレベル確認"""
        assert LogLevel.ERROR.value == "ERROR"

    def test_log_level_critical(self):
        """CRITICALレベル確認"""
        assert LogLevel.CRITICAL.value == "CRITICAL"


class TestJST:
    """JSTタイムゾーンのテスト"""

    def test_jst_offset(self):
        """JST が UTC+9 であること"""
        assert JST == timezone(timedelta(hours=9))

    def test_jst_datetime(self):
        """JST で正しい時刻が取得できること"""
        now_jst = datetime.now(JST)
        assert now_jst.tzinfo == JST


class TestJSONFormatter:
    """JSONFormatterのテスト"""

    def setup_method(self):
        """テストごとに新しいフォーマッターを作成"""
        self.formatter = JSONFormatter()

    def test_basic_format(self):
        """基本フォーマット確認"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = self.formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert data["module"] == "test"
        assert data["line"] == 10
        assert "timestamp" in data

    def test_format_with_exception(self):
        """例外情報付きフォーマット確認"""
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=20,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        result = self.formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test exception"
        assert "traceback" in data["exception"]

    def test_format_with_extra_data(self):
        """extra_data付きフォーマット確認"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=30,
            msg="Test with extra",
            args=(),
            exc_info=None,
        )
        record.extra_data = {"key": "value", "count": 100}
        result = self.formatter.format(record)
        data = json.loads(result)

        assert "extra" in data
        assert data["extra"]["key"] == "value"
        assert data["extra"]["count"] == 100

    def test_format_with_error_context(self):
        """error_context付きフォーマット確認"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=40,
            msg="Error with context",
            args=(),
            exc_info=None,
        )
        record.error_context = {"error_type": "TestError", "details": "test details"}
        result = self.formatter.format(record)
        data = json.loads(result)

        assert "error_context" in data
        assert data["error_context"]["error_type"] == "TestError"

    def test_format_with_exception_none_values(self):
        """例外情報がNoneを含む場合のフォーマット確認"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=50,
            msg="Error with none exc_info",
            args=(),
            exc_info=(None, None, None),
        )
        result = self.formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert data["exception"]["type"] is None
        assert data["exception"]["message"] is None


class TestColorFormatter:
    """ColorFormatterのテスト"""

    def setup_method(self):
        """テストごとに新しいフォーマッターを作成"""
        self.formatter = ColorFormatter()

    def test_basic_format(self):
        """基本フォーマット確認"""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = self.formatter.format(record)

        assert "Test message" in result
        assert "[test_logger]" in result
        assert "\033[32m" in result  # INFO color (green)
        assert "\033[0m" in result  # RESET

    def test_format_debug(self):
        """DEBUGレベルのカラー確認"""
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=10,
            msg="Debug",
            args=(),
            exc_info=None,
        )
        result = self.formatter.format(record)
        assert "\033[36m" in result  # cyan

    def test_format_warning(self):
        """WARNINGレベルのカラー確認"""
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning",
            args=(),
            exc_info=None,
        )
        result = self.formatter.format(record)
        assert "\033[33m" in result  # yellow

    def test_format_error(self):
        """ERRORレベルのカラー確認"""
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error",
            args=(),
            exc_info=None,
        )
        result = self.formatter.format(record)
        assert "\033[31m" in result  # red

    def test_format_critical(self):
        """CRITICALレベルのカラー確認"""
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=10,
            msg="Critical",
            args=(),
            exc_info=None,
        )
        result = self.formatter.format(record)
        assert "\033[95m" in result  # magenta

    def test_format_with_exception(self):
        """例外情報付きフォーマット確認"""
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error",
            args=(),
            exc_info=exc_info,
        )
        result = self.formatter.format(record)
        assert "ValueError" in result
        assert "Test error" in result

    def test_format_unknown_level(self):
        """未知のログレベルの場合のカラー確認"""
        record = logging.LogRecord(
            name="test",
            level=99,  # 未知のレベル
            pathname="test.py",
            lineno=10,
            msg="Unknown level",
            args=(),
            exc_info=None,
        )
        record.levelname = "UNKNOWN"
        result = self.formatter.format(record)
        # RESET colorが使用される
        assert "Unknown level" in result


class TestCryptoBotLogger:
    """CryptoBotLoggerのテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        # 環境変数をクリア
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_basic_instantiation(self, mock_get_config):
        """基本インスタンス化テスト"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")
        assert logger.name == "test_bot"
        assert logger.logger is not None
        assert logger._discord_manager is None

    @patch("src.core.config.get_config")
    def test_instantiation_with_env_log_level(self, mock_get_config):
        """環境変数によるログレベル設定"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        os.environ["LOG_LEVEL"] = "WARNING"
        logger = CryptoBotLogger("test_bot")
        assert logger.logger.level == logging.WARNING

    @patch("src.core.config.get_config")
    def test_set_discord_manager(self, mock_get_config):
        """Discord通知マネージャー設定"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")
        mock_manager = MagicMock()
        logger.set_discord_manager(mock_manager)
        assert logger._discord_manager == mock_manager

    @patch("src.core.config.get_config")
    def test_set_discord_notifier_new_system(self, mock_get_config):
        """新Discord通知システム設定（互換性）"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")
        mock_notifier = MagicMock()
        mock_notifier.send_simple_message = MagicMock()
        logger.set_discord_notifier(mock_notifier)
        assert logger._discord_manager == mock_notifier

    @patch("src.core.config.get_config")
    def test_set_discord_notifier_old_system(self, mock_get_config):
        """旧Discord通知システム設定（警告発生）"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")
        mock_notifier = MagicMock(spec=[])  # send_simple_messageなし
        logger.set_discord_notifier(mock_notifier)
        # 警告が出力されるが、_discord_managerは設定されない
        assert logger._discord_manager is None

    @patch("src.core.config.get_config")
    def test_debug_log(self, mock_get_config):
        """DEBUGログ出力"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger.logger, "log") as mock_log:
            logger.debug("Debug message", extra_data={"key": "value"})
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.DEBUG
            assert call_args[0][1] == "Debug message"

    @patch("src.core.config.get_config")
    def test_info_log(self, mock_get_config):
        """INFOログ出力"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger.logger, "log") as mock_log:
            logger.info("Info message", extra_data={"key": "value"})
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.INFO

    @patch("src.core.config.get_config")
    def test_warning_log(self, mock_get_config):
        """WARNINGログ出力"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger.logger, "log") as mock_log:
            logger.warning("Warning message")
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.WARNING

    @patch("src.core.config.get_config")
    def test_error_log(self, mock_get_config):
        """ERRORログ出力"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger.logger, "log") as mock_log:
            logger.error("Error message", error=ValueError("test error"))
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.ERROR

    @patch("src.core.config.get_config")
    def test_critical_log(self, mock_get_config):
        """CRITICALログ出力"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger.logger, "log") as mock_log:
            logger.critical("Critical message", error=RuntimeError("critical error"))
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][0] == logging.CRITICAL

    @patch("src.core.config.get_config")
    def test_log_with_cryptobot_error(self, mock_get_config):
        """CryptoBotError付きログ出力"""
        from src.core.exceptions import CryptoBotError

        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")
        crypto_error = CryptoBotError("Test crypto error", error_code="E001")

        with patch.object(logger.logger, "log") as mock_log:
            logger.error("Error message", error=crypto_error)
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            # extra引数にerror_contextが含まれる
            assert "extra" in call_args[1]

    @patch("src.core.config.get_config")
    def test_backtest_mode_info_skip(self, mock_get_config):
        """バックテストモード時のINFOログスキップ"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        os.environ["BACKTEST_MODE"] = "true"
        logger = CryptoBotLogger("test_bot")

        with patch.object(logger.logger, "log") as mock_log:
            logger.info("Info message (should be skipped)")
            mock_log.assert_not_called()

    @patch("src.core.config.get_config")
    def test_backtest_mode_warning_not_skip(self, mock_get_config):
        """バックテストモード時のWARNINGログは出力"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        os.environ["BACKTEST_MODE"] = "true"
        logger = CryptoBotLogger("test_bot")

        with patch.object(logger.logger, "log") as mock_log:
            logger.warning("Warning message (should not be skipped)")
            mock_log.assert_called_once()


class TestConditionalLog:
    """conditional_logメソッドのテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_conditional_log_normal_mode(self, mock_get_config):
        """通常モード時のconditional_log"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "error") as mock_error:
            logger.conditional_log("Test message", level="error", backtest_level="debug")
            mock_error.assert_called_once()

    @patch("src.core.config.get_config")
    def test_conditional_log_backtest_mode(self, mock_get_config):
        """バックテストモード時のconditional_log"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        os.environ["BACKTEST_MODE"] = "true"
        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "debug") as mock_debug:
            logger.conditional_log("Test message", level="error", backtest_level="debug")
            mock_debug.assert_called_once()

    @patch("src.core.config.get_config")
    def test_conditional_log_warning(self, mock_get_config):
        """conditional_logでWARNINGレベル"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "warning") as mock_warning:
            logger.conditional_log("Test message", level="warning", backtest_level="debug")
            mock_warning.assert_called_once()

    @patch("src.core.config.get_config")
    def test_conditional_log_info(self, mock_get_config):
        """conditional_logでINFOレベル"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "info") as mock_info:
            logger.conditional_log("Test message", level="info", backtest_level="debug")
            mock_info.assert_called_once()

    @patch("src.core.config.get_config")
    def test_conditional_log_critical(self, mock_get_config):
        """conditional_logでCRITICALレベル"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "critical") as mock_critical:
            logger.conditional_log("Test message", level="critical", backtest_level="debug")
            mock_critical.assert_called_once()

    @patch("src.core.config.get_config")
    def test_conditional_log_unknown_level(self, mock_get_config):
        """conditional_logで未知のレベル（デフォルトINFO）"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "info") as mock_info:
            logger.conditional_log("Test message", level="unknown", backtest_level="debug")
            mock_info.assert_called_once()


class TestLogTrade:
    """log_tradeメソッドのテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_log_trade_success(self, mock_get_config):
        """取引成功ログ"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "info") as mock_info:
            logger.log_trade(
                action="BUY",
                symbol="BTC_JPY",
                amount=0.001,
                price=5000000,
                order_id="12345",
                success=True,
            )
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "取引実行" in call_args[0][0]
            assert "BUY" in call_args[0][0]

    @patch("src.core.config.get_config")
    def test_log_trade_failure(self, mock_get_config):
        """取引失敗ログ"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "error") as mock_error:
            logger.log_trade(
                action="SELL",
                symbol="BTC_JPY",
                amount=0.001,
                price=5000000,
                order_id="12345",
                success=False,
            )
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            assert "取引失敗" in call_args[0][0]


class TestLogSignal:
    """log_signalメソッドのテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_log_signal_with_symbol(self, mock_get_config):
        """シンボル指定ありのシグナルログ"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "info") as mock_info:
            logger.log_signal(
                strategy="ATRBased",
                signal="BUY",
                confidence=0.85,
                symbol="BTC_JPY",
            )
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "シグナル生成" in call_args[0][0]
            assert "ATRBased" in call_args[0][0]

    @patch("src.core.config.get_config")
    def test_log_signal_without_symbol(self, mock_get_config):
        """シンボル指定なしのシグナルログ（設定から取得）"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_config.exchange.symbol = "ETH_JPY"
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "info") as mock_info:
            logger.log_signal(
                strategy="BBReversal",
                signal="SELL",
                confidence=0.75,
            )
            mock_info.assert_called_once()

    @patch("src.core.config.get_config")
    def test_log_signal_config_error_fallback(self, mock_get_config):
        """設定取得エラー時のフォールバック"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        # log_signal内のget_config呼び出しで例外発生させる
        with patch("src.core.config.get_config", side_effect=Exception("Config error")):
            with patch.object(logger, "info") as mock_info:
                logger.log_signal(
                    strategy="BBReversal",
                    signal="HOLD",
                    confidence=0.5,
                )
                mock_info.assert_called_once()
                # extra_dataにBTC/JPY（フォールバック）が含まれる
                call_args = mock_info.call_args
                assert call_args[1]["extra_data"]["symbol"] == "BTC/JPY"


class TestLogPerformance:
    """log_performanceメソッドのテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_log_performance(self, mock_get_config):
        """パフォーマンスログ"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = CryptoBotLogger("test_bot")

        with patch.object(logger, "info") as mock_info:
            logger.log_performance(
                total_pnl=50000.0,
                win_rate=0.65,
                trade_count=100,
                max_drawdown=0.08,
            )
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "パフォーマンス" in call_args[0][0]
            assert "50000" in call_args[0][0]


class TestGlobalFunctions:
    """グローバル関数のテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_get_logger_creates_instance(self, mock_get_config):
        """get_loggerが新規インスタンスを作成"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = get_logger("test_bot")
        assert logger is not None
        assert isinstance(logger, CryptoBotLogger)

    @patch("src.core.config.get_config")
    def test_get_logger_returns_same_instance(self, mock_get_config):
        """get_loggerが同一インスタンスを返す"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger1 = get_logger("test_bot")
        logger2 = get_logger("test_bot")
        assert logger1 is logger2

    @patch("src.core.config.get_config")
    def test_setup_logging(self, mock_get_config):
        """setup_loggingが新規インスタンスを作成"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger = setup_logging("new_bot")
        assert logger is not None
        assert isinstance(logger, CryptoBotLogger)
        assert logger.name == "new_bot"

    @patch("src.core.config.get_config")
    def test_setup_logging_replaces_instance(self, mock_get_config):
        """setup_loggingがインスタンスを置き換える"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        logger1 = get_logger("test_bot")
        logger2 = setup_logging("new_bot")
        logger3 = get_logger()

        assert logger2 is logger3
        assert logger2.name == "new_bot"


class TestFileHandler:
    """ファイルハンドラーのテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_file_config")
    @patch("src.core.config.get_config")
    def test_file_handler_setup(self, mock_get_config, mock_get_file_config):
        """ファイルハンドラーのセットアップ"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = True
        mock_config.logging.retention_days = 14
        mock_get_config.return_value = mock_config
        mock_get_file_config.return_value = 14

        logger = CryptoBotLogger("test_file_bot")

        # ファイルハンドラーが追加されていることを確認
        file_handlers = [
            h
            for h in logger.logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 1

    @patch("src.core.config.get_file_config")
    @patch("src.core.config.get_config")
    def test_file_handler_retention_days(self, mock_get_config, mock_get_file_config):
        """ファイルハンドラーの保持日数設定"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = True
        mock_config.logging.retention_days = 30
        mock_get_config.return_value = mock_config
        mock_get_file_config.return_value = 30

        logger = CryptoBotLogger("test_retention_bot")

        file_handlers = [
            h
            for h in logger.logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 1
        assert file_handlers[0].backupCount == 30


class TestConfigErrorHandling:
    """設定エラー時のハンドリングテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_import_error_fallback(self, mock_get_config):
        """ImportError時のフォールバック"""
        mock_get_config.side_effect = ImportError("Module not found")

        logger = CryptoBotLogger("test_import_error")
        assert logger is not None
        # デフォルト設定が使用される
        assert logger.logger.level in [logging.DEBUG, logging.INFO]

    @patch("src.core.config.get_config")
    def test_attribute_error_fallback(self, mock_get_config):
        """AttributeError時のフォールバック"""
        mock_get_config.side_effect = AttributeError("Attribute not found")

        logger = CryptoBotLogger("test_attr_error")
        assert logger is not None

    @patch("src.core.config.get_config")
    def test_file_not_found_error_fallback(self, mock_get_config):
        """FileNotFoundError時のフォールバック"""
        mock_get_config.side_effect = FileNotFoundError("Config file not found")

        logger = CryptoBotLogger("test_file_error")
        assert logger is not None

    @patch("src.core.config.get_config")
    def test_key_error_fallback(self, mock_get_config):
        """KeyError時のフォールバック"""
        mock_get_config.side_effect = KeyError("Key not found")

        logger = CryptoBotLogger("test_key_error")
        assert logger is not None

    @patch("src.core.config.get_config")
    def test_runtime_error_fallback(self, mock_get_config):
        """RuntimeError時のフォールバック"""
        mock_get_config.side_effect = RuntimeError("Runtime error")

        logger = CryptoBotLogger("test_runtime_error")
        assert logger is not None

    @patch("src.core.config.get_config")
    def test_recursion_error_fallback(self, mock_get_config):
        """RecursionError時のフォールバック（循環参照対策）"""
        mock_get_config.side_effect = RecursionError("Maximum recursion depth exceeded")

        logger = CryptoBotLogger("test_recursion_error")
        assert logger is not None


class TestSetupFileHandlerRetentionDaysNone:
    """_setup_file_handlerのretention_days=None時のテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.logger.get_file_config")
    @patch("src.core.config.get_config")
    def test_file_handler_retention_days_none(self, mock_get_config, mock_get_file_config):
        """retention_days=Noneの場合、get_file_configから取得"""
        mock_config = MagicMock()
        mock_config.logging.level = "DEBUG"
        mock_config.logging.file_enabled = True
        mock_config.logging.retention_days = None  # Noneを設定
        mock_get_config.return_value = mock_config
        mock_get_file_config.return_value = 10  # デフォルト値

        logger = CryptoBotLogger("test_retention_none_bot")

        # get_file_configが呼ばれていることを確認
        assert mock_get_file_config.called

        file_handlers = [
            h
            for h in logger.logger.handlers
            if isinstance(h, logging.handlers.TimedRotatingFileHandler)
        ]
        assert len(file_handlers) == 1


class TestDuplicateHandlerPrevention:
    """重複ハンドラー防止のテスト"""

    def setup_method(self):
        """テストごとにグローバル状態をリセット"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    def teardown_method(self):
        """テスト後にクリーンアップ"""
        import src.core.logger as logger_module

        logger_module._logger_instance = None
        os.environ.pop("LOG_LEVEL", None)
        os.environ.pop("BACKTEST_MODE", None)

    @patch("src.core.config.get_config")
    def test_no_duplicate_handlers(self, mock_get_config):
        """同名ロガーで重複ハンドラーが発生しない"""
        mock_config = MagicMock()
        mock_config.logging.level = "INFO"
        mock_config.logging.file_enabled = False
        mock_config.logging.retention_days = 7
        mock_get_config.return_value = mock_config

        # 同名で複数回インスタンス化
        logger1 = CryptoBotLogger("duplicate_test")
        handler_count1 = len(logger1.logger.handlers)

        logger2 = CryptoBotLogger("duplicate_test")
        handler_count2 = len(logger2.logger.handlers)

        # ハンドラー数が増えていないことを確認
        assert handler_count1 == handler_count2
