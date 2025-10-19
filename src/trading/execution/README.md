# src/trading/execution/ - 注文実行層 🚀 Phase 42.4完了

## 🎯 役割・責任

注文実行・TP/SL管理・トレーリングストップ実装を担当します。Phase 38でtradingレイヤードアーキテクチャの一部として分離、Phase 42で統合TP/SL実装、Phase 42.2でトレーリングストップ機能を完成、Phase 42.4でTP/SL設定最適化を実現しました。

## 📂 ファイル構成

```
execution/
├── executor.py         # 注文実行サービス（Phase 42, 42.2: 統合TP/SL・トレーリング実装）
├── stop_manager.py     # TP/SL管理（Phase 42, 42.2: 統合TP/SL・トレーリング実装）
├── order_strategy.py   # 注文戦略（Phase 42: 統合TP/SL価格計算）
├── __init__.py         # モジュール初期化
└── README.md           # このファイル
```

## 📈 Phase 42.4完了（2025年10月20日）

**🎯 Phase 42.4: TP/SL設定最適化・ハードコード値削除・デイトレード対応**

### ✅ Phase 42.4最適化成果
- **ハードコード値完全削除**: order_strategy.py lines 378-397のハードコード値をthresholds.yaml読み込みに変更
  - 修正前: `sl_rate = min(0.02, max_loss_ratio)` ← 2%ハードコード
  - 修正後: `sl_rate = sl_min_distance_ratio` ← thresholds.yaml参照
  - 修正前: `default_tp_ratio = tp_config.get("default_ratio", 2.5)` ← 2.5倍ハードコード
  - 修正後: `default_tp_ratio = get_threshold("tp_default_ratio", 1.5)` ← thresholds.yaml参照

- **TP/SL距離最適化**: 2025年市場ベストプラクティス準拠（BTC日次ボラティリティ2-5%対応）
  - **SL: 2.0%**（市場推奨3-8%の下限・証拠金1万円で最大損失200円）
  - **TP: 3.0%**（細かく利益確定・市場ボラティリティ中間値）
  - **RR比: 1.5:1**（勝率40%以上で収益化可能・現行MLモデルF1スコア0.56-0.61）

- **デイトレード段階的最適化**:
  - 当面はRR比1.5:1で実績収集
  - 将来的に2:1への移行を検討（勝率33.3%で収益化）
  - 市場データに基づく保守的アプローチ

- **品質保証完了**: 1,164テスト100%成功・69.58%カバレッジ達成

### 📊 Phase 42.4重要事項
- **設定値一元化**: TP/SL距離をthresholds.yamlで一元管理
- **Optuna最適化統合**: optimize_risk_management.py FIXED_TP_SL_PARAMS同期（Phase 40統合対応）
- **後方互換性**: 既存の統合TP/SL・トレーリングストップ機能と完全互換

## 📈 Phase 42.2完了（2025年10月18日）

**🎯 Phase 42.2: トレーリングストップ実装・Bybit/Binance準拠・含み益保護**

### ✅ Phase 42.2最適化成果
- **トレーリングストップ実装**: Bybit/Binance標準仕様準拠（executor.py:811-992, stop_manager.py:1083-1302）
  - 2%含み益でトレーリング開始（activation_profit: 0.02）
  - 3%距離（trailing_percent: 0.03）・Bybit/Binance標準・TP2.5%対応最適化
  - 200円最低更新距離（min_update_distance: 200）・ノイズ防止
  - 0.5%最低利益保証（min_profit_lock: 0.005）・SLがentry+0.5%を下回らない
  - SL>TP時にTPキャンセル（cancel_tp_when_exceeds: true）・さらなる上昇追従

- **含み益保護機能**: -450円損失防止（Phase 42.2有効化効果）
  - 背景: Phase 38で-451円損失（4.5%）発生
  - 対策: 2%含み益到達後、トレーリングSLが0.5%利益を保証
  - 効果: 含み益がある状態での大幅な損失を防止

- **TP超過キャンセル機能**: トレーリングSLがTPを超えた場合にTPを自動キャンセル
  - ロジック: `_cancel_tp_when_trailing_exceeds()`（executor.py:930-992）
  - 効果: TP2.5%を超える上昇時、さらなる利益追求を可能に
  - 安全性: トレーリングSLが最低利益を保証しているため安全

