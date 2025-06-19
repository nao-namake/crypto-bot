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

# Workload Identity Federation 用
variable "project_number" {
  description = "GCP プロジェクトの数値 ID (principalSet 生成に使用)"
  type        = string
}

variable "deployer_sa" {
  description = "GitHub Actions が偽装するサービスアカウント (email)"
  type        = string
}

# Cloud Run へ渡す Bot 実行モード (paper / live など)
variable "mode" {
  description = "Bot running mode (paper | live)"
  type        = string
  default     = "paper"
}