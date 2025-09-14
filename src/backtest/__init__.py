"""
バックテストシステム - Phase 21・本番同一ロジック対応

Phase 21改良:
- BacktestEngineを廃止し、本番と同一のtrading_cycle_managerを使用
- ペーパートレードと同じアプローチでCSVデータからバックテスト実行
- 独自実装を削除し、保守性と信頼性を大幅向上
- CSVデータ差し替えによる簡単な期間変更対応

主要コンポーネント:
- BacktestReporter: レポート生成・可視化（Phase 21対応）
- CSVDataLoader: CSV形式の過去データ読み込み（data/csv_data_loader.pyを活用）

アーキテクチャ変更:
- 従来の独自エンジン廃止 → 本番取引ロジック統合
- 専用データフロー廃止 → CSV + data_pipeline統合
- 独自レポート廃止 → 統一レポートシステム活用.
"""

from .reporter import BacktestReporter

__all__ = [
    "BacktestReporter",
]

__version__ = "21.0.0"
__phase__ = "Phase 21"
__description__ = (
    "本番同一ロジック・バックテストシステム（独自エンジン廃止・CSVデータ対応・保守性向上）"
)
