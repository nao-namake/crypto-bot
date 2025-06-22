############################################
# infra/modules/multi_region_app/outputs.tf
# Outputs for multi-region HA deployment
############################################

output "primary_service_url" {
  description = "URL of the primary Cloud Run service"
  value       = google_cloud_run_service.primary.status[0].url
}

output "secondary_service_url" {
  description = "URL of the secondary Cloud Run service"
  value       = var.enable_secondary_region ? google_cloud_run_service.secondary[0].status[0].url : null
}

output "load_balancer_ip" {
  description = "Global load balancer IP address"
  value       = var.enable_load_balancer ? google_compute_global_address.lb_ip[0].address : null
}

output "primary_service_name" {
  description = "Name of the primary Cloud Run service"
  value       = google_cloud_run_service.primary.name
}

output "secondary_service_name" {
  description = "Name of the secondary Cloud Run service"
  value       = var.enable_secondary_region ? google_cloud_run_service.secondary[0].name : null
}

output "artifact_registry_repo_url" {
  description = "Artifact Registry repository URL"
  value       = "${var.primary_region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
}

output "health_check_url" {
  description = "Health check URL"
  value       = "/healthz"
}

output "regions" {
  description = "Deployed regions"
  value = {
    primary   = var.primary_region
    secondary = var.enable_secondary_region ? var.secondary_region : null
  }
}