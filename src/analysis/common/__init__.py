"""Phase 87 Stage 3: 分析スクリプト共通ライブラリ

live/standard_analysis.py と backtest/standard_analysis.py の重複ロジックを集約。

エクスポート:
- detect_missing_sl: SL未設置検出（金額/件数ベース）
- detect_canceled_unfilled: GCPログから Phase 87 C1 CANCELED_UNFILLED 検出
- calculate_tp_sl_distances: TPSLCalculator 経由でTP/SL距離算出（Phase 86単一実装）
"""

from .canceled_unfilled_detector import (
    CanceledUnfilledEvent,
    detect_canceled_unfilled,
)
from .sl_validators import MissingSLResult, detect_missing_sl
from .tp_sl_helpers import calculate_tp_sl_distances

__all__ = [
    "MissingSLResult",
    "detect_missing_sl",
    "CanceledUnfilledEvent",
    "detect_canceled_unfilled",
    "calculate_tp_sl_distances",
]
