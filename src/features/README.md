# src/features/ - 特徴量生成システム

55 特徴量（Phase 89-β/γ/δ で 37→55 拡張）。`config/core/feature_order.json` 単一真実源連携。

## ファイル構成（Phase 90α・2026-05-19 時点）

```
src/features/
├── __init__.py             # 遅延インポート（循環インポート回避）（41 行）
├── constants.py            # 共通定数（13 行）
├── feature_cache.py        # 特徴量生成キャッシュ（190 行・Phase 89-α Stage 2）
└── feature_generator.py    # 統合特徴量生成（1,345 行・FeatureGenerator クラス）
```

## FeatureGenerator

```python
class FeatureGenerator:
    async def generate_features(self, market_data, strategy_signals=None) -> pd.DataFrame
    def generate_features_sync(self, df, strategy_signals=None) -> pd.DataFrame
    def get_feature_info(self) -> Dict
```

async 版・sync 版は共通パイプライン `_run_feature_pipeline()` を使用。

## feature_cache.py（Phase 89-α Stage 2）

同一 OHLCV に対する 55 特徴量計算を 1 回のみに抑える LRU キャッシュ。DataFrame のハッシュ（最終 timestamp + close 値）をキーに `@lru_cache(maxsize=4)` で再計算回避。20-60ms / cycle 削減見込み。

## constants.py

特徴量モジュール全体で共有する定数定義（`EXPECTED_FEATURE_COUNT` 等）。Phase 87 H7 で共有定数化。

## 55 特徴量構成（Phase 89-β/γ/δ）

| Phase | 追加カテゴリ | 件数 | 累計 |
|---|---|---|---|
| Phase 77 | SHAP + Forward Selection で 55→37 | -18 | 37 |
| Phase 89-β | funding rate / sentiment (Fear & Greed) / microstructure / macro_lite | +10 | 47 |
| Phase 89-γ | microstructure_advanced (VPIN +3) | +5 | 52 |
| Phase 89-δ | cross_asset (BTC-ETH 相関 +3) | +3 | **55** |

詳細は `config/core/feature_order.json` を参照。

## 使用例

```python
from src.features import FeatureGenerator

generator = FeatureGenerator()

# async 版（ライブトレード）
features_df = await generator.generate_features(market_data, strategy_signals)

# sync 版（バックテスト）
features_df = generator.generate_features_sync(df, strategy_signals)
```

## 設定

- **データ要件**: OHLCV 必須（open, high, low, close, volume）
- **依存**: `config/core/feature_order.json`（55 特徴量定義）
- **環境変数**: 不要（設定ファイルから自動取得）
- **キャッシュ**: `data/runtime_state/cross_asset_history.pkl`（Phase 89-δ）

## 関連リンク

- 親 README: [../README.md](../README.md)
- 特徴量順序定義: `../../config/core/feature_order.json`
- データ層: [../data/README.md](../data/README.md)
- ML 統合: [../ml/README.md](../ml/README.md)

---

**最終更新**: 2026年5月19日（Phase 90α: 4 ファイル構成・55 特徴量反映）
