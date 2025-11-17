# src/strategies/implementations/ - 取引戦略実装群

**Phase 52.4-B完了**: 6戦略統合システム・55特徴量・動的信頼度計算・Registry Pattern導入

## 📂 ファイル構成

```
src/strategies/implementations/
├── __init__.py                 # 6戦略エクスポート（33行）
├── atr_based.py               # ATRBased戦略（range型・440行）
├── donchian_channel.py        # DonchianChannel戦略（range型・546行）
├── adx_trend.py               # ADXTrendStrength戦略（trend型・602行）
├── bb_reversal.py             # BBReversal戦略（range型・320行）
├── stochastic_reversal.py     # StochasticReversal戦略（range型・266行）
└── macd_ema_crossover.py      # MACDEMACrossover戦略（trend型・350行）
```

**総行数**: 2,557行（Python 7ファイル）

---

## 🎯 実装戦略（6戦略）

### **1. ATRBasedStrategy**（range型）
**目的**: ボラティリティベース逆張り戦略
**ロジック**:
- ATRで市場ボラティリティ測定
- ボリンジャーバンド位置で過買い・過売り判定
- RSIで追加確認
- 市場ストレスで異常状況フィルター

**設定**:
```yaml
bb_overbought: 0.7  # BB過買い閾値
bb_oversold: 0.3    # BB過売り閾値
rsi_overbought: 65
rsi_oversold: 35
min_confidence: 0.3
```

**特徴**: 平均回帰理論・レンジ相場に強い

---

### **2. DonchianChannelStrategy**（range型）
**目的**: ブレイクアウト・反転検出
**ロジック**:
- 20期間高値・安値チャネル計算
- ブレイクアウト・リバーサル検出
- レンジ相場適応（70-80%市場対応）
- チャネル位置による強度判定

**設定**:
```yaml
channel_period: 20
min_confidence: 0.3
breakout_strength_threshold: 0.6
```

**特徴**: レンジ相場専用・ブレイクアウト精度高

---

### **3. ADXTrendStrengthStrategy**（trend型）
**目的**: トレンド強度・方向性分析
**ロジック**:
- ADX値による市場レジーム判定
- +DI/-DIクロスオーバー検出
- トレンド強度適応型信頼度調整
- レンジ相場での取引抑制

**設定**:
```yaml
adx_weak_threshold: 20
adx_moderate_threshold: 25
adx_strong_threshold: 40
min_confidence: 0.3
```

**特徴**: トレンド相場専用・強度別対応

---

### **4. BBReversalStrategy**（range型）
**目的**: ボリンジャーバンド反転
**ロジック**:
- BB上限タッチ + RSI買われすぎ → SELL
- BB下限タッチ + RSI売られすぎ → BUY
- レンジ相場判定（ADX < 20, BB幅 < 2%）

**設定**:
```yaml
rsi_overbought: 70
rsi_oversold: 30
bb_upper_threshold: 0.95
bb_lower_threshold: 0.05
adx_range_threshold: 20
```

**特徴**: レンジ相場特化・平均回帰狙い

---

### **5. StochasticReversalStrategy**（range型）
**目的**: モメンタム逆張り
**ロジック**:
- レンジ相場判定（ADX < 20）
- SELL: Stochastic過買い（K>80, D>80）+ ベアクロス + RSI > 65
- BUY: Stochastic過売り（K<20, D<20）+ ゴールデンクロス + RSI < 35
- Dynamic confidence: 0.30-0.50

**設定**:
```yaml
stoch_overbought: 80
stoch_oversold: 20
rsi_overbought: 65
rsi_oversold: 35
adx_range_threshold: 20
```

**特徴**: レンジ相場・モメンタム反転捕捉

---

### **6. MACDEMACrossoverStrategy**（trend型）
**目的**: トレンド転換期エントリー
**ロジック**:
- トレンド相場判定（ADX > 25）
- BUY: MACDゴールデンクロス + EMA 20 > EMA 50 + 出来高増加
- SELL: MACDデッドクロス + EMA 20 < EMA 50 + 出来高増加
- Dynamic confidence: 0.35-0.65

**設定**:
```yaml
adx_trend_threshold: 25
macd_histogram_threshold: 0.5
volume_threshold: 1.2
ema_divergence_threshold: 0.01
```

**特徴**: トレンド転換期・押し目買い/戻り売り

---

## 🔧 共通実装パターン

### **Registry Pattern**
```python
from ..strategy_registry import StrategyRegistry
from ..utils import StrategyType

@StrategyRegistry.register(name="ATRBased", strategy_type=StrategyType.ATR_BASED)
class ATRBasedStrategy(StrategyBase):
    ...
```

