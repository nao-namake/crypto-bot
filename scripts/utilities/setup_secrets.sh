#!/usr/bin/env bash
# =============================================================================
# Secret Manager設定スクリプト - Bitbank API認証情報管理
# Phase 1.3: Secret Manager統合・認証情報設定
# =============================================================================
set -euo pipefail

# プロジェクト設定
PROJECT_ID="crypto-bot-439308"
REGION="asia-northeast1"

echo "=== [Phase 1.3] Secret Manager設定開始 ==="
echo "🔐 プロジェクト: $PROJECT_ID"
echo "🌏 リージョン: $REGION"
echo ""

# GCP認証・プロジェクト設定
echo "=== [Step 1] GCP認証・プロジェクト設定 ==="
gcloud config set project $PROJECT_ID

# Secret Manager API有効化
echo ""
echo "=== [Step 2] Secret Manager API有効化 ==="
echo "🔧 Secret Manager API有効化中..."
gcloud services enable secretmanager.googleapis.com

# 既存シークレット確認
echo ""
echo "=== [Step 3] 既存シークレット確認 ==="
BITBANK_API_KEY_EXISTS=$(gcloud secrets list --filter="name:bitbank-api-key" --format="value(name)" || echo "")
BITBANK_API_SECRET_EXISTS=$(gcloud secrets list --filter="name:bitbank-api-secret" --format="value(name)" || echo "")

if [ -n "$BITBANK_API_KEY_EXISTS" ]; then
    echo "✅ bitbank-api-key 既存確認済み"
else
    echo "⚠️ bitbank-api-key が存在しません"
fi

if [ -n "$BITBANK_API_SECRET_EXISTS" ]; then
    echo "✅ bitbank-api-secret 既存確認済み"
else
    echo "⚠️ bitbank-api-secret が存在しません"
fi

# シークレット作成関数
create_secret() {
    local secret_name=$1
    local secret_description=$2
    
    if gcloud secrets describe "$secret_name" >/dev/null 2>&1; then
        echo "✅ $secret_name 既存確認済み"
    else
        echo "🔐 $secret_name 作成中..."
        gcloud secrets create "$secret_name" \
            --description="$secret_description" \
            --replication-policy="automatic"
        echo "✅ $secret_name 作成完了"
    fi
}

# シークレット作成
echo ""
echo "=== [Step 4] シークレット作成 ==="
create_secret "bitbank-api-key" "Bitbank API Key for live trading"
create_secret "bitbank-api-secret" "Bitbank API Secret for live trading"

# Service Account設定
echo ""
echo "=== [Step 5] Service Account権限設定 ==="
SERVICE_ACCOUNT="github-deployer@$PROJECT_ID.iam.gserviceaccount.com"

echo "🔑 Service Account: $SERVICE_ACCOUNT"
echo "🔧 Secret Manager権限設定中..."

# Secret Manager権限付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor" \
    --condition=None

echo "✅ Secret Manager権限設定完了"

# Cloud Run Service Identity設定
echo ""
echo "=== [Step 6] Cloud Run Service Identity設定 ==="
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
CLOUD_RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "🔑 Cloud Run Service Account: $CLOUD_RUN_SA"
echo "🔧 Secret Manager権限設定中..."

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CLOUD_RUN_SA" \
    --role="roles/secretmanager.secretAccessor"

echo "✅ Cloud Run Service Identity設定完了"

# 設定確認
echo ""
echo "=== [Step 7] 設定確認 ==="
echo "📋 作成されたシークレット一覧:"
gcloud secrets list --filter="name:bitbank-" --format="table(name,createTime)"

echo ""
echo "📋 IAM権限確認:"
gcloud projects get-iam-policy $PROJECT_ID \
    --filter="bindings.members:serviceAccount:$SERVICE_ACCOUNT" \
    --format="table(bindings.role,bindings.members)" \
    --flatten="bindings[].members"

# 使用方法説明
echo ""
echo "=== [Phase 1.3] Secret Manager設定完了 ==="
echo "📊 設定内容:"
echo "  ✅ Secret Manager API有効化完了"
echo "  ✅ bitbank-api-key シークレット作成完了"
echo "  ✅ bitbank-api-secret シークレット作成完了"
echo "  ✅ Service Account権限設定完了"
echo "  ✅ Cloud Run Service Identity設定完了"
echo ""
echo "🔧 Cloud Runデプロイ時の使用方法:"
echo "  --set-secrets=BITBANK_API_KEY=bitbank-api-key:latest"
echo "  --set-secrets=BITBANK_API_SECRET=bitbank-api-secret:latest"
echo ""
echo "⚠️ 注意: 実際のAPIキー・シークレットは手動で設定してください"
echo "   gcloud secrets versions add bitbank-api-key --data-file=api_key.txt"
echo "   gcloud secrets versions add bitbank-api-secret --data-file=api_secret.txt"
echo ""
echo "📋 次のステップ: Phase 2.1 - API-onlyモードフォールバック削除"