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

  # Terraformタイムアウト設定（デプロイ時の長時間待機を回避）
  timeouts {
    create = "10m"
    update = "10m"
    delete = "10m"
  }

  template {
    metadata {
      annotations = {
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
        # Paper modeの場合は空でも動作するようにする
        dynamic "env" {
          for_each = var.bitbank_api_key != "" ? [1] : []
          content {
            name  = "BITBANK_API_KEY"
            value = var.bitbank_api_key
          }
        }
        
        dynamic "env" {
          for_each = var.bitbank_api_secret != "" ? [1] : []
          content {
            name  = "BITBANK_API_SECRET"
            value = var.bitbank_api_secret
          }
        }
        
        # 97特徴量固定のため、FEATURE_MODE環境変数は削除
        
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
