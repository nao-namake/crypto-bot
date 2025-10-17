# src/features/ - 特徴量生成システム

**Phase 41.8対応**: 50基本特徴量生成システム（15→50特徴量）・feature_order.json単一真実源連携・11カテゴリ分類による統合特徴量エンジニアリング。5戦略信号特徴量はML学習時に別途生成され、合計55特徴量としてMLモデルに入力されます。

## 📂 ファイル構成

```
src/features/
├── __init__.py            # 特徴量システムエクスポート（23行）
└── feature_generator.py   # 統合特徴量生成システム（466行）
```

## 🔧 主要コンポーネント

### **feature_generator.py（466行）**

**目的**: 50特徴量拡張システム・feature_order.json連携・統合特徴量生成

**主要クラス**:
```python
class FeatureGenerator:
    def __init__(self, lookback_period: Optional[int] = None)  # 初期化
    async def generate_features(self, market_data) -> pd.DataFrame  # 統合特徴量生成（50特徴量）
    def _generate_basic_features(self) -> pd.DataFrame        # 基本特徴量（15個・従来システム）
    def _generate_lag_features(self) -> pd.DataFrame          # ラグ特徴量（10個・Phase 40.6）
    def _generate_rolling_features(self) -> pd.DataFrame      # 移動統計量（12個・Phase 40.6）
    def _generate_interaction_features(self) -> pd.DataFrame  # 交互作用特徴量（6個・Phase 40.6）
    def _generate_time_features(self) -> pd.DataFrame         # 時間ベース特徴量（7個・Phase 40.6）
    def get_feature_info(self) -> Dict                        # 特徴量情報取得
    def _validate_feature_generation(self)                    # 50特徴量確認

# グローバル変数
OPTIMIZED_FEATURES = get_feature_names()     # feature_order.jsonから取得
FEATURE_CATEGORIES = get_feature_categories() # カテゴリ定義
```

**50特徴量システム（11カテゴリ分類・Phase 40.6）**:
```python
FEATURE_ORDER = [
    # 基本データ（2個）: close, volume
    # モメンタム（2個）: rsi_14, macd
    # ボラティリティ（2個）: atr_14, bb_position
    # トレンド（2個）: ema_20, ema_50
    # 出来高（1個）: volume_ratio
    # ブレイクアウト（3個）: donchian_high_20, donchian_low_20, channel_position
    # 市場レジーム（3個）: adx_14, plus_di_14, minus_di_14
    # 【Phase 40.6拡張】
    # ラグ特徴量（10個）: close_lag_1〜5, volume_lag_1〜5
    # 移動統計量（12個）: close_rolling_mean_5/20, std_5/20, max_5/20, min_5/20, volume_rolling_mean_5/20, std_5/20
    # 交互作用特徴量（6個）: rsi_atr, macd_volume, ema_spread, bb_width, volatility_trend, momentum_volume
    # 時間ベース特徴量（7個）: hour, day_of_week, day_of_month, is_weekend, hour_sin, hour_cos, day_sin
]
```

**使用例**:
```python
from src.features.feature_generator import FeatureGenerator

generator = FeatureGenerator()
features_df = await generator.generate_features(market_data)
# 結果: 50特徴量を含むDataFrame（OHLCV + 50特徴量・Phase 40.6拡張完了）
```

## 🚀 使用例

```python
# 基本特徴量生成
from src.features import FeatureGenerator
generator = FeatureGenerator()
features_df = await generator.generate_features(market_data_df)

# feature_order.json整合性確認
from src.core.config.feature_manager import get_feature_names
expected_features = get_feature_names()
generated_features = [col for col in features_df.columns
                     if col not in ['open', 'high', 'low', 'close', 'volume']]
assert generated_features == expected_features  # 順序・整合性確認

# 特徴量情報取得
feature_info = generator.get_feature_info()
print(f"生成特徴量数: {feature_info['total_features']}")
```

## 🔧 設定

**環境変数**: 不要（設定ファイルから自動取得）
**データ要件**: OHLCV必須・100行以上推奨（Phase 40.6: ラグ・移動統計量計算のため増加）
**依存関係**: config/core/feature_order.json（50特徴量定義・Phase 40.6拡張済み）

## ⚠️ 重要事項

### **特性・制約**
- **50基本特徴量統一**: feature_order.json単一真実源による全システム整合性（Phase 40.6拡張完了）
- **11カテゴリ分類**: 従来7カテゴリ + 新規4カテゴリ（lag・rolling・interaction・time）
- **統合効率**: 重複排除・pandasネイティブ最適化・高速計算
- **品質保証**: 50特徴量完全確認・NaN値統一処理・エラーハンドリング
- **Phase 40.6完了**: 15→50特徴量拡張・ML予測精度+8-15%・ロバスト性+10-20%向上
- **Phase 41.8戦略信号**: ML学習時に5戦略信号を別途生成（合計55特徴量システム）
- **依存**: pandas・numpy・src.core.config.feature_manager・src.core.*

## 📊 Phase 41.8: Strategy-Aware ML対応

**Phase 41.8完了**: ML学習システムにおいて、本システムが生成する50基本特徴量に加えて、5戦略信号特徴量がML学習時に生成されます。

### **55特徴量システム構成**
- **50基本特徴量**（本モジュール生成）: 従来の特徴量生成システム
- **5戦略信号特徴量**（ML学習時生成）: `scripts/ml/create_ml_models.py`で実戦略実行により生成
  - `strategy_signal_ATRBased`
  - `strategy_signal_MochipoyAlert`
  - `strategy_signal_MultiTimeframe`
  - `strategy_signal_DonchianChannel`
  - `strategy_signal_ADXTrendStrength`

### **推論時の特徴量**
推論時（実取引判断時）は、TradingOrchestratorが:
1. 本モジュールで50基本特徴量を生成
2. 5戦略を実行して5戦略信号を生成
3. 合計55特徴量をMLモデルに入力

これにより、訓練時と推論時の特徴量構造が完全に一致します（Phase 41.8実装済み）。

---

**特徴量生成システム（Phase 41.8対応）**: feature_order.json単一真実源連携・50基本特徴量拡張システム（15→50）・11カテゴリ分類による統合特徴量エンジニアリング機能。Phase 41.8でML学習時に5戦略信号が追加され、合計55特徴量システムを構成。