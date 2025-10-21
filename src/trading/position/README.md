# src/trading/position/ - ポジション管理層 🚀 Phase 46完了

## 🎯 役割・責任

ポジション追跡・制限管理・クリーンアップ・クールダウン制御を担当します。Phase 38でtradingレイヤードアーキテクチャの一部として分離、Phase 42で平均価格追跡機能、Phase 42.2でトレーリングSL/TP価格フィールド、Phase 42.4で統合TP/SL状態永続化を実装、**Phase 46でデイトレード特化・個別TP/SL管理に回帰**しました。

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

## 📈 Phase 42.4完了（2025年10月20日）

**🎯 Phase 42.4: 統合TP/SL状態永続化・Cloud Run再起動対応**

### ✅ Phase 42.4最適化成果
- **JSON状態永続化実装**: tracker.py lines 489-538に状態保存・復元機能追加
  ```python
  # 状態ファイルパス
  self.local_state_path = "src/core/state/consolidated_tp_sl_state.json"

  # 保存: set_consolidated_tp_sl_ids()呼び出し時に自動保存
  # 復元: __init__()時に自動復元
  ```

- **Cloud Run再起動時の状態維持**:
  - 従来の問題: メモリ内のみの状態管理 → Cloud Run再起動時に消失
  - Phase 42.4解決策: JSON永続化 → 再起動後も統合TP/SL ID維持
  - 効果: 22注文問題（既存TP/SLキャンセル失敗）の根本解決

- **保存内容**:
  ```json
  {
    "tp_order_id": "12345",
    "sl_order_id": "12346",
    "tp_price": 15970209,
    "sl_price": 16793416,
    "side": "sell",
    "average_entry_price": 16464133.0,
    "total_position_size": 0.0001
  }
  ```

- **自動保存・自動復元**:
  - `_save_state()`: 統合TP/SL設定時に自動保存（line 489-512）
  - `_load_state()`: 初期化時に自動復元（line 514-538）
  - `__init__()`: 起動時に自動的に状態復元を呼び出し（line 45）

- **品質保証完了**: 1,164テスト100%成功・69.58%カバレッジ達成

### 📊 Phase 42.4重要事項
- **drawdown_state.json設計踏襲**: 既存のドローダウン永続化と同じJSON設計パターン使用
- **Graceful Degradation**: 状態ファイル読み込み失敗時もシステム継続
- **後方互換性**: 既存のPhase 42/42.2機能と完全互換

## 📈 Phase 42.2完了（2025年10月18日）

**🎯 Phase 42.2: トレーリングSL/TP価格フィールド追加・価格追跡拡張**

### ✅ Phase 42.2最適化成果
- **トレーリングSL/TP価格フィールド追加**: PositionTracker拡張（tracker.py:34-37）
  ```python
  self._consolidated_tp_price: float = 0.0
  self._consolidated_sl_price: float = 0.0
  self._side: str = ""  # buy/sell（トレーリング判定用）
  ```

- **価格追跡機能拡張**: 統合TP/SL ID・価格取得/設定メソッド拡張
  - `get_consolidated_tp_sl_ids()`: TP/SL注文ID・価格取得（Phase 42.2拡張）
  - `set_consolidated_tp_sl_ids()`: TP/SL注文ID・価格設定（Phase 42.2拡張）
  - `get_consolidated_position_info()`: 統合ポジション情報取得（Phase 42.2拡張）

- **トレーリングストップ統合**: Phase 42.2トレーリングSL更新時の価格追跡
  - StopManager.update_trailing_stop_loss()が新SL価格をTrackerに保存
  - Executor.monitor_trailing_conditions()が価格情報を取得して判定

- **品質保証完了**: 1,081テスト100%成功・69.57%カバレッジ達成

### 📊 Phase 42.2重要事項
- **Phase 42基盤拡張**: 統合TP/SL価格追跡機能をトレーリング対応に拡張
- **Sentinel値対応**: `_UNSET`を使用してNone値による明示的クリアをサポート
- **後方互換性**: 既存の統合TP/SL機能を保持しつつ拡張

## 📈 Phase 42完了（2025年10月18日）

**🎯 Phase 42: 平均価格追跡・統合TP/SL対応**

### ✅ Phase 42最適化成果
- **平均価格追跡機能**: PositionTracker拡張（tracker.py:278-336）
  - 加重平均エントリー価格計算: `calculate_average_entry_price()`
  - 新規エントリー時更新: `update_average_on_entry()`
  - 決済時更新: `update_average_on_exit()`（全決済/部分決済対応）

- **統合TP/SL ID管理**: PositionTracker拡張（tracker.py:366-469）
  - 統合TP/SL注文ID取得/設定
  - 統合ポジション情報取得
  - 統合TP/SL情報クリア

