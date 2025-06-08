# File: infra/monitoring.tf
# Description: 
#   - Cloud Run のリクエストレイテンシーが閾値を超えたときにメール通知を行う
#   - google_monitoring_notification_channel で通知先チャネル（メール）を定義し、
#     google_monitoring_alert_policy でアラートポリシーを紐付けています。

# ──────────────────────────────────────────────────────────────────────────────
# 通知チャネル（メール）定義
# ──────────────────────────────────────────────────────────────────────────────
resource "google_monitoring_notification_channel" "email" {
  display_name = "Crypto-Bot High Latency Email"
  type         = "email"
  labels = {
    email_address = "s00198532@gmail.com"  # ← 実際に通知を受け取りたいメールアドレスに置き換えてください
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# アラートポリシー定義
# ──────────────────────────────────────────────────────────────────────────────
resource "google_monitoring_alert_policy" "high_latency" {
  display_name          = "High request latency"
  combiner              = "OR"
  notification_channels = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Latency > 1s"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\""
      threshold_value = 1.0
      comparison      = "COMPARISON_GT"
      duration        = "60s"
    }
  }
}