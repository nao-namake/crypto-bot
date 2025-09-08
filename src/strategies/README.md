# src/strategies/ - 取引戦略システム

## 🎯 役割・責任

AI自動取引システムの戦略層。4つの取引戦略（ATRベース・フィボナッチ・もちぽよアラート・マルチタイムフレーム）を統合管理し、市場データから取引シグナルを生成。統一インターフェース・コンフリクト解決・重み付け統合により、安定した取引判断を提供。

## 📚 詳細ドキュメント

- **[戦略基盤システム詳細](base/README.md)**: StrategyBase抽象基底クラス・StrategyManager統合管理の実装詳細
- **[戦略実装詳細](implementations/README.md)**: 4戦略（ATR・フィボナッチ・もちぽよ・MTF）の個別分析・パラメータ・アルゴリズム
- **[共通処理詳細](utils/README.md)**: RiskManager・SignalBuilder・定数管理の具体的使用方法

## 📂 ファイル構成

```
src/strategies/
├── __init__.py              # 戦略システムエクスポート（20行）
├── base/                    # 戦略基盤システム
│   ├── __init__.py             # 基盤クラスエクスポート（5行）
│   ├── strategy_base.py        # 抽象基底クラス・統一インターフェース（199行）
│   └── strategy_manager.py     # 戦略統合管理・重み付け判定・コンフリクト解決（351行）
├── implementations/         # 戦略実装群
│   ├── __init__.py             # 実装戦略エクスポート（9行）
│   ├── atr_based.py           # ATRベース戦略・ボラティリティ分析（348行）
│   ├── fibonacci_retracement.py # フィボナッチ戦略・レベル分析（563行）
│   ├── mochipoy_alert.py      # もちぽよアラート・複合指標（283行）
│   └── multi_timeframe.py     # マルチタイムフレーム・時間軸統合（313行）
└── utils/                   # 共通処理モジュール
    ├── __init__.py             # 共通機能エクスポート（22行）
    └── strategy_utils.py      # 統合共通処理・定数・リスク管理・シグナル生成（380行）
```

## 🔧 主要コンポーネント

