"""
税務関連モジュール - Phase 49完了時点

確定申告対応システム（Phase 47実装・Phase 49完了時点）:
- TradeHistoryRecorder: 取引履歴記録（SQLite・267件記録中）
- PnLCalculator: 損益計算エンジン（移動平均法・国税庁準拠）
"""

from .pnl_calculator import PnLCalculator
from .trade_history_recorder import TradeHistoryRecorder

__all__ = ["TradeHistoryRecorder", "PnLCalculator"]
