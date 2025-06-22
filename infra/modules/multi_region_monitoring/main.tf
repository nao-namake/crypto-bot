############################################
# infra/modules/multi_region_monitoring/main.tf
# Multi-region monitoring and alerting
############################################

# Notification channels
resource "google_monitoring_notification_channel" "email" {
  count        = length(var.alert_emails)
  display_name = "Email Alert - ${var.alert_emails[count.index]}"
  type         = "email"
  project      = var.project_id

  labels = {
    email_address = var.alert_emails[count.index]
  }
}

resource "google_monitoring_notification_channel" "slack" {
  count        = var.slack_webhook_url != "" ? 1 : 0
  display_name = "Slack Alert"
  type         = "slack"
  project      = var.project_id

  labels = {
    url = var.slack_webhook_url
  }

  sensitive_labels {
    auth_token = var.slack_auth_token
  }
}

# Primary region health check alert
resource "google_monitoring_alert_policy" "primary_health" {
  display_name = "Primary Region Health Check Failure"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Primary region health check failure"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.primary_service_name}\" AND resource.labels.location=\"${var.primary_region}\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.5
      duration        = "300s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = concat(
    google_monitoring_notification_channel.email[*].id,
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "86400s"  # 24 hours
  }
}

# Secondary region health check alert (if enabled)
resource "google_monitoring_alert_policy" "secondary_health" {
  count        = var.enable_secondary_region ? 1 : 0
  display_name = "Secondary Region Health Check Failure"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Secondary region health check failure"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.secondary_service_name}\" AND resource.labels.location=\"${var.secondary_region}\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.5
      duration        = "300s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = concat(
    google_monitoring_notification_channel.email[*].id,
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "86400s"
  }
}

# High latency alert
resource "google_monitoring_alert_policy" "high_latency" {
  display_name = "High Request Latency"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Request latency above threshold"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = var.latency_threshold_ms
      duration        = "300s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
        group_by_fields = [
          "resource.labels.service_name",
          "resource.labels.location"
        ]
      }
    }
  }

  notification_channels = concat(
    google_monitoring_notification_channel.email[*].id,
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "3600s"  # 1 hour
  }
}

# High error rate alert
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Error rate above threshold"

    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class!=\"2xx\""
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = var.error_rate_threshold
      duration        = "300s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields = [
          "resource.labels.service_name",
          "resource.labels.location"
        ]
      }
    }
  }

  notification_channels = concat(
    google_monitoring_notification_channel.email[*].id,
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "3600s"
  }
}

# Trading performance alert (PnL monitoring)
resource "google_monitoring_alert_policy" "trading_loss" {
  display_name = "Trading Loss Alert"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Trading loss exceeds threshold"

    condition_threshold {
      filter          = "resource.type=\"global\" AND metric.type=\"custom.googleapis.com/crypto_bot/pnl\""
      comparison      = "COMPARISON_LESS_THAN"
      threshold_value = var.loss_threshold
      duration        = "3600s"  # 1 hour

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = concat(
    google_monitoring_notification_channel.email[*].id,
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "86400s"
  }
}

# Dashboard for multi-region monitoring
resource "google_monitoring_dashboard" "multi_region" {
  dashboard_json = jsonencode({
    displayName = "Crypto Bot Multi-Region Dashboard"
    mosaicLayout = {
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "Primary Region Request Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.primary_service_name}\" AND resource.labels.location=\"${var.primary_region}\" AND metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Requests/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          xPos   = 6
          widget = {
            title = "Secondary Region Request Count"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${var.secondary_service_name}\" AND resource.labels.location=\"${var.secondary_region}\" AND metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Requests/sec"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 12
          height = 4
          yPos   = 4
          widget = {
            title = "Request Latency by Region"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod    = "60s"
                        perSeriesAligner   = "ALIGN_DELTA"
                        crossSeriesReducer = "REDUCE_PERCENTILE_95"
                        groupByFields      = ["resource.labels.location"]
                      }
                    }
                  }
                  plotType = "LINE"
                }
              ]
              yAxis = {
                label = "Latency (ms)"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          yPos   = 8
          widget = {
            title = "Trading PnL"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"global\" AND metric.type=\"custom.googleapis.com/crypto_bot/pnl\""
                    aggregation = {
                      alignmentPeriod  = "300s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "PnL"
                scale = "LINEAR"
              }
            }
          }
        },
        {
          width  = 6
          height = 4
          xPos   = 6
          yPos   = 8
          widget = {
            title = "Trade Count by Region"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"global\" AND metric.type=\"custom.googleapis.com/crypto_bot/trade_count\""
                    aggregation = {
                      alignmentPeriod  = "300s"
                      perSeriesAligner = "ALIGN_MEAN"
                    }
                  }
                }
                plotType = "LINE"
              }]
              yAxis = {
                label = "Trade Count"
                scale = "LINEAR"
              }
            }
          }
        }
      ]
    }
  })
}

# Uptime check for load balancer
resource "google_monitoring_uptime_check_config" "load_balancer" {
  count        = var.enable_uptime_check && var.load_balancer_ip != "" ? 1 : 0
  display_name = "Crypto Bot Load Balancer Uptime"
  project      = var.project_id

  timeout = "10s"
  period  = "60s"

  http_check {
    path         = "/healthz"
    port         = "80"
    use_ssl      = false
    validate_ssl = false
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      host       = var.load_balancer_ip
      project_id = var.project_id
    }
  }

  checker_type = "STATIC_IP_CHECKERS"
}

# Uptime check alert
resource "google_monitoring_alert_policy" "uptime_failure" {
  count        = var.enable_uptime_check && var.load_balancer_ip != "" ? 1 : 0
  display_name = "Load Balancer Uptime Check Failure"
  project      = var.project_id
  combiner     = "OR"

  conditions {
    display_name = "Uptime check failure"

    condition_threshold {
      filter          = "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\""
      comparison      = "COMPARISON_LESS_THAN"
      threshold_value = 1.0
      duration        = "300s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
      }
    }
  }

  notification_channels = concat(
    google_monitoring_notification_channel.email[*].id,
    var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  )

  alert_strategy {
    auto_close = "3600s"
  }
}