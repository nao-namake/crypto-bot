# Production Environment (infra/envs/prod)

crypto-bot本番環境のTerraform設定です。GCP Cloud Run上でBTC/JPY自動取引を実行します。

## 📋 概要

**環境**: 本番（Production）  
**GCPプロジェクト**: `my-crypto-bot-project`  
**リージョン**: `asia-northeast1` (東京)  
**デプロイ**: CI/CD自動 (`git push origin main`)  
**コスト**: 月額¥2,000以内

## 🎊 2025年8月13日 Discord通知システム完成

**重大変更**: メール通知 → Discord通知完全移行  
- ✅ **`alert_email`変数削除** → **`discord_webhook_url`変数追加**
- ✅ **デプロイ時大量メール問題**完全解決
- ✅ **CI/CD自動設定**: GitHub Secrets経由で安全管理

## 📁 ファイル構成

```
prod/
├── main.tf           # メインTerraform設定・モジュール呼び出し
├── variables.tf      # 環境変数定義
├── terraform.tfvars  # 本番固有値（🔐Discord URL除く）
├── backend.tf        # Terraform State管理
└── README.md         # このファイル
```

## 🏗️ インフラ構成

### **作成されるリソース**
- **Cloud Run Service**: `crypto-bot-service-prod` (BTC/JPY自動取引)
- **Artifact Registry**: Docker image保存 (`crypto-bot-repo`)
- **Monitoring**: Discord通知システム (6種アラート)
- **Cloud Functions**: `webhook-notifier` (Discord送信)
- **Secret Manager**: Discord Webhook URL保存
- **Workload Identity**: GitHub Actions認証

### **モジュール構成**
```hcl
module "app"        # crypto_bot_app (Cloud Run・API認証)
module "monitoring" # monitoring (Discord通知・アラート)  
module "wif"        # workload_identity (GitHub Actions認証)
module "services"   # project_services (GCP API有効化)
```

## ⚙️ 設定詳細

### **Input Variables**

| Variable | 設定値 | 説明 | 例 |
|----------|--------|------|-----|
| `project_id` | `my-crypto-bot-project` | GCPプロジェクトID | 固定 |
| `region` | `asia-northeast1` | デプロイリージョン | 東京 |
| `service_name` | `crypto-bot-service-prod` | Cloud Runサービス名 | 本番固定 |
| `image_name` | `crypto-bot` | Docker イメージ名 | 固定 |
| `image_tag` | `${{ github.sha }}` | Git SHA（CI/CD自動） | 動的 |
| `mode` | `live` | 取引モード | **実資金取引** |
| `discord_webhook_url` | GitHub Secret | Discord通知URL | 🔐機密 |
| `bitbank_api_key` | GitHub Secret | Bitbank APIキー | 🔐機密 |
| `bitbank_api_secret` | GitHub Secret | Bitbank APIシークレット | 🔐機密 |

### **🔐 機密情報管理 (GitHub Secrets)**
```bash
# 必要なSecrets（CI/CDで自動設定）
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
BITBANK_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
BITBANK_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### **リソース仕様**
```yaml
Cloud Run:
  CPU: 1000m (1.0 CPU)
  Memory: 2Gi (2GB RAM)
  Min Instances: 1 (SIGTERM対策)
  Max Instances: 5
  Timeout: 3600s (1時間)
  
Artifact Registry:
  Repository: crypto-bot-repo
  Location: asia-northeast1
  
Cloud Functions:
  Name: webhook-notifier
  Runtime: python311
  Memory: 128MB
  Timeout: 60s
```

## 🚀 デプロイフロー

### **自動デプロイ (推奨)**
```bash
# コードコミット・プッシュでCI/CD自動実行
git add -A
git commit -m "feat: your changes"
git push origin main

# GitHub Actions進行確認
# https://github.com/nao-namake/crypto-bot/actions
```

### **手動デプロイ (緊急時)**
```bash
# 1. 環境変数設定
export TF_VAR_discord_webhook_url="$DISCORD_WEBHOOK_URL"
export TF_VAR_bitbank_api_key="$BITBANK_API_KEY" 
export TF_VAR_bitbank_api_secret="$BITBANK_API_SECRET"

