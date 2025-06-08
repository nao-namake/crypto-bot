# =============================================================================
# ファイル名: infra/variables.tf
# 説明:
#   - Terraform 実行時に指定する変数を定義
#   - GCP プロジェクトやリージョン、リポジトリ名、サービス名、イメージ情報など
# =============================================================================

variable "project_id" {
  description = "GCP プロジェクト ID"
  type        = string
}

variable "region" {
  description = "GCP リージョン（例: asia-northeast1）"
  type        = string
  default     = "asia-northeast1"
}

variable "artifact_registry_repo" {
  description = "Artifact Registry のリポジトリ名"
  type        = string
  default     = "crypto-bot-repo"
}

variable "service_name" {
  description = "Cloud Run サービス名"
  type        = string
  default     = "crypto-bot-service"
}

variable "image_name" {
  description = "ビルドした Docker イメージ名"
  type        = string
  default     = "crypto-bot"
}

variable "image_tag" {
  description = "プッシュする Docker イメージのタグ"
  type        = string
  default     = "latest"
}