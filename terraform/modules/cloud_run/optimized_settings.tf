# Phase H.19: Cloud Run最適化設定
# 外部API接続安定化のための推奨設定

variable "enable_external_api_optimization" {
  description = "外部API接続最適化を有効化"
  type        = bool
  default     = true
}

# Cloud Runサービスリソース（最適化版）
resource "google_cloud_run_service" "crypto_bot_optimized" {
  count    = var.enable_external_api_optimization ? 1 : 0
  name     = "${var.service_name}-optimized"
  location = var.region
  
  template {
    spec {
      # サービスアカウント
      service_account_name = var.service_account_email
      
      # コンテナ設定
      containers {
        image = var.container_image
        
        # Phase H.19: 最適化されたリソース設定
        resources {
          limits = {
            cpu    = "2000m"      # 2 vCPU
            memory = "4096Mi"     # 4GB メモリ
          }
          requests = {
            cpu    = "1000m"      # 最小1 vCPU
            memory = "2048Mi"     # 最小2GB
          }
        }
        
        # Phase H.19: 外部API最適化環境変数
        dynamic "env" {
          for_each = merge(
            var.env_vars,
            {
              # HTTPタイムアウト設定
              "HTTP_TIMEOUT"                = "30"
              "REQUEST_TIMEOUT"             = "30"
              "URLLIB3_TIMEOUT"             = "30"
              
              # キャッシュ設定
              "CACHE_DIR"                   = "/tmp"
              "PYRESHARK_DNS_CACHE_TTL"     = "3600"
              
              # 品質管理設定
              "GRACEFUL_DEGRADATION"        = "true"
              "PARTIAL_DATA_ACCEPTANCE"     = "true"
              "QUALITY_IMPROVEMENT_FACTOR"  = "1.1"
              
              # Python最適化
              "PYTHONUNBUFFERED"           = "1"
              "PYTHONDONTWRITEBYTECODE"    = "1"
              
              # DNS最適化
              "GODEBUG"                    = "netdns=go"
            }
          )
          content {
            name  = env.key
            value = env.value
          }
        }
        
        # ヘルスチェック設定
        startup_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 30
          timeout_seconds       = 10
          period_seconds        = 30
          failure_threshold     = 5
        }
        
        liveness_probe {
          http_get {
            path = "/health"
            port = 8080
          }
          initial_delay_seconds = 60
          timeout_seconds       = 5
          period_seconds        = 60
          failure_threshold     = 3
        }
      }
      
      # Phase H.19: タイムアウト設定（5分）
      timeout_seconds = 300
      
      # 同時実行数（リソース競合回避）
      container_concurrency = 1
    }
    
    # Phase H.19: 最適化メタデータ
    metadata {
      annotations = merge(
        var.service_annotations,
        {
          # オートスケーリング設定
          "autoscaling.knative.dev/minScale"           = "1"    # 最小1インスタンス
          "autoscaling.knative.dev/maxScale"           = "5"    # 最大5インスタンス
          "autoscaling.knative.dev/target"             = "70"   # CPU使用率70%でスケール
          
          # CPU設定
          "run.googleapis.com/cpu-throttling"          = "false" # CPU常時割り当て
          "run.googleapis.com/startup-cpu-boost"       = "true"  # 起動時CPUブースト
          
          # 実行環境
          "run.googleapis.com/execution-environment"   = "gen2"  # 第2世代実行環境
          
          # VPCコネクタ（オプション）
          "run.googleapis.com/vpc-access-connector"    = var.vpc_connector_name
          "run.googleapis.com/vpc-access-egress"       = var.vpc_egress_setting
        }
      )
      
      labels = merge(
        var.service_labels,
        {
          "phase"       = "h19"
          "optimized"   = "true"
          "environment" = var.environment
        }
      )
    }
  }
  
  # トラフィック設定
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  # 自動生成されたURLを無効化（カスタムドメイン使用時）
  autogenerate_revision_name = true
  
  lifecycle {
    create_before_destroy = true
  }
}

