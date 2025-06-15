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
          limits = { cpu = "1000m", memory = "512Mi" }
        }
      }
    }
  }
  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "all_users" {
  service  = google_cloud_run_service.service.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

