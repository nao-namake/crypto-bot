# infra/ - Infrastructure as Code (IaC) システム

## 🏗️ 概要

**Terraform-based Multi-Environment Infrastructure Management**  
本フォルダは crypto-bot プロジェクトの全環境（開発・本番・HA構成・K8s等）のGCPインフラストラクチャを**Infrastructure as Code**で管理する統合基盤システムです。

## 🎯 設計原則

### **モジュラー設計 (Modular Architecture)**
- **再利用可能モジュール**: 共通インフラをモジュール化・環境間で再利用
- **環境分離**: dev/paper/prod/ha-prod/k8s-gke 完全分離
- **設定外部化**: terraform.tfvars による環境固有設定

### **スケーラブル・マルチ環境対応**
```
Single Region → Multi-Region → High Availability → Kubernetes
    ↓              ↓              ↓                 ↓
  dev/prod     ha-prod     Load Balancer        GKE Auto-scaling
```

## 📁 ディレクトリ構成

### `/envs` - 環境別設定

#### **`dev/` - 開発環境**
```terraform
# 軽量・コスト最適化開発環境
module "app" {
  source = "../../modules/crypto_bot_app"
  mode   = "paper"  # ペーパートレード
  cpu    = "500m"   # 最小リソース
  memory = "1Gi"
}
```

#### **`prod/` - 本番環境**  
```terraform
# Phase 14 現在の本番稼働環境
module "app" {
  source = "../../modules/crypto_bot_app"
  mode   = "live"   # リアルトレード
  cpu    = "1000m"  # 1 CPU (Phase H.25 外部API無効化により削減)
  memory = "2Gi"    # 2GB RAM (125特徴量対応)
}
```

#### **`paper/` - ペーパートレード環境**
```terraform
# 本番同等設定でのペーパートレード検証
module "app" {
  mode = "paper"
  # 本番と同等のリソース・設定で安全検証
}
```

#### **`ha-prod/` - 高可用性本番環境**
```terraform
# マルチリージョン・ロードバランサー対応
module "multi_region_app" {
  primary_region         = "asia-northeast1"    # 東京
  secondary_region       = "us-central1"        # バックアップ
  enable_load_balancer   = true
  enable_ssl             = true
}
```

#### **`k8s-gke/` - Kubernetes環境**
```terraform
# GKE (Google Kubernetes Engine) 対応
module "gke" {
  cluster_name     = "${var.environment}-crypto-bot-gke"
  node_count       = var.node_count
  enable_spot_nodes = true  # コスト最適化
}
```

### `/modules` - 再利用可能モジュール

#### **`crypto_bot_app/` - メインアプリケーション**
```terraform
# Cloud Run service + 環境設定
resource "google_cloud_run_service" "service" {
  name     = var.service_name
  location = var.region
  
  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"
        
        resources {
          limits = {
            cpu    = "1000m"  # Phase H.25: 外部API無効化により削減  
            memory = "2Gi"    # 125特徴量対応
          }
        }
        
        # Phase 14 環境変数統合
        env {
          name  = "MODE"
          value = var.mode
        }
        env {
          name  = "FEATURE_MODE" 
          value = var.feature_mode
        }
      }
    }
  }
}
```

#### **`monitoring/` - 監視・アラート**
```terraform
# GCP Cloud Monitoring 統合
resource "google_monitoring_alert_policy" "latency" {
  display_name = "High request latency"
  conditions {
    display_name = "Latency > 3s"
    # Phase 14 パフォーマンス監視
  }
}

resource "google_monitoring_alert_policy" "pnl_loss" {
  display_name = "Crypto Bot Loss Alert" 
  conditions {
    display_name = "PnL < -5000 JPY"  # 損失アラート
  }
}
```

#### **`workload_identity/` - セキュア認証**
```terraform
# GitHub Actions → GCP 認証 (Keyless)
resource "google_iam_workload_identity_pool_provider" "provider" {
  attribute_condition = "attribute.repository == \"${var.github_repo}\" && attribute.ref == \"refs/heads/main\""
  
  # Phase 14 CI/CD セキュリティ強化
  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}

# 最小権限の原則
resource "google_project_iam_member" "deployer_sa_run_admin" {
  role = "roles/run.admin"  # Cloud Run デプロイのみ
}
```

#### **`project_services/` - API有効化**
```terraform
# 必要なGCP APIを自動有効化
resource "google_project_service" "enabled" {
  for_each = toset([
    "run.googleapis.com",           # Cloud Run
    "artifactregistry.googleapis.com", # Container Registry  
    "monitoring.googleapis.com",    # Cloud Monitoring
    "secretmanager.googleapis.com", # API Key管理
  ])
  service = each.value
}
```

#### **その他モジュール**
- **`multi_region_app/`**: マルチリージョン対応アプリ
- **`multi_region_monitoring/`**: リージョン横断監視
- **`gke/`**: Google Kubernetes Engine設定
- **`eks/`**: Amazon EKS設定 (将来対応)

