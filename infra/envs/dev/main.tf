terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      # 5 系なら 5.0 以上 6.0 未満で許可（推奨）
      version = ">= 5.0.0, < 6.0.0"
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
  bitbank_api_key        = var.bitbank_api_key
  bitbank_api_secret     = var.bitbank_api_secret
  feature_mode           = var.feature_mode
  cpu_limit              = var.cpu_limit
  memory_limit           = var.memory_limit
  cpu_request            = var.cpu_request
  memory_request         = var.memory_request
}

module "monitoring" {
  source       = "../../modules/monitoring"
  project_id   = var.project_id
  alert_email  = var.alert_email
  service_name = var.service_name
}

module "wif" {
  source         = "../../modules/workload_identity"
  project_id     = var.project_id
  project_number = var.project_number
  github_repo    = var.github_repo
  deployer_sa    = var.deployer_sa
}
