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

  # Terraformタイムアウト設定（5分に短縮）
  timeouts {
    create = "5m"
    update = "5m"
    delete = "5m"
  }

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = "1"  # SIGTERM頻発対策
        "autoscaling.knative.dev/maxScale" = "5"
        "run.googleapis.com/cpu-throttling" = "false"
        "run.googleapis.com/execution-environment" = "gen2"
      }
      # リビジョン競合を回避するため、自動生成させる（nameを指定しない）
      # name = "${var.service_name}-${substr(replace(var.image_tag, ":", ""), 0, 6)}"
    }
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"
        
        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
          requests = {
            cpu    = var.cpu_request
            memory = var.memory_request
          }
        }
        
        env {
          name  = "MODE"
          value = var.mode
        }
        
        # Bitbank API認証情報（GitHub Secretsから取得）
        # Paper modeでも常に環境変数を設定（空の場合はdefault値）
        env {
          name  = "BITBANK_API_KEY"
          value = var.bitbank_api_key
        }
        
        env {
          name  = "BITBANK_API_SECRET"
          value = var.bitbank_api_secret
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
  
  # Cloud Runサービスが完全に作成されるまで待機
  depends_on = [google_cloud_run_service.service]
}
