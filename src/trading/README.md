# src/trading/ - 統合取引管理層

**Phase 28完了・Phase 29最適化版**: 統合リスク管理・Kelly基準ポジションサイジング・ドローダウン管理・異常検知・取引実行結果管理を統合し、安全で効率的な取引制御を提供。

## 📂 ファイル構成

```
src/trading/
├── __init__.py              # 取引層エクスポート・公開API管理（237行）
├── execution_service.py     # 取引実行サービス・ExecutionServiceProtocol実装（1,213行）
├── margin_monitor.py        # 保証金監視システム（399行）
├── risk_manager.py          # 統合リスク管理・Kelly基準・保証金監視統合（1,805行）
└── risk_monitor.py          # 異常検知・ドローダウン管理統合システム（1,322行）
```

## 🔧 主要コンポーネント

### **1. risk_manager.py（1,805行）**

**目的**: 統合リスク管理・Kelly基準ポジションサイジング・取引実行結果管理

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

@dataclass
class ExecutionResult:
    success: bool                       # 実行成功/失敗
    mode: ExecutionMode                 # PAPER/LIVE
    order_id: Optional[str]             # 注文ID
    status: OrderStatus                 # 注文状態
```

**実装機能**:
- **統合リスク評価**: ML信頼度・ドローダウン・異常検知の総合判定
- **Kelly基準ポジションサイジング**: 数学的最適ポジションサイズ計算
- **ML信頼度連動動的ポジションサイジング**: 低信頼度1-3%・中信頼度3-5%・高信頼度5-10%
- **資金規模別調整**: 小口座（1-5万円）・中規模（5-10万円）・大口座（10万円以上）対応
- **3段階判定システム**: APPROVED（<0.6）・CONDITIONAL（0.6-0.8）・DENIED（≥0.8）
- **取引実行結果管理**: 注文実行結果の統合処理・ペーパートレード/ライブ取引対応

**使用例**:
```python
from src.trading import IntegratedRiskManager

# リスク管理器の作成
risk_manager = IntegratedRiskManager(config=config, initial_balance=1000000)

# 取引機会の評価
evaluation = risk_manager.evaluate_trade_opportunity(
    ml_prediction={'confidence': 0.8, 'action': 'buy'},
    strategy_signal={'strategy_name': 'atr_based', 'action': 'buy', 'confidence': 0.7},
    market_data=market_data,
    current_balance=1000000,
    bid=50000, ask=50100
)
```

### **2. margin_monitor.py（399行）**

**目的**: 保証金維持率監視・警告機能

**主要クラス**:
```python
class MarginMonitor:
    def calculate_current_margin_ratio(balance, open_positions)                  # 現在の維持率計算
    def calculate_projected_margin_ratio(balance, new_position_value)           # 新規ポジション後の予測維持率
    def get_margin_status(margin_ratio)                                         # 状態判定（SAFE/CAUTION/WARNING/CRITICAL）
```

**実装機能**:
- **保証金維持率計算**: 現在の保証金状況を数値化
- **新規ポジション影響予測**: 追加取引による維持率変化の計算
- **4段階状態判定**: SAFE（100%以上）・CAUTION（80-100%）・WARNING（50-80%）・CRITICAL（50%未満）
- **Discord通知連携**: 危険な維持率の自動通知

### **3. execution_service.py（1,213行）**

**目的**: 取引実行サービス・ExecutionServiceProtocol実装

**主要クラス**:
```python
class ExecutionService:
    async def execute_trade(evaluation: TradeEvaluation) -> ExecutionResult     # 統一取引実行
    async def _execute_live_trade(evaluation)                                   # ライブ取引実行
    async def _execute_paper_trade(evaluation)                                  # ペーパー取引実行
    async def _execute_backtest_trade(evaluation)                               # バックテスト取引実行
    async def check_stop_conditions()                                           # ストップ条件チェック
```

**実装機能**:
- **3モード対応**: ライブ・ペーパー・バックテスト取引の統一実行
- **テイクプロフィット/ストップロス**: 自動利確・損切り機能
- **指値注文最適化**: 市場状況に応じた注文戦略
- **緊急停止機能**: 異常な価格変動・システム異常時の自動停止
- **ポジション制限**: 最大3ポジション・1日20取引制限

### **4. risk_monitor.py（1,322行）**

**目的**: 異常検知・ドローダウン管理統合システム

**主要クラス**:
```python
class TradingAnomalyDetector:
    def detect_spread_anomaly(bid, ask)                                         # スプレッド異常検知
    def detect_api_latency_anomaly(response_time)                               # API遅延検知
    def detect_price_spike(current_price, historical_prices)                    # 価格スパイク検知

