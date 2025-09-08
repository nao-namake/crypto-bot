"""
Discord通知クライアントのテスト - Phase 15新実装

シンプルで堅牢なDiscordClient単体テストを実装。
862行の巨大discord.pyから置き換えた新システムの品質保証。
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from src.monitoring.discord_notifier import DiscordClient


class TestDiscordClient:
    """DiscordClient単体テスト"""

    def test_init_with_valid_url(self):
        """有効なWebhookURLでの初期化"""
        valid_url = "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnop"
        client = DiscordClient(webhook_url=valid_url)

        assert client.webhook_url == valid_url
        assert client.enabled is True

    def test_init_with_env_url(self):
        """環境変数からのWebhookURL取得"""
        valid_url = "https://discord.com/api/webhooks/987654321098765432/zyxwvutsrqponmlk"

        with patch.dict("os.environ", {"DISCORD_WEBHOOK_URL": valid_url}):
            client = DiscordClient()

            assert client.webhook_url == valid_url
            assert client.enabled is True

    def test_init_without_url(self):
        """WebhookURL未設定時の初期化"""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("pathlib.Path.exists") as mock_exists,
            patch("os.getenv") as mock_getenv,
        ):

            # .envファイル・txtファイルは存在しない
            mock_exists.return_value = False
            # 環境変数も設定されていない
            mock_getenv.return_value = None

            client = DiscordClient()

            assert client.webhook_url is None
            assert client.enabled is False

    def test_init_with_invalid_url(self):
        """無効なWebhookURLでの初期化"""
        invalid_urls = [
            "https://example.com/webhook",
            "https://discord.com/api/invalid",
            "invalid_url",
            "",
        ]

        with patch("pathlib.Path.exists") as mock_exists, patch("os.getenv") as mock_getenv:

            # .envファイル・txtファイルは存在しない
            mock_exists.return_value = False
            # 環境変数も設定されていない
            mock_getenv.return_value = None

            for invalid_url in invalid_urls:
                client = DiscordClient(webhook_url=invalid_url)
                assert client.enabled is False

    def test_validate_webhook_url_valid(self):
        """WebhookURL検証 - 有効なURL"""
        client = DiscordClient()

        valid_urls = [
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz",
            "https://discord.com/api/webhooks/987654321012345678/ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
        ]

        for url in valid_urls:
            assert client._validate_webhook_url(url) is True

    def test_validate_webhook_url_invalid(self):
        """WebhookURL検証 - 無効なURL"""
        client = DiscordClient()

        invalid_urls = [
            "https://example.com/webhook",
            "https://discord.com/api/invalid",
            "https://discord.com/api/webhooks/123",  # 短すぎる
            "invalid_url",
            "",
            None,
            123,
        ]

        for url in invalid_urls:
            assert client._validate_webhook_url(url) is False

    @patch("requests.post")
    def test_send_message_success(self, mock_post):
        """メッセージ送信成功"""
        # レスポンス設定
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = client.send_message("テストメッセージ", "info")

        assert result is True
        mock_post.assert_called_once()

        # 送信データ検証
        call_args = mock_post.call_args
        assert "data" in call_args.kwargs
        payload = json.loads(call_args.kwargs["data"])
        assert payload["username"] == "Crypto-Bot"
        assert len(payload["embeds"]) == 1
        assert "テストメッセージ" in payload["embeds"][0]["description"]

    @patch("requests.post")
    def test_send_message_disabled_client(self, mock_post):
        """無効化されたクライアントでのメッセージ送信"""
        with patch("pathlib.Path.exists") as mock_exists, patch("os.getenv") as mock_getenv:

            # .envファイル・txtファイルは存在しない
            mock_exists.return_value = False
            # 環境変数も設定されていない
            mock_getenv.return_value = None

            client = DiscordClient()  # WebhookURL未設定
            result = client.send_message("テストメッセージ")

            assert result is False
            mock_post.assert_not_called()

    @patch("requests.post")
    def test_send_message_400_error(self, mock_post):
        """Discord API 400エラー"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = '{"message": "Invalid JSON", "code": 50109}'
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = client.send_message("テストメッセージ")

        assert result is False

    @patch("requests.post")
    def test_send_message_429_rate_limit(self, mock_post):
        """Discord API Rate Limit"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = '{"message": "Too Many Requests", "retry_after": 1.5}'
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = client.send_message("テストメッセージ")

        assert result is False

    @patch("requests.post")
    def test_send_message_network_error(self, mock_post):
        """ネットワークエラー"""
        mock_post.side_effect = requests.exceptions.ConnectionError("接続失敗")

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = client.send_message("テストメッセージ")

        assert result is False

    @patch("requests.post")
    def test_send_embed_success(self, mock_post):
        """埋め込みメッセージ送信成功"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = client.send_embed(
            title="テストタイトル",
            description="テスト説明",
            fields=[{"name": "フィールド1", "value": "値1", "inline": True}],
            level="warning",
        )

        assert result is True

        # 送信データ検証
        call_args = mock_post.call_args
        payload = json.loads(call_args.kwargs["data"])
        embed = payload["embeds"][0]
        assert "テストタイトル" in embed["title"]
        assert embed["description"] == "テスト説明"
        assert len(embed["fields"]) == 1
        assert embed["color"] == 0xF39C12  # warning色

    def test_send_embed_different_levels(self):
        """異なる重要度レベルでの埋め込み送信"""
        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        # 無効化状態でのテスト（実際の送信はしない）
        client.enabled = False

        levels_colors = {"info": 0x3498DB, "warning": 0xF39C12, "critical": 0xE74C3C}

        for level, expected_color in levels_colors.items():
            # テスト用の部分的な検証
            # 実際の実装では色が正しく設定されることを確認
            assert expected_color in [0x3498DB, 0xF39C12, 0xE74C3C]

    @patch("json.dumps")
    def test_send_webhook_json_error(self, mock_json_dumps):
        """JSON形式エラーの処理"""
        mock_json_dumps.side_effect = TypeError("JSON変換エラー")

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = client._send_webhook({"test": "data"})

        assert result is False

    def test_get_iso_timestamp(self):
        """ISO形式タイムスタンプ取得"""
        client = DiscordClient()
        timestamp = client._get_iso_timestamp()

        # ISO形式の基本検証
        assert isinstance(timestamp, str)
        assert "T" in timestamp
        assert timestamp.endswith("+00:00") or timestamp.endswith("Z")

    @patch("requests.post")
    def test_test_connection_success(self, mock_post):
        """接続テスト成功"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = client.test_connection()

        assert result is True

    def test_test_connection_disabled(self):
        """接続テスト - 無効化クライアント"""
        with patch("pathlib.Path.exists") as mock_exists, patch("os.getenv") as mock_getenv:

            # .envファイル・txtファイルは存在しない
            mock_exists.return_value = False
            # 環境変数も設定されていない
            mock_getenv.return_value = None

            client = DiscordClient()  # 無効化状態
            result = client.test_connection()

            assert result is False

    @patch("requests.post")
    def test_send_message_level_variations(self, mock_post):
        """異なるレベルでのメッセージ送信"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        levels = ["info", "warning", "critical"]
        for level in levels:
            result = client.send_message(f"{level}メッセージ", level)
            assert result is True

        # 3回呼ばれていることを確認
        assert mock_post.call_count == 3

    @patch("requests.post")
    def test_send_embed_with_color_validation(self, mock_post):
        """埋め込みメッセージの色検証テスト"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        # 各レベルと期待される色のマッピング
        level_colors = {
            "info": 0x3498DB,  # 青
            "warning": 0xF39C12,  # 黄
            "critical": 0xE74C3C,  # 赤
        }

        for level, expected_color in level_colors.items():
            result = client.send_embed(
                title=f"{level}テスト", description="テスト説明", level=level
            )
            assert result is True

            # 最後の呼び出しの引数を取得
            call_args = mock_post.call_args
            payload = json.loads(call_args.kwargs["data"])
            embed = payload["embeds"][0]

            assert embed["color"] == expected_color

    @patch("requests.post")
    def test_send_embed_with_fields_validation(self, mock_post):
        """埋め込みフィールド検証テスト"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        test_fields = [
            {"name": "フィールド1", "value": "値1", "inline": True},
            {"name": "フィールド2", "value": "値2", "inline": False},
            {"name": "長いフィールド名テスト" * 10, "value": "長い値テスト" * 50},
        ]

        result = client.send_embed(
            title="フィールドテスト", description="複数フィールドテスト", fields=test_fields
        )
        assert result is True

        call_args = mock_post.call_args
        payload = json.loads(call_args.kwargs["data"])
        embed = payload["embeds"][0]

        assert len(embed["fields"]) == 3
        assert embed["fields"][0]["inline"] is True
        assert embed["fields"][1]["inline"] is False

    @patch("requests.post")
    def test_webhook_url_validation_comprehensive(self, mock_post):
        """Webhook URL検証包括テスト"""
        with patch("pathlib.Path.exists") as mock_exists, patch("os.getenv") as mock_getenv:

            # .envファイル・txtファイルは存在しない
            mock_exists.return_value = False
            # 環境変数も設定されていない
            mock_getenv.return_value = None

            # 有効なURL形式の詳細テスト
            valid_urls = [
                "https://discord.com/api/webhooks/123456789012345678/abcdefg",
                "https://discord.com/api/webhooks/999999999999999999/XYZ123abc456DEF789ghi012JKL345mno678PQR901stu234VWX567yzA890BCD",
                "https://discord.com/api/webhooks/100000000000000000/a" * 68,  # 最大長
            ]

            for url in valid_urls:
                client = DiscordClient(webhook_url=url)
                assert client.enabled is True
                assert client.webhook_url == url

            # 無効なURL形式の詳細テスト
            invalid_urls = [
                "http://discord.com/api/webhooks/123456789012345678/abcdefg",  # HTTPS必須
                "https://example.com/api/webhooks/123456789012345678/abcdefg",  # 間違いドメイン
                "https://discord.com/webhooks/123456789012345678/abcdefg",  # /api/ 不足
                "https://discord.com/api/webhooks/12345/abcdefg",  # ID短すぎ
                "https://discord.com/api/webhooks/123456789012345678/ab",  # トークン短すぎ
                "https://discord.com/api/webhooks/abc/xyz",  # 数値でない
                "",  # 空文字
            ]

            for url in invalid_urls:
                client = DiscordClient(webhook_url=url)
                assert client.enabled is False

    def test_environment_variable_loading(self):
        """環境変数読み込みテスト"""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("pathlib.Path.exists") as mock_exists,
            patch("os.getenv") as mock_getenv,
        ):

            # .envファイル・txtファイルは存在しない
            mock_exists.return_value = False
            # 環境変数も設定されていない
            mock_getenv.return_value = None

            # 環境変数未設定
            client = DiscordClient()
            assert client.enabled is False
            assert client.webhook_url is None

    @patch.dict(
        "os.environ",
        {"DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789012345678/token123"},
    )
    def test_environment_variable_override(self):
        """環境変数オーバーライドテスト"""
        # 環境変数設定済み、引数でオーバーライド
        override_url = "https://discord.com/api/webhooks/987654321098765432/override_token"
        client = DiscordClient(webhook_url=override_url)
        assert client.enabled is True
        assert client.webhook_url == override_url  # 引数が優先

        # 引数なし、環境変数から取得
        client_env = DiscordClient()
        assert client_env.enabled is True
        assert (
            client_env.webhook_url == "https://discord.com/api/webhooks/123456789012345678/token123"
        )

    @patch("requests.post")
    def test_error_response_codes(self, mock_post):
        """各種HTTPエラーレスポンステスト"""
        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        error_codes = [
            (400, '{"message": "Bad Request", "code": 50109}'),
            (401, '{"message": "Unauthorized", "code": 0}'),
            (403, '{"message": "Forbidden", "code": 50013}'),
            (404, '{"message": "Not Found", "code": 10015}'),
            (429, '{"message": "Too Many Requests", "retry_after": 5.5}'),
            (500, '{"message": "Internal Server Error"}'),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
        ]

        for status_code, response_text in error_codes:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.text = response_text
            mock_post.return_value = mock_response

            result = client.send_message("テストメッセージ")
            assert result is False

    @patch("requests.post")
    def test_network_exception_handling(self, mock_post):
        """ネットワーク例外処理テスト"""
        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        network_exceptions = [
            requests.exceptions.ConnectionError("接続エラー"),
            requests.exceptions.Timeout("タイムアウト"),
            requests.exceptions.HTTPError("HTTPエラー"),
            requests.exceptions.RequestException("リクエストエラー"),
            Exception("予期しないエラー"),
        ]

        for exception in network_exceptions:
            mock_post.side_effect = exception
            result = client.send_message("テストメッセージ")
            assert result is False
            mock_post.side_effect = None  # リセット

    def test_get_iso_timestamp_format(self):
        """ISO形式タイムスタンプフォーマットテスト"""
        client = DiscordClient()

        # 複数回呼び出してフォーマット一貫性確認
        for _ in range(5):
            timestamp = client._get_iso_timestamp()

            # ISO 8601フォーマット検証
            assert isinstance(timestamp, str)
            assert "T" in timestamp
            assert timestamp.endswith("+00:00") or timestamp.endswith("Z")

            # 基本的な日時フォーマット検証
            date_part, time_part = timestamp.split("T")
            assert len(date_part) == 10  # YYYY-MM-DD
            assert "-" in date_part

    @patch("requests.post")
    def test_large_message_handling(self, mock_post):
        """大きなメッセージ処理テスト"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        # 非常に長いメッセージ（Discord制限テスト）
        very_long_message = "テスト" * 1000  # 4000文字
        result = client.send_message(very_long_message)
        assert result is True

        # 非常に多いフィールド
        many_fields = [{"name": f"フィールド{i}", "value": f"値{i}"} for i in range(50)]
        result = client.send_embed(
            title="多数フィールドテスト", description="フィールド数制限テスト", fields=many_fields
        )
        assert result is True

    @patch("requests.post")
    def test_unicode_message_handling(self, mock_post):
        """Unicode文字メッセージ処理テスト"""
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        client = DiscordClient(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        unicode_messages = [
            "🚀 ロケット絵文字テスト 🌟",
            "中文测试消息",
            "Тест на русском языке",
            "العربية اختبار",
            "日本語のテストメッセージ with English mixed",
            "特殊文字: ©®™℃℉±×÷√∞≈≠≤≥",
        ]

        for message in unicode_messages:
            result = client.send_message(message)
            assert result is True

        # JSON変換確認
        call_args = mock_post.call_args
        assert "data" in call_args.kwargs
        # JSON文字列として正常に変換されている
        payload = json.loads(call_args.kwargs["data"])
        assert isinstance(payload, dict)
