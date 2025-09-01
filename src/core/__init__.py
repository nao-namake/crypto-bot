"""
core/ - 基盤システム

Phase 18完了: システム全体を支える核心的な基盤機能を提供するディレクトリです。
責任分離・コード最適化・保守性向上を実現した企業級個人向けAI自動取引システムの基盤を提供します。
"""

# 設定管理
from .config import (
    Config,
    ConfigManager,
    DataConfig,
    ExchangeConfig,
    LoggingConfig,
    MLConfig,
    RiskConfig,
    get_config,
    get_threshold,
    load_config,
    load_thresholds,
    reload_thresholds,
)

# 例外システム
from .exceptions import (
    ConfigError,
    CryptoBotError,
    DataFetchError,
    DataProcessingError,
    ErrorSeverity,
    ExchangeAPIError,
    FileIOError,
    HealthCheckError,
    ModelLoadError,
    ModelPredictionError,
    RiskManagementError,
    TradingError,
    get_error_severity,
)

# ログシステム
from .logger import (
    CryptoBotLogger,
    JSONFormatter,
    LogLevel,
    get_logger,
    setup_logging,
)

# 市場データ構造
from .market_data import (
    BasicMarketData,
    EnrichedMarketData,
    MarketDataBase,
    OHLCVRecord,
    create_market_data,
)

# 統合制御システム
from .orchestration import (
    MLServiceAdapter,
    TradingOrchestrator,
    create_trading_orchestrator,
)

# プロトコル定義
from .protocols import (
    DataServiceProtocol,
    ExecutionServiceProtocol,
    FeatureServiceProtocol,
    MLServiceProtocol,
    RiskServiceProtocol,
    StrategyServiceProtocol,
)

# Phase 18 エクスポート定義
__all__ = [
    # 設定管理
    "Config",
    "ConfigManager",
    "ExchangeConfig",
    "MLConfig",
    "RiskConfig",
    "DataConfig",
    "LoggingConfig",
    "get_config",
    "load_config",
    "get_threshold",
    "load_thresholds",
    "reload_thresholds",
    # ログシステム
    "CryptoBotLogger",
    "get_logger",
    "setup_logging",
    "LogLevel",
    "JSONFormatter",
    # 例外システム
    "CryptoBotError",
    "ConfigError",
    "DataFetchError",
    "DataProcessingError",
    "ExchangeAPIError",
    "TradingError",
    "RiskManagementError",
    "ModelLoadError",
    "ModelPredictionError",
    "FileIOError",
    "HealthCheckError",
    "ErrorSeverity",
    "get_error_severity",
    # 統合制御
    "TradingOrchestrator",
    "create_trading_orchestrator",
    "MLServiceAdapter",
    # プロトコル
    "DataServiceProtocol",
    "FeatureServiceProtocol",
    "StrategyServiceProtocol",
    "MLServiceProtocol",
    "RiskServiceProtocol",
    "ExecutionServiceProtocol",
    # 市場データ
    "OHLCVRecord",
    "MarketDataBase",
    "BasicMarketData",
    "EnrichedMarketData",
    "create_market_data",
]

# Phase 18完了メタ情報
__version__ = "18.0"
__author__ = "CryptoBot Phase 18 Refactoring"
__description__ = "統合基盤システム - 責任分離・最適化・保守性向上完成"
