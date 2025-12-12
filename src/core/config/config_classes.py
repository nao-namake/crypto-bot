"""
設定クラス統合ファイル - Phase 49完了

全ての設定dataclassを一元管理。以下の5設定クラスを提供：
- ExchangeConfig: 取引所接続設定（bitbank API・レート制限・タイムアウト）
- MLConfig: 機械学習設定（アンサンブル・信頼度閾値・フォールバック）
- RiskConfig: リスク管理設定（Kelly基準・ドローダウン制限・ポジション上限）
- DataConfig: データ取得設定（時間足・キャッシュ・履歴期間）
- LoggingConfig: ログ設定（レベル・ファイル出力・保持期間）

Phase 49完了: 5設定クラス統合・dataclass型安全設計・Optional対応
Phase 28-29: 設定クラス統合・dataclass設計確立
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
    ensemble_weights: Optional[Dict[str, float]] = None  # Phase 51.9-5: ensemble重み設定統合
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

    # Phase 29.5: ML予測統合設定
    strategy_integration: Optional[Dict[str, Any]] = None

    # Phase 45: Meta-Learning動的重み最適化設定
    meta_learning: Optional[Dict[str, Any]] = None

    # Phase 51.9: レジーム別ML統合設定
    regime_ml_integration: Optional[Dict[str, Any]] = None

    # Meta-ML予測信頼度閾値
    min_confidence: Optional[float] = None

    # 市場状況特徴量設定
    market_features: Optional[Dict[str, Any]] = None

    # パフォーマンストラッキング設定
    performance_tracking: Optional[Dict[str, Any]] = None

    # Meta-MLモデル設定
    model_config: Optional[Dict[str, Any]] = None


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

    # Phase 51.5-C: TP/SL再計算フォールバック設定
    fallback_atr: Optional[float] = None  # ATR取得失敗時のフォールバックATR値
    require_tpsl_recalculation: Optional[bool] = None  # TP/SL再計算必須化

    # Phase 24: ポジション管理・残高利用率制限フィールド
    max_capital_usage: Optional[float] = None
    reserve_ratio: Optional[float] = None
    min_account_balance: Optional[float] = None  # 最小運用資金要件（5万円未満取引停止）

    # Phase 25: 動的ポジションサイジング設定
    min_trade_size: Optional[float] = None
    dynamic_position_sizing: Optional[Dict[str, Any]] = None
    account_size_adjustments: Optional[Dict[str, Any]] = None


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
