"""
Market Analysis Module - Phase 16.2-C Integration

市場分析モジュール - 市場環境解析・レジーム判定・異常検知

統合前: analysis/market_environment_analyzer.py
統合後: analysis/market/ サブディレクトリ

機能:
- 市場環境解析・ボラティリティレジーム判定
- 流動性分析・市場深度分析
- 異常検知・トレンド分析
- リアルタイム市場監視

Phase 16.2-C実装日: 2025年8月8日
"""

from .market_environment_analyzer import MarketEnvironmentAnalyzer

__all__ = [
    "MarketEnvironmentAnalyzer",
]

__version__ = "16.2.0"
__author__ = "Phase 16.2-C Integration"
__description__ = "Market Analysis Integration Module"
