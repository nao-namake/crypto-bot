#!/bin/bash
#########################################
# WIF Hardening Verification Script
# Verifies Workload Identity Federation security configuration
#########################################

set -euo pipefail

echo "🔒 Workload Identity Federation Hardening Verification"
echo "======================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo -e "${RED}❌ Error: Not authenticated with gcloud${NC}"
    echo "Please run: gcloud auth login"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null || echo "")
if [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}❌ Error: No GCP project set${NC}"
    echo "Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo -e "${YELLOW}📋 Project: $PROJECT_ID${NC}"
echo

# Verify WIF Pool exists
echo "🔍 Checking Workload Identity Pool..."
if gcloud iam workload-identity-pools describe github-pool --location=global --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${GREEN}✅ WIF Pool exists${NC}"
else
    echo -e "${RED}❌ WIF Pool not found${NC}"
    exit 1
fi

# Verify WIF Provider and attribute conditions
echo "🔍 Checking OIDC Provider configuration..."
PROVIDER_CONFIG=$(gcloud iam workload-identity-pools providers describe github-provider \
    --workload-identity-pool=github-pool \
    --location=global \
    --project="$PROJECT_ID" \
    --format="value(attributeCondition)")

EXPECTED_CONDITION='attribute.repository == "nao-namake/crypto-bot" && attribute.ref == "refs/heads/main"'

if [[ "$PROVIDER_CONFIG" == "$EXPECTED_CONDITION" ]]; then
    echo -e "${GREEN}✅ OIDC attribute condition correctly hardened${NC}"
else
    echo -e "${RED}❌ OIDC attribute condition not properly configured${NC}"
    echo "Expected: $EXPECTED_CONDITION"
    echo "Actual: $PROVIDER_CONFIG"
fi

# Verify Service Account permissions
echo "🔍 Checking GitHub Deployer Service Account permissions..."

SA_EMAIL="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

# Expected minimal permissions
EXPECTED_ROLES=(
    "roles/run.admin"
    "roles/artifactregistry.admin"
    "roles/monitoring.admin"
    "roles/serviceusage.serviceUsageAdmin"
    "roles/secretmanager.admin"
    "roles/storage.objectAdmin"
    "roles/iam.serviceAccountUser"
    "roles/iam.securityReviewer"
)

# Get current roles
CURRENT_ROLES=$(gcloud projects get-iam-policy "$PROJECT_ID" \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:$SA_EMAIL" \
    --format="value(bindings.role)" | sort)

echo "Current roles assigned to $SA_EMAIL:"
for role in $CURRENT_ROLES; do
    if [[ " ${EXPECTED_ROLES[*]} " =~ " ${role} " ]]; then
        echo -e "${GREEN}  ✅ $role${NC}"
    else
        echo -e "${YELLOW}  ⚠️  $role (unexpected)${NC}"
    fi
done

# Check for missing expected roles
echo
echo "Verifying all expected roles are present:"
for expected_role in "${EXPECTED_ROLES[@]}"; do
    if echo "$CURRENT_ROLES" | grep -q "$expected_role"; then
        echo -e "${GREEN}  ✅ $expected_role${NC}"
    else
        echo -e "${RED}  ❌ $expected_role (missing)${NC}"
    fi
done

# Verify WIF binding
echo
echo "🔍 Checking Workload Identity binding..."
WIF_BINDING=$(gcloud iam service-accounts get-iam-policy "$SA_EMAIL" \
    --filter="bindings.members:principalSet*" \
    --format="value(bindings.members)" 2>/dev/null || echo "")

EXPECTED_PRINCIPAL="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/github-pool/attribute.repository/nao-namake/crypto-bot"

if [[ "$WIF_BINDING" == "$EXPECTED_PRINCIPAL" ]]; then
    echo -e "${GREEN}✅ WIF binding correctly configured${NC}"
else
    echo -e "${RED}❌ WIF binding not properly configured${NC}"
    echo "Expected: $EXPECTED_PRINCIPAL"
    echo "Actual: $WIF_BINDING"
fi

echo
echo "🔒 WIF Hardening Verification Complete"
echo "======================================"