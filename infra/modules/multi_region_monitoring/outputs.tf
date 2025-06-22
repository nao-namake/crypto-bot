############################################
# infra/modules/multi_region_monitoring/outputs.tf
# Outputs for multi-region monitoring
############################################

output "dashboard_url" {
  description = "URL of the monitoring dashboard"
  value       = "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.multi_region.id}?project=${var.project_id}"
}

output "notification_channels" {
  description = "Notification channel IDs"
  value = {
    email = google_monitoring_notification_channel.email[*].id
    slack = var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
  }
}

output "alert_policies" {
  description = "Alert policy names"
  value = {
    primary_health    = google_monitoring_alert_policy.primary_health.display_name
    secondary_health  = var.enable_secondary_region ? google_monitoring_alert_policy.secondary_health[0].display_name : null
    high_latency      = google_monitoring_alert_policy.high_latency.display_name
    high_error_rate   = google_monitoring_alert_policy.high_error_rate.display_name
    trading_loss      = google_monitoring_alert_policy.trading_loss.display_name
    uptime_failure    = var.enable_uptime_check && var.load_balancer_ip != "" ? google_monitoring_alert_policy.uptime_failure[0].display_name : null
  }
}

output "uptime_check_id" {
  description = "Uptime check configuration ID"
  value       = var.enable_uptime_check && var.load_balancer_ip != "" ? google_monitoring_uptime_check_config.load_balancer[0].uptime_check_id : null
}