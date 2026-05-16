# Phase 89-γ N-BEATS ロールバック手順

## 用途

N-BEATS が修復後も性能を出さない場合、または ensemble に悪影響を与える場合に **A: weights nbeats=0.0 で実質無効化** して 3 モデル ensemble (LGB/XGB/RF) で運用する手順。

## 判定基準（A 移行を決断する閾値）

ML 再学習後の `models/training/training_metadata.json` で以下のいずれかに該当する場合 A 移行推奨:

| metric | 閾値 | 意味 |
|--------|------|------|
| `nbeats.confidence_std` | < 0.05 | 全予測がほぼ同一値（定数化 / uniform 出力）|
| `nbeats.accuracy` | < 0.4 | クラス予測精度がランダム水準に近い |
| `nbeats.cv_f1_mean` | < 0.5 | CV 性能が低すぎて ensemble に貢献しない |
| `nbeats.f1_score` | < 0.4 | テスト F1 が壊滅的 |

## A 移行手順（weights を 0 に固定）

### 手順 1: thresholds.yaml の weights 更新

```bash
# nbeats の重みを 0 に
yq -i '.ml.ensemble.weights.nbeats = 0.0' config/core/thresholds.yaml

# 他モデルの重みを 3 モデル時代に戻す
yq -i '.ml.ensemble.weights.lightgbm = 0.4' config/core/thresholds.yaml
yq -i '.ml.ensemble.weights.xgboost = 0.4' config/core/thresholds.yaml
yq -i '.ml.ensemble.weights.random_forest = 0.2' config/core/thresholds.yaml
```

または手動で `config/core/thresholds.yaml` を編集:

```yaml
ml:
  ensemble:
    weights:
      lightgbm: 0.40
      xgboost: 0.40
      random_forest: 0.20
      nbeats: 0.0   # ← B 失敗時はこれで N-BEATS 実質無効化（4 モデル中 3 モデルで運用）
```

### 手順 2: commit + push（自動デプロイ）

```bash
git add config/core/thresholds.yaml
git commit -m "rollback: N-BEATS weights to 0.0 (Phase 89-γ A fallback)"
git push origin main
```

CI 経由で Cloud Run 自動デプロイ。約 10 分でリビジョン切替完了。

### 手順 3: 実機検証

```bash
# Cloud Run 新リビジョン確認
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=2

# 5 分後の trigger ログで ensemble が 3 モデル合計重み 1.0 で正規化されていることを確認
gcloud logging read 'textPayload=~"ensemble.*predict|nbeats"' --freshness=10m --limit=20
```

## ensemble.py の正規化挙動

`src/ml/ensemble.py:139-144` のロジック上、`weights.nbeats=0.0` でも N-BEATS の `predict_proba` 自体は呼ばれます（duck typing でループ）。ただし加重平均で 0 倍されるため**最終予測には反映されません**。

```python
for name, proba in probabilities.items():
    weight = self.weights.get(name, 1.0)
    ensemble_proba += proba * weight   # nbeats: 0.0 * proba = 0
    total_weight += weight             # nbeats: total_weight += 0
final_proba = ensemble_proba / total_weight  # 3 モデルの加重平均と等価
```

つまり `weights.nbeats=0.0` は「実質 3 モデル ensemble」と同義。

## 完全な旧モデル復旧（必要な場合のみ）

N-BEATS だけでなく Phase 89 全機能を巻き戻したい場合（年利向上の試みを完全撤回）:

```bash
# Phase 89 buggy backup から復元（55 特徴量・4 モデル・N-BEATS 学習失敗版に戻る）
cp models/production/ensemble_full.phase89_buggy_nbeats.pkl.bak \
   models/production/ensemble_full.pkl

git add models/production/ensemble_full.pkl
git commit -m "rollback: restore phase89 buggy snapshot"
git push origin main
```

**注意**: Phase 84 backup (`ensemble_full.phase84.pkl.bak`・37 特徴量) は現行の 55 特徴量パイプラインと整合せず、起動時 `n_features_in_ mismatch` でクラッシュします。Phase 84 への完全復旧は git tag `phase-89-stable` 等への checkout が必要。

## 関連ファイル

- `models/production/ensemble_full.phase89_buggy_nbeats.pkl.bak` （N-BEATS 故障版 backup）
- `models/production/phase89_buggy_nbeats_metadata.json.bak`
- `models/training/phase89_buggy_nbeats_training_metadata.json.bak`
- `config/core/thresholds.yaml`（`ml.ensemble.weights` セクション）
- `src/ml/ensemble.py:92-146`（predict_proba の重み付け平均ロジック）
