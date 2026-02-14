"""
Trading Core Types - Phase 64整理

取引関連データクラスの一元管理
※ TradeResult・KellyCalculationResult・AnomalyAlert等はrisk/に正本あり（Phase 64で重複削除）
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enums import (
    ExecutionMode,
    MarginStatus,
    OrderStatus,
    RiskDecision,
)

# === Risk Manager関連 ===


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
    adjusted_confidence: Optional[float] = None  # Phase 59.3: 調整済み信頼度（penalty/bonus適用後）

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


# === Phase 61.7: 固定金額TP用データクラス ===


@dataclass
class PositionFeeData:
    """
    Phase 61.7: ポジション手数料データ

    固定金額TP計算に使用するAPIから取得した手数料情報
    """

    unrealized_fee_amount: float = 0.0  # 未収手数料（エントリー時）
    unrealized_interest_amount: float = 0.0  # 未収利息
    average_price: float = 0.0  # 平均建値
    open_amount: float = 0.0  # 保有数量

    @classmethod
    def from_api_response(cls, raw_data: Dict[str, Any]) -> "PositionFeeData":
        """
        bitbank API raw_dataから生成

        Args:
            raw_data: bitbank APIレスポンスのraw_dataフィールド

        Returns:
            PositionFeeData: 手数料データ
        """
        return cls(
            unrealized_fee_amount=float(raw_data.get("unrealized_fee_amount", 0) or 0),
            unrealized_interest_amount=float(raw_data.get("unrealized_interest_amount", 0) or 0),
            average_price=float(raw_data.get("average_price", 0) or 0),
            open_amount=float(raw_data.get("open_amount", 0) or 0),
        )


__all__ = [
    # Risk Manager
    "TradeEvaluation",
    "ExecutionResult",
    "RiskMetrics",
    # Margin Monitor
    "MarginData",
    "MarginPrediction",
    # Phase 61.7: 固定金額TP
    "PositionFeeData",
]
