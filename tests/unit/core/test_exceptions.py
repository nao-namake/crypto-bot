"""カスタム例外クラスのテスト."""

import pytest

from src.core.exceptions import (
    CryptoBotError,
    DataFetchError,
    DataProcessingError,
    ExchangeAPIError,
    FileIOError,
    HealthCheckError,
    ModelLoadError,
    ModelPredictionError,
    RiskManagementError,
    StrategyError,
    TradingError,
)


class TestCryptoBotError:
    """CryptoBotError基底クラスのテスト"""

    def test_basic_instantiation(self):
        """基本インスタンス化テスト"""
        error = CryptoBotError("test error")
        assert str(error) == "test error"
        assert error.message == "test error"
        assert error.error_code is None
        assert error.context == {}

    def test_with_error_code(self):
        """エラーコード付きインスタンス化テスト"""
        error = CryptoBotError("test error", error_code="E001")
        assert error.error_code == "E001"

    def test_with_context(self):
        """コンテキスト付きインスタンス化テスト"""
        context = {"key": "value", "count": 10}
        error = CryptoBotError("test error", context=context)
        assert error.context == context

    def test_to_dict(self):
        """to_dict()メソッドテスト"""
        error = CryptoBotError("test error", error_code="E001", context={"key": "value"})
        result = error.to_dict()
        assert result["error_type"] == "CryptoBotError"
        assert result["message"] == "test error"
        assert result["error_code"] == "E001"
        assert result["context"] == {"key": "value"}


class TestDerivedExceptions:
    """派生例外クラスのテスト"""

    def test_data_fetch_error(self):
        """DataFetchErrorテスト"""
        error = DataFetchError("fetch error")
        assert isinstance(error, CryptoBotError)
        assert error.to_dict()["error_type"] == "DataFetchError"

    def test_exchange_api_error(self):
        """ExchangeAPIErrorテスト"""
        error = ExchangeAPIError("api error", api_endpoint="/api/v1/test", status_code=500)
        assert isinstance(error, CryptoBotError)
        assert error.api_endpoint == "/api/v1/test"
        assert error.status_code == 500
        assert error.to_dict()["error_type"] == "ExchangeAPIError"

    def test_trading_error(self):
        """TradingErrorテスト"""
        error = TradingError("trading error", order_id="12345", symbol="BTC_JPY")
        assert isinstance(error, CryptoBotError)
        assert error.order_id == "12345"
        assert error.symbol == "BTC_JPY"
        assert error.to_dict()["error_type"] == "TradingError"

    def test_risk_management_error(self):
        """RiskManagementErrorテスト"""
        error = RiskManagementError("risk error", risk_level="HIGH", position_size=0.5)
        assert isinstance(error, CryptoBotError)
        assert error.risk_level == "HIGH"
        assert error.position_size == 0.5
        assert error.to_dict()["error_type"] == "RiskManagementError"

    def test_data_processing_error(self):
        """DataProcessingErrorテスト"""
        error = DataProcessingError(
            "processing error", data_type="ohlcv", processing_stage="validation"
        )
        assert isinstance(error, CryptoBotError)
        assert error.data_type == "ohlcv"
        assert error.processing_stage == "validation"
        assert error.to_dict()["error_type"] == "DataProcessingError"

    def test_model_load_error(self):
        """ModelLoadErrorテスト"""
        error = ModelLoadError("load error", model_name="ensemble_full")
        assert isinstance(error, CryptoBotError)
        assert error.model_name == "ensemble_full"
        assert error.to_dict()["error_type"] == "ModelLoadError"

    def test_model_prediction_error(self):
        """ModelPredictionErrorテスト"""
        error = ModelPredictionError("prediction error", model_name="lightgbm")
        assert isinstance(error, CryptoBotError)
        assert error.model_name == "lightgbm"
        assert error.to_dict()["error_type"] == "ModelPredictionError"

    def test_file_io_error(self):
        """FileIOErrorテスト"""
        error = FileIOError("io error", file_path="/tmp/test.csv", operation="read")
        assert isinstance(error, DataProcessingError)
        assert error.file_path == "/tmp/test.csv"
        assert error.operation == "read"
        assert error.to_dict()["error_type"] == "FileIOError"

    def test_health_check_error(self):
        """HealthCheckErrorテスト"""
        error = HealthCheckError("health error", service_name="database")
        assert isinstance(error, CryptoBotError)
        assert error.service_name == "database"
        assert error.to_dict()["error_type"] == "HealthCheckError"

    def test_strategy_error(self):
        """StrategyErrorテスト"""
        error = StrategyError("strategy error", strategy_name="ATRBased")
        assert isinstance(error, CryptoBotError)
        assert error.strategy_name == "ATRBased"
        assert error.to_dict()["error_type"] == "StrategyError"
