############################################
# infra/modules/multi_region_app/main.tf
# Multi-region Cloud Run deployment with HA
############################################

# Artifact Registry (global resource)
resource "google_artifact_registry_repository" "repo" {
  project       = var.project_id
  location      = var.primary_region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
}

# Cloud Run services in multiple regions
resource "google_cloud_run_service" "primary" {
  name     = "${var.service_name}-${var.primary_region}"
  location = var.primary_region
  project  = var.project_id

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }

    spec {
      service_account_name = var.service_account_email
      
      containers {
        image = "${var.primary_region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"

        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }

        # Health check endpoint
        ports {
          container_port = 8080
        }

        # ───── 環境変数 ─────
        env {
          name  = "MODE"
          value = var.mode
        }

        env {
          name  = "REGION"
          value = var.primary_region
        }

        env {
          name  = "INSTANCE_ID"
          value = "primary"
        }

        # ───── Secret 連携環境変数 ─────
        env {
          name = "BYBIT_TESTNET_API_KEY"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_key_secret_name
              key  = "latest"
            }
          }
        }

        env {
          name = "BYBIT_TESTNET_API_SECRET"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_secret_secret_name
              key  = "latest"
            }
          }
        }

        # Startup probe
        startup_probe {
          http_get {
            path = "/healthz"
            port = 8080
          }
          initial_delay_seconds = 10
          timeout_seconds       = 3
          period_seconds        = 10
          failure_threshold     = 3
        }

        # Liveness probe
        liveness_probe {
          http_get {
            path = "/healthz"
            port = 8080
          }
          initial_delay_seconds = 30
          timeout_seconds       = 3
          period_seconds        = 30
          failure_threshold     = 3
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_artifact_registry_repository.repo]
}

resource "google_cloud_run_service" "secondary" {
  count    = var.enable_secondary_region ? 1 : 0
  name     = "${var.service_name}-${var.secondary_region}"
  location = var.secondary_region
  project  = var.project_id

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale" = var.min_instances
        "autoscaling.knative.dev/maxScale" = var.max_instances
        "run.googleapis.com/cpu-throttling" = "false"
      }
    }

    spec {
      service_account_name = var.service_account_email
      
      containers {
        image = "${var.primary_region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}/${var.image_name}:${var.image_tag}"

        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }

        ports {
          container_port = 8080
        }

        # ───── 環境変数 ─────
        env {
          name  = "MODE"
          value = var.mode
        }

        env {
          name  = "REGION"
          value = var.secondary_region
        }

        env {
          name  = "INSTANCE_ID"
          value = "secondary"
        }

        # ───── Secret 連携環境変数 ─────
        env {
          name = "BYBIT_TESTNET_API_KEY"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_key_secret_name
              key  = "latest"
            }
          }
        }

        env {
          name = "BYBIT_TESTNET_API_SECRET"
          value_from {
            secret_key_ref {
              name = var.bybit_testnet_api_secret_secret_name
              key  = "latest"
            }
          }
        }

        startup_probe {
          http_get {
            path = "/healthz"
            port = 8080
          }
          initial_delay_seconds = 10
          timeout_seconds       = 3
          period_seconds        = 10
          failure_threshold     = 3
        }

        liveness_probe {
          http_get {
            path = "/healthz"
            port = 8080
          }
          initial_delay_seconds = 30
          timeout_seconds       = 3
          period_seconds        = 30
          failure_threshold     = 3
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [google_artifact_registry_repository.repo]
}

# Global Load Balancer for HA
resource "google_compute_global_address" "lb_ip" {
  count   = var.enable_load_balancer ? 1 : 0
  name    = "${var.service_name}-lb-ip"
  project = var.project_id
}

# Backend service for primary region
resource "google_compute_region_network_endpoint_group" "primary_neg" {
  name                  = "${var.service_name}-primary-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.primary_region
  project               = var.project_id

  cloud_run {
    service = google_cloud_run_service.primary.name
  }
}

# Backend service for secondary region (if enabled)
resource "google_compute_region_network_endpoint_group" "secondary_neg" {
  count                 = var.enable_secondary_region ? 1 : 0
  name                  = "${var.service_name}-secondary-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.secondary_region
  project               = var.project_id

  cloud_run {
    service = google_cloud_run_service.secondary[0].name
  }
}

# Health check
resource "google_compute_health_check" "default" {
  count   = var.enable_load_balancer ? 1 : 0
  name    = "${var.service_name}-health-check"
  project = var.project_id

  http_health_check {
    request_path = "/healthz"
    port         = "8080"
  }

  check_interval_sec  = 30
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3
}

