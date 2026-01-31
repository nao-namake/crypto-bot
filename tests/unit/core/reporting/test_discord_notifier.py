"""
DiscordNotifierクラスのユニットテスト

src/core/reporting/discord_notifier.pyのカバレッジ向上（80%以上目標）
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import requests

from src.core.reporting.discord_notifier import (
    DiscordClient,
    DiscordManager,
    notify,
)

# =============================================================================
# フィクスチャ
# =============================================================================


@pytest.fixture
def valid_webhook_url():
    """有効なWebhook URLを返すフィクスチャ"""
    return (
        "https://discord.com/api/webhooks/1234567890123456789/abcdefghijklmnopqrstuvwxyz1234567890"
    )


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
def discord_client(valid_webhook_url, mock_logger):
    """有効なDiscordClientインスタンスを返すフィクスチャ"""
    with patch("logging.getLogger", return_value=mock_logger):
        client = DiscordClient(valid_webhook_url)
    return client


@pytest.fixture
def discord_manager(valid_webhook_url, mock_logger):
    """有効なDiscordManagerインスタンスを返すフィクスチャ"""
    with patch("logging.getLogger", return_value=mock_logger):
        with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
            manager = DiscordManager(valid_webhook_url)
    return manager


# =============================================================================
# DiscordClient.__init__ テスト
# =============================================================================


class TestDiscordClientInit:
    """DiscordClient.__init__のテスト"""

    def test_init_with_valid_url(self, valid_webhook_url, mock_logger):
        """有効なWebhook URLで初期化"""
        with patch("logging.getLogger", return_value=mock_logger):
            client = DiscordClient(valid_webhook_url)

        assert client.enabled is True
        assert client.webhook_url == valid_webhook_url

    def test_init_without_url(self, mock_logger):
        """Webhook URLなしで初期化（無効化される）"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch.object(DiscordClient, "_get_webhook_url", return_value=None):
                client = DiscordClient()

        assert client.enabled is False

    def test_init_with_invalid_url(self, mock_logger):
        """無効なWebhook URLで初期化（無効化される）"""
        with patch("logging.getLogger", return_value=mock_logger):
            client = DiscordClient("https://invalid-url.com/webhook")

        assert client.enabled is False

    def test_init_with_short_url(self, mock_logger):
        """短すぎるWebhook URLで初期化"""
        with patch("logging.getLogger", return_value=mock_logger):
            client = DiscordClient("https://discord.com/api/webhooks/123/abc")

        assert client.enabled is False


# =============================================================================
# DiscordClient._get_webhook_url テスト
# =============================================================================


