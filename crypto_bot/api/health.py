"""
ヘルスチェックAPI

Cloud Run のヘルスチェックとロードバランサーの監視に使用するAPIエンドポイント。
アプリケーションの状態、依存関係の確認、パフォーマンス指標を提供します。
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException, Response
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    uvicorn = None
    FastAPI = None
    HTTPException = None
    Response = None
    JSONResponse = None
    FASTAPI_AVAILABLE = False

try:
    from crypto_bot.ha.state_manager import StateManager

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False

logger = logging.getLogger(__name__)

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Crypto Bot Health Check API",
        description="Health check endpoints for multi-region deployment",
        version="1.0.0",
    )
else:
    # Create dummy app object with route decorators that do nothing
    class DummyApp:
        def get(self, path):
            def decorator(func):
                return func

            return decorator

        def post(self, path):
            def decorator(func):
                return func

            return decorator

        async def __call__(self, scope, receive, send):
            """Minimal ASGI app implementation for testing"""
            if scope["type"] == "http":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 404,
                        "headers": [[b"content-type", b"application/json"]],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"detail": "FastAPI not available"}',
                    }
                )

    app = DummyApp()


class HealthChecker:
    """アプリケーションの健全性をチェックするクラス"""

    def __init__(self):
        self.start_time = time.time()
        self.region = os.getenv("REGION", "unknown")
        self.instance_id = os.getenv("INSTANCE_ID", "unknown")
        self.mode = os.getenv("MODE", "unknown")

        # HA State Manager (if available)
        self.state_manager = None
        if HA_AVAILABLE:
            try:
                self.state_manager = StateManager(
                    region=self.region, instance_id=self.instance_id
                )
                # バックグラウンドでハートビートを開始
                self.state_manager.start_background_tasks()
                logger.info("HA State Manager initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize HA State Manager: {e}")

    def check_basic_health(self) -> Dict[str, Any]:
        """基本的なヘルスチェック"""
        uptime = time.time() - self.start_time

        basic_health = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": int(uptime),
            "region": self.region,
            "instance_id": self.instance_id,
            "mode": self.mode,
            "version": "1.0.0",
        }

        # HA情報を追加
        if self.state_manager:
            basic_health.update(
                {"is_leader": self.state_manager.is_leader, "ha_enabled": True}
            )
        else:
            basic_health.update(
                {"is_leader": True, "ha_enabled": False}  # HA無効時は常にリーダー
            )

        return basic_health

    def check_dependencies(self) -> Dict[str, Any]:
        """依存関係のヘルスチェック"""
        checks = {}

        # API キーの存在確認
        try:
            api_key = os.getenv("BYBIT_TESTNET_API_KEY")
            api_secret = os.getenv("BYBIT_TESTNET_API_SECRET")

            checks["api_credentials"] = {
                "status": "healthy" if api_key and api_secret else "unhealthy",
                "details": (
                    "API credentials available"
                    if api_key and api_secret
                    else "Missing API credentials"
                ),
            }
        except Exception as e:
            checks["api_credentials"] = {
                "status": "unhealthy",
                "details": f"Error checking API credentials: {str(e)}",
            }

        # ファイルシステムの確認
        try:
            test_file = "/tmp/health_check_test"
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)

            checks["filesystem"] = {
                "status": "healthy",
                "details": "Filesystem read/write OK",
            }
        except Exception as e:
            checks["filesystem"] = {
                "status": "unhealthy",
                "details": f"Filesystem error: {str(e)}",
            }

        # メモリ使用量の確認
        try:
            import psutil

            memory_percent = psutil.virtual_memory().percent

            checks["memory"] = {
                "status": "healthy" if memory_percent < 90 else "warning",
                "details": f"Memory usage: {memory_percent:.1f}%",
                "usage_percent": memory_percent,
            }
        except ImportError:
            checks["memory"] = {"status": "unknown", "details": "psutil not available"}
        except Exception as e:
            checks["memory"] = {
                "status": "unhealthy",
                "details": f"Memory check error: {str(e)}",
            }

        return checks

    def check_trading_status(self) -> Dict[str, Any]:
        """取引状態のチェック"""
        try:
            # status.json ファイルから最新の取引状態を読み取り
            status_file = "status.json"
            if os.path.exists(status_file):
                with open(status_file, "r") as f:
                    status_data = json.load(f)

                # 最終更新からの経過時間を計算
                last_updated = status_data.get("last_updated", "")
                if last_updated:
                    try:
                        last_update_time = datetime.strptime(
                            last_updated, "%Y-%m-%d %H:%M:%S"
                        )
                        time_diff = (datetime.now() - last_update_time).total_seconds()
                    except ValueError:
                        time_diff = float("inf")
                else:
                    time_diff = float("inf")

                # 5分以上更新されていない場合は警告
                status = "healthy" if time_diff < 300 else "warning"

                return {
                    "status": status,
                    "last_updated": last_updated,
                    "seconds_since_update": int(time_diff),
                    "total_profit": status_data.get("total_profit", 0),
                    "trade_count": status_data.get("trade_count", 0),
                    "position": status_data.get("position", ""),
                }
            else:
                return {
                    "status": "warning",
                    "details": "Status file not found",
                    "total_profit": 0,
                    "trade_count": 0,
                    "position": "",
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "details": f"Trading status check error: {str(e)}",
            }

    def get_comprehensive_health(self) -> Dict[str, Any]:
        """包括的なヘルスチェック"""
        basic = self.check_basic_health()
        dependencies = self.check_dependencies()
        trading = self.check_trading_status()

        # 全体の状態を判定
        all_statuses = [basic["status"]]
        all_statuses.extend([check["status"] for check in dependencies.values()])
        all_statuses.append(trading["status"])

        if "unhealthy" in all_statuses:
            overall_status = "unhealthy"
        elif "warning" in all_statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "overall_status": overall_status,
            "basic": basic,
            "dependencies": dependencies,
            "trading": trading,
        }


# ヘルスチェッカーのインスタンス
health_checker = HealthChecker()


@app.get("/healthz")
@app.get("/health")
async def health_check():
    """
    基本的なヘルスチェックエンドポイント

    Cloud Run とロードバランサーのヘルスチェックで使用されます。
    """
    try:
        health_data = health_checker.check_basic_health()
        return JSONResponse(content=health_data, status_code=200)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/health/detailed")
async def detailed_health_check():
    """
    詳細なヘルスチェックエンドポイント

    依存関係や取引状態を含む包括的な情報を提供します。
    """
    try:
        health_data = health_checker.get_comprehensive_health()

        # ステータスに応じて HTTP ステータスコードを設定
        status_code = 200
        if health_data["overall_status"] == "warning":
            status_code = 200  # 警告でも 200 を返す
        elif health_data["overall_status"] == "unhealthy":
            status_code = 503

        return JSONResponse(content=health_data, status_code=status_code)
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/health/ready")
async def readiness_check():
    """
    レディネスチェックエンドポイント

    アプリケーションがリクエストを処理する準備ができているかを確認します。
    """
    try:
        dependencies = health_checker.check_dependencies()

        # 重要な依存関係が健全であることを確認
        critical_deps = ["api_credentials", "filesystem"]
        unhealthy_deps = [
            dep
            for dep in critical_deps
            if dependencies.get(dep, {}).get("status") == "unhealthy"
        ]

        if unhealthy_deps:
            return JSONResponse(
                content={
                    "status": "not_ready",
                    "unhealthy_dependencies": unhealthy_deps,
                    "details": dependencies,
                },
                status_code=503,
            )

        return JSONResponse(
            content={"status": "ready", "dependencies": dependencies}, status_code=200
        )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/health/live")
async def liveness_check():
    """
    ライブネスチェックエンドポイント

    アプリケーションが稼働していることを確認します。
    """
    try:
        basic_health = health_checker.check_basic_health()
        return JSONResponse(
            content={
                "status": "alive",
                "uptime_seconds": basic_health["uptime_seconds"],
                "timestamp": basic_health["timestamp"],
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Liveness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not alive")


@app.get("/metrics")
async def metrics():
    """
    Prometheus形式のメトリクスエンドポイント
    """
    try:
        trading_status = health_checker.check_trading_status()
        basic = health_checker.check_basic_health()

        region = basic["region"]
        instance_id = basic["instance_id"]
        uptime_seconds = basic["uptime_seconds"]
        total_profit = trading_status.get("total_profit", 0)
        trade_count = trading_status.get("trade_count", 0)
        health_status = (
            1
            if trading_status.get("status") == "healthy"
            else 0.5 if trading_status.get("status") == "warning" else 0
        )

        metrics_lines = [
            "# HELP crypto_bot_uptime_seconds Total uptime in seconds",
            "# TYPE crypto_bot_uptime_seconds counter",
            f'crypto_bot_uptime_seconds{{region="{region}",'
            f'instance="{instance_id}"}} {uptime_seconds}',
            "",
            "# HELP crypto_bot_total_profit Total profit/loss",
            "# TYPE crypto_bot_total_profit gauge",
            f'crypto_bot_total_profit{{region="{region}",'
            f'instance="{instance_id}"}} {total_profit}',
            "",
            "# HELP crypto_bot_trade_count Total number of trades",
            "# TYPE crypto_bot_trade_count counter",
            f'crypto_bot_trade_count{{region="{region}",'
            f'instance="{instance_id}"}} {trade_count}',
            "",
            "# HELP crypto_bot_health_status Health status "
            "(1=healthy, 0.5=warning, 0=unhealthy)",
            "# TYPE crypto_bot_health_status gauge",
            f'crypto_bot_health_status{{region="{region}",'
            f'instance="{instance_id}"}} {health_status}',
        ]
        metrics_text = "\n".join(metrics_lines)

        return Response(content=metrics_text, media_type="text/plain")
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        raise HTTPException(status_code=503, detail="Metrics unavailable")


@app.get("/health/cluster")
async def cluster_health():
    """
    クラスター全体の健全性情報

    マルチリージョン環境でのクラスター状態を確認します。
    """
    try:
        if not health_checker.state_manager:
            return JSONResponse(
                content={
                    "status": "single_instance",
                    "message": "HA mode not enabled",
                    "instance": health_checker.check_basic_health(),
                },
                status_code=200,
            )

        cluster_status = health_checker.state_manager.get_cluster_status()
        basic_health = health_checker.check_basic_health()

        return JSONResponse(
            content={
                "status": "cluster",
                "cluster": cluster_status,
                "current_instance": basic_health,
                "timestamp": datetime.utcnow().isoformat(),
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Cluster health check failed: {e}")
        raise HTTPException(status_code=503, detail="Cluster health unavailable")


@app.post("/health/failover")
async def trigger_failover():
    """
    手動フェイルオーバーのトリガー

    緊急時に手動でフェイルオーバーを実行します。
    """
    try:
        if not health_checker.state_manager:
            raise HTTPException(status_code=400, detail="HA mode not enabled")

        logger.info("Manual failover triggered")
        success = health_checker.state_manager.handle_failover()

        if success:
            return JSONResponse(
                content={
                    "status": "success",
                    "message": "Failover completed successfully",
                    "is_leader": health_checker.state_manager.is_leader,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                status_code=200,
            )
        else:
            return JSONResponse(
                content={
                    "status": "failed",
                    "message": "Failover could not be completed",
                    "timestamp": datetime.utcnow().isoformat(),
                },
                status_code=500,
            )
    except Exception as e:
        logger.error(f"Manual failover failed: {e}")
        raise HTTPException(status_code=503, detail="Failover failed")


if __name__ == "__main__":
    # 開発時の起動用
    uvicorn.run(
        "crypto_bot.api.health:app", host="0.0.0.0", port=8080, log_level="info"
    )
