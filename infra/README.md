# infra/ - Terraform Infrastructure Configuration

## 🏗️ 概要

**🎊 Phase 19+完全達成: CI/CD高速化・インフラ最適化完了**  
crypto-bot プロジェクトのインフラをTerraformで管理します。**Terraform Cloud Runデプロイのタイムアウト問題を根本解決**し、個人開発に最適化した確実で堅牢な構成で、開発環境（Paper Mode）と本番環境（Live Trading）の2環境を高速安定管理します。

## 🎯 設計方針（Phase 19+高速化対応）

### **確実性・高速性・シンプルさの統一**
- **2環境のみ**: dev（Paper Mode）とprod（Live Trading）
- **Static Environment Variables**: dynamic構文排除、確実性重視
- **高速デプロイ最適化**: Terraform処理時間 10分+α → 5分以内達成
- **Provider Version整合**: CI環境とローカル検証の完全一致
- **低コスト運用**: 個人開発に適したリソース設定（月額2,200円）

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
- **リソース**: CPU 500m、Memory 1Gi（Phase 19適正サイズ調整）
- **APIキー**: static env vars（空文字列でも安定動作）
- **コスト**: 約400円/月

### **prod環境（本番稼働用）**
- **用途**: Bitbank実口座での自動取引
- **リソース**: CPU 1000m、Memory 2Gi（97特徴量最適化済み）
- **APIキー**: Bitbank API - static env vars採用で確実設定
- **コスト**: 約1,800円/月

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

### **🚀 Phase 19+高速化対応: 環境変数設定**

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
# Phase 19+: static env vars - 空文字列でも安定動作
bitbank_api_key        = ""
bitbank_api_secret     = ""
```

#### **本番環境（prod/terraform.tfvars）** (2025年8月10日更新)
```hcl
project_id     = "my-crypto-bot-project"
region         = "asia-northeast1"
service_name   = "crypto-bot-service-prod"
mode           = "live"
# API認証情報はCI/CDのGitHub Secretsから取得
# terraform.tfvarsで値を設定するとCI/CDの環境変数を上書きしてしまうため削除
# bitbank_api_key と bitbank_api_secret はCI/CD時に自動設定
```

## 🔒 Phase 19+セキュリティ強化・高速化対応

### **🎊 Static Environment Variables採用・最適化完了**
- **動的構文排除**: 複雑なdynamic for_each→シンプルstatic env vars
- **FEATURE_MODE完全削除**: 97特徴量固定により不要設定除去
- **Provider Version非依存**: Google Provider v5.x/v6.x問わず安定動作
- **確実性重視**: 空文字列でも正常動作、エラー要因除去

### **APIキー管理（2025年8月10日更新）**
- **開発環境**: APIキー不要（Paper Mode）
- **本番環境**: GitHub Secretsのみで管理（terraform.tfvarsにダミー値を設定しない）
- **ローカル**: .envファイルで管理（.gitignore必須）
- **重要**: terraform.tfvarsにAPI認証情報を設定するとCI/CDの環境変数を上書きしてしまうため削除

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
- **重要**: `infra/envs/prod/terraform.tfvars`にダミー値を設定しないこと（CI/CD環境変数を上書きしてしまう）

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

## 🔄 CI/CD統合（Phase 19+高速化対応）

### **高速化されたGitHub Actionsワークフロー**
GitHub Actionsワークフローが自動的に：
1. コードのテスト・品質チェック
2. Dockerイメージのビルド
3. Artifact Registryへのプッシュ
4. **高速Terraformデプロイ** (5分以内)

**🚀 Phase 19+達成済み改善:**
- **Terraformタイムアウト設定短縮**: 10m → 5m
- **古いCloud Runリビジョン削除**: 14個→2個（競合解消）
- **不要環境変数削除**: FEATURE_MODE除去によるCI/CD安定化

mainブランチへのプッシュで本番環境、developブランチで開発環境へ自動デプロイされます。

## 📌 注意事項

- **個人開発用の設定**: 高可用性やマルチリージョン対応は含まれていません
- **段階的な資金投入**: まず1万円で少額運用、安定後に50万円まで増額
- **監視の重要性**: 特に本番環境では定期的にログとメトリクスを確認

## 🎯 個人開発最適化ポイント

### **実装された最適化（Phase 19+対応）**
1. **環境を2つに削減**: paper環境を削除し、dev/prodのみに
2. **リソース設定を変数化**: 環境ごとにCPU/メモリを最適化
3. **dev環境を超軽量化**: CPU 250m、Memory 512Mi（約200円/月）
4. **不要な外部API削除**: Phase 3で削除済みのAPIキー参照を完全除去
5. **HA環境の削除**: 個人開発に不要な高可用性設定を除去
6. **🚀 CI/CD高速化**: Terraformタイムアウト短縮・リビジョンクリーンアップ・FEATURE_MODE削除

### **今後の簡素化候補**
- dev環境も不要な場合は、prod環境のみの単一環境構成も可能
- モニタリングアラートをさらに簡素化可能

---

## 🎊 **CI/CD完全修正・Bot取引問題解決**

### **最新の達成実績（2025年8月10日）**
- ✅ **8つの隠れたエラー修正完了**:
  - API認証失敗（ダミー値問題）解決
  - モデルファイル未発見問題解決
  - タイムスタンプ異常ループ修正
  - INIT-5ブロック問題解決
  - インスタンス切り替え問題解決
  - キャッシュロード失敗対応
  - ポート競合解決
  - データ取得非効率改善
- ✅ **CI/CD YAML構文エラー修正**: インラインPythonコードを外部スクリプト化
- ✅ **terraform.tfvars最適化**: ダミー値削除でGitHub Secrets優先

### **技術仕様確定**
- **Terraformタイムアウト**: create/update/delete = 5m
- **環境変数構成**: MODE, BITBANK_API_KEY, BITBANK_API_SECRET (3個に最適化)
- **ローカル検証**: ダミー値対応・CI/CD実際値上書き方式

---

**最終更新: 2025年8月10日**  
完全個人開発用に最適化したシンプルで低コスト・高速なインフラ構成です。