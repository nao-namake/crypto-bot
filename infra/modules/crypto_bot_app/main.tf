############################################
# infra/modules/crypto_bot_app/main.tf
# Cloud Run service + Artifact Registry remote repo for GHCR
############################################

# Artifact Registry リポジトリを作成
resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
}

resource "google_cloud_run_service" "service" {
  name     = var.service_name
  location = var.region

  template {
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"

        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }

        # ───── 通常の環境変数 ─────
        env {
          name  = "MODE"
          value = var.mode
        }

        # ───── Secret 連携環境変数（API KEY）─────
        env {
          name = "BYBIT_TESTNET_API_KEY"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_key_secret_name   # default "bybit_testnet_api_key"
              key  = "latest"                               # Secret Manager version
            }
          }
        }

        # ───── Secret 連携環境変数（API SECRET）─────
        env {
          name = "BYBIT_TESTNET_API_SECRET"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_secret_secret_name # default "bybit_testnet_api_secret"
              key  = "latest"
            }
          }
        }
      }
    }
  }

  # 100% トラフィックを最新リビジョンへ
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