class DrawdownManager:
    def update_equity(current_balance)                                          # 資産変動記録
    def check_drawdown_limit()                                                  # ドローダウン制限チェック
    def check_consecutive_losses()                                              # 連続損失チェック
```

**実装機能**:
- **異常検知システム**: スプレッド・API遅延・価格スパイクの自動検知
- **ドローダウン管理**: 最大20%ドローダウン・連続5損失で自動停止
- **取引状況監視**: ACTIVE/PAUSED状態管理・自動復旧機能
- **リスク状態永続化**: JSON形式での状態保存・復元

## 🚀 使用方法

### **統合リスク管理システム**

```python
from src.trading import create_risk_manager

# リスクプロファイル別の管理器作成
conservative_manager = create_risk_manager(risk_profile="conservative")
balanced_manager = create_risk_manager(risk_profile="balanced")
aggressive_manager = create_risk_manager(risk_profile="aggressive")

# 取引評価の実行
evaluation = balanced_manager.evaluate_trade_opportunity(
    ml_prediction=ml_result,
    strategy_signal=strategy_result,
    market_data=current_market_data,
    current_balance=account_balance,
    bid=current_bid,
    ask=current_ask
)

# 結果に基づく取引実行
if evaluation.decision == RiskDecision.APPROVED:
    execution_result = await execution_service.execute_trade(evaluation)
```

### **異常検知・ドローダウン管理**

```python
from src.trading import TradingAnomalyDetector, DrawdownManager

# 異常検知システム
anomaly_detector = TradingAnomalyDetector()
alerts = anomaly_detector.check_all_anomalies(market_data)

# ドローダウン管理
drawdown_manager = DrawdownManager()
drawdown_manager.update_equity(current_balance)
trading_status = drawdown_manager.get_trading_status()
```

## ⚙️ 設定管理

### **リスクプロファイル**

- **conservative**: 保守的（最大5%ポジション・高い安全係数）
- **balanced**: バランス型（最大10%ポジション・標準設定）
- **aggressive**: 積極的（最大20%ポジション・効率重視）

### **動的設定取得**

```python
from src.core.config import get_threshold

# 設定値の動的取得（thresholds.yaml）
min_confidence = get_threshold("trading.risk_thresholds.min_ml_confidence", 0.3)
max_position_ratio = get_threshold("trading.kelly_criterion.max_position_ratio", 0.1)
```

## 🧪 テスト・品質保証

```bash
# 取引システム完全テスト
python -m pytest tests/unit/trading/ -v

# 特定コンポーネントテスト
python -m pytest tests/unit/trading/test_risk_manager.py -v          # リスク管理（45テスト）
python -m pytest tests/unit/trading/test_execution_service.py -v     # 取引実行（23テスト）
python -m pytest tests/unit/trading/test_risk_monitor.py -v          # リスク監視（38テスト）
```

**品質指標**:
- **テスト成功率**: 100%
- **リスク評価時間**: 50ms以下
- **取引実行時間**: 200ms以下
- **メモリ使用量**: コンポーネントあたり15MB以下

## ⚠️ 重要事項

### **安全性確保**
- **資金保全最優先**: 複数レベルのリスクチェック・フォールバック機能
- **段階的リスク制御**: 3段階判定（APPROVED/CONDITIONAL/DENIED）
- **緊急停止機能**: 異常検知時の自動取引停止・手動復旧

### **設定管理**
- **統一設定ファイル**: config/core/thresholds.yaml一元管理
- **動的設定反映**: 再起動不要の設定変更
- **プロファイル切替**: 運用状況に応じたリスクレベル調整

### **特性・制約**
- **Kelly基準**: 理論的最適ポジションサイズ・安全係数適用
- **ML信頼度連動**: 低信頼度保守的・高信頼度積極的な動的調整
- **資金規模対応**: 1万円〜50万円の段階的運用対応
- **本番稼働中**: 24時間Cloud Run稼働・Discord監視連携
- **Phase 29最適化**: 実用性重視・保守性向上・システム安定性確保

---

**統合取引管理層（Phase 28完了・Phase 29最適化）**: 統合リスク管理・Kelly基準ポジションサイジング・異常検知・ドローダウン管理・取引実行結果処理による包括的取引制御システム。