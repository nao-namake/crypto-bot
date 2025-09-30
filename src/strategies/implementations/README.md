# src/strategies/implementations/ - 取引戦略実装群

**Phase 28完了・Phase 29最適化版**: 5つの独立した取引戦略による多様な市場対応・動的信頼度計算システム。

## 📂 ファイル構成

```
src/strategies/implementations/
├── __init__.py               # 5戦略エクスポート（30行）
├── atr_based.py             # ATRBased戦略・ボラティリティ分析（350行）
├── mochipoy_alert.py        # MochipoyAlert戦略・複合指標（283行）
├── multi_timeframe.py       # MultiTimeframe戦略・時間軸統合（313行）
├── donchian_channel.py      # DonchianChannel戦略・ブレイクアウト（280行）
└── adx_trend.py            # ADXTrendStrength戦略・トレンド強度（265行）
```

## 🔧 主要戦略

### **1. ATRBasedStrategy（atr_based.py）**
**戦略タイプ**: ボラティリティ追従型・動的信頼度計算

**主要ロジック**:
```python
- ATRボラティリティ測定による市場状況判定
- ボリンジャーバンド位置での過買い・過売り判定
- RSI追加確認による精度向上
- 動的信頼度計算（0.2-0.8範囲）
```

**適用市場**: 高ボラティリティ相場・トレンドフォロー・積極的取引機会

### **2. MochipoyAlertStrategy（mochipoy_alert.py）**
**戦略タイプ**: 複合指標・多数決システム

**主要ロジック**:
```python
- EMAトレンド判定（20EMA vs 50EMA）
- MACDモメンタム分析（MACD > 0）
- RCI逆張り補完（過買い・過売り水準）
- 3指標多数決による最終判定
```

**適用市場**: 全市場状況・機会損失防止・積極的シグナル捕捉

### **3. MultiTimeframeStrategy（multi_timeframe.py）**
**戦略タイプ**: マルチタイムフレーム分析型

**主要ロジック**:
```python
- 4時間足: 50EMAによる中期トレンド分析
- 15分足: 20EMAクロス + RSIエントリータイミング
- 2軸統合: 時間軸間の整合性確認
- 両軸一致時のみエントリー実行
```

**適用市場**: 中期トレンド継続時・明確な方向性のある相場

### **4. DonchianChannelStrategy（donchian_channel.py）**
**戦略タイプ**: ブレイクアウト・反転戦略

**主要ロジック**:
```python
- 20期間ドンチャンチャネル計算
- 高値・安値ブレイクアウト検知
- RSI確認による偽ブレイクアウト除外
- チャネル内レンジ取引対応
```

**適用市場**: ブレイクアウト相場・レンジ抜け・明確なサポレジ

### **5. ADXTrendStrengthStrategy（adx_trend.py）**
**戦略タイプ**: トレンド強度・方向性分析戦略

**主要ロジック**:
```python
- 14期間ADXによるトレンド強度測定
- +DI/-DIによる方向性判定
- 強いトレンド閾値（25以上）でのエントリー
- 方向性明確時の順張り戦略
```

**適用市場**: 強いトレンド相場・方向性明確時・順張り機会

## 🚀 使用例

```python
# 基本的な戦略実装
from src.strategies.implementations import *

# 個別戦略使用
atr_strategy = ATRBasedStrategy()
mochipoy_strategy = MochipoyAlertStrategy()
multi_strategy = MultiTimeframeStrategy()
donchian_strategy = DonchianChannelStrategy()
adx_strategy = ADXTrendStrengthStrategy()

# 市場分析実行
market_data = get_market_data()  # 15特徴量データ
signal = atr_strategy.analyze(market_data)

print(f"戦略: {signal.strategy_name}")
print(f"判定: {signal.action}")
print(f"信頼度: {signal.confidence:.3f}")

# 戦略マネージャーでの統合使用
from src.strategies.base import StrategyManager

manager = StrategyManager()
manager.register_strategy(ATRBasedStrategy(), weight=0.25)
manager.register_strategy(MochipoyAlertStrategy(), weight=0.25)
manager.register_strategy(MultiTimeframeStrategy(), weight=0.20)
manager.register_strategy(DonchianChannelStrategy(), weight=0.15)
manager.register_strategy(ADXTrendStrengthStrategy(), weight=0.15)

# 統合分析実行
combined_signal = manager.analyze_market(market_data)
```

