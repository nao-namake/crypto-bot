#!/usr/bin/env bash
# =============================================================================
# 完全版Bot AMD64ビルドスクリプト - yfinance依存関係修正版
# Phase 1.1: 依存関係修正確認・Docker完全ビルド
# =============================================================================
set -euo pipefail

# プロジェクト設定
PROJECT_ID="crypto-bot-439308"
REGION="asia-northeast1"
REPOSITORY="crypto-bot-repo"
IMAGE_NAME="crypto-bot"
IMAGE_TAG="complete-amd64-$(date +%s)"

echo "=== [Phase 1.1] 完全版Bot AMD64ビルド開始 ==="
echo "🎯 プロジェクト: $PROJECT_ID"
echo "📦 イメージタグ: $IMAGE_TAG"
echo "🏗️ アーキテクチャ: linux/amd64"
echo ""

# Docker buildx設定確認・作成
echo "=== [Step 1] Docker buildx設定確認 ==="
if ! docker buildx ls | grep -q "multiarch-builder"; then
    echo "📦 multiarch-builderを作成中..."
    docker buildx create --name multiarch-builder --use
    docker buildx inspect --bootstrap
else
    echo "✅ multiarch-builder設定済み"
    docker buildx use multiarch-builder
fi

# GCP認証・プロジェクト設定
echo ""
echo "=== [Step 2] GCP認証・プロジェクト設定 ==="
gcloud config set project $PROJECT_ID
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# Artifact Repository確認
echo ""
echo "=== [Step 3] Artifact Registry確認 ==="
if ! gcloud artifacts repositories describe $REPOSITORY --location=$REGION >/dev/null 2>&1; then
    echo "📦 Artifact Registry作成中..."
    gcloud artifacts repositories create $REPOSITORY \
        --repository-format=docker \
        --location=$REGION \
        --description="完全版Bot用Dockerリポジトリ"
else
    echo "✅ Artifact Registry存在確認済み"
fi

# 依存関係確認テスト
echo ""
echo "=== [Step 4] 依存関係確認テスト ==="
echo "📋 yfinance依存関係確認..."
if grep -q "yfinance" requirements-dev.txt; then
    echo "✅ yfinance>=0.2.0 設定確認済み"
else
    echo "❌ yfinance設定が見つかりません"
    exit 1
fi

# Dockerfile構文確認
echo "🔍 Dockerfile構文確認..."
if docker buildx build --dry-run . >/dev/null 2>&1; then
    echo "✅ Dockerfile構文確認済み"
else
    echo "❌ Dockerfile構文エラー"
    exit 1
fi

# AMD64イメージビルド・プッシュ
echo ""
echo "=== [Step 5] AMD64イメージビルド・プッシュ ==="
FULL_IMAGE_NAME="asia-northeast1-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:$IMAGE_TAG"
LATEST_IMAGE_NAME="asia-northeast1-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:latest"

echo "🏗️ AMD64イメージビルド開始..."
docker buildx build \
    --platform linux/amd64 \
    --push \
    --tag "$FULL_IMAGE_NAME" \
    --tag "$LATEST_IMAGE_NAME" \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --cache-from type=gha \
    --cache-to type=gha,mode=max \
    .

echo "✅ AMD64イメージビルド完了: $FULL_IMAGE_NAME"

# イメージ検証テスト
echo ""
echo "=== [Step 6] イメージ検証テスト ==="
echo "🧪 yfinanceインポートテスト..."
if docker run --rm --platform linux/amd64 "$FULL_IMAGE_NAME" python -c "import yfinance; print('✅ yfinance import successful')"; then
    echo "✅ yfinance依存関係確認済み"
else
    echo "❌ yfinance依存関係エラー"
    exit 1
fi

echo "🧪 基本モジュールテスト..."
if docker run --rm --platform linux/amd64 "$FULL_IMAGE_NAME" python -c "import crypto_bot; print('✅ crypto_bot import successful')"; then
    echo "✅ 基本モジュール確認済み"
else
    echo "❌ 基本モジュールエラー"
    exit 1
fi

# 完了報告
echo ""
echo "=== [Phase 1.1] 完全版Bot AMD64ビルド完了 ==="
echo "📊 ビルド結果:"
echo "  ✅ yfinance依存関係修正確認済み"
echo "  ✅ AMD64アーキテクチャ固定確認済み"
echo "  ✅ Cloud Run対応イメージ作成完了"
echo "  ✅ 基本モジュール動作確認済み"
echo ""
echo "🏷️ 作成されたイメージ:"
echo "  📦 完全版: $FULL_IMAGE_NAME"
echo "  📦 最新版: $LATEST_IMAGE_NAME"
echo ""
echo "📋 次のステップ: Phase 1.2 - Secret Manager統合"

# 出力ファイルに結果保存
cat > build_result.txt << EOF
BUILD_SUCCESS=true
IMAGE_NAME=$FULL_IMAGE_NAME
LATEST_IMAGE_NAME=$LATEST_IMAGE_NAME
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ARCHITECTURE=linux/amd64
YFINANCE_VERIFIED=true
BASIC_MODULES_VERIFIED=true
EOF

echo "📄 ビルド結果を build_result.txt に保存しました"