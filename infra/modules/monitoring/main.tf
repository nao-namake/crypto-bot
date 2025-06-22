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
    display_name = "Latency > 3s"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 3
      duration        = "180s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_99"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "pnl_loss" {
  project                = var.project_id
  display_name           = "Crypto Bot Loss Alert"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "PnL < -5000 JPY"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/crypto_bot/pnl\" resource.type=\"global\""
      comparison      = "COMPARISON_LT"
      threshold_value = -5000
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
}

resource "google_monitoring_alert_policy" "error_rate" {
  project                = var.project_id
  display_name           = "High error rate"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.email.id]

  conditions {
    display_name = "5xx error rate > 5%"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.label.response_code_class=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
}
