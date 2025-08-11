#!/usr/bin/env python3
"""
API Health Check テスト

本番環境で重要なヘルスチェック機能のテスト
"""

import json
import unittest

from crypto_bot.api.health import health_checker, update_status


class TestHealthChecker(unittest.TestCase):
    """ヘルスチェック機能テスト"""

    def setUp(self):
        """テスト用設定"""
        # HealthCheckerは設定を受け取らないため、グローバルインスタンスを使用
        self.checker = health_checker

    def test_basic_health_check(self):
        """基本ヘルスチェックテスト"""
        status = self.checker.check_basic_health()

        # 基本的なレスポンス構造
        self.assertIn("status", status)
        self.assertIn("timestamp", status)
        self.assertIn("mode", status)

        # タイムスタンプの妥当性
        self.assertIsInstance(status["timestamp"], str)

        # ステータス値の妥当性
        self.assertEqual(status["status"], "healthy")

    def test_dependencies_health_check(self):
        """依存関係ヘルスチェックテスト"""
        result = self.checker.check_dependencies()

        # 依存関係構造確認
        self.assertIsInstance(result, dict)

        # API認証情報チェック
        if "api_credentials" in result:
            api_check = result["api_credentials"]
            self.assertIn("status", api_check)
            self.assertIn(api_check["status"], ["healthy", "unhealthy"])

        # ファイルシステムチェック
        if "filesystem" in result:
            fs_check = result["filesystem"]
            self.assertIn("status", fs_check)
            self.assertIn(fs_check["status"], ["healthy", "unhealthy"])

    def test_trading_status_check(self):
        """取引ステータスチェックテスト"""
        status = self.checker.check_trading_status()

        # 取引ステータス構造確認
        self.assertIn("status", status)
        self.assertIn(status["status"], ["healthy", "warning", "unhealthy"])

        # 利益・取引回数情報
        self.assertIn("total_profit", status)
        self.assertIn("trade_count", status)

        # 数値型確認
        self.assertIsInstance(status["total_profit"], (int, float))
        self.assertIsInstance(status["trade_count"], int)

    def test_performance_metrics_check(self):
        """パフォーマンスメトリクステスト"""
        metrics = self.checker.get_performance_metrics()

        # メトリクス構造確認
        self.assertIn("status", metrics)
        self.assertIn("kelly_ratio", metrics)
        self.assertIn("win_rate", metrics)
        self.assertIn("max_drawdown", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("trade_count", metrics)

        # 数値型・範囲確認
        self.assertIsInstance(metrics["kelly_ratio"], (int, float))
        self.assertIsInstance(metrics["win_rate"], (int, float))
        self.assertGreaterEqual(metrics["win_rate"], 0.0)
        self.assertLessEqual(metrics["win_rate"], 1.0)

    def test_comprehensive_health_check(self):
        """包括的ヘルスチェックテスト"""
        health = self.checker.get_comprehensive_health()

        # 全体構造確認
        self.assertIn("overall_status", health)
        self.assertIn("basic", health)
        self.assertIn("dependencies", health)
        self.assertIn("trading", health)
        self.assertIn("performance", health)

        # 全体ステータス確認
        self.assertIn(health["overall_status"], ["healthy", "warning", "unhealthy"])

        # 基本情報確認
        basic = health["basic"]
        self.assertIn("uptime_seconds", basic)
        self.assertIn("region", basic)
        self.assertIsInstance(basic["uptime_seconds"], int)

    def test_update_status_function(self):
        """ステータス更新関数テスト"""
        # 基本的な呼び出し
        try:
            update_status(total_profit=1500.50, trade_count=25, position="LONG:0.1BTC")
        except Exception as e:
            self.fail(f"update_status failed: {e}")

        # Noneポジションでの呼び出し
        try:
            update_status(total_profit=-500.25, trade_count=10, position=None)
        except Exception as e:
            self.fail(f"update_status with None position failed: {e}")

    def test_basic_health_structure(self):
        """基本ヘルス構造テスト"""
        basic = self.checker.check_basic_health()

        # 必要なフィールド確認
        required_fields = [
            "status",
            "timestamp",
            "uptime_seconds",
            "region",
            "instance_id",
            "mode",
            "version",
        ]

        for field in required_fields:
            self.assertIn(field, basic, f"Field {field} missing from basic health")

        # 型確認
        self.assertIsInstance(basic["uptime_seconds"], int)
        self.assertIsInstance(basic["timestamp"], str)

        # HA情報
        self.assertIn("is_leader", basic)
        self.assertIn("ha_enabled", basic)
        self.assertIsInstance(basic["is_leader"], bool)
        self.assertIsInstance(basic["ha_enabled"], bool)

    def test_health_response_serializable(self):
        """ヘルスレスポンスのJSONシリアライズテスト"""
        # 基本ヘルス
        basic_status = self.checker.check_basic_health()

        try:
            json_str = json.dumps(basic_status)
            parsed_back = json.loads(json_str)
            self.assertIsInstance(parsed_back, dict)
        except (TypeError, ValueError) as e:
            self.fail(f"Basic health status is not JSON serializable: {e}")

        # 包括的ヘルス（時間がかかる可能性があるため簡略化）
        try:
            comprehensive = self.checker.get_comprehensive_health()
            json.dumps(comprehensive["basic"])  # 基本部分のみテスト
        except (TypeError, ValueError) as e:
            self.fail(f"Comprehensive health basic part is not JSON serializable: {e}")


if __name__ == "__main__":
    unittest.main()
