# infra/envs/k8s-gke/variables.tf

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for resources"
  type        = string
  default     = "asia-northeast1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# Network configuration
variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "pods_cidr" {
  description = "CIDR block for pods secondary range"
  type        = string
  default     = "10.1.0.0/16"
}

variable "services_cidr" {
  description = "CIDR block for services secondary range"
  type        = string
  default     = "10.2.0.0/16"
}

variable "authorized_networks" {
  description = "List of authorized networks that can access the cluster master"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = [
    {
      cidr_block   = "0.0.0.0/0"
      display_name = "All networks"
    }
  ]
}

# Cluster configuration
variable "release_channel" {
  description = "The release channel for the cluster"
  type        = string
  default     = "RAPID"
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization for the cluster"
  type        = bool
  default     = false
}

# Node configuration
variable "node_count" {
  description = "Number of nodes in the primary node pool"
  type        = number
  default     = 2
}

variable "min_node_count" {
  description = "Minimum number of nodes in the primary node pool"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of nodes in the primary node pool"
  type        = number
  default     = 10
}

variable "machine_type" {
  description = "Machine type for primary nodes"
  type        = string
  default     = "e2-standard-2"
}

variable "disk_size_gb" {
  description = "Disk size in GB for primary nodes"
  type        = number
  default     = 50
}

variable "disk_type" {
  description = "Disk type for primary nodes"
  type        = string
  default     = "pd-ssd"
}

variable "preemptible" {
  description = "Whether primary nodes should be preemptible"
  type        = bool
  default     = false
}

# Spot nodes configuration
variable "enable_spot_nodes" {
  description = "Enable spot node pool"
  type        = bool
  default     = true
}

variable "spot_min_node_count" {
  description = "Minimum number of nodes in the spot node pool"
  type        = number
  default     = 0
}

variable "spot_max_node_count" {
  description = "Maximum number of nodes in the spot node pool"
  type        = number
  default     = 5
}

variable "spot_machine_type" {
  description = "Machine type for spot nodes"
  type        = string
  default     = "e2-medium"
}

# Crypto-bot specific configuration
variable "crypto_bot_namespace" {
  description = "Kubernetes namespace for crypto-bot"
  type        = string
  default     = "crypto-bot"
}

variable "crypto_bot_ksa_name" {
  description = "Kubernetes service account name for crypto-bot"
  type        = string
  default     = "crypto-bot"
}

variable "crypto_bot_iam_roles" {
  description = "IAM roles for crypto-bot service account"
  type        = list(string)
  default = [
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor",
  ]
}

# Labels and tags
variable "common_labels" {
  description = "Common labels to apply to all resources"
  type        = map(string)
  default = {
    managed-by = "terraform"
    project    = "crypto-bot"
  }
}

variable "node_labels" {
  description = "Labels to apply to nodes"
  type        = map(string)
  default = {}
}