## ⚙️ 使用方法

### **基本的なデプロイフロー**

#### **1. 環境選択・初期化**
```bash
# 本番環境の場合
cd infra/envs/prod/

# Terraform初期化
terraform init
```

#### **2. 設定確認・計画**  
```bash
# 設定ファイル確認
cat terraform.tfvars

# デプロイ計画表示
terraform plan
```

#### **3. インフラ適用**
```bash
# 本番デプロイ実行
terraform apply

# 特定リソースのみ適用
terraform apply -target=module.app
```

### **環境別設定例**

#### **terraform.tfvars (prod環境)**
```hcl
# Phase 14 本番環境設定
project_id     = "my-crypto-bot-project"
region         = "asia-northeast1"
service_name   = "crypto-bot-service-prod"
mode           = "live"
feature_mode   = "full"

# API Keys (Secret Manager参照)
bitbank_api_key    = "projects/my-crypto-bot-project/secrets/bitbank-api-key/versions/latest"
bitbank_api_secret = "projects/my-crypto-bot-project/secrets/bitbank-api-secret/versions/latest"
```

#### **terraform.tfvars (dev環境)**
```hcl
# 軽量開発環境設定
project_id     = "my-crypto-bot-dev"
region         = "asia-northeast1"
service_name   = "crypto-bot-dev"
mode           = "paper"
feature_mode   = "lite"
```

## 🔒 セキュリティ・ベストプラクティス

### **認証・認可**
- ✅ **Workload Identity Federation**: キーファイル不要認証
- ✅ **最小権限原則**: 必要最小限のIAM権限のみ付与
- ✅ **Secret Manager**: API key等の機密情報管理

### **ネットワークセキュリティ**
```terraform
# Cloud Run セキュリティ設定
resource "google_cloud_run_service_iam_member" "all_users" {
  role   = "roles/run.invoker"
  member = "allUsers"  # パブリック公開 (ヘルスチェック用)
}

# VPC設定 (ha-prod環境)
resource "google_compute_network" "vpc" {
  name                    = "crypto-bot-vpc"
  auto_create_subnetworks = false
}
```

### **監査・コンプライアンス**
- ✅ **Terraform State**: GCS remote backend で状態管理
- ✅ **バージョン管理**: Git でインフラ変更履歴追跡
- ✅ **承認フロー**: Pull Request でインフラ変更レビュー

## 📊 環境・構成比較

| 環境 | 用途 | CPU | Memory | Auto-scaling | HA | 監視 |
|------|------|-----|--------|--------------|----|----- |
| **dev** | 開発・テスト | 500m | 1Gi | ❌ | ❌ | 基本 |
| **paper** | ペーパートレード | 1000m | 2Gi | ❌ | ❌ | 標準 |
| **prod** | 本番稼働 | 1000m | 2Gi | ✅ | ❌ | 完全 |
| **ha-prod** | HA本番 | 1000m | 2Gi | ✅ | ✅ | 完全+ |
| **k8s-gke** | Kubernetes | 可変 | 可変 | ✅ | ✅ | 完全+ |

## 🚀 Phase 14 統合効果

### **従来の課題解決**
- ❌ **Phase 13以前**: 手動インフラ管理・環境不整合
- ❌ **Phase 13以前**: セキュリティ設定の属人化

### **Phase 14で達成**
- ✅ **Infrastructure as Code**: 全インフラをコード管理
- ✅ **環境整合性**: 同一モジュール・異なる設定での環境構築
- ✅ **自動CI/CD統合**: GitHub Actions でのインフラ自動デプロイ
- ✅ **セキュリティ強化**: WIF・最小権限・監査ログ完備
- ✅ **スケーラビリティ**: 単一リージョン→マルチリージョン対応

### **運用コスト最適化**
```
開発環境: ~¥500/月   (軽量設定)
本番環境: ~¥3,650/月 (Phase 14最適化)
HA環境:   ~¥7,300/月 (冗長化対応)
```

## 🛠️ メンテナンス・トラブルシューティング

### **状態管理**
```bash
# Terraform状態確認
terraform state list

# 特定リソース状態表示
terraform state show module.app.google_cloud_run_service.service

# 状態同期  
terraform refresh
```

### **リソース管理**
```bash
# 未使用リソース特定
terraform plan -destroy

# 特定リソース削除
terraform destroy -target=module.monitoring

# インフラ全削除 (注意)
terraform destroy
```

### **デバッグ・ログ**
```bash  
# Terraform詳細ログ
TF_LOG=DEBUG terraform apply

# GCPリソース直接確認
gcloud run services list --region=asia-northeast1
```

---

**Infrastructure as Code**により、crypto-botのインフラ管理は完全に自動化・標準化されました。**Phase 14 Modular Architecture**と統合し、開発から本番まで一貫したインフラ運用基盤を確立しています。🏗️🚀