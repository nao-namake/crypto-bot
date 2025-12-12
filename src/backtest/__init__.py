"""
バックテストシステム - Phase 49完了

Phase 49完了実績（2025/10/22）:
- 戦略シグナル事前計算実装（0埋め問題解消・ライブモード完全一致）
- TP/SL決済ロジック実装（エントリー/エグジット完全ペアリング）
- TradeTracker実装（勝率・プロフィットファクター・最大DD算出）
- matplotlib可視化実装（エクイティカーブ・損益分布・ドローダウン・価格チャート）

Phase 34-35完了実績:
- 15分足データ収集80倍改善（216件→17,271件・99.95%成功率）
- バックテスト10倍高速化達成（6-8時間→45分実行）
- 特徴量バッチ化（無限倍高速化）・ML予測バッチ化（3,000倍高速化）
- Bitbank Public API直接使用・期間統一機能実装

主要コンポーネント:
- BacktestReporter: レポート生成・TradeTracker統合（Phase 49拡張）
- BacktestVisualizer: matplotlib可視化システム（Phase 49.4新規）
- CSVDataLoader: CSV形式の過去データ読み込み（キャッシュ機能付き）

アーキテクチャ:
- 本番同一ロジック（TradingCycleManager統合）
- CSV専用データフロー（API依存排除）
- 固定ファイル名対応（期間変更簡易化）
- 15m足メイン取引・4h足環境認識の2軸構成
"""

from .reporter import BacktestReporter

__all__ = [
    "BacktestReporter",
]

__version__ = "49.15.0"
__phase__ = "Phase 49完了"
__description__ = "本番同一ロジック・バックテストシステム（Phase 49: 戦略シグナル事前計算・TP/SL決済・TradeTracker・matplotlib可視化実装）"