- **複数エントリー対応**: 平均価格ベースの統合TP/SL実現
  - 従来: 3エントリー → 6注文（エントリー3 + TP3 + SL3）
  - Phase 42: 3エントリー → 5注文（エントリー3 + TP1 + SL1）

- **品質保証完了**: 1,081テスト100%成功・69.57%カバレッジ達成

### 📊 Phase 42重要事項
- **Phase 38基盤拡張**: レイヤードアーキテクチャに統合TP/SL機能を追加
- **後方互換性**: 個別TP/SLモード維持・段階的移行可能
- **Phase 42.2統合**: トレーリングストップ価格追跡に拡張

## 📈 Phase 37.5.3完了（2025年10月09日）

**🎯 Phase 37.5.3: 孤児ポジションクリーンアップ・OCO注文代替**

### ✅ Phase 37.5.3最適化成果
- **孤児ポジションクリーンアップ**: cleanup.py実装
  - ポジション決済後に残ったTP/SL注文を自動削除
  - bitbank OCO注文非対応の代替実装

## 📈 Phase 31.1完了（2025年10月02日）

**🎯 Phase 31.1: 柔軟クールダウン・トレンド強度ベース判定**

### ✅ Phase 31.1最適化成果
- **柔軟クールダウン実装**: cooldown.py実装
  - トレンド強度ベース判定（ADX 50%・DI 30%・EMA 20%）
  - 強度>=0.7でクールダウンスキップ・機会損失削減

## 📈 Phase 38完了（2025年10月11日）

**🎯 Phase 38: tradingレイヤードアーキテクチャ実装**

### ✅ Phase 38最適化成果
- **position層分離**: ポジション管理機能を独立層として分離
- **5層アーキテクチャ**: core/balance/execution/position/risk層による責務分離
- **テストカバレッジ向上**: 58.62% → 70.56%（+11.94ポイント）
- **保守性向上**: 4ファイル・平均300行/ファイル（適切な分割）

## 🔧 主要ファイル詳細

### **tracker.py** 🚀**Phase 42.2 価格追跡拡張完了**

ポジション追跡の中核システムです。Phase 42で平均価格追跡、Phase 42.2でトレーリングSL/TP価格フィールドを追加しました。

**Phase 42.2新機能**:
```python
class PositionTracker:
    def __init__(self):
        """PositionTracker初期化"""
        self.logger = get_logger()
        self.virtual_positions: List[Dict[str, Any]] = []

        # Phase 42: 統合TP/SL用追加フィールド
        self._average_entry_price: float = 0.0
        self._total_position_size: float = 0.0
        self._consolidated_tp_order_id: Optional[str] = None
        self._consolidated_sl_order_id: Optional[str] = None

        # Phase 42.2: トレーリングストップ用価格フィールド追加
        self._consolidated_tp_price: float = 0.0
        self._consolidated_sl_price: float = 0.0
        self._side: str = ""  # buy/sell（トレーリング判定用）

    def get_consolidated_tp_sl_ids(self) -> Dict[str, Any]:
        """
        統合TP/SL注文ID・価格取得（Phase 42・Phase 42.2拡張）

        Returns:
            Dict: {
                "tp_order_id": Optional[str],
                "sl_order_id": Optional[str],
                "tp_price": float,  # Phase 42.2追加
                "sl_price": float   # Phase 42.2追加
            }
        """

    def set_consolidated_tp_sl_ids(
        self,
        tp_order_id=_UNSET,
        sl_order_id=_UNSET,
        tp_price=_UNSET,      # Phase 42.2追加
        sl_price=_UNSET,      # Phase 42.2追加
        side=_UNSET           # Phase 42.2追加
    ) -> None:
        """
        統合TP/SL注文ID・価格設定（Phase 42・Phase 42.2拡張・Phase 42.2.7 None値対応）

        Args:
            tp_order_id: TP注文ID（None指定可能=クリア）
            sl_order_id: SL注文ID（None指定可能=クリア）
            tp_price: TP価格（0.0指定可能=クリア）      # Phase 42.2追加
            sl_price: SL価格（0.0指定可能=クリア）      # Phase 42.2追加
            side: ポジションサイド（空文字指定可能=クリア）  # Phase 42.2追加

        Note:
            Phase 42.2.7: Sentinel値（_UNSET）を使用して、
            「パラメータ未指定」と「Noneで明示的にクリア」を区別する。
        """

    def get_consolidated_position_info(self) -> Dict[str, Any]:
        """
        統合ポジション情報取得（Phase 42・Phase 42.2拡張）

        Returns:
            Dict: {
                "average_entry_price": float,
                "total_position_size": float,
                "tp_order_id": Optional[str],
                "sl_order_id": Optional[str],
                "tp_price": float,      # Phase 42.2追加
                "sl_price": float,      # Phase 42.2追加
                "side": str,            # Phase 42.2追加
                "position_count": int
            }
        """
```

