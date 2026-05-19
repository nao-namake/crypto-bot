# src/core/execution/ - 実行モード管理

バックテスト / ペーパートレード / ライブトレードの 3 実行モードを統一インターフェース（`BaseRunner`）で切替。

## ファイル構成

| ファイル | 行数 | 役割 |
|---|---|---|
| `__init__.py` | 22 | エクスポート |
| `base_runner.py` | 212 | 基底実行ランナー（ABC・全モード共通）|
| `backtest_runner.py` | 1,472 | バックテスト実行（CSV データ・時系列ループ・Phase 87 H10 品質フィルタ統合）|
| `live_trading_runner.py` | 335 | ライブトレード実行（Cloud Run + bitbank API）|
| `paper_trading_runner.py` | 207 | ペーパートレード実行（実 API + 仮想ポジション）|

## 主要 API

```python
from src.core.execution import BacktestRunner, LiveTradingRunner, PaperTradingRunner

# バックテスト
runner = BacktestRunner(config)
await runner.run()  # → True/False (成功フラグ)

# ライブ
runner = LiveTradingRunner(config)
await runner.run()  # 無限ループ

# ペーパー
runner = PaperTradingRunner(config)
await runner.run()
```

## 設計原則

- **本番同一ロジック**: バックテストもライブと同じ `TradingCycleManager` を経由（Phase 65.13）
- **モード切替**: `main.py --mode {backtest|paper|live}` で動的選択

## 巨大ファイル backtest_runner.py（1472 行・Phase コメント 81 件）

数式根拠・修正履歴が密集（Phase 60 Walk-Forward 検証・Phase 75 パイプライン最適化・Phase 87 H10 品質フィルタ統合等）。各コメントは保全価値あり。

## 関連リンク

- 親 README: [../README.md](../README.md)
- 取引サイクル: [../services/README.md](../services/README.md)
- バックテストレポート: [../../backtest/README.md](../../backtest/README.md)

---

**最終更新**: 2026年5月20日（Phase 90α: 新規作成）
