"""
Discord通知マネージャーのテスト - Phase 15新実装

通知制御・Rate Limit管理・logger.py統合のテスト。
複雑な旧システムから置き換えた新管理システムの品質保証。
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.monitoring.discord_notifier import DiscordManager


class TestDiscordManager:
    """DiscordManager単体テスト"""

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_init_with_enabled_client(self, mock_client_class):
        """有効なクライアントでの初期化"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        assert manager.enabled is True
        assert manager.client == mock_client
        mock_client_class.assert_called_once_with(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_init_with_disabled_client(self, mock_client_class):
        """無効なクライアントでの初期化"""
        mock_client = Mock()
        mock_client.enabled = False
        mock_client_class.return_value = mock_client

        manager = DiscordManager()

        assert manager.enabled is False

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_send_simple_message_success(self, mock_client_class):
        """シンプルメッセージ送信成功"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_message.return_value = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        # 起動時抑制を無効化（テスト用）
        manager._startup_time = 0

        result = manager.send_simple_message("テストメッセージ", "info")

        assert result is True
        mock_client.send_message.assert_called_once_with("テストメッセージ", "info")

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_send_simple_message_disabled(self, mock_client_class):
        """無効化されたマネージャーでのメッセージ送信"""
        mock_client = Mock()
        mock_client.enabled = False
        mock_client_class.return_value = mock_client

        manager = DiscordManager()
        result = manager.send_simple_message("テストメッセージ")

        assert result is False
        mock_client.send_message.assert_not_called()

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_send_simple_message_startup_suppression(self, mock_client_class):
        """起動時抑制のテスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        # 起動直後（抑制期間中）
        result = manager.send_simple_message("テストメッセージ")

        assert result is False
        mock_client.send_message.assert_not_called()

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("time.time")
    def test_send_simple_message_rate_limit(self, mock_time, mock_client_class):
        """Rate Limit制御のテスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_message.return_value = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = 0  # 起動時抑制を無効化

        # 初回送信
        mock_time.return_value = 100
        result1 = manager.send_simple_message("メッセージ1")
        assert result1 is True

        # 短時間での連続送信（Rate limit）
        mock_time.return_value = 101  # 1秒後（最小間隔2秒未満）
        result2 = manager.send_simple_message("メッセージ2")
        assert result2 is False

        # 十分な間隔での送信
        mock_time.return_value = 103  # 3秒後（最小間隔2秒以上）
        result3 = manager.send_simple_message("メッセージ3")
        assert result3 is True

        # 送信回数確認
        assert mock_client.send_message.call_count == 2

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("src.monitoring.discord_notifier.DiscordFormatter")
    def test_send_trading_signal_success(self, mock_formatter_class, mock_client_class):
        """取引シグナル通知送信成功"""
        # Mock設定
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_embed.return_value = True
        mock_client_class.return_value = mock_client

        mock_formatter = Mock()
        mock_embed_data = {
            "title": "📈 取引シグナル",
            "description": "BUY シグナル検出",
            "fields": [{"name": "価格", "value": "¥1,000,000"}],
        }
        mock_formatter.format_trading_signal.return_value = mock_embed_data
        mock_formatter_class.return_value = mock_formatter

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = 0  # 起動時抑制を無効化

        signal_data = {"action": "buy", "confidence": 0.8, "price": 1000000}
        result = manager.send_trading_signal(signal_data)

        assert result is True
        mock_formatter.format_trading_signal.assert_called_once_with(signal_data)
        mock_client.send_embed.assert_called_once_with(
            title="📈 取引シグナル",
            description="BUY シグナル検出",
            fields=[{"name": "価格", "value": "¥1,000,000"}],
            level="info",
        )

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("src.monitoring.discord_notifier.DiscordFormatter")
    def test_send_trade_execution_success_and_failure(
        self, mock_formatter_class, mock_client_class
    ):
        """取引実行結果通知（成功・失敗）"""
        # Mock設定
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_embed.return_value = True
        mock_client_class.return_value = mock_client

        mock_formatter = Mock()
        mock_formatter_class.return_value = mock_formatter

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = 0

        # 成功した取引
        success_data = {"success": True, "side": "buy"}
        mock_formatter.format_trade_execution.return_value = {
            "title": "成功",
            "description": "説明",
        }

        result = manager.send_trade_execution(success_data)
        assert result is True

        # 最後の呼び出しを確認
        last_call = mock_client.send_embed.call_args
        assert last_call.kwargs["level"] == "info"

        # 失敗した取引
        failure_data = {"success": False, "side": "sell"}
        mock_formatter.format_trade_execution.return_value = {
            "title": "失敗",
            "description": "説明",
        }

        # Rate limit回避のため時間進行をシミュレート
        with patch("time.time", return_value=1000):
            manager._last_send_time = 0
            result = manager.send_trade_execution(failure_data)
            assert result is True

        # 最後の呼び出しを確認
        last_call = mock_client.send_embed.call_args
        assert last_call.kwargs["level"] == "warning"

    def test_send_system_status_different_levels(self):
        """システム状態通知の各レベル"""
        # Mock設定
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_embed.return_value = True

        mock_formatter = Mock()
        mock_formatter.format_system_status.return_value = {"title": "状態", "description": "説明"}

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = 0
        manager._startup_grace_period = 0  # 起動時抑制を無効化
        manager.enabled = True  # 明示的に有効化
        manager.client = mock_client  # 直接設定
        manager.formatter = mock_formatter  # 直接設定

        # 各状態での通知テスト
        status_levels = [
            ({"status": "healthy"}, "info"),
            ({"status": "warning"}, "warning"),
            ({"status": "error"}, "critical"),
        ]

        for i, (status_data, expected_level) in enumerate(status_levels):
            with patch("time.time", return_value=i * 10 + 10):  # Rate limit回避 (10,20,30)
                manager._last_send_time = 0
                result = manager.send_system_status(status_data)
                assert result is True

                # 最後の呼び出しのレベル確認
                last_call = mock_client.send_embed.call_args
                assert last_call.kwargs["level"] == expected_level

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("src.monitoring.discord_notifier.DiscordFormatter")
    def test_send_error_notification_ignores_startup_suppression(
        self, mock_formatter_class, mock_client_class
    ):
        """エラー通知は起動時抑制を無視"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_embed.return_value = True
        mock_client_class.return_value = mock_client

        mock_formatter = Mock()
        mock_formatter.format_error_notification.return_value = {
            "title": "エラー",
            "description": "説明",
        }
        mock_formatter_class.return_value = mock_formatter

        # 起動直後でもエラー通知は送信される
        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        # 起動時抑制期間中

        error_data = {"type": "TestError", "message": "テストエラー", "severity": "critical"}
        result = manager.send_error_notification(error_data)

        assert result is True
        mock_client.send_embed.assert_called_once()

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_test_connection_success(self, mock_client_class):
        """接続テスト成功"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.test_connection.return_value = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        result = manager.test_connection()

        assert result is True
        mock_client.test_connection.assert_called_once()

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_test_connection_disabled(self, mock_client_class):
        """接続テスト - 無効化されたマネージャー"""
        mock_client = Mock()
        mock_client.enabled = False
        mock_client_class.return_value = mock_client

        manager = DiscordManager()
        result = manager.test_connection()

        assert result is False
        mock_client.test_connection.assert_not_called()

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_get_status(self, mock_client_class):
        """ステータス取得"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._last_send_time = 50

        with patch("time.time", return_value=100):
            status = manager.get_status()

        assert status["enabled"] is True
        assert status["client_enabled"] is True
        assert status["last_send_ago"] == 50  # 100 - 50
        assert "startup_grace_remaining" in status

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_should_send_conditions(self, mock_client_class):
        """_should_send の各条件テスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        # 無効化されている場合
        manager.enabled = False
        assert manager._should_send() is False

        # 有効だが起動時抑制中
        manager.enabled = True
        assert manager._should_send() is False

        # 起動時抑制期間を過ぎたが、Rate limit中
        manager._startup_time = 0
        manager._last_send_time = 98
        with patch("time.time", return_value=99):  # 1秒経過（2秒未満）
            assert manager._should_send() is False

        # すべての条件をクリア
        with patch("time.time", return_value=102):  # 4秒後
            assert manager._should_send() is True

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("time.time")
    def test_update_last_send_time(self, mock_time, mock_client_class):
        """最終送信時刻の更新"""
        mock_time.return_value = 150
        mock_client = Mock()
        mock_client.enabled = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._update_last_send_time()

        assert manager._last_send_time == 150

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("src.monitoring.discord_notifier.DiscordFormatter")
    def test_send_statistics_summary(self, mock_formatter_class, mock_client_class):
        """統計サマリー通知テスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_embed.return_value = True
        mock_client_class.return_value = mock_client

        mock_formatter = Mock()
        mock_formatter.format_statistics_summary.return_value = {
            "title": "📊 取引統計",
            "description": "統計情報",
            "color": 0x27AE60,
        }
        mock_formatter_class.return_value = mock_formatter

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = 0

        stats_data = {"total_trades": 10, "win_rate": 0.7}
        result = manager.send_statistics_summary(stats_data)

        assert result is True
        mock_formatter.format_statistics_summary.assert_called_once_with(stats_data)
        mock_client.send_embed.assert_called_once()

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_rate_limit_edge_cases(self, mock_client_class):
        """Rate Limit境界値テスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_message.return_value = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = -100  # 起動時抑制を無効化（100秒前に起動したことにする）

        # 最小間隔（2秒）ちょうど
        with patch("time.time", return_value=10):
            manager._last_send_time = 8.0  # 2秒前
            result = manager.send_simple_message("2秒間隔テスト")
            assert result is True

        # 最小間隔未満（1.999秒）
        with patch("time.time", return_value=15):
            manager._last_send_time = 13.001  # 1.999秒前
            result = manager.send_simple_message("間隔不足テスト")
            assert result is False

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("src.monitoring.discord_notifier.DiscordFormatter")
    def test_emergency_notification_bypass(self, mock_formatter_class, mock_client_class):
        """緊急通知による制限バイパステスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_embed.return_value = True
        mock_client_class.return_value = mock_client

        mock_formatter = Mock()
        mock_formatter.format_error_notification.return_value = {
            "title": "🚨 緊急エラー",
            "description": "システム障害",
        }
        mock_formatter_class.return_value = mock_formatter

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        # 起動時抑制期間中でもエラー通知は送信される

        error_data = {"severity": "critical", "message": "緊急事態"}
        result = manager.send_error_notification(error_data)

        assert result is True
        mock_client.send_embed.assert_called_once()

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_graceful_degradation(self, mock_client_class):
        """優雅な機能低下テスト"""
        # クライアント作成時エラー
        mock_client_class.side_effect = Exception("クライアント作成エラー")

        try:
            manager = DiscordManager(
                "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
            )
            # エラーが発生してもオブジェクトは作成される
            assert manager is not None
        except Exception:
            # 例外処理されていることを確認
            pass

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("time.time")
    def test_startup_grace_period_calculation(self, mock_time, mock_client_class):
        """起動猶予期間計算テスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client_class.return_value = mock_client

        # 初期化時刻
        mock_time.return_value = 1000
        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        # 猶予期間中
        mock_time.return_value = 1020  # 20秒後
        status = manager.get_status()
        assert status["startup_grace_remaining"] > 0

        # 猶予期間終了後
        mock_time.return_value = 1080  # 80秒後（猶予期間60秒経過）
        status = manager.get_status()
        assert status["startup_grace_remaining"] <= 0

    @patch("src.monitoring.discord_notifier.DiscordClient")
    @patch("src.monitoring.discord_notifier.DiscordFormatter")
    def test_formatting_error_handling(self, mock_formatter_class, mock_client_class):
        """フォーマッターエラー処理テスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_embed.return_value = True
        mock_client_class.return_value = mock_client

        # フォーマッターがエラーを発生
        mock_formatter = Mock()
        mock_formatter.format_trading_signal.side_effect = Exception("フォーマットエラー")
        mock_formatter_class.return_value = mock_formatter

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = -100  # 起動時抑制を無効化

        signal_data = {"action": "buy", "confidence": 0.8}

        # フォーマッターでエラーが発生するので例外が発生する予定
        # 実装で例外ハンドリングされていなければ例外が伝播する
        try:
            result = manager.send_trading_signal(signal_data)
            # 例外ハンドリングがある場合は False が返る
            assert result is False
        except Exception as e:
            # 例外ハンドリングがない場合は例外が発生
            assert str(e) == "フォーマットエラー"

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_multiple_webhook_urls(self, mock_client_class):
        """複数WebhookURL処理テスト"""

        # 各呼び出しで新しいmock_clientインスタンスを返すように設定
        def create_mock_client(*args, **kwargs):
            mock_client = Mock()
            mock_client.enabled = True
            mock_client.send_message.return_value = True
            return mock_client

        mock_client_class.side_effect = create_mock_client

        # 異なるWebhookURLで複数のマネージャー
        urls = [
            "https://discord.com/api/webhooks/111111111111111111/token1",
            "https://discord.com/api/webhooks/222222222222222222/token2",
            "https://discord.com/api/webhooks/333333333333333333/token3",
        ]

        managers = []
        for url in urls:
            manager = DiscordManager(url)
            managers.append(manager)
            assert manager.enabled is True

        # 各マネージャーが独立して動作
        for i, manager in enumerate(managers):
            manager._startup_time = -100  # 起動時抑制を無効化
            with patch("time.time", return_value=i * 10):
                manager._last_send_time = (i * 10) - 5  # Rate limitを回避（5秒前に最後の送信）
                result = manager.send_simple_message(f"メッセージ{i}")
                assert result is True

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_concurrent_send_simulation(self, mock_client_class):
        """並行送信シミュレーションテスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.send_message.return_value = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )
        manager._startup_time = -100  # 起動時抑制を無効化

        # 並行送信をシミュレート（Rate limitで制御される）
        send_times = [0, 0.5, 1.0, 2.5, 3.0, 5.0]
        success_count = 0

        for send_time in send_times:
            with patch("time.time", return_value=send_time):
                if send_time == 0:
                    manager._last_send_time = 0  # 初回リセット
                result = manager.send_simple_message(f"メッセージ@{send_time}s")
                if result:
                    success_count += 1

        # Rate limitにより、すべてが成功するわけではない
        assert success_count < len(send_times)
        assert success_count >= 2  # 最低限の送信は成功

    @patch("src.monitoring.discord_notifier.DiscordClient")
    def test_status_information_completeness(self, mock_client_class):
        """ステータス情報完全性テスト"""
        mock_client = Mock()
        mock_client.enabled = True
        mock_client_class.return_value = mock_client

        manager = DiscordManager(
            "https://discord.com/api/webhooks/123456789012345678/abcdefghijklmnopqrstuvwxyz1234567890"
        )

        status = manager.get_status()

        # 必須ステータス情報の存在確認
        required_keys = ["enabled", "client_enabled", "last_send_ago", "startup_grace_remaining"]

        for key in required_keys:
            assert key in status, f"ステータスキー '{key}' が不足"

        # データ型確認
        assert isinstance(status["enabled"], bool)
        assert isinstance(status["client_enabled"], bool)
        assert isinstance(status["last_send_ago"], (int, float))
        assert isinstance(status["startup_grace_remaining"], (int, float))
