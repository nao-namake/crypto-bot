"""
Performance Analysis Module - Phase 16.2-C Integration

パフォーマンス分析モジュール - コスト分析・ROI測定・レポート生成

統合前: analytics/bitbank_interest_avoidance_analyzer.py
統合後: analysis/performance/ サブディレクトリ

機能:
- 金利コスト分析・回避効果測定
- パフォーマンス分析・統計レポート生成
- ROI改善測定・取引所別コスト比較
- 詳細レポート・可視化グラフ生成

Phase 16.2-C実装日: 2025年8月8日
"""

from .bitbank_interest_avoidance_analyzer import (
    BitbankInterestAvoidanceAnalyzer,
    ComparisonPeriod,
    InterestCalculationMethod,
    InterestSavingRecord,
)

__all__ = [
    "BitbankInterestAvoidanceAnalyzer",
    "InterestCalculationMethod",
    "ComparisonPeriod",
    "InterestSavingRecord",
]

__version__ = "16.2.0"
__author__ = "Phase 16.2-C Integration"
__description__ = "Performance Analysis Integration Module"
