# src/strategies/base/ - 戦略基盤システム

## 🎯 役割・責任

全戦略が継承する抽象基底クラスと複数戦略の統合管理を提供します。5つの戦略（ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength）の統一インターフェース・競合解決システム・重み付け統合により、一貫性のある戦略アーキテクチャを実現します。15特徴量統一システムとの連携により、全システムでの整合性を保証します。

### 設計原則
- **統一インターフェース**: 全戦略が共通の規約に従う
- **抽象化**: 戦略固有ロジックと共通処理の明確な分離
- **拡張性**: 新戦略の追加が容易な設計
- **15特徴量統一**: feature_order.json単一真実源との連携

## 🎯 含まれるコンポーネント

### 1. StrategyBase (`strategy_base.py`)
**役割**: すべての戦略が継承する抽象基底クラス

#### StrategySignal データクラス
```python
@dataclass
class StrategySignal:
    # 基本情報
    strategy_name: str           # 戦略名
    timestamp: datetime          # シグナル発生時刻
    
    # シグナル内容
    action: str                  # BUY/SELL/HOLD/CLOSE
    confidence: float            # 信頼度 (0.0-1.0)
    strength: float              # シグナル強度 (0.0-1.0)
    
    # 価格・リスク管理
    current_price: float         # 現在価格
    stop_loss: Optional[float]   # ストップロス価格
    take_profit: Optional[float] # 利確価格
    position_size: Optional[float] # ポジションサイズ
    
    # 詳細情報
    reason: Optional[str]        # シグナル理由
    metadata: Optional[Dict]     # その他メタデータ
```

#### StrategyBase 抽象クラス
```python
class StrategyBase(ABC):
    def __init__(self, name: str, config: Optional[Dict] = None):
        # 共通初期化処理
        
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        # 戦略固有の分析ロジック（実装必須）
        pass
        
    @abstractmethod
    def get_required_features(self) -> List[str]:
        # 必要特徴量リスト（実装必須）
        pass
        
    def generate_signal(self, df: pd.DataFrame) -> StrategySignal:
        # 統一シグナル生成プロセス（共通処理）
        pass
```

**提供機能**:
- **入力データ検証**: 必要特徴量・最小データ数確認
- **パフォーマンス追跡**: 成功率・シグナル履歴管理
- **エラーハンドリング**: 統一されたエラー処理
- **ログ管理**: 戦略固有ログの体系的記録

### 2. StrategyManager (`strategy_manager.py`)
**役割**: 複数戦略の統合管理・シグナル統合

#### 戦略管理機能
```python
class StrategyManager:
    def register_strategy(self, strategy: StrategyBase, weight: float = 1.0):
        # 戦略の登録・重み設定
        
    def analyze_market(self, df: pd.DataFrame) -> StrategySignal:
        # 全戦略実行・統合シグナル生成
        
    def update_strategy_weights(self, new_weights: Dict[str, float]):
        # 動的重み調整
```

**提供機能**:
- **戦略登録管理**: 戦略の追加・削除・有効化制御
- **重み付け統合**: 戦略別重みでの信頼度統合
- **コンフリクト解決**: 相反シグナルの自動解決
- **パフォーマンス監視**: 戦略別成績追跡

## 🎯 StrategyManager詳細システム

### **競合解決メカニズム**

**競合検知ロジック**:
```python
def _has_signal_conflict(self, signal_groups):
    has_buy = "buy" in signal_groups and len(signal_groups["buy"]) > 0
    has_sell = "sell" in signal_groups and len(signal_groups["sell"]) > 0
    return has_buy and has_sell  # BUYとSELLが同時にある場合のみ競合
```

**ケース別処理**:

**1. SELL 3 + HOLD 2 → 競合なし**
```python
# _integrate_consistent_signals で処理
action_counts = {"sell": 3, "hold": 2}
dominant_action = max(action_counts, key=action_counts.get)  # → "sell"
# 結果: SELL選択（積極的アクション優先）
```

**2. SELL 3 + BUY 2 → 競合あり**
```python
# _resolve_signal_conflict で処理
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

### **統合シグナル生成フロー**

```
【各戦略並行実行】→ 個別StrategySignal生成（5戦略）
        ↓
【アクション別グループ化】→ {"buy": [...], "sell": [...], "hold": [...]}
        ↓  
【競合検知】→ BUY vs SELL同時存在チェック
        ↓
4-A. 競合なし → _integrate_consistent_signals（多数決＋重み付け）
4-B. 競合あり → _resolve_signal_conflict（重み付け信頼度比較）
        ↓
