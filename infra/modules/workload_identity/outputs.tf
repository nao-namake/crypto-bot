#######################################
# IAM権限伝播確実化のOutput
#######################################

output "discord_permissions_ready" {
  description = "Discord監視モジュール用のIAM権限が確実に伝播されたことを示すマーカー"
  value       = time_sleep.wait_for_discord_permissions.id
}

#######################################
# 既存のOutput（参考用）
#######################################

output "pool_name" {
  description = "作成されたWorkload Identity Poolの名前"
  value       = google_iam_workload_identity_pool.pool.name
}

output "provider_name" {
  description = "作成されたWorkload Identity Providerの名前" 
  value       = google_iam_workload_identity_pool_provider.provider.name
}