# Monitoring Module - Google Logging Metrics伝播待機システム

crypto-botのためのCloud Monitoring・アラート・Discord通知システムのTerraform設定モジュールです。**Phase 20: Google Logging Metrics伝播待機システム実装完了**

## 📋 概要

**目的**: 重要なシステム異常のDiscord通知・メール通知完全廃止  
**対象**: Cloud Run `crypto-bot-service-prod` の監視  
**通知先**: Discord Webhook（埋め込みメッセージ形式）  
**設計原則**: 重要アラートのみ・私生活影響ゼロ・Google Cloud仕様完全対応

## 🎯 2025年8月14日 Phase 20完成 - Google Logging Metrics伝播待機システム実装完了

### **🆕 Phase 20で解決した問題**
- **🚀 CI/CD 404エラー**: Google Logging Metrics「Cannot find metric」根本解決
- **⏰ メトリクス伝播待機**: `time_sleep`リソース60秒待機でGoogle Cloud仕様対応
- **📊 技術負債回避**: 標準的手法・作成時のみ動作・将来調整可能

### **✅ 前Phase完了実績**
- **❌ デプロイ時大量メール**: 数十通 → ゼロ通
- **❌ 不要なアラート**: 高レイテンシアラート削除
- **✅ Discord管理**: チャンネル単位での整理  
- **✅ 視認性向上**: 色分け・重要度明確化

### **✅ 最適化されたアラート構成**
| アラート | 状態 | 閾値 | 重要度 | 色 |
|---------|------|------|--------|-----|
| 🗑️ 高レイテンシ | **削除** | ~~3秒~~ | - | - |
| 💰 PnL損失 | 最適化 | **10,000円** | 高 | 🔴 |
| ❌ エラー率 | 最適化 | **10%** | 中 | 🟠 |
| ⚡ 取引失敗 | **新規** | **5回連続** | 最高 | 🔴 |
| 🚨 システム停止 | **新規** | ヘルス失敗 | 高 | 🔴 |
| 📊 メモリ異常 | **新規** | **85%** | 中 | 🟡 |
| 📡 データ停止 | **新規** | **10分** | 高 | 🔴 |

## 📁 ファイル構成

```
monitoring/
├── main.tf          # アラートポリシー・通知チャンネル
├── log_metrics.tf   # 🆕 Google Logging Metrics・time_sleep伝播待機
├── pubsub.tf        # Pub/Subトピック・デッドレター
├── functions.tf     # Cloud Functions・IAM・Secret Manager
├── logging_sink.tf  # BigQueryログシンク（既存）
├── variables.tf     # モジュール変数
└── README.md        # このファイル
```

## 🔧 Input Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `project_id` | string | GCPプロジェクトID | `"my-crypto-bot-project"` |
| `service_name` | string | Cloud Runサービス名 | `"crypto-bot-service-prod"` |
| `discord_webhook_url` | string | Discord Webhook URL（機密） | `"https://discord.com/..."` |

## 🏗️ 作成されるリソース

### **通知システム**
- `google_monitoring_notification_channel.discord` - Discord通知チャンネル
- `google_pubsub_topic.alert_notifications` - アラート配信トピック
- `google_pubsub_topic.alert_deadletter` - デッドレターキュー

### **Cloud Functions**
- `google_cloudfunctions_function.webhook_notifier` - Discord送信Function
- `google_service_account.webhook_notifier` - 実行用サービスアカウント
- `google_storage_bucket.function_source` - ソースコード保存バケット

### **🆕 Google Logging Metrics・伝播待機**
- `google_logging_metric.trade_errors` - 取引エラーログメトリクス
- `google_logging_metric.data_fetch_success` - データ取得成功ログメトリクス  
- `time_sleep.wait_for_metrics_propagation` - 60秒待機システム

### **Secret Manager**
- `google_secret_manager_secret.discord_webhook_url` - WebhookURL保存
- `google_secret_manager_secret_version.discord_webhook_url` - 最新版

### **IAM権限**
- `roles/secretmanager.secretAccessor` - Secret Manager読み取り
- `roles/pubsub.publisher` - Pub/Sub発行権限

