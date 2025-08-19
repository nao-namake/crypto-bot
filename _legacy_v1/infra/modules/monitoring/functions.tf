# =============================================================================
# Discord通知用 Cloud Functions 設定
# =============================================================================

# Cloud Functions用Service Account
resource "google_service_account" "webhook_notifier" {
  account_id   = "webhook-notifier"
  display_name = "Discord Webhook Notifier Service Account"
  description  = "Service account for Discord webhook notification function"
  project      = var.project_id

  depends_on = [var.discord_permissions_ready]  # IAM権限伝播完了まで待機
}

# Service AccountにSecret Manager読み取り権限を付与
resource "google_project_iam_member" "webhook_notifier_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.webhook_notifier.email}"
}

# Service AccountにPub/Sub Publisher権限を付与
resource "google_project_iam_member" "webhook_notifier_pubsub" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.webhook_notifier.email}"
}

# Cloud Functions用Storageバケット
resource "google_storage_bucket" "function_source" {
  name     = "${var.project_id}-webhook-notifier-source"
  location = "asia-northeast1"
  project  = var.project_id

  uniform_bucket_level_access = true
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    env     = "production"
    service = "crypto-bot"
    purpose = "cloud-functions"
  }

  depends_on = [var.discord_permissions_ready]  # IAM権限伝播完了まで待機
}

# ソースコードをZipファイルとして作成
data "archive_file" "webhook_notifier_source" {
  type        = "zip"
  output_path = "/tmp/webhook_notifier_source.zip"
  source_dir  = "${path.module}/../../functions/webhook_notifier"
}

# Zipファイルをストレージにアップロード
resource "google_storage_bucket_object" "webhook_notifier_source" {
  name   = "webhook_notifier_source_${data.archive_file.webhook_notifier_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.webhook_notifier_source.output_path

  depends_on = [data.archive_file.webhook_notifier_source]
}

# Discord Webhook URL用Secret Manager
resource "google_secret_manager_secret" "discord_webhook_url" {
  secret_id = "discord-webhook-url"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    env     = "production"
    service = "crypto-bot"
    purpose = "discord-webhook"
  }
}

# Secret Managerにバージョンを作成（値は環境変数から取得）
resource "google_secret_manager_secret_version" "discord_webhook_url" {
  secret      = google_secret_manager_secret.discord_webhook_url.id
  secret_data = var.discord_webhook_url

  lifecycle {
    ignore_changes = [secret_data]
  }
}

# Cloud Functions (Gen 1) 定義
resource "google_cloudfunctions_function" "webhook_notifier" {
  name    = "webhook-notifier"
  project = var.project_id
  region  = "asia-northeast1"

  available_memory_mb   = 128
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.webhook_notifier_source.name
  entry_point          = "webhook_notifier"
  runtime               = "python311"
  timeout               = 60
  service_account_email = google_service_account.webhook_notifier.email

  # Pub/Sub トリガー
  event_trigger {
    event_type = "providers/cloud.pubsub/eventTypes/topic.publish"
    resource   = google_pubsub_topic.alert_notifications.name
    
    failure_policy {
      retry = true
    }
  }

  # 環境変数
  environment_variables = {
    GCP_PROJECT            = var.project_id
    DISCORD_WEBHOOK_URL    = var.discord_webhook_url
  }

  labels = {
    env     = "production"
    service = "crypto-bot"
    purpose = "discord-alerts"
  }

  depends_on = [
    google_storage_bucket_object.webhook_notifier_source,
    google_project_iam_member.webhook_notifier_secret_accessor,
    google_project_iam_member.webhook_notifier_pubsub
  ]
}