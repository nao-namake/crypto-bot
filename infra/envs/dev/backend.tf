terraform {
  backend "gcs" {
    bucket = "my-crypto-bot-tfstate"
    prefix = "dev"
  }
}