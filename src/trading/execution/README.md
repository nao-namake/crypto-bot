# src/trading/execution/ - 注文実行層

## 役割

注文実行・TP/SL管理・ポジション復元を担当する。
Phase 38で trading レイヤードアーキテクチャの一部として分離。
Phase 64.1でTP/SLロジックを専用モジュールに分離・責務を明確化。

## ファイル構成

| ファイル | 行数 | クラス | 責務 |
|---------|------|--------|------|
| `executor.py` | 1,294 | ExecutionService | エントリー注文実行・ペーパー/ライブ分岐 |
| `stop_manager.py` | 1,525 | StopManager | TP/SL到達判定・決済実行 |
| `order_strategy.py` | 769 | OrderStrategy | 注文タイプ決定・Maker実行・最小ロット保証 |
| `tp_sl_config.py` | 125 | TPSLConfig | TP/SL設定パス定数・取得ヘルパー |
| `tp_sl_manager.py` | 1,507 | TPSLManager | TP/SL設置・検証・復旧・計算・ロールバック |
| `position_restorer.py` | 554 | PositionRestorer | ポジション復元・孤児クリーンアップ |

## クラス詳細

### ExecutionService（1,294行）

エントリー注文の実行を担当。ペーパートレード/ライブトレード/バックテスト対応。
エントリー後にTPSLManagerを呼び出してTP/SL配置を実行。

主要メソッド:
- `execute_trade()`: 注文実行メインロジック
- `_execute_live_trade()` / `_execute_paper_trade()` / `_execute_backtest_trade()`: モード別実行
- `restore_positions_from_api()`: ポジション復元（PositionRestorer委譲）

### StopManager（1,525行）

TP/SL到達判定・決済実行を担当。

主要メソッド:
- `check_stop_conditions()`: TP/SL到達チェック
- `cleanup_position_orders()`: ポジション注文クリーンアップ
- `handle_sl_execution()`: SL約定処理

### OrderStrategy（769行）

注文タイプ（指値/成行）の決定・Maker注文実行・最小ロット保証。

主要メソッド:
- `get_optimal_execution_config()`: 最適注文戦略決定
- `get_maker_execution_config()`: Maker戦略判定
- `execute_maker_order()`: Maker注文実行
- `ensure_minimum_trade_size()`: 最小ロット保証

### TPSLConfig（125行）

TP/SL関連の設定パスを定数化し、文字列リテラルによるtypoバグを防止。

主要定数:
- `TPSLConfig.TP_MIN_PROFIT_RATIO`: TP最小利益率パス
- `TPSLConfig.SL_MAX_LOSS_RATIO`: SL最大損失率パス
- `TPSLConfig.FIXED_AMOUNT_TP_*`: 固定金額TP関連パス

ヘルパーメソッド:
- `tp_regime_path()` / `sl_regime_path()`: レジーム別設定パス生成
- `get_tp_sl_config()`: TP/SL設定一括取得

### TPSLManager（1,507行）

TP/SL設置・検証・復旧・計算・ロールバックを統合管理。
executor.pyとstop_manager.pyに分散していたTP/SLロジックを集約。

主要メソッド:
- `place_tp_with_retry()` / `place_sl_with_retry()`: TP/SLリトライ配置
- `place_take_profit()` / `place_stop_loss()`: TP/SL注文配置
- `calculate_tp_sl_for_live_trade()`: TP/SL価格計算
- `cleanup_old_tp_sl_before_entry()`: エントリー前古いTP/SL注文クリーンアップ
- `schedule_tp_sl_verification()`: TP/SL検証スケジューリング
- `periodic_tp_sl_check()`: 10分間隔TP/SL定期チェック
- `rollback_entry()`: Atomic Entryロールバック

### PositionRestorer（554行）

Container再起動時（Cloud Run）に実ポジションから仮想ポジションを復元。
孤児SL/未約定注文のクリーンアップも担当。

主要メソッド:
- `restore_positions_from_api()`: ポジション復元メイン
- `scan_orphan_positions()`: 孤児ポジションスキャン
- `cleanup_old_unfilled_orders()`: 古い未約定注文クリーンアップ
- `cleanup_orphan_sl_orders()`: 孤児SL注文クリーンアップ

## TPSLConfig使用パターン

```python
from src.trading.execution.tp_sl_config import TPSLConfig
from src.core.config.threshold_manager import get_threshold

# 定数でパス指定（文字列リテラル禁止）
tp_ratio = get_threshold(TPSLConfig.TP_MIN_PROFIT_RATIO, 0.009)
sl_ratio = get_threshold(TPSLConfig.SL_MAX_LOSS_RATIO, 0.007)

# レジーム別パス生成
regime_tp = get_threshold(
    TPSLConfig.tp_regime_path("tight_range", "min_profit_ratio"), 0.004
)
```

## 依存関係

- `src/core/logger`: ロギング
- `src/core/config/threshold_manager`: `get_threshold()` による設定取得
- `src/data/bitbank_client`: bitbank API呼び出し
- `src/trading/position/tracker`: ポジション追跡
- `src/trading/risk/`: リスク評価

参照元:
- `src/core/orchestration/orchestrator.py`: 取引サイクル制御

## 設定ファイル

| ファイル | 関連設定 |
|---------|---------|
| `config/core/thresholds.yaml` | TP/SL比率・レジーム別設定・固定金額TP |
| `config/core/unified.yaml` | 注文実行設定・SL設定 |
| `config/core/features.yaml` | 機能トグル |
