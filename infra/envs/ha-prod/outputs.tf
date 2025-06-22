output "primary_service_url" {
  description = "URL of the primary Cloud Run service"
  value       = module.multi_region_app.primary_service_url
}

output "secondary_service_url" {
  description = "URL of the secondary Cloud Run service"
  value       = module.multi_region_app.secondary_service_url
}

output "load_balancer_ip" {
  description = "Global load balancer IP address"
  value       = module.multi_region_app.load_balancer_ip
}

output "dashboard_url" {
  description = "URL of the monitoring dashboard"
  value       = module.multi_region_monitoring.dashboard_url
}

output "regions" {
  description = "Deployed regions"
  value       = module.multi_region_app.regions
}

output "artifact_registry_repo_url" {
  description = "Artifact Registry repository URL"
  value       = module.multi_region_app.artifact_registry_repo_url
}