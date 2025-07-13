"""
JSON構造化ログシステム

Cloud Logging検索・解析最適化のためのJSON構造化ログフォーマッタ。
エラー発生数・APIレスポンス時間メトリクス・トレーダブルイベントを記録。
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """JSON構造化ログフォーマッタ"""

    def __init__(
        self,
        service_name: str = "crypto-bot",
        service_version: str = "1.0.0",
        environment: str = None,
    ):
        super().__init__()
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment or os.getenv("ENVIRONMENT", "unknown")
        self.hostname = socket.gethostname()
        self.region = os.getenv("REGION", "unknown")
        self.instance_id = os.getenv("INSTANCE_ID", "unknown")

    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式にフォーマット"""

        # 基本ログ構造
        log_entry = {
            # タイムスタンプ（ISO 8601形式・UTC）
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            # ログレベル
            "severity": record.levelname,
            "level": record.levelno,
            # メッセージ
            "message": record.getMessage(),
            # サービス情報
            "service": {
                "name": self.service_name,
                "version": self.service_version,
                "environment": self.environment,
            },
            # インフラ情報
            "infrastructure": {
                "hostname": self.hostname,
                "region": self.region,
                "instance_id": self.instance_id,
            },
            # ログソース情報
            "source": {
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "thread": record.thread,
                "thread_name": getattr(record, "threadName", "MainThread"),
            },
        }

        # 例外情報
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # カスタムフィールド（ログに追加された属性）
        custom_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            }:
                # JSON serializable なもののみ追加
                try:
                    json.dumps(value)
                    custom_fields[key] = value
                except (TypeError, ValueError):
                    custom_fields[key] = str(value)

        if custom_fields:
            log_entry["custom"] = custom_fields

        # Google Cloud Logging 互換フィールド
        log_entry["labels"] = {
            "service_name": self.service_name,
            "environment": self.environment,
            "region": self.region,
        }

        return json.dumps(log_entry, ensure_ascii=False, separators=(",", ":"))


class TradingMetricsHandler(logging.Handler):
    """取引メトリクス専用ハンドラー"""

    def __init__(self):
        super().__init__()
        self.metrics_buffer = []
        self.last_flush = time.time()
        self.flush_interval = 60  # 60秒間隔でフラッシュ

    def emit(self, record: logging.LogRecord):
        """メトリクスレコードをバッファに追加"""
        if hasattr(record, "metrics_type"):
            metric_entry = {
                "timestamp": datetime.fromtimestamp(
                    record.created, tz=timezone.utc
                ).isoformat(),
                "type": record.metrics_type,
                "data": getattr(record, "metrics_data", {}),
                "message": record.getMessage(),
            }

            self.metrics_buffer.append(metric_entry)

            # 定期的にフラッシュ
            if time.time() - self.last_flush > self.flush_interval:
                self.flush_metrics()

    def flush_metrics(self):
        """メトリクスをファイルに出力"""
        if not self.metrics_buffer:
            return

        try:
            metrics_file = "logs/trading_metrics.jsonl"
            os.makedirs(os.path.dirname(metrics_file), exist_ok=True)

            with open(metrics_file, "a", encoding="utf-8") as f:
                for metric in self.metrics_buffer:
                    f.write(json.dumps(metric, ensure_ascii=False) + "\n")

            self.metrics_buffer.clear()
            self.last_flush = time.time()

        except Exception as e:
            # ログ出力エラーを避けるため、標準エラーに出力
            print(f"Failed to flush trading metrics: {e}")


def setup_structured_logging(
    service_name: str = "crypto-bot",
    log_level: str = None,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_metrics: bool = True,
) -> logging.Logger:
    """構造化ログシステムのセットアップ"""

    # ログレベル設定
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # JSON フォーマッター
    json_formatter = JSONFormatter(service_name=service_name)

    # コンソールハンドラー（本番環境での標準出力）
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(json_formatter)
        root_logger.addHandler(console_handler)

    # ファイルハンドラー（ローカル開発用）
    if enable_file and os.getenv("ENVIRONMENT", "development") == "development":
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler("logs/application.jsonl", encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)

    # メトリクスハンドラー
    if enable_metrics:
        metrics_handler = TradingMetricsHandler()
        metrics_handler.setLevel(logging.INFO)
        root_logger.addHandler(metrics_handler)

    # アプリケーション用ロガー
    app_logger = logging.getLogger(service_name)

    return app_logger


