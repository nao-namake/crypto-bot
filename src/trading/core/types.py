"""
Trading Core Types - Phase 49完了

すべての取引関連データクラスの一元管理
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import (
    AnomalyLevel,
    ExecutionMode,
    MarginStatus,
    OrderStatus,
    RiskDecision,
    TradingStatus,
)

# === Risk Manager関連 ===


@dataclass
class TradeResult:
    """取引結果記録用データクラス."""

    timestamp: datetime
    profit_loss: float
    is_win: bool
    strategy: str
    confidence: float


@dataclass
class KellyCalculationResult:
    """Kelly計算結果格納用データクラス."""

    kelly_fraction: float
    win_rate: float
    avg_win_loss_ratio: float
    safety_adjusted_fraction: float
    recommended_position_size: float
    sample_size: int
    confidence_level: float


@dataclass
class TradeEvaluation:
    """取引評価結果."""

    decision: RiskDecision
    side: str  # "buy" or "sell"
    risk_score: float  # 0.0-1.0, 高いほど危険
    position_size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence_level: float
    warnings: List[str]
    denial_reasons: List[str]
    evaluation_timestamp: datetime
    kelly_recommendation: float
    drawdown_status: str
    anomaly_alerts: List[str]
    market_conditions: Dict[str, Any]

    # Phase 35.3: オプションフィールド（デフォルト値あり）
    entry_price: Optional[float] = None  # バックテスト用エントリー価格
    strategy_name: str = "unknown"  # Phase 57.12: 戦略名記録
    ml_prediction: Optional[int] = None  # Phase 57.12: ML予測クラス（0=SELL, 1=HOLD, 2=BUY）
    ml_confidence: Optional[float] = None  # Phase 57.12: ML信頼度

    # 後方互換性のためのactionプロパティ（Silent Failure修正）
    @property
    def action(self) -> str:
        """後方互換性のため、sideフィールドをactionとしてもアクセス可能にする"""
        return self.side


@dataclass
class ExecutionResult:
    """注文実行結果."""

    success: bool
    mode: ExecutionMode  # 実行モード
    order_id: Optional[str] = None
    side: Optional[str] = None
    amount: Optional[float] = None
    price: Optional[float] = None
    filled_amount: Optional[float] = None
    filled_price: Optional[float] = None
    fee: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = None
    error_message: Optional[str] = None
    # ペーパートレード用追加情報
    paper_balance_before: Optional[float] = None
    paper_balance_after: Optional[float] = None
    paper_pnl: Optional[float] = None
    # レイテンシー監視・デバッグ情報
    execution_time_ms: Optional[float] = None
    notes: Optional[str] = None
    # 緊急決済関連フィールド（急変時例外処理）
    emergency_exit: Optional[bool] = None
    emergency_reason: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class RiskMetrics:
    """リスク指標."""

    current_drawdown: float
    consecutive_losses: int
    kelly_fraction: float
    anomaly_count_24h: int
    trading_status: str
    last_evaluation: datetime
    total_evaluations: int
    approved_trades: int
    denied_trades: int


# === Risk Monitor関連 ===


@dataclass
class AnomalyAlert:
    """異常アラート."""

    timestamp: datetime
    anomaly_type: str
    level: AnomalyLevel
    value: float
    threshold: float
    message: str
    should_pause_trading: bool


@dataclass
class MarketCondition:
    """市場状況記録."""

    timestamp: datetime
    bid: float
    ask: float
    last_price: float
    volume: float
    spread_pct: float
    api_latency_ms: float


@dataclass
class DrawdownSnapshot:
    """ドローダウン記録用スナップショット."""

    timestamp: datetime
    current_balance: float
    peak_balance: float
    drawdown_ratio: float
    consecutive_losses: int
    status: TradingStatus


@dataclass
class TradingSession:
    """取引セッション記録."""

    start_time: datetime
    end_time: Optional[datetime]
    reason: str
    initial_balance: float
    final_balance: Optional[float]
    total_trades: int
    profitable_trades: int


# === Margin Monitor関連 ===


@dataclass
class MarginData:
    """保証金関連データ."""

    current_balance: float  # 現在の口座残高（JPY）
    position_value_jpy: float  # 建玉総額（JPY換算）
    margin_ratio: float  # 保証金維持率（%）
    status: MarginStatus  # 状態
    message: str  # 状態メッセージ
    timestamp: datetime = None  # 計算時刻


@dataclass
class MarginPrediction:
    """新規ポジション追加後の維持率予測."""

    current_margin: MarginData  # 現在の維持率
    future_margin_ratio: float  # 予測維持率（%）
    future_status: MarginStatus  # 予測状態
    position_size_btc: float  # 追加するポジションサイズ（BTC）
    btc_price: float  # BTC価格（JPY）
    recommendation: str  # 推奨アクション


__all__ = [
    # Risk Manager
    "TradeResult",
    "KellyCalculationResult",
    "TradeEvaluation",
    "ExecutionResult",
    "RiskMetrics",
    # Risk Monitor
    "AnomalyAlert",
    "MarketCondition",
    "DrawdownSnapshot",
    "TradingSession",
    # Margin Monitor
    "MarginData",
    "MarginPrediction",
]
