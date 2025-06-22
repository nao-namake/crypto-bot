############################################
# infra/modules/multi_region_monitoring/variables.tf
# Variables for multi-region monitoring
############################################

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "alert_emails" {
  description = "List of email addresses for alerts"
  type        = list(string)
  default     = []
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for notifications"
  type        = string
  default     = ""
}

variable "slack_auth_token" {
  description = "Slack auth token"
  type        = string
  default     = ""
  sensitive   = true
}

variable "primary_service_name" {
  description = "Primary Cloud Run service name"
  type        = string
}

variable "secondary_service_name" {
  description = "Secondary Cloud Run service name"
  type        = string
  default     = ""
}

variable "primary_region" {
  description = "Primary region"
  type        = string
}

variable "secondary_region" {
  description = "Secondary region"
  type        = string
  default     = ""
}

variable "enable_secondary_region" {
  description = "Enable secondary region monitoring"
  type        = bool
  default     = false
}

variable "enable_uptime_check" {
  description = "Enable uptime checks"
  type        = bool
  default     = true
}

variable "load_balancer_ip" {
  description = "Load balancer IP address"
  type        = string
  default     = ""
}

variable "latency_threshold_ms" {
  description = "Latency threshold in milliseconds"
  type        = number
  default     = 3000
}

variable "error_rate_threshold" {
  description = "Error rate threshold (requests per second)"
  type        = number
  default     = 1.0
}

variable "loss_threshold" {
  description = "Trading loss threshold"
  type        = number
  default     = -5000
}