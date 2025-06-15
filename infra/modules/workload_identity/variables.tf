variable "project_id" {
  type = string
}

variable "pool_id" {
  type    = string
  default = "github-pool"
}

variable "provider_id" {
  type    = string
  default = "github-provider"
}

# GitHub repository (in "owner/repo" format) that is allowed to assume this
# Workload Identity Federation provider.
variable "github_repo" {
  type        = string
  description = "GitHub repository allowed to deploy (e.g., \"nao/crypto-bot\")"
}
