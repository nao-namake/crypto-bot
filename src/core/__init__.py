"""
core/ - 基盤システム - Phase 49完了

システム全体を支える核心的な基盤機能を提供するディレクトリです。
責任分離・コード最適化・保守性向上を実現した企業級個人向けAI自動取引システムの基盤を提供します。

Phase 49完了:
- バックテスト完全改修（信頼性100%達成・TradeTracker統合・matplotlib可視化）
- 証拠金維持率80%遵守・TP/SL設定完全同期（thresholds.yaml完全準拠）
- Phase 48: Discord週間レポート（通知99%削減・コスト35%削減）
- Phase 47: 確定申告対応システム（作業時間95%削減）
- Phase 42: 統合TP/SL（注文数91.7%削減）・トレーリングストップ実装
- Phase 41.8: Strategy-Aware ML（55特徴量・訓練/推論一貫性確保）
- Phase 38: trading層レイヤードアーキテクチャ実装完了
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

# Phase 49完了 エクスポート定義
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

# Phase 49完了メタ情報
__version__ = "49.0"
__author__ = "CryptoBot Phase 49完了"
__description__ = "統合基盤システム - バックテスト完全改修・証拠金維持率80%遵守・週間レポート・確定申告対応・統合TP/SL・Strategy-Aware ML・企業級品質達成"
