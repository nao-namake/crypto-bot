"""
実行モード管理システム - Phase 52.4

orchestrator.pyから分離した実行モード機能を統合管理。
3モード（backtest/paper/live）の統合実行を担当。

主要機能:
- BacktestRunner: バックテスト実行（戦略シグナル事前計算・TP/SL決済・TradeTracker統合）
- LiveTradingRunner: ライブトレード実行（実取引管理・残高確認・証拠金維持率監視）
- PaperTradingRunner: ペーパートレード実行（仮想取引・セッション統計・レポート生成）
- BaseRunner: 共通基底クラス（インターフェース定義・共通機能）
"""

from .backtest_runner import BacktestRunner
from .base_runner import BaseRunner
from .live_trading_runner import LiveTradingRunner
from .paper_trading_runner import PaperTradingRunner

__all__ = ["BaseRunner", "PaperTradingRunner", "LiveTradingRunner", "BacktestRunner"]