class TestGetWebhookUrl:
    """_get_webhook_urlのテスト"""

    def test_get_webhook_url_from_argument(self, valid_webhook_url, mock_logger):
        """引数からWebhook URLを取得"""
        with patch("logging.getLogger", return_value=mock_logger):
            client = DiscordClient.__new__(DiscordClient)
            client.logger = mock_logger
            result = client._get_webhook_url(valid_webhook_url)

        assert result == valid_webhook_url

    def test_get_webhook_url_from_env_file(self, valid_webhook_url, mock_logger, tmp_path):
        """envファイルからWebhook URLを取得"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.DOTENV_AVAILABLE", True):
                with patch("src.core.reporting.discord_notifier.load_dotenv"):
                    with patch.object(Path, "exists", return_value=True):
                        with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": valid_webhook_url}):
                            client = DiscordClient.__new__(DiscordClient)
                            client.logger = mock_logger
                            result = client._get_webhook_url(None)

        assert result == valid_webhook_url

    def test_get_webhook_url_from_environment_variable(self, valid_webhook_url, mock_logger):
        """環境変数からWebhook URLを取得"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch.object(Path, "exists", return_value=False):
                with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": valid_webhook_url}):
                    client = DiscordClient.__new__(DiscordClient)
                    client.logger = mock_logger
                    result = client._get_webhook_url(None)

        assert result == valid_webhook_url

    def test_get_webhook_url_from_txt_file(self, valid_webhook_url, mock_logger, tmp_path):
        """txtファイルからWebhook URLを取得"""
        txt_file = tmp_path / "discord_webhook.txt"
        txt_file.write_text(valid_webhook_url)

        with patch("logging.getLogger", return_value=mock_logger):
            with patch.dict(os.environ, {}, clear=True):
                # 環境変数をクリア
                if "DISCORD_WEBHOOK_URL" in os.environ:
                    del os.environ["DISCORD_WEBHOOK_URL"]
                with patch("src.core.reporting.discord_notifier.Path") as mock_path:
                    # envファイルは存在しない
                    env_path_mock = MagicMock()
                    env_path_mock.exists.return_value = False
                    # txtファイルは存在する
                    txt_path_mock = MagicMock()
                    txt_path_mock.exists.return_value = True
                    txt_path_mock.read_text.return_value = valid_webhook_url

                    def path_side_effect(arg):
                        if "discord_webhook.txt" in str(arg):
                            return txt_path_mock
                        return env_path_mock

                    mock_path.side_effect = path_side_effect

                    client = DiscordClient.__new__(DiscordClient)
                    client.logger = mock_logger
                    result = client._get_webhook_url(None)

        assert result == valid_webhook_url

    def test_get_webhook_url_not_found(self, mock_logger):
        """Webhook URLが見つからない場合"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch.object(Path, "exists", return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    # 環境変数をクリア
                    env_copy = os.environ.copy()
                    if "DISCORD_WEBHOOK_URL" in env_copy:
                        del env_copy["DISCORD_WEBHOOK_URL"]
                    with patch.dict(os.environ, env_copy, clear=True):
                        client = DiscordClient.__new__(DiscordClient)
                        client.logger = mock_logger
                        result = client._get_webhook_url(None)

        assert result is None

    def test_get_webhook_url_cleans_whitespace(self, valid_webhook_url, mock_logger):
        """Webhook URLの前後の空白を除去"""
        url_with_whitespace = f"  {valid_webhook_url}  \n\r"
        with patch("logging.getLogger", return_value=mock_logger):
            with patch.object(Path, "exists", return_value=False):
                with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": url_with_whitespace}):
                    client = DiscordClient.__new__(DiscordClient)
                    client.logger = mock_logger
                    result = client._get_webhook_url(None)

        assert result == valid_webhook_url

    def test_get_webhook_url_env_file_error(self, mock_logger):
        """envファイル読み込みエラー時"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.DOTENV_AVAILABLE", True):
                with patch(
                    "src.core.reporting.discord_notifier.load_dotenv",
                    side_effect=Exception("Load error"),
                ):
                    with patch.object(Path, "exists", return_value=True):
                        with patch.dict(os.environ, {}, clear=True):
                            client = DiscordClient.__new__(DiscordClient)
                            client.logger = mock_logger
                            result = client._get_webhook_url(None)

        # エラーでもNoneを返す（警告ログ出力）
        assert result is None

    def test_get_webhook_url_txt_file_error(self, mock_logger):
        """txtファイル読み込みエラー時"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch.object(Path, "exists", return_value=False):
                with patch.dict(os.environ, {}, clear=True):
                    with patch("src.core.reporting.discord_notifier.Path") as mock_path:
                        env_path_mock = MagicMock()
                        env_path_mock.exists.return_value = False
                        txt_path_mock = MagicMock()
                        txt_path_mock.exists.return_value = True
                        txt_path_mock.read_text.side_effect = IOError("Read error")

                        def path_side_effect(arg):
                            if "discord_webhook.txt" in str(arg):
                                return txt_path_mock
                            return env_path_mock

                        mock_path.side_effect = path_side_effect

                        client = DiscordClient.__new__(DiscordClient)
                        client.logger = mock_logger
                        result = client._get_webhook_url(None)

        assert result is None


# =============================================================================
# DiscordClient._validate_webhook_url テスト
# =============================================================================


class TestValidateWebhookUrl:
    """_validate_webhook_urlのテスト"""

    def test_validate_valid_url(self, discord_client, valid_webhook_url):
        """有効なURLの検証"""
        assert discord_client._validate_webhook_url(valid_webhook_url) is True

    def test_validate_non_string_url(self, discord_client):
        """文字列でないURLの検証"""
        assert discord_client._validate_webhook_url(12345) is False
        assert discord_client._validate_webhook_url(None) is False

    def test_validate_wrong_prefix_url(self, discord_client):
        """誤ったプレフィックスのURLの検証"""
        assert (
            discord_client._validate_webhook_url("https://example.com/api/webhooks/123/abc")
            is False
        )

    def test_validate_short_url(self, discord_client):
        """短すぎるURLの検証"""
        assert discord_client._validate_webhook_url("https://discord.com/api/webhooks/") is False

    def test_validate_missing_token(self, discord_client):
        """トークンがないURLの検証"""
        assert (
            discord_client._validate_webhook_url(
                "https://discord.com/api/webhooks/1234567890123456789"
            )
            is False
        )

    def test_validate_invalid_id_format(self, discord_client):
        """IDが数字でないURLの検証"""
        assert (
            discord_client._validate_webhook_url("https://discord.com/api/webhooks/abc/token123")
            is False
        )

    def test_validate_short_id(self, discord_client):
        """IDが短すぎるURLの検証"""
        assert (
            discord_client._validate_webhook_url("https://discord.com/api/webhooks/123/token123456")
            is False
        )

    def test_validate_short_token(self, discord_client):
        """トークンが短すぎるURLの検証"""
        assert (
            discord_client._validate_webhook_url(
                "https://discord.com/api/webhooks/1234567890123456789/ab"
            )
            is False
        )


# =============================================================================
# DiscordClient.send_message テスト
# =============================================================================


class TestSendMessage:
    """send_messageのテスト"""

    def test_send_message_disabled(self, mock_logger):
        """無効化されている場合"""
        with patch("logging.getLogger", return_value=mock_logger):
            client = DiscordClient.__new__(DiscordClient)
            client.logger = mock_logger
            client.enabled = False

        result = client.send_message("Test message")
        assert result is False

    def test_send_message_info(self, discord_client):
        """infoレベルメッセージ送信"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_message("Test message", "info")

        assert result is True
        mock_send.assert_called_once()
        payload = mock_send.call_args[0][0]
        assert payload["embeds"][0]["color"] == 0x3498DB  # 青色

    def test_send_message_warning(self, discord_client):
        """warningレベルメッセージ送信"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_message("Warning message", "warning")

        assert result is True
        payload = mock_send.call_args[0][0]
        assert payload["embeds"][0]["color"] == 0xF39C12  # 黄色

    def test_send_message_critical(self, discord_client):
        """criticalレベルメッセージ送信"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_message("Critical message", "critical")

        assert result is True
        payload = mock_send.call_args[0][0]
        assert payload["embeds"][0]["color"] == 0xE74C3C  # 赤色

    def test_send_message_unknown_level(self, discord_client):
        """不明なレベルメッセージ送信（デフォルト使用）"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_message("Unknown level", "unknown")

        assert result is True
        payload = mock_send.call_args[0][0]
        assert payload["embeds"][0]["color"] == 0x3498DB  # デフォルト青色


# =============================================================================
# DiscordClient.send_embed テスト
# =============================================================================


class TestSendEmbed:
    """send_embedのテスト"""

    def test_send_embed_disabled(self, mock_logger):
        """無効化されている場合"""
        with patch("logging.getLogger", return_value=mock_logger):
            client = DiscordClient.__new__(DiscordClient)
            client.logger = mock_logger
            client.enabled = False

        result = client.send_embed("Title", "Description")
        assert result is False

    def test_send_embed_basic(self, discord_client):
        """基本的なEmbed送信"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_embed("Test Title", "Test Description")

        assert result is True
        payload = mock_send.call_args[0][0]
        assert "Test Title" in payload["embeds"][0]["title"]
        assert payload["embeds"][0]["description"] == "Test Description"

    def test_send_embed_with_fields(self, discord_client):
        """フィールド付きEmbed送信"""
        fields = [
            {"name": "Field1", "value": "Value1", "inline": True},
            {"name": "Field2", "value": "Value2", "inline": False},
        ]
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_embed("Title", "Description", fields=fields)

        assert result is True
        payload = mock_send.call_args[0][0]
        assert payload["embeds"][0]["fields"] == fields

    def test_send_embed_with_image_url(self, discord_client):
        """画像URL付きEmbed送信"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_embed(
                "Title", "Description", image_url="https://example.com/image.png"
            )

        assert result is True
        payload = mock_send.call_args[0][0]
        assert payload["embeds"][0]["image"]["url"] == "https://example.com/image.png"

    def test_send_embed_with_all_options(self, discord_client):
        """全オプション付きEmbed送信"""
        fields = [{"name": "Field", "value": "Value", "inline": True}]
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_embed(
                "Title",
                "Description",
                fields=fields,
                level="warning",
                image_url="https://example.com/image.png",
            )

        assert result is True
        payload = mock_send.call_args[0][0]
        assert payload["embeds"][0]["color"] == 0xF39C12
        assert "fields" in payload["embeds"][0]
        assert "image" in payload["embeds"][0]


# =============================================================================
# DiscordClient.send_webhook_with_file テスト
# =============================================================================


class TestSendWebhookWithFile:
    """send_webhook_with_fileのテスト"""

    def test_send_webhook_with_file_disabled(self, mock_logger):
        """無効化されている場合"""
        with patch("logging.getLogger", return_value=mock_logger):
            client = DiscordClient.__new__(DiscordClient)
            client.logger = mock_logger
            client.enabled = False

        result = client.send_webhook_with_file("Title", "Description")
        assert result is False

    def test_send_webhook_with_file_no_file(self, discord_client):
        """ファイルなしで送信"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_webhook_with_file("Title", "Description")

        assert result is True
        mock_send.assert_called_once()

    def test_send_webhook_with_file_success(self, discord_client, tmp_path):
        """ファイル添付で送信成功"""
        # テストファイル作成
        test_file = tmp_path / "test_chart.png"
        test_file.write_bytes(b"fake png content")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = discord_client.send_webhook_with_file(
                "Title", "Description", file_path=str(test_file)
            )

        assert result is True
        mock_post.assert_called_once()

    def test_send_webhook_with_file_api_error(self, discord_client, tmp_path):
        """ファイル添付でAPIエラー"""
        test_file = tmp_path / "test_chart.png"
        test_file.write_bytes(b"fake png content")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("requests.post", return_value=mock_response):
            result = discord_client.send_webhook_with_file(
                "Title", "Description", file_path=str(test_file)
            )

        assert result is False

    def test_send_webhook_with_file_exception(self, discord_client, tmp_path):
        """ファイル添付で例外発生"""
        test_file = tmp_path / "test_chart.png"
        test_file.write_bytes(b"fake png content")

        with patch("requests.post", side_effect=Exception("Network error")):
            result = discord_client.send_webhook_with_file(
                "Title", "Description", file_path=str(test_file)
            )

        assert result is False

    def test_send_webhook_with_file_nonexistent(self, discord_client):
        """存在しないファイルで送信"""
        with patch.object(discord_client, "_send_webhook", return_value=True) as mock_send:
            result = discord_client.send_webhook_with_file(
                "Title", "Description", file_path="/nonexistent/file.png"
            )

        # ファイルが存在しない場合は通常送信にフォールバック
        assert result is True
        mock_send.assert_called_once()

    def test_send_webhook_with_file_and_fields(self, discord_client, tmp_path):
        """フィールド付きファイル添付"""
        test_file = tmp_path / "test_chart.png"
        test_file.write_bytes(b"fake png content")

        fields = [{"name": "Field", "value": "Value", "inline": True}]
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = discord_client.send_webhook_with_file(
                "Title", "Description", fields=fields, file_path=str(test_file)
            )

        assert result is True


