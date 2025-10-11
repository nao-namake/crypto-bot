"""
レポート生成・通知システム - Phase 38.4完了版

orchestrator.pyから分離したレポート生成機能とDiscord通知機能を統合管理。
バックテスト・ペーパートレード・エラーレポートの生成およびDiscord通知を担当。

Phase 28-29最適化: monitoringフォルダからDiscord通知機能統合・レポート生成体系確立
Phase 38: trading層レイヤードアーキテクチャ実装完了
Phase 38.4: 全モジュールPhase統一・コード品質保証完了
"""

# BacktestReporter moved to src/backtest/core_reporter.py
from .base_reporter import BaseReporter
from .discord_notifier import DiscordClient, DiscordFormatter, DiscordManager
from .paper_trading_reporter import PaperTradingReporter

__all__ = [
    # レポート生成機能
    "BaseReporter",
    "PaperTradingReporter",
    # Discord通知機能（Phase 38.4完了版）
    "DiscordClient",
    "DiscordFormatter",
    "DiscordManager",
]
