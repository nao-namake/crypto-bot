"""
DiscordNotifier テストファイル - Phase 17品質向上・カバレッジ70%達成

Discord通知システムの全メソッドを包括的にテスト。
3階層通知・レート制限・Webhook送信・エラーハンドリングをカバー。
"""

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.exceptions import CryptoBotError, ErrorSeverity, NotificationError
from src.monitoring.discord import (
    DiscordNotifier,
    NotificationLevel,
    get_discord_notifier,
    setup_discord_notifier,
)


class TestDiscordNotifier:
    """DiscordNotifier メインテストクラス"""

    @pytest.fixture
    def mock_webhook_url(self):
        """モック用WebhookURL"""
        return "https://discord.com/api/webhooks/123456789/mock_webhook_url"

    @pytest.fixture
    def notifier_with_url(self, mock_webhook_url):
        """WebhookURL付きDiscordNotifier"""
        return DiscordNotifier(webhook_url=mock_webhook_url)

    @pytest.fixture
    def notifier_without_url(self):
        """WebhookURLなしDiscordNotifier"""
        return DiscordNotifier(webhook_url=None)

    def test_init_with_webhook_url(self, mock_webhook_url):
        """WebhookURL付き初期化テスト"""
        notifier = DiscordNotifier(webhook_url=mock_webhook_url)

        assert notifier.webhook_url == mock_webhook_url
        assert notifier.enabled is True
        assert notifier._min_interval_seconds == 60
        assert isinstance(notifier._last_notification_time, dict)

    def test_init_without_webhook_url(self):
        """WebhookURLなし初期化テスト"""
        with patch.dict(os.environ, {}, clear=True):
            notifier = DiscordNotifier(webhook_url=None)

            assert notifier.webhook_url is None
            assert notifier.enabled is False

    def test_init_with_env_webhook_url(self, mock_webhook_url):
        """環境変数WebhookURL初期化テスト"""
        with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": mock_webhook_url}):
            notifier = DiscordNotifier(webhook_url=None)

            assert notifier.webhook_url == mock_webhook_url
            assert notifier.enabled is True

    def test_should_send_notification_first_time(self, notifier_with_url):
        """初回通知許可テスト"""
        message = "Test message"
        level = NotificationLevel.INFO

        result = notifier_with_url._should_send_notification(message, level)

        assert result is True
        key = f"{level.value}_{hash(message)}"
        assert key in notifier_with_url._last_notification_time

    def test_should_send_notification_rate_limit(self, notifier_with_url):
        """レート制限テスト"""
        message = "Test message"
        level = NotificationLevel.INFO

        # 初回送信
        result1 = notifier_with_url._should_send_notification(message, level)
        assert result1 is True

        # 連続送信（レート制限）
        result2 = notifier_with_url._should_send_notification(message, level)
        assert result2 is False

    def test_should_send_notification_different_messages(self, notifier_with_url):
        """異なるメッセージは通知許可テスト"""
        message1 = "Test message 1"
        message2 = "Test message 2"
        level = NotificationLevel.INFO

        result1 = notifier_with_url._should_send_notification(message1, level)
        result2 = notifier_with_url._should_send_notification(message2, level)

        assert result1 is True
        assert result2 is True

    def test_create_embed_basic(self, notifier_with_url):
        """基本埋め込み作成テスト"""
        title = "Test Title"
        message = "Test Message"
        level = NotificationLevel.INFO

        embed = notifier_with_url._create_embed(title, message, level)

        assert embed["title"] == f"{notifier_with_url.EMOJIS[level]} {title}"
        assert embed["description"] == message
        assert embed["color"] == notifier_with_url.COLORS[level]
        assert "timestamp" in embed
        assert "footer" in embed
        assert "Crypto-Bot" in embed["footer"]["text"]

    def test_create_embed_with_fields(self, notifier_with_url):
        """フィールド付き埋め込み作成テスト"""
        title = "Test Title"
        message = "Test Message"
        level = NotificationLevel.WARNING
        fields = [{"name": "Field1", "value": "Value1", "inline": True}]

        embed = notifier_with_url._create_embed(title, message, level, fields)

        assert embed["fields"] == fields
        assert embed["color"] == notifier_with_url.COLORS[level]

    def test_create_embed_notification_levels(self, notifier_with_url):
        """通知レベル別埋め込みテスト"""
        title = "Test"
        message = "Message"

        for level in [
            NotificationLevel.INFO,
            NotificationLevel.WARNING,
            NotificationLevel.CRITICAL,
        ]:
            embed = notifier_with_url._create_embed(title, message, level)

            assert embed["color"] == notifier_with_url.COLORS[level]
            assert notifier_with_url.EMOJIS[level] in embed["title"]

    @patch("requests.post")
    def test_send_webhook_success(self, mock_post, notifier_with_url):
        """Webhook送信成功テスト"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        embeds = [{"title": "Test", "description": "Test message"}]
        result = notifier_with_url._send_webhook(embeds)

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["embeds"] == embeds
        assert call_args[1]["json"]["username"] == "Crypto-Bot"

    @patch("requests.post")
    def test_send_webhook_failure(self, mock_post, notifier_with_url):
        """Webhook送信失敗テスト"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        embeds = [{"title": "Test", "description": "Test message"}]
        result = notifier_with_url._send_webhook(embeds)

        assert result is False

    @patch("requests.post")
    def test_send_webhook_exception(self, mock_post, notifier_with_url):
        """Webhook送信例外テスト"""
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        embeds = [{"title": "Test", "description": "Test message"}]
        result = notifier_with_url._send_webhook(embeds)

        assert result is False

    def test_send_webhook_disabled(self, notifier_without_url):
        """無効状態Webhook送信テスト"""
        embeds = [{"title": "Test", "description": "Test message"}]
        result = notifier_without_url._send_webhook(embeds)

        assert result is False

    @patch.object(DiscordNotifier, "_send_webhook")
    @patch.object(DiscordNotifier, "_should_send_notification")
    def test_send_notification_basic(self, mock_should_send, mock_send_webhook, notifier_with_url):
        """基本通知送信テスト"""
        mock_should_send.return_value = True
        mock_send_webhook.return_value = True

        message = "Test notification"
        severity = ErrorSeverity.MEDIUM

        result = notifier_with_url.send_notification(message, severity)

        assert result is True
        mock_should_send.assert_called_once()
        mock_send_webhook.assert_called_once()

    @patch.object(DiscordNotifier, "_should_send_notification")
    def test_send_notification_rate_limited(self, mock_should_send, notifier_with_url):
        """レート制限通知テスト"""
        mock_should_send.return_value = False

        message = "Test notification"
        result = notifier_with_url.send_notification(message)

        assert result is False

    @patch.object(DiscordNotifier, "_send_webhook")
    @patch.object(DiscordNotifier, "_should_send_notification")
    def test_send_notification_with_error(
        self, mock_should_send, mock_send_webhook, notifier_with_url
    ):
        """エラー付き通知送信テスト"""
        mock_should_send.return_value = True
        mock_send_webhook.return_value = True

        message = "Error occurred"
        error = ValueError("Test error")

        result = notifier_with_url.send_notification(message, error=error)

        assert result is True
        # 送信された埋め込みの確認
        call_args = mock_send_webhook.call_args[0][0]
        embed = call_args[0]
        assert "エラー詳細" in [field["name"] for field in embed["fields"]]

    @patch.object(DiscordNotifier, "_send_webhook")
    @patch.object(DiscordNotifier, "_should_send_notification")
    def test_send_notification_with_crypto_bot_error(
        self, mock_should_send, mock_send_webhook, notifier_with_url
    ):
        """CryptoBotError付き通知テスト"""
        mock_should_send.return_value = True
        mock_send_webhook.return_value = True

        message = "CryptoBot error"
        error = CryptoBotError("Test error", ErrorSeverity.HIGH)

        result = notifier_with_url.send_notification(message, error=error)

        assert result is True

    @patch.object(DiscordNotifier, "_send_webhook")
    @patch.object(DiscordNotifier, "_should_send_notification")
    def test_send_notification_with_extra_data(
        self, mock_should_send, mock_send_webhook, notifier_with_url
    ):
        """追加データ付き通知テスト"""
        mock_should_send.return_value = True
        mock_send_webhook.return_value = True

        message = "Trade notification"
        extra_data = {
            "symbol": "BTC/JPY",
            "amount": 0.01,
            "price": 5000000,
            "confidence": 0.95,
            "strategy": "ATR",
            "pnl": 10000,
            "ignored_field": "ignored",
        }

        result = notifier_with_url.send_notification(message, extra_data=extra_data)

        assert result is True
        # 重要フィールドのみが含まれることを確認
        call_args = mock_send_webhook.call_args[0][0]
        embed = call_args[0]
        field_names = [field["name"] for field in embed["fields"]]
        assert "Symbol" in field_names
        assert "Amount" in field_names
        assert "Ignored_field" not in field_names

    def test_send_notification_severity_mapping(self, notifier_with_url):
        """重要度マッピングテスト"""
        with patch.object(notifier_with_url, "_should_send_notification", return_value=True):
            with patch.object(notifier_with_url, "_send_webhook", return_value=True):

                # 各重要度をテスト
                severities = [
                    ErrorSeverity.LOW,
                    ErrorSeverity.MEDIUM,
                    ErrorSeverity.HIGH,
                    ErrorSeverity.CRITICAL,
                ]

                for severity in severities:
                    result = notifier_with_url.send_notification("Test", severity)
                    assert result is True

    @patch.object(DiscordNotifier, "_send_webhook")
    def test_send_trade_notification_success(self, mock_send_webhook, notifier_with_url):
        """成功取引通知テスト"""
        mock_send_webhook.return_value = True

        result = notifier_with_url.send_trade_notification(
            action="buy",
            symbol="BTC/JPY",
            amount=0.01,
            price=5000000,
            success=True,
            order_id="12345",
        )

        assert result is True
        mock_send_webhook.assert_called_once()

        # 埋め込み内容確認
        embed = mock_send_webhook.call_args[0][0][0]
        assert "取引実行完了" in embed["title"]
        assert "✅" in embed["description"]
        assert any(field["name"] == "注文ID" for field in embed["fields"])

    @patch.object(DiscordNotifier, "_send_webhook")
    def test_send_trade_notification_failure(self, mock_send_webhook, notifier_with_url):
        """失敗取引通知テスト"""
        mock_send_webhook.return_value = True

        result = notifier_with_url.send_trade_notification(
            action="sell", symbol="BTC/JPY", amount=0.01, price=5000000, success=False
        )

        assert result is True

        # 埋め込み内容確認
        embed = mock_send_webhook.call_args[0][0][0]
        assert "取引実行失敗" in embed["title"]
        assert "❌" in embed["description"]

    @patch.object(DiscordNotifier, "_send_webhook")
    def test_send_performance_notification_profit(self, mock_send_webhook, notifier_with_url):
        """利益パフォーマンス通知テスト"""
        mock_send_webhook.return_value = True

        result = notifier_with_url.send_performance_notification(
            total_pnl=50000, win_rate=0.65, trade_count=100, max_drawdown=0.15
        )

        assert result is True

        embed = mock_send_webhook.call_args[0][0][0]
        assert "📈" in embed["title"]
        assert "💰" in embed["description"] or "📊" in embed["description"]

    @patch.object(DiscordNotifier, "_send_webhook")
    def test_send_performance_notification_loss(self, mock_send_webhook, notifier_with_url):
        """損失パフォーマンス通知テスト"""
        mock_send_webhook.return_value = True

        result = notifier_with_url.send_performance_notification(
            total_pnl=-25000, win_rate=0.45, trade_count=50, max_drawdown=0.25
        )

        assert result is True

        embed = mock_send_webhook.call_args[0][0][0]
        assert "📉" in embed["title"]
        assert "📉" in embed["description"]

    @patch.object(DiscordNotifier, "_send_webhook")
    def test_send_system_notification(self, mock_send_webhook, notifier_with_url):
        """システム通知テスト"""
        mock_send_webhook.return_value = True

        # 各システム状態をテスト
        statuses = ["normal", "warning", "critical"]

        for status in statuses:
            result = notifier_with_url.send_system_notification(
                message=f"System status: {status}", system_status=status
            )

            assert result is True
            embed = mock_send_webhook.call_args[0][0][0]
            assert "🔧 システム通知" in embed["title"]

    @patch.object(DiscordNotifier, "_send_webhook")
    def test_test_connection_success(self, mock_send_webhook, notifier_with_url):
        """接続テスト成功"""
        mock_send_webhook.return_value = True

        result = notifier_with_url.test_connection()

        assert result is True
        mock_send_webhook.assert_called_once()

        embed = mock_send_webhook.call_args[0][0][0]
        assert "接続テスト" in embed["title"]
        assert "🧪" in embed["description"]

    @patch.object(DiscordNotifier, "_send_webhook")
    def test_test_connection_failure(self, mock_send_webhook, notifier_with_url):
        """接続テスト失敗"""
        mock_send_webhook.return_value = False

        result = notifier_with_url.test_connection()

        assert result is False


