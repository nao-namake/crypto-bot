# =============================================================================
# ファイル名: infra/main.tf
# 説明:
#   - Google Artifact Registry に Docker リポジトリを作成
#   - Cloud Run サービスを作成し、指定した GCP プロジェクト・リージョンにデプロイ
#   - サービスをパブリックに呼び出せるよう IAM 設定
# =============================================================================

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  # GCP プロジェクトIDを直接指定
  project = "my-crypto-bot-project"
  # デプロイ先リージョン
  region  = var.region
}

# Artifact Registry リポジトリを作成
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
}

# Cloud Run サービスを作成し、Artifact Registry のイメージを指定
resource "google_cloud_run_service" "crypto_bot" {
  name     = var.service_name
  location = var.region

  metadata {
    annotations = {
      # GA ステージで公開
      "run.googleapis.com/launch-stage" = "GA"
    }
  }

  template {
    spec {
      containers {
        # イメージパス: <リージョン>-docker.pkg.dev/<プロジェクトID>/<リポジトリ>/<イメージ名>:<タグ>
        image = "${var.region}-docker.pkg.dev/my-crypto-bot-project/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"
      }
    }
  }

  traffic {
    # 最新リビジョンに100%ルーティング
    percent         = 100
    latest_revision = true
  }
}

# Cloud Run をパブリック呼び出し可能にする IAM メンバー設定
resource "google_cloud_run_service_iam_member" "invoker" {
  service  = google_cloud_run_service.crypto_bot.name
  location = google_cloud_run_service.crypto_bot.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}