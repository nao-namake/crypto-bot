# Workload Identity Module - GitHub Actions認証

GitHub ActionsからGCPへの安全なキーファイルレス認証を実現するWorkload Identity Federation設定のTerraform設定モジュールです。

## 📋 概要

**目的**: GitHub ActionsのCI/CDからGCPリソースへの安全認証  
**方式**: Workload Identity Federation（キーファイルレス）  
**対象**: crypto-bot GitHubリポジトリからの自動デプロイ  
**セキュリティ**: 最小権限・リポジトリ・ブランチ限定

## 🔒 セキュリティ機能

### **🎯 Workload Identity Federationの利点**
- ✅ **キーファイル不要**: JSONキーファイル管理の廃止
- ✅ **短期間トークン**: 最大12時間の自動有効期限
- ✅ **リポジトリ限定**: 指定GitHubリポジトリのみからアクセス
- ✅ **ブランチ限定**: mainブランチのみからの実行制限
- ✅ **監査ログ**: すべての認証・操作が追跡可能

### **🛡️ 設定されるセキュリティ制約**
- **Repository**: `nao-namake/crypto-bot` のみ
- **Branch**: `refs/heads/main` のみ  
- **Issuer**: `https://token.actions.githubusercontent.com` のみ
- **Subject**: GitHub Actionsワークフロー実行コンテキスト

## 📁 ファイル構成

```
workload_identity/
├── main.tf                    # WIF Pool・Provider・Service Account
├── hardening_verification.tf # セキュリティ検証・制約確認
├── variables.tf              # 設定変数
├── outputs.tf                # Provider ID・Service Account出力
└── README.md                 # このファイル
```

## 🔧 Input Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `project_id` | string | GCPプロジェクトID | `"my-crypto-bot-project"` |
| `project_number` | string | GCPプロジェクト番号 | `"123456789012"` |
| `pool_id` | string | Workload Identity Pool ID | `"github-pool"` |
| `provider_id` | string | Provider ID | `"github-provider"` |
| `service_account_id` | string | Service Account ID | `"github-deployer"` |
| `github_repo` | string | GitHubリポジトリ | `"nao-namake/crypto-bot"` |

## 🏗️ 作成されるリソース

### **Workload Identity Federation**
- `google_iam_workload_identity_pool.pool` - 認証プール
- `google_iam_workload_identity_pool_provider.provider` - GitHub Provider
  - **OIDC設定**: GitHub Actions Token Service
  - **属性マッピング**: subject・repository・ref
  - **条件制約**: 指定リポジトリ・mainブランチのみ

### **Service Account・権限**
- `google_service_account.deployer` - デプロイ専用SA
- **IAM権限**:
  - `roles/run.admin` - Cloud Run完全管理
  - `roles/iam.serviceAccountUser` - SA権限借用
  - `roles/artifactregistry.admin` - Docker image管理
  - `roles/secretmanager.admin` - 機密情報管理
  - `roles/monitoring.admin` - 監視システム管理
  - `roles/cloudfunctions.admin` - Functions管理
  - `roles/pubsub.admin` - Pub/Sub管理
  - `roles/storage.admin` - GCS管理

### **セキュリティ検証**
- `google_iam_workload_identity_pool_provider.hardening_check` - 制約検証
- `google_service_account_iam_member.wif_sa_binding` - WIF⇔SA連携

## 📊 Output Variables

```hcl
output "workload_identity_provider_name" {
  description = "Workload Identity Provider完全名"
  value       = google_iam_workload_identity_pool_provider.provider.name
}

output "service_account_email" {  
  description = "デプロイ用Service Accountメール"
  value       = google_service_account.deployer.email
}
```

## 🚀 GitHub Actions設定

### **CI/CD Workflow設定例**
```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # 重要: OIDC Token取得権限
    
    steps:
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_DEPLOYER_SA }}
          access_token_lifetime: 7200s  # 2時間
```

