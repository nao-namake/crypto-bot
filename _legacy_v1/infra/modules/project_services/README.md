# Project Services Module - GCP API有効化

crypto-botプロジェクトで必要なGoogle Cloud Platform APIサービスを有効化するTerraform設定モジュールです。

## 📋 概要

**目的**: crypto-bot稼働に必要なGCP APIサービスの一括有効化  
**対象**: Cloud Run・Artifact Registry・Secret Manager・Monitoring・Functions等  
**設計原則**: 必要最小限のAPI・権限管理・自動化

## 🚀 有効化されるAPIサービス

### **コアサービス**
| API | 用途 | 必須度 |
|-----|------|--------|
| `run.googleapis.com` | Cloud Run（アプリ実行） | 🔴 必須 |
| `artifactregistry.googleapis.com` | Docker image保存 | 🔴 必須 |
| `secretmanager.googleapis.com` | API認証情報管理 | 🔴 必須 |

### **監視・通知システム**  
| API | 用途 | 必須度 |
|-----|------|--------|
| `monitoring.googleapis.com` | アラート・メトリクス | 🔴 必須 |
| `logging.googleapis.com` | ログ管理・メトリクス | 🔴 必須 |
| `cloudfunctions.googleapis.com` | Discord通知Functions | 🔴 必須 |
| `pubsub.googleapis.com` | アラート配信 | 🔴 必須 |

### **CI/CD・認証**
| API | 用途 | 必須度 |
|-----|------|--------|
| `iamcredentials.googleapis.com` | Workload Identity | 🔴 必須 |
| `sts.googleapis.com` | Security Token Service | 🔴 必須 |
| `cloudbuild.googleapis.com` | Docker build（オプション） | 🟡 オプション |

## 📁 ファイル構成

```
project_services/
├── main.tf      # API有効化・IAM権限設定
├── variables.tf # サービスリスト・プロジェクト設定
├── outputs.tf   # 有効化されたサービス一覧
└── README.md    # このファイル
```

## 🔧 Input Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `project_id` | string | GCPプロジェクトID | `"my-crypto-bot-project"` |
| `project_number` | string | GCPプロジェクト番号 | `"123456789012"` |
| `services` | list(string) | 有効化するAPIサービス一覧 | 下記参照 |

### **services変数の内容**
```hcl
services = [
  "run.googleapis.com",                    # Cloud Run
  "artifactregistry.googleapis.com",      # Artifact Registry  
  "secretmanager.googleapis.com",         # Secret Manager
  "monitoring.googleapis.com",            # Cloud Monitoring
  "logging.googleapis.com",               # Cloud Logging
  "cloudfunctions.googleapis.com",        # Cloud Functions
  "pubsub.googleapis.com",                # Pub/Sub
  "iamcredentials.googleapis.com",        # Workload Identity
  "sts.googleapis.com",                   # Security Token Service
  "cloudbuild.googleapis.com",            # Cloud Build (オプション)
]
```

## 🏗️ 作成されるリソース

### **APIサービス有効化**
- `google_project_service.enabled` - 各APIサービスの有効化
  - **disable_on_destroy**: true（Terraform destroy時に無効化）
  - **for_each**: services変数の各要素に対して実行

### **IAM権限設定**
- `google_project_iam_member.run_sa_ar_reader` - Cloud Run SA→Artifact Registry読み取り
- `google_project_iam_member.run_sa_secret_accessor` - Cloud Run SA→Secret Manager読み取り

### **自動設定されるService Account権限**
```
Cloud Run実行SA: <PROJECT_NUMBER>-compute@developer.gserviceaccount.com
├── roles/artifactregistry.reader      # Docker image取得
└── roles/secretmanager.secretAccessor # API認証情報取得

Serverless Robot SA: service-<PROJECT_NUMBER>@serverless-robot-prod.iam.gserviceaccount.com  
└── roles/artifactregistry.reader      # Cloud Run Artifact Registry連携
```

## 📊 Output Variables

```hcl
output "enabled_services" {
  description = "有効化されたAPIサービス一覧"
  value       = [for service in google_project_service.enabled : service.service]
}
```

## 🚀 使用方法

### Terraform設定例
```hcl
module "services" {
  source         = "../../modules/project_services"  
  project_id     = var.project_id
  project_number = var.project_number
  services = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com", 
    "secretmanager.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudfunctions.googleapis.com",
    "pubsub.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com"
  ]
}
```

## 🧪 デプロイ・確認

### デプロイ後確認
```bash
# 有効化されたAPIサービス確認
gcloud services list --enabled --project=my-crypto-bot-project

# 特定サービス確認  
gcloud services list --filter="name:run.googleapis.com" --project=my-crypto-bot-project

# IAM権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:*compute@developer.gserviceaccount.com"
```

### 手動API有効化（必要時）
```bash
# 個別API有効化
gcloud services enable run.googleapis.com --project=my-crypto-bot-project
gcloud services enable artifactregistry.googleapis.com --project=my-crypto-bot-project

# 一括API有効化
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com --project=my-crypto-bot-project
```

## ⚠️ トラブルシューティング

### **よくある問題**

**API有効化失敗**:
```bash
# プロジェクト確認
gcloud config get-value project

# 権限確認（Editor以上必要）
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:*your-email*"
```

**Service Account権限不足**:
```bash
# Cloud Run実行SAの権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:*compute@developer.gserviceaccount.com"

# 手動権限付与（必要時）
gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:123456789012-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**Terraform destroy失敗**:
```bash
# API無効化エラー回避
terraform destroy -target=module.services.google_project_service.enabled
```

## 🔄 API依存関係

### **初期化順序**
1. **project_services** - 最初に実行（他モジュールの依存関係）
2. **workload_identity** - IAM・認証設定  
3. **crypto_bot_app** - Cloud Run・Secret Manager
4. **monitoring** - Monitoring・Functions・Pub/Sub

### **削除順序**
1. **monitoring** - アプリケーション依存リソース
2. **crypto_bot_app** - Cloud Runアプリ
3. **workload_identity** - 認証設定
4. **project_services** - 最後に削除（API無効化）

## 💰 コスト

### **API使用料金**
- **APIサービス有効化**: 無料
- **API呼び出し**: 従量制（月額¥10-50程度）
- **IAM権限管理**: 無料

## 🔗 関連リソース

### **関連モジュール**
- **crypto_bot_app**: Cloud Run・Secret Manager使用
- **monitoring**: Cloud Monitoring・Functions・Pub/Sub使用  
- **workload_identity**: IAM Credentials・STS使用

### **GCP Console確認**
- **APIサービス**: [APIs & Services](https://console.cloud.google.com/apis)
- **IAM権限**: [IAM & Admin](https://console.cloud.google.com/iam-admin)
- **サービスアカウント**: [Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)

---

**🎊 Phase 20対応 - Google Cloud API完全統合・crypto-bot稼働基盤**（2025年8月14日）