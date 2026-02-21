"""
BaseReporterクラスのユニットテスト
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.reporting.base_reporter import BaseReporter


@pytest.fixture
def mock_logger():
    """モックロガーを返すフィクスチャ"""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def reporter(mock_logger, tmp_path):
    """BaseReporterインスタンスを返すフィクスチャ"""
    with patch("src.core.config.threshold_manager.get_threshold") as mock_threshold:
        mock_threshold.return_value = str(tmp_path / "reports")
        reporter = BaseReporter(mock_logger)
        return reporter


class TestBaseReporterInit:
    """BaseReporter.__init__のテスト"""

    def test_init_creates_report_directory(self, mock_logger, tmp_path):
        """初期化時にレポートディレクトリが作成される"""
        report_dir = tmp_path / "test_reports"
        with patch("src.core.config.threshold_manager.get_threshold") as mock_threshold:
            mock_threshold.return_value = str(report_dir)
            reporter = BaseReporter(mock_logger)

            assert reporter.report_base_dir.exists()
            assert reporter.logger == mock_logger

    def test_init_uses_default_path(self, mock_logger, tmp_path):
        """デフォルトパスが使用される"""
        with patch("src.core.config.threshold_manager.get_threshold") as mock_threshold:
            mock_threshold.return_value = "logs/reports"
            reporter = BaseReporter(mock_logger)

            assert reporter.report_base_dir == Path("logs/reports")


class TestSaveReport:
    """save_reportメソッドのテスト"""

    @pytest.mark.asyncio
    async def test_save_report_creates_json_file(self, reporter, tmp_path):
        """JSONファイルが正常に作成される"""
        test_data = {"key": "value", "number": 123}
        result_path = await reporter.save_report(test_data, "backtest")

        assert result_path.exists()
        assert result_path.suffix == ".json"

        with open(result_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data == test_data

    @pytest.mark.asyncio
    async def test_save_report_with_prefix(self, reporter):
        """プレフィックス付きファイル名で保存される"""
        test_data = {"test": True}
        result_path = await reporter.save_report(test_data, "paper_trading", "my_prefix")

        assert "my_prefix_" in result_path.name

    @pytest.mark.asyncio
    async def test_save_report_creates_subdirectory(self, reporter):
        """report_typeに応じたサブディレクトリが作成される"""
        test_data = {"data": "test"}
        result_path = await reporter.save_report(test_data, "custom_type")

        assert "custom_type" in str(result_path.parent)
        assert result_path.parent.exists()

    @pytest.mark.asyncio
    async def test_save_report_handles_nested_data(self, reporter):
        """ネストしたデータが正常に保存される"""
        test_data = {"level1": {"level2": {"value": 42}}, "list_data": [1, 2, 3]}
        result_path = await reporter.save_report(test_data, "nested_test")

        with open(result_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["level1"]["level2"]["value"] == 42
        assert saved_data["list_data"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_save_report_handles_datetime(self, reporter):
        """datetimeオブジェクトが文字列に変換されて保存される"""
        test_data = {"timestamp": datetime.now()}
        result_path = await reporter.save_report(test_data, "datetime_test")

        with open(result_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert isinstance(saved_data["timestamp"], str)

    @pytest.mark.asyncio
    async def test_save_report_logs_success(self, reporter, mock_logger):
        """成功時にログが出力される"""
        test_data = {"key": "value"}
        await reporter.save_report(test_data, "log_test")

        mock_logger.info.assert_called()
        call_args = str(mock_logger.info.call_args)
        assert "log_test" in call_args
        assert "レポート保存" in call_args

    @pytest.mark.asyncio
    async def test_save_report_raises_on_error(self, reporter, mock_logger):
        """保存エラー時に例外が発生する"""
        with patch("builtins.open", side_effect=IOError("Cannot write file")):
            with pytest.raises(IOError):
                await reporter.save_report({"data": "test"}, "error_test")

        mock_logger.error.assert_called()


class TestSaveErrorReport:
    """save_error_reportメソッドのテスト"""

    @pytest.mark.asyncio
    async def test_save_error_report_basic(self, reporter):
        """エラーレポートが正常に保存される"""
        result_path = await reporter.save_error_report("Test error message")

        assert result_path.exists()
        assert "errors" in str(result_path.parent)
        assert "error_" in result_path.name

    @pytest.mark.asyncio
    async def test_save_error_report_content(self, reporter):
        """エラーレポートの内容が正しい"""
        error_msg = "Something went wrong"
        context = {"module": "test_module", "line": 42}
        result_path = await reporter.save_error_report(error_msg, context)

        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["error_message"] == error_msg
        assert data["context"] == context
        assert "timestamp" in data
        assert data["system_info"]["module"] == "BaseReporter"

    @pytest.mark.asyncio
    async def test_save_error_report_without_context(self, reporter):
        """コンテキストなしでエラーレポートが保存される"""
        result_path = await reporter.save_error_report("Error without context")

        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["context"] == {}

    @pytest.mark.asyncio
    async def test_save_error_report_with_complex_context(self, reporter):
        """複雑なコンテキストデータが保存される"""
        context = {
            "stack_trace": ["line1", "line2"],
            "variables": {"x": 10, "y": 20},
            "nested": {"level": 1},
        }
        result_path = await reporter.save_error_report("Complex error", context)

        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["context"]["stack_trace"] == ["line1", "line2"]
        assert data["context"]["variables"]["x"] == 10


class TestEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.asyncio
    async def test_special_characters_in_data(self, reporter):
        """特殊文字を含むデータの保存"""
        data = {
            "japanese": "日本語テスト",
            "emoji": "テスト",
            "special": "!@#$%^&*()",
            "newline": "line1\nline2",
        }
        result_path = await reporter.save_report(data, "special_chars")

        with open(result_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert saved_data["japanese"] == "日本語テスト"
        assert saved_data["special"] == "!@#$%^&*()"

    @pytest.mark.asyncio
    async def test_large_data(self, reporter):
        """大量のデータの保存"""
        data = {f"key_{i}": f"value_{i}" for i in range(100)}
        result_path = await reporter.save_report(data, "large_data")

        with open(result_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        assert len(saved_data) == 100


class TestReportIntegration:
    """統合テスト"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, reporter):
        """完全なワークフローテスト"""
        # 1. データ作成
        test_data = {"metrics": {"profit": 1000, "trades": 50}, "summary": "Test run completed"}

        # 2. JSONレポート保存
        json_path = await reporter.save_report(test_data, "integration", "workflow")
        assert json_path.exists()

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, reporter, mock_logger):
        """エラー発生時のワークフロー"""
        # エラーレポート保存
        error_path = await reporter.save_error_report(
            "Integration test error", {"step": "test_step", "iteration": 5}
        )
        assert error_path.exists()

        # エラーレポートの内容確認
        with open(error_path, "r", encoding="utf-8") as f:
            error_data = json.load(f)

        assert error_data["error_message"] == "Integration test error"
        assert error_data["context"]["step"] == "test_step"