- **品質保証完了**: 1,081テスト100%成功・69.57%カバレッジ達成

### 📊 Phase 42.2重要事項
- **Bybit/Binance準拠**: 主要取引所と同じ仕様で実装・移植容易性確保
- **Phase 42統合**: 統合TP/SLシステムと完全統合・複数エントリー対応
- **設定有効化**: `config/core/thresholds.yaml:335 enabled: true`

## 📈 Phase 42完了（2025年10月18日）

**🎯 Phase 42: 統合TP/SL実装・複数エントリー対応・注文数削減**

### ✅ Phase 42最適化成果
- **統合TP/SL実装**: 複数エントリーの平均価格ベースで単一TP/SL注文を配置
  - 従来: 3エントリー → 6注文（エントリー3 + TP3 + SL3）
  - Phase 42: 3エントリー → 5注文（エントリー3 + TP1 + SL1）
  - 効果: 注文数削減・API呼び出し削減・コスト最適化

- **平均価格追跡**: PositionTracker拡張（tracker.py:278-336）
  - 加重平均エントリー価格計算
  - 新規エントリー時の平均価格更新
  - 決済時の平均価格更新（全決済/部分決済対応）

- **統合TP/SL配置**: StopManager拡張（stop_manager.py:879-1077）
  - 平均価格ベースのTP/SL価格計算
  - 既存TP/SL注文の自動キャンセル
  - 統合TP/SL注文の配置

- **品質保証完了**: 1,081テスト100%成功・69.57%カバレッジ達成

### 📊 Phase 42重要事項
- **後方互換性**: 個別TP/SLモード維持・段階的移行可能
- **Phase 42.2統合**: トレーリングストップと完全統合
- **注文管理改善**: OCO注文非対応のbitbank APIに最適化

## 📈 Phase 38完了（2025年10月11日）

**🎯 Phase 38: tradingレイヤードアーキテクチャ実装**

### ✅ Phase 38最適化成果
- **execution層分離**: 注文実行機能を独立層として分離
- **5層アーキテクチャ**: core/balance/execution/position/risk層による責務分離
- **テストカバレッジ向上**: 58.62% → 70.56%（+11.94ポイント）
- **保守性向上**: executor.py 1,008行・適切なファイル分割

## 🔧 主要ファイル詳細

### **executor.py** 🚀**Phase 42.2 トレーリングストップ実装完了**

注文実行サービスの中核システムです。Phase 42で統合TP/SL実装、Phase 42.2でトレーリングストップ機能を完成させました。

**Phase 42.2新機能**:
```python
async def monitor_trailing_conditions(
    self,
    bitbank_client: BitbankClient,
    current_price: float
) -> None:
    """
    Phase 42.2: トレーリングストップ条件監視・SL更新

    Args:
        bitbank_client: Bitbank APIクライアント
        current_price: 現在価格

    処理:
        1. 統合ポジション情報取得
        2. トレーリング条件判定（2%含み益以上）
        3. StopManager.update_trailing_stop_loss()呼び出し
        4. SL>TP時にTPキャンセル（_cancel_tp_when_trailing_exceeds）
    """

async def _cancel_tp_when_trailing_exceeds(
    self,
    bitbank_client: BitbankClient,
    current_sl_price: float
) -> None:
    """
    Phase 42.2: トレーリングSLがTP超過時にTPキャンセル

    Args:
        bitbank_client: Bitbank APIクライアント
        current_sl_price: 現在のトレーリングSL価格

    ロジック:
        - buy: SL > TP → TPキャンセル（SLが上昇してTPを超えた）
        - sell: SL < TP → TPキャンセル（SLが下降してTPを超えた）

    効果:
        - TP2.5%を超える上昇時、さらなる利益追求
        - トレーリングSLが0.5%最低利益を保証しているため安全
    """
```

