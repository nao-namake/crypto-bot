# =============================================================================
# ファイル名: infra/outputs.tf
# 説明:
#   - Terraform 実行後に参照したい出力値を定義
#   - デプロイされた Cloud Run サービスの URL を表示
# =============================================================================

output "cloud_run_url" {
  description = "デプロイされた Cloud Run サービスの URL"
  value       = google_cloud_run_service.crypto_bot.status[0].url
}