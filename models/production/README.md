# models/production/ - 本番環境モデル管理

実取引で使用される本番モデル + ロールバック用バックアップ。**ProductionEnsemble**（55 特徴量・4 モデル加重平均・メタラベリング方式）。

## ファイル構成（Phase 90α・2026-05-17 時点）

```
models/production/
├── README.md                              # このファイル
├── ensemble_full.pkl                      # ★ メイン: 55 特徴量・4 モデル（13MB）
├── ensemble_basic.pkl                     # フォールバック: 55 特徴量・3 モデル（32MB）
├── production_model_metadata.json         # 現用メタデータ
├── production_model_metadata_basic.json   # Basic メタデータ
│
├── ensemble_full.pre_v8_20260517_101041.pkl.bak    # ★ v8e 直前（Phase 90α 最新ロールバック）
├── production_model_metadata.pre_v8_20260517_101041.json.bak
├── ensemble_full.pre_v8_20260517_062507.pkl.bak    # v7/v8a 直前
├── production_model_metadata.pre_v8_20260517_062507.json.bak
│
├── ensemble_full.phase84.pkl.bak                   # Phase 84 安定版（深いロールバック）
├── ensemble_basic.phase84.pkl.bak                  # Phase 84 basic
├── production_model_metadata.phase84.json.bak
│
├── ensemble_full.phase89_buggy_nbeats.pkl.bak      # N-BEATS 故障版（Phase 90β 比較用）
└── phase89_buggy_nbeats_metadata.json.bak
```

## メインモデル仕様（Phase 90α）

| 項目 | 値 |
|------|-----|
| **特徴量数** | **55**（Phase 89-β/γ/δ で 37→55 拡張） |
| **アンサンブル** | 4 モデル加重平均 |
| **モデル重み** | LightGBM 34% / XGBoost 34% / RandomForest 17% / N-BEATS 15% |
| **分類** | **2 クラス（success / failure）メタラベリング**（Triple Barrier Method）|
| **学習データ** | 365 日分（35,036 サンプル・SMOTE 後 41,312） |
| **macro F1** | LGB CV 0.546 / Test 0.486・naive 0.41 比 **+0.14** |
| **ファイルサイズ** | 13MB |

## 3 段階 Graceful Degradation

```
Level 1: ensemble_full.pkl（55 特徴量・4 モデル）
    ↓ 読み込み失敗
Level 2: ensemble_basic.pkl（55 特徴量・3 モデル fallback）
    ↓ 読み込み失敗
Level 3: DummyModel（常に HOLD）
```

## バックアップの選び方（ロールバック判断）

| ロールバック理由 | 使うバックアップ | 戻る Phase |
|---|---|---|
| Phase 90α 不調・直前に戻す | `pre_v8_20260517_101041.pkl.bak` | v8c（Phase 89-buggy・直前）|
| v7/v8 系全部失敗 | `pre_v8_20260517_062507.pkl.bak` | v7 試行直前 |
| 4 モデル全部不調・3 モデルに戻す | `phase89_buggy_nbeats.pkl.bak` | Phase 89 N-BEATS 失敗版 |
| 深刻な問題・Phase 84 に戻す | `phase84.pkl.bak`（37 特徴量）| Phase 84 |

**注意**: `phase84.pkl.bak` は **37 特徴量**で現行 55 特徴量パイプラインと非互換。起動時 `n_features_in_ mismatch` でクラッシュする可能性 → git tag `phase-89-stable` checkout も検討。詳細は `../../docs/運用ガイド/統合運用ガイド.md` 第7部「N-BEATS rollback 手順」参照。

## 使用方法

### モデル読み込み

```python
import joblib

model = joblib.load("models/production/ensemble_full.pkl")
prediction = model.predict(features)        # (N,) 0=failure / 1=success
probabilities = model.predict_proba(features)  # (N, 2)
```

### メタデータ確認

```bash
# モデル重み
cat models/production/production_model_metadata.json | jq '.model_weights'

# CV F1 / Test F1
cat models/production/production_model_metadata.json | jq '.performance_metrics'

# 特徴量一覧
cat models/production/production_model_metadata.json | jq '.feature_names'
```

### モデル再学習

```bash
# CI: GitHub Actions（週次 + Drift 検知時 Auto Retraining）
gh workflow run model-training.yml --ref main -f n_trials=50

# ローカル: wrapper（caffeinate + n_jobs=-1 + 自動 backup）
bash scripts/ml/run_local_training.sh 50
```

## 整理方針

| 対象 | 整理ルール |
|---|---|
| `*.pkl` `_metadata.json` | **絶対に削除・改変しない**（現用本番） |
| `*.pkl.bak`（直近 Phase ロールバック）| **保全**（CLAUDE.md「異常時のロールバック」参照） |
| `*.pkl.bak`（連続学習中間スナップショット）| `/organize-folder models/production` で承認制クリーンアップ |

## 関連リンク

- 親 README: [../README.md](../README.md)
- 実装: `../../src/ml/ensemble.py`
- 学習: `../../scripts/ml/create_ml_models.py`
- ロールバック手順: [../../docs/運用ガイド/統合運用ガイド.md](../../docs/運用ガイド/統合運用ガイド.md) 第7部

---

**最終更新**: 2026年5月18日（Phase 90α: 55 特徴量・4 モデル・メタラベリング対応）
