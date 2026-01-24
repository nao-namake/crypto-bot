# models/training/ - 個別モデル学習・管理（Phase 61更新）

## 役割・責任

ProductionEnsembleを構成する個別モデル（LightGBM・XGBoost・RandomForest）の学習・管理を担当します。

## ファイル構成

```
models/training/
├── README.md                    # このファイル
└── training_metadata.json       # 学習結果メタデータ（Git管理）

# 以下は学習時に生成（Git管理外・再生成可能）
# ├── lightgbm_model.pkl         # LightGBM個別モデル
# ├── xgboost_model.pkl          # XGBoost個別モデル
# └── random_forest_model.pkl    # RandomForest個別モデル
```

**注意**: 個別モデル（*.pkl）はGit管理外です。`create_ml_models.py`で再生成できます。本番運用には`production/ensemble_*.pkl`のみ必要です。

## 個別モデル仕様

| モデル | 重み | 特徴 |
|--------|------|------|
| **LightGBM** | 40% | 高速・軽量 |
| **XGBoost** | 40% | 高精度 |
| **RandomForest** | 20% | 安定性・過学習耐性 |

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

### モデル学習（個別モデル生成）
```bash
# 週次自動学習（GitHub Actions: 毎週日曜18:00 JST）
# または手動実行:
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

## 本番モデルとの関係

```
models/training/           models/production/
├── lightgbm_model.pkl  ─┐
├── xgboost_model.pkl   ─┼→ ensemble_basic.pkl（49特徴量）
├── random_forest_model.pkl ┘
                           └→ ensemble_full.pkl（55特徴量・戦略信号付き）
```

- `training/`の個別モデルは学習時の中間成果物
- `production/ensemble_*.pkl`が本番運用に使用される
- 個別モデルがなくても`production/`があれば運用可能

## Git管理方針

| ファイル | Git追跡 | 理由 |
|---------|---------|------|
| README.md | ✅ Yes | ドキュメント |
| training_metadata.json | ✅ Yes | 学習履歴追跡 |
| *.pkl | ❌ No | 中間成果物（再生成可能） |

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `scripts/ml/create_ml_models.py` | モデル学習スクリプト |
| `src/ml/ensemble.py` | ProductionEnsemble実装 |
| `models/production/` | 本番用アンサンブルモデル |
| `.github/workflows/train_model.yml` | 週次自動学習 |

---

**最終更新**: 2026年1月24日（Phase 61: 実態に合わせて更新）
