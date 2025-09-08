# src/trading/ - 取引実行・リスク管理層

AI自動取引システムの取引実行層。統合リスク管理・Kelly基準ポジションサイジング・ドローダウン管理・異常検知・注文実行を統合管理し、安全で効率的な取引実行を提供。

## 📂 ファイル構成

```
src/trading/
├── __init__.py              # 取引層エクスポート・公開API管理（230行）
├── executor.py              # 注文実行システム・ペーパートレード・実取引・統計管理（1000行）
├── risk_manager.py          # 統合リスク管理・Kelly基準ポジションサイジング（1400行）
└── risk_monitor.py          # 異常検知・ドローダウン管理統合システム（1400行）
```

## 🔧 主要コンポーネント

### **1. risk_manager.py（1400行）**
**目的**: 統合リスク管理・Kelly基準ポジションサイジング

**主要クラス**:
```python
class IntegratedRiskManager:
    def evaluate_trade_opportunity(ml_prediction, strategy_signal, market_data)  # 取引機会評価
    def _calculate_risk_score(evaluation_data)                                   # リスクスコア算出
    def _make_final_decision(risk_score)                                         # 最終判定

class KellyCriterion:
    def calculate_dynamic_position_size(balance, entry_price, atr_value)         # 動的ポジションサイズ
    def add_trade_result(profit_loss, strategy, confidence)                      # 取引結果記録
    
@dataclass
class TradeEvaluation:
    decision: RiskDecision              # APPROVED/CONDITIONAL/DENIED
    position_size: float                # 推奨ポジションサイズ
    risk_score: float                   # リスクスコア(0.0-1.0)
    recommended_action: str             # BUY/SELL/HOLD
```

**実装機能**:
- **統合リスク評価**: ML信頼度・ドローダウン・異常検知の総合判定
- **Kelly基準ポジションサイジング**: 数学的最適ポジションサイズ計算
- **3段階判定システム**: APPROVED（<0.6）・CONDITIONAL（0.6-0.8）・DENIED（≥0.8）
- **リスクスコア算出**: ML信頼度・異常・ドローダウン・連続損失・ボラティリティの重み付け統合

**使用例**:
```python
from src.trading import IntegratedRiskManager, RiskDecision

# リスク管理器の作成
risk_manager = IntegratedRiskManager(
    config=config,
    initial_balance=1000000
)

# 取引機会の評価
evaluation = risk_manager.evaluate_trade_opportunity(
    ml_prediction={'confidence': 0.8, 'action': 'buy'},
    strategy_signal={'strategy_name': 'atr_based', 'action': 'buy', 'confidence': 0.7},
    market_data=market_data,
    current_balance=1000000,
    bid=50000, ask=50100
)

print(f"判定: {evaluation.decision}")
print(f"ポジションサイズ: {evaluation.position_size}")
print(f"リスクスコア: {evaluation.risk_score:.3f}")
```

### **2. risk_monitor.py（1400行）**
**目的**: 異常検知・ドローダウン管理統合システム

**主要クラス**:
```python
class TradingAnomalyDetector:
    def comprehensive_anomaly_check(bid, ask, last_price, volume)                # 包括的異常検知
    def should_pause_trading()                                                   # 取引停止判定
    def _detect_spread_anomaly(bid, ask)                                        # スプレッド異常検知
    def _detect_price_spike(last_price, market_data)                            # 価格スパイク検知

class DrawdownManager:
    def update_balance(current_balance)                                         # 残高更新・監視
    def record_trade_result(profit_loss, strategy)                              # 取引結果記録
    def is_trading_allowed()                                                    # 取引許可判定
    def reset_if_needed()                                                       # 強制リセット機能

@dataclass
class AnomalyAlert:
    level: AnomalyLevel                 # WARNING/CRITICAL
    message: str                        # 異常内容
    metric_value: float                 # 測定値
```

**実装機能**:
- **異常検知**: スプレッド（0.3%警告・0.5%重大）・API遅延（1秒警告・3秒重大）・価格スパイク・出来高異常
- **ドローダウン管理**: 20%制限・連続損失5回制限・24時間クールダウン・強制リセット機能
- **取引状況管理**: ACTIVE/PAUSED_DRAWDOWN/PAUSED_CONSECUTIVE_LOSS/PAUSED_MANUAL
- **状態永続化**: JSON形式での状態保存・復元・破損検知

