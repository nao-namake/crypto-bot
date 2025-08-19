"""
エラー耐性強化システム - Phase H.8.3
包括的エラーハンドリング・リカバリ・サーキットブレーカー機能
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """エラー記録"""

    timestamp: datetime
    error_type: str
    error_message: str
    component: str
    severity: str
    recovery_attempted: bool = False
    recovery_successful: bool = False


@dataclass
class CircuitBreakerState:
    """サーキットブレーカー状態"""

    component: str
    state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    failure_threshold: int = 5
    recovery_timeout: int = 300  # 5分

    def reset(self):
        """状態リセット"""
        self.state = "CLOSED"
        self.failure_count = 0
        self.last_failure_time = None


class ErrorResilienceManager:
    """エラー耐性管理システム"""

    def __init__(self, max_error_history: int = 1000):
        self.error_history: List[ErrorRecord] = []
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {}
        self.max_error_history = max_error_history
        self.lock = threading.Lock()

        # Phase H.8.3: 緊急停止フラグ
        self.emergency_stop = False
        self.critical_error_count = 0
        self.critical_error_threshold = 3

        logger.info("🛡️ [PHASE-H8.3] Error Resilience Manager initialized")

    def record_error(
        self,
        component: str,
        error_type: str,
        error_message: str,
        severity: str = "WARNING",
    ) -> None:
        """エラー記録"""
        with self.lock:
            error_record = ErrorRecord(
                timestamp=datetime.now(),
                error_type=error_type,
                error_message=error_message,
                component=component,
                severity=severity,
            )

            self.error_history.append(error_record)

            # 履歴サイズ制限
            if len(self.error_history) > self.max_error_history:
                self.error_history = self.error_history[-self.max_error_history :]

            # CRITICAL エラーの場合
            if severity == "CRITICAL":
                self.critical_error_count += 1
                logger.critical(
                    f"🚨 [RESILIENCE] CRITICAL error recorded: {component} - {error_type}"
                )

                # 緊急停止判定
                if self.critical_error_count >= self.critical_error_threshold:
                    self.emergency_stop = True
                    logger.critical(
                        f"🚨 [RESILIENCE] EMERGENCY STOP activated: {self.critical_error_count} critical errors"
                    )

            # サーキットブレーカー更新
            self._update_circuit_breaker(component, False)

            logger.warning(
                f"⚠️ [RESILIENCE] Error recorded: {component} - {error_type} - {severity}"
            )

    def record_success(self, component: str) -> None:
        """成功記録（サーキットブレーカー回復用）"""
        with self.lock:
            self._update_circuit_breaker(component, True)

            # CRITICAL エラーカウントのリセット条件
            if component in ["data_fetcher", "ml_strategy", "trading_core"]:
                if self.critical_error_count > 0:
                    self.critical_error_count = max(0, self.critical_error_count - 1)
                    logger.info(
                        f"✅ [RESILIENCE] Critical error count reduced: {self.critical_error_count}"
                    )

    def _update_circuit_breaker(self, component: str, success: bool) -> None:
        """サーキットブレーカー状態更新"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = CircuitBreakerState(component=component)

        breaker = self.circuit_breakers[component]
        current_time = datetime.now()

        if success:
            breaker.last_success_time = current_time
            if breaker.state == "HALF_OPEN":
                # HALF_OPEN状態で成功 → CLOSED状態に復帰
                breaker.reset()
                logger.info(f"✅ [RESILIENCE] Circuit breaker RECOVERED: {component}")
            elif breaker.state == "CLOSED":
                # 成功時は失敗カウントを減らす
                breaker.failure_count = max(0, breaker.failure_count - 1)
        else:
            breaker.failure_count += 1
            breaker.last_failure_time = current_time

            if (
                breaker.state == "CLOSED"
                and breaker.failure_count >= breaker.failure_threshold
            ):
                # 失敗閾値超過 → OPEN状態
                breaker.state = "OPEN"
                logger.critical(f"🚨 [RESILIENCE] Circuit breaker OPENED: {component}")
            elif breaker.state == "HALF_OPEN":
                # HALF_OPEN状態で失敗 → OPEN状態に戻る
                breaker.state = "OPEN"
                logger.warning(f"⚠️ [RESILIENCE] Circuit breaker REOPENED: {component}")

    def is_circuit_open(self, component: str) -> bool:
        """サーキットブレーカーがOPEN状態かチェック"""
        if component not in self.circuit_breakers:
            return False

        breaker = self.circuit_breakers[component]
        current_time = datetime.now()

        if breaker.state == "OPEN":
            # リカバリタイムアウト後はHALF_OPEN状態に
            if (
                breaker.last_failure_time
                and current_time - breaker.last_failure_time
                > timedelta(seconds=breaker.recovery_timeout)
            ):
                breaker.state = "HALF_OPEN"
                logger.info(f"🔄 [RESILIENCE] Circuit breaker HALF_OPEN: {component}")
                return False
            return True

        return False

    def can_proceed(self, component: str) -> bool:
        """コンポーネントが実行可能かチェック"""
        if self.emergency_stop:
            return False
        return not self.is_circuit_open(component)

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """エラーサマリー取得"""
        with self.lock:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_errors = [e for e in self.error_history if e.timestamp > cutoff_time]

            summary = {
                "total_errors": len(recent_errors),
                "critical_errors": len(
                    [e for e in recent_errors if e.severity == "CRITICAL"]
                ),
                "warning_errors": len(
                    [e for e in recent_errors if e.severity == "WARNING"]
                ),
                "error_by_component": {},
                "error_by_type": {},
                "circuit_breaker_states": {},
                "emergency_stop": self.emergency_stop,
                "critical_error_count": self.critical_error_count,
            }

            # コンポーネント別エラー集計
            for error in recent_errors:
                comp = error.component
                summary["error_by_component"][comp] = (
                    summary["error_by_component"].get(comp, 0) + 1
                )

                err_type = error.error_type
                summary["error_by_type"][err_type] = (
                    summary["error_by_type"].get(err_type, 0) + 1
                )

            # サーキットブレーカー状態
            for component, breaker in self.circuit_breakers.items():
                summary["circuit_breaker_states"][component] = {
                    "state": breaker.state,
                    "failure_count": breaker.failure_count,
                    "last_failure": (
                        breaker.last_failure_time.isoformat()
                        if breaker.last_failure_time
                        else None
                    ),
                }

            return summary

    def force_recovery(self, component: str) -> bool:
        """強制リカバリ"""
        with self.lock:
            if component in self.circuit_breakers:
                self.circuit_breakers[component].reset()
                logger.info(f"🔄 [RESILIENCE] Forced recovery for: {component}")
                return True
            return False

    def reset_emergency_stop(self) -> None:
        """緊急停止リセット"""
        with self.lock:
            self.emergency_stop = False
            self.critical_error_count = 0
            logger.info("🔄 [RESILIENCE] Emergency stop RESET")

    def with_error_handling(self, component: str, operation_name: str):
        """エラーハンドリング付きデコレーター"""

        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                if not self.can_proceed(component):
                    raise RuntimeError(f"Circuit breaker open for {component}")

                try:
                    result = func(*args, **kwargs)
                    self.record_success(component)
                    return result
                except Exception as e:
                    self.record_error(
                        component=component,
                        error_type=type(e).__name__,
                        error_message=str(e),
                        severity=(
                            "CRITICAL"
                            if isinstance(e, (ConnectionError, TimeoutError))
                            else "WARNING"
                        ),
                    )
                    raise

            return wrapper

        return decorator


