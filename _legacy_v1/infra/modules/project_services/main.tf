resource "google_project_service" "enabled" {
  for_each           = toset(var.services)
  project            = var.project_id
  service            = each.value
  disable_on_destroy = true
}

resource "google_project_iam_member" "run_sa_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:service-${var.project_number}@serverless-robot-prod.iam.gserviceaccount.com"
}

# Cloud Run の実行サービスアカウントに Secret Manager の読み取り権限を付与
resource "google_project_iam_member" "run_sa_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  # デフォルトの Cloud Run 実行 SA (<PROJECT_NUMBER>-compute@developer.gserviceaccount.com)
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}