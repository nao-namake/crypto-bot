"""
レポート生成・通知システム - Phase 49完了

orchestrator.pyから分離したレポート生成機能とDiscord通知機能を統合管理。
バックテスト・ペーパートレード・エラーレポートの生成およびDiscord通知を担当。

Phase 49完了:
- BaseReporter: 統一レポート保存インターフェース（backtest/paper_trading/error）
- PaperTradingReporter: ペーパートレードレポート生成（セッション統計・取引履歴・パフォーマンス）
- DiscordManager: Discord週間レポート専用通知システム（Phase 48完了・通知99%削減達成）

Phase 48: Discord通知システム大幅簡素化（週間レポート特化・通知99%削減・コスト35%削減）
Phase 28-29: レポート生成体系確立・Discord通知機能統合
"""

# BacktestReporter moved to src/backtest/core_reporter.py
from .base_reporter import BaseReporter
from .discord_notifier import DiscordClient, DiscordManager
from .paper_trading_reporter import PaperTradingReporter

__all__ = [
    # レポート生成機能
    "BaseReporter",
    "PaperTradingReporter",
    # Discord通知機能（Phase 48完了版 - 週間レポート専用）
    "DiscordClient",
    "DiscordManager",
]
