"""
レポート生成・通知システム - Phase 52.4

レポート生成機能とDiscord週間レポート送信を統合管理。
Phase 48で通知システムを99%削減し、週間レポート送信に特化。

主要機能:
- BaseReporter: 統一レポート保存インターフェース（JSON/Markdown）
- PaperTradingReporter: ペーパートレードレポート生成（セッション統計・取引履歴）
- DiscordClient: シンプルWebhook通知クライアント（画像ファイル送信対応）
- DiscordManager: 週間レポート専用通知マネージャー
"""

# BacktestReporter moved to src/backtest/core_reporter.py
from .base_reporter import BaseReporter
from .discord_notifier import DiscordClient, DiscordManager
from .paper_trading_reporter import PaperTradingReporter

__all__ = [
    # レポート生成機能
    "BaseReporter",
    "PaperTradingReporter",
    # Discord通知機能（週間レポート専用）
    "DiscordClient",
    "DiscordManager",
]