### **必要なGitHub Secrets**
```bash
# Workload Identity Provider ID (projects/123/locations/global/workloadIdentityPools/github-pool/providers/github-provider)
GCP_WIF_PROVIDER=projects/123456789012/locations/global/workloadIdentityPools/github-pool/providers/github-provider

# Service Account Email
GCP_DEPLOYER_SA=github-deployer@my-crypto-bot-project.iam.gserviceaccount.com

# その他
GCP_PROJECT_ID=my-crypto-bot-project
GCP_PROJECT_NUMBER=123456789012
```

## 🧪 デプロイ・検証

### デプロイ後確認
```bash
# Workload Identity Pool確認
gcloud iam workload-identity-pools list --location=global --project=my-crypto-bot-project

# Provider確認  
gcloud iam workload-identity-pools providers list \
  --workload-identity-pool=github-pool \
  --location=global \
  --project=my-crypto-bot-project

# Service Account確認
gcloud iam service-accounts list --project=my-crypto-bot-project \
  --filter="email:github-deployer@*"

# 権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:*github-deployer*"
```

### GitHub Actions認証テスト
```bash
# GitHub Actions実行時のToken検証
gcloud logging read "protoPayload.authenticationInfo.principalEmail:github-deployer@*" \
  --limit=5 \
  --project=my-crypto-bot-project
```

## ⚠️ トラブルシューティング

### **よくある問題**

**認証失敗 "Permission denied"**:
```bash
# WIF Provider設定確認
gcloud iam workload-identity-pools providers describe github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --project=my-crypto-bot-project

# 条件制約確認（リポジトリ・ブランチ）
# attribute_condition = "attribute.repository == "nao-namake/crypto-bot" && attribute.ref == "refs/heads/main""
```

**"Token exchange failed"**:
```bash
# GitHub Secrets確認
gh secret list --repo nao-namake/crypto-bot | grep GCP_

# Provider OIDC設定確認
gcloud iam workload-identity-pools providers describe github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --project=my-crypto-bot-project \
  --format="value(oidc.issuerUri)"
```

**Service Account権限不足**:
```bash
# 必要権限の手動付与（緊急時）
gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:github-deployer@my-crypto-bot-project.iam.gserviceaccount.com" \
  --role="roles/run.admin"
```

## 🔄 セキュリティ監査・維持管理

### **定期確認項目**
- **月次**: Service Account使用状況・権限過多チェック
- **四半期**: 認証ログ分析・不審なアクセス確認
- **半年**: Workload Identity設定見直し・セキュリティ強化

### **監査コマンド**
```bash
# 認証ログ確認（過去7日間）
gcloud logging read "protoPayload.authenticationInfo.principalEmail:github-deployer@*" \
  --freshness=7d \
  --project=my-crypto-bot-project

# Service Account鍵確認（0個が正常）
gcloud iam service-accounts keys list \
  --iam-account=github-deployer@my-crypto-bot-project.iam.gserviceaccount.com

# 不要権限チェック
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:*github-deployer*"
```

## 💰 コスト

### **WIF使用料金**
- **Workload Identity Federation**: 無料
- **Service Account**: 無料  
- **認証Token取得**: 無料
- **監査ログ**: ¥10-20/月（30日保持）

## 🔗 関連リソース

### **GitHub Actions**
- **CI/CD Workflow**: `../../../.github/workflows/ci.yml`
- **Repository Settings**: Secrets・Security設定

### **GCP Console**
- **Workload Identity**: [IAM & Admin → Workload Identity Federation](https://console.cloud.google.com/iam-admin/workload-identity-pools)  
- **Service Accounts**: [IAM & Admin → Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
- **Audit Logs**: [Logging → Logs Explorer](https://console.cloud.google.com/logs/)

### **関連モジュール**
- **project_services**: IAM API・STS API有効化
- **crypto_bot_app**: Service Account→Cloud Run権限  
- **monitoring**: Service Account→Monitoring権限

---

**🎊 Phase 20対応 - セキュアなキーファイルレスCI/CD認証システム**（2025年8月14日）