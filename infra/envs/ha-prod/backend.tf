terraform {
  backend "gcs" {
    bucket = "crypto-bot-tf-state-ha"
    prefix = "terraform/state/ha-prod"
  }
}