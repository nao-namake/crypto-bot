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
  }
}

# =============================================================================
# メトリクス伝播待機
# Google Cloudでメトリクスが利用可能になるまで最大10分かかるため待機
# =============================================================================

resource "time_sleep" "wait_for_metrics_propagation" {
  depends_on = [
    google_logging_metric.trade_errors,
    google_logging_metric.data_fetch_success
  ]
  
  create_duration = "60s"  # 初期値60秒、必要に応じて調整可能
}