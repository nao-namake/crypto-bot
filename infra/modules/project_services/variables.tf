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
variable "project_number" {
  description = "Numeric project ID (e.g. 11445303925)"
  type        = string
}
