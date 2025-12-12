"""
カスタム例外クラス - Phase 49完了

エラーの種類を明確に分類し、適切なエラーハンドリングと
重要度ベースのログ出力を可能にします。

Phase 49完了:
- 11種類のカスタム例外クラス（CryptoBotError基底・10派生クラス）
- エラー重要度自動マッピング（LOW/MEDIUM/HIGH/CRITICAL）
- 構造化エラーコンテキスト（to_dict()メソッド）
Phase 28-29: 企業級品質の例外システム確立
Phase 22: スリム化・実使用例外のみ残存（DataQualityError・StrategyError追加）
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
    ) -> None:
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
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.api_endpoint = api_endpoint
        self.status_code = status_code
        self.context.update({"api_endpoint": api_endpoint, "status_code": status_code})


class TradingError(CryptoBotError):
    """取引実行エラー."""

    def __init__(
        self,
        message: str,
        order_id: Optional[str] = None,
        symbol: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.order_id = order_id
        self.symbol = symbol
        self.context.update({"order_id": order_id, "symbol": symbol})


class RiskManagementError(CryptoBotError):
    """リスク管理エラー."""

    def __init__(
        self,
        message: str,
        risk_level: Optional[str] = None,
        position_size: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.risk_level = risk_level
        self.position_size = position_size
        self.context.update({"risk_level": risk_level, "position_size": position_size})


class DataProcessingError(CryptoBotError):
    """データ処理エラー."""

    def __init__(
        self,
        message: str,
        data_type: Optional[str] = None,
        processing_stage: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.data_type = data_type
        self.processing_stage = processing_stage
        self.context.update({"data_type": data_type, "processing_stage": processing_stage})


# Phase 22スリム化後の例外定義: ML・API・ファイルI/O関連の具体的例外
class ModelLoadError(CryptoBotError):
    """モデルファイル読み込みエラー"""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.model_name = model_name
        self.context.update({"model_name": model_name})


class ModelPredictionError(CryptoBotError):
    """ML予測実行エラー"""

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.model_name = model_name
        self.context.update({"model_name": model_name})


class FileIOError(DataProcessingError):
    """ファイル入出力エラー"""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, data_type="file", **kwargs)
        self.file_path = file_path
        self.operation = operation
        self.context.update({"file_path": file_path, "operation": operation})


class HealthCheckError(CryptoBotError):
    """システムヘルスチェックエラー"""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.service_name = service_name
        self.context.update({"service_name": service_name})


class DataQualityError(DataProcessingError):
    """データ品質エラー（Phase 22 バックテスト用・CI/CD統合対応）."""

    def __init__(
        self,
        message: str,
        quality_check: Optional[str] = None,
        expected_value: Optional[Any] = None,
        actual_value: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
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


class StrategyError(CryptoBotError):
    """戦略システムエラー（Phase 22で必要性確認・再追加）."""

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.strategy_name = strategy_name
        self.context.update({"strategy_name": strategy_name})


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
    RiskManagementError: ErrorSeverity.HIGH,
    DataProcessingError: ErrorSeverity.MEDIUM,
    # Phase 22スリム化: 実際に使用されている例外のみ
    ModelLoadError: ErrorSeverity.HIGH,
    ModelPredictionError: ErrorSeverity.MEDIUM,
    FileIOError: ErrorSeverity.MEDIUM,
    HealthCheckError: ErrorSeverity.MEDIUM,
    DataQualityError: ErrorSeverity.MEDIUM,
    StrategyError: ErrorSeverity.HIGH,  # Phase 22で再追加・戦略システム重要度高
}


def get_error_severity(error: Exception) -> str:
    """例外の重要度を取得."""
    error_type = type(error)
    return ERROR_SEVERITY_MAP.get(error_type, ErrorSeverity.MEDIUM)
