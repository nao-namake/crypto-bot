# CI/CDデプロイメントガイド

**最終更新**: 2025年9月8日  
**対象者**: 開発者・DevOpsエンジニア・システム管理者  
**目的**: GitHub Actions CI/CDパイプラインを使用したGCP Cloud Runへの自動デプロイ環境構築

## 📋 概要

GitHub ActionsとGCP Cloud Runを使用した自動CI/CDパイプラインの構築手順を説明します。統一設定ファイル（`unified.yaml`）とWorkload Identityを活用し、安全で効率的なデプロイを実現します。

## 🚀 クイックスタート

```bash
# 1. 自動環境構築
bash scripts/deployment/setup_ci_prerequisites.sh --interactive

# 2. GitHub Secretsを設定（後述の表参照）

# 3. 初回デプロイ実行
bash scripts/testing/checks.sh  # 品質チェック
git add . && git commit -m "feat: CI/CD環境構築完了" && git push origin main
```

## 🛠️ GCP環境構築

### Step 1: 前提条件確認

```bash
# gcloud CLI認証
gcloud auth login
gcloud config set project my-crypto-bot-project

# 権限確認（Project EditorまたはOwner権限必要）
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
```

### Step 2: 必要なAPI有効化

```bash
# 必要なGCP API有効化
gcloud services enable cloudbuild.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

### Step 3: Artifact Registry設定

```bash
# Dockerリポジトリ作成
gcloud artifacts repositories create crypto-bot-repo \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="crypto-bot Docker images"

# Docker認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

### Step 4: サービスアカウント作成

```bash
# GitHub Actions用サービスアカウント作成
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account" \
  --description="CI/CD automation service account"

# 必要な権限付与
SA_EMAIL="github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com"

for role in \
  "roles/artifactregistry.writer" \
  "roles/run.developer" \
  "roles/secretmanager.secretAccessor" \
  "roles/logging.logWriter" \
  "roles/monitoring.editor"; do
  gcloud projects add-iam-policy-binding my-crypto-bot-project \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$role"
done
```

### Step 5: Workload Identity設定

```bash
# Workload Identity Pool作成
gcloud iam workload-identity-pools create github-pool \
  --location="global" \
  --display-name="GitHub Actions Pool" \
  --description="GitHub Actions用Workload Identity Pool"

# OIDC Provider作成（リポジトリ名を実際の値に変更）
GITHUB_REPO="YOUR_USERNAME/crypto-bot"  # 実際のリポジトリ名に変更

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool="github-pool" \
  --location="global" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'"

# IAMポリシーバインディング
PROVIDER_NAME="projects/my-crypto-bot-project/locations/global/workloadIdentityPools/github-pool/providers/github-provider"

gcloud iam service-accounts add-iam-policy-binding \
  "$SA_EMAIL" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${PROVIDER_NAME}/attribute.repository/${GITHUB_REPO}"
```

### Step 6: Secret Manager設定

```bash
# APIキー・認証情報設定
echo -n "YOUR_BITBANK_API_KEY" | gcloud secrets create bitbank-api-key --data-file=-
echo -n "YOUR_BITBANK_API_SECRET" | gcloud secrets create bitbank-api-secret --data-file=-
echo -n "YOUR_DISCORD_WEBHOOK_URL" | gcloud secrets create discord-webhook --data-file=-

# サービスアカウントに Secret Manager権限付与
for secret in bitbank-api-key bitbank-api-secret discord-webhook; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"
done
```

## 🔐 GitHub Secrets設定

GitHubリポジトリの `Settings > Secrets and variables > Actions` で以下を設定:

**Repository Secrets**:

| Name | Value | 説明 |
|------|-------|------|
| `GCP_PROJECT_ID` | `my-crypto-bot-project` | GCPプロジェクトID |
| `GCP_WIF_PROVIDER` | `projects/{PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/providers/github-provider` | Workload Identity プロバイダー |
| `GCP_SERVICE_ACCOUNT` | `github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com` | サービスアカウント |
| `DEPLOY_MODE` | `paper` | デプロイモード（paper/live制御） |

**Repository Variables**:

