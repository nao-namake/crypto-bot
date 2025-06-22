# infra/modules/eks/variables.tf

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

# Network configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

# EKS cluster configuration
variable "kubernetes_version" {
  description = "Kubernetes version for the EKS cluster"
  type        = string
  default     = "1.28"
}

variable "enable_private_endpoint" {
  description = "Enable private API server endpoint"
  type        = bool
  default     = true
}

variable "enable_public_endpoint" {
  description = "Enable public API server endpoint"
  type        = bool
  default     = true
}

variable "public_access_cidrs" {
  description = "List of CIDR blocks that can access the public API server endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "cluster_log_types" {
  description = "List of control plane log types to enable"
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

# KMS configuration
variable "kms_key_arn" {
  description = "ARN of KMS key for envelope encryption. If null, a new key will be created"
  type        = string
  default     = null
}

# Node group configuration
variable "instance_types" {
  description = "List of instance types for the primary node group"
  type        = list(string)
  default     = ["m5.large"]
}

variable "ami_type" {
  description = "Type of Amazon Machine Image (AMI) associated with the EKS Node Group"
  type        = string
  default     = "AL2_x86_64"
}

variable "disk_size" {
  description = "Disk size in GiB for worker nodes"
  type        = number
  default     = 50
}

variable "desired_capacity" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 10
}

variable "min_capacity" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "max_unavailable_nodes" {
  description = "Maximum number of nodes unavailable during update"
  type        = number
  default     = 1
}

# Spot instances configuration
variable "enable_spot_instances" {
  description = "Enable spot instances node group"
  type        = bool
  default     = true
}

variable "spot_instance_types" {
  description = "List of instance types for the spot node group"
  type        = list(string)
  default     = ["m5.medium", "m5.large", "m4.large"]
}

variable "spot_disk_size" {
  description = "Disk size in GiB for spot worker nodes"
  type        = number
  default     = 30
}

variable "spot_desired_capacity" {
  description = "Desired number of spot worker nodes"
  type        = number
  default     = 1
}

variable "spot_max_capacity" {
  description = "Maximum number of spot worker nodes"
  type        = number
  default     = 5
}

variable "spot_min_capacity" {
  description = "Minimum number of spot worker nodes"
  type        = number
  default     = 0
}

# Labels and tags
variable "node_labels" {
  description = "Kubernetes labels to apply to nodes"
  type        = map(string)
  default     = {}
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Crypto-bot specific configuration
variable "crypto_bot_namespace" {
  description = "Kubernetes namespace for crypto-bot"
  type        = string
  default     = "crypto-bot"
}

variable "crypto_bot_service_account" {
  description = "Kubernetes service account name for crypto-bot"
  type        = string
  default     = "crypto-bot"
}

variable "additional_crypto_bot_policies" {
  description = "Additional IAM policy statements for crypto-bot service account"
  type = list(object({
    Effect   = string
    Action   = list(string)
    Resource = any
  }))
  default = []
}