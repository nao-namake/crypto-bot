"""
core/ - 基盤システム - Phase 38.4完了版

システム全体を支える核心的な基盤機能を提供するディレクトリです。
責任分離・コード最適化・保守性向上を実現した企業級個人向けAI自動取引システムの基盤を提供します。

Phase 28-29最適化:
- 基盤コンポーネントの配置最適化完了
- 横断的機能の適切な分離維持
- デプロイ前コードクリーンアップ完了

Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了
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

# Phase 38.4完了版 エクスポート定義
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

# Phase 38.4完了版メタ情報
__version__ = "38.4"
__author__ = "CryptoBot Phase 38.4完了版"
__description__ = "統合基盤システム - trading層レイヤードアーキテクチャ完成・全モジュールPhase統一・コード品質保証完了"
