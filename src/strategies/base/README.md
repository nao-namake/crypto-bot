# src/strategies/base/ - 戦略基盤システム

**Phase 52.4-B完了**: 全戦略の統一インターフェース・競合解決システム・重み付け統合による戦略アーキテクチャ基盤。

## 📂 ファイル構成

```
src/strategies/base/
├── __init__.py          # 基盤エクスポート（17行）
├── strategy_base.py     # 抽象基底クラス（294行）
└── strategy_manager.py  # 戦略統合管理（557行）
```

## 🔧 主要コンポーネント

### **strategy_base.py（294行）**

**目的**: 全戦略（ATRBased・DonchianChannel・ADXTrendStrength・BBReversal・StochasticReversal・MACDEMACrossover）が継承する統一基底クラス

**主要クラス**:
```python
@dataclass
class StrategySignal:
    strategy_name: str                      # 戦略名
    timestamp: datetime                     # シグナル発生時刻
    action: str                            # BUY/SELL/HOLD/CLOSE
    confidence: float                      # 信頼度 (0.0-1.0)
    strength: float                        # シグナル強度 (0.0-1.0)
    current_price: float                   # 現在価格
    stop_loss: Optional[float]             # ストップロス価格
    take_profit: Optional[float]           # 利確価格
    reason: Optional[str]                  # シグナル理由

class StrategyBase(ABC):
    def analyze(self, df: pd.DataFrame) -> StrategySignal      # 戦略固有分析（実装必須）
    def get_required_features(self) -> List[str]              # 必要特徴量（実装必須）
    def generate_signal(self, df: pd.DataFrame) -> StrategySignal  # 統一シグナル生成
```

### **strategy_manager.py（557行）**

**目的**: 6戦略統合管理・競合解決・重み付け統合による最終シグナル生成

**主要クラス**:
```python
class StrategyManager:
    def register_strategy(self, strategy: StrategyBase, weight: float = 1.0)    # 戦略登録
    def analyze_market(self, df: pd.DataFrame) -> StrategySignal              # 統合分析
    def update_strategy_weights(self, new_weights: Dict[str, float])          # 重み調整
```

## 🚀 使用例

```python
# 基本的な戦略実装
from src.strategies.base import StrategyBase, StrategySignal

class CustomStrategy(StrategyBase):
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        # 戦略固有分析ロジック
        decision = {
            'action': 'BUY',
            'confidence': 0.7,
            'strength': 0.6,
            'analysis': "戦略分析結果"
        }
        return self._create_signal(decision, df)

    def get_required_features(self) -> List[str]:
        return ['close', 'volume', 'rsi_14', 'atr_14', 'macd']

# 戦略マネージャーでの統合
from src.strategies.base import StrategyManager
from src.strategies.implementations import *

manager = StrategyManager()
manager.register_strategy(ATRBasedStrategy(), weight=1.0)
manager.register_strategy(DonchianChannelStrategy(), weight=1.0)
manager.register_strategy(ADXTrendStrengthStrategy(), weight=1.0)
manager.register_strategy(BBReversalStrategy(), weight=1.0)
manager.register_strategy(StochasticReversalStrategy(), weight=1.0)
manager.register_strategy(MACDEMACrossoverStrategy(), weight=1.0)

# 統合分析実行
market_data = get_market_data()  # 15特徴量データ
combined_signal = manager.analyze_market(market_data)
```

## 📊 競合解決システム

### **競合検知・解決フロー**

```
【各戦略並行実行】→ 個別StrategySignal生成（6戦略）
        ↓
【アクション別グループ化】→ {"buy": [...], "sell": [...], "hold": [...]}
        ↓
【競合検知】→ BUY vs SELL同時存在チェック
        ↓
競合なし → 多数決＋重み付け統合
競合あり → 重み付け信頼度比較＋閾値判定
        ↓
【最終統合シグナル】→ StrategySignal(strategy_name="StrategyManager")
```

**競合解決ロジック**:
```python
# ケース1: SELL 3 + HOLD 2 → 競合なし（積極的アクション優先）
action_counts = {"sell": 3, "hold": 2}
dominant_action = max(action_counts, key=action_counts.get)  # → "sell"

# ケース2: SELL 3 + BUY 2 → 競合あり（重み付け信頼度比較）
buy_weighted_confidence = self._calculate_weighted_confidence(buy_signals)
sell_weighted_confidence = self._calculate_weighted_confidence(sell_signals)

if abs(buy_weighted_confidence - sell_weighted_confidence) < 0.1:
    return self._create_hold_signal(df, reason="信頼度差が小さいためコンフリクト回避")
else:
    return winner_group_signal  # 高信頼度グループが勝利
```

### **重み付け信頼度計算**

```python
def _calculate_weighted_confidence(self, signals: List[Tuple[str, StrategySignal]]) -> float:
    total_weighted_confidence = 0.0
    total_weight = 0.0

    for strategy_name, signal in signals:
        weight = self.strategy_weights.get(strategy_name, 1.0)
        weighted_confidence = signal.confidence * weight

        total_weighted_confidence += weighted_confidence
        total_weight += weight

    return total_weighted_confidence / total_weight if total_weight > 0 else 0.0
```

## 🔧 設定

**環境変数**: 不要（設定ファイルから自動取得）
**データ要件**: 55特徴量統一・feature_order.json準拠・最小データ数20以上
**戦略重み**: ATRBased:1.0・DonchianChannel:1.0・ADXTrendStrength:1.0・BBReversal:1.0・StochasticReversal:1.0・MACDEMACrossover:1.0

## ⚠️ 重要事項

### **特性・制約**
- **統一インターフェース**: 全戦略がStrategyBase継承・StrategySignal統一形式
- **競合解決**: BUY vs SELL同時発生時の自動解決・安全性優先
- **重み付け統合**: 戦略別重みでの信頼度統合・パフォーマンス反映
- **55特徴量連携**: feature_order.json単一真実源との完全整合
- **Phase 52.4-B完了**: コード品質改善・6戦略システム・定数抽出
- **依存**: pandas・datetime・abc・typing・src.strategies.utils.*

---

**戦略基盤システム（Phase 52.4-B完了）**: 6戦略統一インターフェース・競合解決システム・重み付け統合による55特徴量連携戦略アーキテクチャ基盤。