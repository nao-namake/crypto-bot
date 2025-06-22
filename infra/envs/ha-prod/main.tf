terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0, < 6.0.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.primary_region
}

module "services" {
  source         = "../../modules/project_services"
  project_id     = var.project_id
  project_number = var.project_number
}

module "multi_region_app" {
  source                 = "../../modules/multi_region_app"
  project_id             = var.project_id
  project_number         = var.project_number
  primary_region         = var.primary_region
  secondary_region       = var.secondary_region
  enable_secondary_region = var.enable_secondary_region
  enable_load_balancer   = var.enable_load_balancer
  enable_ssl             = var.enable_ssl
  enable_public_access   = var.enable_public_access
  domains                = var.domains
  artifact_registry_repo = var.artifact_registry_repo
  service_name           = var.service_name
  image_name             = var.image_name
  image_tag              = var.image_tag
  mode                   = var.mode
  service_account_email  = var.service_account_email
  cpu_limit              = var.cpu_limit
  memory_limit           = var.memory_limit
  min_instances          = var.min_instances
  max_instances          = var.max_instances

  depends_on = [module.services]
}

module "multi_region_monitoring" {
  source                  = "../../modules/multi_region_monitoring"
  project_id              = var.project_id
  alert_emails            = var.alert_emails
  slack_webhook_url       = var.slack_webhook_url
  slack_auth_token        = var.slack_auth_token
  primary_service_name    = module.multi_region_app.primary_service_name
  secondary_service_name  = module.multi_region_app.secondary_service_name
  primary_region          = var.primary_region
  secondary_region        = var.secondary_region
  enable_secondary_region = var.enable_secondary_region
  enable_uptime_check     = var.enable_uptime_check
  load_balancer_ip        = module.multi_region_app.load_balancer_ip
  latency_threshold_ms    = var.latency_threshold_ms
  error_rate_threshold    = var.error_rate_threshold
  loss_threshold          = var.loss_threshold

  depends_on = [module.multi_region_app]
}

module "wif" {
  source         = "../../modules/workload_identity"
  project_id     = var.project_id
  project_number = var.project_number
  github_repo    = var.github_repo
  deployer_sa    = var.deployer_sa
}