【最終統合シグナル生成】→ StrategySignal(strategy_name="StrategyManager")
```

### **動的信頼度実装**

```python
# 動的confidence計算（市場状況反映）
base_confidence = get_threshold("ml.dynamic_confidence.base_hold", 0.3)

# 市場ボラティリティに応じた調整
if volatility > 0.02:  # 高ボラティリティ
    confidence = base_confidence * 0.8  # 信頼度を下げる
elif volatility < 0.005:  # 低ボラティリティ  
    confidence = base_confidence * 1.2  # 信頼度を上げる
```

**💡 重要ポイント**:
- StrategyManagerは統合シグナル生成のみ担当
- 実際の取引実行判定はリスクマネージャーが別途実施
- 競合回避システムで安全性を最優先
- 動的信頼度で市場状況を反映

## 🔄 戦略基盤システム改善済み

### 戦略基底クラスの強化
```python
# Before: 各戦略で個別の基盤実装
class ATRBasedStrategy:
    def __init__(self):
        self.logger = None  # 個別実装
        self.signal_history = []  # 個別管理
        self.performance_stats = {}  # 戦略ごとに異なる形式
    
    def analyze(self, df):
        # バラバラな検証処理
        if len(df) < 20:  # ハードコード
            raise ValueError("データ不足")  # 統一されていない
```

```python
# After: 統一された基盤クラス
class ATRBasedStrategy(StrategyBase):  # 基底クラス継承
    def analyze(self, df):
        # 共通の前処理・後処理は基底クラスが担当
        # 戦略固有ロジックのみ実装
        pass
```

### 戦略マネージャーの簡素化
```python
# Before: 複雑な統合ロジック
class StrategyManager:
    def analyze_market(self, df):
        # 複雑な重み計算・コンフリクト解決
        # 詳細な履歴管理・統計処理
        # 200行以上の処理

# After: シンプルで効果的な統合
class StrategyManager:  # 本番運用移行・システム最適化
    def analyze_market(self, df):
        # シンプルな重み付け統合
        # 効率的なコンフリクト解決
        # 必要十分な統計管理
```

## 📊 アーキテクチャ図

```
┌─────────────────────────────────────────────────────────────┐
│                    StrategyManager                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Strategy Orchestration              │    │
│  │  - 戦略登録管理                                      │    │
│  │  - 重み付け統合                                      │    │
│  │  - コンフリクト解決                                  │    │
│  │  - パフォーマンス監視                                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────┬───────────────────┬──────────────────────┘
                  │                   │
        ┌─────────▼────────┐   ┌──────▼─────────┐
        │   StrategyBase   │   │   StrategyBase │
        │   (Abstract)     │   │   (Abstract)   │
        └─────────┬────────┘   └──────┬─────────┘
                  │                   │
        ┌─────────▼────────┐   ┌──────▼─────────┐
        │   ATRBased       │   │  MochipoyAlert │
        │   Strategy       │   │   Strategy     │
        └──────────────────┘   └────────────────┘
        
        ┌──────────────────┐   ┌────────────────┐   ┌──────────────────┐
        │  MultiTimeframe  │   │ DonchianChannel│   │ ADXTrendStrength │
        │    Strategy      │   │   Strategy     │   │    Strategy      │
        └──────────────────┘   └────────────────┘   └──────────────────┘
```

## 🔧 使用方法

### 新戦略の実装
```python
from ..base.strategy_base import StrategyBase, StrategySignal
from ..utils import EntryAction, SignalBuilder, StrategyType

class CustomStrategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__(name="Custom", config=config)
    
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        # 戦略固有分析ロジック
        decision = {
            'action': EntryAction.BUY,
            'confidence': 0.7,
            'strength': 0.6,
            'analysis': "カスタム分析結果"
        }
        
        # 共通のシグナル生成（リスク管理統合済み）
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=float(df['close'].iloc[-1]),
            df=df,
            config=self.config,
            strategy_type=StrategyType.CUSTOM
        )
    
    def get_required_features(self) -> List[str]:
        return ['close', 'volume', 'rsi_14', 'atr_14', 'macd', 'bb_position', 'ema_20', 'ema_50', 'volume_ratio', 'donchian_high_20', 'donchian_low_20', 'channel_position', 'adx_14', 'plus_di_14', 'minus_di_14']
```

### 戦略マネージャーでの統合
```python
from ..base.strategy_manager import StrategyManager
from ..implementations import *

# マネージャー初期化
manager = StrategyManager(config={
    'min_conflict_threshold': 0.1  # コンフリクト解決閾値
})