| Name | Value | 説明 |
|------|-------|------|
| `GCP_REGION` | `asia-northeast1` | デプロイリージョン |
| `ARTIFACT_REPOSITORY` | `crypto-bot-repo` | Artifact Repository名 |
| `CLOUD_RUN_SERVICE` | `crypto-bot-service` | Cloud Runサービス名 |

## 🚀 デプロイメント

### 自動CI/CDフロー

```bash
# ローカル品質チェック
bash scripts/testing/checks.sh

# コード変更をプッシュしてCI/CD実行
git add -A
git commit -m "feat: 新機能追加"
git push origin main

# デプロイ状況確認
gh run list --limit 5
gh run view --log
```

### モード切り替え

デプロイモードはGitHub Secrets `DEPLOY_MODE` で制御:

- `paper`: ペーパートレード（安全、推奨）
- `live`: 本番取引

```bash
# GitHub CLIでの設定例
gh secret set DEPLOY_MODE --body "paper"  # ペーパートレード
gh secret set DEPLOY_MODE --body "live"   # 本番取引
```

### 手動デプロイ（緊急時）

```bash
# 品質チェック
bash scripts/testing/checks.sh

# GCPに直接デプロイ
gcloud run deploy crypto-bot-service-prod \
  --source . \
  --region=asia-northeast1 \
  --memory=1Gi \
  --cpu=1 \
  --set-env-vars="MODE=live"
```

## 📊 監視・運用

### システム確認

```bash
# Cloud Runサービス状態確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# 最新ログ確認
gcloud logging read 'resource.type="cloud_run_revision"' --limit=20

# GitHub Actions実行状況
gh run list --workflow=ci.yml --limit=5
```

### パフォーマンス監視

**目標指標**:
- **稼働率**: 99.5%以上
- **レスポンス時間**: 平均3秒以下
- **エラー率**: 5件/時間以下

## 🚨 トラブルシューティング

### よくある問題

#### 1. GitHub Actions失敗

```bash
# 失敗詳細確認
gh run view <run-id> --log-failed

# GCP環境検証
bash scripts/deployment/verify_gcp_setup.sh --ci

# 手動修復
bash scripts/deployment/setup_ci_prerequisites.sh --repair
```

#### 2. 権限エラー

```bash
# サービスアカウント権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:*github-actions-sa*"

# Workload Identity設定確認
gcloud iam workload-identity-pools list --location=global
```

#### 3. Secret Manager接続エラー

```bash
# シークレット存在確認
gcloud secrets list

# アクセス権限確認
gcloud secrets get-iam-policy bitbank-api-key
```

### 緊急時対応

#### システム完全停止

```bash
# 1. 即座ロールバック
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1
gcloud run services update-traffic crypto-bot-service-prod \
  --to-revisions=<安定リビジョン>=100 \
  --region=asia-northeast1

# 2. 緊急停止（最終手段）
gcloud run services update crypto-bot-service-prod \
  --min-instances=0 \
  --region=asia-northeast1
```

## 📋 設定完了チェックリスト

### 基本設定
- [ ] gcloud CLI認証済み
- [ ] プロジェクト設定済み
- [ ] 必要な権限確認済み

### GCP環境
- [ ] 必要なAPI有効化済み
- [ ] Artifact Registryリポジトリ作成済み
- [ ] サービスアカウント作成済み
- [ ] Workload Identity設定済み

### Secret Manager
- [ ] bitbank-api-key設定済み
- [ ] bitbank-api-secret設定済み
- [ ] discord-webhook設定済み

### GitHub設定
- [ ] Repository Secrets設定済み
- [ ] Repository Variables設定済み
- [ ] 初回CI/CD実行成功

## 🔗 関連リソース

### スクリプト
- `scripts/deployment/setup_ci_prerequisites.sh` - 自動環境構築
- `scripts/deployment/verify_gcp_setup.sh` - 環境検証
- `scripts/testing/checks.sh` - 品質チェック

### 設定ファイル
- `config/core/unified.yaml` - 統一設定ファイル
- `.github/workflows/ci.yml` - CI/CDワークフロー

### その他ドキュメント
- `docs/運用手順/運用マニュアル.md` - 日常運用手順
- `docs/運用手順/ローカル検証手順.md` - 開発時検証手順

---

**📝 このガイドに従って環境を構築することで、安全で効率的なCI/CDパイプラインを構築し、継続的な品質改善と自動デプロイを実現できます。**