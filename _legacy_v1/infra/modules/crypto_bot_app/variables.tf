############################################
# crypto_bot_app / variables.tf
# Cloud Run サービスをデプロイするモジュールの入力変数
############################################

variable "project_id" {
  type        = string
  description = "デプロイ対象の GCP プロジェクト ID"
}

variable "region" {
  type        = string
  description = "Cloud Run / Artifact Registry をデプロイするリージョン (例: asia‑northeast1)"
}

variable "artifact_registry_repo" {
  type        = string
  description = "Docker イメージを格納する Artifact Registry リポジトリ名"
  default     = "crypto-bot-repo"
}

variable "service_name" {
  type        = string
  description = "Cloud Run サービス名 (例: crypto-bot-service)"
}

variable "image_name" {
  type        = string
  description = "イメージ名 (ghcr.io や AR のリポジトリパスを含む)"
}

variable "image_tag" {
  type        = string
  description = "デプロイする Docker イメージのタグ (Git SHA など)"
}

variable "mode" {
  description = "Botコンテナの実行モード (例: \"paper\" または \"prod\")。Cloud Run に環境変数 MODE として渡されます。"
  type        = string
  default     = "Live"
}

# --------------------------------------------------
# Bitbank API credentials (from GitHub Secrets)
# --------------------------------------------------
variable "bitbank_api_key" {
  type        = string
  description = "Bitbank の API キー (GitHub Secrets から渡される)"
  sensitive   = true
  default     = ""  # dev環境（paper mode）では不要なので空でOK
}

variable "bitbank_api_secret" {
  type        = string
  description = "Bitbank の API シークレット (GitHub Secrets から渡される)"
  sensitive   = true
  default     = ""  # dev環境（paper mode）では不要なので空でOK
}

# External API Keys は Phase 3 で完全に削除されたため、設定不要

# 97特徴量固定のため、feature_mode変数は削除

# --------------------------------------------------
# Resource configuration for Cloud Run
# --------------------------------------------------
variable "cpu_limit" {
  type        = string
  description = "CPU limit for Cloud Run service (e.g., '1000m' for 1 CPU)"
  default     = "1000m"
}

variable "memory_limit" {
  type        = string
  description = "Memory limit for Cloud Run service (e.g., '2Gi' for 2GB)"
  default     = "2Gi"
}

variable "cpu_request" {
  type        = string
  description = "Minimum CPU request for Cloud Run service"
  default     = "500m"
}

variable "memory_request" {
  type        = string
  description = "Minimum memory request for Cloud Run service"
  default     = "1Gi"
}

# --------------------------------------------------
# Secret Manager configuration
# --------------------------------------------------
variable "create_secrets" {
  type        = bool
  description = "Whether to create Secret Manager secrets (set to true for first deployment)"
  default     = false
}

variable "project_number" {
  type        = string
  description = "GCP project number (for service account references)"
  default     = ""
}