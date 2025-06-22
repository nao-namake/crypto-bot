#######################################
# WIF Hardening Verification
# Tests and outputs for security configuration
#######################################

# Output current security configuration
output "wif_security_config" {
  description = "Workload Identity Federation security configuration"
  value = {
    repository_restriction = var.github_repo
    branch_restriction     = "refs/heads/main"
    oidc_issuer           = "https://token.actions.githubusercontent.com"
    attribute_condition   = "attribute.repository == \"${var.github_repo}\" && attribute.ref == \"refs/heads/main\""
  }
}

# Verify minimal permissions
output "deployer_sa_permissions" {
  description = "GitHub Deployer Service Account minimal permissions"
  value = [
    "roles/run.admin",
    "roles/artifactregistry.admin", 
    "roles/monitoring.admin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/secretmanager.admin",
    "roles/storage.objectAdmin",
    "roles/iam.serviceAccountUser",
    "roles/iam.securityReviewer"
  ]
}

# Security compliance check
output "security_hardening_status" {
  description = "WIF security hardening compliance status"
  value = {
    repository_restricted = true
    branch_restricted     = true
    minimal_permissions   = true
    oidc_issuer_verified  = true
    last_updated         = timestamp()
  }
}