### **設定管理（thresholds.yaml統合）**
```python
from ...core.config.threshold_manager import get_threshold

default_config = {
    "min_confidence": get_threshold("strategies.atr_based.min_confidence", 0.3),
    "stop_loss_atr_multiplier": get_threshold("sl_atr_normal_vol", 2.0),
    ...
}
```

### **SignalBuilder統一**
```python
from ..utils import SignalBuilder, EntryAction

signal = SignalBuilder.build(
    strategy=self,
    action=EntryAction.BUY,
    confidence=0.7,
    strength=0.6,
    current_price=df["close"].iloc[-1],
    indicators=analysis
)
```

---

## 📊 戦略タイプ別分類

### **Range型（レンジ相場）** - 4戦略
1. ATRBased: ボラティリティベース逆張り
2. DonchianChannel: ブレイクアウト・反転
3. BBReversal: ボリンジャーバンド反転
4. StochasticReversal: モメンタム逆張り

### **Trend型（トレンド相場）** - 2戦略
1. ADXTrendStrength: トレンド強度分析
2. MACDEMACrossover: トレンド転換期エントリー

**市場対応**: レンジ相場70-80% → range型4戦略で重点カバー

---

## 🚀 使用例

```python
from src.strategies.implementations import (
    ATRBasedStrategy,
    DonchianChannelStrategy,
    ADXTrendStrengthStrategy,
    BBReversalStrategy,
    StochasticReversalStrategy,
    MACDEMACrossoverStrategy
)
from src.strategies.base import StrategyManager

# 戦略マネージャー初期化
manager = StrategyManager()

# 6戦略登録（均等重み）
manager.register_strategy(ATRBasedStrategy(), weight=1.0)
manager.register_strategy(DonchianChannelStrategy(), weight=1.0)
manager.register_strategy(ADXTrendStrengthStrategy(), weight=1.0)
manager.register_strategy(BBReversalStrategy(), weight=1.0)
manager.register_strategy(StochasticReversalStrategy(), weight=1.0)
manager.register_strategy(MACDEMACrossoverStrategy(), weight=1.0)

# 市場分析実行
market_data = get_market_data()  # 55特徴量データ
combined_signal = manager.analyze_market(market_data)

# 統合シグナル取得
print(f"Action: {combined_signal.action}")
print(f"Confidence: {combined_signal.confidence:.3f}")
```

---

## ⚙️ 設定

**環境変数**: 不要（thresholds.yaml・features.yaml・strategies.yamlから自動取得）

**データ要件**:
- 55特徴量統一（feature_order.json準拠）
- 最小データ数: 20以上
- 4時間足（トレンド判定）+ 15分足（エントリー実行）

**デフォルト設定ファイル**:
- `config/core/thresholds.yaml`: 戦略パラメータ・閾値
- `config/core/features.yaml`: 機能トグル
- `config/core/strategies.yaml`: 戦略登録・重み設定

**SL/TP設定**:
- SL: ATR × 2.0（通常ボラティリティ）
- TP: thresholds.yaml設定優先
- RR比: 1.29:1（デイトレード特化）

---

## ✅ 品質保証

**テスト**:
- 単体テスト: 各戦略ごとに完備
- 統合テスト: StrategyManager経由
- カバレッジ: 68.77%（目標68.27%超過）

**コード品質**:
- flake8: 全ファイルPASS
- isort: インポートソート済み
- black: コードフォーマット済み

**CI/CD**:
- GitHub Actions自動品質ゲート
- GCP Cloud Run自動デプロイ

---

## ⚠️ 重要事項

### **アーキテクチャ**
- **Registry Pattern**: 動的戦略登録・拡張容易
- **設定駆動**: ハードコード禁止・thresholds.yaml一元管理
- **SignalBuilder統一**: 全戦略で統一シグナル生成
- **55特徴量システム**: feature_order.json単一真実源

### **Phase 52.4-B完了内容**
- 6戦略統合システム確立
- Phase参照統一（Phase 52.4-B）
- 特徴量数統一（55特徴量）
- コード品質改善（magic numbers削減）

### **依存関係**
- pandas: データ処理
- numpy: 数値計算
- src.strategies.base: StrategyBase継承
- src.strategies.utils: SignalBuilder・EntryAction・StrategyType
- src.core.config: get_threshold設定管理

---

**Phase 52.4-B完了**: 6戦略統合システム・55特徴量・Registry Pattern・thresholds.yaml統合・動的戦略管理基盤
