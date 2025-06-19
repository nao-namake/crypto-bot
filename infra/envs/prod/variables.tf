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
  default     = "paper"  # ← prod でもまずは paper で安全に稼働
}