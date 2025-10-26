"""
実行モード管理システム - Phase 49完了

orchestrator.pyから分離した実行モード機能を統合管理。
3モード（backtest/paper/live）の統合実行を担当。

Phase 49完了:
- BacktestRunner: 完全改修（戦略シグナル事前計算・TP/SL決済ロジック・TradeTracker統合・matplotlib可視化）
- LiveTradingRunner: 実取引管理・残高確認・取引サイクル実行
- PaperTradingRunner: ペーパートレード管理・セッション統計・レポート生成
- BaseRunner: 共通インターフェース・実行モード基底クラス

Phase 35: バックテスト10倍高速化（特徴量事前計算・ML予測事前計算）
Phase 28-29: 実行モード機能分離・3モード統合管理確立
"""

from .backtest_runner import BacktestRunner
from .base_runner import BaseRunner
from .live_trading_runner import LiveTradingRunner
from .paper_trading_runner import PaperTradingRunner

__all__ = ["BaseRunner", "PaperTradingRunner", "LiveTradingRunner", "BacktestRunner"]
