output "enabled_services" {
  description = "List of enabled API services"
  # map → list に変換して service 属性を抜き出す
  value       = [for s in values(google_project_service.enabled) : s.service]
}