### **アラートポリシー（7種類）**
1. **💰 PnL損失** - 10,000円超損失
2. **❌ エラー率** - 10%超システムエラー
3. **⚡ 取引失敗** - 5回連続エントリー失敗
4. **🚨 システム停止** - ヘルスチェック・インスタンス異常
5. **📊 メモリ異常** - 85%超使用率
6. **📡 データ停止** - 10分超取得停止

## 🚀 使用方法

### Terraform設定例
```hcl
module "monitoring" {
  source              = "../../modules/monitoring"
  project_id          = "my-crypto-bot-project"
  service_name        = "crypto-bot-service-prod"
  discord_webhook_url = var.discord_webhook_url  # GitHub Secrets経由
}
```

### 環境変数設定（CI/CD）
```yaml
env:
  TF_VAR_discord_webhook_url: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

## 🧪 テスト・検証

### アラート動作テスト
```bash
# Discord直接テスト
python ../../../scripts/monitoring/discord_notification_test.py --type direct

# 各アラート種別テスト
python ../../../scripts/monitoring/discord_notification_test.py --type loss
python ../../../scripts/monitoring/discord_notification_test.py --type trade_failure
```

### Cloud Functions確認
```bash
# Functions状態確認
gcloud functions describe webhook-notifier --region=asia-northeast1

# ログ確認
gcloud functions logs read webhook-notifier --region=asia-northeast1 --limit=10
```

### Pub/Sub確認
```bash
# トピック確認
gcloud pubsub topics list --filter="name:crypto-bot-alert"

# テストメッセージ送信
gcloud pubsub topics publish crypto-bot-alert-notifications --message='{"test": true}'
```

## ⚠️ トラブルシューティング

### **よくある問題**

**Discord Webhook URL未設定**:
```bash
# GitHub Secrets確認・設定
gh secret list | grep DISCORD_WEBHOOK_URL
gh secret set DISCORD_WEBHOOK_URL --body "https://discord.com/..."
```

**Cloud Functions デプロイエラー**:
```bash
# 手動デプロイ（必要時）
cd ../../functions/webhook_notifier/
gcloud functions deploy webhook-notifier \
  --runtime python311 \
  --trigger-topic crypto-bot-alert-notifications \
  --region asia-northeast1 \
  --memory 128MB
```

**Permission Denied エラー**:
```bash
# Service Account権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members:webhook-notifier@*"
```

**アラート未発火**:
```bash
# アラートポリシー状態確認
gcloud alpha monitoring policies list --project=my-crypto-bot-project

# 条件確認（メトリクス存在）
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod" --limit=3
```

## 📊 モニタリング・維持管理

### **成功指標**
- ✅ **Discord配信率**: 99%以上
- ✅ **Functions応答時間**: 5秒以内
- ✅ **メール通知**: 完全ゼロ
- ✅ **重要度フィルタリング**: 不要アラート排除

### **定期確認項目**
- **月次**: アラート発火頻度・Discord配信状況
- **デプロイ時**: Functions正常動作・通知テスト
- **四半期**: アラート閾値・重要度の見直し

## 🔄 変更履歴

### **v2.0.0 (2025年8月13日) - Discord移行**
- ✅ **Major**: メール通知 → Discord通知完全移行
- ✅ **削除**: 高レイテンシアラート（デプロイ時大量通知原因）
- ✅ **最適化**: PnL損失（10,000円）・エラー率（10%）閾値引き上げ
- ✅ **追加**: 4つの重要アラート（取引失敗・システム停止・メモリ・データ停止）
- ✅ **追加**: Cloud Functions・Pub/Sub・Secret Manager統合

### **v1.x.x (〜2025年8月12日) - メール通知**
- ❌ **削除済**: メール通知システム（`google_monitoring_notification_channel.email`）
- ❌ **削除済**: `alert_email` 変数

## 🔗 関連リソース

### **Terraform設定**
- **メイン環境**: `../../envs/prod/main.tf`
- **CI/CD**: `../../../.github/workflows/ci.yml`

### **Cloud Functions**
- **ソースコード**: `../../functions/webhook_notifier/`
- **デプロイ**: 自動（Terraform管理）

### **テスト・監視**
- **テストスクリプト**: `../../../scripts/monitoring/discord_notification_test.py`
- **稼働監視**: `../../../scripts/operational_status_checker.py`

---

**🎊 Phase 20完成 - Google Logging Metrics伝播待機システム実装完了・CI/CDエラー根絶達成**（2025年8月14日完成）