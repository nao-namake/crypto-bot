# Auto Retraining セットアップ (Phase 89-γ / H10 / H12)

`MLHealthMonitor.trigger_retraining()` から GitHub Actions の `repository_dispatch` を起動するための運用手順。

## 概要

- Drift 検出が連続 N 回（`ml.drift.consecutive_threshold`、既定 3）に達すると、`MLHealthMonitor.record_feature_distribution` が `trigger_retraining(event_type="ml-drift-detected")` を呼び出す。
- 内部で GitHub REST API `POST /repos/{owner}/{repo}/dispatches` に PAT 認証で送る。
- `.github/workflows/model-training.yml` の `repository_dispatch: types: [ml-drift-detected]` が受け取り、再学習 + デプロイのフルパイプラインを起動。
- 24 時間 cooldown (`ml.drift.retrain_cooldown_hours`) で重複起動を防止。

## 必要な GitHub Secret / 環境変数

| 変数 | 取得元 | 説明 |
|------|--------|------|
| `GITHUB_REPO_OWNER` | リポジトリのオーナー名（例: `nao-namake`） | env で設定 |
| `GITHUB_REPO_NAME` | リポジトリ名（例: `bitbank-btc-bot`） | env で設定 |
| `GITHUB_REPO_DISPATCH_TOKEN` | GitHub Personal Access Token (Fine-grained, スコープ: `Repository permissions > Actions: Read and write`) | Secret Manager 経由 |

## 手順

### 1. GitHub PAT 発行

1. GitHub Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token
2. リポジトリ選択（Only select repositories → bitbank-btc-bot）
3. Repository permissions:
   - **Actions: Read and write**（必須）
   - **Contents: Read**（任意・workflow 内で commit する場合）
4. Generate → 表示されたトークン `ghp_xxxx...` をコピー（再表示不可）

### 2. GCP Secret Manager に登録

```bash
# Secret 作成
echo -n "ghp_xxxx..." | gcloud secrets create github-repo-dispatch-token \
  --replication-policy="automatic" --data-file=-

# 確認
gcloud secrets list | grep github-repo-dispatch-token

# Cloud Run サービスアカウントに read 権限付与
gcloud secrets add-iam-policy-binding github-repo-dispatch-token \
  --member="serviceAccount:bitbank-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 3. Cloud Run env で参照

`.github/workflows/ci.yml` の Cloud Run deploy ステップで以下を追加（既存 `--set-env-vars` / `--set-secrets` の末尾に append）:

```yaml
--set-env-vars="GITHUB_REPO_OWNER=nao-namake,GITHUB_REPO_NAME=bitbank-btc-bot" \
--set-secrets="GITHUB_REPO_DISPATCH_TOKEN=github-repo-dispatch-token:latest"
```

### 4. 動作確認

#### 手動 dispatch でテスト

```bash
# GitHub CLI で repository_dispatch を発火
gh api repos/nao-namake/bitbank-btc-bot/dispatches \
  -X POST \
  -f event_type=ml-drift-detected

# Workflow が enqueue されることを確認
gh run list --workflow=model-training.yml --limit 1
```

#### Cloud Run から実 trigger

```bash
# Drift を意図的に発生させる（テスト用・本番では非推奨）
# → 5 分後に Auto Retraining trigger が起動する
gcloud logging read 'textPayload=~"Auto Retraining triggered"' --freshness=1h
```

### 5. Cooldown 解除（緊急時）

24h cooldown を強制リセットしたい場合:

```bash
# Firestore コンソール or gcloud で
# collection: ml_health_monitor / doc: default の last_retrain_trigger_at を削除
```

## トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `GitHub 設定不足` warning | env / Secret が伝播していない | Cloud Run リビジョン再デプロイ + Secret Manager 紐付け確認 |
| HTTP 401 / 403 | PAT スコープ不足 or 失効 | PAT 再発行 → Secret 更新 |
| HTTP 422 | event_type 不一致 | workflow YAML `types:` と一致確認 |
| `cooldown 中` ログのみで実行されない | 直近 24h 以内に既に trigger 済み | Firestore `last_retrain_trigger_at` 確認・必要なら削除 |
| workflow が起動しない | `if:` 条件で skip | Phase 89 C5 修正済（`repository_dispatch` を許可）。`.github/workflows/model-training.yml:50` を確認 |

## 関連設定

- `config/core/thresholds.yaml` の `ml.drift` セクション（window_size / ks_alpha / consecutive_threshold / retrain_cooldown_hours / significant_feature_min / enable_auto_retraining）
- `.github/workflows/model-training.yml` の `repository_dispatch: types: [ml-drift-detected]`
- `src/core/orchestration/ml_health_monitor.py` の `trigger_retraining()`
