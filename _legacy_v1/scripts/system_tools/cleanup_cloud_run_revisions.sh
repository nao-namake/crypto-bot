#!/bin/bash

###############################################
# scripts/cleanup_cloud_run_revisions.sh
# Cloud Run リビジョン競合解決スクリプト
# Phase 18 CI/CD修正用
###############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧹 Cloud Run リビジョンクリーンアップ開始${NC}"

# Default values
SERVICE_NAME="${SERVICE_NAME:-crypto-bot-service-prod}"
REGION="${REGION:-asia-northeast1}"

# Check if required environment variables are set
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}❌ GCP_PROJECT_ID が設定されていません${NC}"
    echo "export GCP_PROJECT_ID=your-project-id を実行してください"
    exit 1
fi

echo -e "${YELLOW}📋 Service: $SERVICE_NAME${NC}"
echo -e "${YELLOW}📋 Region: $REGION${NC}"
echo -e "${YELLOW}📋 Project: $GCP_PROJECT_ID${NC}"

# List all revisions
echo -e "${YELLOW}📋 現在のリビジョン一覧:${NC}"
gcloud run revisions list \
    --service=$SERVICE_NAME \
    --region=$REGION \
    --project=$GCP_PROJECT_ID \
    --format="table(name,status,traffic.percent,createTime)" || {
    echo -e "${RED}❌ サービスが見つかりません: $SERVICE_NAME${NC}"
    exit 1
}

# Get the problematic revision
PROBLEM_REVISION="crypto-bot-service-prod-00025-zex"

# Check if the problematic revision exists
if gcloud run revisions describe $PROBLEM_REVISION \
    --region=$REGION \
    --project=$GCP_PROJECT_ID &>/dev/null; then
    
    echo -e "${YELLOW}⚠️  問題のリビジョンが見つかりました: $PROBLEM_REVISION${NC}"
    
    # Check if it has traffic
    TRAFFIC=$(gcloud run revisions describe $PROBLEM_REVISION \
        --region=$REGION \
        --project=$GCP_PROJECT_ID \
        --format="value(traffic.percent)" 2>/dev/null || echo "0")
    
    if [ "$TRAFFIC" != "0" ] && [ -n "$TRAFFIC" ]; then
        echo -e "${YELLOW}🚦 トラフィックを削除中...${NC}"
        gcloud run services update-traffic $SERVICE_NAME \
            --region=$REGION \
            --project=$GCP_PROJECT_ID \
            --remove=$PROBLEM_REVISION
    fi
    
    echo -e "${RED}🗑️  リビジョンを削除中: $PROBLEM_REVISION${NC}"
    gcloud run revisions delete $PROBLEM_REVISION \
        --region=$REGION \
        --project=$GCP_PROJECT_ID \
        --quiet
    
    echo -e "${GREEN}✅ リビジョン削除完了${NC}"
else
    echo -e "${GREEN}✅ 問題のリビジョンは存在しません${NC}"
fi

# Clean up old revisions (keep only latest 5)
echo -e "${YELLOW}🧹 古いリビジョンをクリーンアップ中...${NC}"

# Get list of revisions sorted by creation time (newest first)
REVISIONS=$(gcloud run revisions list \
    --service=$SERVICE_NAME \
    --region=$REGION \
    --project=$GCP_PROJECT_ID \
    --format="value(name)" \
    --sort-by="~createTime" 2>/dev/null || echo "")

if [ -n "$REVISIONS" ]; then
    # Convert to array
    REVISION_ARRAY=($REVISIONS)
    TOTAL_REVISIONS=${#REVISION_ARRAY[@]}
    
    if [ $TOTAL_REVISIONS -gt 5 ]; then
        echo -e "${YELLOW}📋 合計リビジョン数: $TOTAL_REVISIONS (5個を超えています)${NC}"
        
        # Delete revisions beyond the 5th
        for i in $(seq 5 $((TOTAL_REVISIONS - 1))); do
            REVISION_TO_DELETE=${REVISION_ARRAY[$i]}
            
            # Check if revision has traffic
            TRAFFIC=$(gcloud run revisions describe $REVISION_TO_DELETE \
                --region=$REGION \
                --project=$GCP_PROJECT_ID \
                --format="value(traffic.percent)" 2>/dev/null || echo "0")
            
            if [ "$TRAFFIC" == "0" ] || [ -z "$TRAFFIC" ]; then
                echo -e "${YELLOW}🗑️  削除中: $REVISION_TO_DELETE${NC}"
                gcloud run revisions delete $REVISION_TO_DELETE \
                    --region=$REGION \
                    --project=$GCP_PROJECT_ID \
                    --quiet || echo -e "${RED}⚠️  削除失敗: $REVISION_TO_DELETE${NC}"
            else
                echo -e "${YELLOW}⏭️  スキップ (トラフィックあり): $REVISION_TO_DELETE ($TRAFFIC%)${NC}"
            fi
        done
    else
        echo -e "${GREEN}✅ リビジョン数は適切です ($TOTAL_REVISIONS/5)${NC}"
    fi
fi

# Show final state
echo -e "${GREEN}📋 最終的なリビジョン状態:${NC}"
gcloud run revisions list \
    --service=$SERVICE_NAME \
    --region=$REGION \
    --project=$GCP_PROJECT_ID \
    --format="table(name,status,traffic.percent,createTime)"

echo -e "${GREEN}✅ Cloud Run リビジョンクリーンアップ完了！${NC}"
echo -e "${GREEN}🚀 CI/CDパイプラインを再実行してください${NC}"