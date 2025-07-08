# 🔍 特徴量システム完全分析レポート

## 📊 実際の特徴量構成（85特徴量確認済み）

**分析日時**: 2025-07-08 13:52  
**設定**: BASELINE_79pct_winrate.yml  
**実際生成数**: **85特徴量** (設定65 → 実際85)

### 🏗️ 特徴量詳細構成

#### **1. 基本OHLCV (5特徴量)**
1. open
2. high  
3. low
4. close
5. volume

#### **2. 基本ML特徴量 (15特徴量)**
6. ATR_14
7-18. close_lag_1 ~ close_lag_12 (12個)
19. close_mean_20
20. close_std_20

#### **3. テクニカル指標 (28特徴量)**

**基本テクニカル (6特徴量):**
21. rsi_14
22-24. macd, macd_signal, macd_hist (3個)
25. rci_9
26. volume_zscore_20
27. sma_200
28. ema_50

**高度テクニカル (14特徴量):**
29-30. stoch_k, stoch_d (2個)
31-35. bb_upper, bb_middle, bb_lower, bb_percent, bb_width (5個)
36-38. adx, di_plus, di_minus (3個)
39. willr_14
40. cmf_20
41-42. fisher, fisher_signal (2個)

**移動平均追加 (8特徴量):**
78. sma_50
79. sma_100
80. ema_12
81. ema_26
82. sma_20
83. ema_20
84. sma_10
85. ema_10

#### **4. マクロ経済統合 (33特徴量)**

**Fear & Greed Index (13特徴量):**
43-55. fg_level, fg_change, fg_change_abs, fg_sma_7, fg_sma_14, fg_deviation, fg_zscore, fg_regime, fg_extreme_fear, fg_extreme_greed, fg_momentum, fg_volatility, fg_fear_streak, fg_greed_streak

**Funding Rate & OI (17特徴量):**
56-73. fr_rate, fr_change_1d, fr_change_3d, fr_zscore_7d, fr_zscore_30d, fr_regime, fr_extreme_long, fr_extreme_short, fr_volatility, fr_trend_strength, oi_normalized, oi_change_1d, oi_momentum_3d, oi_zscore_7d, oi_new_high, oi_new_low, position_bias

**VIX特徴量**: 現在の設定では生成されていない（データアライメント問題）
**DXY特徴量**: 現在の設定では生成されていない（データアライメント問題）

#### **5. 時間・シグナル特徴量 (4特徴量)**
74. day_of_week
75. hour_of_day
76. mochipoyo_long_signal
77. mochipoyo_short_signal

### ⚠️ **重要発見事項**

1. **特徴量数の真実**: 設定65特徴量 → 実際85特徴量
2. **VIX・DXYの欠落**: データアライメント問題で実際には生成されていない
3. **実用的な構成**: 85特徴量でも79.7%勝率を達成している
4. **安定した生成**: 基本的な特徴量は確実に生成されている

### 🔧 **修正すべき課題**

1. **VIX特徴量の復活**: データアライメント修正が必要
2. **DXY特徴量の復活**: マクロデータ取得の改善が必要
3. **特徴量数の一致**: 設定値と実際値の整合性確保
4. **エラーハンドリング**: データ取得失敗時の適切な代替処理

### 🎯 **推奨アクション**

1. **現在の85特徴量を「実用ベースライン」として確定**
2. **VIX・DXY復活版を「拡張版100特徴量システム」として開発**
3. **特徴量数明記の正確な設定ファイル作成**
4. **データ品質監視システムの導入**

## 📁 **対応するモデル情報**

- **モデルファイル**: model_90features_baseline.pkl
- **実際の入力**: 85特徴量
- **学習サンプル数**: 1,859サンプル
- **モデルタイプ**: LogisticRegression
- **パフォーマンス**: 79.7%勝率、シャープレシオ16.13

この分析により、79.7%勝率達成の**真の技術基盤**が明確になりました。