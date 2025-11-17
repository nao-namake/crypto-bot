"""
バックテストシステム - Phase 52.4-B対応完了

最終更新: 2025/11/16 (Phase 52.4-B)

現状:
- 本番同一ロジック・高速CSV読み込みシステム
- TradeTracker統合・matplotlib可視化
- 信頼性100%達成（Phase 49完全改修ベース）
- Phase 51-52 ML統合・レジーム分類対応

主要コンポーネント:
- BacktestReporter: レポート生成・TradeTracker統合・週次レポート対応
- BacktestVisualizer: matplotlib可視化システム（4種類のグラフ）
- CSVDataLoader: 高速CSV読み込み（キャッシュ機能・8種類整合性チェック）

アーキテクチャ:
- 本番同一ロジック（TradingCycleManager統合）
- CSV専用データフロー（API依存排除）
- 固定ファイル名対応（期間変更簡易化）
- 15m足メイン取引・4h足環境認識の2軸構成

開発履歴:
- Phase 52.4-B: コード整理・ドキュメント統一
- Phase 49: 戦略シグナル事前計算・TP/SL決済・TradeTracker・matplotlib可視化
- Phase 34-35: 15分足データ収集80倍改善・バックテスト10倍高速化
"""

from .reporter import BacktestReporter

__all__ = [
    "BacktestReporter",
]

__version__ = "52.4.0"
__phase__ = "Phase 52.4-B対応完了"
__description__ = (
    "本番同一ロジック・バックテストシステム（Phase 52.4-B: コード整理・ドキュメント統一完了）"
)
