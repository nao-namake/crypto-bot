# config/backtest/ - バックテスト設定管理

## 📋 概要

**Backtest Configuration Management**  
production.ymlを踏襲したバックテスト設定を管理し、97特徴量から選択した指標組み合わせのテストを可能にします。

## 🎯 主要機能

### **指標組み合わせテスト**
- 97特徴量から任意の指標を選択
- production設定を基にしたバックテスト実行
- 固定ファイル名・絶対パス対応
- ウォークフォワード分析対応

### **設定継承システム**
- production.ymlから核心設定を継承
- バックテスト固有の設定を追加
- 軽量化されたテスト設定

## 📁 ファイル構成

```
config/backtest/
├── README.md                          # このファイル（使用方法）
├── base_backtest_config.yml           # ベース設定（97特徴量フル）
├── indicator_combination_samples.yml  # 指標組み合わせサンプル集
└── test_rsi_macd_ema.yml              # 実際のテスト用設定例
```

## 🚀 使用方法

### **1. 基本的なバックテスト実行**
```bash
# RSI + MACD + EMAテスト実行
python -m crypto_bot.main backtest --config config/backtest/test_rsi_macd_ema.yml

# 結果確認
ls -la results/backtest/
```

### **2. カスタム指標組み合わせテスト**

#### ステップ1: 設定ファイルをコピー
```bash
cp config/backtest/base_backtest_config.yml config/backtest/my_test.yml
```

#### ステップ2: 特徴量を選択して編集
```yaml
# my_test.yml の ml.extra_features セクションを編集
ml:
  extra_features:
    # ボリンジャーバンド + RSI の組み合わせ例
    - bb_position
    - bb_upper
    - bb_lower
    - bb_width
    - rsi_14
    - rsi_oversold
    - rsi_overbought
    - close_lag_1
    - volume_ratio
    - atr_14
```

#### ステップ3: バックテスト実行
```bash
python -m crypto_bot.main backtest --config config/backtest/my_test.yml
```

### **3. 利用可能な97特徴量一覧**

#### **価格・リターン系**
- `close_lag_1`, `close_lag_3` - 価格ラグ
- `returns_1`, `returns_2`, `returns_3`, `returns_5`, `returns_10` - リターン系

#### **移動平均系**
- `ema_5`, `ema_10`, `ema_20`, `ema_50`, `ema_100`, `ema_200` - EMA各期間
- `price_position_20`, `price_position_50` - 価格ポジション
- `price_vs_sma20` - SMA比較

#### **ボリンジャーバンド系**
- `bb_position`, `bb_upper`, `bb_middle`, `bb_lower` - バンド位置・値
- `bb_width`, `bb_squeeze` - バンド幅・スクイーズ

#### **オシレーター系**
- `rsi_14`, `rsi_oversold`, `rsi_overbought` - RSI系
- `macd`, `macd_signal`, `macd_hist`, `macd_cross_up`, `macd_cross_down` - MACD系
- `stoch_k`, `stoch_d`, `stoch_oversold`, `stoch_overbought` - ストキャスティクス

#### **ボラティリティ・ATR系**
- `atr_14`, `volatility_20` - ボラティリティ指標

#### **ボリューム系**
- `volume_lag_1`, `volume_lag_4`, `volume_lag_5` - ボリュームラグ
- `volume_sma_20`, `volume_ratio`, `volume_trend` - ボリューム分析
- `vwap`, `vwap_distance` - VWAP系

#### **マネーフロー系**
- `obv`, `obv_sma` - OBV（オンバランスボリューム）
- `cmf`, `mfi`, `ad_line` - マネーフロー指標

#### **トレンド系**
- `adx_14`, `plus_di`, `minus_di` - ADX・DMI
- `trend_strength`, `trend_direction` - トレンド判定
- `cci_20`, `williams_r`, `ultimate_oscillator`, `momentum_14` - その他オシレーター

#### **サポート・レジスタンス系**
- `support_distance`, `resistance_distance`, `support_strength`
- `price_breakout_up`, `price_breakout_down`, `volume_breakout`

#### **キャンドルスティックパターン**
- `doji`, `hammer`, `engulfing`, `pinbar`

