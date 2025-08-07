"""
ヘルスチェックAPI

Cloud Run のヘルスチェックとロードバランサーの監視に使用するAPIエンドポイント。
アプリケーションの状態、依存関係の確認、パフォーマンス指標を提供します。
"""

from __future__ import annotations

import json
import logging
import os
import statistics
import time
from datetime import datetime
from typing import Any, Dict, List

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

# Phase H.8.5: エラー耐性管理システム統合
try:
    from crypto_bot.utils.error_resilience import (
        get_resilience_manager,
        get_system_health_status,
    )

    RESILIENCE_AVAILABLE = True
except ImportError:
    RESILIENCE_AVAILABLE = False

logger = logging.getLogger(__name__)


def update_status(total_profit: float, trade_count: int, position):
    """
    現在の Bot 状態を JSON へ書き出して、外部モニター（Streamlit 等）から
    参照できるようにするユーティリティ。

    Parameters
    ----------
    total_profit : float
        現在までの累積損益
    trade_count : int
        約定数（取引回数）
    position : Any
        現在ポジション（無い場合は None）
    """
    status = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_profit": total_profit,
        "trade_count": trade_count,
        "position": position or "",
    }
    with open("status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


# 初期化状況を追跡するグローバル変数
INIT_STATUS = {
    "phase": "starting",  # starting, basic, statistics, features, complete
    "timestamp": datetime.utcnow().isoformat(),
    "details": {
        "api_server": False,
        "basic_system": False,
        "statistics_system": False,
        "feature_system": False,
        "trading_loop": False,
    },
    "errors": [],
}


def update_init_status(phase: str, component: str = None, error: str = None):
    """初期化状況を更新する"""
    INIT_STATUS["phase"] = phase
    INIT_STATUS["timestamp"] = datetime.utcnow().isoformat()

    if component:
        INIT_STATUS["details"][component] = True

    if error:
        INIT_STATUS["errors"].append(
            {"phase": phase, "error": error, "timestamp": datetime.utcnow().isoformat()}
        )


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

        # API キーの存在確認 (Bitbank本番専用)
        try:
            # Bitbank本番用認証情報をチェック
            bitbank_api_key = os.getenv("BITBANK_API_KEY")
            bitbank_api_secret = os.getenv("BITBANK_API_SECRET")

            if bitbank_api_key and bitbank_api_secret:
                # 信用取引モードの確認（環境変数・設定ファイル両方をチェック）
                margin_mode = False

                # まず環境変数をチェック
                env_margin = os.getenv("BITBANK_MARGIN_MODE", "false").lower() == "true"

                # 設定ファイルからも確認（利用可能な場合）
                try:
                    import yaml

                    # 本番設定ファイルを確認（固定ファイル名統一化対応）
                    config_files = [
                        "config/production/production.yml",
                        "/app/config/production/production.yml",
                        # フォールバック（旧構造）
                        "config/production/bitbank_config.yml",
                        "/app/config/production/bitbank_config.yml",
                        "config/bitbank_101features_production.yml",
                        "/app/config/bitbank_101features_production.yml",
                    ]

                    for config_file in config_files:
                        if os.path.exists(config_file):
                            with open(config_file, "r", encoding="utf-8") as f:
                                config = yaml.safe_load(f)
                                margin_config = config.get("live", {}).get(
                                    "margin_trading", {}
                                )
                                margin_mode = margin_config.get("enabled", False)
                                break

                    # 環境変数が設定されている場合はそちらを優先
                    if env_margin:
                        margin_mode = True

                except Exception:
                    # 設定ファイル読み取りエラー時は環境変数のみ使用
                    margin_mode = env_margin

                checks["api_credentials"] = {
                    "status": "healthy",
                    "details": "Bitbank API credentials configured",
                    "exchange": "bitbank",
                    "margin_mode": margin_mode,
                }
            else:
                checks["api_credentials"] = {
                    "status": "unhealthy",
                    "details": "Missing Bitbank API credentials",
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
            # status.json ファイルから最新の取引状態を読み取り（Cloud Run環境対応）
            status_file = (
                "/app/status.json"  # Phase G.2.4.1: 絶対パス統一・Cloud Run環境対応
            )
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

    def get_performance_metrics(self) -> Dict[str, Any]:
        """パフォーマンスメトリクス取得（Kelly比率・勝率・ドローダウン）"""
        try:
            # 取引履歴ファイル検索
            trade_files = []
            for file_pattern in [
                "results/*trades.csv",
                "logs/trading_metrics.jsonl",
                "trades.json",
            ]:
                import glob

                trade_files.extend(glob.glob(file_pattern))

            if not trade_files:
                return {
                    "status": "no_data",
                    "message": "No trading history found",
                    "kelly_ratio": 0.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "trade_count": 0,
                }

            # 最新の取引ファイルを使用
            latest_file = max(trade_files, key=os.path.getmtime)
            trades_data = self._parse_trading_data(latest_file)

            if not trades_data:
                return {
                    "status": "no_trades",
                    "message": "No completed trades found",
                    "kelly_ratio": 0.0,
                    "win_rate": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "trade_count": 0,
                }

            # パフォーマンス計算
            metrics = self._calculate_performance_metrics(trades_data)
            metrics["status"] = "calculated"
            metrics["last_calculation"] = datetime.utcnow().isoformat()

            return metrics

        except Exception as e:
            logger.error(f"Performance metrics calculation failed: {e}")
            return {
                "status": "error",
                "message": f"Failed to calculate metrics: {str(e)}",
                "kelly_ratio": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "trade_count": 0,
            }

    def _parse_trading_data(self, file_path: str) -> List[Dict]:
        """取引データのパース"""
        trades = []

        try:
            if file_path.endswith(".csv"):
                import csv

                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if "pnl" in row or "profit" in row:
                            pnl = float(row.get("pnl", row.get("profit", 0)))
                            trades.append(
                                {
                                    "pnl": pnl,
                                    "timestamp": row.get("timestamp", ""),
                                    "side": row.get("side", ""),
                                    "price": float(row.get("price", 0)),
                                    "quantity": float(row.get("quantity", 0)),
                                }
                            )

            elif file_path.endswith(".jsonl"):
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        data = json.loads(line.strip())
                        if data.get(
                            "type"
                        ) == "trade_execution" and "profit_loss" in data.get(
                            "data", {}
                        ):
                            metrics_data = data.get("data", {})
                            trades.append(
                                {
                                    "pnl": metrics_data.get("profit_loss", 0),
                                    "timestamp": data.get("timestamp", ""),
                                    "side": metrics_data.get("type", ""),
                                    "price": metrics_data.get("price", 0),
                                    "quantity": metrics_data.get("quantity", 0),
                                }
                            )

            elif file_path.endswith(".json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        trades = data
                    elif isinstance(data, dict) and "trades" in data:
                        trades = data["trades"]

        except Exception as e:
            logger.error(f"Failed to parse trading data from {file_path}: {e}")

        return trades

    def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict[str, Any]:
        """パフォーマンスメトリクス計算"""
        if not trades:
            return {
                "kelly_ratio": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "trade_count": 0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
            }

        # PnL抽出
        pnls = [trade["pnl"] for trade in trades if "pnl" in trade]

        if not pnls:
            return {
                "kelly_ratio": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "trade_count": 0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
            }

        # 基本統計
        total_trades = len(pnls)
        winning_trades = [pnl for pnl in pnls if pnl > 0]
        losing_trades = [pnl for pnl in pnls if pnl < 0]

        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        total_pnl = sum(pnls)

        # 平均損益
        avg_win = statistics.mean(winning_trades) if winning_trades else 0.0
        avg_loss = statistics.mean(losing_trades) if losing_trades else 0.0

        # Kelly比率計算
        kelly_ratio = 0.0
        if avg_loss != 0 and win_rate > 0:
            win_loss_ratio = abs(avg_win / avg_loss)
            kelly_ratio = win_rate - ((1 - win_rate) / win_loss_ratio)
            kelly_ratio = max(0.0, min(1.0, kelly_ratio))  # 0-1の範囲にクリップ

        # 最大ドローダウン計算
        cumulative_pnl = []
        running_total = 0
        for pnl in pnls:
            running_total += pnl
            cumulative_pnl.append(running_total)

        max_drawdown = 0.0
        if cumulative_pnl:
            peak = cumulative_pnl[0]
            for value in cumulative_pnl:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / max(abs(peak), 1) if peak != 0 else 0
                max_drawdown = max(max_drawdown, drawdown)

        # シャープレシオ計算（簡易版）
        sharpe_ratio = 0.0
        if pnls and len(pnls) > 1:
            mean_return = statistics.mean(pnls)
            std_return = statistics.stdev(pnls)
            if std_return > 0:
                sharpe_ratio = mean_return / std_return

        return {
            "kelly_ratio": round(kelly_ratio, 4),
            "win_rate": round(win_rate, 4),
            "max_drawdown": round(max_drawdown, 4),
            "sharpe_ratio": round(sharpe_ratio, 4),
            "trade_count": total_trades,
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
        }

    def get_comprehensive_health(self) -> Dict[str, Any]:
        """包括的なヘルスチェック"""
        basic = self.check_basic_health()
        dependencies = self.check_dependencies()
        trading = self.check_trading_status()
        performance = self.get_performance_metrics()

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

        # Phase H.8.5: エラー耐性情報を追加
        resilience_info = {}
        if RESILIENCE_AVAILABLE:
            try:
                resilience_info = get_system_health_status()
            except Exception as e:
                logger.warning(f"Failed to get resilience info: {e}")
                resilience_info = {"status": "unavailable", "error": str(e)}

        return {
            "overall_status": overall_status,
            "basic": basic,
            "dependencies": dependencies,
            "trading": trading,
            "performance": performance,
            "resilience": resilience_info,  # Phase H.8.5: エラー耐性情報追加
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


@app.get("/health/performance")
async def performance_metrics():
    """
    パフォーマンスメトリクス専用エンドポイント

    Kelly比率・勝率・ドローダウン・シャープレシオを提供します。
    """
    try:
        performance = health_checker.get_performance_metrics()
        return JSONResponse(content=performance, status_code=200)
    except Exception as e:
        logger.error(f"Performance metrics failed: {e}")
        raise HTTPException(status_code=503, detail="Performance metrics unavailable")


@app.get("/metrics")
async def metrics():
    """
    Prometheus形式のメトリクスエンドポイント（拡張版）
    """
    try:
        trading_status = health_checker.check_trading_status()
        basic = health_checker.check_basic_health()
        performance = health_checker.get_performance_metrics()

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

        # パフォーマンスメトリクス
        kelly_ratio = performance.get("kelly_ratio", 0)
        win_rate = performance.get("win_rate", 0)
        max_drawdown = performance.get("max_drawdown", 0)
        sharpe_ratio = performance.get("sharpe_ratio", 0)
        performance_trade_count = performance.get("trade_count", 0)

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
            "",
            "# HELP crypto_bot_kelly_ratio Kelly criterion ratio "
            "(optimal position size)",
            "# TYPE crypto_bot_kelly_ratio gauge",
            f'crypto_bot_kelly_ratio{{region="{region}",'
            f'instance="{instance_id}"}} {kelly_ratio}',
            "",
            "# HELP crypto_bot_win_rate Win rate percentage (0.0-1.0)",
            "# TYPE crypto_bot_win_rate gauge",
            f'crypto_bot_win_rate{{region="{region}",'
            f'instance="{instance_id}"}} {win_rate}',
            "",
            "# HELP crypto_bot_max_drawdown Maximum drawdown percentage (0.0-1.0)",
            "# TYPE crypto_bot_max_drawdown gauge",
            f'crypto_bot_max_drawdown{{region="{region}",'
            f'instance="{instance_id}"}} {max_drawdown}',
            "",
            "# HELP crypto_bot_sharpe_ratio Sharpe ratio (risk-adjusted return)",
            "# TYPE crypto_bot_sharpe_ratio gauge",
            f'crypto_bot_sharpe_ratio{{region="{region}",'
            f'instance="{instance_id}"}} {sharpe_ratio}',
            "",
            "# HELP crypto_bot_performance_trade_count Number of trades "
            "used for performance calculation",
            "# TYPE crypto_bot_performance_trade_count gauge",
            f'crypto_bot_performance_trade_count{{region="{region}",'
            f'instance="{instance_id}"}} {performance_trade_count}',
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


@app.get("/health/init")
async def initialization_status():
    """
    初期化状況の確認

    システムの初期化進捗を確認します。
    Cloud Runの起動時やデバッグ時に使用します。
    """
    try:
        # 初期化完了チェック
        all_components = all(INIT_STATUS["details"].values())

        # ステータスコード決定
        if INIT_STATUS["phase"] == "complete" and all_components:
            status_code = 200
        elif INIT_STATUS["errors"]:
            status_code = 503
        else:
            status_code = 202  # Accepted - still initializing

        return JSONResponse(
            content={
                "phase": INIT_STATUS["phase"],
                "timestamp": INIT_STATUS["timestamp"],
                "is_complete": all_components,
                "components": INIT_STATUS["details"],
                "errors": (
                    INIT_STATUS["errors"][-5:] if INIT_STATUS["errors"] else []
                ),  # 最新5件のエラー
                "feature_mode": os.getenv("FEATURE_MODE", "full"),
            },
            status_code=status_code,
        )
    except Exception as e:
        logger.error(f"Init status check failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to check init status")


@app.get("/health/resilience")
async def resilience_status():
    """
    エラー耐性状態専用エンドポイント（Phase H.8.5）

    システムのエラー耐性、サーキットブレーカー状態、エラー履歴を提供します。
    """
    try:
        if not RESILIENCE_AVAILABLE:
            return JSONResponse(
                content={
                    "status": "unavailable",
                    "message": "Error resilience system not available",
                },
                status_code=200,
            )

        resilience_manager = get_resilience_manager()

        # エラーサマリー（過去1時間）
        error_summary_1h = resilience_manager.get_error_summary(hours=1)

        # エラーサマリー（過去24時間）
        error_summary_24h = resilience_manager.get_error_summary(hours=24)

        # システムヘルス状態
        system_health = get_system_health_status()

        response_data = {
            "system_health": system_health,
            "error_summary_1h": error_summary_1h,
            "error_summary_24h": error_summary_24h,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # ステータスコード決定
        status_code = 200
        if system_health.get("overall_health") == "CRITICAL":
            status_code = 503
        elif system_health.get("overall_health") == "WARNING":
            status_code = 200  # 警告でも200を返す

        return JSONResponse(content=response_data, status_code=status_code)

    except Exception as e:
        logger.error(f"Resilience status check failed: {e}")
        raise HTTPException(status_code=503, detail="Resilience status unavailable")


@app.post("/health/resilience/reset")
async def reset_resilience():
    """
    エラー耐性状態リセットエンドポイント（Phase H.8.5）

    緊急停止状態やサーキットブレーカーを手動でリセットします。
    """
    try:
        if not RESILIENCE_AVAILABLE:
            raise HTTPException(
                status_code=400, detail="Error resilience system not available"
            )

        resilience_manager = get_resilience_manager()

        # 緊急停止リセット
        resilience_manager.reset_emergency_stop()

        # 全サーキットブレーカーリセット
        reset_components = []
        for component in list(resilience_manager.circuit_breakers.keys()):
            if resilience_manager.force_recovery(component):
                reset_components.append(component)

        logger.info(f"🔄 [PHASE-H8.5] Manual resilience reset: {reset_components}")

        return JSONResponse(
            content={
                "status": "success",
                "message": "Resilience state reset successfully",
                "reset_components": reset_components,
                "timestamp": datetime.utcnow().isoformat(),
            },
            status_code=200,
        )

    except Exception as e:
        logger.error(f"Resilience reset failed: {e}")
        raise HTTPException(status_code=503, detail="Resilience reset failed")


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


def start_api_server(host: str = "0.0.0.0", port: int = 8080):
    """APIサーバーを起動する関数"""
    if not FASTAPI_AVAILABLE:
        logger.error("FastAPI not available, cannot start API server")
        return

    logger.info("🌐 APIサーバーをバックグラウンド起動...")
    uvicorn.run(
        "crypto_bot.api.health:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )
    logger.info(f"✅ APIサーバー起動完了 (PID: {os.getpid()})")


if __name__ == "__main__":
    # 開発時の起動用
    start_api_server()
