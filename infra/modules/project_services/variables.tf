variable "project_id" { type = string }
variable "services" {
  type    = list(string)
  default = [
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
  ]
}
