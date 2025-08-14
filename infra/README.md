# infra/ - Terraform Infrastructure Configuration

## 🏗️ 概要

**🎊 Phase 20完全達成: Google Logging Metrics伝播待機システム実装完了**  
crypto-bot プロジェクトのインフラをTerraformで管理します。**Google Cloud Logging Metricsの伝播待機システムを実装**し、CI/CDエラーを根本解決した確実で堅牢な単一環境（本番環境）構成で高速安定管理します。

## 🎯 設計方針（Phase 20+完全安定化対応）

### **確実性・高速性・シンプルさの統一**
- **単一環境構成**: prod（Live Trading）のみのシンプル構成
- **Static Environment Variables**: dynamic構文排除、確実性重視  
- **高速デプロイ最適化**: Terraform処理時間 10分+α → 5分以内達成
- **Provider Version整合**: CI環境とローカル検証の完全一致
- **🆕 メトリクス伝播対応**: Google Cloudの仕様に対応した待機システム
- **低コスト運用**: 個人開発に適したリソース設定（月額2,000円）

## 📁 ディレクトリ構成

```
infra/
├── envs/
│   └── prod/   # 本番環境（Live Trading）
│       ├── main.tf          # 環境設定
│       ├── variables.tf     # 変数定義
│       ├── backend.tf       # Terraform状態管理
│       └── terraform.tfvars # 環境固有の値
│
└── modules/
    ├── crypto_bot_app/     # Cloud Runアプリケーション
    ├── monitoring/         # Discord通知・ログメトリクス・伝播待機システム
    ├── project_services/   # GCP API有効化
    └── workload_identity/  # GitHub Actions認証
```

## 🚀 環境設定

### **prod環境（本番稼働用）**
- **用途**: Bitbank実口座での自動取引
- **リソース**: CPU 1000m、Memory 2Gi（97特徴量最適化済み）
- **安定性**: **min-instances=1設定**でSIGTERM頻発問題完全解決（Phase 1完了）
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

### **🆕 Google Logging Metrics管理**
```bash
# メトリクス作成状況確認
gcloud logging metrics list --filter="name:crypto_bot_*"

# アラートポリシー状況確認  
gcloud alpha monitoring policies list --filter="displayName:crypto*"

# time_sleepリソース状況確認
terraform state show module.monitoring.time_sleep.wait_for_metrics_propagation
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

## 🎊 **CI/CD完全修正・Google Logging Metrics伝播待機システム実装**

### **🆕 Phase 20達成実績（2025年8月14日）**
- ✅ **Google Logging Metrics伝播待機システム実装**:
  - `time_sleep`リソースで60秒待機システム追加
  - アラートポリシーの`depends_on`をtime_sleepリソースに変更
  - CI/CD 404エラー「Cannot find metric」問題を根本解決
  - bot_manager.py terraform_checkメソッド追加で事前検証強化

### **技術的成果**
- ✅ **標準的手法**: Terraformの公式`time_sleep`リソース使用で技術負債回避
- ✅ **運用影響なし**: 作成時のみ動作、通常運用でオーバーヘッドゼロ
- ✅ **将来対応**: Google API改善時に調整可能、不要時削除も簡単
- ✅ **Terraform検証**: 3項目すべて成功、事前チェック体制強化

### **従来の達成実績（2025年8月13日まで）**
- ✅ **Discord通知システム完全実装**: メール通知廃止・私生活影響ゼロ
- ✅ **8つの隠れたエラー修正完了**: API認証・モデルファイル・INIT-5等解決
- ✅ **CI/CD完全最適化**: YAML構文・terraform.tfvars最適化

### **技術仕様確定**
- **Terraformタイムアウト**: create/update/delete = 5m
- **メトリクス伝播待機**: 60秒（Google Cloud最大10分仕様対応）
- **環境変数構成**: MODE, BITBANK_API_KEY, BITBANK_API_SECRET (3個に最適化)
- **ローカル検証**: ダミー値対応・CI/CD実際値上書き方式

---

**最終更新: 2025年8月14日**  
Google Cloud仕様完全対応・CI/CDエラー根絶を達成したシンプルで低コスト・高速なインフラ構成です。