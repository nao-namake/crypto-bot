variable "project_id"             { type = string }
variable "region"                 { type = string }
variable "artifact_registry_repo" { type = string }
variable "service_name"           { type = string }
variable "image_name"             { type = string }
variable "image_tag"              { type = string }
variable "alert_email"            { type = string }
variable "github_repo" {
  description = "owner/repository 形式の GitHub リポジトリ識別子"
  type        = string
}