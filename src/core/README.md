# src/core/ - コアシステム基盤

Phase 90α 時点で **30 Python ファイル / 9,892 行 / 6 サブフォルダ**で構成される取引システムの中核基盤。

## 📂 ディレクトリ構成

```
src/core/
├── README.md                      # このファイル
├── __init__.py
├── logger.py                      # JST 対応ログシステム・構造化出力
├── exceptions.py                  # カスタム例外階層
│
├── config/        (5 files / 1014 行)  # 設定管理（詳細: config/README.md）
├── execution/     (5 files / 2248 行)  # 実行モード管理（詳細: execution/README.md）
├── orchestration/ (11 files / 2500 行) # システム統合制御（詳細: orchestration/README.md）
├── persistence/   (2 files / 243 行)   # Firestore 永続化（詳細: persistence/README.md）
├── reporting/     (3 files / 376 行)   # レポート出力（詳細: reporting/README.md）
└── services/      (10 files / 3007 行) # 取引サイクル・レジーム分類（詳細: services/README.md）
```

## サブフォルダ役割サマリ

| サブフォルダ | 役割 | 主要クラス |
|---|---|---|
| `config/` | 設定管理（1 ファイル化された thresholds.yaml の読み書き）| `ThresholdManager`, `FeatureManager`, `RuntimeFlags` |
| `execution/` | バックテスト/ペーパー/ライブ 3 モード実行 | `BaseRunner`, `BacktestRunner`, `LiveTradingRunner`, `PaperTradingRunner` |
| `orchestration/` | 全サービス統合・ML ロード・gating・品質フィルタ・Phase 88 trigger_server | `TradingOrchestrator`, `MLServiceAdapter`, `MLHealthMonitor`, `QualityFilter`, `TradeGating` |
| `persistence/` | Phase 87 H4/H5 Firestore 状態永続化 | `FirestoreStateClient` |
| `reporting/` | レポート基底クラス・ペーパートレードレポート | `BaseReporter`, `PaperTradingReporter` |
| `services/` | 取引サイクル管理・レジーム分類・動的戦略選択 | `TradingCycleManager`, `MarketRegimeClassifier`, `DynamicStrategySelector` |

## 巨大ファイル（保全・整理スコープ外）

| ファイル | 行数 | 役割 | 注記 |
|---|---|---|---|
| `services/trading_cycle_manager.py` | 1,490 | 取引サイクル全体の orchestrator | public メソッド 1（`execute_trading_cycle`）でクリーン設計 |
| `execution/backtest_runner.py` | 1,472 | バックテストランナー | Phase コメント 81 件（数式根拠）|
| `orchestration/orchestrator.py` | 619 | アプリケーションサービス層 | public 4（initialize/run/run_trading_cycle/run_monitor_only）|
| `orchestration/ml_health_monitor.py` | 494 | ML 健全性監視・Phase 87 C4 サーキットブレーカー | - |

リファクタは別タスク（本番影響大・数日規模）。本フォルダの整理は「過去 Phase コメント保全 / pycache 削除 / README 整備」のみ。

## 主要エントリポイント

```python
from src.core.orchestration import TradingOrchestrator
from src.core.config import get_threshold

# システム初期化
orchestrator = TradingOrchestrator()
await orchestrator.initialize()

# 取引サイクル実行
await orchestrator.run()  # ライブ/ペーパー
await orchestrator.run_trading_cycle()  # 1 サイクルのみ
await orchestrator.run_monitor_only()  # Phase 89-α gating で monitor_only スキップ
```

## 設定参照パターン

```python
from src.core.config.threshold_manager import get_threshold

# ハードコード禁止・必ず get_threshold 経由
sl_rate = get_threshold("risk.sl_min_distance_ratio", 0.02)
```

## 関連リンク

- 親 README: [../README.md](../README.md)
- 開発ガイド: [../../CLAUDE.md](../../CLAUDE.md)
- 設定ファイル: `../../config/core/thresholds.yaml`

---

**最終更新**: 2026年5月20日（Phase 90α: 30 ファイル / 9892 行・6 サブフォルダ反映）
