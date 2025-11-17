# src/core/execution - 実行モード管理システム 📋 Phase 52.4

3モード実行システム（backtest/paper/live）の統合管理。
各モードは共通基底クラス（BaseRunner）を継承し、モード固有の処理を実装。

---

## 📂 ファイル構成

### 主要ファイル

- **`base_runner.py`** (189行): 実行モード基底クラス・共通インターフェース定義
- **`backtest_runner.py`** (1,243行): バックテストモード実装（戦略検証・パフォーマンス分析）
- **`paper_trading_runner.py`** (211行): ペーパートレードモード実装（仮想取引）
- **`live_trading_runner.py`** (339行): ライブトレードモード実装（実取引管理）
- **`__init__.py`** (22行): モジュールエクスポート

---

## 🏗️ アーキテクチャ

### 責任範囲

| モード | 責任 | 主要機能 |
|-------|------|---------|
| **BaseRunner** | 共通基盤 | 初期化・終了処理・依存性検証・エラーハンドリング・実行間隔制御 |
| **BacktestRunner** | バックテスト実行 | CSV読込・特徴量事前計算・時系列実行・TP/SL決済・TradeTracker統合・matplotlib可視化 |
| **PaperTradingRunner** | ペーパートレード | 仮想取引実行・セッション統計・定期レポート生成・Discord通知 |
| **LiveTradingRunner** | ライブトレード | 実取引管理・残高確認・証拠金維持率監視・Discord通知・取引サイクル実行 |

### 共通インターフェース（BaseRunner）

```python
class BaseRunner(ABC):
    @abstractmethod
    async def run(self) -> None:
        """メイン実行メソッド"""

    @abstractmethod
    async def initialize_mode(self) -> bool:
        """モード初期化処理"""

    @abstractmethod
    async def cleanup_mode(self) -> None:
        """モード終了処理"""
```

---

## 🎯 各モード詳細

### BacktestRunner（バックテストモード）

**目的**: 過去データを使用した戦略検証・パフォーマンス分析

**主要機能**:
- **戦略シグナル事前計算**: Look-ahead bias完全防止（全時点で実戦略実行）
- **TP/SL決済ロジック**: 高値・安値判定・リアル取引完全再現
- **TradeTracker統合**: エントリー/エグジットペアリング・損益計算
- **matplotlib可視化**: エクイティカーブ・損益分布・ドローダウン・価格チャート
- **CSV履歴データ読込**: 4h足・15m足対応
- **バックテスト高速化**: 特徴量事前計算・ML予測事前計算（Phase 35）

**設定ファイル連携**:
```yaml
# config/core/thresholds.yaml
execution:
  backtest_period_days: 180
  backtest_mode_interval_seconds: 1

backtest:
  lookback_window: 100
  min_data_points: 50
  progress_report_percentage: 10
  strategy_signal_min_data_rows: 20
```

**使用例**:
```python
from src.core.execution import BacktestRunner

backtest = BacktestRunner(orchestrator_ref, logger)
await backtest.run()
```

### PaperTradingRunner（ペーパートレードモード）

**目的**: 実資金を使わない仮想取引による戦略検証

**主要機能**:
- ペーパートレード管理（trading_cycle_manager統合）
- セッション統計（cycle_count・session_stats）
- レポート生成（PaperTradingReporter統合）
- 定期実行制御（デフォルト5分間隔）
- Discord通知統合（セッション開始・エラー通知）

**設定ファイル連携**:
```yaml
# config/core/thresholds.yaml
execution:
  paper_mode_interval_seconds: 300
  paper_report_interval: 10
```

**使用例**:
```python
from src.core.execution import PaperTradingRunner

paper = PaperTradingRunner(orchestrator_ref, logger)
await paper.run()
```

### LiveTradingRunner（ライブトレードモード）

**目的**: 実資金を使用した本番取引実行

**主要機能**:
- 実取引管理（trading_cycle_manager統合）
- 残高確認・証拠金維持率監視
- セッション統計（cycle_count・trade_count・total_pnl）
- Discord通知統合（取引開始・取引実行・エラー通知）
- 定期実行制御（デフォルト5分間隔）
- 進捗ログ出力（50サイクル毎）

**設定ファイル連携**:
```yaml
# config/core/thresholds.yaml
execution:
  live_mode_interval_seconds: 300

live:
  progress_log_cycle_interval: 50
```

**使用例**:
```python
from src.core.execution import LiveTradingRunner

live = LiveTradingRunner(orchestrator_ref, logger)
await live.run()
```

