# models/ - 機械学習モデル管理（Phase 61更新）

## 役割・責任

機械学習モデルの学習・管理・本番運用を統合管理します。**ProductionEnsemble**（重み付き平均方式）で安定した高収益を実現。

## ディレクトリ構成

```
models/
├── README.md                              # このファイル
├── production/                            # 本番環境用モデル（65MB）
│   ├── ensemble_full.pkl                  # メイン: 55特徴量（32MB）
│   ├── ensemble_basic.pkl                 # フォールバック: 49特徴量（33MB）
│   ├── production_model_metadata.json     # メインモデルメタデータ
│   └── production_model_metadata_basic.json
├── training/                              # 学習メタデータ
│   └── training_metadata.json             # 学習結果記録（Git管理）
│   # *.pkl は学習時に生成（Git管理外・再生成可能）
└── archive/                               # バックアップ（自動生成）
```

## モデル仕様

| 項目 | 値 |
|------|-----|
| **特徴量数** | 55（49基本 + 6戦略信号） |
| **アンサンブル方式** | 重み付き平均 |
| **モデル重み** | LightGBM 40% / XGBoost 40% / RF 20% |
| **分類** | 3クラス（BUY / HOLD / SELL） |

## 3段階Graceful Degradation

```
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
| production/*.json | ✅ Yes | `git checkout` |
| training/*.json | ✅ Yes | `git checkout` |
| training/*.pkl | ❌ No | `create_ml_models.py`で再生成 |
| archive/ | ❌ No | 週次学習で自動生成 |

**注意**: 本番運用には`production/`のみ必要。`training/*.pkl`がなくても運用可能。

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `src/ml/ensemble.py` | ProductionEnsemble実装 |
| `src/features/feature_manager.py` | 特徴量生成 |
| `scripts/ml/create_ml_models.py` | モデル学習スクリプト |
| `.github/workflows/train_model.yml` | 週次自動学習 |

---

**最終更新**: 2026年1月24日（Phase 61: 実態に合わせて整理）