# グローバルインスタンス
_global_resilience_manager: Optional[ErrorResilienceManager] = None


def get_resilience_manager() -> ErrorResilienceManager:
    """グローバルレジリエンスマネージャー取得"""
    global _global_resilience_manager
    if _global_resilience_manager is None:
        _global_resilience_manager = ErrorResilienceManager()
    return _global_resilience_manager


def with_resilience(component: str, operation_name: str = ""):
    """レジリエンス付きデコレーター"""
    manager = get_resilience_manager()
    return manager.with_error_handling(component, operation_name)


# 使用例
class ResilientDataFetcher:
    """レジリエント付きデータフェッチャー"""

    def __init__(self, base_fetcher):
        self.base_fetcher = base_fetcher
        self.resilience = get_resilience_manager()

    @with_resilience("data_fetcher", "fetch_price_data")
    def fetch_price_data(self, *args, **kwargs):
        """レジリエント付きデータ取得"""
        return self.base_fetcher.get_price_df(*args, **kwargs)

    @with_resilience("data_fetcher", "fetch_balance")
    def fetch_balance(self, *args, **kwargs):
        """レジリエント付き残高取得"""
        return self.base_fetcher.fetch_balance(*args, **kwargs)


def get_system_health_status() -> Dict[str, Any]:
    """システムヘルス状態取得"""
    manager = get_resilience_manager()

    summary = manager.get_error_summary(hours=1)  # 過去1時間

    health_status = {
        "overall_health": "HEALTHY",
        "emergency_stop": summary["emergency_stop"],
        "error_summary": summary,
        "recommendations": [],
    }

    # ヘルス判定
    if summary["emergency_stop"]:
        health_status["overall_health"] = "CRITICAL"
        health_status["recommendations"].append("緊急停止中 - 手動リセットが必要")
    elif summary["critical_errors"] > 0:
        health_status["overall_health"] = "WARNING"
        health_status["recommendations"].append("CRITICAL エラーあり - 調査が必要")
    elif summary["total_errors"] > 10:
        health_status["overall_health"] = "WARNING"
        health_status["recommendations"].append("エラー多発 - システム監視強化推奨")

    # サーキットブレーカー確認
    open_breakers = [
        comp
        for comp, state in summary["circuit_breaker_states"].items()
        if state["state"] == "OPEN"
    ]
    if open_breakers:
        health_status["overall_health"] = "WARNING"
        health_status["recommendations"].append(
            f"サーキットブレーカーOPEN: {', '.join(open_breakers)}"
        )

    return health_status
