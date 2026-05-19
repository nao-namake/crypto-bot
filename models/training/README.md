# models/training/ - 個別モデル学習・管理

ProductionEnsemble を構成する個別モデル（LightGBM / XGBoost / RandomForest / N-BEATS）と学習メタデータ。

## ファイル構成（Phase 90α・2026-05-17 時点）

```
models/training/
├── README.md                    # このファイル
├── training_metadata.json       # 学習結果メタデータ（最新の v8e 学習）
├── lightgbm_model.pkl           # LightGBM 個別モデル（26K）
├── xgboost_model.pkl            # XGBoost 個別モデル（2.5M）
├── random_forest_model.pkl      # RandomForest 個別モデル（11M）
└── nbeats_model.pkl             # N-BEATS 個別モデル（412K・Phase 89-γ 追加）
```

## 個別モデル仕様（Phase 90α）

| モデル | 重み | 特徴 |
|--------|------|------|
| **LightGBM** | 34% | 高速・軽量・SMOTE 適応 |
| **XGBoost** | 34% | 高精度（過学習傾向あり・Phase 90β 対策候補） |
| **RandomForest** | 17% | 安定性・GCP gVisor 制約で `n_jobs` 環境変数化 |
| **N-BEATS** | 15% | Phase 89-γ 追加・PyTorch・macOS では `torch.set_num_threads(1)` 必須 |

## 学習仕様

| 項目 | 値 |
|------|-----|
| **特徴量数** | **55**（Phase 89-β/γ/δ で拡張）|
| **分類** | **2 クラス（success / failure）**・Triple Barrier Method（Phase 90α メタラベリング有効化） |
| **TP/SL 閾値** | `--meta-tp-ratio 0.007` / `--meta-sl-ratio 0.0086`（tight_range 運用に合わせる）|
| **交差検証** | TimeSeriesSplit n_splits=5 + Purged K-Fold（embargo_pct=0.01・Phase 89-β）|
| **過学習防止** | Early Stopping + Optuna 50 trials |
| **クラス不均衡** | SMOTE オーバーサンプリング（success 30.8% / failure 69.2%）|

## 使用方法

### モデル学習

```bash
# CI: GitHub Actions（週次 + Drift 検知時 Auto Retraining）
gh workflow run model-training.yml --ref main -f n_trials=50

# ローカル: wrapper（caffeinate + n_jobs=-1 + 自動 backup）
bash scripts/ml/run_local_training.sh 50

# 直接実行（n_jobs=-1 で並列化・ローカル開発用）
ML_TRAINING_N_JOBS=-1 python3 scripts/ml/create_ml_models.py \
  --model full --n-classes 3 --threshold 0.005 \
  --use-smote --optimize --n-trials 50 \
  --meta-label --meta-tp-ratio 0.007 --meta-sl-ratio 0.0086 \
  --verbose
```

### メタデータ確認

```bash
# 各モデルの CV F1
cat models/training/training_metadata.json | jq '.model_metrics'

# Optuna best params
cat models/training/training_metadata.json | jq '.optuna_best_params'

# 学習所要時間
cat models/training/training_metadata.json | jq '.elapsed_seconds'
```

## 本番モデルとの関係

```
models/training/              models/production/
├── lightgbm_model.pkl       ┐
├── xgboost_model.pkl        ├─→ ensemble_full.pkl (4 モデル加重平均)
├── random_forest_model.pkl  │   ensemble_basic.pkl (3 モデル fallback)
└── nbeats_model.pkl         ┘
```

- `training/` の個別モデルは学習時の中間成果物
- `production/ensemble_*.pkl` が本番運用に使用される
- 個別モデルがなくても `production/` があれば運用可能

## 整理方針

| ファイル | 整理ルール |
|---|---|
| `*.pkl` | 学習毎に上書き・最新セットのみ保持 |
| `training_metadata.json` | 最新の学習結果（前回分は production/_metadata.bak で保全）|
| `*.json.bak` | 連続学習時の残骸 → `/organize-folder models/training` で承認制削除 |

## 関連リンク

- 親 README: [../README.md](../README.md)
- 学習スクリプト: [../../scripts/ml/create_ml_models.py](../../scripts/ml/create_ml_models.py)
- 学習 wrapper: [../../scripts/ml/run_local_training.sh](../../scripts/ml/run_local_training.sh)
- 本番モデル: [../production/README.md](../production/README.md)

---

**最終更新**: 2026年5月18日（Phase 90α: 4 モデル化・メタラベリング対応）
