"""
Unified Analysis System - Phase 16.2-C Integration

統合分析システム - analysis/ + analytics/ 統合

統合前 (2フォルダ - 2ファイル):
├── analysis/market_environment_analyzer.py - 市場分析・環境解析
└── analytics/bitbank_interest_avoidance_analyzer.py - パフォーマンス分析・レポート

統合後 (1フォルダ - 2サブディレクトリ):
├── market/market_environment_analyzer.py - 市場分析系
└── performance/bitbank_interest_avoidance_analyzer.py - パフォーマンス分析系

Usage:
    # 市場分析
    from crypto_bot.analysis.market import MarketEnvironmentAnalyzer

    # パフォーマンス分析
    from crypto_bot.analysis.performance import BitbankInterestAvoidanceAnalyzer

    # 統合インポート
    from crypto_bot.analysis import (
        MarketEnvironmentAnalyzer,
        BitbankInterestAvoidanceAnalyzer,
    )

Phase 16.2-C実装: 2025年8月8日
統合効果: 役割明確化・保守性向上・統合API提供
"""

# 市場分析系インポート
from .market import MarketEnvironmentAnalyzer

# パフォーマンス分析系インポート
from .performance import (
    BitbankInterestAvoidanceAnalyzer,
    ComparisonPeriod,
    InterestCalculationMethod,
    InterestSavingRecord,
)

# 統合インターフェース
__all__ = [
    # 市場分析
    "MarketEnvironmentAnalyzer",
    # パフォーマンス分析
    "BitbankInterestAvoidanceAnalyzer",
    "InterestCalculationMethod",
    "ComparisonPeriod",
    "InterestSavingRecord",
]

__version__ = "16.2.0"
__author__ = "Phase 16.2-C Integration"
__description__ = "Unified Analysis System"

# 統合状況
INTEGRATION_STATUS = {
    "phase": "16.2-C",
    "market_analysis": "analysis/market/ - 市場環境解析統合完了",
    "performance_analysis": "analysis/performance/ - パフォーマンス分析統合完了",
    "folders_integrated": "2 → 1",
    "substructure_created": "market/ + performance/",
    "api_unified": "統合インターフェース提供",
    "maintainability": "役割明確化・保守性向上",
}


def get_analysis_summary() -> dict:
    """統合分析システム概要取得"""
    return {
        "integration_status": INTEGRATION_STATUS,
        "market_analysis": {
            "module": "analysis.market",
            "class": "MarketEnvironmentAnalyzer",
            "features": [
                "市場環境解析",
                "ボラティリティレジーム判定",
                "流動性分析",
                "異常検知",
                "リアルタイム監視",
            ],
        },
        "performance_analysis": {
            "module": "analysis.performance",
            "class": "BitbankInterestAvoidanceAnalyzer",
            "features": [
                "金利コスト分析",
                "ROI改善測定",
                "統計レポート生成",
                "コスト比較分析",
                "効果可視化",
            ],
        },
    }
