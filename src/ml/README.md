# src/ml/ - 機械学習システム

**Phase 90α**: 55 特徴量を入力とした **4 モデルアンサンブル**（LightGBM・XGBoost・RandomForest・N-BEATS）による **2 クラスメタラベリング**（success/failure・Triple Barrier Method）品質判定システム。

## ファイル構成

```
src/ml/
├── __init__.py            # ML 層エクスポート（26 行）
├── models.py              # 個別モデル実装 LGB/XGB/RF（586 行）
├── ensemble.py            # ProductionEnsemble（207 行・4 モデル加重平均）
├── nbeats.py              # N-BEATS 軽量実装（131 行・Pure PyTorch・CPU 推論・Phase 89-γ）
├── nbeats_predictor.py    # NBeatsPredictor sklearn 互換ラッパー（364 行・Phase 89-γ）
└── cv/
    ├── __init__.py        # PurgedKFold エクスポート
    └── purged_kfold.py    # Purged K-Fold CV（78 行・Phase 89-β）
```

## 主要コンポーネント

### models.py（586 行）

個別機械学習モデル（LightGBM / XGBoost / RandomForest）実装。

```python
class BaseMLModel(ABC):                              # 基底クラス
    def fit(self, X, y) -> 'BaseMLModel'             # 学習実行
    def predict(self, X) -> np.ndarray               # 予測実行
    def predict_proba(self, X) -> np.ndarray         # 確率予測
    def get_feature_importance(self) -> pd.DataFrame # 特徴量重要度
    def save(self, filepath) -> None                  # 保存
    def load(cls, filepath) -> 'BaseMLModel'         # 読込

class LGBMModel(BaseMLModel):                        # LightGBM 実装
class XGBModel(BaseMLModel):                         # XGBoost 実装
class RFModel(BaseMLModel):                          # RandomForest 実装
```

### ensemble.py（207 行）

本番用 4 モデルアンサンブル予測（重み付け平均）。

```python
class ProductionEnsemble:                            # 本番用アンサンブル
    def predict(self, features) -> np.ndarray        # 加重平均
    def predict_proba(self, features) -> np.ndarray  # 加重確率
    def get_model_info(self) -> Dict                 # モデル情報
    def update_weights(self, new_weights)            # 重み更新
    def validate_predictions(self, X, y_true=None)   # 予測精度検証
```

### nbeats.py / nbeats_predictor.py（Phase 89-γ）

N-BEATS（Neural Basis Expansion Analysis for Time Series）の Pure PyTorch 実装と sklearn 互換ラッパー。

**ハング対策**: macOS Apple Silicon で PyTorch + sklearn OpenMP 競合 deadlock を回避するため、`fit()` 冒頭で `torch.set_num_threads(1)` + `torch.set_num_interop_threads(1)` を強制実行（Phase 90α・CLAUDE.md 既知問題対応）。

```python
class NBeatsPredictor:                               # sklearn 互換ラッパー
    def fit(self, X, y, ...) -> 'NBeatsPredictor'   # 学習（StandardScaler + Early Stopping）
    def predict(self, X) -> np.ndarray
    def predict_proba(self, X) -> np.ndarray
    def get_params() / set_params()                 # sklearn 互換
```

### cv/purged_kfold.py（Phase 89-β・78 行）

時系列データ用 Purged K-Fold Cross-Validation。各 fold 間に embargo（パージ期間）を挟むことでリーク防止。

```python
class PurgedKFold:
    def __init__(self, n_splits=5, embargo_pct=0.01):
        ...
    def split(self, X) -> Iterator[(train_idx, test_idx)]
```

## アンサンブル構成（Phase 90α）

```python
weights = {
    'lightgbm': 0.34,        # 34% - 高速・SMOTE 適応
    'xgboost': 0.34,         # 34% - 過学習傾向あり（Phase 90β で正則化強化検討）
    'random_forest': 0.17,   # 17% - 安定性・gVisor 制約で n_jobs 環境変数化
    'nbeats': 0.15           # 15% - 時系列パターン捕捉（Phase 89-γ 追加）
}
```

## 分類設計（Phase 90α メタラベリング）

| 項目 | 値 |
|------|-----|
| 分類クラス | **2 クラス**（success / failure）|
| ラベリング手法 | Triple Barrier Method |
| TP/SL 閾値 | `--meta-tp-ratio 0.007` / `--meta-sl-ratio 0.0086`（tight_range 運用と整合）|
| macro F1 | LGB CV 0.546 / Test 0.486（naive 0.41 比 +0.14 で真の予測力獲得）|

## 使用例

```python
# 本番用 ProductionEnsemble の使用
import joblib
production_model = joblib.load('models/production/ensemble_full.pkl')

predictions = production_model.predict(features)        # 55 特徴量必須
probabilities = production_model.predict_proba(features) # (N, 2)
```

## 設定

- **環境変数**: 不要（推論時）/ `ML_TRAINING_N_JOBS` `ML_TRAINING_PER_MODEL_TIMEOUT` `MKL/OMP/OPENBLAS_NUM_THREADS=1`（学習時）
- **データ要件**: 55 特徴量・順序厳守（`config/core/feature_order.json`）
- **本番モデル**: `models/production/ensemble_full.pkl`

## 関連リンク

- 親 README: [../README.md](../README.md)
- 特徴量生成: [../features/README.md](../features/README.md)
- 学習スクリプト: [../../scripts/ml/README.md](../../scripts/ml/README.md)
- 本番モデル: [../../models/production/README.md](../../models/production/README.md)
- Phase 90α 経緯: [../../docs/開発履歴/Phase_90.md](../../docs/開発履歴/Phase_90.md)

---

**最終更新**: 2026年5月19日（Phase 90α: 4 モデル・55 特徴量・メタラベリング・N-BEATS / Purged K-Fold 追記）
