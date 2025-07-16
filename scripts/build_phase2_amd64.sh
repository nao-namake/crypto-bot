#!/usr/bin/env bash
# =============================================================================
# Phase 2 ATR修正システム - AMD64イメージビルド・デプロイスクリプト
# Terminal 1専用: メインデプロイメント作業
# =============================================================================
set -euo pipefail

# プロジェクト設定
PROJECT_ID="crypto-bot-439308"
REGION="asia-northeast1"
REPOSITORY="crypto-bot-repo"
IMAGE_NAME="crypto-bot"
IMAGE_TAG="phase2-amd64-$(date +%s)"
SERVICE_NAME="crypto-bot-service-phase2"

echo "=== [Terminal 1] Phase 2 ATR修正システム AMD64ビルド開始 ==="
echo "🎯 プロジェクト: $PROJECT_ID"
echo "🌏 リージョン: $REGION"
echo "📦 イメージ: $IMAGE_NAME:$IMAGE_TAG"
echo "🚀 サービス: $SERVICE_NAME"

# Docker Buildx設定（AMD64プラットフォーム対応）
echo ""
echo "=== [INIT-1] Docker Buildx設定 ==="
docker buildx create --use --name phase2-builder || true
docker buildx inspect --bootstrap

# GCPプロジェクト設定
echo ""
echo "=== [INIT-2] GCPプロジェクト設定確認 ==="
gcloud config set project $PROJECT_ID
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# Artifact Repository確認・作成
echo ""
echo "=== [INIT-3] Artifact Registry確認 ==="
if ! gcloud artifacts repositories describe $REPOSITORY --location=$REGION --format="value(name)" 2>/dev/null; then
    echo "📦 Artifact Registry作成中..."
    gcloud artifacts repositories create $REPOSITORY \
        --repository-format=docker \
        --location=$REGION \
        --description="Phase 2 ATR修正システム用Dockerリポジトリ"
else
    echo "✅ Artifact Registry存在確認済み"
fi

# AMD64プラットフォーム指定ビルド
echo ""
echo "=== [INIT-4] AMD64イメージビルド実行 ==="
FULL_IMAGE_NAME="asia-northeast1-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG"

docker buildx build \
    --platform linux/amd64 \
    --push \
    --tag "$FULL_IMAGE_NAME" \
    --tag "asia-northeast1-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:latest" \
    --cache-from type=gha \
    --cache-to type=gha,mode=max \
    .

echo "✅ [INIT-4] AMD64イメージビルド完了: $FULL_IMAGE_NAME"

# Cloud Run新サービスデプロイ
echo ""
echo "=== [INIT-5] Cloud Run新サービスデプロイ実行 ==="
gcloud run deploy $SERVICE_NAME \
    --image "$FULL_IMAGE_NAME" \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="MODE=live,EXCHANGE=bitbank" \
    --memory=1Gi \
    --cpu=1000m \
    --min-instances=0 \
    --max-instances=10 \
    --timeout=3600

echo ""
echo "=== [INIT-6] デプロイ完了・サービスURL取得 ==="
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo "🌐 新サービスURL: $SERVICE_URL"

# 基本ヘルスチェック
echo ""
echo "=== [INIT-7] 基本ヘルスチェック実行 ==="
echo "⏰ 30秒待機（サービス起動待ち）..."
sleep 30

echo "🏥 ヘルスチェック実行: $SERVICE_URL/health"
if curl -f "$SERVICE_URL/health"; then
    echo ""
    echo "✅ [INIT-7] 基本ヘルスチェック成功"
else
    echo ""
    echo "❌ [INIT-7] 基本ヘルスチェック失敗"
    exit 1
fi

echo ""
echo "=== [Terminal 1] Task A完了: AMD64イメージデプロイ成功 ==="
echo "📋 次のステップ: Terminal 3でのヘルスチェック・検証待ち"
echo "🎯 サービス名: $SERVICE_NAME"
echo "🌐 URL: $SERVICE_URL"
echo "📦 イメージ: $FULL_IMAGE_NAME"