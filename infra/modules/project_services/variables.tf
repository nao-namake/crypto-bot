variable "project_id" {
  description = "Google Cloud project ID where services are enabled"
  type        = string
}

variable "services" {
  description = "List of Google APIs to enable for the project"
  type        = list(string)
  default = [
    "artifactregistry.googleapis.com",
    "run.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "cloudfunctions.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "secretmanager.googleapis.com",
  ]
}

variable "project_number" {
  description = "Numeric Google Cloud project number (e.g. 11445303925)"
  type        = string
}