# 5戦略登録（重み付け）
manager.register_strategy(ATRBasedStrategy(), weight=0.25)
manager.register_strategy(MochiPoyAlertStrategy(), weight=0.25)
manager.register_strategy(MultiTimeframeStrategy(), weight=0.20)
manager.register_strategy(DonchianChannelStrategy(), weight=0.15)
manager.register_strategy(ADXTrendStrengthStrategy(), weight=0.15)

# 統合分析実行
market_data = get_market_data()  # OHLCV + 15特徴量データ
combined_signal = manager.analyze_market(market_data)

print(f"統合判定: {combined_signal.action}")
print(f"総合信頼度: {combined_signal.confidence:.3f}")
print(f"判定理由: {combined_signal.reason}")
```

## 🧪 テスト体系

### StrategyBase テスト
```bash
# 基底クラスの統合テスト
python -m pytest tests/unit/strategies/base/test_strategy_base.py -v

# 具体的なテスト項目
- 抽象メソッドの強制実装
- 入力データ検証
- シグナル履歴管理
- パフォーマンス追跡
- エラーハンドリング
```

### StrategyManager テスト
```bash
# 戦略マネージャーテスト（18テスト）
python -m pytest tests/unit/strategies/test_strategy_manager.py -v

# 主要テスト項目
- 戦略登録・解除
- 重み付け統合
- コンフリクト解決
- パフォーマンス集計
- エラー時の処理

# 統合基盤確認
python scripts/testing/dev_check.py validate --mode light
```

## 📋 設計パターン

### Strategy Pattern（戦略パターン）
```python
# 戦略の差し替え可能性
def execute_trading_strategy(market_data, strategy_type="atr_based"):
    if strategy_type == "atr_based":
        strategy = ATRBasedStrategy()
    elif strategy_type == "donchian_channel":
        strategy = DonchianChannelStrategy()
    
    return strategy.analyze(market_data)
```

### Template Method Pattern（テンプレートメソッドパターン）
```python
# StrategyBase.generate_signal()での統一フロー
def generate_signal(self, df: pd.DataFrame) -> StrategySignal:
    self._validate_input_data(df)        # 共通前処理
    signal = self.analyze(df)            # 戦略固有処理（抽象メソッド）
    self._post_process_signal(signal)    # 共通後処理
    return signal
```

### Observer Pattern（観察者パターン）
```python
# パフォーマンス追跡での使用
class StrategyBase:
    def update_performance(self, signal_success: bool):
        if signal_success:
            self.successful_signals += 1
        # 戦略マネージャーに通知可能
```

## 🔮 拡張設計

### 機能追加予定
```python
# 予定される拡張インターフェース
class StrategyBase(ABC):
    # 現在実装済み
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        pass
    
    # 追加予定
    def optimize_parameters(self, historical_data):
        """パラメータ自動最適化"""
        pass
    
    def get_performance_metrics(self):
        """詳細パフォーマンス指標"""
        pass
    
    def adapt_to_market_regime(self, regime_info):
        """市場体制適応機能"""
        pass
```

### A/Bテストフレームワーク
```python
# 戦略改良の効果測定
class StrategyManager:
    def enable_ab_testing(self, strategy_a, strategy_b, traffic_split=0.5):
        """A/Bテスト実行機能"""
        pass
    
    def get_ab_test_results(self):
        """A/Bテスト結果分析"""
        pass
```

## ⚙️ 設定システム

### 基底クラス設定
```yaml
# config/strategies/base.yml
strategy_base:
  min_data_points: 20           # 最低データ数
  max_signal_history: 1000      # 履歴保存数
  performance_tracking: true    # パフォーマンス追跡
  error_recovery: true          # エラー回復機能

strategy_manager:
  min_conflict_threshold: 0.1   # コンフリクト解決閾値
  max_strategies: 10            # 登録可能戦略数
  performance_window: 100       # パフォーマンス計算期間
```

### 動的設定変更
```python
# ランタイムでの設定調整
manager.config['min_conflict_threshold'] = 0.15
strategy.config['min_data_points'] = 30

# 設定の即座反映
manager.update_config(new_config)
```

## 🎯 品質指標

### コード品質
- **テストカバレッジ**: 95%以上
- **循環的複雑度**: 10以下
- **コード重複**: 5%以下
- **メソッド行数**: 平均20行以下

### パフォーマンス指標
- **シグナル生成時間**: 100ms以下
- **メモリ使用量**: 戦略あたり10MB以下
- **CPU使用率**: 統合分析で30%以下

---

**戦略基盤システム**: 5つの戦略が継承する抽象基底クラスと複数戦略の統合管理を提供。統一インターフェース・競合解決システム・重み付け統合により、15特徴量統一システムと連携した一貫性のある戦略アーキテクチャを実現。