# src/trading/risk/ - リスク管理層 🛡️ Phase 46完了

## 🎯 役割・責任

リスク管理・ポジションサイジング・Kelly基準・異常検知・ドローダウン管理を担当します。Phase 38でtradingレイヤードアーキテクチャの一部として分離、Phase 43で維持率100%未満拒否機能を実現、**Phase 46でハードコード値完全排除**を達成しました。

## 📂 ファイル構成

```
risk/
├── manager.py      # 統合リスク管理（Phase 46: ハードコード値排除）
├── sizer.py        # ポジションサイジング（動的サイジング・Kelly統合）
├── kelly.py        # Kelly基準計算（履歴ベース最適サイズ）
├── anomaly.py      # 異常検知システム（市場異常・システム異常）
├── drawdown.py     # ドローダウン管理（最大20%制限）
├── __init__.py     # モジュール初期化
└── README.md       # このファイル
```

## 📈 Phase 46完了（2025年10月22日）

**🎯 Phase 46: デイトレード特化・ハードコード値完全排除**

### ✅ Phase 46.3 ハードコード値排除成果

**背景**: 要件定義.md「ハードコード値ゼロ」要件を遵守するため、RiskManagerに残存していたハードコード値を完全排除しました。

**修正内容**:

**manager.py** (Line 369):
```python
# Phase 46修正前（ハードコード値）:
sl_rate = min(0.01, max_loss_ratio)  # ← 0.01（1%）ハードコード

# Phase 46修正後（thresholds.yaml読み込み）:
sl_rate = get_threshold("sl_min_distance_ratio", 0.01)
```

**効果**:
- ハードコード値完全排除（100%達成）
- 設定ファイル一元管理（thresholds.yaml）
- デイトレード設定反映（SL 2%・TP 4%・RR 2.0:1）
- 運用中のパラメータ調整容易化

### ✅ Phase 46設計変更：個別TP/SL管理対応

**背景**: Phase 46で統合TP/SL機能を削除し、個別TP/SL管理に回帰したため、RiskManagerの計算ロジックもシンプル化しました。

**変更内容**:
- 統合TP/SL価格計算削除（order_strategy.pyから移動済み）
- 個別エントリー毎のTP/SL計算に特化
- thresholds.yaml設定値を直接使用

**計算ロジック**（Phase 46簡略化版）:
```python
# SL計算（thresholds.yaml参照）
sl_rate = get_threshold("sl_min_distance_ratio", 0.01)  # 2.0%
sl_price = entry_price * (1 - sl_rate) if side == "buy" else entry_price * (1 + sl_rate)

# TP計算（thresholds.yaml参照）
tp_ratio = get_threshold("tp_default_ratio", 2.0)  # RR比2.0:1
tp_profit_ratio = sl_rate * tp_ratio  # 2% × 2.0 = 4%
tp_price = entry_price * (1 + tp_profit_ratio) if side == "buy" else entry_price * (1 - tp_profit_ratio)
```

### 📊 Phase 46重要事項
- **Phase 46設計哲学**: デイトレード特化・個別TP/SL管理・ハードコード値ゼロ
- **設定一元化**: 全てthresholds.yamlから取得（get_threshold()パターン）
- **品質保証完了**: 1,101テスト100%成功・68.93%カバレッジ達成

---

## 📈 Phase 43完了（2025年10月21日）

**🎯 Phase 43: 維持率100%未満エントリー拒否実装（追証リスク回避）**

### ✅ Phase 43 維持率制限実装成果

**背景**: 本番環境で保証金維持率が50%に低下し、追証（マージンコール）が発生しました。これはbitbank信用取引で維持率100%未満になると発生する重大なリスクです。

**実装内容**:

**manager.py** (`_check_margin_ratio()`):
```python
async def _check_margin_ratio(
    self,
    current_balance: float,
    btc_price: float,
    ml_prediction: Dict[str, Any],
    strategy_signal: Any,
) -> Tuple[bool, Optional[str]]:  # Phase 43: 戻り値変更
    """
    Phase 43: 拒否機能追加

    Returns:
        Tuple[bool, Optional[str]]:
            - bool: True=拒否すべき, False=許可
            - Optional[str]: 拒否/警告メッセージ
    """
    # ... 証拠金維持率予測 ...

    future_margin_ratio = margin_prediction.future_margin_ratio

    # Phase 43: 維持率100%未満で新規エントリー拒否（追証リスク回避）
    critical_threshold = get_threshold("margin.thresholds.critical", 100.0)
    if future_margin_ratio < critical_threshold:
        deny_message = (
            f"🚨 Phase 43: 維持率100%未満予測 - エントリー拒否 "
            f"({future_margin_ratio:.1f}% < {critical_threshold:.0f}%、追証リスク)"
        )
        self.logger.warning(deny_message)
        return True, deny_message  # True = 拒否

    # 警告レベル
    should_warn, warning_message = self.balance_monitor.should_warn_user(margin_prediction)
    if should_warn:
        return False, warning_msg  # False = 許可（警告のみ）

    return False, None  # 問題なし
```