# =============================================================================
# DiscordClient._send_webhook テスト
# =============================================================================


class TestSendWebhook:
    """_send_webhookのテスト"""

    def test_send_webhook_success_200(self, discord_client):
        """200レスポンスで成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is True

    def test_send_webhook_success_204(self, discord_client):
        """204レスポンスで成功"""
        mock_response = MagicMock()
        mock_response.status_code = 204

        with patch("requests.post", return_value=mock_response):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is True

    def test_send_webhook_error_400(self, discord_client):
        """400エラー"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("requests.post", return_value=mock_response):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is False

    def test_send_webhook_error_401(self, discord_client):
        """401エラー"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("requests.post", return_value=mock_response):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is False

    def test_send_webhook_error_429(self, discord_client):
        """429 Rate Limit"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate Limited"

        with patch("requests.post", return_value=mock_response):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is False

    def test_send_webhook_error_500(self, discord_client):
        """500エラー"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"

        with patch("requests.post", return_value=mock_response):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is False

    def test_send_webhook_network_error(self, discord_client):
        """ネットワークエラー"""
        with patch(
            "requests.post", side_effect=requests.exceptions.RequestException("Network error")
        ):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is False

    def test_send_webhook_unexpected_error(self, discord_client):
        """予期しないエラー"""
        with patch("requests.post", side_effect=Exception("Unexpected error")):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=10
            ):
                result = discord_client._send_webhook({"test": "data"})

        assert result is False

    def test_send_webhook_json_error(self, discord_client):
        """JSON変換エラー"""
        # 循環参照を持つオブジェクトを作成
        circular_data = {}
        circular_data["self"] = circular_data

        with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=10):
            result = discord_client._send_webhook(circular_data)

        assert result is False


# =============================================================================
# DiscordClient._get_iso_timestamp テスト
# =============================================================================


class TestGetIsoTimestamp:
    """_get_iso_timestampのテスト"""

    def test_get_iso_timestamp_format(self, discord_client):
        """ISO形式タイムスタンプの取得"""
        result = discord_client._get_iso_timestamp()

        # ISO形式であることを確認
        assert "T" in result
        assert "+" in result or "Z" in result or "-" in result[10:]  # タイムゾーン情報


# =============================================================================
# DiscordClient.test_connection テスト
# =============================================================================


class TestClientTestConnection:
    """test_connectionのテスト"""

    def test_connection_success(self, discord_client):
        """接続テスト成功"""
        with patch.object(discord_client, "send_message", return_value=True):
            result = discord_client.test_connection()

        assert result is True

    def test_connection_failure(self, discord_client):
        """接続テスト失敗"""
        with patch.object(discord_client, "send_message", return_value=False):
            result = discord_client.test_connection()

        assert result is False


# =============================================================================
# DiscordManager.__init__ テスト
# =============================================================================


class TestDiscordManagerInit:
    """DiscordManager.__init__のテスト"""

    def test_init_enabled(self, valid_webhook_url, mock_logger):
        """有効な状態で初期化"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
                manager = DiscordManager(valid_webhook_url)

        assert manager.enabled is True
        assert manager.client.enabled is True

    def test_init_disabled(self, mock_logger):
        """無効な状態で初期化"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
                with patch.object(DiscordClient, "_get_webhook_url", return_value=None):
                    manager = DiscordManager()

        assert manager.enabled is False


# =============================================================================
# DiscordManager.send_simple_message テスト
# =============================================================================


class TestSendSimpleMessage:
    """send_simple_messageのテスト"""

    def test_send_simple_message_success(self, discord_manager):
        """メッセージ送信成功"""
        with patch.object(discord_manager.client, "send_message", return_value=True):
            # Rate limitをリセット
            discord_manager._last_send_time = 0
            result = discord_manager.send_simple_message("Test message")

        assert result is True

    def test_send_simple_message_rate_limited(self, discord_manager):
        """Rate Limitで送信ブロック"""
        discord_manager._last_send_time = time.time()  # 直前に送信した状態
        result = discord_manager.send_simple_message("Test message")

        assert result is False

    def test_send_simple_message_disabled(self, mock_logger):
        """無効化されている場合"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
                with patch.object(DiscordClient, "_get_webhook_url", return_value=None):
                    manager = DiscordManager()

        result = manager.send_simple_message("Test message")
        assert result is False


