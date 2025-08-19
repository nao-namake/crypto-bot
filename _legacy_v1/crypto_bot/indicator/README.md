# indicator/ - テクニカル指標計算

## 📋 概要

**Technical Indicator Calculation System**  
本フォルダは crypto-bot のテクニカル指標計算機能を提供し、各種インジケーター（ATR、移動平均、MACD、RSI等）の計算を担当します。

## 🎯 主要機能

### **テクニカル指標計算**
- ATR（Average True Range）- ボラティリティ指標
- 移動平均（SMA/EMA）- トレンド指標
- MACD - トレンド転換指標
- RSI - オシレーター系指標
- RCI - 順位相関指標
- その他多数のインジケーター

### **ライブラリ統合**
- pandas-ta完全活用
- TA-Lib非依存（インストール不要）
- pandas DataFrame対応
- ベクトル化計算

## 📁 ファイル構成

```
indicator/
├── __init__.py      # パッケージ初期化
└── calculator.py    # テクニカル指標計算実装
```

## 🔍 ファイルの役割

### **calculator.py**
- `IndicatorCalculator`クラス - 指標計算本体
- pandas-taラッパー実装
- 静的メソッドによる関数型インターフェース
- NaN値処理・エラーハンドリング
- Phase H.26対応（超堅牢化版）

## 🚀 使用方法

### **基本的な指標計算**
```python
from crypto_bot.indicator.calculator import IndicatorCalculator

# ATR計算（ボラティリティ）
atr = IndicatorCalculator.calculate_atr(df, period=14)

# 移動平均計算
sma_20 = IndicatorCalculator.calculate_sma(df, period=20)
ema_50 = IndicatorCalculator.calculate_ema(df, period=50)

# MACD計算
macd_line, signal_line, histogram = IndicatorCalculator.calculate_macd(
    df, fast=12, slow=26, signal=9
)

# RSI計算
rsi = IndicatorCalculator.calculate_rsi(df, period=14)
```

### **複数指標の一括計算**
```python
# 複数のテクニカル指標を追加
df['atr_14'] = IndicatorCalculator.calculate_atr(df, 14)
df['sma_20'] = IndicatorCalculator.calculate_sma(df, 20)
df['ema_50'] = IndicatorCalculator.calculate_ema(df, 50)
df['rsi_14'] = IndicatorCalculator.calculate_rsi(df, 14)
df['macd'], df['macd_signal'], df['macd_hist'] = IndicatorCalculator.calculate_macd(df)
```

### **カスタム指標計算**
```python
# RCI（順位相関）計算
rci = IndicatorCalculator.calculate_rci(df, period=9)

# ボリンジャーバンド
bb_upper, bb_middle, bb_lower = IndicatorCalculator.calculate_bollinger_bands(
    df, period=20, std=2
)

# ストキャスティクス
stoch_k, stoch_d = IndicatorCalculator.calculate_stochastic(
    df, k_period=14, d_period=3
)
```

## ⚠️ 課題・改善点

### **ファイル数不足**
- 指標機能に対して単一ファイルのみ
- カテゴリ別分離の検討
- より多様な指標実装

### **機能拡張余地**
- カスタム指標定義機能
- 複合指標計算
- マルチタイムフレーム対応
- リアルタイム計算最適化

### **エラー処理**
- より詳細なエラーメッセージ
- 入力検証の強化
- NaN値処理の統一化

### **パフォーマンス**
- 大規模データでの最適化
- 並列計算対応
- メモリ効率改善

## 📝 今後の展開

1. **指標カテゴリ別整理**
   ```
   indicator/
   ├── trend/           # トレンド系
   │   ├── ma.py        # 移動平均
   │   ├── macd.py      # MACD
   │   └── adx.py       # ADX
   ├── oscillator/      # オシレーター系
   │   ├── rsi.py       # RSI
   │   ├── stoch.py     # ストキャスティクス
   │   └── williams.py  # Williams %R
   ├── volatility/      # ボラティリティ系
   │   ├── atr.py       # ATR
   │   ├── bb.py        # ボリンジャーバンド
   │   └── keltner.py   # ケルトナーチャネル
   └── volume/          # 出来高系
       ├── obv.py       # OBV
       ├── mfi.py       # MFI
       └── vwap.py      # VWAP
   ```

2. **高度な指標**
   - 機械学習ベース指標
   - パターン認識
   - マーケットプロファイル
   - オーダーフロー分析

3. **リアルタイム対応**
   - ストリーミング計算
   - 増分更新
   - 低レイテンシー実装
   - WebSocket統合

4. **カスタマイズ機能**
   - ユーザー定義指標
   - 指標組み合わせ
   - パラメータ最適化
   - バックテスト統合