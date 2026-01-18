# models/ - 機械学習モデル管理（Phase 59完了）

## 役割・責任

機械学習モデルの学習・管理・本番運用を統合管理します。**Phase 59: ProductionEnsemble採用**により、Stacking無効化・重み付き平均方式で安定した高収益を実現。

## ディレクトリ構成

```
models/
├── README.md                              # このファイル
├── production/                            # 本番環境用モデル（100MB）
│   ├── ensemble_full.pkl                  # メイン: 55特徴量（32MB）
│   ├── ensemble_basic.pkl                 # フォールバック: 49特徴量（33MB）
│   ├── stacking_ensemble.pkl              # Stacking（無効・参照用）
│   ├── meta_learner.pkl                   # メタ学習器（無効・参照用）
│   ├── production_model_metadata.json     # メインモデルメタデータ
│   └── production_model_metadata_basic.json
├── training/                              # 個別モデル（33MB）
│   ├── lightgbm_model.pkl                 # LightGBM（245KB）
│   ├── xgboost_model.pkl                  # XGBoost（4.8MB）
│   ├── random_forest_model.pkl            # RandomForest（28MB）
│   └── training_metadata.json
└── archive/                               # バックアップ（空）
```

## モデル仕様（Phase 59）

| 項目 | 値 |
|------|-----|
| **特徴量数** | 55（49基本 + 6戦略信号） |
| **アンサンブル方式** | 重み付き平均（Stacking無効） |
| **モデル重み** | LightGBM 40% / XGBoost 40% / RF 20% |
| **分類** | 3クラス（BUY / HOLD / SELL） |

## 4段階Graceful Degradation

```
Level 0: Stacking無効（現在の設定）
    ↓ Full特徴量生成失敗
Level 1: ensemble_full.pkl（55特徴量）
    ↓ モデル読み込み失敗
Level 2: ensemble_basic.pkl（49特徴量）
    ↓ モデル読み込み失敗
Level 3: DummyModel（常にHOLD）
```

## 使用方法

### モデル学習
```bash
# 週次自動学習（GitHub Actions: 毎週日曜18:00 JST）
# または手動実行:
python3 scripts/ml/create_ml_models.py
```

### 本番モデル使用
```python
from src.ml.ensemble import ProductionEnsemble

model = ProductionEnsemble()
prediction = model.predict(features)
probabilities = model.predict_proba(features)
```

### メタデータ確認
```bash
cat models/production/production_model_metadata.json | jq '.model_weights'
```

## Git管理

| ディレクトリ | Git追跡 | 復元方法 |
|-------------|---------|----------|
| production/*.pkl | ✅ Yes | `git checkout` |
| training/*.pkl | ❌ No | `create_ml_models.py` |
| archive/ | ❌ No | 週次学習で自動生成 |

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `src/ml/ensemble.py` | ProductionEnsemble実装 |
| `src/features/feature_manager.py` | 特徴量生成 |
| `scripts/ml/create_ml_models.py` | モデル学習スクリプト |
| `config/core/thresholds.yaml` | stacking_enabled設定 |
| `.github/workflows/train_model.yml` | 週次自動学習 |

---

**最終更新**: 2026年1月18日（Phase 59完了）
