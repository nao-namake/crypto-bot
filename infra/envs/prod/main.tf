terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "services" {
  source     = "../../modules/project_services"
  project_id = var.project_id
  project_number = var.project_number
}

module "app" {
  source                 = "../../modules/crypto_bot_app"
  project_id             = var.project_id
  region                 = var.region
  artifact_registry_repo = var.artifact_registry_repo
  service_name           = var.service_name
  image_name             = var.image_name
  image_tag              = var.image_tag
  mode                   = var.mode
  mode                 = var.mode
}

module "monitoring" {
  source      = "../../modules/monitoring"
  project_id  = var.project_id
  alert_email = var.alert_email
}

module "wif" {
  source         = "../../modules/workload_identity"
  project_id     = var.project_id
  project_number = var.project_number
  github_repo    = var.github_repo
  deployer_sa    = var.deployer_sa
}
