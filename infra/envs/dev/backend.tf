#---------------------------------------------------------------------------------
# Remote backend
#   • GCS bucket must exist **before** terraform init
#   • SA (github-deployer) needs roles/storage.objectAdmin (or equivalent)
#---------------------------------------------------------------------------------
terraform {
  backend "gcs" {
    bucket = "my-crypto-bot-tfstate"
    prefix = "dev"
  }
}