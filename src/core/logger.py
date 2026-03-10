"""統合ログシステム - JSTタイムゾーン・構造化ログ・カラー出力."""

import json
import logging
import logging.handlers
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_file_config
from .exceptions import CryptoBotError

# タイムゾーン設定（日本の取引システム用）
JST = timezone(timedelta(hours=9))  # 日本標準時


class JSONFormatter(logging.Formatter):
    """
    JSON形式でログを出力するフォーマッター

    構造化ログにより解析・監視を容易にする.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(JST).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 例外情報を追加
        if record.exc_info:
            log_data["exception"] = {
                "type": (record.exc_info[0].__name__ if record.exc_info[0] else None),
                "message": (str(record.exc_info[1]) if record.exc_info[1] else None),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # 追加コンテキスト情報
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        # CryptoBotError固有の情報
        if hasattr(record, "error_context"):
            log_data["error_context"] = record.error_context

        return json.dumps(log_data, ensure_ascii=False)


class ColorFormatter(logging.Formatter):
    """
    コンソール用カラーフォーマッター

    開発時の視認性向上.
    """

    COLORS = {
        "DEBUG": "\033[36m",  # シアン
        "INFO": "\033[32m",  # 緑
        "WARNING": "\033[33m",  # 黄
        "ERROR": "\033[31m",  # 赤
        "CRITICAL": "\033[95m",  # マゼンタ
        "RESET": "\033[0m",  # リセット
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]

        # タイムスタンプ
        timestamp = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")

        # レベル（色付き）
        level = f"{color}[{record.levelname:8}]{reset}"

        # ロガー名
        logger_name = f"[{record.name}]"

        # メッセージ
        message = record.getMessage()

        # 例外情報
        exc_text = ""
        if record.exc_info:
            exc_text = f"\n{self.formatException(record.exc_info)}"

        return f"{timestamp} {level} {logger_name} {message}{exc_text}"


class CryptoBotLogger:
    """暗号資産取引Bot専用ログシステム（ファイル出力・コンソール出力）."""

    def __init__(self, name: str = "crypto_bot"):
        self.name = name
        self.logger = logging.getLogger(name)

        # Phase 35: 環境変数からログレベルを取得（バックテスト最適化）
        env_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
        initial_level = getattr(logging, env_log_level, logging.DEBUG)
        self.logger.setLevel(initial_level)

        # 重複ハンドラー防止
        if self.logger.handlers:
            self.logger.handlers.clear()

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """ログハンドラーのセットアップ（循環参照回避版）."""
        try:
            # 🚨 CRITICAL FIX: 循環参照を防ぐため遅延インポート
            from .config import get_config  # noqa: F401

            config = get_config()
            logging_config = config.logging
        except (
            ImportError,
            AttributeError,
            FileNotFoundError,
            KeyError,
            RuntimeError,
        ) as e:
            # 循環参照エラーや設定エラー時はデフォルト設定使用
            # RuntimeError: テスト環境で設定が未読み込み時の対応・RecursionError(RuntimeError継承)も含む
            if isinstance(e, RecursionError):
                # 循環参照の場合は追加ログを出力しない（さらなる循環を防ぐ）
                pass
            # デフォルト設定オブジェクトを作成（型安全）

            class DefaultLoggingConfig:
                level: str = "INFO"
                file_enabled: bool = True
                retention_days: int = 7

            logging_config = DefaultLoggingConfig()

        # Phase 35: ログレベル設定（環境変数を最優先）
        env_log_level = os.getenv("LOG_LEVEL")
        if env_log_level:
            log_level = getattr(logging, env_log_level.upper(), logging.INFO)
        else:
            log_level = getattr(logging, logging_config.level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        # コンソールハンドラー
        self._setup_console_handler()

        # ファイルハンドラー
        if logging_config.file_enabled:
            self._setup_file_handler(logging_config.retention_days)

    def _setup_console_handler(self) -> None:
        """コンソールハンドラーのセットアップ（Phase 35: 環境変数対応）."""
        console_handler = logging.StreamHandler(sys.stdout)
        # Phase 35: 環境変数でハンドラーレベルも制御
        env_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
        handler_level = getattr(logging, env_log_level, logging.DEBUG)
        console_handler.setLevel(handler_level)
        console_handler.setFormatter(ColorFormatter())
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self, retention_days: Optional[int] = None) -> None:
        """ファイルハンドラーのセットアップ."""
        # 設定ファイルからパラメータ取得
        if retention_days is None:
            retention_days = get_file_config("logging.retention_days", 7)

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"{self.name}.log"

        # ローテーションハンドラー（日次、保持期間設定）
        # 設定ファイルからローテーション設定取得
        backup_count = get_file_config("logging.backup_count", retention_days)

        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=str(log_file),
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
        )

        # Phase 35: 環境変数でハンドラーレベルも制御（バックテスト最適化）
        env_log_level = os.getenv("LOG_LEVEL", "DEBUG").upper()
        handler_level = getattr(logging, env_log_level, logging.DEBUG)
        file_handler.setLevel(handler_level)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)

    def _log_with_context(
        self,
        level: int,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """コンテキスト付きログ出力."""
        # Phase 35.7: バックテストモード時のログフィルタ（高速化）
        is_backtest = os.environ.get("BACKTEST_MODE") == "true"

        # バックテストモード時は不要なログをスキップ
        if is_backtest and level == logging.INFO:
            # INFO レベルは完全スキップ（I/O削減）
            return

        # ログレコード作成
        extra = {}
        if extra_data:
            extra["extra_data"] = extra_data

        if isinstance(error, CryptoBotError):
            extra["error_context"] = error.to_dict()

        # ログ出力
        if error:
            self.logger.log(level, message, exc_info=error, extra=extra)
        else:
            self.logger.log(level, message, extra=extra)

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """デバッグログ."""
        self._log_with_context(logging.DEBUG, message, extra_data)

    def info(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """情報ログ."""
        self._log_with_context(logging.INFO, message, extra_data)

    def warning(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """警告ログ."""
        self._log_with_context(logging.WARNING, message, extra_data)

    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """エラーログ."""
        self._log_with_context(logging.ERROR, message, extra_data, error)

    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """クリティカルログ."""
        self._log_with_context(logging.CRITICAL, message, extra_data, error)

    def conditional_log(
        self,
        message: str,
        level: str = "info",
        backtest_level: str = "debug",
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """バックテストモード自動判定ログ."""
        is_backtest = os.environ.get("BACKTEST_MODE") == "true"
        effective_level = backtest_level if is_backtest else level

        level_map = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL,
        }

        log_level = level_map.get(effective_level.lower(), logging.INFO)

        if log_level == logging.CRITICAL:
            self.critical(message, extra_data=extra_data)
        elif log_level == logging.ERROR:
            self.error(message, extra_data=extra_data)
        elif log_level == logging.WARNING:
            self.warning(message, extra_data=extra_data)
        elif log_level == logging.INFO:
            self.info(message, extra_data=extra_data)
        else:  # DEBUG
            self.debug(message, extra_data=extra_data)


# グローバルロガーインスタンス
_logger_instance: Optional[CryptoBotLogger] = None


def get_logger(name: str = "crypto_bot") -> CryptoBotLogger:
    """グローバルロガーを取得."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = CryptoBotLogger(name)
    return _logger_instance


def setup_logging(name: str = "crypto_bot") -> CryptoBotLogger:
    """ログシステムを初期化."""
    global _logger_instance
    _logger_instance = CryptoBotLogger(name)
    return _logger_instance
