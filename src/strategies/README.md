# src/strategies/ - 取引戦略システム

**Phase 49完了**: 市場不確実性計算統合・バックテストログユーティリティ追加・コード重複削減による戦略層最適化。

## 🎯 役割・責任

AI自動取引システムの戦略層。5つの取引戦略（ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength）を統合管理し、市場データから取引シグナルを生成。統一インターフェース・競合解決・重み付け統合・動的信頼度計算により、安定した取引判断を提供。

**Phase 49完了**:
- 市場不確実性計算統合（MarketUncertaintyCalculator）: 全5戦略の重複コード250-300行削減
- バックテストログユーティリティ（conditional_log）: 20-30箇所の環境変数チェック統一
- 保守性向上: 統一ユーティリティ活用による一元管理実現

## 📂 ファイル構成

```
src/strategies/
├── __init__.py              # 戦略システムエクスポート（41行・Phase 49完了）
├── base/                    # 戦略基盤システム
│   ├── strategy_base.py        # 抽象基底クラス（294行・Phase 49完了）
│   └── strategy_manager.py     # 戦略統合管理（557行・Phase 49完了）
├── implementations/         # 戦略実装群
│   ├── atr_based.py           # ATRBased戦略（436行・Phase 49完了）
│   ├── mochipoy_alert.py      # MochipoyAlert戦略（352行・Phase 49完了）
│   ├── multi_timeframe.py     # MultiTimeframe戦略（445行・Phase 49完了）
│   ├── donchian_channel.py    # DonchianChannel戦略（544行・Phase 49完了）
│   └── adx_trend.py          # ADXTrendStrength戦略（600行・Phase 49完了）
└── utils/                   # 共通処理モジュール
    ├── strategy_utils.py      # 統合共通処理（572行・Phase 49完了）
    └── market_utils.py        # 市場分析ユーティリティ（180行・Phase 49完了）
```

## 🔧 主要コンポーネント

### **base/ - 戦略基盤システム** → [詳細](base/README.md)

**StrategyBase**: 全戦略共通の抽象基底クラス
```python
class StrategyBase(ABC):
    def analyze(self, df: pd.DataFrame) -> StrategySignal          # 戦略分析（抽象）
    def get_required_features(self) -> List[str]                  # 必要特徴量
```

**StrategyManager**: 複数戦略の統合管理・競合解決
```python
class StrategyManager:
    def register_strategy(self, strategy, weight=1.0)             # 戦略登録
    def analyze_market(self, df: pd.DataFrame) -> StrategySignal  # 統合分析
```

### **implementations/ - 戦略実装群** → [詳細](implementations/README.md)

**5戦略の特徴**:
- **ATRBased**: ボラティリティ追従・動的信頼度計算（0.2-0.8範囲）
- **MochipoyAlert**: EMA・MACD・RCI複合指標・多数決システム
- **MultiTimeframe**: 4時間足＋15分足・時間軸統合分析
- **DonchianChannel**: 20期間ブレイクアウト・中央域対応
- **ADXTrendStrength**: トレンド強度分析・弱トレンド対応

### **utils/ - 共通処理モジュール** → [詳細](utils/README.md)

**統一機能**:
```python
class EntryAction:          # BUY/SELL/HOLD定数
class StrategyType:         # 戦略タイプ識別
class RiskManager:          # リスク管理計算
class SignalBuilder:        # シグナル生成統合
```

## 🚀 使用方法

### **戦略マネージャーでの統合実行**

```python
from src.strategies.base.strategy_manager import StrategyManager
from src.strategies.implementations import *

# 戦略マネージャー初期化
manager = StrategyManager()

# 5戦略登録（重み付け）
manager.register_strategy(ATRBasedStrategy(), weight=0.25)
manager.register_strategy(MochipoyAlertStrategy(), weight=0.25)
manager.register_strategy(MultiTimeframeStrategy(), weight=0.20)
manager.register_strategy(DonchianChannelStrategy(), weight=0.15)
manager.register_strategy(ADXTrendStrengthStrategy(), weight=0.15)

# 統合分析実行
market_data = get_market_data()  # 15特徴量データ
combined_signal = manager.analyze_market(market_data)

print(f"統合判定: {combined_signal.action}")
print(f"総合信頼度: {combined_signal.confidence:.3f}")
```