# =============================================================================
# DiscordManager.send_embed テスト
# =============================================================================


class TestManagerSendEmbed:
    """DiscordManager.send_embedのテスト"""

    def test_send_embed_success(self, discord_manager):
        """Embed送信成功"""
        with patch.object(discord_manager.client, "send_embed", return_value=True):
            discord_manager._last_send_time = 0
            result = discord_manager.send_embed("Title", "Description")

        assert result is True

    def test_send_embed_rate_limited(self, discord_manager):
        """Rate Limitで送信ブロック"""
        discord_manager._last_send_time = time.time()
        result = discord_manager.send_embed("Title", "Description")

        assert result is False


# =============================================================================
# DiscordManager.send_webhook_with_file テスト
# =============================================================================


class TestManagerSendWebhookWithFile:
    """DiscordManager.send_webhook_with_fileのテスト"""

    def test_send_webhook_with_file_success(self, discord_manager):
        """ファイル添付送信成功"""
        with patch.object(discord_manager.client, "send_webhook_with_file", return_value=True):
            discord_manager._last_send_time = 0
            result = discord_manager.send_webhook_with_file("Title", "Description")

        assert result is True

    def test_send_webhook_with_file_rate_limited(self, discord_manager):
        """Rate Limitで送信ブロック"""
        discord_manager._last_send_time = time.time()
        result = discord_manager.send_webhook_with_file("Title", "Description")

        assert result is False