# VPCアクセスコネクタ（外部API安定化用）
resource "google_vpc_access_connector" "api_connector" {
  count         = var.enable_vpc_connector ? 1 : 0
  name          = "${var.service_name}-api-connector"
  region        = var.region
  network       = var.vpc_network
  ip_cidr_range = var.vpc_connector_cidr
  
  # スループット設定（外部API用に最適化）
  min_throughput = 200   # 最小200 Mbps
  max_throughput = 1000  # 最大1000 Mbps
  
  # インスタンス設定
  min_instances = 2
  max_instances = 10
}

# Cloud Armorセキュリティポリシー（DDoS対策）
resource "google_compute_security_policy" "api_security_policy" {
  count = var.enable_cloud_armor ? 1 : 0
  name  = "${var.service_name}-api-security-policy"
  
  # レート制限ルール
  rule {
    action   = "throttle"
    priority = "1000"
    
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
    
    description = "Rate limit for API requests"
  }
  
  # デフォルトルール
  rule {
    action   = "allow"
    priority = "2147483647"
    
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    
    description = "Default allow rule"
  }
}

# アラートポリシー（外部API監視）
resource "google_monitoring_alert_policy" "external_api_alerts" {
  count        = var.enable_monitoring ? 1 : 0
  display_name = "${var.service_name} External API Alerts"
  combiner     = "OR"
  
  # 外部API失敗率アラート
  conditions {
    display_name = "External API Failure Rate"
    
    condition_threshold {
      filter          = <<-EOF
        metric.type="run.googleapis.com/request_count"
        AND resource.type="cloud_run_revision"
        AND resource.label.service_name="${var.service_name}"
        AND metric.label.response_code_class="5xx"
      EOF
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  
  # レイテンシアラート
  conditions {
    display_name = "High API Latency"
    
    condition_threshold {
      filter          = <<-EOF
        metric.type="run.googleapis.com/request_latencies"
        AND resource.type="cloud_run_revision"
        AND resource.label.service_name="${var.service_name}"
      EOF
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10000  # 10秒
      
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
        cross_series_reducer = "REDUCE_MEAN"
      }
    }
  }
  
  # メモリ使用率アラート
  conditions {
    display_name = "High Memory Usage"
    
    condition_threshold {
      filter          = <<-EOF
        metric.type="run.googleapis.com/container/memory/utilizations"
        AND resource.type="cloud_run_revision"
        AND resource.label.service_name="${var.service_name}"
      EOF
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85  # 85%
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = var.notification_channels
  
  documentation {
    content = <<-EOF
      ## External API Alert
      
      This alert indicates issues with external API connections.
      
      ### Troubleshooting Steps:
      1. Check Cloud Run logs for specific API errors
      2. Run diagnose-apis command: `python -m crypto_bot.main diagnose-apis`
      3. Verify network connectivity and DNS resolution
      4. Check if external APIs are experiencing outages
      5. Review timeout settings and retry logic
      
      ### Common Issues:
      - Timeout errors: Increase timeout settings
      - DNS resolution: Check VPC connector configuration
      - Memory issues: Scale up memory allocation
      - Rate limiting: Implement backoff strategies
    EOF
    mime_type = "text/markdown"
  }
}

# 出力値
output "optimized_service_url" {
  value       = var.enable_external_api_optimization ? google_cloud_run_service.crypto_bot_optimized[0].status[0].url : null
  description = "最適化されたCloud RunサービスのURL"
}

output "vpc_connector_id" {
  value       = var.enable_vpc_connector ? google_vpc_access_connector.api_connector[0].id : null
  description = "VPCアクセスコネクタのID"
}

output "monitoring_dashboard_url" {
  value       = var.enable_monitoring ? "https://console.cloud.google.com/monitoring/dashboards/custom/${var.project_id}" : null
  description = "Cloud Monitoringダッシュボードへのリンク"
}