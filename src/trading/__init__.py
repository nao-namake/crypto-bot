"""
Trading Layer - Phase 6リスク管理層

統合リスク管理システム・Kelly基準ポジションサイジング・
ドローダウン管理・異常検知の包括的取引制御機能。

主要コンポーネント:
- IntegratedRiskManager: 統合リスク管理API
- KellyCriterion: Kelly基準ポジションサイジング
- DrawdownManager: ドローダウン管理・連続損失制御
- TradingAnomalyDetector: 取引実行用異常検知

Phase 11完了: 2025年8月18日.
"""

# 異常検知
from .anomaly_detector import (
    AnomalyAlert,
    AnomalyLevel,
    MarketCondition,
    TradingAnomalyDetector,
)

# ドローダウン管理
from .drawdown_manager import (
    DrawdownManager,
    DrawdownSnapshot,
    TradingSession,
    TradingStatus,
)

# Kelly基準ポジションサイジング
from .position_sizing import (
    KellyCalculationResult,
    KellyCriterion,
    PositionSizeIntegrator,
    TradeResult,
)

# 統合API
from .risk import (
    IntegratedRiskManager,
    RiskDecision,
    RiskMetrics,
    TradeEvaluation,
)

# パブリックAPI
__all__ = [
    # 統合API
    "IntegratedRiskManager",
    "TradeEvaluation",
    "RiskMetrics",
    "RiskDecision",
    # Kelly基準
    "KellyCriterion",
    "PositionSizeIntegrator",
    "TradeResult",
    "KellyCalculationResult",
    # ドローダウン管理
    "DrawdownManager",
    "DrawdownSnapshot",
    "TradingSession",
    "TradingStatus",
    # 異常検知
    "TradingAnomalyDetector",
    "AnomalyAlert",
    "AnomalyLevel",
    "MarketCondition",
    # Phase 7拡張: リスクプロファイル機能
    "RISK_PROFILES",
    "DEFAULT_RISK_CONFIG",
    "create_risk_manager",
    "get_risk_profile_config",
    "list_risk_profiles",
]

# バージョン情報
__version__ = "11.0.0"
__phase__ = "Phase 11"
__description__ = "統合リスク管理層 + 実行層（段階的リスクプロファイル機能拡張・CI/CD統合・24時間監視・段階的デプロイ対応）"

# Phase 11拡張: 段階的リスクプロファイル機能（レガシーAggressiveRiskManager参考・CI/CD統合・24時間監視・段階的デプロイ対応）
RISK_PROFILES = {
    "conservative": {
        "kelly_criterion": {
            "max_position_ratio": 0.05,
            "safety_factor": 0.5,
            "min_trades_for_kelly": 30,
        },
        "risk_thresholds": {
            "min_ml_confidence": 0.35,
            "risk_threshold_deny": 0.7,
            "risk_threshold_conditional": 0.5,
        },
        "description": "保守的リスク管理（初期運用推奨）",
    },
    "balanced": {
        "kelly_criterion": {
            "max_position_ratio": 0.10,
            "safety_factor": 0.7,
            "min_trades_for_kelly": 20,
        },
        "risk_thresholds": {
            "min_ml_confidence": 0.30,
            "risk_threshold_deny": 0.8,
            "risk_threshold_conditional": 0.6,
        },
        "description": "バランス型リスク管理（標準・Phase 11デフォルト・CI/CD統合・24時間監視対応）",
    },
    "aggressive": {
        "kelly_criterion": {
            "max_position_ratio": 0.20,
            "safety_factor": 0.8,
            "min_trades_for_kelly": 15,
        },
        "risk_thresholds": {
            "min_ml_confidence": 0.25,
            "risk_threshold_deny": 0.85,
            "risk_threshold_conditional": 0.65,
        },
        "description": "積極的リスク管理（レガシーAggressiveRiskManager継承）",
    },
}

# より実践的なデフォルト設定（Phase 11バランス型プロファイル採用・CI/CD統合・24時間監視・段階的デプロイ対応）
DEFAULT_RISK_CONFIG = {
    "kelly_criterion": {
        "max_position_ratio": 0.10,  # 最大10%（5%→10%・Phase 11バランス調整・24時間監視対応）
        "safety_factor": 0.7,  # Kelly値の70%使用（60%→70%・効率向上）
        "min_trades_for_kelly": 20,  # Kelly適用最小取引数
    },
    "drawdown_manager": {
        "max_drawdown_ratio": 0.20,  # 最大ドローダウン20%
        "consecutive_loss_limit": 5,  # 連続5損失で停止
        "cooldown_hours": 24,  # 24時間クールダウン
    },
    "anomaly_detector": {
        "spread_warning_threshold": 0.003,  # 0.3%スプレッド警告
        "spread_critical_threshold": 0.005,  # 0.5%スプレッド重大
        "api_latency_warning_ms": 1000,  # 1秒遅延警告
        "api_latency_critical_ms": 3000,  # 3秒遅延重大
        "price_spike_zscore_threshold": 3.0,  # 3σ価格スパイク
        "volume_spike_zscore_threshold": 3.0,  # 3σ出来高スパイク
    },
    "risk_thresholds": {
        "min_ml_confidence": 0.30,  # 最小ML信頼度30%（35%→30%・Phase 11調整・CI/CD統合）
        "risk_threshold_deny": 0.8,  # 80%以上で拒否
        "risk_threshold_conditional": 0.6,  # 60%以上で条件付き
    },
}


def create_risk_manager(
    config: dict = None,
    initial_balance: float = 1000000,
    risk_profile: str = "balanced",
) -> IntegratedRiskManager:
    """
    統合リスク管理器の作成（Phase 11拡張: リスクプロファイル対応・CI/CD統合・24時間監視・段階的デプロイ対応）

    Args:
        config: リスク管理設定。Noneの場合はプロファイル使用
        initial_balance: 初期残高
        risk_profile: リスクプロファイル ("conservative", "balanced", "aggressive")

    Returns:
        IntegratedRiskManager: 設定済みリスク管理器
    """
    if config is None:
        config = get_risk_profile_config(risk_profile)

    return IntegratedRiskManager(
        config=config,
        initial_balance=initial_balance,
        enable_discord_notifications=True,
    )


def get_risk_profile_config(profile_name: str = "balanced") -> dict:
    """
    リスクプロファイル設定を取得（Phase 11新機能・CI/CD統合・24時間監視・段階的デプロイ対応）

    Args:
        profile_name: プロファイル名 ("conservative", "balanced", "aggressive")

    Returns:
        dict: 完全なリスク管理設定

    Raises:
        ValueError: 無効なプロファイル名
    """
    if profile_name not in RISK_PROFILES:
        raise ValueError(
            f"無効なリスクプロファイル: {profile_name}. " f"利用可能: {list(RISK_PROFILES.keys())}"
        )

    # デフォルト設定をベースに、プロファイル設定で上書き
    config = DEFAULT_RISK_CONFIG.copy()
    profile_config = RISK_PROFILES[profile_name]

    # Kelly基準設定を上書き
    if "kelly_criterion" in profile_config:
        config["kelly_criterion"].update(profile_config["kelly_criterion"])

    # リスク閾値設定を上書き
    if "risk_thresholds" in profile_config:
        config["risk_thresholds"].update(profile_config["risk_thresholds"])

    return config


def list_risk_profiles() -> dict:
    """
    利用可能なリスクプロファイル一覧を取得

    Returns:
        dict: プロファイル名: 説明 の辞書.
    """
    return {name: profile["description"] for name, profile in RISK_PROFILES.items()}
