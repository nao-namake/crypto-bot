# infra/modules/gke/variables.tf

variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region for the cluster"
  type        = string
  default     = "asia-northeast1"
}

variable "cluster_name" {
  description = "The name of the GKE cluster"
  type        = string
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

variable "master_ipv4_cidr_block" {
  description = "CIDR block for the master nodes"
  type        = string
  default     = "172.16.0.0/28"
}

variable "enable_private_endpoint" {
  description = "Enable private endpoint for the cluster master"
  type        = bool
  default     = false
}

variable "authorized_networks" {
  description = "List of authorized networks that can access the cluster master"
  type = list(object({
    cidr_block   = string
    display_name = string
  }))
  default = null
}

# Cluster configuration
variable "release_channel" {
  description = "The release channel for the cluster"
  type        = string
  default     = "RAPID"
  validation {
    condition     = contains(["RAPID", "REGULAR", "STABLE"], var.release_channel)
    error_message = "Release channel must be one of: RAPID, REGULAR, STABLE."
  }
}

variable "enable_binary_authorization" {
  description = "Enable Binary Authorization for the cluster"
  type        = bool
  default     = false
}

variable "cluster_labels" {
  description = "Labels to apply to the cluster"
  type        = map(string)
  default     = {}
}

# Node pool configuration
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

variable "image_type" {
  description = "Image type for nodes"
  type        = string
  default     = "COS_CONTAINERD"
}

variable "preemptible" {
  description = "Whether primary nodes should be preemptible"
  type        = bool
  default     = false
}

variable "node_labels" {
  description = "Labels to apply to nodes"
  type        = map(string)
  default     = {}
}

variable "node_tags" {
  description = "Network tags to apply to nodes"
  type        = list(string)
  default     = []
}

# Spot nodes configuration
variable "enable_spot_nodes" {
  description = "Enable spot node pool"
  type        = bool
  default     = true
}

variable "spot_node_count" {
  description = "Number of nodes in the spot node pool"
  type        = number
  default     = 1
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

variable "spot_disk_size_gb" {
  description = "Disk size in GB for spot nodes"
  type        = number
  default     = 30
}

# Upgrade settings
variable "max_surge" {
  description = "Maximum number of nodes that can be created during upgrade"
  type        = number
  default     = 1
}

variable "max_unavailable" {
  description = "Maximum number of nodes that can be unavailable during upgrade"
  type        = number
  default     = 0
}

# Maintenance window
variable "maintenance_start_time" {
  description = "Start time for maintenance window (RFC3339 format)"
  type        = string
  default     = "2023-01-01T01:00:00Z"
}

variable "maintenance_end_time" {
  description = "End time for maintenance window (RFC3339 format)"
  type        = string
  default     = "2023-01-01T05:00:00Z"
}

variable "maintenance_recurrence" {
  description = "Recurrence rule for maintenance window"
  type        = string
  default     = "FREQ=WEEKLY;BYDAY=SU"
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

# Ingress configuration
variable "create_ingress_ip" {
  description = "Create static IP for ingress"
  type        = bool
  default     = true
}