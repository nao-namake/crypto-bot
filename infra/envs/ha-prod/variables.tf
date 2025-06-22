variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "project_number" {
  description = "GCP project number"
  type        = string
}

variable "primary_region" {
  description = "Primary region for deployment"
  type        = string
  default     = "asia-northeast1"
}

variable "secondary_region" {
  description = "Secondary region for failover"
  type        = string
  default     = "us-central1"
}

variable "enable_secondary_region" {
  description = "Enable deployment to secondary region"
  type        = bool
  default     = true
}

variable "enable_load_balancer" {
  description = "Enable global load balancer"
  type        = bool
  default     = true
}

variable "enable_ssl" {
  description = "Enable SSL/HTTPS"
  type        = bool
  default     = false
}

variable "enable_public_access" {
  description = "Enable public access to Cloud Run services"
  type        = bool
  default     = true
}

variable "enable_uptime_check" {
  description = "Enable uptime checks"
  type        = bool
  default     = true
}

variable "domains" {
  description = "List of domains for SSL certificate"
  type        = list(string)
  default     = []
}

variable "artifact_registry_repo" {
  description = "Artifact Registry repository name"
  type        = string
}

variable "service_name" {
  description = "Cloud Run service name prefix"
  type        = string
}

variable "image_name" {
  description = "Docker image name"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "mode" {
  description = "Running mode (live | paper | backtest)"
  type        = string
  default     = "live"
}

variable "service_account_email" {
  description = "Service account email for Cloud Run"
  type        = string
  default     = null
}

variable "cpu_limit" {
  description = "CPU limit for Cloud Run containers"
  type        = string
  default     = "2000m"
}

variable "memory_limit" {
  description = "Memory limit for Cloud Run containers"
  type        = string
  default     = "1Gi"
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = string
  default     = "2"
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = string
  default     = "20"
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

variable "github_repo" {
  description = "GitHub repository in owner/repo format"
  type        = string
}

variable "deployer_sa" {
  description = "Service account email for GitHub Actions deployment"
  type        = string
  default     = null
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