"""
設定クラス統合ファイル - Phase 22 ハードコード排除（ファイル数削減維持）

全ての設定dataclassを一元管理。以下の設定クラスを提供：
- ExchangeConfig: 取引所接続設定
- MLConfig: 機械学習設定
- RiskConfig: リスク管理設定
- DataConfig: データ取得設定
- LoggingConfig: ログ設定
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ExchangeConfig:
    """取引所接続設定."""

    name: Optional[str] = None
    symbol: Optional[str] = None
    leverage: Optional[float] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    rate_limit_ms: Optional[int] = None
    timeout_ms: Optional[int] = None
    retries: Optional[int] = None
    ssl_verify: Optional[bool] = None
    api_version: Optional[str] = None


@dataclass
class MLConfig:
    """機械学習設定."""

    confidence_threshold: Optional[float] = None
    ensemble_enabled: Optional[bool] = None
    models: Optional[List[str]] = None
    model_weights: Optional[List[float]] = None
    model_path: Optional[str] = None
    model_update_check: Optional[bool] = None
    fallback_enabled: Optional[bool] = None
    prediction: Optional[Dict[str, Any]] = None

    # thresholds.yaml mlセクション対応フィールド
    default_confidence: Optional[float] = None
    prediction_fallback_confidence: Optional[float] = None
    emergency_stop_on_dummy: Optional[bool] = None
    allow_dummy_fallback: Optional[bool] = None
    max_model_failures: Optional[int] = None
    dummy_confidence: Optional[float] = None
    model_paths: Optional[Dict[str, Any]] = None
    dynamic_confidence: Optional[Dict[str, Any]] = None


@dataclass
class RiskConfig:
    """リスク管理設定."""

    risk_per_trade: Optional[float] = None
    kelly_max_fraction: Optional[float] = None
    max_drawdown: Optional[float] = None
    stop_loss_atr_multiplier: Optional[float] = None
    consecutive_loss_limit: Optional[int] = None
    take_profit_ratio: Optional[float] = None
    daily_loss_limit: Optional[float] = None
    weekly_loss_limit: Optional[float] = None
    emergency_stop_enabled: Optional[bool] = None
    kelly_criterion: Optional[Dict[str, Any]] = None
    drawdown_manager: Optional[Dict[str, Any]] = None
    anomaly_detector: Optional[Dict[str, Any]] = None
    risk_thresholds: Optional[Dict[str, float]] = None

    # thresholds.yaml riskセクション対応フィールド
    emergency_ratio: Optional[float] = None
    emergency_stop_ratio: Optional[float] = None
    fallback_max_ratio: Optional[float] = None
    fallback_min_ratio: Optional[float] = None
    fallback_stop_ratio: Optional[float] = None
    kelly_lookback_days: Optional[int] = None
    recent_lookback_hours: Optional[int] = None
    safe_balance_ratio: Optional[float] = None


@dataclass
class DataConfig:
    """データ取得設定."""

    timeframes: Optional[List[str]] = None
    since_hours: Optional[int] = None
    limit: Optional[int] = None
    cache_enabled: Optional[bool] = None
    cache: Optional[Dict[str, Any]] = None

    # thresholds.yaml dataセクション対応フィールド
    fetch_limits: Optional[Dict[str, int]] = None
    min_data_points: Optional[int] = None
    max_missing_ratio: Optional[float] = None


@dataclass
class LoggingConfig:
    """ログ設定."""

    level: Optional[str] = None
    file_enabled: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    retention_days: Optional[int] = None
    file: Optional[Dict[str, Any]] = None
    discord: Optional[Dict[str, Any]] = None
