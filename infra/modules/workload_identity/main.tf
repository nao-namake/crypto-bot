#######################################
# プール
#######################################
resource "google_iam_workload_identity_pool" "pool" {
  project                   = var.project_id
  workload_identity_pool_id = var.pool_id
  display_name              = "GitHub Actions Pool"
}

#######################################
# プロバイダ（GitHub OIDC, repository 条件付き）
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
  # NOTE: Keep using the variable so other environments can override.
  # default value is defined in variables.tf
  attribute_condition = "attribute.repository == \"${var.github_repo}\""

  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}


#######################################
# SA に ServiceAccountViewer を付与（getIamPolicy を許可）
#######################################
resource "google_service_account_iam_member" "deployer_sa_viewer" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.deployer_sa}"
  role               = "roles/iam.serviceAccountViewer"
  member             = "serviceAccount:${var.deployer_sa}"
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.deployer_sa}"
  role               = "roles/iam.workloadIdentityUser"

  # principalSet 形式:
  # principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${OWNER_REPO}
  member = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.pool.workload_identity_pool_id}/attribute.repository/${var.github_repo}"
}

#######################################
# SA に Workload‑Identity Pool Admin を付与（Pool/Provider を Terraform 管理出来るように）
#######################################
resource "google_project_iam_member" "deployer_sa_wip_admin" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityPoolAdmin"
  member  = "serviceAccount:${var.deployer_sa}"
}

#######################################
# SA に ServiceAccountAdmin を付与（自身の IAM を更新出来るように）
#######################################
resource "google_project_iam_member" "deployer_sa_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${var.deployer_sa}"
}
