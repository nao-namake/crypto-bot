# src/trading/position/ - ポジション管理層 📊 Phase 52.4-B完了

## 🎯 役割・責任

ポジション追跡・制限管理・クリーンアップ・クールダウン制御を担当します。tradingレイヤードアーキテクチャの一部として、Phase 46でデイトレード特化・個別TP/SL管理に回帰し、Phase 52.4-Bで設定管理統一・コード品質最適化を完了しました。

## 📂 ファイル構成

```
position/
├── tracker.py       # ポジション追跡（Phase 46: 個別TP/SL管理・平均価格統計のみ）
├── limits.py        # ポジション制限管理
├── cleanup.py       # 孤児ポジションクリーンアップ（Phase 37.5.3）
├── cooldown.py      # クールダウン管理（Phase 31.1）
├── __init__.py      # モジュール初期化
└── README.md        # このファイル
```

## 📈 Phase 46完了（2025年10月22日）

**🎯 Phase 46: デイトレード特化・個別TP/SL管理回帰・統合機能削除**

### ✅ Phase 46.2.4 統合TP/SL管理削除成果（-173行のコード削減）

**背景**: Phase 42-42.4で実装したスイングトレード向けの統合TP/SL管理機能（複数ポジション加重平均・統合注文ID管理・状態永続化）が、デイトレード特化戦略では不要な複雑性を生み出していました。Phase 46で個別TP/SL管理に回帰し、シンプル性を最優先しました。

**削除内容**:
- **tracker.py**: 統合TP/SL ID管理削除（Line 366-469、-104行）
  - `get_consolidated_tp_sl_ids()` 削除
  - `set_consolidated_tp_sl_ids()` 削除
  - `get_consolidated_position_info()` 削除
  - `clear_consolidated_tp_sl()` 削除
- **tracker.py**: 状態永続化機能削除（Line 489-538、-50行）
  - `_save_state()` 削除（JSON保存機能）
  - `_load_state()` 削除（起動時復元機能）
  - `src/core/state/consolidated_tp_sl_state.json` 削除
- **tracker.py**: 統合用フィールド削除（Line 34-41、-8行）
  - `_consolidated_tp_order_id` 削除
  - `_consolidated_sl_order_id` 削除
  - `_consolidated_tp_price` 削除
  - `_consolidated_sl_price` 削除
  - `_side` 削除
- **コメント整理**: Phase 42-42.4関連コメント削除（-11行）
- **合計**: -173行削除（Phase 42-42.4レガシーコード完全削除）

**効果**:
- コードベース大幅簡略化（tracker.py: 538行 → 373行、-30.7%）
- 個別TP/SL管理に回帰（エントリー毎に独立したTP/SL注文）
- 平均価格追跡は統計目的で維持（統合機能削除・監視用データとして活用）

### ✅ Phase 46設計変更：平均価格追跡の用途変更

**背景**: Phase 42で実装した平均価格追跡機能は統合TP/SL計算用でしたが、Phase 46では統計・監視目的に用途変更しました。

**変更内容**:
```python
# Phase 46: 平均価格追跡（統計用・統合TP/SL機能は削除）
self._average_entry_price: float = 0.0
self._total_position_size: float = 0.0
```

**活用方法**:
- Discord通知での平均エントリー価格表示
- ダッシュボード統計情報
- ポジション管理モニタリング
- デバッグ・解析用データ

**メソッド維持**:
- `calculate_average_entry_price()`: 加重平均価格計算（統計用）
- `update_average_on_entry()`: エントリー時平均更新（統計用）
- `update_average_on_exit()`: 決済時平均更新（統計用）

### 📊 Phase 46重要事項
- **Phase 46設計哲学**: デイトレード特化・個別TP/SL管理・シンプル性優先
- **平均価格用途変更**: 統合TP/SL計算用 → 統計・監視用
- **状態永続化削除**: Cloud Run再起動対応不要（個別TP/SL管理）
- **品質保証完了**: 1,101テスト100%成功・68.93%カバレッジ達成

---

## 🔧 主要ファイル詳細（Phase 52.4完了）

### **tracker.py**（404行・16メソッド）

ポジション追跡サービス。Phase 46でデイトレード特化・個別TP/SL管理に回帰。平均価格追跡は統計・監視目的で維持。