---

## ⚙️ 設定ファイル連携

### config/core/thresholds.yaml

**実行設定**:
```yaml
execution:
  backtest_period_days: 180
  live_mode_interval_seconds: 300
  paper_mode_interval_seconds: 300
  backtest_mode_interval_seconds: 1
```

**バックテスト設定**:
```yaml
backtest:
  lookback_window: 100
  min_data_points: 50
  progress_interval: 100
  progress_report_percentage: 10
  strategy_signal_min_data_rows: 20
```

**ライブトレード設定**:
```yaml
live:
  progress_log_cycle_interval: 50
```

### config/core/features.yaml

```yaml
development:
  backtest:
    drawdown_limits:  # DrawdownManager設定（Phase 52.2）
```

---

## 🚀 使用例

### モード別実行

```python
from src.core.execution import (
    BacktestRunner,
    PaperTradingRunner,
    LiveTradingRunner
)

# バックテスト実行
backtest = BacktestRunner(orchestrator_ref, logger)
await backtest.run()

# ペーパートレード実行
paper = PaperTradingRunner(orchestrator_ref, logger)
await paper.run()

# ライブトレード実行
live = LiveTradingRunner(orchestrator_ref, logger)
await live.run()
```

### 実行間隔の取得

```python
from src.core.execution import BaseRunner

runner = MyRunner(orchestrator_ref, logger)
interval = runner.get_mode_interval()  # モード別実行間隔（秒）
```

---

## 🔧 設計原則

### ハードコード禁止 ⛔

全ての設定値は`config/core/thresholds.yaml`で管理。

**❌ 避けるべき**:
```python
progress_interval = total_rows // 10  # ハードコード
```

**✅ 推奨**:
```python
from src.core.config import get_threshold
progress_percentage = get_threshold("backtest.progress_report_percentage", 10)
progress_interval = max(1, total_rows // progress_percentage)
```

### Look-ahead bias防止（BacktestRunner）

過去データのみを使用した戦略シグナル計算:

```python
# 各タイムスタンプで過去データのみ使用
for i in range(total_rows):
    historical_data = main_df.iloc[: i + 1]  # 過去データのみ
    features_df = feature_gen.generate_features_sync(historical_data)
    # 戦略実行...
```

### リアル取引完全再現（BacktestRunner）

高値・安値を使用したTP/SL決済判定:

```python
# 各時点の高値・安値でTP/SL判定
high_price = row["high"]
low_price = row["low"]

if low_price <= stop_loss_price:
    # SL決済実行
elif high_price >= take_profit_price:
    # TP決済実行
```

---

## 📊 Phase履歴（抜粋）

- **Phase 52.4**: コード品質改善・Phase参照統一・ハードコード値削減・README.md作成
- **Phase 52.2**: DrawdownManager統合（本番シミュレーション対応）
- **Phase 51.10-C**: バックテスト進捗表示改善（ETA追加・経過時間表示）
- **Phase 51.8-J4**: バックテスト完全改修（5分間隔実行・TP/SL決済・証拠金返還）
- **Phase 49**: バックテスト完全改修（TradeTracker統合・matplotlib可視化・信頼性100%達成）
- **Phase 35**: バックテスト10倍高速化（特徴量事前計算・ML予測事前計算）
- **Phase 28-29**: 実行モード機能分離・3モード統合管理確立

---

## 🧪 テスト

### 単体テスト

- `tests/unit/core/execution/`: 実行モード単体テスト
- カバレッジ目標: 68%以上

### バックテストデータ要件

- **4h足データ**: `src/backtest/data/historical/btc_jpy_4h.csv`（最低1,081行）
- **15m足データ**: `src/backtest/data/historical/btc_jpy_15m.csv`（最低17,272行）

---

## 🔗 関連ファイル

### システム統合

- `src/core/orchestration/orchestrator.py`: TradingOrchestrator（実行モード呼び出し元）
- `src/core/services/trading_cycle_manager.py`: TradingCycleManager（取引サイクル管理）

### レポーティング

- `src/backtest/reporter.py`: BacktestReporter（バックテストレポート生成）
- `src/core/reporting/paper_trading_reporter.py`: PaperTradingReporter（ペーパーレポート）

### データ取得

- `src/backtest/data/csv_data_loader.py`: CSVDataLoader（履歴データ読込）

---

**🎯 Phase 52.4完了**: Phase参照統一・ハードコード値削減・README.md作成により、保守性・可読性が大幅に向上しています。
