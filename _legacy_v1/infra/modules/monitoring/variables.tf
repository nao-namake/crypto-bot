variable "project_id"  { type = string }
variable "service_name" { type = string }
variable "discord_webhook_url" { 
  type        = string
  description = "Discord Webhook URL for alert notifications"
  sensitive   = true
}
variable "discord_permissions_ready" {
  type        = string
  description = "IAM権限伝播完了を示すマーカー（workload_identity moduleから取得）"
}
