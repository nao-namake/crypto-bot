# infra/envs/k8s-gke/main.tf
# GKE environment configuration for crypto-bot

terraform {
  required_version = ">= 1.0"
  
  backend "gcs" {
    bucket = "crypto-bot-terraform-state"
    prefix = "k8s-gke"
  }
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# GKE Cluster
module "gke" {
  source = "../../modules/gke"

  project_id   = var.project_id
  region       = var.region
  cluster_name = "${var.environment}-crypto-bot-gke"

  # Network configuration
  subnet_cidr  = var.subnet_cidr
  pods_cidr    = var.pods_cidr
  services_cidr = var.services_cidr

  # Cluster configuration
  release_channel            = var.release_channel
  enable_binary_authorization = var.enable_binary_authorization

  # Node configuration
  node_count     = var.node_count
  min_node_count = var.min_node_count
  max_node_count = var.max_node_count
  machine_type   = var.machine_type
  disk_size_gb   = var.disk_size_gb
  disk_type      = var.disk_type
  preemptible    = var.preemptible

  # Spot nodes
  enable_spot_nodes    = var.enable_spot_nodes
  spot_min_node_count  = var.spot_min_node_count
  spot_max_node_count  = var.spot_max_node_count
  spot_machine_type    = var.spot_machine_type

  # Security
  authorized_networks = var.authorized_networks

  # Crypto-bot specific
  crypto_bot_namespace = var.crypto_bot_namespace
  crypto_bot_ksa_name  = var.crypto_bot_ksa_name
  crypto_bot_iam_roles = var.crypto_bot_iam_roles

  # Labels
  cluster_labels = merge(var.common_labels, {
    environment = var.environment
    purpose     = "crypto-trading-bot"
  })

  node_labels = merge(var.node_labels, {
    environment = var.environment
  })

  depends_on = [google_project_service.required_apis]
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "crypto_bot" {
  repository_id = "crypto-bot"
  location      = var.region
  format        = "DOCKER"
  description   = "Container registry for crypto-bot application"

  labels = var.common_labels
}

# Static IP for ingress
resource "google_compute_global_address" "crypto_bot_ip" {
  name        = "${var.environment}-crypto-bot-ip"
  description = "Static IP for crypto-bot ingress"
  project     = var.project_id
}

# Secrets in Secret Manager
resource "google_secret_manager_secret" "bybit_testnet_api_key" {
  secret_id = "crypto-bot-bybit-testnet-api-key"
  project   = var.project_id

  replication {
    automatic = true
  }

  labels = var.common_labels
}

resource "google_secret_manager_secret" "bybit_testnet_api_secret" {
  secret_id = "crypto-bot-bybit-testnet-api-secret"
  project   = var.project_id

  replication {
    automatic = true
  }

  labels = var.common_labels
}