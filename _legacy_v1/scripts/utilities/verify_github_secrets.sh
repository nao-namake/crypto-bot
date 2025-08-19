#!/bin/bash

###############################################
# scripts/verify_github_secrets.sh
# GitHub Secrets設定確認スクリプト
# Phase 18 CI/CD修正用
###############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 GitHub Secrets 設定確認開始${NC}"

# Required secrets for deployment
REQUIRED_SECRETS=(
    "GCP_PROJECT_ID"
    "GCP_PROJECT_NUMBER"
    "GCP_WIF_PROVIDER"
    "GCP_DEPLOYER_SA"
    "BITBANK_API_KEY"
    "BITBANK_API_SECRET"
)

# Optional secrets (for external APIs - currently disabled)
OPTIONAL_SECRETS=(
    "ALPHA_VANTAGE_API_KEY"
    "POLYGON_API_KEY"
    "FRED_API_KEY"
    "ALERT_EMAIL"
)

echo -e "${YELLOW}📋 必須シークレットの確認:${NC}"
missing_required=0

for secret in "${REQUIRED_SECRETS[@]}"; do
    if gh secret list | grep -q "^$secret"; then
        echo -e "${GREEN}✅ $secret${NC}"
    else
        echo -e "${RED}❌ $secret (未設定)${NC}"
        missing_required=$((missing_required + 1))
    fi
done

echo ""
echo -e "${YELLOW}📋 オプションシークレットの確認:${NC}"

for secret in "${OPTIONAL_SECRETS[@]}"; do
    if gh secret list | grep -q "^$secret"; then
        echo -e "${GREEN}✅ $secret${NC}"
    else
        echo -e "${YELLOW}⚠️  $secret (未設定 - オプション)${NC}"
    fi
done

echo ""
if [ $missing_required -eq 0 ]; then
    echo -e "${GREEN}✅ すべての必須シークレットが設定されています！${NC}"
else
    echo -e "${RED}❌ $missing_required 個の必須シークレットが未設定です${NC}"
    echo ""
    echo -e "${YELLOW}📝 GitHub Secretsの設定方法:${NC}"
    echo ""
    echo "1. GitHubリポジトリの Settings > Secrets and variables > Actions"
    echo "2. 'New repository secret' をクリック"
    echo "3. 以下のコマンドでも設定可能:"
    echo ""
    echo "# .envファイルから自動設定"
    if [ -f ".env" ]; then
        echo "source .env"
        echo "gh secret set BITBANK_API_KEY --body \"\$BITBANK_API_KEY\""
        echo "gh secret set BITBANK_API_SECRET --body \"\$BITBANK_API_SECRET\""
    else
        echo "# 手動設定"
        echo "gh secret set BITBANK_API_KEY"
        echo "gh secret set BITBANK_API_SECRET"
    fi
    echo ""
    echo "# GCP関連のシークレット設定"
    echo "gh secret set GCP_PROJECT_ID --body \"your-project-id\""
    echo "gh secret set GCP_PROJECT_NUMBER --body \"your-project-number\""
    echo "gh secret set GCP_WIF_PROVIDER --body \"projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider\""
    echo "gh secret set GCP_DEPLOYER_SA --body \"github-deployer@PROJECT_ID.iam.gserviceaccount.com\""
fi

echo ""
echo -e "${YELLOW}📊 GitHub Secrets一覧:${NC}"
gh secret list