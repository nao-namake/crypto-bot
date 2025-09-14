"""
core/ - 基盤システム

Phase 22完了: システム全体を支える核心的な基盤機能を提供するディレクトリです。
責任分離・コード最適化・保守性向上を実現した企業級個人向けAI自動取引システムの基盤を提供します。

Phase 22最適化:
- 未使用ファイル削除（market_data.py）
- 例外クラススリム化（未使用例外削除）
- プロトコル再配置（protocols.py → orchestration/）
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
    StrategyError,
    TradingError,
    get_error_severity,
)

# ログシステム
from .logger import CryptoBotLogger, JSONFormatter, LogLevel, get_logger, setup_logging

# 統合制御システム
from .orchestration import MLServiceAdapter, TradingOrchestrator, create_trading_orchestrator

# Phase 22 エクスポート定義
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
    "StrategyError",
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
]

# Phase 22完了メタ情報
__version__ = "22.0"
__author__ = "CryptoBot Phase 22 Core Optimization"
__description__ = "統合基盤システム - 未使用コード削除・構造最適化・保守性向上完成"
