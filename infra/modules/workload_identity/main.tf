#######################################
# プール（既存リソースの管理を引き継ぎ）
#######################################
resource "google_iam_workload_identity_pool" "pool" {
  project                   = var.project_id
  workload_identity_pool_id = var.pool_id
  display_name              = "GitHub Actions Pool"
}

#######################################
# プロバイダ（既存リソースの管理を引き継ぎ）
#######################################
resource "google_iam_workload_identity_pool_provider" "provider" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.pool.workload_identity_pool_id
  workload_identity_pool_provider_id = var.provider_id

  display_name = "GitHub Provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }
  attribute_condition = "attribute.repository == \"${var.github_repo}\" && attribute.ref == \"refs/heads/main\""

  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}

#########################################
# Workload Identity Federation binding
#########################################
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.deployer_sa}"
  role               = "roles/iam.workloadIdentityUser"

  # principalSet 形式:
  # principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${OWNER_REPO}
  member = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.pool.workload_identity_pool_id}/attribute.repository/${var.github_repo}"
}

#########################################
# Minimal permissions for GitHub deployer SA
# Following the principle of least privilege
#########################################

# Cloud Run permissions - for deploying services
resource "google_project_iam_member" "deployer_sa_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${var.deployer_sa}"
}

# Artifact Registry permissions - for pushing/pulling container images
resource "google_project_iam_member" "deployer_sa_artifact_registry_admin" {
  project = var.project_id
  role    = "roles/artifactregistry.admin"
  member  = "serviceAccount:${var.deployer_sa}"
}

# Monitoring permissions - for managing monitoring resources
resource "google_project_iam_member" "deployer_sa_monitoring_admin" {
  project = var.project_id
  role    = "roles/monitoring.admin"
  member  = "serviceAccount:${var.deployer_sa}"
}

# Service Usage permissions - for managing enabled APIs
resource "google_project_iam_member" "deployer_sa_service_usage_admin" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageAdmin"
  member  = "serviceAccount:${var.deployer_sa}"
}

# Secret Manager permissions - for managing API keys
resource "google_project_iam_member" "deployer_sa_secret_manager_admin" {
  project = var.project_id
  role    = "roles/secretmanager.admin"
  member  = "serviceAccount:${var.deployer_sa}"
}

# Storage Object Admin - for Terraform state management
resource "google_project_iam_member" "deployer_sa_storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${var.deployer_sa}"
}

#######################################
# Limited IAM permissions for Terraform operations
#######################################

# Service Account User - for using service accounts
resource "google_project_iam_member" "deployer_sa_iam_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${var.deployer_sa}"
}

# IAM Security Reviewer - minimal read-only access for IAM (replacing securityAdmin)
resource "google_project_iam_member" "deployer_sa_security_reviewer" {
  project = var.project_id
  role    = "roles/iam.securityReviewer"
  member  = "serviceAccount:${var.deployer_sa}"
}

# BigQuery Admin - for creating datasets and managing BigQuery resources
resource "google_project_iam_member" "deployer_sa_bigquery_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${var.deployer_sa}"
}

# Logging Admin - for creating log sinks and managing logging configuration
resource "google_project_iam_member" "deployer_sa_logging_admin" {
  project = var.project_id
  role    = "roles/logging.admin"
  member  = "serviceAccount:${var.deployer_sa}"
}

# IAM Workload Identity Pool Admin - for managing WIF pools and providers
resource "google_project_iam_member" "deployer_sa_wif_admin" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityPoolAdmin"
  member  = "serviceAccount:${var.deployer_sa}"
}