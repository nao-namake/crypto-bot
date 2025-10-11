# src/features/ - 特徴量生成システム

**Phase 38.4完了**: 15特徴量統一システム・feature_order.json単一真実源連携・7カテゴリ分類による統合特徴量エンジニアリング。

## 📂 ファイル構成

```
src/features/
├── __init__.py            # 特徴量システムエクスポート（23行）
└── feature_generator.py   # 統合特徴量生成システム（466行）
```

## 🔧 主要コンポーネント

### **feature_generator.py（466行）**

**目的**: 15特徴量統一システム・feature_order.json連携・統合特徴量生成

**主要クラス**:
```python
class FeatureGenerator:
    def __init__(self, lookback_period: Optional[int] = None)  # 初期化
    async def generate_features(self, market_data) -> pd.DataFrame  # 統合特徴量生成
    def _generate_basic_features(self) -> pd.DataFrame        # 基本特徴量（2個）
    def _generate_technical_indicators(self) -> pd.DataFrame  # テクニカル指標（8個）
    def _generate_anomaly_indicators(self) -> pd.DataFrame    # 異常検知指標（5個）
    def get_feature_info(self) -> Dict                        # 特徴量情報取得
    def _validate_feature_generation(self)                    # 15特徴量確認

# グローバル変数
OPTIMIZED_FEATURES = get_feature_names()     # feature_order.jsonから取得
FEATURE_CATEGORIES = get_feature_categories() # カテゴリ定義
```

**15特徴量システム（7カテゴリ分類）**:
```python
FEATURE_ORDER = [
    # 基本データ（2個）: close, volume
    # モメンタム（2個）: rsi_14, macd
    # ボラティリティ（2個）: atr_14, bb_position
    # トレンド（2個）: ema_20, ema_50
    # 出来高（1個）: volume_ratio
    # ブレイクアウト（3個）: donchian_high_20, donchian_low_20, channel_position
    # 市場レジーム（3個）: adx_14, plus_di_14, minus_di_14
]
```

**使用例**:
```python
from src.features.feature_generator import FeatureGenerator

generator = FeatureGenerator()
features_df = await generator.generate_features(market_data)
# 結果: 15特徴量を含むDataFrame（OHLCV + 15特徴量）
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
**データ要件**: OHLCV必須・50行以上推奨
**依存関係**: config/core/feature_order.json（15特徴量定義）

## ⚠️ 重要事項

### **特性・制約**
- **15特徴量統一**: feature_order.json単一真実源による全システム整合性
- **7カテゴリ分類**: basic・momentum・volatility・trend・volume・breakout・regime
- **統合効率**: 重複排除・pandasネイティブ最適化・高速計算
- **品質保証**: 15特徴量完全確認・NaN値統一処理・エラーハンドリング
- **Phase 38.4完了**: Phase 28/29最適化完了状態維持・Phaseマーカー統一
- **依存**: pandas・numpy・src.core.config.feature_manager・src.core.*

---

**特徴量生成システム（Phase 38.4完了）**: feature_order.json単一真実源連携・15特徴量統一システム・7カテゴリ分類による統合特徴量エンジニアリング機能。