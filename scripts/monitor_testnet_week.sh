#!/bin/bash
# =============================================================================
# 1週間テストネット監視スクリプト
# =============================================================================

set -euo pipefail

# 設定
SERVICE_NAME="crypto-bot-service-prod"
REGION="asia-northeast1"
SERVICE_URL="https://crypto-bot-service-prod-lufv3saz7q-an.a.run.app"
MONITORING_DURATION="168h"  # 1週間 (7 * 24 時間)
CHECK_INTERVAL="300"        # 5分間隔

# ログファイル
LOG_FILE="testnet_monitoring_$(date +%Y%m%d_%H%M%S).log"
TRADING_LOG="trading_activity_$(date +%Y%m%d_%H%M%S).log"

# 色付きログ出力
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARN: $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE"
}

# ヘルスチェック
check_health() {
    local response
    local status_code
    
    response=$(curl -s -w "%{http_code}" "$SERVICE_URL/health" || echo "000")
    status_code="${response: -3}"
    
    if [[ "$status_code" == "200" ]]; then
        log_info "✅ Health check passed (HTTP $status_code)"
        return 0
    else
        log_error "❌ Health check failed (HTTP $status_code)"
        return 1
    fi
}

# Cloud Runサービス状態確認
check_service_status() {
    local status
    status=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.conditions[0].status)" 2>/dev/null || echo "Unknown")
    
    if [[ "$status" == "True" ]]; then
        log_info "✅ Cloud Run service is ready"
        return 0
    else
        log_error "❌ Cloud Run service status: $status"
        return 1
    fi
}

# トレーディングログ収集
collect_trading_logs() {
    log_info "📊 Collecting trading logs..."
    
    # 過去5分のトレーディング関連ログを取得
    gcloud logging read \
        "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND (textPayload:\"BUY\" OR textPayload:\"SELL\" OR textPayload:\"signal\" OR textPayload:\"profit\" OR textPayload:\"loss\")" \
        --limit=50 \
        --format="value(timestamp,textPayload)" \
        --freshness=5m >> "$TRADING_LOG" 2>/dev/null || true
}

# メトリクス収集
collect_metrics() {
    local uptime
    local memory_usage
    
    log_info "📈 Collecting service metrics..."
    
    # アップタイム確認
    uptime=$(curl -s "$SERVICE_URL/health" | jq -r '.uptime_seconds' 2>/dev/null || echo "unknown")
    
    log_info "Service uptime: ${uptime}s"
    
    # Cloud Run metrics (if available)
    # Note: メトリクス取得には時間がかかる場合があるのでバックグラウンドで実行
    {
        gcloud monitoring metrics list \
            --filter="metric.type:run.googleapis.com/container/memory/utilization" \
            --limit=1 > /dev/null 2>&1 || true
    } &
}

# アラート送信（エラー時）
send_alert() {
    local message="$1"
    log_error "🚨 ALERT: $message"
    
    # 将来的にSlack/Discordなどへの通知を実装可能
    # curl -X POST -H 'Content-type: application/json' \
    #     --data "{\"text\":\"$message\"}" \
    #     "$SLACK_WEBHOOK_URL" || true
}

# メイン監視ループ
main_monitoring_loop() {
    local start_time
    local end_time
    local iteration=0
    
    start_time=$(date +%s)
    end_time=$((start_time + 604800))  # 1週間後
    
    log_info "🚀 Starting 1-week testnet monitoring"
    log_info "Service: $SERVICE_NAME"
    log_info "URL: $SERVICE_URL"
    log_info "Duration: $MONITORING_DURATION"
    log_info "Check interval: ${CHECK_INTERVAL}s"
    
    while [[ $(date +%s) -lt $end_time ]]; do
        iteration=$((iteration + 1))
        local current_time
        current_time=$(date '+%Y-%m-%d %H:%M:%S')
        
        log_info "--- Monitoring iteration #$iteration at $current_time ---"
        
        # ヘルスチェック
        if ! check_health; then
            send_alert "Health check failed at $current_time"
        fi
        
        # サービス状態確認
        if ! check_service_status; then
            send_alert "Service status check failed at $current_time"
        fi
        
        # トレーディングログ収集
        collect_trading_logs
        
        # メトリクス収集
        collect_metrics
        
        # 進捗表示
        local elapsed=$(($(date +%s) - start_time))
        local remaining=$((end_time - $(date +%s)))
        log_info "📊 Elapsed: ${elapsed}s, Remaining: ${remaining}s"
        
        # 待機
        sleep "$CHECK_INTERVAL"
    done
    
    log_info "✅ 1-week monitoring completed successfully!"
}

# エラーハンドリング
trap 'log_error "Script interrupted"; exit 1' INT TERM

# 引数処理
case "${1:-start}" in
    "start")
        main_monitoring_loop
        ;;
    "check")
        log_info "Running one-time health check..."
        check_health && check_service_status
        ;;
    "logs")
        log_info "Collecting recent trading logs..."
        collect_trading_logs
        tail -20 "$TRADING_LOG"
        ;;
    *)
        echo "Usage: $0 [start|check|logs]"
        echo "  start: Start 1-week monitoring (default)"
        echo "  check: One-time health check"
        echo "  logs:  Show recent trading logs"
        exit 1
        ;;
esac