class TestDiscordGlobalFunctions:
    """Discord グローバル関数テストクラス"""

    def test_get_discord_notifier_singleton(self):
        """シングルトンDiscordNotifier取得テスト"""
        # グローバル変数をリセット
        import src.monitoring.discord as discord_module

        discord_module._discord_notifier = None

        notifier1 = get_discord_notifier()
        notifier2 = get_discord_notifier()

        assert notifier1 is notifier2
        assert isinstance(notifier1, DiscordNotifier)

    def test_setup_discord_notifier(self):
        """DiscordNotifier初期化テスト"""
        webhook_url = "https://discord.com/api/webhooks/test"

        notifier = setup_discord_notifier(webhook_url)

        assert isinstance(notifier, DiscordNotifier)
        assert notifier.webhook_url == webhook_url

        # グローバルインスタンスが更新されることを確認
        global_notifier = get_discord_notifier()
        assert global_notifier is notifier


class TestNotificationLevel:
    """NotificationLevel Enum テストクラス"""

    def test_notification_level_values(self):
        """NotificationLevel値テスト"""
        assert NotificationLevel.INFO.value == "info"
        assert NotificationLevel.WARNING.value == "warning"
        assert NotificationLevel.CRITICAL.value == "critical"

    def test_notification_level_colors(self):
        """NotificationLevel色設定テスト"""
        assert DiscordNotifier.COLORS[NotificationLevel.INFO] == 0x3498DB
        assert DiscordNotifier.COLORS[NotificationLevel.WARNING] == 0xF39C12
        assert DiscordNotifier.COLORS[NotificationLevel.CRITICAL] == 0xE74C3C

    def test_notification_level_emojis(self):
        """NotificationLevel絵文字設定テスト"""
        assert DiscordNotifier.EMOJIS[NotificationLevel.INFO] == "ℹ️"
        assert DiscordNotifier.EMOJIS[NotificationLevel.WARNING] == "⚠️"
        assert DiscordNotifier.EMOJIS[NotificationLevel.CRITICAL] == "🚨"


