"""
Unified Logging System - Phase 16.2-B Integration

統合ログシステム - 以下の2つのファイルを統合:
- logger.py (423行) - JSON構造化ログフォーマッタ
- logging.py (51行) - 基本ログ設定

統合後の機能:
- JSON構造化ログ・Cloud Logging最適化
- 基本ログ設定・環境変数対応
- メトリクス記録・トレーダブルイベント
- ログレベル管理・ファイルローテーション

Phase 16.2-B実装日: 2025年8月8日
統合対象行数: 474行
"""

from __future__ import annotations

import json
import logging
import os
import socket

# time import removed - not currently used
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional, Union

# ==============================================================================
# JSON構造化ログフォーマッタ (from logger.py)
# ==============================================================================


class JSONFormatter(logging.Formatter):
    """JSON構造化ログフォーマッタ - Cloud Logging検索・解析最適化"""

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

    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式でフォーマット"""
        # 基本ログ情報
        log_data = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": {
                "name": self.service_name,
                "version": self.service_version,
                "environment": self.environment,
            },
            "system": {
                "hostname": self.hostname,
                "process_id": os.getpid(),
                "thread_name": record.threadName,
            },
            "location": {
                "filename": record.filename,
                "line_number": record.lineno,
                "function_name": record.funcName,
                "module": record.module,
            },
        }

        # 例外情報の追加
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # 追加フィールドの処理
        if hasattr(record, "extra_fields"):
            log_data["extra"] = record.extra_fields

        return json.dumps(log_data, ensure_ascii=False)


# ==============================================================================
# 基本ログ設定機能 (from logging.py)
# ==============================================================================


def setup_logging(
    level: Optional[Union[str, int]] = None,
    format_type: str = "standard",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """統合ログ設定

    Args:
        level: ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: フォーマット種別 ('standard', 'json')
        log_file: ログファイルパス
        max_bytes: ログファイル最大サイズ
        backup_count: バックアップファイル数
    """
    # ログレベル決定
    if level is None:
        level_name = os.getenv("CRYPTO_BOT_LOG_LEVEL", "INFO").upper()
        if hasattr(logging, level_name):
            level = getattr(logging, level_name)
        else:
            level = logging.INFO
    elif isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    # フォーマッター選択
    if format_type == "json":
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 既存ハンドラーのクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # コンソールハンドラー
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ファイルハンドラー（オプション）
    if log_file:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 外部ライブラリのログレベル調整
    _configure_external_loggers()


def _configure_external_loggers() -> None:
    """外部ライブラリのログレベル調整"""
    external_loggers = [
        "httpx",
        "httpcore",
        "urllib3",
        "ccxt",
        "asyncio",
        "websockets",
        "requests",
    ]

    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.WARNING)


# ==============================================================================
# 統合ログユーティリティ
# ==============================================================================


def get_structured_logger(
    name: str, service_name: str = "crypto-bot", service_version: str = "1.0.0"
) -> logging.Logger:
    """構造化ログ対応のロガー取得"""
    logger = logging.getLogger(name)

    # JSON フォーマッタが設定されていない場合は追加
    if not any(isinstance(h.formatter, JSONFormatter) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter(service_name, service_version))
        logger.addHandler(handler)
        logger.propagate = False  # 重複ログ防止

    return logger


def log_trading_event(
    logger: logging.Logger,
    event_type: str,
    symbol: str,
    action: str,
    amount: float = None,
    price: float = None,
    **kwargs,
) -> None:
    """取引イベントログ"""
    extra_fields = {
        "event_type": "trading",
        "trading_event": event_type,
        "symbol": symbol,
        "action": action,
    }

    if amount is not None:
        extra_fields["amount"] = amount
    if price is not None:
        extra_fields["price"] = price

    extra_fields.update(kwargs)

    logger.info(
        f"Trading event: {event_type} - {action} {symbol}",
        extra={"extra_fields": extra_fields},
    )


def log_performance_metric(
    logger: logging.Logger, metric_name: str, value: float, unit: str = None, **kwargs
) -> None:
    """パフォーマンスメトリクスログ"""
    extra_fields = {
        "event_type": "metric",
        "metric_name": metric_name,
        "value": value,
    }

    if unit:
        extra_fields["unit"] = unit

    extra_fields.update(kwargs)

    logger.info(
        f"Metric: {metric_name} = {value}" + (f" {unit}" if unit else ""),
        extra={"extra_fields": extra_fields},
    )


# ==============================================================================
# INTEGRATION STATUS
# ==============================================================================
"""
Phase 16.2-B 統合完了:
✅ JSONFormatter統合完了 (logger.py機能)
✅ setup_logging統合完了 (logging.py機能)
✅ 外部ライブラリログレベル調整統合
✅ 構造化ログユーティリティ追加
✅ 取引イベント・メトリクスログ統合

統合効果:
- ファイル数50%削減 (2→1)
- 機能統一・重複解消
- API一元化・保守性向上
"""
