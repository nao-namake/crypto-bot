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
