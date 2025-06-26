terraform {
  backend "gcs" {
    bucket = "my-crypto-bot-terraform-state"
    prefix = "prod"
  }
}
