"""
Bitbank API制限対応システム拡張
429エラー対応・自動リトライ・exponential backoff・circuit breaker実装
"""

import logging
import random
import re
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """サーキットブレーカー状態"""

    CLOSED = "closed"  # 正常状態
    OPEN = "open"  # 開放状態（リクエスト拒否）
    HALF_OPEN = "half_open"  # 半開放状態（試験的リクエスト）


class APIError(Exception):
    """API エラー"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.retry_after = retry_after


class RateLimitError(APIError):
    """レート制限エラー"""

    pass


class CircuitBreaker:
    """
    サーキットブレーカー実装

    連続失敗時にAPI呼び出しを一時停止し、
    システム保護とリカバリを管理
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()

        logger.info(
            "CircuitBreaker initialized: threshold=%d, timeout=%d",
            failure_threshold,
            recovery_timeout,
        )

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        サーキットブレーカー経由でファンクション呼び出し

        Args:
            func: 呼び出し関数
            *args: 関数引数
            **kwargs: 関数キーワード引数

        Returns:
            関数の実行結果

        Raises:
            CircuitBreakerOpenError: サーキットが開放中
            元の例外: 関数実行時の例外
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker half-open, attempting reset")
                else:
                    raise APIError("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result

            except self.expected_exception:
                self._on_failure()
                raise

    def _should_attempt_reset(self) -> bool:
        """リセット試行判定"""
        if self.last_failure_time is None:
            return True

        return (
            datetime.now() - self.last_failure_time
        ).total_seconds() > self.recovery_timeout

    def _on_success(self) -> None:
        """成功時の処理"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        logger.debug("Circuit breaker reset to closed")

    def _on_failure(self) -> None:
        """失敗時の処理"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


class ExponentialBackoff:
    """
    指数バックオフ実装

    リトライ間隔を指数的に増加させる
    """

    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
    ):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter

        self.current_delay = initial_delay

    def get_delay(self) -> float:
        """次の遅延時間を取得"""
        delay = min(self.current_delay, self.max_delay)

        if self.jitter:
            # ジッターを追加（±20%）
            jitter_factor = random.uniform(0.8, 1.2)
            delay *= jitter_factor

        # 次回のために遅延を増加
        self.current_delay = min(self.current_delay * self.multiplier, self.max_delay)

        return delay

    def reset(self) -> None:
        """遅延をリセット"""
        self.current_delay = self.initial_delay