**Phase 42新機能**:
```python
async def _handle_consolidated_tp_sl(
    self,
    bitbank_client: BitbankClient,
    evaluation: TradeEvaluation,
    entry_order_id: str,
    entry_price: float,
    entry_amount: float
) -> None:
    """
    Phase 42: 統合TP/SL処理（複数エントリー対応）

    処理フロー:
        1. 平均エントリー価格更新（PositionTracker）
        2. 既存TP/SL注文キャンセル（StopManager）
        3. 新しい統合TP/SL配置（平均価格ベース）
        4. 統合注文ID・価格をPositionTrackerに保存
    """
```

**主要メソッド**:
- `execute_order()`: 注文実行メインロジック
- `_handle_consolidated_tp_sl()`: **【Phase 42新規】統合TP/SL処理**
- `monitor_trailing_conditions()`: **【Phase 42.2新規】トレーリング条件監視**
- `_cancel_tp_when_trailing_exceeds()`: **【Phase 42.2新規】TP超過キャンセル**

**ファイル構造**:
- Lines 1-349: 初期化・基本設定
- Lines 350-362: TP/SLモード判定（individual/consolidated）
- Lines 450-806: ペーパートレード・ライブトレード実行
- Lines 665-806: **【Phase 42】統合TP/SL処理**
- Lines 811-992: **【Phase 42.2】トレーリングストップ監視**

### **stop_manager.py** 🚀**Phase 42.2 トレーリングストップ実装完了**

TP/SL管理の中核システムです。Phase 42で統合TP/SL実装、Phase 42.2でトレーリングストップ機能を完成させました。

**Phase 42.2新機能**:
```python
async def update_trailing_stop_loss(
    self,
    bitbank_client: BitbankClient,
    current_price: float,
    side: str,
    entry_price: float,
    current_sl_price: float,
    current_sl_order_id: Optional[str],
    total_position_size: float
) -> Dict[str, Any]:
    """
    Phase 42.2: トレーリングストップロス更新（Bybit/Binance準拠）

    Args:
        bitbank_client: Bitbank APIクライアント
        current_price: 現在価格
        side: ポジションサイド（buy/sell）
        entry_price: エントリー価格
        current_sl_price: 現在のSL価格
        current_sl_order_id: 現在のSL注文ID
        total_position_size: 総ポジションサイズ

    Returns:
        Dict: {
            "updated": bool,
            "new_sl_price": float,
            "new_sl_order_id": Optional[str],
            "reason": str
        }

    トレーリングロジック:
        1. 2%含み益でトレーリング開始（activation_profit: 0.02）
        2. 3%距離維持（trailing_percent: 0.03）
        3. 200円最低更新距離（ノイズ防止）
        4. 0.5%最低利益保証（min_profit_lock: 0.005）
    """
```

**Phase 42新機能**:
```python
async def place_consolidated_tp_sl(
    self,
    bitbank_client: BitbankClient,
    side: str,
    average_entry_price: float,
    total_position_size: float,
    tp_price: float,
    sl_price: float
) -> Dict[str, Any]:
    """
    Phase 42: 統合TP/SL配置（平均価格ベース）

    Args:
        bitbank_client: Bitbank APIクライアント
        side: ポジションサイド（buy/sell）
        average_entry_price: 加重平均エントリー価格
        total_position_size: 総ポジションサイズ
        tp_price: TP価格
        sl_price: SL価格

    Returns:
        Dict: {
            "tp_order_id": Optional[str],
            "sl_order_id": Optional[str],
            "success": bool
        }
    """

async def cancel_existing_tp_sl(
    self,
    bitbank_client: BitbankClient,
    tp_order_id: Optional[str],
    sl_order_id: Optional[str]
) -> None:
    """
    Phase 42: 既存TP/SL注文キャンセル

    Args:
        bitbank_client: Bitbank APIクライアント
        tp_order_id: キャンセルするTP注文ID
        sl_order_id: キャンセルするSL注文ID
    """
```

**主要メソッド**:
- `check_stop_conditions()`: TP/SL条件チェック（Phase 28基盤）
- `place_consolidated_tp_sl()`: **【Phase 42新規】統合TP/SL配置**
- `cancel_existing_tp_sl()`: **【Phase 42新規】既存TP/SLキャンセル**
- `update_trailing_stop_loss()`: **【Phase 42.2新規】トレーリングSL更新**
- `_should_update_trailing_stop()`: **【Phase 42.2新規】更新判定**
- `_calculate_new_trailing_stop_price()`: **【Phase 42.2新規】新SL価格計算**
- `_calculate_min_profit_lock_price()`: **【Phase 42.2新規】最低利益保証価格**

