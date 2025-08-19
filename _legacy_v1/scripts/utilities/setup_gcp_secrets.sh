#!/bin/bash

###############################################
# scripts/setup_gcp_secrets.sh
# GCP Secret Managerへのシークレット作成スクリプト
# Phase 18 CI/CD修正用
###############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 GCP Secret Manager セットアップ開始${NC}"

# Check if required environment variables are set
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}❌ GCP_PROJECT_ID が設定されていません${NC}"
    echo "export GCP_PROJECT_ID=your-project-id を実行してください"
    exit 1
fi

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
    echo -e "${RED}❌ gcloud認証が必要です${NC}"
    echo "gcloud auth login を実行してください"
    exit 1
fi

echo -e "${YELLOW}📋 Project ID: $GCP_PROJECT_ID${NC}"

# Enable Secret Manager API if not already enabled
echo -e "${YELLOW}🔧 Secret Manager APIを有効化中...${NC}"
gcloud services enable secretmanager.googleapis.com --project=$GCP_PROJECT_ID || true

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if gcloud secrets describe $secret_name --project=$GCP_PROJECT_ID &>/dev/null; then
        echo -e "${YELLOW}📝 既存のシークレット '$secret_name' を更新中...${NC}"
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=- --project=$GCP_PROJECT_ID
    else
        echo -e "${GREEN}✨ 新規シークレット '$secret_name' を作成中...${NC}"
        echo -n "$secret_value" | gcloud secrets create $secret_name --data-file=- --project=$GCP_PROJECT_ID
    fi
}

# Create Bitbank API secrets
if [ -n "$BITBANK_API_KEY" ] && [ -n "$BITBANK_API_SECRET" ]; then
    echo -e "${GREEN}🔐 Bitbank APIシークレットを作成中...${NC}"
    create_or_update_secret "bitbank-api-key" "$BITBANK_API_KEY"
    create_or_update_secret "bitbank-api-secret" "$BITBANK_API_SECRET"
else
    echo -e "${YELLOW}⚠️  BITBANK_API_KEY または BITBANK_API_SECRET が環境変数に設定されていません${NC}"
    echo "手動で入力する場合は以下のコマンドを使用してください:"
    echo ""
    echo "# Bitbank API Key"
    echo "echo -n 'your-api-key' | gcloud secrets create bitbank-api-key --data-file=- --project=$GCP_PROJECT_ID"
    echo ""
    echo "# Bitbank API Secret"
    echo "echo -n 'your-api-secret' | gcloud secrets create bitbank-api-secret --data-file=- --project=$GCP_PROJECT_ID"
fi

# Grant access to Cloud Run service account
echo -e "${YELLOW}🔑 Cloud Runサービスアカウントにアクセス権限を付与中...${NC}"

# Get project number
PROJECT_NUMBER=$(gcloud projects describe $GCP_PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo -e "${YELLOW}📋 Service Account: $SERVICE_ACCOUNT${NC}"

# Grant access to secrets
for secret in bitbank-api-key bitbank-api-secret; do
    if gcloud secrets describe $secret --project=$GCP_PROJECT_ID &>/dev/null; then
        echo -e "${GREEN}✅ '$secret' へのアクセス権限を付与中...${NC}"
        gcloud secrets add-iam-policy-binding $secret \
            --member="serviceAccount:${SERVICE_ACCOUNT}" \
            --role="roles/secretmanager.secretAccessor" \
            --project=$GCP_PROJECT_ID
    fi
done

echo -e "${GREEN}✅ Secret Manager セットアップ完了！${NC}"

# List created secrets
echo -e "${YELLOW}📋 作成されたシークレット:${NC}"
gcloud secrets list --project=$GCP_PROJECT_ID --filter="name:(bitbank-api-key OR bitbank-api-secret)" --format="table(name,createTime)"

echo -e "${GREEN}🚀 CI/CDパイプラインを再実行してください${NC}"