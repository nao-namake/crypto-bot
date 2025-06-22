# infra/modules/eks/outputs.tf

output "cluster_name" {
  description = "Name of the EKS cluster"
  value       = aws_eks_cluster.cluster.name
}

output "cluster_endpoint" {
  description = "Endpoint for EKS control plane"
  value       = aws_eks_cluster.cluster.endpoint
}

output "cluster_security_group_id" {
  description = "Security group ID attached to the EKS cluster"
  value       = aws_eks_cluster.cluster.vpc_config[0].cluster_security_group_id
}

output "cluster_iam_role_arn" {
  description = "IAM role ARN associated with EKS cluster"
  value       = aws_eks_cluster.cluster.role_arn
}

output "cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.cluster.certificate_authority[0].data
  sensitive   = true
}

output "cluster_version" {
  description = "The Kubernetes version for the EKS cluster"
  value       = aws_eks_cluster.cluster.version
}

output "cluster_oidc_issuer_url" {
  description = "The URL on the EKS cluster OIDC Issuer"
  value       = aws_eks_cluster.cluster.identity[0].oidc[0].issuer
}

# VPC outputs
output "vpc_id" {
  description = "ID of the VPC where the cluster is deployed"
  value       = aws_vpc.eks_vpc.id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

# Node group outputs
output "node_group_arn" {
  description = "Amazon Resource Name (ARN) of the EKS Node Group"
  value       = aws_eks_node_group.primary.arn
}

output "node_group_status" {
  description = "Status of the EKS Node Group"
  value       = aws_eks_node_group.primary.status
}

output "spot_node_group_arn" {
  description = "Amazon Resource Name (ARN) of the EKS Spot Node Group"
  value       = var.enable_spot_instances ? aws_eks_node_group.spot[0].arn : null
}

# IAM outputs
output "crypto_bot_role_arn" {
  description = "ARN of the IAM role for crypto-bot service account"
  value       = aws_iam_role.crypto_bot_role.arn
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC Provider for IRSA"
  value       = aws_iam_openid_connect_provider.eks_oidc.arn
}

# Security group outputs
output "cluster_primary_security_group_id" {
  description = "The cluster primary security group ID created by EKS"
  value       = aws_eks_cluster.cluster.vpc_config[0].cluster_security_group_id
}

output "node_security_group_id" {
  description = "ID of the EKS node shared security group"
  value       = aws_security_group.eks_nodes.id
}

# KMS outputs
output "kms_key_arn" {
  description = "ARN of the KMS key used for EKS encryption"
  value       = var.kms_key_arn != null ? var.kms_key_arn : aws_kms_key.eks[0].arn
}

output "kms_key_id" {
  description = "ID of the KMS key used for EKS encryption"
  value       = var.kms_key_arn != null ? var.kms_key_arn : aws_kms_key.eks[0].key_id
}

# kubectl configuration
output "kubectl_config_command" {
  description = "kubectl config command to configure access to the EKS cluster"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${aws_eks_cluster.cluster.name}"
}

# Helm values for crypto-bot chart
output "helm_values" {
  description = "Suggested Helm values for crypto-bot deployment on EKS"
  value = {
    serviceAccount = {
      annotations = {
        "eks.amazonaws.com/role-arn" = aws_iam_role.crypto_bot_role.arn
      }
    }
    nodeSelector = {
      "node-role.kubernetes.io/crypto-bot" = "true"
    }
    tolerations = [
      {
        key      = "node-role.kubernetes.io/crypto-bot"
        value    = "true"
        effect   = "NoSchedule"
        operator = "Equal"
      }
    ]
    ingress = {
      enabled = true
      annotations = {
        "kubernetes.io/ingress.class"                    = "alb"
        "alb.ingress.kubernetes.io/scheme"               = "internet-facing"
        "alb.ingress.kubernetes.io/target-type"          = "ip"
        "alb.ingress.kubernetes.io/healthcheck-path"     = "/healthz"
        "alb.ingress.kubernetes.io/listen-ports"         = "[{\"HTTP\": 80}, {\"HTTPS\": 443}]"
        "alb.ingress.kubernetes.io/ssl-redirect"         = "443"
        "alb.ingress.kubernetes.io/certificate-arn"      = "arn:aws:acm:${var.region}:${data.aws_caller_identity.current.account_id}:certificate/YOUR_CERT_ID"
      }
    }
  }
}

# CloudWatch Log Group
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group for EKS cluster"
  value       = aws_cloudwatch_log_group.eks_cluster.name
}