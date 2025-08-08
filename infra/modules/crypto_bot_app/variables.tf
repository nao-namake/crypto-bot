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
}

variable "bitbank_api_secret" {
  type        = string
  description = "Bitbank の API シークレット (GitHub Secrets から渡される)"
  sensitive   = true
}

# --------------------------------------------------
# External API Keys (Phase H.22)
# --------------------------------------------------
variable "alpha_vantage_api_key" {
  type        = string
  description = "Alpha Vantage API キー (VIXデータ取得用)"
  sensitive   = true
  default     = ""
}

variable "polygon_api_key" {
  type        = string
  description = "Polygon.io API キー (市場データ取得用)"
  sensitive   = true
  default     = ""
}

variable "fred_api_key" {
  type        = string
  description = "FRED API キー (経済指標取得用)"
  sensitive   = true
  default     = ""
}

# --------------------------------------------------
# Feature Mode (lite/full) for system optimization  
# --------------------------------------------------
variable "feature_mode" {
  type        = string
  description = "特徴量モード: lite (3特徴量・高速) または full (126特徴量・完全版)"
  default     = "lite"
  validation {
    condition     = contains(["lite", "full"], var.feature_mode)
    error_message = "feature_mode must be either 'lite' or 'full'."
  }
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