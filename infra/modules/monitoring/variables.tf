variable "project_id"  { type = string }
variable "service_name" { type = string }
variable "discord_webhook_url" { 
  type        = string
  description = "Discord Webhook URL for alert notifications"
  sensitive   = true
}
