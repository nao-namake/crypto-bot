"""
Health API のテスト
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from crypto_bot.api.health import app, health_checker


class TestHealthAPI:

    @pytest.fixture
    def client(self):
        """テストクライアントを作成"""
        return TestClient(app)

    @pytest.fixture
    def temp_status_file(self):
        """テンポラリのstatus.jsonファイルを作成"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            test_status = {
                "last_updated": "2025-06-22 12:00:00",
                "total_profit": 1000.0,
                "trade_count": 5,
                "position": "BUY",
            }
            json.dump(test_status, f)
            temp_file = f.name

        # 元のファイルパスを保存
        original_file = (
            health_checker.state_manager.local_state_file
            if health_checker.state_manager
            else "status.json"
        )

        # テストファイルに差し替え
        if health_checker.state_manager:
            health_checker.state_manager.local_state_file = temp_file

        # パッチを適用
        with patch("crypto_bot.api.health.health_checker") as mock_checker:
            mock_checker.state_manager = (
                Mock() if health_checker.state_manager else None
            )
            mock_checker.state_manager.local_state_file = (
                temp_file if mock_checker.state_manager else None
            )

            yield temp_file

        # クリーンアップ
        try:
            os.unlink(temp_file)
        except FileNotFoundError:
            pass

        # 元に戻す
        if health_checker.state_manager:
            health_checker.state_manager.local_state_file = original_file

    def test_basic_health_check(self, client):
        """基本ヘルスチェックのテスト"""
        response = client.get("/healthz")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "region" in data
        assert "instance_id" in data
        assert "mode" in data
        assert "version" in data
        assert "is_leader" in data
        assert "ha_enabled" in data

    def test_health_endpoint_alias(self, client):
        """ヘルスチェックのエイリアスエンドポイントをテスト"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_detailed_health_check(self, client):
        """詳細ヘルスチェックのテスト"""
        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert "overall_status" in data
        assert "basic" in data
        assert "dependencies" in data
        assert "trading" in data

        # 基本情報の確認
        basic = data["basic"]
        assert basic["status"] == "healthy"
        assert "uptime_seconds" in basic

        # 依存関係の確認
        dependencies = data["dependencies"]
        assert "api_credentials" in dependencies
        assert "filesystem" in dependencies

        # 取引状態の確認
        trading = data["trading"]
        assert "status" in trading

    def test_readiness_check(self, client):
        """レディネスチェックのテスト"""
        response = client.get("/health/ready")

        # APIキーが設定されていない環境では503が返される可能性
        assert response.status_code in [200, 503]

        data = response.json()
        assert "status" in data
        assert "dependencies" in data

    def test_liveness_check(self, client):
        """ライブネスチェックのテスト"""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "alive"
        assert "uptime_seconds" in data
        assert "timestamp" in data

    def test_metrics_endpoint(self, client):
        """メトリクスエンドポイントのテスト"""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        content = response.text
        assert "crypto_bot_uptime_seconds" in content
        assert "crypto_bot_total_profit" in content
        assert "crypto_bot_trade_count" in content
        assert "crypto_bot_health_status" in content

    @patch("crypto_bot.api.health.health_checker")
    def test_cluster_health_without_ha(self, mock_health_checker, client):
        """HA無効時のクラスターヘルスチェックをテスト"""
        # HAが無効なHealthCheckerをモック
        mock_health_checker.state_manager = None
        mock_health_checker.check_basic_health.return_value = {
            "status": "healthy",
            "region": "test-region",
            "instance_id": "test-instance",
            "is_leader": True,
            "ha_enabled": False,
        }

        response = client.get("/health/cluster")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "single_instance"
        assert data["message"] == "HA mode not enabled"
        assert "instance" in data

    @patch("crypto_bot.api.health.health_checker")
    def test_cluster_health_with_ha(self, mock_health_checker, client):
        """HA有効時のクラスターヘルスチェックをテスト"""
        # HAが有効なHealthCheckerをモック
        mock_state_manager = Mock()
        mock_state_manager.get_cluster_status.return_value = {
            "instances": ["asia-northeast1-primary", "us-central1-secondary"],
            "leader": "asia-northeast1-primary",
            "total_instances": 2,
        }

        mock_health_checker.state_manager = mock_state_manager
        mock_health_checker.check_basic_health.return_value = {
            "status": "healthy",
            "region": "asia-northeast1",
            "instance_id": "primary",
            "is_leader": True,
            "ha_enabled": True,
        }

        response = client.get("/health/cluster")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "cluster"
        assert "cluster" in data
        assert "current_instance" in data
        assert data["cluster"]["total_instances"] == 2

    @patch("crypto_bot.api.health.health_checker")
    def test_manual_failover_without_ha(self, mock_health_checker, client):
        """HA無効時の手動フェイルオーバーをテスト"""
        mock_health_checker.state_manager = None

        response = client.post("/health/failover")

        # HTTPExceptionがキャッチされて503になる
        assert response.status_code == 503
        data = response.json()
        assert data["detail"] == "Failover failed"

    @patch("crypto_bot.api.health.health_checker")
    def test_manual_failover_with_ha_success(self, mock_health_checker, client):
        """HA有効時の手動フェイルオーバー成功をテスト"""
        mock_state_manager = Mock()
        mock_state_manager.handle_failover.return_value = True
        mock_state_manager.is_leader = True

        mock_health_checker.state_manager = mock_state_manager

        response = client.post("/health/failover")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["message"] == "Failover completed successfully"
        assert data["is_leader"] is True

    @patch("crypto_bot.api.health.health_checker")
    def test_manual_failover_with_ha_failure(self, mock_health_checker, client):
        """HA有効時の手動フェイルオーバー失敗をテスト"""
        mock_state_manager = Mock()
        mock_state_manager.handle_failover.return_value = False

        mock_health_checker.state_manager = mock_state_manager

        response = client.post("/health/failover")

        assert response.status_code == 500
        data = response.json()

        assert data["status"] == "failed"
        assert data["message"] == "Failover could not be completed"

    @patch("crypto_bot.api.health.health_checker")
    def test_health_check_with_trading_status(self, mock_health_checker, client):
        """取引状態を含むヘルスチェックをテスト"""
        # HealthCheckerをモック
        mock_health_checker.get_comprehensive_health.return_value = {
            "overall_status": "healthy",
            "basic": {
                "status": "healthy",
                "uptime_seconds": 3600,
                "region": "test-region",
                "instance_id": "test-instance",
            },
            "dependencies": {
                "api_credentials": {"status": "healthy"},
                "filesystem": {"status": "healthy"},
            },
            "trading": {
                "status": "healthy",
                "last_updated": "2025-06-22 12:00:00",
                "total_profit": 1500.0,
                "trade_count": 8,
                "position": "SELL",
            },
        }

        response = client.get("/health/detailed")

        assert response.status_code == 200
        data = response.json()

        trading = data["trading"]
        assert trading["total_profit"] == 1500.0
        assert trading["trade_count"] == 8
        assert trading["position"] == "SELL"

    def test_environment_variables_handling(self, client):
        """環境変数の取り扱いをテスト"""
        with patch.dict(
            os.environ,
            {
                "REGION": "test-region",
                "INSTANCE_ID": "test-instance",
                "MODE": "test-mode",
            },
        ):
            # 新しいHealthCheckerインスタンスを作成
            from crypto_bot.api.health import HealthChecker

            test_checker = HealthChecker()

            health_data = test_checker.check_basic_health()

            assert health_data["region"] == "test-region"
            assert health_data["instance_id"] == "test-instance"
            assert health_data["mode"] == "test-mode"

    def test_error_handling_in_health_checks(self, client):
        """ヘルスチェックでのエラーハンドリングをテスト"""
        with patch(
            "crypto_bot.api.health.health_checker.check_basic_health"
        ) as mock_check:
            mock_check.side_effect = Exception("Test error")

            response = client.get("/healthz")

            assert response.status_code == 503
            data = response.json()
            assert data["detail"] == "Service unhealthy"
