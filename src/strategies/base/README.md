# Strategy Base - 戦略基盤システム

Phase 12完了・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応で設計された、すべての戦略実装の**基盤となるアーキテクチャ**・GitHub Actions対応。

## 📁 フォルダの目的

戦略システム全体の基盤を提供し、**一貫性・保守性・拡張性**を確保する核となるコンポーネント群。

### 設計原則
- **統一インターフェース**: 全戦略が共通の規約に従う
- **抽象化**: 戦略固有ロジックと共通処理の明確な分離
- **拡張性**: 新戦略の追加が容易な設計

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

## 🔄 Phase 12での改善点（CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応）

### 戦略基底クラスの強化（GitHub Actions対応）
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
# After: 統一された基盤クラス（Phase 12・CI/CDワークフロー最適化）
class ATRBasedStrategy(StrategyBase):  # 基底クラス継承・GitHub Actions対応
    def analyze(self, df):
        # 共通の前処理・後処理は基底クラスが担当・手動実行監視対応
        # 戦略固有ロジックのみ実装・段階的デプロイ対応
        pass
```

### 戦略マネージャーの簡素化
```python
# Before: 複雑な統合ロジック（387行）
class StrategyManager:
    def analyze_market(self, df):
        # 複雑な重み計算・コンフリクト解決
        # 詳細な履歴管理・統計処理
        # 200行以上の処理

# After: シンプルで効果的な統合（351行・9%削減・Phase 12対応）
class StrategyManager:  # CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応
    def analyze_market(self, df):
        # シンプルな重み付け統合・GitHub Actions対応
        # 効率的なコンフリクト解決・監視統合
        # 必要十分な統計管理・品質ゲート対応
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
        │   ATRBased       │   │  MochiPoyAlert │
        │   Strategy       │   │   Strategy     │
        └──────────────────┘   └────────────────┘
        
        ┌──────────────────┐   ┌────────────────┐
        │  MultiTimeframe  │   │  Fibonacci     │
        │    Strategy      │   │  Retracement   │
        └──────────────────┘   └────────────────┘
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
        return ['close', 'volume', 'rsi_14', 'atr_14']
```

### 戦略マネージャーでの統合
```python
from ..base.strategy_manager import StrategyManager
from ..implementations import *

# マネージャー初期化
manager = StrategyManager(config={
    'min_conflict_threshold': 0.1  # コンフリクト解決閾値
})

# 戦略登録（重み付け）
manager.register_strategy(ATRBasedStrategy(), weight=0.3)
manager.register_strategy(MochiPoyAlertStrategy(), weight=0.25)
manager.register_strategy(MultiTimeframeStrategy(), weight=0.25)
manager.register_strategy(FibonacciRetracementStrategy(), weight=0.2)

# 統合分析実行
market_data = get_market_data()  # OHLCV + 特徴量データ
combined_signal = manager.analyze_market(market_data)

print(f"統合判定: {combined_signal.action}")
print(f"総合信頼度: {combined_signal.confidence:.3f}")
print(f"判定理由: {combined_signal.reason}")
```

## 🧪 テスト体系

### StrategyBase テスト（Phase 12統合・CI/CD対応）
```bash
# 基底クラスの統合テスト（GitHub Actions統合）
python -m pytest tests/unit/strategies/base/test_strategy_base.py -v

# 具体的なテスト項目（手動実行監視対応）
- 抽象メソッドの強制実装・CI/CD品質ゲート対応
- 入力データ検証・段階的デプロイ対応
- シグナル履歴管理・監視統合
- パフォーマンス追跡・GitHub Actions対応
- エラーハンドリング・手動実行監視統合
```

### StrategyManager テスト（Phase 12対応）
```bash
# 戦略マネージャーテスト（18テスト・CI/CDワークフロー最適化）
python -m pytest tests/unit/strategies/test_strategy_manager.py -v

# 主要テスト項目（GitHub Actions対応）
- 戦略登録・解除・手動実行監視対応
- 重み付け統合・段階的デプロイ対応
- コンフリクト解決・CI/CD品質ゲート対応
- パフォーマンス集計・監視統合
- エラー時の処理・GitHub Actions統合

# 399テスト統合基盤確認
python scripts/management/dev_check.py validate --mode light
```

## 📋 設計パターン

### Strategy Pattern（戦略パターン）
```python
# 戦略の差し替え可能性
def execute_trading_strategy(market_data, strategy_type="atr_based"):
    if strategy_type == "atr_based":
        strategy = ATRBasedStrategy()
    elif strategy_type == "fibonacci":
        strategy = FibonacciRetracementStrategy()
    
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

### Phase 12での機能追加予定（CI/CDワークフロー最適化基盤活用）
```python
# 予定される拡張インターフェース（GitHub Actions基盤）
class StrategyBase(ABC):
    # 現在実装済み
    @abstractmethod
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        pass
    
    # Stage 2追加予定
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

### A/Bテストフレームワーク（Phase 12基盤活用）
```python
# 戦略改良の効果測定（CI/CDワークフロー最適化・手動実行監視対応）
class StrategyManager:
    def enable_ab_testing(self, strategy_a, strategy_b, traffic_split=0.5):
        """A/Bテスト実行機能・GitHub Actions統合"""
        pass
    
    def get_ab_test_results(self):
        """A/Bテスト結果分析・段階的デプロイ対応"""
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

**Phase 12完了日**: 2025年8月18日・CI/CDワークフロー最適化・手動実行監視・段階的デプロイ対応  
**設計方針**: 統一インターフェース・拡張性・保守性重視・GitHub Actions統合  
**基底クラス機能**: 入力検証・パフォーマンス追跡・エラーハンドリング・監視統合  
**マネージャー機能**: 戦略統合・コンフリクト解決・重み付け・CI/CD品質ゲート対応  
**テスト品質**: 基底クラス・マネージャー包括的テスト完了・399テスト統合基盤対応・GitHub Actions統合