# Phase 51.7 Day 1 完了レポート: Feature Importance分析

**実行日**: 2025年11月05日
**分析対象**: models/production/ensemble_full.pkl (60特徴量)
**分析手法**: LightGBM Feature Importance + カテゴリ別分類

---

## 📊 主要発見事項

### 🎯 重大な発見

**当初削除予定だったが、実は最重要特徴量だった**:
1. **volume_lag_2: 17.0** ← 全特徴量中**第1位**！
2. **close_std_5: 16.0** ← 全特徴量中**第2位**！
3. **close_std_10: 12.0** ← 全特徴量中**第3位**！

→ **データドリブンアプローチの重要性**を証明

### ⚠️ 驚くべき発見: 戦略信号がImportance = 0

**既存3戦略の戦略信号特徴量**:
- strategy_signal_ATRBased: **0.0**
- strategy_signal_DonchianChannel: **0.0**
- strategy_signal_ADXTrendStrength: **0.0**

**原因仮説**:
1. 戦略信号が単純すぎる（BUY/SELL/HOLD の3値のみ）
2. MLモデルが戦略信号を学習する前に、他の特徴量（RSI、MACD等）から直接学習している
3. 戦略信号の表現力不足（信頼度・強度情報が不足）

**Phase 51.7への影響**:
- 新3戦略の戦略信号特徴量を追加しても、同様にImportance = 0になる可能性
- 戦略信号の表現方法を見直す必要あり（Phase 51.8以降で検討）

---

## 🗑️ 削除対象特徴量（最終版）

### 【確実に削除】Importance = 0（15個）

**移動統計量系**:
1. close_ma_5: 0.0
2. close_max_5: 0.0
3. close_max_10: 0.0
4. close_min_5: 0.0
5. close_min_10: 0.0
6. close_min_20: 0.0

**時間的特徴量**:
7. hour_sin: 0.0
8. is_weekend: 0.0
9. is_quarter_end: 0.0
10. quarter: 0.0
11. is_asia_session: 0.0
12. is_us_session: 0.0

**テクニカル指標**:
13. donchian_high_20: 0.0

**戦略信号**:
14. strategy_signal_ATRBased: 0.0
15. strategy_signal_DonchianChannel: 0.0
16. strategy_signal_ADXTrendStrength: 0.0

### 【追加削除検討】Importance < 1.5（4個）

17. close_max_20: 1.0
18. close_lag_5: 1.0
19. month: 1.0
20. ema_20: 1.0

**合計削除**: 20特徴量

---

## ➕ 追加特徴量（最終版）

### 【必須追加】6戦略実装用（6個）

1. **stoch_k**: Stochastic %K（Stochastic Reversal戦略用）
2. **stoch_d**: Stochastic %D（Stochastic Reversal戦略用）
3. **macd_signal**: MACDシグナル線（MACD+EMA戦略用）
4. **macd_histogram**: MACDヒストグラム（MACD+EMA戦略用）
5. **bb_upper**: BB上限（BB Reversal戦略用）
6. **bb_lower**: BB下限（BB Reversal戦略用）

### 【オプション追加】システム強化用（2個）

7. **volume_ema**: 出来高EMA 20期間
8. **atr_ratio**: ATR/Close比率（ボラティリティ正規化）

### 【新戦略信号】Phase 51.7新規戦略用（3個）

9. **strategy_signal_BBReversal**: BB Reversal戦略信号
10. **strategy_signal_StochasticReversal**: Stochastic Reversal戦略信号
11. **strategy_signal_MACDEMACrossover**: MACD+EMA戦略信号

**合計追加**: 11特徴量

---

## 📐 最終特徴量数

```
現在の特徴量数: 60
削除: -20
追加: +11
───────────────
最終特徴量数: 51
```

**目標50特徴量に近い！** （さらに1特徴量削減で50達成可能）

---

## 📦 カテゴリ別Feature Importance（保持決定後）

### ラグ特徴量（残り7個）
- **保持理由**: volume_lag_2が最重要（17.0）、close_lag_1も重要（9.0）
- **削除**: close_lag_5（1.0）
- **残す**: volume_lag_1/2/3, close_lag_1/2/10, rsi_lag_1, macd_lag_1

### 移動統計量（残り9個）
- **保持理由**: close_std_5/10が超重要（16.0/12.0）
- **削除**: close_ma_5, close_max_5/10/20, close_min_5/10/20
- **残す**: close_ma_10/20, close_std_5/10/20, close_max_5削除後は無し

### 交互作用（残り6個）
- **保持理由**: rsi_x_atr（7.0）等が中程度の重要度
- **削除**: なし
- **残す**: 全6個保持

