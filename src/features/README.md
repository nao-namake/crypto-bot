# 📈 特徴量生成システム

**最終更新**: 2025/11/16 (Phase 52.4-B)

## 🎯 概要

AI自動取引システムの特徴量生成層。55特徴量固定システム（49基本+6戦略シグナル）。

### 現状（Phase 52.4-B）

- ✅ **55特徴量固定**: 49基本特徴量+6戦略シグナル特徴量
- ✅ **設定駆動型**: feature_order.json単一真実源連携
- ✅ **統合効率**: 重複排除・pandasネイティブ最適化
- ✅ **品質保証**: 55特徴量完全確認・NaN値統一処理

### 開発履歴

**Phase 52.4-B（2025/11/16）**: コード整理・ドキュメント統一完了
**Phase 51.7 Day 7（2025/11/07）**: 6戦略統合・55特徴量システム確立
**Phase 51.7 Day 2**: Feature Importance分析に基づく最適化（60→51特徴量）
**Phase 50.9**: 外部API完全削除・シンプル設計回帰（60特徴量固定）
**Phase 50.2**: 時間的特徴量拡張（55→60特徴量）
**Phase 50.1**: 確実な特徴量生成実装
**Phase 41**: Strategy-Aware ML実装（50→55特徴量）
**Phase 40.6**: Feature Engineering拡張（15→50特徴量）
**Phase 38.4**: 97→15特徴量最適化

---

## 📂 ファイル構成

```
src/features/
├── __init__.py            # 遅延インポート・循環インポート回避
└── feature_generator.py   # 統合特徴量生成システム
```

---

## 🔧 主要コンポーネント

### **feature_generator.py**

統合特徴量生成システム（55特徴量固定）

#### 主要クラス

```python
class FeatureGenerator:
    """統合特徴量生成クラス"""

    def __init__(self, lookback_period: Optional[int] = None)

    # 非同期版（ライブトレード・ペーパートレード用）
    async def generate_features(
        self, market_data, strategy_signals=None
    ) -> pd.DataFrame

    # 同期版（バックテスト事前計算用）
    def generate_features_sync(
        self, df, strategy_signals=None
    ) -> pd.DataFrame

    # 内部メソッド（特徴量カテゴリ別）
    def _generate_basic_features() -> pd.DataFrame        # 基本（2個）
    def _generate_technical_indicators() -> pd.DataFrame  # テクニカル（17個）
    def _generate_anomaly_indicators() -> pd.DataFrame    # 異常検知（1個）
    def _generate_lag_features() -> pd.DataFrame          # ラグ（9個）
    def _generate_rolling_statistics() -> pd.DataFrame    # 移動統計（5個）
    def _generate_interaction_features() -> pd.DataFrame  # 交互作用（5個）
    def _generate_time_features() -> pd.DataFrame         # 時間的（7個）
    def _add_strategy_signal_features() -> pd.DataFrame   # 戦略シグナル（6個）

    # ユーティリティ
    def get_feature_info() -> Dict  # 特徴量情報取得
```

#### グローバル定数

**Phase 52.4-B: Magic number抽出**

```python
# テクニカル指標パラメータ
RSI_PERIOD = 14
MACD_FAST_PERIOD = 12
MACD_SLOW_PERIOD = 26
MACD_SIGNAL_PERIOD = 9
ATR_PERIOD = 14
BB_PERIOD = 20
BB_STD_MULTIPLIER = 2
EMA_SHORT_PERIOD = 20
EMA_LONG_PERIOD = 50
DONCHIAN_PERIOD = 20
ADX_PERIOD = 14
STOCHASTIC_PERIOD = 14
STOCHASTIC_SMOOTH_K = 3
STOCHASTIC_SMOOTH_D = 3
VOLUME_EMA_PERIOD = 20

# ラグ・ローリング設定
LAG_PERIODS_CLOSE = [1, 2, 3, 10]
LAG_PERIODS_VOLUME = [1, 2, 3]
LAG_PERIODS_INDICATOR = [1]
ROLLING_WINDOWS_MA = [10, 20]
ROLLING_WINDOWS_STD = [5, 10, 20]

# 市場時間（JST）
MARKET_OPEN_HOUR = 9
MARKET_CLOSE_HOUR = 15
EUROPE_SESSION_START = 16
EUROPE_SESSION_END_HOUR = 23
EUROPE_SESSION_EARLY_HOUR = 1

# 数値安定性・周期性
EPSILON = 1e-8
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7
```

