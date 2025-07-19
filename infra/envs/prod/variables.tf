variable "project_id"             { type = string }
variable "region"                 { type = string }
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