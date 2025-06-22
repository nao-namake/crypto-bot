#!/bin/bash
#########################################
# 48時間ペーパートレード監視スクリプト
# Dev環境での連続稼働監視・ログ解析・メトリクス検証
#########################################

set -euo pipefail

echo "🚀 48時間ペーパートレード監視開始"
echo "================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="my-crypto-bot-project"
SERVICE_NAME="crypto-bot-dev"
REGION="asia-northeast1"
LOG_FILE="/tmp/crypto_bot_48h_monitor.log"
REPORT_FILE="/tmp/crypto_bot_48h_report.txt"

# Monitoring start time
START_TIME=$(date +%s)
START_TIME_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "📋 監視開始時刻: $(date)"
echo "📋 プロジェクト: $PROJECT_ID"
echo "📋 サービス: $SERVICE_NAME"
echo "📋 リージョン: $REGION"
echo

# Function: Check if gcloud is authenticated
check_auth() {
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
        echo -e "${RED}❌ Error: Not authenticated with gcloud${NC}"
        echo "Please run: gcloud auth login"
        exit 1
    fi
    echo -e "${GREEN}✅ gcloud認証確認済み${NC}"
}

# Function: Check service health
check_service_health() {
    echo "🔍 サービスヘルスチェック..."
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [[ -z "$SERVICE_URL" ]]; then
        echo -e "${RED}❌ サービスが見つかりません${NC}"
        return 1
    fi
    
    # Test health endpoint
    if curl -sf "$SERVICE_URL/healthz" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ヘルスチェック OK: $SERVICE_URL${NC}"
        return 0
    else
        echo -e "${RED}❌ ヘルスチェック失敗: $SERVICE_URL${NC}"
        return 1
    fi
}

# Function: Get deployment status
check_deployment_status() {
    echo "🔍 デプロイ状況確認..."
    
    # Check if service exists and is ready
    READY_CONDITION=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.conditions[0].status)" 2>/dev/null || echo "Unknown")
    
    if [[ "$READY_CONDITION" == "True" ]]; then
        echo -e "${GREEN}✅ サービス稼働中${NC}"
        
        # Get current revision
        CURRENT_REVISION=$(gcloud run services describe "$SERVICE_NAME" \
            --region="$REGION" \
            --format="value(status.latestReadyRevisionName)" 2>/dev/null || echo "Unknown")
        echo "   現在のリビジョン: $CURRENT_REVISION"
        return 0
    else
        echo -e "${RED}❌ サービス未稼働: $READY_CONDITION${NC}"
        return 1
    fi
}

# Function: Check recent logs for errors
check_error_logs() {
    echo "🔍 エラーログ確認..."
    
    # Get recent error logs
    ERROR_COUNT=$(gcloud logging read "
        resource.type=\"cloud_run_revision\" 
        AND resource.labels.service_name=\"$SERVICE_NAME\"
        AND severity>=ERROR 
        AND timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\"
    " --limit=50 --format="value(timestamp)" 2>/dev/null | wc -l || echo "0")
    
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  直近5分でエラー $ERROR_COUNT 件${NC}"
        
        # Get latest error details
        echo "最新エラー:"
        gcloud logging read "
            resource.type=\"cloud_run_revision\" 
            AND resource.labels.service_name=\"$SERVICE_NAME\"
            AND severity>=ERROR 
            AND timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\"
        " --limit=3 --format="value(timestamp,textPayload)" 2>/dev/null || echo "取得失敗"
    else
        echo -e "${GREEN}✅ 直近5分エラーなし${NC}"
    fi
}

# Function: Check trading metrics
check_trading_metrics() {
    echo "🔍 トレーディングメトリクス確認..."
    
    # Check if trading logs exist
    TRADE_LOG_COUNT=$(gcloud logging read "
        resource.type=\"cloud_run_revision\" 
        AND resource.labels.service_name=\"$SERVICE_NAME\"
        AND (textPayload:\"TRADE\" OR textPayload:\"ORDER\" OR textPayload:\"Position\")
        AND timestamp>=\"$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)\"
    " --limit=100 --format="value(timestamp)" 2>/dev/null | wc -l || echo "0")
    
    if [[ "$TRADE_LOG_COUNT" -gt 0 ]]; then
        echo -e "${GREEN}✅ 直近1時間のトレーディングログ: $TRADE_LOG_COUNT 件${NC}"
    else
        echo -e "${YELLOW}⚠️  直近1時間のトレーディングログなし${NC}"
    fi
}

# Function: Generate monitoring report
generate_report() {
    local current_time=$(date +%s)
    local elapsed_hours=$(( (current_time - START_TIME) / 3600 ))
    local remaining_hours=$(( 48 - elapsed_hours ))
    
    cat > "$REPORT_FILE" << EOF
48時間ペーパートレード監視レポート
================================
開始時刻: $(date -d @$START_TIME '+%Y-%m-%d %H:%M:%S')
現在時刻: $(date '+%Y-%m-%d %H:%M:%S')
経過時間: ${elapsed_hours}時間
残り時間: ${remaining_hours}時間

サービス情報:
- プロジェクト: $PROJECT_ID
- サービス名: $SERVICE_NAME
- リージョン: $REGION

最新チェック結果:
$(check_service_health 2>&1)
$(check_deployment_status 2>&1)
$(check_error_logs 2>&1)
$(check_trading_metrics 2>&1)

=====================================
レポート生成時刻: $(date)
EOF
    
    echo -e "${BLUE}📊 レポート生成: $REPORT_FILE${NC}"
}

# Function: Main monitoring loop
main_monitor() {
    echo "🔄 監視ループ開始 (Ctrl+C で停止)"
    
    while true; do
        echo
        echo "$(date '+%Y-%m-%d %H:%M:%S') - 監視チェック実行中..."
        
        {
            echo "=== $(date) ==="
            check_service_health
            check_deployment_status
            check_error_logs
            check_trading_metrics
            echo
        } >> "$LOG_FILE"
        
        # Generate periodic report
        generate_report
        
        # Sleep for 5 minutes
        sleep 300
    done
}

# Main execution
echo "🔍 初期チェック実行中..."
check_auth

if check_service_health && check_deployment_status; then
    echo -e "${GREEN}✅ 初期チェック完了 - 監視開始準備OK${NC}"
    
    # Create initial log entry
    echo "=== 48時間監視開始: $START_TIME_ISO ===" > "$LOG_FILE"
    
    echo
    echo "💡 監視オプション:"
    echo "   1. 連続監視 (5分間隔): ./scripts/monitor_48h_deployment.sh"
    echo "   2. ワンタイムチェック: ./scripts/monitor_48h_deployment.sh --once"
    echo "   3. レポート生成のみ: ./scripts/monitor_48h_deployment.sh --report"
    echo
    
    # Handle command line arguments
    if [[ "${1:-}" == "--once" ]]; then
        check_error_logs
        check_trading_metrics
        generate_report
        echo -e "${GREEN}✅ ワンタイムチェック完了${NC}"
    elif [[ "${1:-}" == "--report" ]]; then
        generate_report
        cat "$REPORT_FILE"
    else
        main_monitor
    fi
else
    echo -e "${RED}❌ 初期チェック失敗 - サービス状態を確認してください${NC}"
    exit 1
fi