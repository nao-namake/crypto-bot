# Discord通知用Pub/Sub通知チャンネル
resource "google_monitoring_notification_channel" "discord" {
  project      = var.project_id
  display_name = "Crypto-Bot Discord Alert"
  type         = "pubsub"
  labels       = { 
    topic = google_pubsub_topic.alert_notifications.id
  }
  
  depends_on = [
    google_pubsub_topic.alert_notifications,
    var.discord_permissions_ready  # IAM権限伝播完了まで待機
  ]
}

# 高レイテンシアラート（削除：頻発しがちで実用性低い）
# 必要時のみコメントアウトを外す
# resource "google_monitoring_alert_policy" "latency" {
#   project                = var.project_id
#   display_name           = "High request latency"
#   combiner               = "OR"
#   notification_channels  = [google_monitoring_notification_channel.discord.id]
#
#   conditions {
#     display_name = "Latency > 5s"  # 閾値を3s→5sに引き上げ
#     condition_threshold {
#       filter          = "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\""
#       comparison      = "COMPARISON_GT"
#       threshold_value = 5
#       duration        = "300s"  # 3分→5分に延長
#       aggregations {
#         alignment_period   = "60s"
#         per_series_aligner = "ALIGN_PERCENTILE_99"
#       }
#     }
#   }
# }

resource "google_monitoring_alert_policy" "pnl_loss" {
  project                = var.project_id
  display_name           = "Crypto Bot Loss Alert"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.discord.id]

  conditions {
    display_name = "PnL < -10000 JPY"  # -5000円→-10000円に引き上げ（より重要な損失のみ通知）
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/crypto_bot/pnl\" resource.type=\"global\""
      comparison      = "COMPARISON_LT"
      threshold_value = -10000
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  documentation {
    content = "取引で10,000円以上の損失が発生しました。リスク管理設定を確認してください。"
  }
}

resource "google_monitoring_alert_policy" "error_rate" {
  project                = var.project_id
  display_name           = "High error rate"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.discord.id]

  conditions {
    display_name = "5xx error rate > 10%"  # 5%→10%に引き上げ（より重要なエラーのみ）
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.label.response_code_class=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.10
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  documentation {
    content = "システムエラー率が10%を超えています。サーバーの状態を確認してください。"
  }
}

# 🆕 取引実行失敗アラート（ログベース・最重要）
resource "google_monitoring_alert_policy" "trade_execution_failure" {
  project                = var.project_id
  display_name           = "Trade Execution Failure Alert"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.discord.id]

  conditions {
    display_name = "取引実行エラーログ検出"
    condition_threshold {
      # ログベースメトリクスを参照
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.trade_errors.name}\" resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_GT"
      threshold_value = 3  # 5分間で3回エラーログがあればアラート
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  documentation {
    content = "🚨 **最重要**: 取引実行エラーが検出されました。ログを確認してAPI認証・残高・システム状態をチェックしてください。"
  }

  depends_on = [time_sleep.wait_for_metrics_propagation]
}

# 🆕 システム停止アラート
resource "google_monitoring_alert_policy" "system_down" {
  project                = var.project_id
  display_name           = "System Health Check Failure"
  notification_channels  = [google_monitoring_notification_channel.discord.id]

  conditions {
    display_name = "ヘルスチェック失敗"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\" metric.label.response_code!=\"200\" resource.labels.service_name=\"${var.service_name}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 3
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  conditions {
    display_name = "インスタンス数ゼロ"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/container/instance_count\" resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.service_name}\""
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      duration        = "120s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  combiner = "AND"  # すべての条件が満たされた場合のみアラート

  documentation {
    content = "🚨 **システム停止**: crypto-botが応答しません。Cloud Runの状態・ログを確認してください。"
  }
}

# 🆕 メモリ使用率異常アラート  
resource "google_monitoring_alert_policy" "memory_usage" {
  project                = var.project_id
  display_name           = "High Memory Usage Alert"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.discord.id]

  conditions {
    display_name = "メモリ使用率 > 85%"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/container/memory/utilizations\" resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${var.service_name}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85
      duration        = "300s"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_PERCENTILE_99"  # DISTRIBUTION型メトリクスと互換性のあるaligner
      }
    }
  }

  documentation {
    content = "⚠️ **メモリ不足警告**: メモリ使用率が85%を超えています。OOMキラーによる強制終了リスクがあります。"
  }
}

# 🆕 データ取得停止アラート（ログベース）
resource "google_monitoring_alert_policy" "data_fetch_failure" {
  project                = var.project_id
  display_name           = "Market Data Fetch Failure"
  combiner               = "OR"
  notification_channels  = [google_monitoring_notification_channel.discord.id]

  conditions {
    display_name = "データ取得ログが10分間なし"
    condition_threshold {
      # ログベースメトリクスを参照
      filter          = "metric.type=\"logging.googleapis.com/user/${google_logging_metric.data_fetch_success.name}\" resource.type=\"cloud_run_revision\""
      comparison      = "COMPARISON_LT"
      threshold_value = 1  # 10分間で1回もデータ取得ログがなければアラート
      duration        = "600s"  # 10分
      aggregations {
        alignment_period   = "300s"  # 5分間隔でチェック
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  documentation {
    content = "🚨 **データ取得停止**: 10分以上市場データ取得ログが確認できません。Bitbank API・ネットワーク接続・システム状態を確認してください。"
  }

  depends_on = [time_sleep.wait_for_metrics_propagation]
}
