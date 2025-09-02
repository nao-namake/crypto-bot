"""
統合ログシステム - ファイル・コンソール・Discord通知の統合

レガシーシステムの複雑なログ設定をシンプル化し、
適切なログレベル管理とDiscord通知統合を実現。.
"""

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from .config import get_file_config
from .exceptions import CryptoBotError, ErrorSeverity, get_error_severity

# タイムゾーン設定（日本の取引システム用）
JST = timezone(timedelta(hours=9))  # 日本標準時


class LogLevel(Enum):
    """ログレベル定義."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


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
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
    """
    暗号資産取引Bot専用ログシステム

    ファイル出力・コンソール出力・Discord通知を統合管理.
    """

    def __init__(self, name: str = "crypto_bot"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 重複ハンドラー防止
        if self.logger.handlers:
            self.logger.handlers.clear()

        self._setup_handlers()

        # Discord通知マネージャー（Phase 15新実装）
        self._discord_manager = None

    def _setup_handlers(self) -> None:
        """ログハンドラーのセットアップ（循環参照回避版）."""
        try:
            # 🚨 CRITICAL FIX: 循環参照を防ぐため遅延インポート
            from .config import get_config  # noqa: F401

            config = get_config()
            logging_config = config.logging
        except (ImportError, AttributeError, FileNotFoundError, KeyError, RuntimeError) as e:
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

        # ログレベル設定
        log_level = getattr(logging, logging_config.level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        # コンソールハンドラー
        self._setup_console_handler()

        # ファイルハンドラー
        if logging_config.file_enabled:
            self._setup_file_handler(logging_config.retention_days)

    def _setup_console_handler(self) -> None:
        """コンソールハンドラーのセットアップ."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
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

        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)

    def set_discord_manager(self, manager: Any) -> None:
        """Discord通知マネージャーを設定（Phase 15新実装）."""
        self._discord_manager = manager

    # 旧インターフェース互換性維持
    def set_discord_notifier(self, notifier: Any) -> None:
        """Discord通知システムを設定（レガシー互換性）."""
        # 新しいDiscordManagerを使用
        if hasattr(notifier, "send_simple_message"):
            self._discord_manager = notifier
        else:
            # 旧システムの場合は警告
            self.logger.warning(
                "⚠️ 旧Discord通知システムが渡されました - 新システムに移行してください"
            )

    def _log_with_context(
        self,
        level: int,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
        discord_notify: bool = False,
    ) -> None:
        """コンテキスト付きログ出力."""
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

        # Discord通知（Phase 15簡素化実装）
        if discord_notify and self._discord_manager:
            try:
                # ログレベルに応じた重要度設定
                level_map = {
                    logging.DEBUG: "info",
                    logging.INFO: "info",
                    logging.WARNING: "warning",
                    logging.ERROR: "critical",
                    logging.CRITICAL: "critical",
                }

                discord_level = level_map.get(level, "info")

                # エラー情報がある場合はエラー通知として送信
                if error:
                    error_data = {
                        "type": type(error).__name__,
                        "message": str(error),
                        "component": (
                            extra_data.get("component", "システム") if extra_data else "システム"
                        ),
                        "severity": discord_level,
                    }
                    result = self._discord_manager.send_error_notification(error_data)
                else:
                    # 通常メッセージとして送信
                    result = self._discord_manager.send_simple_message(message, discord_level)

                if result:
                    self.logger.debug("✅ Discord通知送信成功")
                else:
                    self.logger.debug("⚠️ Discord通知送信失敗（Rate limit等）")

            except Exception as e:
                # 通知エラーは無限ループを避けるため別途ログ
                self.logger.error(f"❌ Discord通知送信に失敗: {type(e).__name__}: {e}")

    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """デバッグログ."""
        self._log_with_context(logging.DEBUG, message, extra_data)

    def info(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        discord_notify: bool = False,
    ) -> None:
        """情報ログ."""
        self._log_with_context(logging.INFO, message, extra_data, discord_notify=discord_notify)

    def warning(
        self,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        discord_notify: bool = True,
    ) -> None:
        """警告ログ."""
        self._log_with_context(logging.WARNING, message, extra_data, discord_notify=discord_notify)

    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        discord_notify: bool = True,
    ) -> None:
        """エラーログ."""
        self._log_with_context(
            logging.ERROR,
            message,
            extra_data,
            error,
            discord_notify=discord_notify,
        )

    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """クリティカルログ（必ずDiscord通知）."""
        self._log_with_context(logging.CRITICAL, message, extra_data, error, discord_notify=True)

    def log_trade(
        self,
        action: str,
        symbol: str,
        amount: float,
        price: float,
        order_id: Optional[str] = None,
        success: bool = True,
    ):
        """取引ログ（専用メソッド）."""
        trade_data = {
            "action": action,
            "symbol": symbol,
            "amount": amount,
            "price": price,
            "order_id": order_id,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if success:
            self.info(
                f"取引実行: {action} {symbol} {amount}@{price}",
                extra_data=trade_data,
                discord_notify=True,
            )
        else:
            self.error(
                f"取引失敗: {action} {symbol} {amount}@{price}",
                extra_data=trade_data,
            )

    def log_signal(
        self,
        strategy: str,
        signal: str,
        confidence: float,
        symbol: str = "BTC/JPY",
    ):
        """シグナルログ（専用メソッド）."""
        signal_data = {
            "strategy": strategy,
            "signal": signal,
            "confidence": confidence,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.info(
            f"シグナル生成: {strategy} {signal} (confidence: {confidence:.3f})",
            extra_data=signal_data,
        )

    def log_performance(
        self,
        total_pnl: float,
        win_rate: float,
        trade_count: int,
        max_drawdown: float,
    ):
        """パフォーマンスログ（専用メソッド）."""
        perf_data = {
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "trade_count": trade_count,
            "max_drawdown": max_drawdown,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.info(
            f"パフォーマンス: PnL={total_pnl:.2f} 勝率={win_rate:.1%} "
            f"取引数={trade_count} DD={max_drawdown:.1%}",
            extra_data=perf_data,
            discord_notify=True,
        )


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
