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
      # リビジョン競合を回避するため、自動生成させる（nameを指定しない）
      # name = "${var.service_name}-${substr(replace(var.image_tag, ":", ""), 0, 6)}"
    }
    spec {
      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"
        
        resources {
          limits = {
            cpu    = "1000m"  # 1 CPU (Phase H.25: 外部API無効化により削減)
            memory = "2Gi"    # 2GB RAM (125特徴量での動作に十分)
          }
          requests = {
            cpu    = "500m"   # 最小0.5 CPU
            memory = "1Gi"    # 最小1GB RAM
          }
        }
        
        env {
          name  = "MODE"
          value = var.mode
        }
        
        # Bitbank API認証情報（GitHub Secretsから取得）
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
        
        # Phase H.22: External API Keys（Phase 3で無効化済み）
        # 注: これらの外部APIはPhase 3で除去され、現在使用されていません
        # 将来的に必要になった場合の参考用にコメントとして保持
        #
        # # Alpha Vantage API (VIXデータ用 - 現在未使用)
        # env {
        #   name  = "ALPHA_VANTAGE_API_KEY"
        #   value = var.alpha_vantage_api_key
        # }
        #
        # # Polygon.io API (市場データ用 - 現在未使用)
        # env {
        #   name  = "POLYGON_API_KEY"
        #   value = var.polygon_api_key
        # }
        #
        # # FRED API (経済指標用 - 現在未使用)
        # env {
        #   name  = "FRED_API_KEY"
        #   value = var.fred_api_key
        # }
        
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
