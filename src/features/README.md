# src/features/ - 特徴量生成システム

37特徴量（SHAP最適化）。feature_order.json単一真実源連携。

## ファイル構成

```
src/features/
├── __init__.py            # 遅延インポート（循環インポート回避）
└── feature_generator.py   # 統合特徴量生成（FeatureGeneratorクラス）
```

## FeatureGenerator

```python
class FeatureGenerator:
    async def generate_features(self, market_data, strategy_signals=None) -> pd.DataFrame
    def generate_features_sync(self, df, strategy_signals=None) -> pd.DataFrame
    def get_feature_info(self) -> Dict
```

async版・sync版は共通パイプライン `_run_feature_pipeline()` を使用。

## 37特徴量構成（Phase 77: SHAP最適化）

Phase 77でSHAP+Forward Selectionにより55→37特徴量に最適化。戦略シグナル廃止・単一モデル化。
詳細はconfig/core/feature_order.jsonを参照。

## 使用例

```python
from src.features import FeatureGenerator

generator = FeatureGenerator()

# async版（ライブトレード）
features_df = await generator.generate_features(market_data, strategy_signals)

# sync版（バックテスト）
features_df = generator.generate_features_sync(df, strategy_signals)
```

## 設定

- **データ要件**: OHLCV必須（open, high, low, close, volume）
- **依存**: config/core/feature_order.json（37特徴量定義）
- **環境変数**: 不要（設定ファイルから自動取得）
