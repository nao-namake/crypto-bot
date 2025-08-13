# =============================================================================
# ログベースメトリクス定義
# Google Cloud Monitoringのアラートポリシーで使用するメトリクス
# =============================================================================

# 取引エラーログメトリクス
resource "google_logging_metric" "trade_errors" {
  name    = "crypto_bot_trade_errors"
  project = var.project_id
  filter  = "resource.type=\"cloud_run_revision\" AND textPayload:\"TRADE_ERROR\" AND resource.labels.service_name=\"${var.service_name}\""
  
  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Trade Execution Errors"
    labels {
      key         = "service_name"
      value_type  = "STRING"
      description = "Cloud Run service name"
    }
  }
}

# データ取得成功ログメトリクス
resource "google_logging_metric" "data_fetch_success" {
  name    = "crypto_bot_data_fetch_success"
  project = var.project_id
  filter  = "resource.type=\"cloud_run_revision\" AND (textPayload:\"Progress\" OR textPayload:\"Data fetched\") AND resource.labels.service_name=\"${var.service_name}\""
  
  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Data Fetch Success"
    labels {
      key         = "service_name"
      value_type  = "STRING"
      description = "Cloud Run service name"
    }
  }
}