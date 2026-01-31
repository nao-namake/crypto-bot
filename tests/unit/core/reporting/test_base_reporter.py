"""
BaseReporterクラスのユニットテスト

src/core/reporting/base_reporter.pyのカバレッジ向上（27%→70%以上目標）
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
        test_data = {
            "level1": {
                "level2": {
                    "value": 42
                }
            },
            "list_data": [1, 2, 3]
        }
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


class TestFormatMarkdown:
    """format_markdownメソッドのテスト"""

    def test_format_markdown_basic(self, reporter):
        """基本的なマークダウン変換"""
        data = {"key1": "value1", "key2": 100}
        result = reporter.format_markdown(data, "テストレポート")

        assert "# テストレポート" in result
        assert "**key1**: value1" in result
        assert "**key2**: 100" in result

    def test_format_markdown_with_nested_dict(self, reporter):
        """ネストした辞書の変換"""
        data = {
            "section": {
                "item1": "A",
                "item2": "B"
            }
        }
        result = reporter.format_markdown(data, "Nested Report")

        assert "## section" in result
        assert "**item1**: A" in result
        assert "**item2**: B" in result

    def test_format_markdown_default_title(self, reporter):
        """デフォルトタイトルが使用される"""
        data = {"test": "data"}
        result = reporter.format_markdown(data)

        assert "# レポート" in result

    def test_format_markdown_includes_timestamp(self, reporter):
        """生成日時が含まれる"""
        data = {"key": "value"}
        result = reporter.format_markdown(data, "Test")

        assert "**生成日時**" in result
        assert "年" in result
        assert "月" in result

    def test_format_markdown_mixed_data(self, reporter):
        """トップレベルの値と辞書が混在するデータ"""
        data = {
            "simple_key": "simple_value",
            "nested_section": {
                "nested_key": "nested_value"
            },
            "another_simple": 123
        }
        result = reporter.format_markdown(data, "Mixed Report")

        assert "**simple_key**: simple_value" in result
        assert "## nested_section" in result
        assert "**nested_key**: nested_value" in result
        assert "**another_simple**: 123" in result


class TestFormatDiscordEmbed:
    """format_discord_embedメソッドのテスト"""

    def test_format_discord_embed_basic(self, reporter):
        """基本的なEmbed生成"""
        data = {"field1": "value1", "field2": 100}
        result = reporter.format_discord_embed(data, "Test Embed")

        assert result["title"] == "Test Embed"
        assert result["color"] == 0x00FF00  # デフォルト緑
        assert "timestamp" in result
        assert len(result["fields"]) == 2

    def test_format_discord_embed_custom_color(self, reporter):
        """カスタム色の指定"""
        data = {"test": "data"}
        result = reporter.format_discord_embed(data, "Error", color=0xFF0000)

        assert result["color"] == 0xFF0000

    def test_format_discord_embed_nested_dict_summary(self, reporter):
        """ネストした辞書がサマリーに変換される"""
        data = {
            "metrics": {
                "a": 1,
                "b": 2,
                "c": 3
            }
        }
        result = reporter.format_discord_embed(data, "Metrics")

        fields = result["fields"]
        assert len(fields) == 1
        assert fields[0]["name"] == "metrics"
        assert "a: 1" in fields[0]["value"]
        assert "b: 2" in fields[0]["value"]
        assert "c: 3" in fields[0]["value"]

    def test_format_discord_embed_nested_dict_truncation(self, reporter):
        """4項目以上のネスト辞書が省略される"""
        data = {
            "many_items": {
                "a": 1,
                "b": 2,
                "c": 3,
                "d": 4,
                "e": 5
            }
        }
        result = reporter.format_discord_embed(data, "Many Items")

        fields = result["fields"]
        assert "..." in fields[0]["value"]

    def test_format_discord_embed_fields_are_inline(self, reporter):
        """フィールドがinline=Trueで設定される"""
        data = {"key1": "value1", "key2": "value2"}
        result = reporter.format_discord_embed(data, "Inline Test")

        for field in result["fields"]:
            assert field["inline"] is True

    def test_format_discord_embed_converts_to_string(self, reporter):
        """非文字列値が文字列に変換される"""
        data = {"number": 42, "boolean": True, "none": None}
        result = reporter.format_discord_embed(data, "Conversion")

        for field in result["fields"]:
            assert isinstance(field["value"], str)


class TestSaveMarkdownReport:
    """save_markdown_reportメソッドのテスト"""

    @pytest.mark.asyncio
    async def test_save_markdown_report_creates_file(self, reporter):
        """マークダウンファイルが作成される"""
        data = {"key": "value"}
        result_path = await reporter.save_markdown_report(data, "md_test", "Test Title")

        assert result_path.exists()
        assert result_path.suffix == ".md"

    @pytest.mark.asyncio
    async def test_save_markdown_report_content(self, reporter):
        """正しい内容がファイルに書き込まれる"""
        data = {"metric": 100}
        result_path = await reporter.save_markdown_report(data, "content_test", "Content Check")

        with open(result_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "# Content Check" in content
        assert "**metric**: 100" in content

    @pytest.mark.asyncio
    async def test_save_markdown_report_creates_subdirectory(self, reporter):
        """サブディレクトリが作成される"""
        data = {"test": True}
        result_path = await reporter.save_markdown_report(data, "subdir_test", "Subdir Title")

        assert "subdir_test" in str(result_path.parent)
        assert result_path.parent.exists()

    @pytest.mark.asyncio
    async def test_save_markdown_report_logs_success(self, reporter, mock_logger):
        """成功時にログが出力される"""
        data = {"key": "value"}
        await reporter.save_markdown_report(data, "log_test", "Log Test")

        mock_logger.info.assert_called()
        call_args = str(mock_logger.info.call_args)
        assert "マークダウンレポート保存" in call_args

    @pytest.mark.asyncio
    async def test_save_markdown_report_raises_on_error(self, reporter, mock_logger):
        """保存エラー時に例外が発生する"""
        with patch("builtins.open", side_effect=IOError("Cannot write")):
            with pytest.raises(IOError):
                await reporter.save_markdown_report({"data": "test"}, "error", "Error Test")

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
            "nested": {"level": 1}
        }
        result_path = await reporter.save_error_report("Complex error", context)

        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["context"]["stack_trace"] == ["line1", "line2"]
        assert data["context"]["variables"]["x"] == 10


class TestGetReportSummary:
    """get_report_summaryメソッドのテスト"""

    def test_get_report_summary_basic(self, reporter):
        """基本的なサマリーが生成される"""
        data = {"key1": "value1", "key2": "value2", "key3": 100}
        result = reporter.get_report_summary(data)

        assert result["total_fields"] == 3
        assert result["has_nested_data"] is False
        assert "timestamp" in result
        assert "data_size_bytes" in result

    def test_get_report_summary_with_nested_data(self, reporter):
        """ネストしたデータを検出"""
        data = {
            "simple": "value",
            "nested": {"inner": "data"}
        }
        result = reporter.get_report_summary(data)

        assert result["has_nested_data"] is True
        assert result["total_fields"] == 2

    def test_get_report_summary_empty_data(self, reporter):
        """空のデータに対するサマリー"""
        data = {}
        result = reporter.get_report_summary(data)

        assert result["total_fields"] == 0
        assert result["has_nested_data"] is False

    def test_get_report_summary_data_size(self, reporter):
        """データサイズが正しく計算される"""
        small_data = {"a": 1}
        large_data = {"a": "x" * 1000}

        small_summary = reporter.get_report_summary(small_data)
        large_summary = reporter.get_report_summary(large_data)

        assert large_summary["data_size_bytes"] > small_summary["data_size_bytes"]

    def test_get_report_summary_timestamp_format(self, reporter):
        """タイムスタンプがISO形式"""
        data = {"test": "data"}
        result = reporter.get_report_summary(data)

        # ISO形式のタイムスタンプを検証
        timestamp = result["timestamp"]
        datetime.fromisoformat(timestamp)  # 変換できることを確認


class TestEdgeCases:
    """エッジケースのテスト"""

    @pytest.mark.asyncio
    async def test_special_characters_in_data(self, reporter):
        """特殊文字を含むデータの保存"""
        data = {
            "japanese": "日本語テスト",
            "emoji": "テスト",  # 絵文字なし（規約に従う）
            "special": "!@#$%^&*()",
            "newline": "line1\nline2"
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

    def test_format_markdown_empty_nested_dict(self, reporter):
        """空のネスト辞書の変換"""
        data = {"empty_section": {}}
        result = reporter.format_markdown(data, "Empty Section Test")

        assert "## empty_section" in result

    def test_format_discord_embed_empty_nested_dict(self, reporter):
        """空のネスト辞書のEmbed変換"""
        data = {"empty": {}}
        result = reporter.format_discord_embed(data, "Empty Nested")

        assert len(result["fields"]) == 1
        assert result["fields"][0]["name"] == "empty"
        # 空の辞書は空文字列のサマリーになる
        assert result["fields"][0]["value"] == ""

    def test_format_discord_embed_exactly_three_items(self, reporter):
        """ちょうど3項目のネスト辞書（省略なし）"""
        data = {
            "three_items": {
                "a": 1,
                "b": 2,
                "c": 3
            }
        }
        result = reporter.format_discord_embed(data, "Three Items")

        fields = result["fields"]
        assert "..." not in fields[0]["value"]


class TestReportIntegration:
    """統合テスト"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, reporter):
        """完全なワークフローテスト"""
        # 1. データ作成
        test_data = {
            "metrics": {
                "profit": 1000,
                "trades": 50
            },
            "summary": "Test run completed"
        }

        # 2. JSONレポート保存
        json_path = await reporter.save_report(test_data, "integration", "workflow")
        assert json_path.exists()

        # 3. マークダウンレポート保存
        md_path = await reporter.save_markdown_report(test_data, "integration", "Integration Test")
        assert md_path.exists()

        # 4. サマリー生成
        summary = reporter.get_report_summary(test_data)
        assert summary["total_fields"] == 2
        assert summary["has_nested_data"] is True

        # 5. Discord Embed生成
        embed = reporter.format_discord_embed(test_data, "Integration Embed")
        assert len(embed["fields"]) == 2

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, reporter, mock_logger):
        """エラー発生時のワークフロー"""
        # エラーレポート保存
        error_path = await reporter.save_error_report(
            "Integration test error",
            {"step": "test_step", "iteration": 5}
        )
        assert error_path.exists()

        # エラーレポートの内容確認
        with open(error_path, "r", encoding="utf-8") as f:
            error_data = json.load(f)

        assert error_data["error_message"] == "Integration test error"
        assert error_data["context"]["step"] == "test_step"