**ファイル構造**:
- Lines 1-86: TP/SL条件チェック（Phase 28基盤）
- Lines 87-219: 個別TP/SL配置（後方互換性維持）
- Lines 407-522: 緊急ストップロス（急激な価格変動対応）
- Lines 576-735: 孤児注文クリーンアップ（Phase 37.5.3・OCO代替）
- Lines 737-839: 柔軟クールダウン（Phase 31.1）
- Lines 879-1077: **【Phase 42】統合TP/SL専用メソッド**
- Lines 1083-1302: **【Phase 42.2】トレーリングストップ専用メソッド**

### **order_strategy.py** 🚀**Phase 42.4 TP/SL設定最適化完了**

注文戦略の中核システムです。Phase 42で統合TP/SL価格計算機能を追加、Phase 42.4でハードコード値削除・設定値最適化を実現しました。

**Phase 42.4最適化**:
```python
# Phase 42.4修正前（ハードコード値）:
sl_rate = min(0.02, max_loss_ratio)  # ← 2%ハードコード
default_tp_ratio = tp_config.get("default_ratio", 2.5)  # ← 2.5倍ハードコード

# Phase 42.4修正後（thresholds.yaml読み込み）:
from src.core.config import get_threshold

default_tp_ratio = get_threshold("tp_default_ratio", 1.5)
min_profit_ratio = get_threshold("tp_min_profit_ratio", 0.019)
default_atr_multiplier = get_threshold("sl_atr_normal_vol", 2.0)
sl_min_distance_ratio = get_threshold("sl_min_distance_ratio", 0.01)
max_loss_ratio = get_threshold("position_management.stop_loss.max_loss_ratio", 0.03)

# デフォルトSL率を設定から取得（ハードコード0.02削除）
sl_rate = sl_min_distance_ratio  # Phase 42.4: thresholds.yamlから直接取得
```

**Phase 42.4設定値（thresholds.yaml）**:
- `sl_min_distance_ratio: 0.02` （2.0%・市場推奨3-8%の下限）
- `tp_default_ratio: 1.5` （RR比1.5:1・段階的最適化アプローチ）
- `tp_min_profit_ratio: 0.03` （3.0%・デイトレード最適化）

**Phase 42新機能**:
```python
def calculate_consolidated_tp_sl_prices(
    average_entry_price: float,
    side: str,
    atr_value: float,
    config: Dict
) -> Tuple[float, float]:
    """
    Phase 42: 統合TP/SL価格計算（平均価格ベース）

    Args:
        average_entry_price: 加重平均エントリー価格
        side: ポジションサイド（buy/sell）
        atr_value: ATR値
        config: 設定辞書

    Returns:
        Tuple[float, float]: (TP価格, SL価格)

    計算ロジック:
        - TP: average_entry ± (average_entry × tp_rate)
        - SL: average_entry ± (atr_value × sl_atr_multiplier)
    """
```

**主要メソッド**:
- `determine_order_type()`: 注文タイプ決定（Phase 33スマート注文）
- `calculate_tp_sl_prices()`: 個別TP/SL価格計算
- `calculate_consolidated_tp_sl_prices()`: **【Phase 42新規】統合TP/SL価格計算**

## 📝 使用方法・例

### **Phase 42.2トレーリングストップの動作**

```python
from src.trading.execution.executor import ExecutionService
from src.data.bitbank_client import BitbankClient

# ExecutionService初期化
executor = ExecutionService(mode="live")

# トレーリング条件監視（取引サイクル毎に実行）
await executor.monitor_trailing_conditions(
    bitbank_client=bitbank_client,
    current_price=14000000.0  # 現在価格: 1400万円
)

# トレーリング動作例:
# Entry: 1000万円
# Current: 1020万円（+2%含み益） → トレーリング開始
# Trailing SL: 989.7万円（1020万円 × 0.97 = 3%距離）
# Min Profit Lock: 1005万円（1000万円 × 1.005 = 0.5%利益保証）
# → 実際のSL: max(989.7万円, 1005万円) = 1005万円

# さらに上昇:
# Current: 1050万円（+5%含み益）
# Trailing SL: 1018.5万円（1050万円 × 0.97 = 3%距離）
# Min Profit Lock: 1005万円（変わらず）
# → 実際のSL: 1018.5万円（200円以上の更新のため更新実行）

# TP超過:
# TP: 1025万円（2.5%）
# Trailing SL: 1018.5万円 > TP → TPキャンセル
# → さらなる上昇を追従可能
```

