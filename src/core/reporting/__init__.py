"""
レポート生成・通知システム - Phase 28完了・Phase 29最適化版

orchestrator.pyから分離したレポート生成機能とDiscord通知機能を統合管理。
バックテスト・ペーパートレード・エラーレポートの生成およびDiscord通知を担当。

Phase 28完了・Phase 29最適化: monitoringフォルダからDiscord通知機能を統合。
"""

# BacktestReporter moved to src/backtest/core_reporter.py
from .base_reporter import BaseReporter
from .discord_notifier import DiscordClient, DiscordFormatter, DiscordManager
from .paper_trading_reporter import PaperTradingReporter

__all__ = [
    # レポート生成機能
    "BaseReporter",
    "PaperTradingReporter",
    # Discord通知機能（Phase 28完了・Phase 29最適化）
    "DiscordClient",
    "DiscordFormatter",
    "DiscordManager",
]