class AdvancedAPIRateLimiter:
    """
    高度なAPI制限管理システム

    429エラー対応・自動リトライ・circuit breaker・exponential backoff統合
    """

    def __init__(
        self,
        get_limit: int = 10,
        post_limit: int = 6,
        window_seconds: int = 1,
        max_retries: int = 3,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: int = 60,
    ):

        # 基本レート制限
        self.get_limit = get_limit
        self.post_limit = post_limit
        self.window_seconds = window_seconds
        self.max_retries = max_retries

        # リクエスト履歴
        self.get_requests: deque = deque()
        self.post_requests: deque = deque()
        self.lock = threading.Lock()

        # サーキットブレーカー
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_timeout,
            expected_exception=APIError,
        )

        # 統計情報
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited_requests": 0,
            "circuit_breaker_opens": 0,
            "total_retries": 0,
        }

        logger.info("AdvancedAPIRateLimiter initialized")
        logger.info(f"Limits: GET {get_limit}/sec, POST {post_limit}/sec")
        logger.info(
            "Circuit breaker: threshold=%d, timeout=%d",
            circuit_breaker_threshold,
            circuit_breaker_timeout,
        )

    def execute_with_limit(
        self, func: Callable, request_type: str = "POST", *args, **kwargs
    ) -> Any:
        """
        レート制限付きでファンクション実行

        Args:
            func: 実行する関数
            request_type: リクエストタイプ ("GET" or "POST")
            *args: 関数引数
            **kwargs: 関数キーワード引数

        Returns:
            関数の実行結果
        """
        self.stats["total_requests"] += 1

        # サーキットブレーカーチェック
        try:
            return self.circuit_breaker.call(
                self._execute_with_retry, func, request_type, *args, **kwargs
            )
        except APIError:
            self.stats["failed_requests"] += 1
            raise

    def _execute_with_retry(
        self, func: Callable, request_type: str, *args, **kwargs
    ) -> Any:
        """
        リトライ付きでファンクション実行

        Args:
            func: 実行する関数
            request_type: リクエストタイプ
            *args: 関数引数
            **kwargs: 関数キーワード引数

        Returns:
            関数の実行結果
        """
        backoff = ExponentialBackoff()
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # レート制限チェック
                self._wait_for_rate_limit(request_type)

                # 関数実行
                result = func(*args, **kwargs)

                # 成功時の処理
                self._record_request(request_type)
                self.stats["successful_requests"] += 1

                if attempt > 0:
                    logger.info(f"Request succeeded after {attempt} retries")

                return result

            except Exception as e:
                last_exception = e

                # 429エラーの場合
                if self._is_rate_limit_error(e):
                    self.stats["rate_limited_requests"] += 1
                    retry_after = self._extract_retry_after(e)

                    if retry_after:
                        logger.warning(f"Rate limited, waiting {retry_after} seconds")
                        time.sleep(retry_after)
                    else:
                        # Retry-After情報がない場合は指数バックオフ
                        delay = backoff.get_delay()
                        logger.warning(f"Rate limited, backing off {delay:.2f} seconds")
                        time.sleep(delay)

                # その他のエラーの場合
                elif attempt < self.max_retries:
                    self.stats["total_retries"] += 1
                    delay = backoff.get_delay()
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)

                # 最後の試行で失敗
                else:
                    logger.error(
                        f"Request failed after {self.max_retries} retries: {e}"
                    )
                    raise APIError(f"Max retries exceeded: {e}")

        # 理論上ここには到達しない
        raise APIError(f"Unexpected error: {last_exception}")

    def _wait_for_rate_limit(self, request_type: str) -> None:
        """レート制限待機"""
        with self.lock:
            self._cleanup_old_requests()

            if request_type.upper() == "GET":
                current_requests = len(self.get_requests)
                limit = self.get_limit
                request_queue = self.get_requests
            else:
                current_requests = len(self.post_requests)
                limit = self.post_limit
                request_queue = self.post_requests

            if current_requests >= limit:
                # 最も古いリクエストから待機時間を計算
                oldest_request = request_queue[0]
                wait_time = (
                    self.window_seconds
                    - (datetime.now() - oldest_request).total_seconds()
                )

                if wait_time > 0:
                    logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                    time.sleep(wait_time)

    def _record_request(self, request_type: str) -> None:
        """リクエスト記録"""
        with self.lock:
            now = datetime.now()

            if request_type.upper() == "GET":
                self.get_requests.append(now)
            else:
                self.post_requests.append(now)

    def _cleanup_old_requests(self) -> None:
        """古いリクエスト記録クリーンアップ"""
        cutoff_time = datetime.now() - timedelta(seconds=self.window_seconds)

        while self.get_requests and self.get_requests[0] < cutoff_time:
            self.get_requests.popleft()

        while self.post_requests and self.post_requests[0] < cutoff_time:
            self.post_requests.popleft()

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """レート制限エラー判定"""
        # 一般的なレート制限エラーパターン
        error_str = str(error).lower()

        # HTTP 429エラー
        if "429" in error_str:
            return True

        # Bitbank固有のエラーコード
        if "rate limit" in error_str or "too many requests" in error_str:
            return True

        # その他のレート制限インディケーター
        rate_limit_indicators = [
            "ratelimit",
            "rate_limit",
            "too_many_requests",
            "request_limit_exceeded",
            "api_limit_exceeded",
        ]

        return any(indicator in error_str for indicator in rate_limit_indicators)

    def _extract_retry_after(self, error: Exception) -> Optional[int]:
        """Retry-After情報抽出"""
        error_str = str(error)

        # Retry-After ヘッダーの抽出を試行
        # "Retry-After: 60" パターン
        match = re.search(r"retry[_-]after[:\s]*(\d+)", error_str, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # "wait 60 seconds" パターン
        match = re.search(r"wait[:\s]*(\d+)", error_str, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    def get_status(self) -> Dict[str, Any]:
        """ステータス情報取得"""
        with self.lock:
            self._cleanup_old_requests()

            return {
                "rate_limits": {
                    "get_limit": self.get_limit,
                    "post_limit": self.post_limit,
                    "window_seconds": self.window_seconds,
                    "current_get_requests": len(self.get_requests),
                    "current_post_requests": len(self.post_requests),
                    "get_utilization": len(self.get_requests) / self.get_limit,
                    "post_utilization": len(self.post_requests) / self.post_limit,
                },
                "circuit_breaker": {
                    "state": self.circuit_breaker.state.value,
                    "failure_count": self.circuit_breaker.failure_count,
                    "last_failure_time": (
                        self.circuit_breaker.last_failure_time.isoformat()
                        if self.circuit_breaker.last_failure_time
                        else None
                    ),
                },
                "statistics": self.stats.copy(),
            }

    def reset_stats(self) -> None:
        """統計情報リセット"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "rate_limited_requests": 0,
            "circuit_breaker_opens": 0,
            "total_retries": 0,
        }

        logger.info("API rate limiter stats reset")


# デコレータ版
def rate_limited(limiter: AdvancedAPIRateLimiter, request_type: str = "POST"):
    """
    レート制限デコレータ

    Args:
        limiter: AdvancedAPIRateLimiter インスタンス
        request_type: リクエストタイプ ("GET" or "POST")
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return limiter.execute_with_limit(func, request_type, *args, **kwargs)

        return wrapper

    return decorator
