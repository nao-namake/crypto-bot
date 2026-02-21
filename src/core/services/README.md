# src/core/services/ - システムサービス層

## 役割

orchestrator.pyから分離したサービス機能を統合管理。取引サイクル実行・ヘルスチェック・ログ管理・市場レジーム分類を担当。

## ファイル構成

```
services/
├── trading_cycle_manager.py        # 取引サイクル実行管理（最重要・~1,100行）
├── health_checker.py               # システムヘルスチェック
├── trading_logger.py               # 取引ログ管理
├── system_recovery.py              # 自動復旧システム
├── graceful_shutdown_manager.py    # グレースフルシャットダウン
├── market_regime_classifier.py     # 市場レジーム分類器（4段階）
├── regime_types.py                 # RegimeType Enum定義
├── dynamic_strategy_selector.py    # レジーム別戦略重み選択
├── __init__.py                     # 5サービスエクスポート
└── README.md                       # このファイル
```

## 主要コンポーネント

| サービス | 役割 |
|---------|------|
| **TradingCycleManager** | データ取得→特徴量→戦略→ML→リスク→注文の全フロー制御 |
| **HealthChecker** | 全サービス健全性確認・システムリソース監視 |
| **TradingLoggerService** | 取引判定・実行結果・統計情報のログ出力 |
| **SystemRecoveryService** | MLサービス復旧・エラー記録・自動再起動 |
| **GracefulShutdownManager** | SIGINT/SIGTERM処理・30秒タイムアウト |
| **MarketRegimeClassifier** | 市場データ→4段階分類（tight_range/normal_range/trending/high_volatility） |
| **DynamicStrategySelector** | レジーム別戦略重み取得・重み検証 |

## 依存関係

- `src/core/orchestration/orchestrator.py` → TradingCycleManager初期化・取引サイクル実行
- `src/core/config/` → thresholds.yaml準拠設定管理
- `src/strategies/` → 6戦略システム・戦略シグナル生成
- `src/ml/` → ProductionEnsemble・ML予測結果生成
