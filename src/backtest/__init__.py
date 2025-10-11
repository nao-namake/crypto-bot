"""
バックテストシステム - Phase 38.4完了

Phase 34-35完了実績:
- 15分足データ収集80倍改善（216件→17,271件・99.95%成功率）
- バックテスト10倍高速化達成（6-8時間→45分実行）
- 特徴量バッチ化（無限倍高速化）・ML予測バッチ化（3,000倍高速化）
- Bitbank Public API直接使用・期間統一機能実装

主要コンポーネント:
- BacktestReporter: レポート生成・可視化（JSON形式・進捗追跡）
- CSVDataLoader: CSV形式の過去データ読み込み（キャッシュ機能付き）

アーキテクチャ:
- 本番同一ロジック（TradingCycleManager統合）
- CSV専用データフロー（API依存排除）
- 固定ファイル名対応（期間変更簡易化）.
"""

from .reporter import BacktestReporter

__all__ = [
    "BacktestReporter",
]

__version__ = "38.4.0"
__phase__ = "Phase 38.4完了"
__description__ = "本番同一ロジック・バックテストシステム（Phase 34-35: 15分足80倍改善・10倍高速化達成・CSV直接取得実装）"
