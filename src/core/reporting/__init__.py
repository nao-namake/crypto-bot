"""
レポート生成システム - Phase 14-B リファクタリング

orchestrator.pyから分離したレポート生成機能を統合管理。
バックテスト・ペーパートレード・エラーレポートの生成を担当。
"""

# BacktestReporter moved to src/backtest/core_reporter.py
from .base_reporter import BaseReporter
from .paper_trading_reporter import PaperTradingReporter

__all__ = ["BaseReporter", "PaperTradingReporter"]
