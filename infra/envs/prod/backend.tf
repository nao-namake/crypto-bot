terraform {
  backend "local" {               # 後で GCS backend に書き換えても OK
    path = "terraform.prod.tfstate"
  }
}
