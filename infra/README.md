# infra/ - Terraform Infrastructure Configuration

## 🏗️ 概要

**個人開発向けシンプルなGCPインフラ管理**  
crypto-bot プロジェクトのインフラをTerraformで管理します。個人開発に最適化したシンプルな構成で、開発環境（Paper Mode）と本番環境（Live Trading）の2環境のみを管理します。

## 🎯 設計方針

### **シンプルで管理しやすい構成**
- **2環境のみ**: dev（Paper Mode）とprod（Live Trading）
- **必要最小限のモジュール**: Cloud Run、監視、認証のみ
- **低コスト運用**: 個人開発に適したリソース設定

## 📁 ディレクトリ構成

```
infra/
├── envs/
│   ├── dev/    # 開発環境（Paper Mode）
│   │   ├── main.tf          # 環境設定
│   │   ├── variables.tf     # 変数定義
│   │   ├── backend.tf       # Terraform状態管理
│   │   └── terraform.tfvars # 環境固有の値
│   │
│   └── prod/   # 本番環境（Live Trading）
│       ├── main.tf
│       ├── variables.tf
│       ├── backend.tf
│       └── terraform.tfvars
│
└── modules/
    ├── crypto_bot_app/     # Cloud Runアプリケーション
    ├── monitoring/         # 基本的な監視設定
    ├── project_services/   # GCP API有効化
    └── workload_identity/  # GitHub Actions認証
```

## 🚀 環境別設定

### **dev環境（開発・テスト用）**
- **用途**: 開発、テスト、Paper Modeでの動作確認
- **リソース**: CPU 250m、Memory 512Mi（超最小構成）
- **APIキー**: 不要（Paper Modeのため）
- **コスト**: 約200円/月

### **prod環境（本番稼働用）**
- **用途**: Bitbank実口座での自動取引
- **リソース**: CPU 1000m、Memory 2Gi（環境変数で調整可能）
- **APIキー**: Bitbank API必須
- **コスト**: 約2,000円/月

## ⚙️ 使用方法

### **初回セットアップ**

1. **GCPプロジェクトの準備**
```bash
# プロジェクトIDを確認
gcloud config get-value project

# 必要なAPIを有効化（Terraformが自動で行うが、念のため）
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

2. **Terraform初期化**
```bash
# 環境を選択（dev or prod）
cd infra/envs/dev/  # または prod/

# 初期化
terraform init
```

### **デプロイ手順**

#### **開発環境へのデプロイ**
```bash
cd infra/envs/dev/
terraform plan
terraform apply
```

#### **本番環境へのデプロイ**
```bash
cd infra/envs/prod/
terraform plan
terraform apply
```

### **環境変数の設定**

#### **開発環境（dev/terraform.tfvars）**
```hcl
project_id             = "my-crypto-bot-project"
region                 = "asia-northeast1"
artifact_registry_repo = "crypto-bot-repo"
service_name           = "crypto-bot-dev"
image_name             = "crypto-bot"
mode                   = "paper"
alert_email            = "your-email@example.com"
github_repo            = "your-github-username/crypto-bot"
project_number         = "123456789"
deployer_sa            = "github-deployer@my-crypto-bot-project.iam.gserviceaccount.com"
# Bitbank APIキーは不要（Paper Modeのため）
```

#### **本番環境（prod/terraform.tfvars）**
```hcl
project_id     = "my-crypto-bot-project"
region         = "asia-northeast1"
service_name   = "crypto-bot-service-prod"
mode           = "live"
# Bitbank APIキーはGitHub Secretsから取得
```

## 🔒 セキュリティ

### **APIキー管理**
- **開発環境**: APIキー不要（Paper Mode）
- **本番環境**: GitHub Secretsで管理
- **ローカル**: .envファイルで管理（.gitignore必須）

### **認証**
- **Workload Identity Federation**: キーファイルレスでGCPにアクセス
- **最小権限の原則**: 必要最小限のIAM権限のみ付与

## 📊 コスト最適化

### **月額コスト目安**
| 環境 | CPU | Memory | 推定コスト |
|------|-----|--------|-----------|
| dev  | 250m | 512Mi | ~200円/月  |
| prod | 1000m | 2Gi  | ~2,000円/月 |
| **合計** | - | - | **~2,200円/月** |

### **コスト削減のヒント**
1. 開発時以外はdev環境を停止
2. 初期は最小リソースで運用し、必要に応じて増強
3. Cloud Runの自動スケーリングを活用

## 🛠️ トラブルシューティング

### **よくある問題と解決方法**

#### **Terraform apply失敗**
```bash
# 状態をリフレッシュ
terraform refresh

# 特定のリソースのみ再作成
terraform apply -target=module.app
```

#### **Cloud Runデプロイエラー**
```bash
# サービスの状態確認
gcloud run services list --region=asia-northeast1

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

#### **APIキーエラー（本番環境）**
- GitHub Secretsに`BITBANK_API_KEY`と`BITBANK_API_SECRET`が設定されているか確認
- CI/CDワークフローでこれらのシークレットが正しく参照されているか確認

## 📝 メンテナンス

### **リソースクリーンアップ**
```bash
# 環境全体を削除（注意！）
terraform destroy

# 特定のリソースのみ削除
terraform destroy -target=module.monitoring
```

### **状態管理**
```bash
# 現在の状態を確認
terraform state list

# 状態の詳細表示
terraform state show module.app.google_cloud_run_service.service
```

## 🔄 CI/CD統合

GitHub Actionsワークフローが自動的に：
1. コードのテスト・品質チェック
2. Dockerイメージのビルド
3. Artifact Registryへのプッシュ
4. Terraformによるデプロイ

mainブランチへのプッシュで本番環境、developブランチで開発環境へ自動デプロイされます。

## 📌 注意事項

- **個人開発用の設定**: 高可用性やマルチリージョン対応は含まれていません
- **段階的な資金投入**: まず1万円で少額運用、安定後に50万円まで増額
- **監視の重要性**: 特に本番環境では定期的にログとメトリクスを確認

## 🎯 個人開発最適化ポイント

### **実装された最適化**
1. **環境を2つに削減**: paper環境を削除し、dev/prodのみに
2. **リソース設定を変数化**: 環境ごとにCPU/メモリを最適化
3. **dev環境を超軽量化**: CPU 250m、Memory 512Mi（約200円/月）
4. **不要な外部API削除**: Phase 3で削除済みのAPIキー参照を完全除去
5. **HA環境の削除**: 個人開発に不要な高可用性設定を除去

### **今後の簡素化候補**
- dev環境も不要な場合は、prod環境のみの単一環境構成も可能
- モニタリングアラートをさらに簡素化可能

---

**最終更新: 2025年8月9日**  
完全個人開発用に最適化したシンプルで低コストなインフラ構成です。