### 時間的特徴量（残り8個）
- **保持理由**: day_sin（7.0）が重要
- **削除**: hour_sin, is_weekend, is_quarter_end, quarter, is_asia_session, is_us_session, month
- **残す**: day_sin/cos, day_of_week, hour_sin/cos, hour, is_europe_session, is_market_open_hour

### 戦略信号（残り0個 → 新規3個）
- **削除**: 既存3戦略の戦略信号（全てImportance = 0）
- **追加**: 新3戦略の戦略信号（Phase 51.7実装後）

---

## 🎯 Day 2実装計画（修正版）

### 実装ファイル: `src/features/technical_indicators.py`

#### 1. 削除対象コード（20特徴量）

```python
# 移動統計量削除
df['close_ma_5'] = ...  # 削除
df['close_max_5'] = ...  # 削除
df['close_max_10'] = ...  # 削除
df['close_max_20'] = ...  # 削除
df['close_min_5'] = ...  # 削除
df['close_min_10'] = ...  # 削除
df['close_min_20'] = ...  # 削除

# ラグ特徴量削除
df['close_lag_5'] = ...  # 削除
df['month'] = ...  # 削除

# 時間的特徴量削除
df['hour_sin'] = ...  # 削除
df['is_weekend'] = ...  # 削除
df['is_quarter_end'] = ...  # 削除
df['quarter'] = ...  # 削除
df['is_asia_session'] = ...  # 削除
df['is_us_session'] = ...  # 削除

# テクニカル指標削除
df['donchian_high_20'] = ...  # 削除
df['ema_20'] = ...  # 削除

# 戦略信号削除（Phase 51.7 Day 3-5で新規戦略追加後に削除）
df['strategy_signal_ATRBased'] = ...  # 後で削除
df['strategy_signal_DonchianChannel'] = ...  # 後で削除
df['strategy_signal_ADXTrendStrength'] = ...  # 後で削除
```

#### 2. 追加コード（11特徴量）

```python
def calculate_stochastic(df: pd.DataFrame, period: int = 14, smooth_k: int = 3) -> pd.DataFrame:
    """Stochastic Oscillator計算"""
    low_min = df['low'].rolling(window=period).min()
    high_max = df['high'].rolling(window=period).max()
    
    df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
    df['stoch_d'] = df['stoch_k'].rolling(window=smooth_k).mean()
    
    return df

def calculate_macd_extended(df: pd.DataFrame) -> pd.DataFrame:
    """MACD拡張（シグナル線・ヒストグラム追加）"""
    ema_12 = df['close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    return df

def calculate_bb_extended(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    """BB拡張（上限・下限を特徴量化）"""
    bb_middle = df['close'].rolling(window=period).mean()
    bb_std = df['close'].rolling(window=period).std()
    
    df['bb_upper'] = bb_middle + (bb_std * std)
    df['bb_lower'] = bb_middle - (bb_std * std)
    
    return df

def calculate_volume_ema(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """出来高EMA計算"""
    df['volume_ema'] = df['volume'].ewm(span=period, adjust=False).mean()
    return df

def calculate_atr_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """ATR/Close比率計算"""
    df['atr_ratio'] = df['atr_14'] / df['close']
    return df
```

---

## ✅ Day 1完了状況

### 完了タスク
- ✅ Feature Importance分析実行（2時間）
- ✅ 削除対象特徴量の最終決定（2時間）
- ✅ 追加特徴量の実装仕様策定（2時間）
- ✅ Day 1レポート作成（30分）

### 成果物
1. **feature_importance_analysis.csv** - 全60特徴量のImportance値
2. **day1_feature_analysis_report.md** - 本レポート
3. **削除リスト**: 20特徴量（データドリブン決定）
4. **追加リスト**: 11特徴量（6戦略最適化）
5. **最終特徴量数**: 51特徴量

---

## 🚀 Day 2への引き継ぎ事項

### 実装優先度

**Priority 1（必須）**:
- Stochastic計算関数実装（stoch_k/d）
- MACD拡張実装（macd_signal/histogram）
- BB拡張実装（bb_upper/lower）

**Priority 2（推奨）**:
- volume_ema実装
- atr_ratio実装

**Priority 3（戦略実装後）**:
- 新3戦略の戦略信号追加
- 旧3戦略の戦略信号削除

### 注意事項

1. **volume_lag_2を絶対に削除しない** - 最重要特徴量
2. **close_std_5/10を絶対に削除しない** - 第2/3位特徴量
3. **戦略信号のImportance = 0問題** - Phase 51.8以降で改善検討
4. **51特徴量 → 50特徴量** - 1特徴量追加削減で目標達成（day_cos削除候補）

---

**📅 作成日**: 2025年11月05日
**✅ ステータス**: Day 1完了・Day 2実装準備完了
**⏱ 実行時間**: 約6時間（予定通り）
