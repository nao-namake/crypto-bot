"""
core/ - 基盤システム - Phase 52.4完了

システム全体を支える核心的な基盤機能を提供するディレクトリです。
責任分離・コード最適化・保守性向上を実現した企業級個人向けAI自動取引システムの基盤を提供します。

Phase 52.4: コード品質改善・設定ファイル統合
- Phase参照統一（67%削減達成）・ハードコード値設定ファイル化
- logging設定完全外部化・設定一元化による保守性向上

Phase 49-51: バックテスト完全改修・動的戦略管理・証拠金維持率80%遵守
Phase 48-47: Discord週間レポート（通知99%削減）・確定申告対応システム
Phase 42-38: 統合TP/SL・Strategy-Aware ML・レイヤードアーキテクチャ
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

# Phase 52.4 エクスポート定義
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

# Phase 52.4 メタ情報
__version__ = "52.4"
__author__ = "CryptoBot Phase 52.4"
__description__ = "統合基盤システム - コード品質改善・設定ファイル統合・Phase参照67%削減・logging設定外部化・保守性向上"
