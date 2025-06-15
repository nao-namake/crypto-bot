resource "google_monitoring_notification_channel" "email" {
  project      = var.project_id
  display_name = "Crypto-Bot Alert Email"
  type         = "email"
  labels       = { email_address = var.alert_email }
}

resource "google_monitoring_alert_policy" "latency" {
  project                = var.project_id
  display_name           = "High request latency"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "Latency > 1s"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "60s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_99"
      }
    }
  }
}
