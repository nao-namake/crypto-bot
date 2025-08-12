#!/bin/bash
# =============================================================================
# Deployment Monitoring Script
# Description:
#   - Monitors a Cloud Run service for a specified duration.
#   - Checks health, deployment status, and error logs.
#   - Generates periodic reports.
# Usage:
#   bash scripts/monitor_deployment.sh [duration_hours] [service_name]
# =============================================================================

set -euo pipefail

# --- Configuration ---
PROJECT_ID="my-crypto-bot-project"
REGION="asia-northeast1"
DEFAULT_DURATION_HOURS=48
DEFAULT_SERVICE_NAME="crypto-bot-service-prod"
CHECK_INTERVAL=300 # 5 minutes

# --- Arguments ---
DURATION_HOURS=${1:-$DEFAULT_DURATION_HOURS}
SERVICE_NAME=${2:-$DEFAULT_SERVICE_NAME}
DURATION_SECONDS=$((DURATION_HOURS * 3600))

# --- Log and Report Files ---
LOG_FILE="/tmp/${SERVICE_NAME}_monitor.log"
REPORT_FILE="/tmp/${SERVICE_NAME}_report.txt"

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Functions ---
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

check_service_health() {
    echo "🔍 Checking service health..."
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)" 2>/dev/null || echo "")
    if [[ -z "$SERVICE_URL" ]]; then
        echo -e "${RED}❌ Service not found${NC}"
        return 1
    fi
    if curl -sf "$SERVICE_URL/healthz" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check OK: $SERVICE_URL${NC}"
        return 0
    else
        echo -e "${RED}❌ Health check failed: $SERVICE_URL${NC}"
        return 1
    fi
}

check_error_logs() {
    echo "🔍 Checking for error logs..."
    ERROR_COUNT=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND severity>=ERROR AND timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\"" --limit=50 --format="value(timestamp)" 2>/dev/null | wc -l || echo "0")
    if [[ "$ERROR_COUNT" -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  Found $ERROR_COUNT errors in the last 5 minutes.${NC}"
    else
        echo -e "${GREEN}✅ No recent errors found.${NC}"
    fi
}

# --- Main Execution ---
log_info "Starting deployment monitoring for $SERVICE_NAME."
log_info "Duration: $DURATION_HOURS hours."

START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION_SECONDS))

while [[ $(date +%s) -lt $END_TIME ]]; do
    log_info "--- New monitoring cycle ---"
    check_service_health
    check_error_logs
    
    ELAPSED=$(( $(date +%s) - START_TIME ))
    REMAINING=$(( END_TIME - $(date +%s) ))
    log_info "Elapsed: $((ELAPSED / 3600))h, Remaining: $((REMAINING / 3600))h."
    
    sleep $CHECK_INTERVAL
done

log_info "Monitoring finished."