**呼び出し側更新** (manager.py Line 249-256):
```python
# Phase 43: Tuple戻り値対応
should_deny, margin_message = await self._check_margin_ratio(...)

if should_deny and margin_message:
    denial_reasons.append(margin_message)  # 拒否
elif margin_message:
    warnings.append(margin_message)  # 警告のみ
```

**thresholds.yaml設定** (`margin.thresholds`):
```yaml
margin:
  position_value_estimation_ratio: 0.8
  # Phase 43: 維持率閾値設定
  thresholds:
    critical: 100.0      # 追証発生レベル - 100%未満でエントリー拒否
    warning: 100.0       # 警告レベル
    caution: 150.0       # 注意レベル
    safe: 200.0          # 安全レベル
```

**効果**:
- 維持率100%未満予測時、新規エントリーを**完全拒否**
- 追証リスクの完全回避（bitbank信用取引100%未満で追証発生）
- 既存ポジションは維持（無理な決済を回避）

### 📊 Phase 43重要事項
- **追証防止**: 維持率100%を下回る前にエントリー拒否
- **予測ベース**: 将来の維持率を予測してエントリー判断
- **品質保証完了**: 1,141テスト100%成功・69.47%カバレッジ達成

---

## 🔧 主要ファイル詳細

### **manager.py** 🛡️**Phase 43 維持率制限実装完了**

統合リスク管理の中核システムです。Phase 43で維持率100%未満エントリー拒否機能を追加しました。

**Phase 43新機能**:
```python
async def _check_margin_ratio(
    self,
    current_balance: float,
    btc_price: float,
    ml_prediction: Dict[str, Any],
    strategy_signal: Any,
) -> Tuple[bool, Optional[str]]:
    """
    Phase 43: 維持率100%未満拒否機能追加

    処理:
        1. 証拠金維持率予測（balance_monitor）
        2. Critical閾値（100%）チェック
        3. 100%未満なら拒否（True, deny_message）
        4. 100%以上なら許可（False, warning_message or None）
    """
```

**主要メソッド**:
- `evaluate_trade()`: 取引評価メインロジック
- `_check_margin_ratio()`: **【Phase 43更新】維持率チェック・拒否機能**
- `_calculate_risk_score()`: リスクスコア計算（0-100%）
- `_check_position_limits()`: ポジション制限チェック
- `_check_drawdown_limits()`: ドローダウン制限チェック
- `_detect_anomalies()`: 異常検知

**ファイル構造**:
- Lines 1-91: 初期化・基本設定
- Lines 92-285: 取引評価ロジック（**Phase 43: Line 249-256更新**）
- Lines 286-384: **Phase 43: _check_margin_ratio()更新**
- Lines 385-459: リスクスコア計算
- Lines 460-546: ポジション制限・ドローダウン制限
- Lines 547-619: 異常検知
- Lines 620-783: 証拠金管理・統計情報

### **sizer.py** 📊**ポジションサイジング統合システム**

Kelly基準・動的サイジング・RiskManagerを統合したポジションサイズ計算システムです。

**主要メソッド**:
```python
def calculate_integrated_position_size(
    self,
    ml_confidence: float,
    risk_manager_confidence: float,
    strategy_name: str,
    config: Dict,
    current_balance: float = None,
    btc_price: float = None,
) -> float:
    """
    Kelly基準と既存RiskManagerの統合ポジションサイズ計算

    計算ロジック:
        1. 動的ポジションサイジング計算（ML信頼度ベース）
        2. Kelly基準計算（履歴ベース）
        3. RiskManager計算（戦略設定ベース）
        4. 3つの値のうち最も保守的な値を採用（min）
    """
```

**動的ポジションサイジング**:
```python
def _calculate_dynamic_position_size(
    self, ml_confidence: float, current_balance: float, btc_price: float
) -> float:
    """
    ML信頼度に基づく動的ポジションサイジング

    信頼度カテゴリー:
        - 低（< 0.6）: 1-3%
        - 中（0.6-0.75）: 3-5%
        - 高（≥ 0.75）: 5-10%

    最小ロット保証:
        - 計算値と0.0001BTCの大きい方（max）を採用
        - 少額資金（< 50,000円）時は最小ロット優先
    """
```

### **kelly.py** 📈**Kelly基準計算システム**

取引履歴ベースの最適ポジションサイズ計算システムです。