## 📊 統合判定システム

### **統合判定フロー**

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

### **戦略重み設定**

```python
# 現在の推奨重み設定
strategy_weights = {
    'ATRBased': 0.25,           # 25% - ボラティリティ対応
    'MochipoyAlert': 0.25,      # 25% - 複合指標信頼性
    'MultiTimeframe': 0.20,     # 20% - 時間軸統合精度
    'DonchianChannel': 0.15,    # 15% - ブレイクアウト捕捉
    'ADXTrendStrength': 0.15    # 15% - トレンド強度確認
}
```

## 🔧 動的信頼度計算システム

### **市場データ基づく動的信頼度**

**Phase 29最適化**: 全5戦略でハードコード値を削除し、市場データに基づく動的信頼度計算を実装。

### **動的信頼度の特徴**

- **小数点第3位まで表示**: 0.235、0.678など動的に変化する値
- **市場不確実性反映**: ATR、ボリューム、価格変動率を統合計算
- **設定ベース調整**: thresholds.yamlで最小値・最大値・パラメータを管理
- **固定値回避**: 0.2、0.4等の固定値は完全に排除

### **計算方式**

```python
# 市場不確実性計算（全戦略共通）
def _calculate_market_uncertainty(df):
    # ATRベースボラティリティ要因
    volatility_factor = min(0.05, atr_value / current_price)

    # ボリューム異常度
    volume_factor = min(0.03, abs(volume_ratio - 1.0) * 0.1)

    # 価格変動率
    price_factor = min(0.02, price_change)

    # 統合不確実性
    return volatility_factor + volume_factor + price_factor

# 戦略別動的信頼度
base_confidence = get_threshold("dynamic_confidence.strategies.{strategy}.{level}_base")
confidence = (base_confidence + signal_strength) * (1 + market_uncertainty)
```

### **戦略別動的信頼度実装**

#### **MochipoyAlert戦略**: 3指標多数決システム
```python
# 2票以上賛成時: 0.70～0.95の動的範囲
buy_strong_confidence = 0.70 + bonus * (1 + market_uncertainty)

# 1票賛成時: 0.45～0.60の動的範囲
buy_weak_confidence = 0.45 + weak_bonus * (1 + market_uncertainty)

# HOLD時: 0.10～0.35の動的範囲
hold_confidence = 0.20 + hold_adjustment * (1 + market_uncertainty)
```

#### **MultiTimeframe戦略**: 2軸統合システム
```python
# 両軸一致時: 0.75～1.05の動的範囲
agreement_confidence = 0.75 + agreement_bonus * (1 + market_uncertainty)

# 重み付け判定: 4h軸60% + 15m軸40%
weighted_score = tf_4h_signal * 0.6 + tf_15m_signal * 0.4
confidence = abs(weighted_score) * (1 + market_uncertainty)
```

#### **DonchianChannel戦略**: ブレイクアウト・レンジシステム
```python
# ブレイクアウト時: 0.60～0.85の動的範囲
breakout_confidence = 0.60 + breakout_strength * (1 + market_uncertainty)

# レンジ内: 0.20～0.45の動的範囲
range_confidence = 0.30 + range_adjustment * (1 + market_uncertainty)
```

#### **ADXTrendStrength戦略**: トレンド強度システム
```python
# 強トレンド: 0.40～0.85の動的範囲
strong_confidence = 0.65 + adx_bonus * (1 + market_uncertainty)

# 弱トレンド: 0.25～0.50の動的範囲
weak_confidence = 0.35 + weak_bonus * (1 + market_uncertainty)
```

#### **ATRBased戦略**: ボラティリティ追従システム
```python
# BB+RSI一致: 0.65上限の動的調整
agreement_confidence = combined_base * (1 + market_uncertainty)

# 単独シグナル: 0.70倍減額 + 動的調整
single_confidence = base_confidence * 0.7 * (1 + market_uncertainty)
```

