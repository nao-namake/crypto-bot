# Phase 54.2 変更前設定バックアップ

**作成日**: 2025/12/16
**目的**: ロールバック用に変更前の設定値を記録

---

## 1. tight_range戦略重み配分（変更前）

**ファイル**: `config/core/thresholds.yaml` L275-282

```yaml
tight_range:  # 狭いレンジ相場（BB幅 < 3%, 価格変動 < 2%）
  # Phase 51.8-10: レンジ型戦略95%集中（理論的初期値）
  ATRBased: 0.45            # 主力
  BBReversal: 0.35          # BB反転
  DonchianChannel: 0.10     # ブレイクアウト
  StochasticReversal: 0.10  # Stochastic
  ADXTrendStrength: 0.0     # 無効化
  MACDEMACrossover: 0.0     # 無効化
```

---

## 2. ATRBased戦略設定（変更前）

**ファイル**: `config/core/thresholds.yaml`

```yaml
atr_based:
  bb_overbought: 0.7        # BB上限閾値
  bb_oversold: 0.3          # BB下限閾値
  rsi_overbought: 65        # RSI売り閾値
  rsi_oversold: 35          # RSI買い閾値
  high_volatility_strength: 0.5
  normal_volatility_strength: 0.25
  low_volatility_strength: 0.2
  min_confidence: 0.25      # 最低信頼度
  hold_confidence: 0.15
```

---

## 3. DonchianChannel戦略設定（変更前）

**ファイル**: `config/core/thresholds.yaml`

```yaml
donchian_channel:
  breakout_threshold: 0.95
  reversal_threshold: 0.05
  middle_zone_upper: 0.60
  middle_zone_lower: 0.40
  min_confidence: 0.30
  hold_confidence: 0.20
  volume_threshold: 1.2
  # weak_signal_enabled: 設定なし（コード内デフォルトでtrue）
```

---

## 4. ATRBased戦略コード（変更対象箇所）

**ファイル**: `src/strategies/implementations/atr_based.py`

### BB位置分析（L104-140）
```python
# 現在の閾値
bb_overbought = get_threshold("strategies.atr_based.bb_overbought", 0.7)
bb_oversold = get_threshold("strategies.atr_based.bb_oversold", 0.3)
```

### RSI分析（L142-194）
```python
# 現在の閾値
rsi_overbought = get_threshold("strategies.atr_based.rsi_overbought", 65)
rsi_oversold = get_threshold("strategies.atr_based.rsi_oversold", 35)
```

### 微弱シグナル生成（L263-396）
```python
# 現在: 乖離度 > 0.25 で微弱シグナル生成
if total_deviation > 0.25:
    weak_base = 0.08
    weak_multiplier = 0.1
    confidence = weak_base + total_deviation * weak_multiplier
```

---

## 5. DonchianChannel戦略コード（変更対象箇所）

**ファイル**: `src/strategies/implementations/donchian_channel.py`

### 弱シグナルゾーン判定（L210-321）
```python
# 現在: 弱シグナルゾーンでもエントリー
in_weak_buy_zone = 0.25 <= channel_position < 0.4
in_weak_sell_zone = 0.6 < channel_position <= 0.75
```

---

## ロールバック方法

### 設定ファイル
```bash
git checkout HEAD -- config/core/thresholds.yaml
```

### コードファイル
```bash
git checkout HEAD -- src/strategies/implementations/atr_based.py
git checkout HEAD -- src/strategies/implementations/donchian_channel.py
```

### 全体ロールバック（Phase 53.13へ）
```bash
git checkout b4d2f99c -- config/core/thresholds.yaml
git checkout b4d2f99c -- src/strategies/implementations/
```

---

**バックアップ作成日時**: 2025/12/16