# 2. Terraform実行
cd infra/envs/prod/
terraform init
terraform plan
terraform apply
```

## 🧪 デプロイ後確認

### **必須確認項目**

**1. Cloud Run状態**:
```bash
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
```

**2. Discord通知テスト**:
```bash
python scripts/monitoring/discord_notification_test.py --type direct
```

**3. ヘルスチェック**:
```bash
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health
```

**4. 完璧稼働状況確認**:
```bash
python scripts/operational_status_checker.py --verbose
```

### **ログ監視**
```bash
# アプリケーションログ (日本時間)
python scripts/utilities/gcp_log_viewer.py --hours 0.5

# システムログ (UTC)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod" --limit=5
```

## ⚠️ トラブルシューティング

### **よくある問題**

**Discord通知が送信されない**:
```bash
# Webhook URL確認
gh secret list | grep DISCORD_WEBHOOK_URL

# Cloud Functions状態確認  
gcloud functions describe webhook-notifier --region=asia-northeast1

# テスト送信
python scripts/monitoring/discord_notification_test.py --type direct
```

**デプロイ失敗**:
```bash
# GitHub Actions ログ確認
gh run list --limit=5
gh run view [run-id]

# Terraform State確認
cd infra/envs/prod/
terraform show
```

**取引が実行されない**:
```bash
# 設定確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 \
  --format="value(spec.template.spec.template.spec.containers[0].env[?(@.name=='MODE')].value)"

# ログ確認  
python scripts/utilities/gcp_log_viewer.py --search "TRADE"
```

**API認証エラー**:
```bash
# Secrets確認
gh secret list | grep BITBANK

# Cloud Run環境変数確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 \
  --format="value(spec.template.spec.template.spec.containers[0].env[].name)"
```

## 📊 モニタリング・アラート

### **Discord通知アラート（6種類）**
1. **💰 PnL損失**: 10,000円超損失（赤色・重要）
2. **❌ エラー率**: 10%超システムエラー（オレンジ・中）  
3. **⚡ 取引失敗**: 5回連続エントリー失敗（赤色・最重要）
4. **🚨 システム停止**: ヘルスチェック失敗（赤色・重要）
5. **📊 メモリ異常**: 85%超使用率（黄色・中）
6. **📡 データ停止**: 10分超取得停止（赤色・重要）

### **監視コマンド**
```bash
# アラート状態確認
gcloud alpha monitoring policies list --project=my-crypto-bot-project

# Cloud Functions監視  
gcloud functions logs read webhook-notifier --region=asia-northeast1 --limit=10
```

## 💰 コスト管理

### **月額予算目標: ¥2,000以内**

| リソース | 月額概算 | 備考 |
|----------|-----------|------|
| Cloud Run | ¥1,500-1,800 | CPU・メモリ・リクエスト |
| Artifact Registry | ¥50-100 | Docker image保存 |
| Cloud Functions | ¥50-100 | Discord通知送信 |
| Secret Manager | ¥10-20 | API key保存 |
| Monitoring | ¥10-30 | アラート・ログ |
| **合計** | **¥1,620-2,050** | **目標範囲内** |

### **コスト最適化設定**
- **Min Instances**: 1 (SIGTERM対策・若干コスト増)
- **Max Instances**: 5 (トラフィック制限)
- **Function Memory**: 128MB (最小設定)
- **Log Retention**: 30日 (標準)

## 🔄 環境管理

### **設定変更手順**
1. `terraform.tfvars` または `variables.tf` を編集
2. GitHub Secrets更新（機密情報）
3. `git push origin main` で自動デプロイ
4. Discord通知テストで動作確認

### **緊急時操作**  
```bash
# サービス停止 (緊急時)
gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --no-traffic

# サービス再開
gcloud run services update crypto-bot-service-prod --region=asia-northeast1 --traffic=latest=100
```

### **バックアップ・復旧**
- **Terraform State**: GCS Backend自動管理
- **Docker Images**: Artifact Registry自動保持
- **設定ファイル**: Git管理・バージョン管理済

## 🔗 関連リソース

### **設定ファイル**
- **アプリ**: `../modules/crypto_bot_app/`
- **監視**: `../modules/monitoring/`  
- **認証**: `../modules/workload_identity/`

### **CI/CD**
- **GitHub Actions**: `../../.github/workflows/ci.yml`
- **Secret管理**: GitHub Repository Settings

### **監視・テスト**
- **Discord通知**: `../../scripts/monitoring/discord_notification_test.py`
- **稼働監視**: `../../scripts/operational_status_checker.py`

---

**🎊 メール通知完全廃止・Discord移行完成の本番環境**（2025年8月13日）