# src/ml/ - 機械学習システム

**Phase 64.6更新**: 55特徴量を入力とした3モデルアンサンブル（LightGBM・XGBoost・RandomForest）による高精度取引シグナル予測システム。

## ファイル構成

```
src/ml/
├── __init__.py          # ML層エクスポート
├── models.py            # 個別モデル実装（586行）
└── ensemble.py          # ProductionEnsemble（~200行）
```

## 主要コンポーネント

### **models.py（586行）**

個別機械学習モデル（LightGBM・XGBoost・RandomForest）実装。

```python
class BaseMLModel(ABC):                               # 基底クラス
    def fit(self, X, y) -> 'BaseMLModel'              # 学習実行
    def predict(self, X) -> np.ndarray                # 予測実行
    def predict_proba(self, X) -> np.ndarray          # 確率予測
    def get_feature_importance(self) -> Dict          # 特徴量重要度

class LGBMModel(BaseMLModel):                         # LightGBM実装
class XGBModel(BaseMLModel):                          # XGBoost実装
class RFModel(BaseMLModel):                           # RandomForest実装
```

### **ensemble.py（~200行）**

本番用3モデルアンサンブル予測（重み付け投票）。

```python
class ProductionEnsemble:                             # 本番用アンサンブル
    def predict(self, features) -> np.ndarray         # 重み付け投票
    def predict_proba(self, features) -> np.ndarray   # 重み付け確率
    def update_weights(self, new_weights)             # 重み更新
    def validate_predictions(self, X, y_true=None)    # 予測精度検証
```

## 使用例

```python
# 本番用ProductionEnsemble使用
import pickle
with open('models/production/ensemble_full.pkl', 'rb') as f:
    production_model = pickle.load(f)

predictions = production_model.predict(sample_features)  # 55特徴量必須
```

## アンサンブル構成

**重み付け設定**（ProductionEnsemble）:
```python
weights = {
    'lightgbm': 0.4,        # 40% - 高いCV F1スコア
    'xgboost': 0.4,         # 40% - 高い精度・補完性能
    'random_forest': 0.2    # 20% - 安定性重視・過学習抑制
}
```

## 設定

- **環境変数**: 不要（設定ファイルから自動取得）
- **データ要件**: 55特徴量固定・順序厳守
- **本番モデル**: models/production/ensemble_full.pkl
