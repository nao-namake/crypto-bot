# src/trading/position/ - ポジション管理層

## 役割

仮想ポジションの追跡・制限管理・孤児クリーンアップ・クールダウン制御を担当する。
Phase 38で trading レイヤードアーキテクチャの一部として分離。

## ファイル構成

| ファイル | 行数 | クラス | 責務 |
|---------|------|--------|------|
| `tracker.py` | 456 | PositionTracker | 仮想ポジション追加・削除・検索・平均価格追跡 |
| `limits.py` | 379 | PositionLimits | ポジション数・資金利用率・日次取引回数の制限チェック |
| `cleanup.py` | 321 | PositionCleanup | 孤児ポジション検出・TP/SL注文削除（OCO代替） |
| `cooldown.py` | 178 | CooldownManager | トレンド強度ベース柔軟クールダウン判定 |
| `__init__.py` | 17 | - | モジュール初期化・公開API定義 |

## クラス詳細

### PositionTracker（456行・19メソッド）

仮想ポジション（`virtual_positions`リスト）の管理と統計追跡。

主要メソッド:
- `add_position()` / `remove_position()` / `find_position()`: CRUD操作
- `get_position_count()` / `get_total_exposure()`: 集計
- `calculate_average_entry_price()`: 加重平均エントリー価格計算（統計用）
- `update_average_on_entry()` / `update_average_on_exit()`: 平均価格更新
- `get_position_summary()`: ポジション状態サマリー

### PositionLimits（379行・9メソッド）

エントリー前の各種制限チェックを一括実行。

主要メソッド:
- `check_limits()`: 全制限チェック統合
- `_check_minimum_balance()`: 最小資金要件
- `_check_cooldown()`: クールダウン判定
- `_check_max_positions()`: 最大ポジション数
- `_check_capital_usage()`: 残高利用率
- `_check_daily_trades()`: 日次取引回数

### PositionCleanup（321行・8メソッド）

bitbank OCO非対応の代替として、ポジション決済後に残ったTP/SL注文を自動削除。

主要メソッド:
- `cleanup_orphaned_positions()`: 孤児ポジション検出・クリーンアップ
- `check_stale_positions()`: 古いポジション検出
- `emergency_cleanup()`: 緊急クリーンアップ

### CooldownManager（178行・4メソッド）

トレンド強度（ADX 50% + DI 30% + EMA 20%）に基づく柔軟なクールダウン判定。
強度 >= 0.7 でクールダウンをスキップし、強トレンド時の機会損失を防止。

主要メソッド:
- `should_apply_cooldown()`: クールダウン適用判定
- `calculate_trend_strength()`: トレンド強度計算
- `get_cooldown_status()`: ステータス取得

## 依存関係

- `src/core/logger`: ロギング
- `src/core/config/threshold_manager`: `get_threshold()` による設定取得
- `src/data/bitbank_client`: API呼び出し（cleanup時）

参照元:
- `src/trading/execution/executor.py`: ポジション追跡・制限チェック
- `src/trading/execution/stop_manager.py`: TP/SL配置時のポジション参照
- `src/core/execution/execution_service.py`: 制限チェック呼び出し

## 設定ファイル

| ファイル | 関連設定 |
|---------|---------|
| `config/core/thresholds.yaml` | ポジション制限値・クールダウン閾値 |
| `config/core/features.yaml` | 柔軟クールダウン有効/無効 |