**使用例**:
```python
from src.trading import TradingAnomalyDetector, DrawdownManager

# 異常検知器
detector = TradingAnomalyDetector()
alerts = detector.comprehensive_anomaly_check(
    bid=50000, ask=50100,
    last_price=50050, volume=1000,
    api_latency_ms=500,
    market_data=market_data
)

# ドローダウン管理
dd_manager = DrawdownManager(max_drawdown_ratio=0.20)
drawdown, allowed = dd_manager.update_balance(950000)
if not allowed:
    print(f"取引停止: ドローダウン{drawdown:.1%}")
```

### **3. executor.py（1000行）**
**目的**: 注文実行システム・ペーパートレード・実取引・統計管理

**主要クラス**:
```python
class OrderExecutor:
    def execute_evaluation(evaluation)                                          # リスク評価結果の実行
    def execute_trade(action, position_size, current_price)                     # 取引実行
    def get_statistics()                                                        # 統計取得
    def _execute_paper_trade(action, position_size, stop_loss)                  # ペーパートレード

class VirtualPosition:
    def open_position(action, size, entry_price, stop_loss)                     # ポジション開始
    def close_position(exit_price)                                              # ポジション決済
    def update_position(current_price)                                          # ポジション更新

@dataclass
class ExecutionResult:
    success: bool                       # 実行成功
    order_id: Optional[str]             # 注文ID
    execution_time_ms: float            # 実行時間
    error_message: Optional[str]        # エラーメッセージ
```

**実装機能**:
- **ペーパートレード**: 仮想ポジション管理・リスクフリー検証・統計追跡
- **実取引モード**: Bitbank API統合・成行注文・30秒約定監視・自動キャンセル
- **レイテンシー監視**: 1秒目標・500ms警告・パフォーマンス追跡
- **統計管理**: 勝率・損益・シャープレシオ・CSV出力

**使用例**:
```python
from src.trading import create_order_executor

# ペーパートレード実行器作成
executor = create_order_executor(mode='paper', initial_balance=1000000)

# リスク評価結果の実行
if evaluation.decision == RiskDecision.APPROVED:
    result = executor.execute_evaluation(evaluation)
    print(f"注文実行: {result.order_id}")
    print(f"実行時間: {result.execution_time_ms}ms")

# 統計確認
stats = executor.get_statistics()
print(f"総損益: {stats.total_pnl:,.0f}円")
print(f"勝率: {stats.win_rate:.1%}")
```

### **4. __init__.py（230行）**
**目的**: 取引層エクスポート・公開API管理

**エクスポート機能**:
```python
# 統合API
from .risk_manager import (
    IntegratedRiskManager,
    KellyCriterion,
    TradeEvaluation,
    RiskDecision
)

# 監視システム
from .risk_monitor import (
    TradingAnomalyDetector,
    DrawdownManager,
    AnomalyAlert,
    TradingStatus
)

# 実行システム
from .executor import (
    OrderExecutor,
    create_order_executor,
    ExecutionResult,
    VirtualPosition
)
```

## 🚀 使用方法

### **統合取引実行フロー**
```python
from src.trading import (
    IntegratedRiskManager, 
    create_order_executor, 
    RiskDecision
)

# 1. リスク管理器の作成
risk_manager = IntegratedRiskManager(
    config=trading_config,
    initial_balance=1000000
)

# 2. 注文実行器の作成
executor = create_order_executor(
    mode='paper',  # or 'live'
    initial_balance=1000000
)

# 3. 取引機会の評価
evaluation = risk_manager.evaluate_trade_opportunity(
    ml_prediction=ml_prediction,
    strategy_signal=strategy_signal,
    market_data=market_data,
    current_balance=executor.current_balance
)

# 4. 承認された取引のみ実行
if evaluation.decision == RiskDecision.APPROVED:
    result = executor.execute_evaluation(evaluation)
    print(f"取引実行: {result.success}")
elif evaluation.decision == RiskDecision.CONDITIONAL:
    # 条件付き実行（監視強化）
    result = executor.execute_evaluation(evaluation, enhanced_monitoring=True)
else:
    # 取引拒否
    print(f"取引拒否: {evaluation.denial_reasons}")
```

### **個別コンポーネントの使用**

**リスク管理のみ**:
```python
from src.trading import IntegratedRiskManager

risk_manager = IntegratedRiskManager()
evaluation = risk_manager.evaluate_trade_opportunity(
    ml_prediction={'confidence': 0.7, 'action': 'buy'},
    strategy_signal={'strategy_name': 'atr_based', 'action': 'buy'},
    market_data=market_data
)
```

