# src/ - AI自動取引システム

Phase 64完了。55特徴量 → 6戦略 → ML予測 → リスク管理 → 取引実行の完全自動化。

## ディレクトリ構成

```
src/
├── core/                   # 基盤システム
│   ├── orchestration/      # TradingOrchestrator（取引サイクル制御）
│   ├── config/             # 設定管理（unified.yaml / thresholds.yaml / features.yaml）
│   ├── execution/          # 実行ランナー（backtest / live / paper）
│   ├── reporting/          # レポート生成（BaseReporter・PaperTradingReporter）
│   └── services/           # GracefulShutdown・MarketRegimeClassifier・HealthChecker
├── data/                   # Bitbank API統合・データキャッシュ
├── features/               # 特徴量生成（49基本特徴量）
├── strategies/             # 6戦略（BBReversal・StochasticDivergence・ATRBased・DonchianChannel・MACDEMACrossover・ADXTrendStrength）
├── ml/                     # ProductionEnsemble（LightGBM・XGBoost・RandomForest）
├── trading/                # 取引管理（5層分離）
│   ├── core/               # enums・types
│   ├── balance/            # MarginMonitor（証拠金維持率監視）
│   ├── execution/          # ExecutionService・OrderStrategy・TPSLManager・PositionRestorer
│   ├── position/           # Tracker・Limits・Cleanup
│   └── risk/               # IntegratedRiskManager・Kelly基準・DrawdownManager
├── backtest/               # バックテストシステム（CSV・TradeTracker・レポート）
└── monitoring/             # 週間レポート生成
```

## データフロー

```
Bitbank API（15分足取得）
    ↓
特徴量生成（49基本特徴量）
    ↓
6戦略実行 → 戦略信号（+6特徴量 = 55特徴量）
    ↓
ML予測（ProductionEnsemble → 信頼度）
    ↓
レジーム判定（tight_range / normal_range / trending）
    ↓
動的戦略選択（レジーム別重みづけ適用）
    ↓
リスク評価（Kelly基準・ポジション制限）
    ↓
取引実行（完全指値・bitbank API）
```

## 詳細ドキュメント

- [戦略システム](strategies/README.md)
- [取引実行システム](trading/README.md)
- [コア基盤](core/README.md)