**Phase 42新機能**:
```python
def calculate_average_entry_price(self) -> float:
    """
    加重平均エントリー価格計算（Phase 42）

    全ての仮想ポジションから加重平均価格を計算する。

    Returns:
        float: 加重平均エントリー価格（ポジションがない場合は0.0）
    """

def update_average_on_entry(self, price: float, amount: float) -> float:
    """
    新規エントリー時に平均価格更新（Phase 42）

    Args:
        price: 新規エントリー価格
        amount: 新規エントリー数量

    Returns:
        float: 更新後の平均エントリー価格

    計算式:
        new_average = (old_average × old_size + price × amount) / (old_size + amount)
    """

def update_average_on_exit(self, amount: float) -> float:
    """
    決済時に平均価格更新（Phase 42）

    Args:
        amount: 決済数量

    Returns:
        float: 更新後の平均エントリー価格（全決済時は0.0）

    処理:
        - 全決済: 平均価格リセット
        - 部分決済: 平均価格維持・サイズのみ減少
    """
```

**主要メソッド**:
- `add_position()`: ポジション追加
- `remove_position()`: ポジション削除
- `find_position()`: ポジション検索
- `calculate_average_entry_price()`: **【Phase 42新規】加重平均価格計算**
- `update_average_on_entry()`: **【Phase 42新規】エントリー時平均更新**
- `update_average_on_exit()`: **【Phase 42新規】決済時平均更新**
- `get_consolidated_tp_sl_ids()`: **【Phase 42新規・Phase 42.2拡張】TP/SL ID・価格取得**
- `set_consolidated_tp_sl_ids()`: **【Phase 42新規・Phase 42.2拡張】TP/SL ID・価格設定**

**ファイル構造**:
- Lines 1-273: 基本ポジション管理（追加・削除・検索）
- Lines 278-336: **【Phase 42】平均価格追跡メソッド**
- Lines 366-469: **【Phase 42・Phase 42.2】統合TP/SL管理メソッド**

### **limits.py**

ポジション制限管理の中核システムです。Phase 38で分離、Phase 31.1で柔軟クールダウン統合しました。

**主要メソッド**:
- `check_limits()`: ポジション管理制限チェック
- `_check_minimum_balance()`: 最小資金要件チェック
- `_check_cooldown()`: クールダウンチェック（Phase 31.1柔軟判定）
- `_check_max_positions()`: 最大ポジション数チェック
- `_check_capital_usage()`: 残高利用率チェック
- `_check_daily_trades()`: 日次取引回数チェック

### **cleanup.py** 🚀**Phase 37.5.3 孤児ポジション対策完了**

孤児ポジションクリーンアップの中核システムです。Phase 37.5.3でbitbank OCO非対応の代替実装を完成させました。

**Phase 37.5.3新機能**:
```python
async def cleanup_orphaned_positions(
    self,
    bitbank_client: Optional[BitbankClient] = None
) -> Dict[str, Any]:
    """
    Phase 37.5.3: 孤児ポジションクリーンアップ

    実際のポジションと仮想ポジションを照合し、
    消失したポジションのTP/SL注文を削除する。

    処理フロー:
        1. 実際のポジション取得
        2. 孤児ポジション検出
        3. TP/SL注文削除
        4. 仮想ポジション削除

    Returns:
        クリーンアップ結果
    """
```

**主要メソッド**:
- `cleanup_orphaned_positions()`: **【Phase 37.5.3新規】孤児ポジションクリーンアップ**
- `check_stale_positions()`: 古いポジション検出
- `emergency_cleanup()`: 緊急クリーンアップ

### **cooldown.py** 🚀**Phase 31.1 柔軟クールダウン完了**

クールダウン管理の中核システムです。Phase 31.1でトレンド強度ベース判定を実装しました。

**Phase 31.1新機能**:
```python
async def should_apply_cooldown(self, evaluation: TradeEvaluation) -> bool:
    """
    Phase 31.1: 柔軟なクールダウン判定

    強いトレンド発生時はクールダウンをスキップし、
    機会損失を防ぐ。

    処理:
        1. features.yaml設定確認
        2. トレンド強度計算（ADX・DI・EMA）
        3. 閾値判定（0.7以上でスキップ）

    Returns:
        bool: クールダウンを適用するか
    """

def calculate_trend_strength(self, market_data: Dict) -> float:
    """
    Phase 31.1: トレンド強度計算（ADX・DI・EMA総合判定）

    Args:
        market_data: 市場データ（特徴量含む）

    Returns:
        float: トレンド強度 (0.0-1.0)

    計算式:
        trend_strength = ADX(50%) + DI差分(30%) + EMAトレンド(20%)
    """
```