# =============================================================================
# DiscordManager.test_connection テスト
# =============================================================================


class TestManagerTestConnection:
    """DiscordManager.test_connectionのテスト"""

    def test_connection_success(self, discord_manager):
        """接続テスト成功"""
        with patch.object(discord_manager.client, "test_connection", return_value=True):
            result = discord_manager.test_connection()

        assert result is True

    def test_connection_disabled(self, mock_logger):
        """無効化されている場合"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
                with patch.object(DiscordClient, "_get_webhook_url", return_value=None):
                    manager = DiscordManager()

        result = manager.test_connection()
        assert result is False


# =============================================================================
# DiscordManager._rate_limit_check テスト
# =============================================================================


class TestRateLimitCheck:
    """_rate_limit_checkのテスト"""

    def test_rate_limit_check_allowed(self, discord_manager):
        """Rate Limit内で許可"""
        discord_manager._last_send_time = 0  # 過去に設定
        result = discord_manager._rate_limit_check()

        assert result is True

    def test_rate_limit_check_blocked(self, discord_manager):
        """Rate Limitでブロック"""
        discord_manager._last_send_time = time.time()  # 現在時刻
        result = discord_manager._rate_limit_check()

        assert result is False

    def test_rate_limit_check_disabled(self, mock_logger):
        """無効化されている場合"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
                with patch.object(DiscordClient, "_get_webhook_url", return_value=None):
                    manager = DiscordManager()

        result = manager._rate_limit_check()
        assert result is False


