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
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "5"
        "run.googleapis.com/cpu-throttling" = "false"
        "run.googleapis.com/execution-environment" = "gen2"
      }
    }
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"
        
        resources {
          limits = {
            cpu    = "2000m"  # 2 CPU (126特徴量対応)
            memory = "4Gi"    # 4GB RAM (外部データ処理対応)
          }
          requests = {
            cpu    = "1000m"  # 最小1 CPU
            memory = "2Gi"    # 最小2GB RAM
          }
        }
        
        env {
          name  = "MODE"
          value = var.mode
        }
        
        env {
          name  = "BITBANK_API_KEY"
          value = var.bitbank_api_key
        }
        
        env {
          name  = "BITBANK_API_SECRET"
          value = var.bitbank_api_secret
        }
        
        env {
          name  = "FEATURE_MODE"
          value = var.feature_mode
        }
        
        # Phase H.22: External API Keys
        env {
          name  = "ALPHA_VANTAGE_API_KEY"
          value = var.alpha_vantage_api_key
        }
        
        env {
          name  = "POLYGON_API_KEY"
          value = var.polygon_api_key
        }
        
        env {
          name  = "FRED_API_KEY"
          value = var.fred_api_key
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
