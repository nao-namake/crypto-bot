# src/ - AI 自動取引システム

**Phase 90α**: 55 特徴量 → 6 戦略 → ML 4 モデルアンサンブル品質判定 → リスク管理 → 取引実行の完全自動化。

## ディレクトリ構成

```
src/
├── README.md
├── __init__.py
├── analysis/               # 分析共通ライブラリ（Phase 87 H10・gcp_metrics 等）
├── backtest/               # バックテストシステム（reporter / visualizer / CSV ローダー・3.2MB）
├── core/                   # 基盤システム（30 .py / 9892 行）
│   ├── config/             # 設定管理（thresholds.yaml 1 ファイル化）
│   ├── execution/          # 実行ランナー（backtest / live / paper）
│   ├── orchestration/      # TradingOrchestrator・gating・品質フィルタ・trigger_server
│   ├── persistence/        # Firestore 永続化（Phase 87 H4/H5）
│   ├── reporting/          # レポート生成
│   └── services/           # TradingCycleManager・MarketRegimeClassifier・DynamicStrategySelector
├── data/                   # Bitbank API 統合・WebSocket・データキャッシュ・external API
├── features/               # 特徴量生成（55 特徴量・FeatureCache）
├── ml/                     # ProductionEnsemble 4 モデル（LightGBM / XGBoost / RandomForest / N-BEATS）+ PurgedKFold
├── strategies/             # 6 戦略（ATRBased / BBReversal / StochasticReversal / CMFReversal / MACDEMACrossover / ADXTrendStrength）
└── trading/                # 取引管理（6 層分離・13K 行）
    ├── analysis/           # TradeAnalysisRecorder（Phase 69.7 事後分析）
    ├── balance/            # MarginMonitor（証拠金維持率監視）
    ├── core/               # enums・types
    ├── execution/          # ExecutionService・OrderStrategy・TPSLManager・StopManager・PositionRestorer・SLMonitor
    ├── position/           # Tracker・Limits・Cleanup・Cooldown
    └── risk/               # IntegratedRiskManager・Kelly 基準・DrawdownManager・AnomalyDetector
```

## データフロー

```
Bitbank API（15 分足取得・WebSocket）
    ↓
特徴量生成（55 特徴量・SHAP+Forward Selection + Phase 89-β/γ/δ 拡張）
    ↓
ML 予測（ProductionEnsemble 4 モデル → success/failure 確率）
    ↓
レジーム判定（tight_range / normal_range / trending）
    ↓
動的戦略選択（レジーム別重みづけ・trending 全停止）
    ↓
品質フィルタ（メタラベリング Go/No-Go・Phase 90α）
    ↓
リスク評価（Fractional Kelly・ポジション制限・Drift 検出）
    ↓
取引実行（完全指値 + stop SL・bitbank API・Atomic Entry）
```

## 整理サマリ（Phase 90α・2026-05-20）

| サブフォルダ | 死コード削除 | README |
|---|---|---|
| data/ | bitbank_client.py 4 メソッド・78 行 | 全面改訂 |
| features/ | 0 | 全面改訂 |
| strategies/ | **DonchianChannel 1112 行**（実体 + テスト + enum）| 4 件改訂 |
| ml/ | 0 | 全面改訂 |
| analysis/ | 0 | 2 件新規 |
| backtest/ | 0（.bak 2 件・1.8MB 削除）| 行数のみ修正 |
| core/ | 0 | 1 全面改訂 + 4 新規 |
| trading/ | **stop_manager.py 2 メソッド・144 行**+ テスト 9 件 | 2 新規 + 1 部分修正 |

**合計**: コード **1334 行削減** + テスト **697 行削減** + ドキュメント **20+ README 整備**。

## 詳細ドキュメント

- [analysis/](analysis/README.md) — 分析共通ライブラリ
- [backtest/](backtest/README.md) — バックテストシステム
- [core/](core/README.md) — 基盤システム（サブフォルダ別 README 完備）
- [data/](data/README.md) — データ層
- [features/](features/README.md) — 特徴量生成
- [ml/](ml/README.md) — 機械学習
- [strategies/](strategies/README.md) — 6 戦略
- [trading/](trading/README.md) — 取引管理層（サブフォルダ別 README 完備）

## 関連リンク

- 親 README: [../README.md](../README.md)
- 開発ガイド: [../CLAUDE.md](../CLAUDE.md)
- 統合運用ガイド: [../docs/運用ガイド/統合運用ガイド.md](../docs/運用ガイド/統合運用ガイド.md)

---

**最終更新**: 2026年5月20日（Phase 90α: 55 特徴量・4 モデル・6 戦略・6 層分離 trading・全 22 README 整備完了）
