"""
Trading Layer - Phase 52.4-B完了

5層レイヤードアーキテクチャによる統合取引管理層。
Phase 52.4-Bで設定管理統一・コード品質最適化完了。

主要コンポーネント:
- IntegratedRiskManager: 統合リスク管理API
- ExecutionService: 取引実行サービス
- KellyCriterion: Kelly基準ポジションサイジング
- DrawdownManager: ドローダウン管理・連続損失制御
- TradingAnomalyDetector: 取引実行用異常検知
- BalanceMonitor: 残高・保証金監視

Phase 52.4-B完了
"""

# 残高監視層
from .balance import BalanceMonitor

# 後方互換性のためのインポート
# コア層（列挙型・データクラス）
from .core import (
    DrawdownSnapshot,
    ExecutionMode,
    ExecutionResult,
    MarginData,
    MarginPrediction,
    MarginStatus,
    MarketCondition,
    OrderStatus,
    RiskDecision,
    RiskMetrics,
    TradeEvaluation,
    TradingSession,
)

# 実行層
from .execution import ExecutionService, OrderStrategy, StopManager

# ポジション管理層
from .position import CooldownManager, PositionCleanup, PositionLimits, PositionTracker

# リスク管理層
from .risk import (
    AnomalyAlert,
    AnomalyLevel,
    DrawdownManager,
    IntegratedRiskManager,
    KellyCalculationResult,
    KellyCriterion,
    PositionSizeIntegrator,
    TradeRecord,
    TradeResult,
    TradingAnomalyDetector,
    TradingStatus,
)

# パブリックAPI
__all__ = [
    # コア層
    "ExecutionMode",
    "ExecutionResult",
    "MarginData",
    "MarginPrediction",
    "MarginStatus",
    "OrderStatus",
    "RiskDecision",
    "TradeEvaluation",
    # 実行層
    "ExecutionService",
    "OrderStrategy",
    "StopManager",
    # ポジション管理層
    "PositionTracker",
    "PositionLimits",
    "PositionCleanup",
    "CooldownManager",
    # 残高監視層
    "BalanceMonitor",
    # リスク管理層
    "KellyCriterion",
    "PositionSizeIntegrator",
    "TradeResult",
    "KellyCalculationResult",
    "DrawdownManager",
    "TradeRecord",
    "TradingStatus",
    "TradingAnomalyDetector",
    "AnomalyAlert",
    "AnomalyLevel",
    # 後方互換性（廃止予定）
    "IntegratedRiskManager",
    "RiskMetrics",
    "DrawdownSnapshot",
    "TradingSession",
    "MarketCondition",
    # リスクプロファイル機能
    "RISK_PROFILES",
    "DEFAULT_RISK_CONFIG",
    "create_risk_manager",
    "get_risk_profile_config",
    "list_risk_profiles",
]

# バージョン情報
__version__ = "52.4"
__phase__ = "Phase 52.4-B完了"
__description__ = "5層レイヤードアーキテクチャによる統合取引管理層・設定管理統一・コード品質最適化"

# リスクプロファイル機能
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
            "min_trades_for_kelly": 5,
        },
        "risk_thresholds": {
            "min_ml_confidence": 0.30,
            "risk_threshold_deny": 0.8,
            "risk_threshold_conditional": 0.6,
        },
        "description": "バランス型リスク管理（標準）",
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
        "description": "積極的リスク管理",
    },
}

# デフォルト設定（バランス型プロファイル採用）
DEFAULT_RISK_CONFIG = {
    "kelly_criterion": {
        "max_position_ratio": 0.10,  # 最大10%
        "safety_factor": 0.7,  # Kelly値の70%使用
        "min_trades_for_kelly": 5,  # Kelly適用最小取引数
    },
    "drawdown_manager": {
        "max_drawdown_ratio": 0.20,  # 最大ドローダウン20%
        "consecutive_loss_limit": 5,  # 連続5損失で停止
        "cooldown_hours": 24,  # 24時間クールダウン
    },
    "anomaly_detector": {
        "spread_warning_threshold": 0.003,  # 0.3%スプレッド警告
        "spread_critical_threshold": 0.005,  # 0.5%スプレッド重大
        "api_latency_warning_ms": 2000,  # 2秒遅延警告
        "api_latency_critical_ms": 5000,  # 5秒遅延重大
        "price_spike_zscore_threshold": 3.0,  # 3σ価格スパイク
        "volume_spike_zscore_threshold": 3.0,  # 3σ出来高スパイク
    },
    "risk_thresholds": {
        "min_ml_confidence": 0.30,  # 最小ML信頼度30%
        "risk_threshold_deny": 0.8,  # 80%以上で拒否
        "risk_threshold_conditional": 0.6,  # 60%以上で条件付き
    },
}


def create_risk_manager(
    config: dict = None,
    initial_balance: float = None,
    risk_profile: str = "balanced",
    mode: str = "live",
    bitbank_client=None,
    execution_service=None,
) -> IntegratedRiskManager:
    """
    統合リスク管理器の作成

    Args:
        config: リスク管理設定。Noneの場合はプロファイル使用
        initial_balance: 初期残高（Noneの場合はmode_balancesから自動取得）
        risk_profile: リスクプロファイル ("conservative", "balanced", "aggressive")
        mode: 実行モード（paper/live/backtest）
        bitbank_client: Bitbank APIクライアント
        execution_service: ExecutionServiceインスタンス

    Returns:
        IntegratedRiskManager: 設定済みリスク管理器
    """
    if config is None:
        config = get_risk_profile_config(risk_profile)

    # initial_balanceがNoneの場合はmode_balancesから取得
    if initial_balance is None:
        from ..core.config import load_config

        unified_config = load_config("config/core/unified.yaml")
        mode_balances = getattr(unified_config, "mode_balances", {})
        mode_balance_config = mode_balances.get(mode, {})
        initial_balance = mode_balance_config.get("initial_balance", 10000.0)

    return IntegratedRiskManager(
        config=config,
        initial_balance=initial_balance,
        enable_discord_notifications=True,
        mode=mode,
        bitbank_client=bitbank_client,
        execution_service=execution_service,
    )


def get_risk_profile_config(profile_name: str = "balanced") -> dict:
    """
    リスクプロファイル設定を取得

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

    # デフォルト設定をベースに、プロファイル設定で上書き（深いコピーで元の設定を保護）
    config = {
        "kelly_criterion": DEFAULT_RISK_CONFIG["kelly_criterion"].copy(),
        "drawdown_manager": DEFAULT_RISK_CONFIG["drawdown_manager"].copy(),
        "anomaly_detector": DEFAULT_RISK_CONFIG["anomaly_detector"].copy(),
        "risk_thresholds": DEFAULT_RISK_CONFIG["risk_thresholds"].copy(),
    }
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