class StructuredLogger:
    """構造化ログ用のヘルパークラス"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_api_request(
        self,
        endpoint: str,
        method: str,
        response_time: float,
        status_code: int = None,
        error: str = None,
    ):
        """Record API request logs."""
        extra = {
            "api_endpoint": endpoint,
            "http_method": method,
            "response_time_ms": round(response_time * 1000, 2),
            "status_code": status_code,
            "metrics_type": "api_request",
            "metrics_data": {
                "endpoint": endpoint,
                "method": method,
                "response_time": response_time,
                "status_code": status_code,
                "success": status_code is None or (200 <= status_code < 400),
            },
        }

        if error:
            extra["error"] = error
            self.logger.error(f"API request failed: {method} {endpoint}", extra=extra)
        else:
            self.logger.info(f"API request: {method} {endpoint}", extra=extra)

    def log_trade_execution(
        self,
        trade_type: str,
        symbol: str,
        price: float,
        quantity: float,
        profit_loss: float = None,
        strategy: str = None,
    ):
        """取引実行のログ記録"""
        extra = {
            "trade_type": trade_type,
            "symbol": symbol,
            "price": price,
            "quantity": quantity,
            "profit_loss": profit_loss,
            "strategy": strategy,
            "metrics_type": "trade_execution",
            "metrics_data": {
                "type": trade_type,
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "profit_loss": profit_loss,
                "strategy": strategy,
            },
        }

        self.logger.info(f"Trade executed: {trade_type} {symbol}", extra=extra)

    def log_signal_generation(
        self,
        signal_strength: float,
        timeframe: str,
        features_count: int,
        vix_level: float = None,
        threshold: float = None,
    ):
        """シグナル生成のログ記録"""
        extra = {
            "signal_strength": signal_strength,
            "timeframe": timeframe,
            "features_count": features_count,
            "vix_level": vix_level,
            "threshold": threshold,
            "metrics_type": "signal_generation",
            "metrics_data": {
                "signal_strength": signal_strength,
                "timeframe": timeframe,
                "features_count": features_count,
                "vix_level": vix_level,
                "threshold": threshold,
            },
        }

        self.logger.info(
            f"Signal generated: strength={signal_strength:.3f}", extra=extra
        )

    def log_portfolio_metrics(
        self,
        total_balance: float,
        pnl: float,
        win_rate: float,
        sharpe_ratio: float = None,
        max_drawdown: float = None,
        kelly_ratio: float = None,
    ):
        """ポートフォリオメトリクスのログ記録"""
        extra = {
            "total_balance": total_balance,
            "pnl": pnl,
            "win_rate": win_rate,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "kelly_ratio": kelly_ratio,
            "metrics_type": "portfolio_metrics",
            "metrics_data": {
                "total_balance": total_balance,
                "pnl": pnl,
                "win_rate": win_rate,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "kelly_ratio": kelly_ratio,
            },
        }

        self.logger.info(
            f"Portfolio update: PnL={pnl:.2f}, WinRate={win_rate:.1%}", extra=extra
        )

    def log_system_error(
        self,
        error_type: str,
        component: str,
        error_message: str,
        stack_trace: str = None,
    ):
        """システムエラーのログ記録"""
        extra = {
            "error_type": error_type,
            "component": component,
            "stack_trace": stack_trace,
            "metrics_type": "system_error",
            "metrics_data": {
                "error_type": error_type,
                "component": component,
                "severity": "error",
            },
        }

        self.logger.error(f"System error in {component}: {error_message}", extra=extra)


def get_structured_logger(name: str = None) -> StructuredLogger:
    """構造化ログインスタンスを取得"""
    logger_name = name or "crypto-bot"
    logger = logging.getLogger(logger_name)
    return StructuredLogger(logger)


# 使用例とテスト用関数
def test_structured_logging():
    """構造化ログのテスト"""
    # ログシステムセットアップ
    setup_structured_logging(log_level="DEBUG")

    # 構造化ロガー取得
    structured_logger = get_structured_logger()

    # 各種ログテスト
    structured_logger.log_api_request(
        endpoint="/api/v1/orders", method="POST", response_time=0.234, status_code=200
    )

    structured_logger.log_trade_execution(
        trade_type="BUY",
        symbol="BTC/JPY",
        price=5000000.0,
        quantity=0.01,
        profit_loss=1500.0,
        strategy="multi_timeframe",
    )

    structured_logger.log_signal_generation(
        signal_strength=0.72,
        timeframe="1h",
        features_count=101,
        vix_level=22.5,
        threshold=0.45,
    )

    structured_logger.log_portfolio_metrics(
        total_balance=1050000.0,
        pnl=50000.0,
        win_rate=0.65,
        sharpe_ratio=1.8,
        max_drawdown=0.08,
        kelly_ratio=0.25,
    )

    print("✅ 構造化ログテスト完了")


if __name__ == "__main__":
    test_structured_logging()
