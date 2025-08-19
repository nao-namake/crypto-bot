# Crypto Bot App Module - Cloud Run Application

crypto-bot本体アプリケーションをGCP Cloud Run上で実行するためのTerraform設定モジュールです。

## 📋 概要

**目的**: BTC/JPY自動取引botをCloud Run上で24/7稼働  
**対象**: Python FastAPIアプリケーション（crypto-bot）  
**環境**: Production（実資金取引）・Paper Trade対応  
**設計原則**: 最小コスト・高可用性・個人開発最適化

## 🚀 主要機能

### **🤖 アプリケーション仕様**
- **取引対象**: Bitbank BTC/JPY信用取引
- **ML予測**: 97特徴量アンサンブル学習（LightGBM・XGBoost・RandomForest）
- **エントリー**: confidence > 0.25でリアルタイム判定
- **リスク管理**: Kelly基準・ATR損切り・1%ポジションサイジング

### **🏗️ インフラ仕様**
- **CPU**: 1000m (1.0 CPU)
- **Memory**: 2Gi (2GB RAM)  
- **Min Instances**: 1（SIGTERM対策）
- **Max Instances**: 5
- **Timeout**: 3600s（1時間）
- **リージョン**: asia-northeast1（東京）

## 📁 ファイル構成

```
crypto_bot_app/
├── main.tf      # Cloud Run Service・コンテナ設定
├── secrets.tf   # Secret Manager連携
├── variables.tf # モジュール変数定義
├── outputs.tf   # サービスURL・その他出力
└── README.md    # このファイル
```

## 🔧 Input Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `project_id` | string | GCPプロジェクトID | `"my-crypto-bot-project"` |
| `region` | string | デプロイリージョン | `"asia-northeast1"` |
| `service_name` | string | Cloud Runサービス名 | `"crypto-bot-service-prod"` |
| `image_name` | string | Dockerイメージ名 | `"crypto-bot"` |
| `image_tag` | string | Dockerイメージタグ | `"latest"`, `"${{ github.sha }}"` |
| `artifact_registry_repo` | string | Artifact Registryリポジトリ | `"crypto-bot-repo"` |
| `mode` | string | 取引モード | `"live"`, `"paper"` |
| `bitbank_api_key` | string | Bitbank APIキー（機密） | `"xxxxxxxx..."` |
| `bitbank_api_secret` | string | Bitbank APIシークレット（機密） | `"xxxxxxxx..."` |

## 🏗️ 作成されるリソース

### **Cloud Run Service**
- `google_cloud_run_service.service` - メインアプリケーション
  - **コンテナイメージ**: Artifact Registry
  - **環境変数**: MODE, 設定ファイルパス
  - **Secrets**: Bitbank API認証情報

### **Secret Manager統合**
- `google_secret_manager_secret.bitbank_api_key` - APIキー保存
- `google_secret_manager_secret.bitbank_api_secret` - APIシークレット保存
- `google_secret_manager_secret_version.*` - 各シークレットの最新版

### **IAM・Service Account**
- Cloud Run実行用のService Account
- Secret Manager読み取り権限
- Artifact Registry読み取り権限

## 📊 Output Variables

```hcl
output "service_url" {
  description = "Cloud Run サービスのURL"
  value       = google_cloud_run_service.service.status[0].url
}

output "service_name" {
  description = "サービス名"
  value       = google_cloud_run_service.service.name
}
```

## 🚀 使用方法

### Terraform設定例
```hcl
module "app" {
  source                   = "../../modules/crypto_bot_app"
  project_id              = var.project_id
  region                  = var.region
  service_name            = var.service_name
  image_name              = var.image_name
  image_tag               = var.image_tag
  artifact_registry_repo  = var.artifact_registry_repo
  mode                    = var.mode
  bitbank_api_key         = var.bitbank_api_key
  bitbank_api_secret      = var.bitbank_api_secret
}
```

## 🔒 セキュリティ

### **機密情報管理**
- **Bitbank API認証**: Secret Manager経由で安全管理
- **環境変数暗号化**: Google Cloud自動暗号化
- **最小権限の原則**: 必要最小限のIAM権限のみ

### **アクセス制御**  
- **パブリックアクセス**: `--allow-unauthenticated`（ヘルスチェック用）
- **APIエンドポイント**: 認証不要（個人用・単純化）
- **Secret Manager**: Service Accountでのみアクセス

## 🧪 デプロイ・テスト

### デプロイ後確認
```bash
# Cloud Runサービス状態確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# ヘルスチェック
curl https://[service-url]/health

# 環境変数確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 \
  --format="value(spec.template.spec.template.spec.containers[0].env[].name)"
```

### ログ確認
```bash
# アプリケーションログ
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod" --limit=10

# エラーログのみ
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10
```

## ⚠️ トラブルシューティング

### **よくある問題**

**コンテナ起動失敗**:
```bash
# イメージ確認
gcloud artifacts docker images list --repository=crypto-bot-repo --location=asia-northeast1

# ログ確認
gcloud run services logs read crypto-bot-service-prod --region=asia-northeast1
```

**Secret Manager権限エラー**:
```bash
# Service Account権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:*cloud-run*"
```

**メモリ不足・OOMKiller**:
```bash
# メモリ使用量確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:killed" --limit=5

# 対処: variables.tfでmemory="4Gi"に増量
```

## 💰 コスト最適化

### **月額コスト内訳**
| リソース | 使用量 | 月額概算 |
|----------|--------|----------|
| **Cloud Run CPU** | 1 vCPU × 24/7 | ¥1,200-1,500 |
| **Cloud Run Memory** | 2GB × 24/7 | ¥300-400 |
| **Network Egress** | API通信 | ¥50-100 |
| **Secret Manager** | 2 Secrets | ¥10-20 |
| **合計** | - | **¥1,560-2,020** |

### **最適化設定**
- **Min Instances = 1**: SIGTERM対策（若干コスト増も安定性重視）
- **Request Timeout**: 3600s（長時間処理対応）
- **Memory**: 2Gi（97特徴量処理に最適化）

## 🔄 運用・保守

### **設定変更手順**
1. `variables.tf`で設定変更
2. Git commit & push（CI/CD自動実行）
3. デプロイ後動作確認

### **スケーリング調整**
```bash
# 手動スケーリング（緊急時）
gcloud run services update crypto-bot-service-prod \
  --region=asia-northeast1 \
  --min-instances=0 \
  --max-instances=10
```

### **リソース監視**
- CPU・メモリ使用率: Cloud Monitoring
- エラー率: アラートポリシー
- レイテンシ: 定期確認

## 🔗 関連リソース

### **関連モジュール**
- **監視**: `../monitoring/` - アラート・Discord通知
- **認証**: `../workload_identity/` - GitHub Actions認証  
- **API**: `../project_services/` - GCP API有効化

### **CI/CD**
- **GitHub Actions**: `../../../.github/workflows/ci.yml`
- **Docker Build**: 自動ビルド・Artifact Registry保存

### **設定・モデル**
- **本番設定**: `config/production/production.yml`
- **本番モデル**: `models/production/model.pkl`

---

**🎊 Phase 20対応 - Google Cloud仕様完全対応・24/7安定稼働のBTC/JPY自動取引システム**（2025年8月14日）