# =============================================================================
# DiscordManager.get_status テスト
# =============================================================================


class TestGetStatus:
    """get_statusのテスト"""

    def test_get_status(self, discord_manager):
        """状態取得"""
        discord_manager._last_send_time = time.time() - 10
        result = discord_manager.get_status()

        assert "enabled" in result
        assert "client_enabled" in result
        assert "last_send_ago" in result
        assert result["enabled"] is True
        assert result["last_send_ago"] >= 10


# =============================================================================
# notify関数 テスト
# =============================================================================


class TestNotifyFunction:
    """notify関数のテスト"""

    def test_notify_success(self, valid_webhook_url, mock_logger):
        """notify関数成功"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
                with patch.object(
                    DiscordClient, "_get_webhook_url", return_value=valid_webhook_url
                ):
                    with patch.object(DiscordClient, "_send_webhook", return_value=True):
                        result = notify("Test message")

        assert result is True

    def test_notify_disabled(self, mock_logger):
        """notify関数（無効化）"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=2):
                with patch.object(DiscordClient, "_get_webhook_url", return_value=None):
                    result = notify("Test message")

        assert result is False


# =============================================================================
# 統合テスト
# =============================================================================


class TestDiscordNotifierIntegration:
    """統合テスト"""

    def test_full_workflow(self, valid_webhook_url, mock_logger, tmp_path):
        """完全なワークフローテスト"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch(
                "src.core.reporting.discord_notifier.get_monitoring_config", return_value=0.1
            ):
                manager = DiscordManager(valid_webhook_url)

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.post", return_value=mock_response):
            # シンプルメッセージ送信
            result1 = manager.send_simple_message("Test message", "info")
            assert result1 is True

            # 少し待機してRate Limitをリセット
            time.sleep(0.2)

            # Embed送信
            result2 = manager.send_embed("Title", "Description", level="warning")
            assert result2 is True

            # 状態確認
            status = manager.get_status()
            assert status["enabled"] is True

    def test_error_handling_workflow(self, valid_webhook_url, mock_logger):
        """エラーハンドリングワークフロー"""
        with patch("logging.getLogger", return_value=mock_logger):
            with patch("src.core.reporting.discord_notifier.get_monitoring_config", return_value=0):
                manager = DiscordManager(valid_webhook_url)

        # 各種エラーレスポンス
        error_responses = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (429, "Rate Limited"),
            (500, "Server Error"),
        ]

        for status_code, text in error_responses:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.text = text

            with patch("requests.post", return_value=mock_response):
                result = manager.send_simple_message(f"Test {status_code}")
                assert result is False
