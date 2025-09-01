"""
バックテストシステム - Phase 12・CI/CD統合・手動実行監視・段階的デプロイ対応.

レガシーシステムの良い部分を継承しつつ、シンプルで高性能な
バックテスト環境を提供。過去6ヶ月データでの戦略検証を実現。

主要コンポーネント:
- BacktestEngine: バックテスト実行エンジン・GitHub Actions対応
- Evaluator: 性能評価・統計分析・CI/CD品質ゲート対応
- DataLoader: 過去データ取得・管理・手動実行監視対応
- Reporter: レポート生成・可視化・段階的デプロイ対応

レガシー継承機能:
- TradeRecord: 取引記録管理
- ウォークフォワード検証
- 評価指標計算（最大ドローダウン、CAGR、シャープレシオ）

Phase 12新システム改善:
- データ配置最適化（src/backtest/data/）・CI/CD統合
- Phase 1-11統合インターフェース・GitHub Actions対応
- 60秒以内処理目標・手動実行監視対応
- シンプルな設定管理・段階的デプロイ対応.
"""

# Phase 18統合: DataLoaderはdata_pipeline.pyのBacktestDataLoaderに統合
from ..data.data_pipeline import BacktestDataLoader
from .engine import BacktestEngine, TradeRecord
from .evaluator import BacktestEvaluator, PerformanceMetrics
from .reporter import BacktestReporter

__all__ = [
    "BacktestEngine",
    "TradeRecord",
    "BacktestEvaluator",
    "PerformanceMetrics",
    "BacktestDataLoader",  # Phase 18統合版
    "BacktestReporter",
]

__version__ = "18.0.0"
__phase__ = "Phase 18"
__description__ = "統合バックテストシステム（重複削除・コード統合・reporter統合・DataLoader統合・BacktestRunner削除・1500行削減達成）"