### **個別戦略の使用**

```python
from src.strategies.implementations.atr_based import ATRBasedStrategy

# ATRBased戦略の個別実行
atr_strategy = ATRBasedStrategy()
signal = atr_strategy.analyze(market_data_df)

print(f"ATR戦略: {signal.action}")
print(f"信頼度: {signal.confidence:.3f}")
```

## ⚙️ 戦略統合システム

### **競合解決メカニズム**

**統合判定フロー**:
```
【各戦略並行実行】→ 個別StrategySignal生成（5戦略）
        ↓
【アクション別グループ化】→ {"buy": [...], "sell": [...], "hold": [...]}
        ↓
【競合検知】→ BUY vs SELL同時存在チェック
        ↓
競合なし → 多数決＋重み付け統合
競合あり → 重み付け信頼度比較
        ↓
【最終統合シグナル】→ StrategySignal(strategy_name="StrategyManager")
```

**処理パターン**:
- **競合なし（例: SELL 3 + HOLD 2）**: 多数決で積極的アクション（SELL）優先
- **競合あり（例: SELL 3 + BUY 2）**: 重み付け信頼度比較・安全なHOLD選択

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

```bash
# 戦略システム完全テスト実行
bash scripts/testing/checks.sh

# 個別コンポーネントテスト
python -m pytest tests/unit/strategies/implementations/ -v  # 5戦略テスト（各15テスト）
python -m pytest tests/unit/strategies/base/ -v           # 基盤システムテスト（38テスト）
python -m pytest tests/unit/strategies/utils/ -v          # 共通処理テスト（23テスト）
```

**品質指標**:
- **テスト成功率**: 100%
- **シグナル生成時間**: 100ms以下
- **統合分析処理**: 200ms以下
- **メモリ使用量**: 戦略あたり10MB以下

## ⚠️ 重要事項

### **戦略実装ルール**

**必須継承**:
```python
from src.strategies.base.strategy_base import StrategyBase, StrategySignal
from src.strategies.utils import EntryAction, StrategyType

class CustomStrategy(StrategyBase):
    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """必須実装: 戦略固有分析ロジック"""
        decision = {'action': EntryAction.BUY, 'confidence': 0.7}

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
        return ['close', 'volume', 'rsi_14', 'atr_14', 'macd', 'bb_position', 'ema_20', 'ema_50', 'volume_ratio', 'donchian_high_20', 'donchian_low_20', 'channel_position', 'adx_14', 'plus_di_14', 'minus_di_14']
```

### **設定管理**

**動的設定システム（thresholds.yaml統合）**:
```python
from src.core.config.threshold_manager import get_threshold

# 設定値を動的取得（フォールバック回避）
bb_overbought = get_threshold("strategies.atr_based.bb_overbought", 0.7)
min_confidence = get_threshold("strategies.atr_based.min_confidence", 0.3)
```

### **特性・制約**
- **15特徴量統一**: feature_order.json準拠・順序厳守必須
- **動的信頼度**: 各戦略が市場状況に応じて0.2-0.8範囲で動的計算
- **統一インターフェース**: 全戦略がStrategyBase継承・StrategySignal統一形式
- **設定一元化**: config/core/thresholds.yaml一括管理・再起動で設定反映
- **Phase 49完了**: コード重複削減・統一ユーティリティ活用・保守性向上
- **依存**: pandas・numpy・src.core.*・統合15特徴量データ

---

**取引戦略システム（Phase 49完了）**: 5戦略統合管理・競合解決システム・重み付け統合・動的信頼度計算・市場不確実性計算統合・バックテストログユーティリティによる統一戦略層。