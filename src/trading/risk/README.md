# src/trading/risk/ - リスク管理層 ⚖️ Phase 52.4-B完了

## 🎯 役割・責任

リスク管理・ポジションサイジング・Kelly基準・異常検知・ドローダウン管理を担当します。tradingレイヤードアーキテクチャの一部として、Phase 52.4-Bで設定管理完全統一・コード品質最適化を完了しました。

## 📂 ファイル構成

```
risk/
├── manager.py      # 統合リスク管理（Phase 52.4: 設定管理統一）
├── sizer.py        # ポジションサイジング（動的サイジング・Kelly統合）
├── kelly.py        # Kelly基準計算（履歴ベース最適サイズ）
├── anomaly.py      # 異常検知システム（市場異常・システム異常）
├── drawdown.py     # ドローダウン管理（最大20%制限）
├── __init__.py     # モジュール初期化
└── README.md       # このファイル
```

---

## 🔧 主要ファイル詳細（Phase 52.4-B完了）

### **manager.py**（872行・統合リスク管理）

統合リスク管理の中核システムです。

**主要メソッド**:
- `evaluate_trade()`: 取引評価メインロジック
- `_check_margin_ratio()`: 証拠金維持率チェック（80%未満でエントリー拒否）
- `_calculate_risk_score()`: リスクスコア計算（0-100%）
- `_check_position_limits()`: ポジション制限チェック
- `_check_drawdown_limits()`: ドローダウン制限チェック
- `_detect_anomalies()`: 異常検知

**証拠金維持率チェック**（Phase 52.4-B）:
```python
async def _check_margin_ratio(
    self,
    current_balance: float,
    btc_price: float,
    ml_prediction: Dict[str, Any],
    strategy_signal: Any,
) -> Tuple[bool, Optional[str]]:
    """
    証拠金維持率チェック（Phase 52.4-B: 80%未満で拒否）

    処理:
        1. 証拠金維持率予測（balance_monitor）
        2. Critical閾値（80%）チェック
        3. 80%未満なら拒否（True, deny_message）
        4. 80%以上なら許可（False, warning_message or None）

    Returns:
        Tuple[bool, Optional[str]]:
            - bool: True=拒否すべき, False=許可
            - Optional[str]: 拒否/警告メッセージ
    """
```

**ファイル構造**:
- Lines 1-91: 初期化・基本設定
- Lines 92-285: 取引評価ロジック
- Lines 286-384: 証拠金維持率チェック
- Lines 385-459: リスクスコア計算
- Lines 460-546: ポジション制限・ドローダウン制限
- Lines 547-619: 異常検知
- Lines 620-783: 証拠金管理・統計情報

### **sizer.py**（205行・ポジションサイジング統合）

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

### **kelly.py**（536行・Kelly基準計算）

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

### **anomaly.py**（267行・異常検知システム）

市場異常・システム異常を検知するシステムです。

**検知項目**:
- 急激な価格変動（5分で5%以上）
- 異常な出来高（平均の3倍以上）
- API応答遅延（2秒以上）
- メモリ使用率異常（80%以上）

### **drawdown.py**（310行・ドローダウン管理システム）

最大ドローダウン20%制限を管理するシステムです。

**主要機能**:
- ドローダウン率計算（最大残高からの下落率）
- 20%到達時の取引停止
- 回復時の自動再開（10%未満に回復）
- 状態永続化（`src/core/state/drawdown_state.json`）

---

## 📝 使用方法・例

### **証拠金維持率80%確実遵守の動作**

```python
# エントリー前の維持率チェック（自動実行）
should_deny, margin_message = await risk_manager._check_margin_ratio(
    current_balance=100000,  # 現在残高10万円
    btc_price=14000000,      # BTC価格1,400万円
    ml_prediction={"confidence": 0.6},
    strategy_signal=strategy_signal
)

# ログ出力例:
# 📊 Phase 52.4 維持率チェック: 現在=85.0%, 予測=75.0%, 閾値=80.0%
# 🚨 Phase 52.4: 維持率80.0%未満予測 - エントリー拒否 (現在=85.0% → 予測=75.0% < 80.0%)

if should_deny:
    # エントリー拒否（should_deny=True）
    return TradeEvaluation(side="hold", ...)
```

### **統合ポジションサイジングの動作**

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

### **証拠金維持率制限の動作条件**
- **Critical閾値**: 80%（Phase 52.4: 安全性重視設定）
- **予測ベース**: 将来の維持率を予測してエントリー判断
- **既存ポジション維持**: 拒否されるのは新規エントリーのみ
- **エラー時**: 安全第一（拒否）

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

### **主要ファイル**
- `src/trading/risk/manager.py`: 統合リスク管理（証拠金維持率チェック）
- `src/trading/risk/sizer.py`: ポジションサイジング統合
- `src/trading/risk/kelly.py`: Kelly基準計算
- `src/trading/risk/anomaly.py`: 異常検知
- `src/trading/risk/drawdown.py`: ドローダウン管理

### **参照元システム**
- `src/core/orchestration/trading_cycle_manager.py`: リスク評価呼び出し
- `src/trading/balance/monitor.py`: 証拠金維持率監視
- `src/data/bitbank_client.py`: bitbank API呼び出し

### **設定ファイル連携**
- `config/core/thresholds.yaml`: リスク閾値・ポジションサイジング設定
- `config/core/unified.yaml`: リスク管理基本設定

---

**🎯 Phase 52.4-B完了**: 設定管理完全統一・コード品質最適化・Phase参照統一により、保守性・可読性が大幅に向上しています。
