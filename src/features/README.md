# src/features/ - 特徴量生成システム

## 🎯 役割・責任

AI自動取引システムの特徴量エンジニアリング層。テクニカル指標、異常検知指標、基本特徴量の生成を担当し、15特徴量統一システムにより機械学習モデルに高品質な入力データを提供します。feature_order.json単一真実源との連携により、全システムでの特徴量一貫性を保証します。

## 📂 ファイル構成

```
src/features/
├── __init__.py            # 特徴量システムエクスポート
└── feature_generator.py   # 統合特徴量生成システム
```

## 🔧 主要コンポーネント

### **feature_generator.py**

**目的**: 15特徴量統一システムによる統合特徴量生成・feature_order.json連携

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

# Phase 21統合: 単一クラスによる統合特徴量生成システム
```

**15特徴量システム**:
```python
# 15特徴量リスト（7カテゴリ分類）
FEATURE_ORDER = [
    # 基本データ（2個）
    "close", "volume",
    
    # モメンタム（2個）
    "rsi_14", "macd",
    
    # ボラティリティ（2個）
    "atr_14", "bb_position",
    
    # トレンド（2個）
    "ema_20", "ema_50",
    
    # 出来高（1個）
    "volume_ratio",
    
    # ブレイクアウト（3個）
    "donchian_high_20", "donchian_low_20", "channel_position",
    
    # 市場レジーム（3個）
    "adx_14", "plus_di_14", "minus_di_14"
]

# カテゴリ別分類
FEATURE_CATEGORIES = {
    "basic": ["close", "volume"],
    "momentum": ["rsi_14", "macd"],
    "volatility": ["atr_14", "bb_position"],
    "trend": ["ema_20", "ema_50"],
    "volume": ["volume_ratio"],
    "breakout": ["donchian_high_20", "donchian_low_20", "channel_position"],
    "regime": ["adx_14", "plus_di_14", "minus_di_14"]
}
```

## 🚀 使用方法

### **基本的な特徴量生成**
```python
from src.features.feature_generator import FeatureGenerator
import pandas as pd

# データ準備（OHLCV必須）
market_data = pd.DataFrame({
    'open': [...],
    'high': [...],
    'low': [...],
    'close': [...],
    'volume': [...]
})

# 特徴量生成
feature_generator = FeatureGenerator()
features_df = await feature_generator.generate_features(market_data)

# 結果確認（15特徴量生成）
print(f"生成特徴量数: {len(features_df.columns) - 5}")  # OHLCVを除く
print("特徴量リスト:", list(features_df.columns))
```


### **特徴量情報の取得**
```python
# 特徴量詳細情報
feature_info = feature_generator.get_feature_info()
print("カテゴリ別特徴量:", feature_info['feature_categories'])
print("特徴量説明:", feature_info['feature_descriptions'])
print("合計特徴量数:", feature_info['total_features'])
```

### **feature_order.json連携確認**
```python
# feature_order.json整合性確認
from src.core.config.feature_manager import FeatureManager

fm = FeatureManager()
generated_features = await feature_generator.generate_features(market_data)

# 順序・整合性確認
expected_features = fm.get_feature_names()
actual_features = [col for col in generated_features.columns if col not in ['open', 'high', 'low', 'close', 'volume']]

assert actual_features == expected_features, "特徴量順序が不一致"
print("✅ feature_order.json整合性確認完了")
```

### **設定カスタマイズ**
```python
# 異常検知パラメータ調整
feature_generator = FeatureGenerator(
    lookback_period=30  # 異常検知参照期間を30に変更
)

features_df = await feature_generator.generate_features(market_data)
```

## 📊 15特徴量詳細

### **基本データ（2個）**
- `close`: 終値（基準価格）
- `volume`: 出来高（市場活動度）

### **モメンタム指標（2個）**
- `rsi_14`: RSI 14期間（オーバーボート・オーバーソールド判定）
- `macd`: MACD（トレンド転換シグナル）

### **ボラティリティ指標（2個）**
- `atr_14`: ATR 14期間（ボラティリティ測定）
- `bb_position`: ボリンジャーバンド位置（価格位置判定）

### **トレンド指標（2個）**
- `ema_20`: EMA 20期間（短期トレンド）
- `ema_50`: EMA 50期間（中期トレンド）

### **出来高指標（1個）**
- `volume_ratio`: 出来高比率（出来高異常検知）

### **ブレイクアウト指標（3個）**
- `donchian_high_20`: 20期間最高値（上限ブレイクアウト判定）
- `donchian_low_20`: 20期間最安値（下限ブレイクアウト判定）
- `channel_position`: Donchianチャネル内位置（相対位置判定）

### **市場レジーム指標（3個）**
- `adx_14`: ADX 14期間（トレンド強度測定）
- `plus_di_14`: +DI 14期間（上昇方向性指標）
- `minus_di_14`: -DI 14期間（下降方向性指標）

## 🔧 統合システム特徴

### **feature_order.json統合**
- **単一真実源**: config/core/feature_order.json が全システムの特徴量定義基準
- **統一管理**: 特徴量名・順序・カテゴリの完全一致保証
- **システム連携**: 特徴量生成・戦略・ML・バックテストの統合整合性

### **7カテゴリ分類システム**
- **basic**: 基本価格・出来高データ
- **momentum**: モメンタム系指標（RSI・MACD）
- **volatility**: ボラティリティ系指標（ATR・ボリンジャーバンド）
- **trend**: トレンド系指標（EMA）
- **volume**: 出来高系指標
- **breakout**: ブレイクアウト系指標（Donchianチャネル）
- **regime**: 市場レジーム系指標（ADX・DI）

### **品質保証システム**
- **統一インターフェース**: 全特徴量生成の一元化
- **エラーハンドリング**: 統一されたNaN値処理・例外処理
- **検証機能**: 15特徴量完全確認システム
- **後方互換性**: 既存コードとの完全互換性維持

## ⚠️ 重要事項

### **データ要件**
- **必須列**: `open`, `high`, `low`, `close`, `volume`
- **最小行数**: 50行以上推奨（移動平均計算のため）
- **データ品質**: 欠損値・異常値の事前確認推奨

### **パフォーマンス考慮**
- **大量データ**: 10万行超の場合は分割処理推奨
- **メモリ効率**: pandasネイティブ最適化済み
- **リアルタイム**: 増分計算による高速処理

### **エラーハンドリング**
- **データ不足**: 警告ログ出力後、利用可能データで計算継続
- **計算エラー**: 個別特徴量失敗時は該当特徴量のみスキップ
- **NaN値処理**: 前方補間・後方補間・ゼロ補間の段階的処理

### **設計原則**
- **統一システム**: feature_order.json単一真実源との完全整合性
- **統合効率**: 重複排除による高速計算
- **品質保証**: 15特徴量完全生成の確認機能
- **後方互換性**: 既存コードとの完全互換性維持

### **依存関係**
- **内部依存**: src.core.config.feature_manager（特徴量定義）、src.core.logger、src.core.exceptions
- **外部設定**: config/core/feature_order.json（15特徴量統一定義）
- **外部ライブラリ**: pandas（データ処理）、numpy（数値計算）

---

**特徴量生成システム**: feature_order.json単一真実源と連携した15特徴量統一システム。7カテゴリ分類による体系的特徴量管理により、高品質で効率的な機械学習入力データを提供する統合特徴量エンジニアリングシステム。