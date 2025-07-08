############################################
# infra/modules/crypto_bot_app/main.tf
# Cloud Run service + Artifact Registry remote repo for GHCR
############################################

# Artifact Registry リポジトリを参照（既存のものを使用）
data "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo
}

# Cloud Run service（作成）
resource "google_cloud_run_service" "service" {
  name     = var.service_name
  location = var.region
  project  = var.project_id

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"
        
        env {
          name  = "MODE"
          value = var.mode
        }
        
        env {
          name = "BYBIT_TESTNET_API_KEY"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_key_secret_name
              key  = "latest"
            }
          }
        }
        
        env {
          name = "BYBIT_TESTNET_API_SECRET"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_secret_secret_name
              key  = "latest"
            }
          }
        }
        
        ports {
          container_port = 8080
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Invoke permission（パブリック公開）
resource "google_cloud_run_service_iam_member" "all_users" {
  service  = google_cloud_run_service.service.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
