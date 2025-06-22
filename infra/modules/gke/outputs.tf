# infra/modules/gke/outputs.tf

output "cluster_name" {
  description = "Name of the GKE cluster"
  value       = google_container_cluster.primary.name
}

output "cluster_location" {
  description = "Location of the GKE cluster"
  value       = google_container_cluster.primary.location
}

output "cluster_endpoint" {
  description = "Endpoint of the GKE cluster"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "CA certificate of the GKE cluster"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "node_service_account_email" {
  description = "Email of the node service account"
  value       = google_service_account.gke_node_sa.email
}

output "crypto_bot_service_account_email" {
  description = "Email of the crypto-bot service account"
  value       = google_service_account.crypto_bot_sa.email
}

output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.vpc.name
}

output "subnet_name" {
  description = "Name of the subnet"
  value       = google_compute_subnetwork.subnet.name
}

output "ingress_ip" {
  description = "Static IP address for ingress"
  value       = var.create_ingress_ip ? google_compute_global_address.ingress_ip[0].address : null
}

output "ingress_ip_name" {
  description = "Name of the static IP address for ingress"
  value       = var.create_ingress_ip ? google_compute_global_address.ingress_ip[0].name : null
}

# Outputs for kubectl configuration
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "gcloud container clusters get-credentials ${google_container_cluster.primary.name} --region=${var.region} --project=${var.project_id}"
}

# Workload Identity annotations
output "workload_identity_annotation" {
  description = "Annotation for Kubernetes service account to use Workload Identity"
  value       = "iam.gke.io/gcp-service-account=${google_service_account.crypto_bot_sa.email}"
}

# Helm values for crypto-bot chart
output "helm_values" {
  description = "Suggested Helm values for crypto-bot deployment"
  value = {
    serviceAccount = {
      annotations = {
        "iam.gke.io/gcp-service-account" = google_service_account.crypto_bot_sa.email
      }
    }
    ingress = var.create_ingress_ip ? {
      annotations = {
        "kubernetes.io/ingress.global-static-ip-name" = google_compute_global_address.ingress_ip[0].name
      }
    } : {}
    nodeSelector = {
      "node-role.kubernetes.io/crypto-bot" = "true"
    }
    tolerations = [{
      key      = "node-role.kubernetes.io/crypto-bot"
      value    = "true"
      effect   = "NoSchedule"
      operator = "Equal"
    }]
  }
}