##############################################
# Module: workload_identity / variables.tf
# Purpose: Central definition of inputs for
#          Workload‑Identity Federation pool /
#          provider + optional SA binding.
##############################################

# ────────────────────────────────────────────
# GCP settings
# ────────────────────────────────────────────
variable "project_id" {
  description = "GCP project ID where Workload‑Identity Pool & Provider are created"
  type        = string
}

variable "project_number" {
  description = "Numeric project number (used for principalSet strings in IAM bindings)"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{6,}$", var.project_number))
    error_message = "project_number must be the numeric string you get from `gcloud projects describe`."
  }
}

variable "location" {
  description = "Location of the Workload‑Identity Pool (almost always \"global\")"
  type        = string
  default     = "global"
}

# ────────────────────────────────────────────
# Workload‑Identity Pool / Provider IDs
# ────────────────────────────────────────────
variable "pool_id" {
  description = "Workload‑Identity Pool ID"
  type        = string
  default     = "github-pool"
}

variable "provider_id" {
  description = "Workload‑Identity Provider ID"
  type        = string
  default     = "github-provider"
}

# ────────────────────────────────────────────
# GitHub‑side settings
# ────────────────────────────────────────────
variable "github_repo" {
  description = "GitHub repository allowed to deploy (format: \"<owner>/<repo>\")"
  type        = string
  default     = "nao-namake/crypto-bot"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repo))
    error_message = "github_repo must be in \"owner/repo\" format, e.g. \"nao-namake/crypto-bot\"."
  }
}

variable "deployer_sa" {
  description = "Service‑account e‑mail that GitHub Actions will impersonate (optional)."
  type        = string
  default     = null

  validation {
    condition     = var.deployer_sa == null || can(regex("^[A-Za-z0-9-]+@[A-Za-z0-9-]+\\.iam\\.gserviceaccount\\.com$", var.deployer_sa))
    error_message = "deployer_sa, if set, must be a valid service‑account e‑mail (…@<project>.iam.gserviceaccount.com)."
  }
}