**主要メソッド**:
- `should_apply_cooldown()`: **【Phase 31.1新規】柔軟クールダウン判定**
- `calculate_trend_strength()`: **【Phase 31.1新規】トレンド強度計算**
- `get_cooldown_status()`: クールダウンステータス取得

## 📝 使用方法・例

### **Phase 42.2トレーリング価格追跡の動作**

```python
from src.trading.position.tracker import PositionTracker

# PositionTracker初期化
tracker = PositionTracker()

# Phase 42: エントリー時平均価格更新
average_price = tracker.update_average_on_entry(price=10000000.0, amount=0.001)

# Phase 42: 統合TP/SL配置後にID・価格を保存
tracker.set_consolidated_tp_sl_ids(
    tp_order_id="12345",
    sl_order_id="12346",
    tp_price=10250000.0,  # Phase 42.2追加
    sl_price=9800000.0,   # Phase 42.2追加
    side="buy"            # Phase 42.2追加
)

# Phase 42.2: トレーリングSL更新後に価格を更新
tracker.set_consolidated_tp_sl_ids(
    sl_price=10050000.0  # トレーリングSLが上昇
)

# Phase 42.2: 統合ポジション情報取得（トレーリング判定用）
info = tracker.get_consolidated_position_info()
print(f"Average Entry: {info['average_entry_price']:.0f}円")
print(f"TP Price: {info['tp_price']:.0f}円")
print(f"SL Price: {info['sl_price']:.0f}円")  # Phase 42.2で追跡可能
print(f"Side: {info['side']}")  # Phase 42.2で追跡可能
```

### **Phase 42平均価格追跡の動作**

```python
from src.trading.position.tracker import PositionTracker

# PositionTracker初期化
tracker = PositionTracker()

# 複数エントリー例
tracker.update_average_on_entry(price=10000000.0, amount=0.001)
# → 平均: 1000万円

tracker.update_average_on_entry(price=10100000.0, amount=0.001)
# → 平均: 1005万円（(1000万×0.001 + 1010万×0.001) / 0.002）

tracker.update_average_on_entry(price=10200000.0, amount=0.001)
# → 平均: 1010万円（(1005万×0.002 + 1020万×0.001) / 0.003）

# 統合TP/SL価格は1010万円ベースで計算される
```

## ⚠️ 注意事項・制約

### **Phase 42.2価格追跡の動作**
- **Sentinel値使用**: `_UNSET`を使用してNone値による明示的クリアをサポート
- **価格更新**: トレーリングSL更新時は`sl_price`のみ更新・他フィールドは維持
- **後方互換性**: Phase 42の統合TP/SL機能を保持しつつ拡張

### **Phase 42平均価格追跡の動作条件**
- **複数エントリー対応**: 加重平均価格計算で公平なTP/SL配置
- **部分決済対応**: 決済時は平均価格維持・サイズのみ減少
- **全決済時リセット**: 平均価格・サイズ・TP/SL IDをすべてリセット

### **Phase 37.5.3孤児ポジションクリーンアップの動作**
- **OCO代替**: bitbank OCO非対応のため手動クリーンアップ実装
- **定期実行**: 取引サイクル毎に孤児ポジション検出・削除
- **エラーハンドリング**: 注文キャンセル失敗時も継続

### **Phase 31.1柔軟クールダウンの動作**
- **トレンド強度判定**: ADX 50%・DI 30%・EMA 20%の加重平均
- **閾値0.7**: 強度0.7以上でクールダウンスキップ
- **機会損失削減**: 強トレンド時の取引機会確保

## 🔗 関連ファイル・依存関係

### **Phase 42.2新規ファイル**
- `src/trading/position/tracker.py`: 価格フィールド追加（lines 34-37）

### **Phase 42新規ファイル**
- `src/trading/position/tracker.py`: 平均価格追跡（lines 278-336）
- `src/trading/position/tracker.py`: 統合TP/SL管理（lines 366-469）

### **Phase 37.5.3新規ファイル**
- `src/trading/position/cleanup.py`: 孤児ポジションクリーンアップ

### **Phase 31.1新規ファイル**
- `src/trading/position/cooldown.py`: 柔軟クールダウン

### **参照元システム**
- `src/trading/execution/executor.py`: ポジション追跡・トレーリング監視
- `src/trading/execution/stop_manager.py`: TP/SL配置・トレーリングSL更新
- `src/core/execution/execution_service.py`: ポジション制限チェック

### **設定ファイル連携**
- `config/core/thresholds.yaml`: ポジション制限・クールダウン設定
- `config/core/features.yaml`: 柔軟クールダウン設定

---

**🎯 重要**: Phase 42.2により、トレーリングストップ対応の価格追跡機能を実装しました。Phase 42の平均価格追跡基盤を拡張し、複数エントリーに対するトレーリングSL/TP管理を実現しています。
