"""カスタム例外クラス - CryptoBotError基底・9派生クラス."""

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


class ModelLoadError(CryptoBotError):
    """モデルファイル読み込みエラー."""

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
    """ML予測実行エラー."""

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
    """ファイル入出力エラー."""

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
    """システムヘルスチェックエラー."""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.service_name = service_name
        self.context.update({"service_name": service_name})


class StrategyError(CryptoBotError):
    """戦略システムエラー."""

    def __init__(
        self,
        message: str,
        strategy_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.strategy_name = strategy_name
        self.context.update({"strategy_name": strategy_name})


class PostOnlyCancelledException(TradingError):
    """post_only注文が即時約定回避のためキャンセルされた例外."""

    def __init__(
        self,
        message: str,
        price: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.price = price
        self.context.update({"price": price})
