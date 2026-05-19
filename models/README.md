# models/ - 機械学習モデル管理

機械学習モデルの学習・本番運用・履歴管理。**ProductionEnsemble**（55 特徴量・4 モデル加重平均・メタラベリング方式）。

## ディレクトリ構成

| サブフォルダ | サイズ | 役割 |
|---|---|---|
| `production/` | ~193MB | 本番モデル本体 + ロールバック用 `.bak` バックアップ |
| `training/` | ~14MB | 個別モデル中間生成物 + 学習メタデータ |
| `archive/` | ~311MB（直近 1 ヶ月） | 過去の自動アーカイブ（タイムスタンプ命名）|
| `optuna/` | 12KB | Optuna ハイパラ最適化結果（Phase 39.5）|
| `regime/` | 4KB | HMM レジーム検出モデル（Phase 89-γ）|

## モデル仕様（Phase 90α・2026-05-17 時点）

| 項目 | 値 |
|------|-----|
| **特徴量数** | **55**（Phase 89-β/γ/δ で 37→55 拡張） |
| **アンサンブル** | 4 モデル加重平均 |
| **モデル重み** | LightGBM 34% / XGBoost 34% / RandomForest 17% / N-BEATS 15% |
| **分類** | **2 クラス（success / failure）メタラベリング**（Phase 90α・Triple Barrier Method）|
| **macro F1** | LGB CV 0.546 / Test 0.486・naive 0.41 比 **+0.14** |

## 3 段階 Graceful Degradation

```
Level 1: production/ensemble_full.pkl（55 特徴量・4 モデル）
    ↓ 読み込み失敗
Level 2: production/ensemble_basic.pkl（55 特徴量・3 モデル fallback）
    ↓ 読み込み失敗
Level 3: DummyModel（常に HOLD）
```

## production/ バックアップ階層

| バックアップ | 用途 | 参照元 |
|---|---|---|
| `ensemble_full.pre_v8_20260517_101041.pkl.bak` | **v8e 直前**（Phase 90α 最新ロールバック先）| CLAUDE.md「異常時のロールバック」 |
| `ensemble_full.pre_v8_20260517_062507.pkl.bak` | v7/v8a 直前 | Phase_90.md |
| `ensemble_full.phase84.pkl.bak` + `_basic` + metadata | Phase 84 安定版（深いロールバック）| CLAUDE.md / 統合運用ガイド |
| `ensemble_full.phase89_buggy_nbeats.pkl.bak` + metadata | N-BEATS 故障版（Phase 90β 比較用）| 統合運用ガイド第7部 |

**注意**: `phase84.pkl.bak` は 37 特徴量パイプライン用。現行 55 特徴量と整合しないため `n_features_in_ mismatch` でクラッシュする可能性あり。深いロールバックは git tag `phase-89-stable` も検討。

## 使用方法

### モデル学習

```bash
# CI: GitHub Actions model-training.yml（週次自動 + Drift 検知時 Auto Retraining）
gh workflow run model-training.yml --ref main -f n_trials=50

# ローカル: caffeinate ラップ付き wrapper
bash scripts/ml/run_local_training.sh 50
```

### 本番モデル使用

```python
from src.ml.ensemble import ProductionEnsemble
import joblib

model = joblib.load("models/production/ensemble_full.pkl")
prediction = model.predict(features)        # (N,) 0=failure / 1=success
probabilities = model.predict_proba(features)  # (N, 2)
```

### メタデータ確認

```bash
cat models/production/production_model_metadata.json | jq '.model_weights'
cat models/production/production_model_metadata.json | jq '.performance_metrics'
```

## 整理方針（gitignore とは別の運用ルール）

| 対象 | 保持期間 | 整理ツール |
|---|---|---|
| `production/*.pkl` `_metadata.json` | 現用・**絶対不可侵** | - |
| `production/*.bak`（直近 Phase ロールバック）| **保全**（CLAUDE.md 参照）| - |
| `production/*.bak`（連続学習中間スナップショット）| 不要 | `/organize-folder models/production` |
| `archive/` | **直近 1 ヶ月**（過去は削除）| `/organize-folder models/archive` |
| `training/*.pkl` `.json` | 直近の learning セット | 自動上書き |

## 関連ファイル

| ファイル | 役割 |
|---|---|
| `src/ml/ensemble.py` | ProductionEnsemble 実装（加重平均・predict / predict_proba）|
| `src/ml/nbeats_predictor.py` | N-BEATS 個別モデル（Phase 89-γ）|
| `src/core/orchestration/ml_loader.py` | 3 段階 Graceful Degradation ローダー |
| `scripts/ml/create_ml_models.py` | モデル学習スクリプト（CLI: `--meta-label --n-trials N`）|
| `scripts/ml/run_local_training.sh` | ローカル学習 wrapper（caffeinate + n_jobs=-1）|
| `.github/workflows/model-training.yml` | CI 週次自動学習（repository_dispatch も対応）|

## 関連リンク

- 親 README: [../README.md](../README.md)
- 学習スクリプト: [../scripts/ml/README.md](../scripts/ml/README.md)
- Phase 90α 詳細: [../docs/開発履歴/Phase_90.md](../docs/開発履歴/Phase_90.md)
- 統合運用ガイド第7部「N-BEATS rollback 手順」: [../docs/運用ガイド/統合運用ガイド.md](../docs/運用ガイド/統合運用ガイド.md)

---

**最終更新**: 2026年5月18日（Phase 90α: 55 特徴量・4 モデル・メタラベリング対応 + 整理方針追記）
