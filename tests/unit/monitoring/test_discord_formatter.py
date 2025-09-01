"""
Discord通知フォーマッターのテスト - Phase 15新実装

各種通知タイプのメッセージフォーマット機能テスト。
統一されたフォーマットの品質保証。
"""

import pytest

from src.monitoring.discord_notifier import DiscordFormatter


class TestDiscordFormatter:
    """DiscordFormatterのテスト"""

    def test_format_trading_signal_buy(self):
        """買いシグナルのフォーマット"""
        signal_data = {"action": "buy", "confidence": 0.85, "price": 1000000}

        result = DiscordFormatter.format_trading_signal(signal_data)

        assert result["title"] == "📈 取引シグナル"
        assert "BUY" in result["description"]
        assert result["color"] == 0x27AE60  # 高信頼度（緑色）

        # フィールド検証
        fields = result["fields"]
        assert len(fields) == 2
        assert fields[0]["name"] == "💰 価格"
        assert "¥1,000,000" in fields[0]["value"]
        assert fields[1]["name"] == "🎯 信頼度"
        assert "85.0%" in fields[1]["value"]

    def test_format_trading_signal_sell(self):
        """売りシグナルのフォーマット"""
        signal_data = {"action": "sell", "confidence": 0.65, "price": 950000}

        result = DiscordFormatter.format_trading_signal(signal_data)

        assert result["title"] == "📉 取引シグナル"
        assert "SELL" in result["description"]
        assert result["color"] == 0xF39C12  # 中信頼度（黄色）

        fields = result["fields"]
        assert "¥950,000" in fields[0]["value"]
        assert "65.0%" in fields[1]["value"]

    def test_format_trading_signal_hold(self):
        """ホールドシグナルのフォーマット"""
        signal_data = {"action": "hold", "confidence": 0.45, "price": 980000}

        result = DiscordFormatter.format_trading_signal(signal_data)

        assert result["title"] == "⏸️ 取引シグナル"
        assert "HOLD" in result["description"]
        assert result["color"] == 0xE67E22  # 低信頼度（オレンジ色）

    def test_format_trading_signal_unknown_action(self):
        """不明なアクションのフォーマット"""
        signal_data = {"action": "unknown", "confidence": 0.5, "price": 1000000}

        result = DiscordFormatter.format_trading_signal(signal_data)

        assert result["title"] == "❓ 取引シグナル"
        assert "UNKNOWN" in result["description"]

    def test_format_trade_execution_successful_buy(self):
        """成功した買い注文のフォーマット"""
        execution_data = {
            "success": True,
            "side": "buy",
            "amount": 0.01,
            "price": 1000000,
            "pnl": 5000,
        }

        result = DiscordFormatter.format_trade_execution(execution_data)

        assert result["title"] == "✅ 📈 取引成功"
        assert result["color"] == 0x27AE60  # 成功（緑色）

        fields = result["fields"]
        assert len(fields) == 4  # 取引タイプ、数量、価格、PnL

        # 各フィールドの検証
        field_values = {field["name"]: field["value"] for field in fields}
        assert field_values["📊 取引タイプ"] == "BUY"
        assert "0.0100 BTC" in field_values["💎 数量"]
        assert "¥1,000,000" in field_values["💰 価格"]
        assert "¥5,000" in field_values["💰 損益"]

    def test_format_trade_execution_failed_sell(self):
        """失敗した売り注文のフォーマット"""
        execution_data = {"success": False, "side": "sell", "amount": 0.02, "price": 950000}

        result = DiscordFormatter.format_trade_execution(execution_data)

        assert result["title"] == "❌ 📉 取引失敗"
        assert result["color"] == 0xE74C3C  # 失敗（赤色）

        fields = result["fields"]
        assert len(fields) == 3  # PnLなし

        field_values = {field["name"]: field["value"] for field in fields}
        assert field_values["📊 取引タイプ"] == "SELL"
        assert "0.0200 BTC" in field_values["💎 数量"]

    def test_format_trade_execution_with_loss(self):
        """損失のある取引のフォーマット"""
        execution_data = {
            "success": True,
            "side": "sell",
            "amount": 0.01,
            "price": 980000,
            "pnl": -3000,
        }

        result = DiscordFormatter.format_trade_execution(execution_data)

        fields = result["fields"]
        pnl_field = next(f for f in fields if "損益" in f["name"])
        assert "💸 損益" == pnl_field["name"]  # 損失絵文字
        assert "¥-3,000" in pnl_field["value"]

    def test_format_system_status_healthy(self):
        """健全なシステム状態のフォーマット"""
        status_data = {
            "status": "healthy",
            "uptime": 7230,  # 2時間30秒
            "trades_today": 5,
            "current_balance": 1050000,
        }

        result = DiscordFormatter.format_system_status(status_data)

        assert result["title"] == "🟢 システム状態"
        assert "HEALTHY" in result["description"]
        assert result["color"] == 0x27AE60  # 健全（緑色）

        fields = result["fields"]
        field_values = {field["name"]: field["value"] for field in fields}
        assert "2時間0分" in field_values["⏱️ 稼働時間"]
        assert "5回" in field_values["📈 本日取引数"]
        assert "¥1,050,000" in field_values["💰 現在残高"]

    def test_format_system_status_warning(self):
        """警告状態のシステムフォーマット"""
        status_data = {"status": "warning", "uptime": 3661, "trades_today": 0}  # 1時間1分1秒

        result = DiscordFormatter.format_system_status(status_data)

        assert result["title"] == "🟡 システム状態"
        assert "WARNING" in result["description"]
        assert result["color"] == 0xF39C12  # 警告（黄色）

        fields = result["fields"]
        field_values = {field["name"]: field["value"] for field in fields}
        assert "1時間1分" in field_values["⏱️ 稼働時間"]
        assert "0回" in field_values["📈 本日取引数"]

    def test_format_system_status_error(self):
        """エラー状態のシステムフォーマット"""
        status_data = {"status": "error", "uptime": 120, "trades_today": 0}

        result = DiscordFormatter.format_system_status(status_data)

        assert result["title"] == "🔴 システム状態"
        assert result["color"] == 0xE74C3C  # エラー（赤色）

    def test_format_error_notification_critical(self):
        """クリティカルエラー通知のフォーマット"""
        error_data = {
            "type": "ConnectionError",
            "message": "API接続が失敗しました",
            "component": "BitbankClient",
            "severity": "critical",
        }

        result = DiscordFormatter.format_error_notification(error_data)

        assert result["title"] == "🚨 エラー発生"
        assert "BitbankClient" in result["description"]
        assert result["color"] == 0xE74C3C  # クリティカル（赤色）

        fields = result["fields"]
        assert len(fields) == 2
        assert fields[0]["name"] == "🏷️ エラータイプ"
        assert fields[0]["value"] == "ConnectionError"
        assert fields[1]["name"] == "📝 メッセージ"
        assert "API接続が失敗" in fields[1]["value"]

    def test_format_error_notification_long_message(self):
        """長いエラーメッセージの切り詰め"""
        long_message = "A" * 150  # 150文字の長いメッセージ
        error_data = {
            "type": "ValueError",
            "message": long_message,
            "component": "システム",
            "severity": "error",
        }

        result = DiscordFormatter.format_error_notification(error_data)

        fields = result["fields"]
        message_field = fields[1]
        # 100文字で切り詰められ、"..."が追加される
        assert len(message_field["value"]) <= 103
        assert message_field["value"].endswith("...")

    def test_format_statistics_summary_positive_return(self):
        """プラスリターンの統計サマリー"""
        stats_data = {
            "total_trades": 10,
            "winning_trades": 7,
            "win_rate": 0.7,
            "return_rate": 0.08,  # 8%リターン
            "current_balance": 1080000,
        }

        result = DiscordFormatter.format_statistics_summary(stats_data)

        assert result["title"] == "📊 取引統計サマリー"
        assert result["color"] == 0x27AE60  # 良好（緑色）

        fields = result["fields"]
        field_values = {field["name"]: field["value"] for field in fields}
        assert field_values["🔢 総取引数"] == "10回"
        assert field_values["🏆 勝ち取引"] == "7回"
        assert field_values["📈 勝率"] == "70.0%"
        assert field_values["💰 現在残高"] == "¥1,080,000"
        assert field_values["📊 リターン率"] == "+8.00%"

    def test_format_statistics_summary_negative_return(self):
        """マイナスリターンの統計サマリー"""
        stats_data = {
            "total_trades": 5,
            "winning_trades": 2,
            "win_rate": 0.4,
            "return_rate": -0.03,  # -3%リターン
            "current_balance": 970000,
        }

        result = DiscordFormatter.format_statistics_summary(stats_data)

        assert result["color"] == 0xE67E22  # 注意（オレンジ色）

        fields = result["fields"]
        field_values = {field["name"]: field["value"] for field in fields}
        assert field_values["📊 リターン率"] == "-3.00%"

    def test_format_statistics_summary_small_positive_return(self):
        """小さなプラスリターンの統計サマリー"""
        stats_data = {
            "total_trades": 3,
            "winning_trades": 2,
            "win_rate": 0.67,
            "return_rate": 0.02,  # 2%リターン
            "current_balance": 1020000,
        }

        result = DiscordFormatter.format_statistics_summary(stats_data)

        assert result["color"] == 0xF39C12  # 普通（黄色）

        fields = result["fields"]
        field_values = {field["name"]: field["value"] for field in fields}
        assert field_values["📊 リターン率"] == "+2.00%"

    def test_format_methods_handle_missing_data(self):
        """データ不足時の各メソッドの処理"""
        # 最小限のデータでのテスト
        minimal_signal = {}
        result = DiscordFormatter.format_trading_signal(minimal_signal)
        assert result["title"] == "❓ 取引シグナル"

        minimal_execution = {}
        result = DiscordFormatter.format_trade_execution(minimal_execution)
        assert "❌" in result["title"]  # デフォルトは失敗

        minimal_status = {}
        result = DiscordFormatter.format_system_status(minimal_status)
        assert "🟡" in result["title"]  # デフォルトは警告

        minimal_error = {}
        result = DiscordFormatter.format_error_notification(minimal_error)
        assert "⚠️" in result["title"]  # デフォルトは警告

        minimal_stats = {}
        result = DiscordFormatter.format_statistics_summary(minimal_stats)
        assert result["title"] == "📊 取引統計サマリー"

    def test_format_trading_signal_comprehensive_actions(self):
        """取引シグナル包括的アクションテスト"""
        test_cases = [
            ("BUY", "📈", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            ("buy", "📈", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            ("SELL", "📉", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            ("sell", "📉", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            ("HOLD", "⏸️", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            ("hold", "⏸️", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            ("wait", "❓", 0xE67E22),  # unknown actionでもconfidence=0.5なので低信頼度オレンジ
            ("unknown_action", "❓", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            ("", "❓", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
            (None, "❓", 0xE67E22),  # confidence=0.5なので低信頼度オレンジ
        ]

        for action, expected_emoji, expected_color in test_cases:
            signal_data = {"action": action, "confidence": 0.5, "price": 1000000}
            result = DiscordFormatter.format_trading_signal(signal_data)

            assert expected_emoji in result["title"]
            assert result["color"] == expected_color

    def test_format_trading_signal_confidence_levels(self):
        """信頼度レベル別テスト"""
        confidence_tests = [
            (0.9, 0x27AE60),  # 高信頼度（緑）
            (0.8, 0x27AE60),  # 高信頼度（緑）
            (0.7, 0xF39C12),  # 中信頼度（黄）
            (0.6, 0xF39C12),  # 中信頼度（黄）
            (0.5, 0xE67E22),  # 低信頼度（オレンジ）
            (0.4, 0xE67E22),  # 低信頼度（オレンジ）
            (0.0, 0xE67E22),  # 最低信頼度（オレンジ）
            (1.0, 0x27AE60),  # 最高信頼度（緑）
            (-0.1, 0xE67E22),  # 異常値（オレンジ）
            (1.1, 0x27AE60),  # 異常値（緑）
        ]

        for confidence, expected_color in confidence_tests:
            signal_data = {"action": "buy", "confidence": confidence, "price": 1000000}
            result = DiscordFormatter.format_trading_signal(signal_data)
            assert result["color"] == expected_color

    def test_format_trade_execution_complex_scenarios(self):
        """取引実行複雑シナリオテスト"""
        # 大きな利益
        big_profit = {
            "success": True,
            "side": "sell",
            "amount": 0.1,
            "price": 10000000,  # 1000万円
            "pnl": 500000,  # 50万円利益
        }
        result = DiscordFormatter.format_trade_execution(big_profit)
        assert "💰 損益" in [f["name"] for f in result["fields"]]

        # 大きな損失
        big_loss = {
            "success": True,
            "side": "buy",
            "amount": 0.05,
            "price": 5000000,
            "pnl": -200000,  # 20万円損失
        }
        result = DiscordFormatter.format_trade_execution(big_loss)
        assert "💸 損益" in [f["name"] for f in result["fields"]]

        # ゼロ損益
        zero_pnl = {"success": True, "side": "sell", "amount": 0.01, "price": 5000000, "pnl": 0}
        result = DiscordFormatter.format_trade_execution(zero_pnl)
        assert "💸 損益" in [f["name"] for f in result["fields"]]  # pnl=0は > 0ではないので💸

    def test_format_system_status_uptime_formatting(self):
        """システム稼働時間フォーマットテスト"""
        uptime_tests = [
            (0, "0分"),
            (59, "0分"),  # 1分未満
            (60, "1分"),  # ちょうど1分
            (3600, "1時間0分"),  # ちょうど1時間
            (3661, "1時間1分"),  # 1時間1分
            (7200, "2時間0分"),  # 2時間
            (7323, "2時間2分"),  # 2時間2分3秒（秒は無視）
            (86400, "24時間0分"),  # 1日
            (90061, "25時間1分"),  # 25時間1分
        ]

        for uptime_seconds, expected_format in uptime_tests:
            status_data = {"status": "healthy", "uptime": uptime_seconds, "trades_today": 5}
            result = DiscordFormatter.format_system_status(status_data)

            uptime_field = next(f for f in result["fields"] if "稼働時間" in f["name"])
            assert expected_format in uptime_field["value"]

    def test_format_error_notification_severity_mapping(self):
        """エラー重要度マッピングテスト"""
        severity_tests = [
            ("critical", "🚨", 0xE74C3C),
            ("error", "❌", 0xE67E22),  # 実装では0xE67E22
            ("warning", "⚠️", 0xF39C12),
            ("", "⚠️", 0xF39C12),  # デフォルト
            (None, "⚠️", 0xF39C12),  # None
            ("unknown", "⚠️", 0xF39C12),  # 未知
        ]

        for severity, expected_emoji, expected_color in severity_tests:
            error_data = {
                "type": "TestError",
                "message": "テストエラー",
                "severity": severity,
                "component": "TestComponent",
            }
            result = DiscordFormatter.format_error_notification(error_data)

            assert expected_emoji in result["title"]
            assert result["color"] == expected_color

    def test_format_statistics_return_rate_edge_cases(self):
        """統計リターン率エッジケーステスト"""
        return_rate_tests = [
            (0.15, "📊 リターン率", "+15.00%", 0x27AE60),  # 15%以上（緑）
            (0.05, "📊 リターン率", "+5.00%", 0xF39C12),  # 5%（黄）
            (0.01, "📊 リターン率", "+1.00%", 0xF39C12),  # 1%（黄）
            (0.0, "📊 リターン率", "+0.00%", 0xE67E22),  # 0%（オレンジ）※return_rate > 0 ではない
            (-0.01, "📊 リターン率", "-1.00%", 0xE67E22),  # マイナス（オレンジ）
            (-0.1, "📊 リターン率", "-10.00%", 0xE67E22),  # -10%（オレンジ）
            (1.0, "📊 リターン率", "+100.00%", 0x27AE60),  # 100%（緑）
            (-0.5, "📊 リターン率", "-50.00%", 0xE67E22),  # -50%（オレンジ）
        ]

        for return_rate, field_name, expected_value, expected_color in return_rate_tests:
            stats_data = {
                "total_trades": 10,
                "winning_trades": 6,
                "win_rate": 0.6,
                "return_rate": return_rate,
                "current_balance": 1000000,
            }
            result = DiscordFormatter.format_statistics_summary(stats_data)

            # リターン率フィールドを見つける
            return_field = next(f for f in result["fields"] if field_name in f["name"])
            assert expected_value in return_field["value"]
            assert result["color"] == expected_color

    def test_price_formatting_edge_cases(self):
        """価格フォーマットエッジケーステスト"""
        price_tests = [
            (0, "未設定"),  # price > 0 ではないので未設定
            (1, "¥1"),
            (999, "¥999"),
            (1000, "¥1,000"),
            (10000, "¥10,000"),
            (100000, "¥100,000"),
            (1000000, "¥1,000,000"),
            (10000000, "¥10,000,000"),
            (999999999, "¥999,999,999"),
            (1000000000, "¥1,000,000,000"),  # 10億
            (1.5, "¥2"),  # 小数点は整数に丸める
            (1000.99, "¥1,001"),  # 小数点は整数に丸める
            (-1000, "未設定"),  # 負の値は price > 0 ではないので未設定
        ]

        for price, expected_format in price_tests:
            signal_data = {"action": "buy", "confidence": 0.8, "price": price}
            result = DiscordFormatter.format_trading_signal(signal_data)

            price_field = next(f for f in result["fields"] if "価格" in f["name"])
            assert expected_format in price_field["value"]

    def test_message_truncation_limits(self):
        """メッセージ切り詰め制限テスト"""
        # 非常に長いエラーメッセージ
        very_long_message = "A" * 200  # 200文字
        error_data = {
            "type": "LongError",
            "message": very_long_message,
            "component": "TestComponent",
            "severity": "error",
        }
        result = DiscordFormatter.format_error_notification(error_data)

        message_field = next(f for f in result["fields"] if "メッセージ" in f["name"])
        # 100文字で切り詰め + "..." = 103文字以下
        assert len(message_field["value"]) <= 103
        if len(very_long_message) > 100:
            assert message_field["value"].endswith("...")

    def test_unicode_handling_in_formats(self):
        """Unicode文字処理テスト"""
        unicode_data = {
            "action": "buy",
            "confidence": 0.8,
            "price": 1000000,
            "symbol": "BTC/JPY 🚀",  # 絵文字含む
            "note": "テスト用の日本語メッセージ",
        }

        result = DiscordFormatter.format_trading_signal(unicode_data)

        # Unicode文字が正しく処理される
        assert isinstance(result["title"], str)
        assert isinstance(result["description"], str)
        for field in result["fields"]:
            assert isinstance(field["name"], str)
            assert isinstance(field["value"], str)

    def test_field_structure_validation(self):
        """フィールド構造検証テスト"""
        signal_data = {"action": "buy", "confidence": 0.8, "price": 1000000}
        result = DiscordFormatter.format_trading_signal(signal_data)

        # 必須フィールド構造チェック
        assert "title" in result
        assert "description" in result
        assert "color" in result
        assert "fields" in result

        # フィールド配列の構造チェック
        for field in result["fields"]:
            assert "name" in field
            assert "value" in field
            assert isinstance(field["name"], str)
            assert isinstance(field["value"], str)
            assert len(field["name"]) > 0
            assert len(field["value"]) > 0

    def test_color_consistency_across_methods(self):
        """メソッド間色一貫性テスト"""
        # 成功系の色（緑）
        success_signal = {"action": "buy", "confidence": 0.9, "price": 1000000}
        success_execution = {"success": True, "side": "buy", "amount": 0.01, "pnl": 1000}
        healthy_status = {"status": "healthy", "uptime": 3600}

        signal_result = DiscordFormatter.format_trading_signal(success_signal)
        execution_result = DiscordFormatter.format_trade_execution(success_execution)
        status_result = DiscordFormatter.format_system_status(healthy_status)

        # 成功系は同じ緑色
        green_color = 0x27AE60
        assert signal_result["color"] == green_color
        assert execution_result["color"] == green_color
        assert status_result["color"] == green_color

        # 警告系の色（黄色）
        warning_signal = {"action": "buy", "confidence": 0.6, "price": 1000000}
        warning_status = {"status": "warning", "uptime": 3600}

        signal_warning = DiscordFormatter.format_trading_signal(warning_signal)
        status_warning = DiscordFormatter.format_system_status(warning_status)

        # 警告系は同じ黄色
        warning_color = 0xF39C12
        assert signal_warning["color"] == warning_color
        assert status_warning["color"] == warning_color

    def test_default_value_handling(self):
        """デフォルト値処理テスト"""
        # 完全に空のデータ
        empty_data = {}

        signal_result = DiscordFormatter.format_trading_signal(empty_data)
        assert signal_result["title"] is not None
        assert signal_result["description"] is not None
        assert signal_result["color"] is not None
        assert isinstance(signal_result["fields"], list)

        execution_result = DiscordFormatter.format_trade_execution(empty_data)
        assert execution_result["title"] is not None
        assert execution_result["color"] is not None

        status_result = DiscordFormatter.format_system_status(empty_data)
        assert status_result["title"] is not None
        assert status_result["color"] is not None

        error_result = DiscordFormatter.format_error_notification(empty_data)
        assert error_result["title"] is not None
        assert error_result["color"] is not None

        stats_result = DiscordFormatter.format_statistics_summary(empty_data)
        assert stats_result["title"] is not None
        assert stats_result["color"] is not None
