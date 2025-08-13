# =============================================================================
# Discord通知用 Pub/Sub トピック設定
# =============================================================================

# アラート通知用Pub/Subトピック
resource "google_pubsub_topic" "alert_notifications" {
  name    = "crypto-bot-alert-notifications"
  project = var.project_id

  labels = {
    env     = "production"
    service = "crypto-bot"
    purpose = "discord-alerts"
  }

  depends_on = [var.discord_permissions_ready]  # IAM権限伝播完了まで待機
}

# Cloud Functionsは直接トリガーで受信するため、手動サブスクリプションは不要
# Pub/Subトピックから直接トリガーされる

# デッドレターキュー用トピック
resource "google_pubsub_topic" "alert_deadletter" {
  name    = "crypto-bot-alert-deadletter"
  project = var.project_id

  labels = {
    env     = "production"
    service = "crypto-bot"
    purpose = "deadletter"
  }

  depends_on = [var.discord_permissions_ready]  # IAM権限伝播完了まで待機
}