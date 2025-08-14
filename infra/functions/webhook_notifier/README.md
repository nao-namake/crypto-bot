# Discord Webhook Notifier Cloud Functions

Discord通知システム用のCloud Functionsコードです。GCP Cloud MonitoringのアラートをDiscordチャンネルに送信します。

## 📋 概要

**目的**: GCPアラートのメール通知を廃止し、Discord通知に完全移行（Phase 20: Google Logging Metrics対応済み）  
**トリガー**: Pub/Sub `crypto-bot-alert-notifications` トピック  
**実行時間**: 平均2-5秒、タイムアウト60秒  
**メモリ**: 128MB（軽量実装）

## 📁 ファイル構成

```
webhook_notifier/
├── main.py           # メイン処理（Discord送信ロジック）
├── requirements.txt  # Python依存関係
└── README.md        # このファイル
```

## 🚀 主要機能

### 1. **アラート種別対応**
- 💰 **PnL損失アラート**: 10,000円以上の損失（赤色）
- ❌ **エラー率アラート**: 10%以上のシステムエラー（オレンジ）
- ⚡ **取引実行失敗**: 5回連続エントリー失敗（赤色・最重要）
- 🚨 **システム停止**: ヘルスチェック失敗（赤色）
- 📊 **メモリ異常**: 85%超使用率（黄色）
- 📡 **データ取得停止**: 10分超取得停止（赤色）

### 2. **Discord埋め込み形式**
- **色分け表示**: アラート重要度に応じた視覚的分類
- **JST時刻統一**: 日本時間での統一表示
- **構造化情報**: ポリシー名・状態・詳細をフィールド分け
- **回復通知**: アラート解決時の緑色通知

## 🔧 環境設定

### 必要な環境変数
```bash
GCP_PROJECT=my-crypto-bot-project           # GCPプロジェクトID
DISCORD_WEBHOOK_URL=https://discord.com/... # Discord Webhook URL（Secret Manager経由）
```

### 必要な権限
Cloud Functions実行用のService Account `webhook-notifier` に以下の権限が付与されています：
- `roles/secretmanager.secretAccessor` - Discord Webhook URL取得
- `roles/pubsub.publisher` - Pub/Sub操作（必要時）

## 📨 メッセージ形式

### Discord埋め込みメッセージ例
```json
{
  "embeds": [{
    "title": "🤖 Crypto-Bot Alert: PnL < -10000 JPY",
    "description": "💰 **損失アラート**: 取引で大きな損失が発生しています",
    "color": 16711680,  // 赤色
    "fields": [
      {"name": "📊 ポリシー", "value": "Crypto Bot Loss Alert"},
      {"name": "🚨 状態", "value": "🔴 OPEN"},
      {"name": "⏰ 検出時刻", "value": "2025年8月13日 15:30:45 JST"}
    ]
  }]
}
```

## 🧪 テスト方法

### ローカルテスト
```bash
# Discord直接テスト
python ../../scripts/monitoring/discord_notification_test.py --type direct

# 特定アラートテスト
python ../../scripts/monitoring/discord_notification_test.py --type loss
python ../../scripts/monitoring/discord_notification_test.py --type trade_failure
```

### GCP環境での確認
```bash
# Cloud Functions ログ確認
gcloud functions logs read webhook-notifier --region=asia-northeast1 --limit=10

# Functions状態確認
gcloud functions describe webhook-notifier --region=asia-northeast1
```

## 🔄 デプロイフロー

1. **自動デプロイ**: `git push origin main` でCI/CD自動実行
2. **Terraformプロビジョニング**: 
   - Cloud Functions作成
   - Service Account・権限設定
   - Pub/Subトピック連携
3. **初回デプロイ時間**: 約5-10分

## ⚠️ トラブルシューティング

### よくある問題

**Discord Webhook URL未設定**:
```bash
# GitHub Secretsの確認
gh secret list | grep DISCORD_WEBHOOK_URL

# 設定（必要時）
gh secret set DISCORD_WEBHOOK_URL --body "https://discord.com/..."
```

**Permission Denied エラー**:
```bash
# Service Account権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:webhook-notifier@*"
```

**Pub/Sub接続エラー**:
```bash
# トピック存在確認
gcloud pubsub topics list --filter="name:crypto-bot-alert-notifications"

# テストメッセージ送信
gcloud pubsub topics publish crypto-bot-alert-notifications --message="test"
```

## 📊 モニタリング

### 成功指標
- ✅ **応答時間**: 平均2-5秒以内
- ✅ **成功率**: 99%以上
- ✅ **Discord配信**: 204レスポンス
- ✅ **エラー率**: 1%未満

### 監視コマンド
```bash
# 実行統計
gcloud functions call webhook-notifier --region=asia-northeast1 --data='{}'

# メトリクス確認
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=webhook-notifier" --limit=5
```

## 🔗 関連ファイル

- **Terraform設定**: `../modules/monitoring/functions.tf`
- **アラートポリシー**: `../modules/monitoring/main.tf`  
- **テストスクリプト**: `../../scripts/monitoring/discord_notification_test.py`
- **CI/CD設定**: `../../.github/workflows/ci.yml`

---

**🎊 Phase 20完成 - Google Logging Metrics伝播待機システム対応・Discord通知システムが私生活への影響を完全排除**（2025年8月14日）