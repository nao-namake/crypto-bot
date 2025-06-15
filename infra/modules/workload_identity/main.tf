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
  attribute_condition = "attribute.repository == \"${var.github_repo}\""

  oidc { issuer_uri = "https://token.actions.githubusercontent.com" }
}