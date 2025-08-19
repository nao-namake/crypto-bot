"""
統一外部APIリトライ処理システム
exponential backoff・circuit breaker機能付き
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Circuit Breaker パターン実装"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Circuit Breaker経由でAPI呼び出し"""
        with self._lock:
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker: HALF_OPEN state")
                else:
                    logger.warning("Circuit breaker: OPEN - call blocked")
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise e

    def _should_attempt_reset(self) -> bool:
        """リセット試行判定"""
        if self.last_failure_time is None:
            return True
        return datetime.now() - self.last_failure_time > timedelta(
            seconds=self.recovery_timeout
        )

    def _on_success(self):
        """成功時の処理"""
        self.failure_count = 0
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            logger.info("Circuit breaker: Recovered to CLOSED state")

    def _on_failure(self):
        """失敗時の処理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker: OPEN after {self.failure_count} failures")


class ExponentialBackoffRetry:
    """Exponential Backoff リトライ処理"""

    def __init__(
        self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """Exponential Backoff付きリトライ実行"""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    logger.warning(
                        f"Retry {attempt + 1}/{self.max_retries} after {delay:.2f}s: "
                        f"{e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries ({self.max_retries}) exceeded: {e}")

        raise last_exception


class APIRetryManager:
    """統一APIリトライ管理システム"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        circuit_breaker_enabled: bool = True,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,
    ):

        self.retry_handler = ExponentialBackoffRetry(max_retries, base_delay, max_delay)
        self.circuit_breaker = (
            CircuitBreaker(failure_threshold, recovery_timeout)
            if circuit_breaker_enabled
            else None
        )

        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_breaker_blocks": 0,
            "retry_attempts": 0,
        }

    def call_api(self, func: Callable, *args, **kwargs) -> Any:
        """統一APIリトライ処理"""
        self.stats["total_calls"] += 1

        try:
            if self.circuit_breaker:
                # Circuit Breaker経由でリトライ処理実行
                result = self.circuit_breaker.call(
                    self._retry_with_stats, func, *args, **kwargs
                )
            else:
                # 直接リトライ処理実行
                result = self._retry_with_stats(func, *args, **kwargs)

            self.stats["successful_calls"] += 1
            return result

        except Exception as e:
            self.stats["failed_calls"] += 1
            if "Circuit breaker is OPEN" in str(e):
                self.stats["circuit_breaker_blocks"] += 1
            raise e

    def _retry_with_stats(self, func: Callable, *args, **kwargs) -> Any:
        """統計情報付きリトライ実行"""
        try:
            return self.retry_handler.retry(func, *args, **kwargs)
        except Exception as e:
            # リトライ回数を統計に記録
            self.stats["retry_attempts"] += self.retry_handler.max_retries
            raise e

    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得"""
        return {
            **self.stats,
            "success_rate": self.stats["successful_calls"]
            / max(self.stats["total_calls"], 1),
            "circuit_breaker_state": (
                self.circuit_breaker.state if self.circuit_breaker else "DISABLED"
            ),
        }

    def reset_stats(self):
        """統計情報リセット"""
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "circuit_breaker_blocks": 0,
            "retry_attempts": 0,
        }


# グローバル APIリトライ管理インスタンス
_global_retry_manager = APIRetryManager(
    max_retries=3,
    base_delay=2.0,
    max_delay=60.0,
    circuit_breaker_enabled=True,
    failure_threshold=5,
    recovery_timeout=300,
)


def api_retry(
    max_retries: int = 3, base_delay: float = 2.0, circuit_breaker: bool = True
):
    """APIリトライデコレーター"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return _global_retry_manager.call_api(func, *args, **kwargs)

        return wrapper

    return decorator


def get_api_retry_stats() -> Dict[str, Any]:
    """グローバルAPIリトライ統計情報取得"""
    return _global_retry_manager.get_stats()


def reset_api_retry_stats():
    """グローバルAPIリトライ統計情報リセット"""
    _global_retry_manager.reset_stats()
