# models/production/ - 本番環境モデル管理（Phase 59完了）

## 役割・責任

実際の取引で使用される本番用機械学習モデルを管理します。**Phase 59: ProductionEnsemble採用**により、Stacking無効化・重み付き平均方式で安定した高収益を実現します。

## ファイル構成（Phase 61更新）

```
models/production/
├── README.md                              # このファイル
├── ensemble_full.pkl                      # メイン: 55特徴量モデル（32MB）
├── ensemble_basic.pkl                     # フォールバック: 49特徴量モデル（33MB）
├── production_model_metadata.json         # メインモデルのメタデータ
└── production_model_metadata_basic.json   # Basicモデルのメタデータ
```

※ Stackingモデル（stacking_ensemble.pkl, meta_learner.pkl）はPhase 61で削除済み

## 主要モデル

### ensemble_full.pkl - メインモデル（55特徴量）

本番環境で使用される主力モデルです。

| 項目 | 値 |
|------|-----|
| **特徴量数** | 55（49基本 + 6戦略信号） |
| **アンサンブル方式** | 重み付き平均（Stacking無効） |
| **モデル重み** | LightGBM 40% / XGBoost 40% / RF 20% |
| **分類** | 3クラス（BUY / HOLD / SELL） |
| **ファイルサイズ** | 約32MB |

**特徴量構成:**
- 基本特徴量（49個）: 価格・ボリューム・モメンタム・ボラティリティ・トレンド・時間
- 戦略信号（6個）: ATRBased・DonchianChannel・ADXTrendStrength・BBReversal・StochasticReversal・MACDEMACrossover

### ensemble_basic.pkl - フォールバックモデル（49特徴量）

戦略信号なしで動作する安定モデルです。

| 項目 | 値 |
|------|-----|
| **特徴量数** | 49（基本特徴量のみ） |
| **使用場面** | Full特徴量生成失敗時のフォールバック |
| **ファイルサイズ** | 約33MB |

## 4段階Graceful Degradation（Phase 59）

```
Level 0: Stacking無効（現在の設定）
    ↓ Full特徴量生成失敗
Level 1: ensemble_full.pkl（55特徴量）
    ↓ モデル読み込み失敗
Level 2: ensemble_basic.pkl（49特徴量）
    ↓ モデル読み込み失敗
Level 3: DummyModel（常にHOLD）
```

**設定**: `config/core/thresholds.yaml`
```yaml
ensemble:
  stacking_enabled: false  # Phase 59: Stacking無効化
```

## Phase 59 検証結果

| 項目 | ProductionEnsemble | Stacking |
|------|-------------------|----------|
| **損益** | ¥+54,526（過去最高） | ¥+43,729 |
| **PF** | 1.60 | 1.58 |
| **勝率** | 53.2% | 54.5% |
| **年利換算** | 22.9% | 18.3% |

**結論**: ProductionEnsemble（Stacking無効）が12-25%高収益

## 使用方法

### モデル読み込み
```python
from src.ml.ensemble import ProductionEnsemble

# 自動的にStacking設定を参照し、適切なモデルを使用
model = ProductionEnsemble()
prediction = model.predict(features)
probabilities = model.predict_proba(features)
```

### メタデータ確認
```bash
# モデル情報
cat models/production/production_model_metadata.json | jq '.model_weights'

# 特徴量一覧
cat models/production/production_model_metadata.json | jq '.feature_names'
```

### モデル再学習
```bash
# 週次自動学習（GitHub Actions: 毎週日曜18:00 JST）
# または手動実行:
python3 scripts/ml/create_ml_models.py
```

## 注意事項

### ファイル管理
- 本番環境では読み取り専用
- モデル更新時はメタデータも同時更新必須
- 週次自動学習でGitHub Actionsが更新

### リソース
- メモリ使用量: モデル読み込み時約100-150MB
- 読み込み時間: 初回数秒

### Stackingについて
Stackingモデルは**Phase 61で完全削除**されました。ProductionEnsemble（重み付き平均）がStackingより高収益であることがPhase 59で確認されたため、Stacking機能は使用しません。

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `src/ml/ensemble.py` | ProductionEnsemble実装 |
| `src/features/feature_manager.py` | 特徴量生成 |
| `scripts/ml/create_ml_models.py` | モデル学習スクリプト |
| `config/core/thresholds.yaml` | stacking_enabled設定 |
| `.github/workflows/train_model.yml` | 週次自動学習 |

---

**最終更新**: 2026年1月24日（Phase 61: Stackingモデル削除）
