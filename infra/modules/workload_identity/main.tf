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
  # NOTE: keep using the variable so other environments can override.
  # default value is defined in variables.tf
  attribute_condition = "attribute.repository == \"${var.github_repo}\""

  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}


#######################################
# Service‑Account ↔ WIF プリンシパル紐付け
# GitHub Actions → Workload Identity → SA impersonation
#######################################
resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = "projects/${var.project_id}/serviceAccounts/${var.deployer_sa}"
  role               = "roles/iam.workloadIdentityUser"

  # principalSet 形式:
  # principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${OWNER_REPO}
  member = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.pool.workload_identity_pool_id}/attribute.repository/${var.github_repo}"
}