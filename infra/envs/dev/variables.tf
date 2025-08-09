variable "project_id"             { type = string }
variable "region"                 { type = string }
variable "artifact_registry_repo" { type = string }
variable "service_name"           { type = string }
variable "image_name"             { type = string }
variable "image_tag" {
  description = "Docker image tag to deploy. Defaults to \"latest\" so you can omit it in *.tfvars when you just want the newest image."
  type        = string
  default     = "latest"
}
variable "alert_email"            { type = string }
variable "github_repo" {
  description = "owner/repository 形式の GitHub リポジトリ識別子"
  type        = string
}

variable "project_number" {
  description = "GCP project number (used for Workload Identity Federation)"
  type        = string
}

variable "deployer_sa" {
  description = "Service account email for GitHub Actions deployment"
  type        = string
  default     = null
}

variable "mode" {
  description = "Running mode for Cloud Run container (live | paper | backtest)"
  type    = string
  default = "paper" # dev 環境の既定値
}

# Bitbank API credentials (optional for paper mode)
variable "bitbank_api_key" {
  type        = string
  description = "Bitbank API key (not required for paper mode)"
  sensitive   = true
  default     = ""
}

variable "bitbank_api_secret" {
  type        = string
  description = "Bitbank API secret (not required for paper mode)"
  sensitive   = true
  default     = ""
}

# --------------------------------------------------
# Feature Mode (lite/full) for system optimization  
# --------------------------------------------------
variable "feature_mode" {
  type        = string
  description = "特徴量モード: lite (3特徴量・高速) または full (97特徴量・完全版)"
  default     = "lite"
  validation {
    condition     = contains(["lite", "full"], var.feature_mode)
    error_message = "feature_mode must be either 'lite' or 'full'."
  }
}

# --------------------------------------------------
# Resource configuration for development environment
# --------------------------------------------------
variable "cpu_limit" {
  type        = string
  description = "CPU limit for dev environment"
  default     = "250m"  # 最小構成 0.25 CPU
}

variable "memory_limit" {
  type        = string
  description = "Memory limit for dev environment"
  default     = "512Mi"  # 最小構成 512MB
}

variable "cpu_request" {
  type        = string
  description = "Minimum CPU for dev environment"
  default     = "100m"  # 最小要求 0.1 CPU
}

variable "memory_request" {
  type        = string
  description = "Minimum memory for dev environment"
  default     = "256Mi"  # 最小要求 256MB
}