### **Phase 42統合TP/SLの動作**

```python
from src.trading.execution.executor import ExecutionService

# ExecutionService初期化
executor = ExecutionService(mode="live")

# エントリー実行（自動的に統合TP/SL処理）
result = await executor.execute_order(
    bitbank_client=bitbank_client,
    evaluation=evaluation,
    mode="live"
)

# 内部動作:
# 1. エントリー注文実行（例: 1000万円で0.001 BTC買い）
# 2. PositionTracker.update_average_on_entry()呼び出し
# 3. 既存TP/SL注文キャンセル
# 4. 新しい統合TP/SL配置（平均価格ベース）
# 5. 統合注文ID・価格をTrackerに保存

# 複数エントリー例:
# Entry 1: 1000万円で0.001 BTC → 平均: 1000万円
# Entry 2: 1010万円で0.001 BTC → 平均: 1005万円
# Entry 3: 1020万円で0.001 BTC → 平均: 1010万円
# → TP/SLは1010万円（平均価格）ベースで計算
```

## ⚠️ 注意事項・制約

### **Phase 42.2トレーリングストップの動作条件**
- **有効化必須**: `config/core/thresholds.yaml:335 enabled: true`
- **2%起動閾値**: 2%含み益到達でトレーリング開始
- **3%距離**: Bybit/Binance標準・TP2.5%対応最適化
- **200円最低更新**: ノイズによる頻繁なSL更新を防止
- **0.5%利益保証**: SLがentry+0.5%を下回らない

### **TP超過キャンセルの安全性**
- **最低利益保証**: トレーリングSLが0.5%利益を保証
- **リスク管理**: TP2.5% < Trailing SL（例: 3%）の場合のみキャンセル
- **手動介入可能**: 必要に応じて手動でTPを再設定可能

### **Phase 42統合TP/SLの動作条件**
- **複数エントリー対応**: 平均価格ベースで単一TP/SL配置
- **個別モード維持**: 後方互換性のため個別TP/SLモードも利用可能
- **OCO非対応対策**: bitbank APIの制限に最適化された実装

### **Phase 38 Graceful Degradation統合**
- **エラーハンドリング**: TP/SL配置失敗時も取引続行
- **孤児注文クリーンアップ**: Phase 37.5.3で実装済み
- **柔軟クールダウン**: Phase 31.1で実装済み

## 🔗 関連ファイル・依存関係

### **Phase 42.2新規ファイル**
- `src/trading/execution/executor.py`: トレーリング監視（lines 811-992）
- `src/trading/execution/stop_manager.py`: トレーリングSL更新（lines 1083-1302）
- `config/core/thresholds.yaml`: トレーリング設定（lines 334-340）

### **Phase 42新規ファイル**
- `src/trading/execution/executor.py`: 統合TP/SL処理（lines 665-806）
- `src/trading/execution/stop_manager.py`: 統合TP/SL配置（lines 879-1077）
- `src/trading/execution/order_strategy.py`: 統合価格計算（lines 352-467）

### **参照元システム**
- `src/core/execution/execution_service.py`: 注文実行制御
- `src/trading/position/tracker.py`: ポジション追跡・平均価格管理
- `src/data/bitbank_client.py`: bitbank API呼び出し

### **設定ファイル連携**
- `config/core/thresholds.yaml`: TP/SL・トレーリングストップ設定
- `config/core/unified.yaml`: 注文実行設定

---

**🎯 重要**: Phase 42.2により、Bybit/Binance準拠のトレーリングストップ機能を実装しました。Phase 42の統合TP/SLシステムと完全統合し、複数エントリーに対する含み益保護を実現しています。