#### **統計・その他**
- `zscore`, `close_std_10` - 統計指標
- `roc_10`, `roc_20`, `trix`, `mass_index` - レート・その他

#### **チャネル・エンベロープ系**
- `keltner_upper`, `keltner_lower` - ケルトナーチャネル
- `donchian_upper`, `donchian_lower` - ドンチャンチャネル
- `ichimoku_conv`, `ichimoku_base` - 一目均衡表

#### **高度な市場分析**
- `price_efficiency`, `trend_consistency`, `volume_price_correlation`
- `volatility_regime`, `momentum_quality`, `market_phase`

#### **時間・セッション系**
- `hour`, `day_of_week`, `is_weekend`
- `is_asian_session`, `is_us_session`

## 💡 指標組み合わせのアイデア

### **トレンドフォロー戦略**
```yaml
extra_features:
  - ema_20
  - ema_50
  - macd
  - adx_14
  - trend_direction
  - close_lag_1
```

### **逆張り戦略**
```yaml
extra_features:
  - rsi_14
  - rsi_oversold
  - rsi_overbought
  - bb_position
  - stoch_k
  - stoch_d
```

### **ボリューム重視戦略**
```yaml
extra_features:
  - vwap
  - obv
  - volume_ratio
  - volume_breakout
  - cmf
  - mfi
```

### **ブレイクアウト戦略**
```yaml
extra_features:
  - donchian_upper
  - donchian_lower
  - price_breakout_up
  - price_breakout_down
  - atr_14
  - volume_breakout
```

## ⚙️ 設定カスタマイズ

### **バックテスト期間調整**
```yaml
walk_forward:
  train_window: 1500  # 学習期間（時間数）
  test_window: 250    # テスト期間（時間数）
  step: 125           # 移動幅（時間数）
```

### **信頼度閾値調整**
```yaml
ml:
  confidence_threshold: 0.25  # 0.15-0.4 推奨範囲
strategy:
  confidence_threshold: 0.25  # 同じ値に設定
```

### **データ量調整**
```yaml
data:
  limit: 500        # 取得データ数（テスト用）
  since_hours: 96   # データ取得期間（時間）
```

## 📊 結果確認方法

### **結果ファイル場所**
```bash
results/backtest/
├── {test_name}_performance.png    # パフォーマンスチャート
├── {test_name}_portfolio.csv      # ポートフォリオ推移
└── {test_name}_trades.csv         # 個別取引記録
```

### **重要メトリクス**
- **Total Return**: 総リターン（%）
- **Sharpe Ratio**: リスク調整後リターン
- **Max Drawdown**: 最大ドローダウン（%）
- **Win Rate**: 勝率（%）
- **Profit Factor**: プロフィットファクター

## ⚠️ 注意事項

### **データ品質**
- バックテストは過去データに基づく（フォワードテスト必要）
- オーバーフィッティングに注意
- 十分なデータ量確保（最低1000時間以上推奨）

### **計算リソース**
- 特徴量が多いほど計算時間増加
- 20-30特徴量程度が実用的
- テスト時はlimit値を小さく設定

### **設定の一貫性**
- strategy.params.ml.extra_features と ml.extra_features を一致させる
- confidence_threshold は ml と strategy で同じ値に設定

## 🔍 トラブルシューティング

### **よくあるエラー**

**1. 特徴量不一致エラー**
```
# 原因: strategy.params.ml.extra_features と ml.extra_features が不一致
# 解決: 両方に同じ特徴量リストを設定
```

**2. データ不足エラー**
```
# 原因: walk_forward の window が大きすぎる
# 解決: train_window, test_window を小さく設定
```

**3. モデル読み込みエラー**
```
# 原因: model.pkl が存在しない
# 解決: python scripts/model_tools/create_proper_ensemble_model.py を実行
```

## 📈 次のステップ

1. **基本テスト実行**: RSI + MACD + EMA から開始
2. **指標組み合わせ探索**: サンプルから選択してテスト
3. **パラメータ最適化**: 有効な組み合わせの閾値調整
4. **ペーパートレード検証**: バックテスト結果をリアルタイムで検証
5. **本番適用**: 検証済み指標組み合わせを production.yml に反映