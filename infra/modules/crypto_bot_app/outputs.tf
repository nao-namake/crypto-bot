output "service_url" {
  value = data.google_cloud_run_service.service.status[0].url
}