**主要メソッド**:
- `add_position()`: ポジション追加
- `remove_position()`: ポジション削除
- `find_position()`: ポジション検索
- `calculate_average_entry_price()`: 加重平均価格計算（統計用）
- `update_average_on_entry()`: エントリー時平均更新（統計用）
- `update_average_on_exit()`: 決済時平均更新（統計用）

### **limits.py**（363行・9メソッド）

ポジション制限管理サービス。Phase 51.8でレジーム別制限実装・Phase 31.1で柔軟クールダウン統合。

**主要メソッド**:
- `check_limits()`: 制限チェック統合エントリーポイント
- `_check_minimum_balance()`: 最小資金要件チェック
- `_check_cooldown()`: クールダウンチェック（Phase 31.1柔軟判定）
- `_check_max_positions()`: 最大ポジション数チェック（Phase 51.8レジーム別制限）
- `_check_capital_usage()`: 残高利用率チェック
- `_check_daily_trades()`: 日次取引回数チェック

### **cleanup.py**（304行・8メソッド）

孤児ポジションクリーンアップサービス。Phase 37.5.3でbitbank OCO非対応の代替実装完成。

**主要メソッド**:
- `cleanup_orphaned_positions()`: 孤児ポジションクリーンアップ（OCO代替）
- `check_stale_positions()`: 古いポジション検出
- `emergency_cleanup()`: 緊急クリーンアップ

### **cooldown.py**（178行・4メソッド）

クールダウン管理サービス。Phase 31.1でトレンド強度ベース判定実装。

**主要メソッド**:
- `should_apply_cooldown()`: 柔軟クールダウン判定（トレンド強度>=0.7でスキップ）
- `calculate_trend_strength()`: トレンド強度計算（ADX 50%・DI 30%・EMA 20%）
- `get_cooldown_status()`: クールダウンステータス取得

## 📝 使用方法・例

### **PositionTracker: 平均価格追跡（統計用）**

```python
from src.trading.position.tracker import PositionTracker

# PositionTracker初期化
tracker = PositionTracker()

# エントリー時平均価格更新（統計用）
average_price = tracker.update_average_on_entry(price=10000000.0, amount=0.001)
# → 平均: 1000万円

average_price = tracker.update_average_on_entry(price=10100000.0, amount=0.001)
# → 平均: 1005万円（Discord通知・ダッシュボード統計用）
```

### **PositionLimits: 制限チェック**

```python
from src.trading.position.limits import PositionLimits

# PositionLimits初期化
limits = PositionLimits()

# 制限チェック実行
result = await limits.check_limits(evaluation, mode="live")
if result["allowed"]:
    print("エントリー許可")
else:
    print(f"エントリー拒否: {result['reason']}")
```

## ⚠️ 注意事項・制約

### **Phase 46設計思想**
- **デイトレード特化**: 個別TP/SL管理・固定TP/SL（SL 1.5%・TP 1.0%）
- **平均価格用途変更**: 統合TP/SL計算用 → 統計・監視用（Discord通知・ダッシュボード）
- **Phase 42-42.4削除**: 統合TP/SL・トレーリングストップ・状態永続化完全削除（-173行）

### **孤児ポジションクリーンアップ**
- **OCO代替**: bitbank OCO非対応のため手動クリーンアップ実装
- **定期実行**: 取引サイクル毎に孤児ポジション検出・削除

### **柔軟クールダウン**
- **トレンド強度判定**: ADX 50%・DI 30%・EMA 20%の加重平均
- **閾値0.7**: 強度0.7以上でクールダウンスキップ・機会損失削減

## 🔗 関連ファイル・依存関係

### **参照元システム**
- `orchestrator.py`: PositionTracker/PositionLimits/CooldownManager初期化・依存注入
- `executor.py`: ポジション追跡・個別TP/SL配置

### **設定ファイル連携**
- `config/core/thresholds.yaml`: ポジション制限設定
- `config/core/features.yaml`: 柔軟クールダウン設定

---

**🎯 Phase 52.4-B完了**: デイトレード特化・個別TP/SL管理・シンプル設計回帰。Phase 46でレガシーコード削除（-173行）達成。設定管理統一・コード品質改善により保守性大幅向上。
