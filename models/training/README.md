# models/training/ - 個別モデル学習・管理（Phase 59完了）

## 役割・責任

ProductionEnsembleを構成する個別モデル（LightGBM・XGBoost・RandomForest）の学習・管理を担当します。

## ファイル構成

```
models/training/
├── README.md                    # このファイル
├── lightgbm_model.pkl           # LightGBM個別モデル（245KB）
├── xgboost_model.pkl            # XGBoost個別モデル（4.8MB）
├── random_forest_model.pkl      # RandomForest個別モデル（28MB）
└── training_metadata.json       # 学習結果メタデータ
```

## 個別モデル

| モデル | 重み | ファイルサイズ | 特徴 |
|--------|------|---------------|------|
| **LightGBM** | 40% | 245KB | 高速・軽量 |
| **XGBoost** | 40% | 4.8MB | 高精度 |
| **RandomForest** | 20% | 28MB | 安定性・過学習耐性 |

**特徴量数**: 49（基本特徴量のみ）

## 学習仕様

| 項目 | 値 |
|------|-----|
| **分類** | 3クラス（BUY / HOLD / SELL） |
| **閾値** | 0.5%（ノイズ削減） |
| **交差検証** | TimeSeriesSplit n_splits=5 |
| **過学習防止** | Early Stopping rounds=20 |
| **クラス不均衡** | SMOTE + class_weight='balanced' |
| **最適化** | Optuna TPESampler |

## 使用方法

### モデル学習
```bash
# 個別モデル学習（週次自動実行）
python3 scripts/ml/create_ml_models.py

# 詳細ログ付き
python3 scripts/ml/create_ml_models.py --verbose

# Optuna最適化付き
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50
```

### メタデータ確認
```bash
cat models/training/training_metadata.json | jq '.model_metrics'
```

### 個別モデル読み込み
```python
import pickle

with open('models/training/lightgbm_model.pkl', 'rb') as f:
    lgb_model = pickle.load(f)

prediction = lgb_model.predict(features)
```

## 本番モデルとの関係

```
models/training/           models/production/
├── lightgbm_model.pkl  ─┐
├── xgboost_model.pkl   ─┼→ ensemble_basic.pkl（49特徴量）
├── random_forest_model.pkl ┘
                           └→ ensemble_full.pkl（55特徴量・戦略信号付き）
```

- `training/`の個別モデルは`production/ensemble_basic.pkl`の構成要素
- `production/ensemble_full.pkl`は戦略信号（6個）を追加した55特徴量版

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `scripts/ml/create_ml_models.py` | モデル学習スクリプト |
| `src/ml/ensemble.py` | ProductionEnsemble実装 |
| `models/production/` | 本番用アンサンブルモデル |
| `.github/workflows/train_model.yml` | 週次自動学習 |

---

**最終更新**: 2026年1月18日（Phase 59完了）
