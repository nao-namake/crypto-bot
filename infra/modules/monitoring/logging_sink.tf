# =============================================================================
# Cloud Logging Sink の定義
# Cloud Run のログを BigQuery に転送するための設定
# =============================================================================

# BigQuery データセット（既存リソースを参照）
data "google_bigquery_dataset" "crypto_bot_logs" {
  dataset_id = replace("${var.service_name}_logs", "-", "_")
  project    = var.project_id
}

# Logging Sink の作成
resource "google_logging_project_sink" "crypto_bot_bq_sink" {
  name = "${var.service_name}_bq_sink"
  
  # Cloud Run のログのみをフィルタリング
  filter = <<-EOT
    resource.type="cloud_run_revision"
    resource.labels.service_name="${var.service_name}"
  EOT

  # BigQuery データセットを宛先に設定
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${data.google_bigquery_dataset.crypto_bot_logs.dataset_id}"

  # ログの取り込み制御
  unique_writer_identity = true
}

# Logging Sink に BigQuery への書き込み権限を付与
resource "google_bigquery_dataset_iam_member" "log_sink_writer" {
  dataset_id = data.google_bigquery_dataset.crypto_bot_logs.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = google_logging_project_sink.crypto_bot_bq_sink.writer_identity
}

# ログ分析用の BigQuery ビュー作成（ログテーブルが作成された後に作成されるようignore_changes設定）
# TODO: サービス稼働後にログテーブルが作成されたら有効化
# resource "google_bigquery_table" "error_logs_view" {
#   dataset_id = data.google_bigquery_dataset.crypto_bot_logs.dataset_id
#   table_id   = "error_logs_view"

#   view {
#     query = <<-EOT
#       SELECT 
#         timestamp,
#         severity,
#         textPayload,
#         resource.labels.service_name,
#         resource.labels.revision_name,
#         CASE 
#           WHEN textPayload LIKE '%ConnectionError%' THEN 'Connection Issue'
#           WHEN textPayload LIKE '%timeout%' THEN 'Timeout'
#           WHEN textPayload LIKE '%authentication%' THEN 'Auth Error'
#           WHEN textPayload LIKE '%rate limit%' THEN 'Rate Limit'
#           WHEN textPayload LIKE '%insufficient%' THEN 'Insufficient Balance'
#           ELSE 'Other Error'
#         END as error_category
#       FROM `${var.project_id}.${data.google_bigquery_dataset.crypto_bot_logs.dataset_id}.run_googleapis_com_stderr_*`
#       WHERE severity >= 'ERROR'
#         AND DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
#       ORDER BY timestamp DESC
#     EOT
#     use_legacy_sql = false
#   }

#   lifecycle {
#     ignore_changes = [view[0].query]
#   }

#   depends_on = [google_bigquery_dataset_iam_member.log_sink_writer]
# }

# 性能分析用ビュー（ログテーブルが作成された後に作成されるようignore_changes設定）
# TODO: サービス稼働後にログテーブルが作成されたら有効化
# resource "google_bigquery_table" "performance_view" {
#   dataset_id = data.google_bigquery_dataset.crypto_bot_logs.dataset_id
#   table_id   = "performance_view"

#   view {
#     query = <<-EOT
#       WITH latency_stats AS (
#         SELECT 
#           DATE(timestamp) as date,
#           EXTRACT(HOUR FROM timestamp) as hour,
#           httpRequest.status,
#           EXTRACT(EPOCH FROM CAST(httpRequest.latency AS INTERVAL)) as latency_seconds
#         FROM `${var.project_id}.${data.google_bigquery_dataset.crypto_bot_logs.dataset_id}.run_googleapis_com_requests_*`
#         WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
#           AND httpRequest.latency IS NOT NULL
#           AND httpRequest.requestUrl NOT LIKE '%/healthz%'
#       )
#       SELECT 
#         date,
#         hour,
#         httpRequest.status,
#         COUNT(*) as request_count,
#         ROUND(APPROX_QUANTILES(latency_seconds, 100)[OFFSET(50)], 3) as p50_latency,
#         ROUND(APPROX_QUANTILES(latency_seconds, 100)[OFFSET(95)], 3) as p95_latency,
#         ROUND(APPROX_QUANTILES(latency_seconds, 100)[OFFSET(99)], 3) as p99_latency,
#         ROUND(AVG(latency_seconds), 3) as avg_latency
#       FROM latency_stats
#       GROUP BY date, hour, httpRequest.status
#       ORDER BY date DESC, hour DESC
#     EOT
#     use_legacy_sql = false
#   }

#   lifecycle {
#     ignore_changes = [view[0].query]
#   }

#   depends_on = [google_bigquery_dataset_iam_member.log_sink_writer]
# }