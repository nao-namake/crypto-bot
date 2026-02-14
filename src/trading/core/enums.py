"""
Trading Core Enums - Phase 64整理

取引関連列挙型の一元管理
※ AnomalyLevel・TradingStatusはrisk/に正本あり（Phase 64で重複削除）
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
    "MarginStatus",
]