class TestDiscordNotifierEdgeCases:
    """DiscordNotifier エッジケーステスト"""

    def test_invalid_system_status(self):
        """無効システム状態テスト"""
        notifier = DiscordNotifier("https://test.webhook")

        with patch.object(notifier, "_send_webhook", return_value=True):
            result = notifier.send_system_notification(
                message="Test", system_status="invalid_status"
            )

            assert result is True
            # デフォルトはINFOレベルになることを想定

    def test_empty_models_dict_in_notification(self):
        """空モデル辞書通知テスト"""
        notifier = DiscordNotifier("https://test.webhook")

        with patch.object(notifier, "_should_send_notification", return_value=True):
            with patch.object(notifier, "_send_webhook", return_value=True):
                result = notifier.send_notification(message="Test", extra_data={})

                assert result is True

    def test_large_message_handling(self):
        """大きなメッセージ処理テスト"""
        notifier = DiscordNotifier("https://test.webhook")

        # 非常に長いメッセージ
        long_message = "A" * 2000

        with patch.object(notifier, "_should_send_notification", return_value=True):
            with patch.object(notifier, "_send_webhook", return_value=True):
                result = notifier.send_notification(long_message)

                assert result is True

    def test_special_characters_in_fields(self):
        """特殊文字フィールドテスト"""
        notifier = DiscordNotifier("https://test.webhook")

        special_data = {
            "symbol": "BTC/JPY",
            "amount": "0.01 ₿",
            "price": "¥5,000,000",
            "note": "Special chars: <>\"'&",
        }

        with patch.object(notifier, "_should_send_notification", return_value=True):
            with patch.object(notifier, "_send_webhook", return_value=True):
                result = notifier.send_notification("Test special chars", extra_data=special_data)

                assert result is True