---

## 📊 55特徴量システム構成

### **49基本特徴量**

1. **基本データ（2個）**: close, volume
2. **テクニカル指標（17個）**:
   - RSI: rsi_14
   - MACD: macd, macd_signal, macd_histogram
   - ATR: atr_14
   - Bollinger Bands: bb_upper, bb_lower, bb_position
   - EMA: ema_20, ema_50
   - Donchian Channel: donchian_high_20, donchian_low_20, channel_position
   - ADX: adx_14, plus_di_14, minus_di_14
   - Stochastic: stoch_k, stoch_d
   - Volume: volume_ema, atr_ratio
3. **異常検知（1個）**: volume_ratio
4. **ラグ特徴量（9個）**: close_lag_1/2/3/10, volume_lag_1/2/3, rsi_lag_1, macd_lag_1
5. **移動統計量（5個）**: close_ma_10/20, close_std_5/10/20
6. **交互作用特徴量（5個）**: rsi_x_atr, macd_x_volume, bb_position_x_volume_ratio, close_x_atr, volume_x_bb_position
7. **時間的特徴量（7個）**: hour, day_of_week, is_market_open_hour, is_europe_session, hour_cos, day_sin, day_cos

### **6戦略シグナル特徴量**

Phase 52.4-B: strategies.yamlから動的取得

- strategy_signal_ATRBased
- strategy_signal_DonchianChannel
- strategy_signal_ADXTrendStrength
- strategy_signal_BBReversal
- strategy_signal_StochasticReversal
- strategy_signal_MACDEMACrossover

---

## 🚀 使用例

### 基本的な使い方

```python
from src.features import FeatureGenerator

# インスタンス生成
generator = FeatureGenerator()

# 非同期版（ライブトレード・ペーパートレード）
features_df = await generator.generate_features(
    market_data=market_data_dict,
    strategy_signals=strategy_signals_dict  # オプション
)

# 同期版（バックテスト事前計算）
features_df = generator.generate_features_sync(
    df=ohlcv_df,
    strategy_signals=strategy_signals_dict  # オプション
)

# 特徴量情報取得
feature_info = generator.get_feature_info()
print(f"生成特徴量数: {feature_info['total_features']}")
```

### feature_order.json整合性確認

```python
from src.core.config.feature_manager import get_feature_names

expected_features = get_feature_names()
generated_features = [col for col in features_df.columns
                     if col not in ['open', 'high', 'low', 'close', 'volume']]
assert generated_features == expected_features  # 順序・整合性確認
```

---

## ⚙️ 設定

### データ要件

- **必須列**: open, high, low, close, volume
- **推奨行数**: 100行以上（ラグ・移動統計量計算のため）
- **形式**: pandas.DataFrame または dict

### 依存関係

- **設定ファイル**: config/core/feature_order.json（55特徴量定義）
- **ライブラリ**: pandas, numpy
- **内部依存**: src.core.config.feature_manager, src.core.logger, src.strategies.strategy_loader

---

## ⚠️ 重要事項

### 特性・制約

- **55特徴量固定**: feature_order.json単一真実源による全システム整合性
- **設定駆動型**: strategies.yamlから戦略シグナル特徴量を動的取得
- **確実な生成**: strategy_signals=None時も0.0埋めで6特徴量追加
- **統合効率**: 重複排除・pandasネイティブ最適化・高速計算
- **品質保証**: 55特徴量完全確認・NaN値統一処理・エラーハンドリング

### Phase 52.4-B: コード品質改善

- Magic number完全抽出（グローバル定数化）
- Phase参照統一（Phase 52.4-B対応完了）
- ドキュメント整理（開発履歴・使用例・設定明確化）

---

**Phase 52.4-B完了**: コード整理・ドキュメント統一・55特徴量固定システム（49基本+6戦略シグナル）・設定駆動型特徴量生成
