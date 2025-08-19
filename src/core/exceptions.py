"""
カスタム例外クラス - エラーの種類を明確に分類

レガシーシステムの散在していた例外処理を統一し、
適切なエラーハンドリングとログ出力を可能にします。.
"""

from typing import Any, Dict, Optional


class CryptoBotError(Exception):
    """
    暗号資産取引Bot基底例外クラス

    すべてのBot固有の例外はこのクラスを継承する.
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """例外情報を辞書形式で返す（ログ・通知用）."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }


class ConfigError(CryptoBotError):
    """設定関連エラー."""

    pass


class DataFetchError(CryptoBotError):
    """データ取得エラー."""

    pass


class ExchangeAPIError(CryptoBotError):
    """取引所API関連エラー."""

    def __init__(
        self,
        message: str,
        api_endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.api_endpoint = api_endpoint
        self.status_code = status_code
        self.context.update(
            {"api_endpoint": api_endpoint, "status_code": status_code}
        )


class TradingError(CryptoBotError):
    """取引実行エラー."""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.order_id = order_id
        self.symbol = symbol
        self.context.update({"order_id": order_id, "symbol": symbol})


class MLModelError(CryptoBotError):
    """機械学習モデルエラー."""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        feature_count: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.model_name = model_name
        self.feature_count = feature_count
        self.context.update(
            {"model_name": model_name, "feature_count": feature_count}
        )


class RiskManagementError(CryptoBotError):
    """リスク管理エラー."""

    def __init__(
        self,
        message: str,
        risk_level: Optional[str] = None,
        position_size: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.risk_level = risk_level
        self.position_size = position_size
        self.context.update(
            {"risk_level": risk_level, "position_size": position_size}
        )


class StrategyError(CryptoBotError):
    """戦略実行エラー."""

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        confidence: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.strategy_name = strategy_name
        self.confidence = confidence
        self.context.update(
            {"strategy_name": strategy_name, "confidence": confidence}
        )


class NotificationError(CryptoBotError):
    """通知システムエラー."""

    def __init__(
        self, message: str, notification_type: Optional[str] = None, **kwargs
    ):
        super().__init__(message, **kwargs)
        self.notification_type = notification_type
        self.context.update({"notification_type": notification_type})


# 緊急停止が必要なクリティカルエラー
class CriticalError(CryptoBotError):
    """
    緊急停止が必要なクリティカルエラー

    このエラーが発生した場合は、取引を即座に停止し、
    管理者への緊急通知を行う必要がある.
    """

    pass


class InsufficientFundsError(TradingError):
    """資金不足エラー."""

    pass


class ConnectionError(ExchangeAPIError):
    """接続エラー."""

    pass


class RateLimitError(ExchangeAPIError):
    """レート制限エラー."""

    pass


class ValidationError(CryptoBotError):
    """入力値検証エラー."""

    pass


class DataProcessingError(CryptoBotError):
    """データ処理エラー."""

    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        processing_stage: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.data_type = data_type
        self.processing_stage = processing_stage
        self.context.update(
            {"data_type": data_type, "processing_stage": processing_stage}
        )


class DataQualityError(DataProcessingError):
    """データ品質エラー（Phase 11 バックテスト用・CI/CD統合対応）."""

    def __init__(
        self,
        message: str,
        quality_check: Optional[str] = None,
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
        **kwargs,
    ):
        super().__init__(message, data_type="quality_check", **kwargs)
        self.quality_check = quality_check
        self.expected_value = expected_value
        self.actual_value = actual_value
        self.context.update(
            {
                "quality_check": quality_check,
                "expected_value": expected_value,
                "actual_value": actual_value,
            }
        )


# エラー重要度レベル
class ErrorSeverity:
    """エラー重要度定義."""

    LOW = "low"  # 軽微なエラー（ログのみ）
    MEDIUM = "medium"  # 注意が必要（Warning通知）
    HIGH = "high"  # 重要なエラー（Error通知）
    CRITICAL = "critical"  # 緊急対応必要（Critical通知）


# エラーと重要度のマッピング
ERROR_SEVERITY_MAP = {
    ConfigError: ErrorSeverity.HIGH,
    DataFetchError: ErrorSeverity.MEDIUM,
    ExchangeAPIError: ErrorSeverity.MEDIUM,
    TradingError: ErrorSeverity.HIGH,
    MLModelError: ErrorSeverity.MEDIUM,
    RiskManagementError: ErrorSeverity.HIGH,
    StrategyError: ErrorSeverity.MEDIUM,
    NotificationError: ErrorSeverity.LOW,
    CriticalError: ErrorSeverity.CRITICAL,
    InsufficientFundsError: ErrorSeverity.HIGH,
    ConnectionError: ErrorSeverity.MEDIUM,
    RateLimitError: ErrorSeverity.LOW,
    ValidationError: ErrorSeverity.LOW,
    DataProcessingError: ErrorSeverity.MEDIUM,
}


def get_error_severity(error: Exception) -> str:
    """例外の重要度を取得."""
    error_type = type(error)
    return ERROR_SEVERITY_MAP.get(error_type, ErrorSeverity.MEDIUM)
