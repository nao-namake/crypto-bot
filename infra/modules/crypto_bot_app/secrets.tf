############################################
# infra/modules/crypto_bot_app/secrets.tf
# Secret Manager resources for API keys (OPTIONAL)
# 
# Note: このファイルはSecret Managerを使用する場合のオプション設定です。
# デフォルトではGitHub Secretsから環境変数として直接設定されます。
############################################

# Bitbank API Key Secret (OPTIONAL - only if create_secrets = true)
resource "google_secret_manager_secret" "bitbank_api_key" {
  count = var.create_secrets ? 1 : 0
  
  secret_id = "bitbank-api-key"
  project   = var.project_id

  replication {
    auto {}
  }
}

# Bitbank API Key Secret Version
resource "google_secret_manager_secret_version" "bitbank_api_key" {
  count = var.create_secrets && var.bitbank_api_key != "" ? 1 : 0
  
  secret      = google_secret_manager_secret.bitbank_api_key[0].id
  secret_data = var.bitbank_api_key
}

# Bitbank API Secret
resource "google_secret_manager_secret" "bitbank_api_secret" {
  count = var.create_secrets ? 1 : 0
  
  secret_id = "bitbank-api-secret"
  project   = var.project_id

  replication {
    auto {}
  }
}

# Bitbank API Secret Version
resource "google_secret_manager_secret_version" "bitbank_api_secret" {
  count = var.create_secrets && var.bitbank_api_secret != "" ? 1 : 0
  
  secret      = google_secret_manager_secret.bitbank_api_secret[0].id
  secret_data = var.bitbank_api_secret
}

# Secret Managerへのアクセス権限をCloud Runサービスアカウントに付与
resource "google_secret_manager_secret_iam_member" "bitbank_api_key_access" {
  count = var.create_secrets ? 1 : 0
  
  project   = var.project_id
  secret_id = google_secret_manager_secret.bitbank_api_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "bitbank_api_secret_access" {
  count = var.create_secrets ? 1 : 0
  
  project   = var.project_id
  secret_id = google_secret_manager_secret.bitbank_api_secret[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}