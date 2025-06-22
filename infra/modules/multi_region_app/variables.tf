############################################
# infra/modules/multi_region_app/variables.tf
# Variables for multi-region HA deployment
############################################

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
  default     = "paper"
}

variable "service_account_email" {
  description = "Service account email for Cloud Run"
  type        = string
  default     = null
}

variable "bybit_testnet_api_key_secret_name" {
  description = "Secret name for Bybit Testnet API key"
  type        = string
  default     = "bybit_testnet_api_key"
}

variable "bybit_testnet_api_secret_secret_name" {
  description = "Secret name for Bybit Testnet API secret"
  type        = string
  default     = "bybit_testnet_api_secret"
}

variable "cpu_limit" {
  description = "CPU limit for Cloud Run containers"
  type        = string
  default     = "1000m"
}

variable "memory_limit" {
  description = "Memory limit for Cloud Run containers"
  type        = string
  default     = "512Mi"
}

variable "min_instances" {
  description = "Minimum number of instances"
  type        = string
  default     = "1"
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = string
  default     = "10"
}