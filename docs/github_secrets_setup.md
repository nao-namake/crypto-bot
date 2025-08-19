# GitHub Secrets設定ガイド

Phase 12 CI/CDパイプライン稼働のためのGitHub Secrets設定手順

## 📋 必要なSecrets

### 1. GCP Workload Identity認証
**GCP_WIF_PROVIDER** 
```
projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/providers/PROVIDER_ID
```

**GCP_SERVICE_ACCOUNT**
```
github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com
```

**GCP_PROJECT**
```
my-crypto-bot-project
```

### 2. デプロイ設定
**DEPLOY_MODE**
```
paper  # 初期設定（後でliveに変更）
```

## 🛠️ 設定手順

### Step 1: GCP Workload Identity設定確認

```bash
# プロジェクト情報確認
gcloud config get-value project
# → my-crypto-bot-project

# プロジェクト番号取得
gcloud projects list --filter="project_id:my-crypto-bot-project" --format="value(project_number)"

# Workload Identity Pool確認
gcloud iam workload-identity-pools list --location=global

# サービスアカウント確認
gcloud iam service-accounts list --filter="displayName:GitHub Actions"
```

### Step 2: GitHub Repository Secrets設定

1. GitHubリポジトリページに移動
2. Settings → Secrets and variables → Actions
3. 以下のSecretsを追加：

| Name | Value | 説明 |
|------|-------|------|
| `GCP_WIF_PROVIDER` | `projects/{PROJECT_NUMBER}/locations/global/workloadIdentityPools/{POOL_ID}/providers/{PROVIDER_ID}` | Workload Identity プロバイダー |
| `GCP_SERVICE_ACCOUNT` | `github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com` | GitHub Actions用サービスアカウント |
| `GCP_PROJECT` | `my-crypto-bot-project` | GCPプロジェクトID |
| `DEPLOY_MODE` | `paper` | 初期デプロイモード（段階的にliveに変更） |

### Step 3: GCP Secret Manager設定

```bash
# Bitbank API認証情報設定
echo "YOUR_BITBANK_API_KEY" | gcloud secrets create bitbank-api-key --data-file=-
echo "YOUR_BITBANK_API_SECRET" | gcloud secrets create bitbank-api-secret --data-file=-

# Discord Webhook URL設定
echo "YOUR_DISCORD_WEBHOOK_URL" | gcloud secrets create discord-webhook --data-file=-

# Secret確認
gcloud secrets list
```

### Step 4: IAM権限設定確認

```bash
# GitHub ActionsサービスアカウントにSecret Manager権限付与
gcloud secrets add-iam-policy-binding bitbank-api-key \
    --member="serviceAccount:github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding bitbank-api-secret \
    --member="serviceAccount:github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding discord-webhook \
    --member="serviceAccount:github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## 🧪 設定確認

### GitHub Actions設定テスト

```bash
# テストコミット・プッシュでCI/CD実行
git add .
git commit -m "feat: Phase 12 CI/CD初回稼働テスト"
git push origin main

# GitHub Actionsタブで実行状況確認
# https://github.com/USERNAME/REPOSITORY/actions
```

### 期待される結果

1. **Quality Check & Tests** ジョブ成功
   - 398/399テスト合格
   - 重要コンポーネントテスト成功
   - システム統合確認完了

2. **Build & Deploy to GCP** ジョブ成功
   - Docker Build & Push成功
   - Cloud Run デプロイ成功
   - ヘルスチェック成功

## 📊 監視・確認コマンド

### GitHub Actions監視
```bash
# GitHub CLI で実行状況確認
gh run list --limit 5
gh run view --log
```

### GCP デプロイ確認
```bash
# Cloud Run サービス確認
gcloud run services list --region=asia-northeast1

# サービス詳細確認
gcloud run services describe crypto-bot-service --region=asia-northeast1

# ログ確認
gcloud logging read "resource.type=\"cloud_run_revision\"" --limit=20
```

## 🚨 トラブルシューティング

### GitHub Actions失敗時
1. **認証エラー**: Workload Identity設定確認
2. **権限エラー**: IAM権限設定確認
3. **Secret未設定**: Secret Manager・GitHub Secrets確認
4. **ビルドエラー**: ローカルでDocker Buildテスト

### デプロイ失敗時
1. **イメージプッシュ失敗**: Artifact Registry権限確認
2. **Cloud Run起動失敗**: リソース設定・環境変数確認
3. **ヘルスチェック失敗**: アプリケーションログ確認

## 📋 チェックリスト

Phase 12-1実行前の確認項目：

- [ ] GCP Workload Identity Pool作成済み
- [ ] GitHub Actions用サービスアカウント作成済み
- [ ] 必要なGCP API有効化済み
- [ ] GitHub Repository Secrets設定完了
- [ ] GCP Secret Manager認証情報設定完了
- [ ] IAM権限設定完了
- [ ] ローカル環境でのテスト実行済み

---

**次のステップ**: このガイドに従ってGitHub Secrets設定完了後、CI/CDパイプライン初回実行を行い、段階的デプロイに進みます。