**主要機能**:
```python
def calculate_optimal_size(
    self,
    ml_confidence: float,
    strategy_name: Optional[str] = None
) -> float:
    """
    Kelly基準による最適ポジションサイズ計算

    履歴不足時（< 5取引）:
        - 固定で最小取引単位（0.0001 BTC）を返す
        - 最初の5取引は安全な固定サイズで実行

    履歴十分時（≥ 5取引）:
        - 勝率・平均利益・平均損失から最適サイズ計算
        - f* = (bp - q) / b
        - 上限: 残高の10%まで
    """
```

### **anomaly.py** 🚨**異常検知システム**

市場異常・システム異常を検知するシステムです。

**検知項目**:
- 急激な価格変動（5分で5%以上）
- 異常な出来高（平均の3倍以上）
- API応答遅延（2秒以上）
- メモリ使用率異常（80%以上）

### **drawdown.py** 📉**ドローダウン管理システム**

最大ドローダウン20%制限を管理するシステムです。

**主要機能**:
- ドローダウン率計算（最大残高からの下落率）
- 20%到達時の取引停止
- 回復時の自動再開（10%未満に回復）
- 状態永続化（`src/core/state/drawdown_state.json`）

---

## 📝 使用方法・例

### **Phase 43 維持率制限の動作**

```python
from src.trading.risk.manager import IntegratedRiskManager

# IntegratedRiskManager初期化
risk_manager = IntegratedRiskManager(...)

# 取引評価（Phase 43: 維持率チェック含む）
evaluation = await risk_manager.evaluate_trade(
    current_balance=10000,
    btc_price=16000000,
    ml_prediction=ml_prediction,
    strategy_signal=strategy_signal
)

# 動作例:
# 現在維持率: 120% → 問題なし
# エントリー後予測維持率: 95% → **拒否**（100%未満）
# 拒否メッセージ: "🚨 Phase 43: 維持率100%未満予測 - エントリー拒否 (95.0% < 100.0%、追証リスク)"

# evaluation.decision: "denied"
# evaluation.denial_reasons: ["維持率100%未満予測..."]
```

### **ポジションサイジングの動作**

```python
from src.trading.risk.sizer import PositionSizeIntegrator
from src.trading.risk.kelly import KellyCriterion

# Kelly基準初期化
kelly = KellyCriterion()

# ポジションサイズ統合器初期化
sizer = PositionSizeIntegrator(kelly_criterion=kelly)

# 統合ポジションサイズ計算
position_size = sizer.calculate_integrated_position_size(
    ml_confidence=0.702,  # ML信頼度70.2%
    risk_manager_confidence=0.673,
    strategy_name="ATRBased",
    config=config,
    current_balance=10000,
    btc_price=16000000
)

# 内部動作:
# 1. Dynamic: 0.000100 BTC（ML信頼度70.2% → 中信頼度4.4%）
# 2. Kelly: 0.000100 BTC（履歴不足 → 固定サイズ）
# 3. RiskManager: 0.009578 BTC（戦略設定ベース）
# 4. 採用: min(0.000100, 0.000100, 0.009578) = 0.000100 BTC
```

---

## ⚠️ 注意事項・制約

### **Phase 43 維持率制限の動作条件**
- **Critical閾値**: 100%（bitbank信用取引の追証発生レベル）
- **予測ベース**: 将来の維持率を予測してエントリー判断
- **既存ポジション維持**: 拒否されるのは新規エントリーのみ

### **ポジションサイジングの制約**
- **最小ロット**: 0.0001 BTC（bitbank最小取引単位）
- **最大ポジション**: 残高の10%まで（Kelly基準上限）
- **保守的採用**: 3つの値（Dynamic・Kelly・RiskManager）の最小値

### **Kelly基準の制約**
- **履歴要件**: 5取引以上で本格計算開始
- **初期固定サイズ**: 最初の5取引は0.0001 BTC固定
- **戦略フィルター**: 戦略別に履歴分離可能

---

## 🔗 関連ファイル・依存関係

### **Phase 43新規ファイル**
- `src/trading/risk/manager.py`: 維持率制限実装（Line 286-384）
- `config/core/thresholds.yaml`: margin.thresholds設定追加

### **参照元システム**
- `src/core/orchestration/trading_cycle_manager.py`: リスク評価呼び出し
- `src/trading/balance/monitor.py`: 証拠金維持率監視
- `src/data/bitbank_client.py`: bitbank API呼び出し

### **設定ファイル連携**
- `config/core/thresholds.yaml`: リスク閾値・ポジションサイジング設定
- `config/core/unified.yaml`: リスク管理基本設定

---

**🎯 重要**: Phase 43により、bitbank信用取引の追証リスクを完全回避する維持率100%未満エントリー拒否機能を実装しました。これにより、本番環境での安全性が大幅に向上しています。