### **設定管理システム**

**設定ファイル**: `config/core/thresholds.yaml`

```yaml
# 共通市場不確実性パラメータ
dynamic_confidence:
  market_uncertainty:
    volatility_factor_max: 0.05      # ATRボラティリティ上限
    volume_factor_max: 0.03          # ボリューム異常度上限
    price_factor_max: 0.02           # 価格変動率上限
    uncertainty_max: 0.10            # 市場不確実性最大値
    uncertainty_boost: 1.5           # 不確実性ブースト係数

  # 戦略別動的信頼度パラメータ
  strategies:
    mochipoy_alert:
      buy_strong_base: 0.70          # 2票以上賛成時基準信頼度
      buy_strong_max: 0.95           # 2票以上賛成時最大信頼度
      buy_weak_base: 0.45            # 1票賛成時基準信頼度
      hold_base: 0.20                # HOLD時基準信頼度
      hold_max: 0.35                 # HOLD時最大信頼度

    multi_timeframe:
      agreement_base: 0.75           # 両軸一致時基準信頼度
      agreement_max: 1.05            # 両軸一致時最大信頼度
      weighted_base: 0.50            # 重み付け基準信頼度

    donchian_channel:
      breakout_base: 0.60            # ブレイクアウト基準信頼度
      breakout_max: 0.85             # ブレイクアウト最大信頼度
      hold_base: 0.30                # レンジ内基準信頼度
      hold_max: 0.45                 # レンジ内最大信頼度

    adx_trend:
      strong_base: 0.65              # 強トレンド基準信頼度
      strong_max: 0.85               # 強トレンド最大信頼度
      weak_base: 0.35                # 弱トレンド基準信頼度
      weak_max: 0.50                 # 弱トレンド最大信頼度

    atr_based:
      agreement_max: 0.65            # 一致時最大信頼度
      weak_base: 0.08                # 微弱シグナル基準値
      volatility_bonus: 1.02         # 高ボラティリティボーナス
```

## 🎯 戦略選択ガイド

### **市場状況別推奨戦略**

**高ボラティリティ・トレンド相場**:
```python
recommended = ["ATRBased", "MultiTimeframe", "ADXTrendStrength"]
```

**横ばい・レンジ相場**:
```python
recommended = ["MochipoyAlert", "DonchianChannel"]
```

**ブレイクアウト期待相場**:
```python
recommended = ["DonchianChannel", "ADXTrendStrength"]
```

**不明確な相場**:
```python
recommended = ["ATRBased", "MochipoyAlert", "MultiTimeframe"]  # バランス型
```

## 🧪 テスト

```bash
# 全戦略テスト実行
python -m pytest tests/unit/strategies/implementations/ -v

# 個別戦略テスト
python -m pytest tests/unit/strategies/implementations/test_atr_based.py -v
python -m pytest tests/unit/strategies/implementations/test_mochipoy_alert.py -v

# 統合基盤確認
python scripts/testing/dev_check.py validate --mode light
```

**テスト構成**:
- **ATRBased**: 15テスト（ボラティリティ分析・エントリー判定等）
- **MochipoyAlert**: 15テスト（RCI分析・多数決システム等）
- **MultiTimeframe**: 15テスト（時間軸統合・トレンド整合性等）
- **DonchianChannel**: 15テスト（ブレイクアウト検知等）
- **ADXTrendStrength**: 15テスト（トレンド強度分析等）

## ⚠️ 重要事項

### **特性・制約**
- **15特徴量統一**: feature_order.json準拠・順序厳守必須
- **動的信頼度**: 各戦略が市場状況に応じて0.2-0.8範囲で動的計算
- **統一インターフェース**: 全戦略がStrategyBase継承・StrategySignal統一形式
- **設定一元化**: thresholds.yaml一括管理・再起動で設定反映
- **Phase 29最適化**: Phaseマーカー統一・実用性重視・簡潔化完了
- **依存**: pandas・datetime・src.strategies.base・src.core.*

---

**取引戦略実装群（Phase 28完了・Phase 29最適化）**: 5戦略統合による多様な市場対応・動的信頼度計算・統一設定管理システム。