> 💡 **詳細情報**: 各コンポーネントの実装詳細・使用方法は[詳細ドキュメント](#📚-詳細ドキュメント)を参照

### **base/ - 戦略基盤システム** → [詳細](base/README.md)

#### strategy_base.py（199行）
**目的**: 全戦略共通の抽象基底クラス・統一インターフェース

**主要クラス**:
```python
class StrategyBase(ABC):
    def __init__(self, name: str, config: Optional[Dict] = None)  # 基底初期化
    def analyze(self, df: pd.DataFrame) -> StrategySignal          # 戦略分析（抽象）
    def generate_signal(self, df: pd.DataFrame) -> StrategySignal  # シグナル生成
    def get_required_features(self) -> List[str]                  # 必要特徴量
    def get_info(self) -> Dict                                    # 戦略情報

@dataclass
class StrategySignal:
    strategy_name: str              # 戦略名
    action: str                     # BUY/SELL/HOLD/CLOSE
    confidence: float               # 信頼度 (0.0-1.0)
    current_price: float            # 現在価格
    stop_loss: Optional[float]      # ストップロス価格
    take_profit: Optional[float]    # 利確価格
    reason: str                     # シグナル理由
```

#### strategy_manager.py（351行）
**目的**: 複数戦略の統合管理・コンフリクト解決・重み付け統合

**主要クラス**:
```python
class StrategyManager:
    def register_strategy(self, strategy, weight=1.0)             # 戦略登録
    def analyze_market(self, df: pd.DataFrame) -> StrategySignal  # 統合分析
    def _has_signal_conflict(self, signal_groups) -> bool         # 競合検知
    def _resolve_signal_conflict(self, signals, df)               # 競合解決
    def _integrate_consistent_signals(self, signals)              # 一貫性統合
    def _calculate_weighted_confidence(self, signals)             # 重み付け信頼度
```

### **implementations/ - 戦略実装群** → [詳細](implementations/README.md)

#### atr_based.py（348行）
**目的**: ATRベースボラティリティ追従戦略

**主要クラス**:
```python
class ATRBasedStrategy(StrategyBase):
    def __init__(self, config=None)                               # ATR戦略初期化
    def analyze(self, df: pd.DataFrame) -> StrategySignal         # ATR分析実行
    def _make_decision(self, bb_analysis, rsi_analysis, atr_analysis)  # 判定ロジック
    def _analyze_bb_position(self, df)                            # ボリンジャーバンド分析
    def _analyze_rsi(self, df)                                    # RSI分析
    def _analyze_atr_volatility(self, df)                         # ATRボラティリティ分析
```

#### fibonacci_retracement.py（563行）
**目的**: フィボナッチリトレースメント戦略

**主要クラス**:
```python
class FibonacciRetracementStrategy(StrategyBase):
    def __init__(self, config=None)                               # フィボナッチ初期化
    def analyze(self, df: pd.DataFrame) -> StrategySignal         # フィボ分析実行
    def _identify_swings(self, df)                                # スイング高値・安値検出
    def _calculate_fibonacci_levels(self, high, low)              # フィボレベル計算
    def _check_price_near_fib_level(self, current_price, levels) # レベル接近判定
    def _detect_reversal_signal(self, df, fib_level)             # 反転シグナル検出
```

#### mochipoy_alert.py（283行）
**目的**: もちぽよアラート複合指標戦略

**主要クラス**:
```python
class MochiPoyAlertStrategy(StrategyBase):
    def __init__(self, config=None)                               # もちぽよ初期化
    def analyze(self, df: pd.DataFrame) -> StrategySignal         # 複合分析実行
    def _analyze_ema(self, df)                                    # EMA分析
    def _analyze_macd_and_rci(self, df)                          # MACD・RCI分析
    def _make_simple_decision(self, ema_signal, macd_signal, rci_signal)  # 多数決判定
```

#### multi_timeframe.py（313行）
**目的**: マルチタイムフレーム統合戦略

**主要クラス**:
```python
class MultiTimeframeStrategy(StrategyBase):
    def __init__(self, config=None)                               # MTF初期化
    def analyze(self, df: pd.DataFrame) -> StrategySignal         # 時間軸統合分析
    def _analyze_4h_trend(self, df)                               # 4時間足トレンド分析
    def _analyze_15m_timing(self, df)                             # 15分足タイミング分析
    def _integrate_timeframes(self, trend_4h, timing_15m)         # 時間軸統合判定
```

### **utils/ - 共通処理モジュール** → [詳細](utils/README.md)

#### strategy_utils.py（380行）
**目的**: 戦略間重複コード排除・統一計算ロジック・リスク管理統合

**主要機能**:
```python
class EntryAction:          # 取引アクション定数
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"

class StrategyType:         # 戦略タイプ識別
    ATR_BASED = "atr_based"
    FIBONACCI = "fibonacci_retracement"
    MOCHIPOY = "mochipoy_alert"
    MULTI_TIMEFRAME = "multi_timeframe"

class RiskManager:          # リスク管理計算
    @staticmethod
    def calculate_stop_loss_take_profit(price, action, atr, config)  # SL/TP計算
    @staticmethod
    def calculate_position_size(confidence, config)                  # ポジションサイズ
    @staticmethod
    def calculate_risk_ratio(stop_loss, take_profit, entry_price)    # リスク比率

class SignalBuilder:        # シグナル生成統合
    @staticmethod
    def create_signal_with_risk_management(strategy_name, decision, current_price, df, config, strategy_type)  # 統合シグナル生成
    @staticmethod
    def create_hold_signal(strategy_name, current_price, reason)     # ホールドシグナル
    @staticmethod
    def create_error_signal(strategy_name, current_price, error)     # エラーシグナル
```

## 🚀 使用方法

### **戦略マネージャーでの統合実行**
```python
from src.strategies.base.strategy_manager import StrategyManager
from src.strategies.implementations import (
    ATRBasedStrategy, FibonacciRetracementStrategy, 
    MochiPoyAlertStrategy, MultiTimeframeStrategy
)

# 戦略マネージャー初期化
manager = StrategyManager()

# 戦略登録（重み付け）
manager.register_strategy(ATRBasedStrategy(), weight=0.3)
manager.register_strategy(FibonacciRetracementStrategy(), weight=0.25)
manager.register_strategy(MochiPoyAlertStrategy(), weight=0.25)
manager.register_strategy(MultiTimeframeStrategy(), weight=0.2)

# 統合分析実行
market_data = get_market_data()  # OHLCV + 特徴量データ
combined_signal = manager.analyze_market(market_data)

print(f"統合判定: {combined_signal.action}")
print(f"総合信頼度: {combined_signal.confidence:.3f}")
print(f"判定理由: {combined_signal.reason}")
```

### **個別戦略の使用**
```python
from src.strategies.implementations.atr_based import ATRBasedStrategy

# ATRベース戦略の個別実行
atr_strategy = ATRBasedStrategy()
signal = atr_strategy.analyze(market_data_df)

print(f"ATR戦略: {signal.action}")
print(f"信頼度: {signal.confidence:.3f}")
print(f"判定理由: {signal.reason}")
```

### **共通処理の活用**
```python
from src.strategies.utils import RiskManager, SignalBuilder, EntryAction

# リスク管理計算
stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
    current_price=1000000,
    action=EntryAction.BUY,
    atr_value=50000,
    config={'atr_multiplier': 2.0}
)

# ポジションサイズ計算
position_size = RiskManager.calculate_position_size(
    confidence=0.7,
    config={'max_position_size': 0.1}
)

# 統合シグナル生成
signal = SignalBuilder.create_signal_with_risk_management(
    strategy_name="CustomStrategy",
    decision={'action': EntryAction.BUY, 'confidence': 0.75},
    current_price=1000000,
    df=market_data_df,
    config=strategy_config,
    strategy_type=StrategyType.ATR_BASED
)
```

## ⚙️ 戦略統合システム

### **競合解決メカニズム**

**競合検知**:
```python
def _has_signal_conflict(self, signal_groups):
    has_buy = "buy" in signal_groups and len(signal_groups["buy"]) > 0
    has_sell = "sell" in signal_groups and len(signal_groups["sell"]) > 0
    return has_buy and has_sell  # BUYとSELLが同時存在時のみ競合
```

**処理パターン**:

**1. 競合なし（例: SELL 2 + HOLD 2）**
- `_integrate_consistent_signals`で多数決処理
- 積極的アクション（SELL）を優先選択

**2. 競合あり（例: SELL 2 + BUY 2）**
- `_resolve_signal_conflict`で重み付け信頼度比較
- 信頼度差0.1未満なら安全なHOLD選択
- 信頼度差0.1以上なら高信頼度グループが勝利

### **統合判定フロー**

```
【各戦略並行実行】→ 個別StrategySignal生成
        ↓
【アクション別グループ化】→ {"buy": [...], "sell": [...], "hold": [...]}
        ↓
【競合検知】→ BUY vs SELL同時存在チェック
        ↓
【競合なし】→ 多数決 + 重み付け統合
【競合あり】→ 重み付け信頼度比較 → 安全判定
        ↓
【最終統合シグナル】→ StrategySignal(strategy_name="StrategyManager")
```

### **重み付け信頼度計算**

```python
def _calculate_weighted_confidence(self, signals):
    total_weighted_confidence = 0.0
    total_weight = 0.0
    
    for strategy_name, signal in signals:
        weight = self.strategy_weights.get(strategy_name, 1.0)
        weighted_confidence = signal.confidence * weight
        
        total_weighted_confidence += weighted_confidence
        total_weight += weight
    
    return total_weighted_confidence / total_weight if total_weight > 0 else 0.0
```

## 🧪 テスト・品質保証

> 📋 **テスト詳細**: 各モジュール別のテスト仕様・実行方法は[詳細ドキュメント](#📚-詳細ドキュメント)を参照

### **戦略システム全体テスト**
```bash
# 戦略システム完全テスト実行
bash scripts/testing/checks.sh

# 個別戦略テスト
python -m pytest tests/unit/strategies/implementations/ -v

# 戦略基盤テスト
python -m pytest tests/unit/strategies/base/ -v

# 共通処理テスト
python -m pytest tests/unit/strategies/utils/ -v
```

### **テスト構成**

**実装戦略テスト**:
- `test_atr_based.py`: ATR戦略テスト（15テスト）
- `test_fibonacci_retracement.py`: フィボナッチ戦略テスト（17テスト）
- `test_mochipoy_alert.py`: もちぽよアラートテスト（15テスト）
- `test_multi_timeframe.py`: マルチタイムフレームテスト（15テスト）

**基盤システムテスト**:
- `test_strategy_base.py`: 基底クラステスト（20テスト）
- `test_strategy_manager.py`: 統合管理テスト（18テスト）

**共通処理テスト**:
- `test_strategy_utils.py`: 共通機能テスト（23テスト）

### **品質指標**

**コード品質**:
- テスト成功率: 100%
- テスト実行時間: 1秒以内
- コードカバレッジ: 95%以上

**パフォーマンス**:
- シグナル生成時間: 100ms以下
- メモリ使用量: 戦略あたり10MB以下
- 統合分析処理: 200ms以下

## ⚠️ 重要事項

> ⚙️ **実装ガイド**: 戦略開発・カスタマイズの詳細は[詳細ドキュメント](#📚-詳細ドキュメント)を参照

### **戦略実装ルール**

**必須継承**:
```python
from src.strategies.base.strategy_base import StrategyBase, StrategySignal
from src.strategies.utils import EntryAction, StrategyType

class CustomStrategy(StrategyBase):
    def __init__(self, config=None):
        super().__init__("custom_strategy", config)
    
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """必須実装: 戦略固有分析ロジック"""
        # 戦略分析処理
        decision = {'action': EntryAction.BUY, 'confidence': 0.7}
        
        # 統合シグナル生成
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=float(df['close'].iloc[-1]),
            df=df,
            config=self.config,
            strategy_type=StrategyType.CUSTOM
        )
    
    def get_required_features(self) -> List[str]:
        """必須実装: 必要特徴量リスト"""
        return ['close', 'volume', 'rsi_14', 'atr_14']
```

**エラーハンドリング**:
```python
from src.core.exceptions import StrategyError

def analyze(self, df: pd.DataFrame) -> StrategySignal:
    try:
        # 戦略ロジック
        return self._perform_analysis(df)
    except Exception as e:
        raise StrategyError(
            f"{self.name}戦略分析エラー",
            context={'df_shape': df.shape}
        ) from e
```

### **設定管理**

**戦略固有設定**:
```python
class ATRBasedStrategy(StrategyBase):
    def __init__(self, config=None):
        default_config = {
            'atr_period': 14,
            'volatility_threshold': 1.2,
            'stop_loss_multiplier': 2.0
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__("atr_based", merged_config)
```

### **依存関係**

**外部ライブラリ**:
- pandas: データ処理
- numpy: 数値計算
- dataclasses: データ構造
- typing: 型注釈

**内部依存**:
- src.core.exceptions: カスタム例外
- src.core.logger: ログ管理
- src.core.config: 設定管理

### **制限事項**
- 各戦略は12特徴量データを前提とした設計
- 統合シグナルは最大4戦略での重み付け統合
- リスク管理機能は共通処理に依存

---

## 🔗 関連ドキュメント

- **[システム全体概要](../../../README.md)**: プロジェクト全体アーキテクチャ
- **[特徴量システム](../features/README.md)**: 12特徴量生成・統合管理
- **[MLシステム](../ml/README.md)**: ProductionEnsemble・機械学習統合
- **[取引実行システム](../trading/README.md)**: リスク管理・取引実行

---

**取引戦略システム**: 4つの戦略（ATRベース・フィボナッチ・もちぽよアラート・マルチタイムフレーム）を統合管理する戦略層。統一インターフェース・競合解決システム・重み付け統合により、安定した取引シグナル生成を実現。