**異常検知のみ**:
```python
from src.trading import TradingAnomalyDetector

detector = TradingAnomalyDetector()
alerts = detector.comprehensive_anomaly_check(
    bid=50000, ask=50100, last_price=50050
)
```

**ドローダウン管理のみ**:
```python
from src.trading import DrawdownManager

dd_manager = DrawdownManager(max_drawdown_ratio=0.20)
allowed = dd_manager.is_trading_allowed()
```

## 🧪 テスト・品質保証

### **テスト実行**
```bash
# 取引システム全体テスト
bash scripts/testing/checks.sh

# 個別テスト実行
python -m pytest tests/unit/trading/ -v

# カバレッジ確認
python -m pytest tests/unit/trading/ --cov=src.trading
```

### **テスト構成**
- `test_executor.py`: 注文実行・ペーパートレード・統計管理テスト
- `test_risk_manager.py`: 統合リスク管理・Kelly基準テスト
- `test_risk_monitor.py`: 異常検知・ドローダウン管理テスト

### **品質指標**
- **テスト成功率**: 100%
- **コードカバレッジ**: 95%以上
- **実行時間**: 取引評価200ms以内・注文実行1秒以内

## ⚙️ 設定システム

### **デフォルト設定**
```python
from src.trading import DEFAULT_RISK_CONFIG, create_risk_manager

# デフォルト設定での作成
risk_manager = create_risk_manager()

# カスタム設定
custom_config = {
    "kelly_criterion": {
        "max_position_ratio": 0.03,     # 最大3%
        "safety_factor": 0.5,           # Kelly値の50%使用
        "min_trades_for_kelly": 20      # 20取引以上で適用
    },
    "drawdown_manager": {
        "max_drawdown_ratio": 0.20,     # 20%制限
        "consecutive_loss_limit": 5,    # 5回制限
        "cooldown_hours": 24            # 24時間停止
    },
    "anomaly_detector": {
        "spread_warning_threshold": 0.003,   # 0.3%警告
        "spread_critical_threshold": 0.005,  # 0.5%重大
        "api_latency_warning_ms": 1000,      # 1秒警告
        "api_latency_critical_ms": 3000      # 3秒重大
    }
}

risk_manager = create_risk_manager(config=custom_config)
```

## 📈 パフォーマンス指標

### **実行パフォーマンス**
- **リスク評価速度**: 50回評価0.5秒以内
- **注文実行レイテンシー**: 1秒目標・500ms警告
- **メモリ使用量**: 1000件履歴で10MB以下

### **リスク管理効果**
- **Kelly基準精度**: 数学的公式100%正確実装
- **ドローダウン制御**: リアルタイム監視・即座の制限適用
- **異常検知感度**: 偽陽性率10%以下・重大異常100%検知

### **安全性指標**
- **約定成功率**: 30秒以内約定・未約定自動キャンセル
- **API安定性**: レート制限遵守・認証エラー0件目標
- **状態永続化**: JSON形式・起動時自動復元

## ⚠️ 重要事項

### **資金管理の重要性**
- **Kelly基準の制限**: 50%安全係数・3%絶対上限の厳守
- **ドローダウン監視**: 20%制限の絶対遵守・手動介入可能
- **連続損失制御**: 5回制限での自動停止・感情的判断排除

### **安全機能**
- **ML信頼度**: 25%以下は自動拒否・品質依存性
- **市場データ品質**: データ品質がリスク判定に直結
- **3段階判定**: APPROVED/CONDITIONAL/DENIED の厳格な判定

### **本番運用準備**
- **バックテスト**: 過去データでの十分な検証必須
- **ペーパートレード**: 仮想取引での動作確認
- **段階的運用**: 少額から開始・徐々に規模拡大

### **依存関係**
- **外部ライブラリ**: pandas・numpy・ccxt・asyncio
- **内部依存**: src.core（設定・ログ・例外）・src.features（特徴量生成）
- **API依存**: Bitbank API・Discord Webhook

---

**取引実行・リスク管理層**: 統合リスク管理・Kelly基準ポジションサイジング・異常検知・ドローダウン管理・注文実行を統合した包括的な取引制御システム。3段階判定（APPROVED/CONDITIONAL/DENIED）による安全性重視の設計で、ペーパートレードから実取引まで対応。