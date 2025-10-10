"""
Trading Core Enums - Phase 38リファクタリング

すべての取引関連列挙型の一元管理
"""

from enum import Enum


# === Risk Manager関連 ===


class RiskDecision(Enum):
    """リスク判定結果."""

    APPROVED = "approved"
    DENIED = "denied"
    CONDITIONAL = "conditional"


class ExecutionMode(Enum):
    """実行モード."""

    PAPER = "paper"  # ペーパートレード
    LIVE = "live"  # 実取引


class OrderStatus(Enum):
    """注文状態."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REJECTED = "rejected"  # ポジション管理制限により拒否


# === Risk Monitor関連 ===


class AnomalyLevel(Enum):
    """異常レベル."""

    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class TradingStatus(Enum):
    """取引状態."""

    ACTIVE = "active"
    PAUSED_DRAWDOWN = "paused_drawdown"
    PAUSED_CONSECUTIVE_LOSS = "paused_consecutive_loss"
    PAUSED_MANUAL = "paused_manual"


# === Margin Monitor関連 ===


class MarginStatus(Enum):
    """保証金維持率の状態."""

    SAFE = "safe"  # 200%以上 - 安全
    CAUTION = "caution"  # 150-200% - 注意
    WARNING = "warning"  # 100-150% - 警告
    CRITICAL = "critical"  # 100%未満 - 危険（追証発生レベル）


__all__ = [
    "RiskDecision",
    "ExecutionMode",
    "OrderStatus",
    "AnomalyLevel",
    "TradingStatus",
    "MarginStatus",
]