# Backend service
resource "google_compute_backend_service" "default" {
  count                           = var.enable_load_balancer ? 1 : 0
  name                           = "${var.service_name}-backend"
  project                        = var.project_id
  port_name                      = "http"
  protocol                       = "HTTP"
  timeout_sec                    = 30
  connection_draining_timeout_sec = 300

  # Primary region backend
  backend {
    group           = google_compute_region_network_endpoint_group.primary_neg.id
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
  }

  # Secondary region backend (if enabled)
  dynamic "backend" {
    for_each = var.enable_secondary_region ? [1] : []
    content {
      group           = google_compute_region_network_endpoint_group.secondary_neg[0].id
      balancing_mode  = "UTILIZATION"
      capacity_scaler = 0.8  # Lower priority
    }
  }

  health_checks = [google_compute_health_check.default[0].id]

  # Failover configuration
  dynamic "failover_policy" {
    for_each = var.enable_secondary_region ? [1] : []
    content {
      disable_connection_drain_on_failover = false
      drop_traffic_if_unhealthy             = true
      failover_ratio                        = 0.1
    }
  }
}

# URL map
resource "google_compute_url_map" "default" {
  count           = var.enable_load_balancer ? 1 : 0
  name            = "${var.service_name}-url-map"
  project         = var.project_id
  default_service = google_compute_backend_service.default[0].id
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "default" {
  count   = var.enable_load_balancer && var.enable_ssl ? 1 : 0
  name    = "${var.service_name}-https-proxy"
  project = var.project_id
  url_map = google_compute_url_map.default[0].id
  ssl_certificates = [
    google_compute_managed_ssl_certificate.default[0].id
  ]
}

# HTTP proxy (redirect to HTTPS or direct)
resource "google_compute_target_http_proxy" "default" {
  count   = var.enable_load_balancer ? 1 : 0
  name    = "${var.service_name}-http-proxy"
  project = var.project_id
  url_map = var.enable_ssl ? google_compute_url_map.redirect[0].id : google_compute_url_map.default[0].id
}

# Redirect URL map (HTTP to HTTPS)
resource "google_compute_url_map" "redirect" {
  count   = var.enable_load_balancer && var.enable_ssl ? 1 : 0
  name    = "${var.service_name}-redirect"
  project = var.project_id

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

# Managed SSL certificate
resource "google_compute_managed_ssl_certificate" "default" {
  count   = var.enable_load_balancer && var.enable_ssl && length(var.domains) > 0 ? 1 : 0
  name    = "${var.service_name}-ssl-cert"
  project = var.project_id

  managed {
    domains = var.domains
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Global forwarding rule (HTTPS)
resource "google_compute_global_forwarding_rule" "https" {
  count                 = var.enable_load_balancer && var.enable_ssl ? 1 : 0
  name                  = "${var.service_name}-https-rule"
  project               = var.project_id
  target                = google_compute_target_https_proxy.default[0].id
  port_range            = "443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip[0].address
}

# Global forwarding rule (HTTP)
resource "google_compute_global_forwarding_rule" "http" {
  count                 = var.enable_load_balancer ? 1 : 0
  name                  = "${var.service_name}-http-rule"
  project               = var.project_id
  target                = google_compute_target_http_proxy.default[0].id
  port_range            = "80"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.lb_ip[0].address
}

# IAM bindings for Cloud Run services
resource "google_cloud_run_service_iam_member" "primary_public" {
  count    = var.enable_public_access ? 1 : 0
  service  = google_cloud_run_service.primary.name
  location = var.primary_region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "secondary_public" {
  count    = var.enable_secondary_region && var.enable_public_access ? 1 : 0
  service  = google_cloud_run_service.secondary[0].name
  location = var.secondary_region
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM binding for load balancer access
resource "google_cloud_run_service_iam_member" "primary_lb" {
  count    = var.enable_load_balancer ? 1 : 0
  service  = google_cloud_run_service.primary.name
  location = var.primary_region
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${var.project_number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_cloud_run_service_iam_member" "secondary_lb" {
  count    = var.enable_secondary_region && var.enable_load_balancer ? 1 : 0
  service  = google_cloud_run_service.secondary[0].name
  location = var.secondary_region
  role     = "roles/run.invoker"
  member   = "serviceAccount:service-${var.project_number}@serverless-robot-prod.iam.gserviceaccount.com"
}