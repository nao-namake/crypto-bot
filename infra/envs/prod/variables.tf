variable "project_id"             { type = string }
variable "region"                 { type = string }
variable "artifact_registry_repo" { 
  type    = string
  default = "crypto-bot-repo"
}
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
# ────────────────────────────────────────────
# Workload-Identity / デプロイ共通
# ────────────────────────────────────────────
variable "project_number" {
  description = "GCP プロジェクトの数値 ID"
  type        = string
}

variable "deployer_sa" {
  description = "GitHub Actions が Impersonate するデプロイ用 Service Account"
  type        = string
}

# Cloud Run へ渡す実行モード（paper / live など）
variable "mode" {
  description = "Bot の実行モード: paper | live"
  type        = string
  default     = "live"  # ← Bitbank実トレードモードに変更
}

# Bitbank API credentials (from GitHub Secrets)
variable "bitbank_api_key" {
  type        = string
  description = "Bitbank の API キー (GitHub Secrets から渡される)"
  sensitive   = true
}

variable "bitbank_api_secret" {
  type        = string
  description = "Bitbank の API シークレット (GitHub Secrets から渡される)"
  sensitive   = true
}

# External API Keys は Phase 3 で完全に削除されたため、設定不要

# 97特徴量固定のため、feature_mode変数は削除

# --------------------------------------------------
# Resource configuration for production environment
# --------------------------------------------------
variable "cpu_limit" {
  type        = string
  description = "CPU limit for production environment"
  default     = "1000m"  # 本番環境 1.0 CPU
}

variable "memory_limit" {
  type        = string
  description = "Memory limit for production environment"
  default     = "2Gi"  # 本番環境 2GB RAM
}

variable "cpu_request" {
  type        = string
  description = "Minimum CPU for production environment"
  default     = "500m"  # 最小要求 0.5 CPU
}

variable "memory_request" {
  type        = string
  description = "Minimum memory for production environment"
  default     = "1Gi"  # 最小要求 1GB RAM
}