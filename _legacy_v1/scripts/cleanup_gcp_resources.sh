#!/bin/bash
# =============================================================================
# GCPリソースクリーンアップスクリプト
# - dev環境リソースの削除
# - 古いリビジョンの削除
# - 古いDockerイメージの削除
# =============================================================================

set -euo pipefail

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
PROJECT_ID="my-crypto-bot-project"
REGION="asia-northeast1"
ARTIFACT_REGISTRY_REPO="crypto-bot-repo"
PRODUCTION_SERVICE="crypto-bot-service-prod"
DEV_SERVICE="crypto-bot-dev"  # 削除対象

# ドライラン mode (デフォルト: true)
DRY_RUN=${1:-"--dry-run"}

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}GCP リソースクリーンアップ開始${NC}"
echo -e "${BLUE}==============================================================================${NC}"

if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo -e "${YELLOW}⚠️  ドライランモードで実行中（実際の削除は行いません）${NC}"
    echo -e "${YELLOW}実際に削除する場合は: bash $0 --execute${NC}"
else
    echo -e "${RED}⚠️  実際の削除を実行します！${NC}"
    read -p "続行しますか? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        echo "キャンセルしました"
        exit 0
    fi
fi

echo ""

# ────────────────────────────────────────────────────────────────────────────
# 1. dev環境のCloud Runサービス削除
# ────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[1/4] dev環境のCloud Runサービスを確認中...${NC}"

if gcloud run services describe "$DEV_SERVICE" --region="$REGION" --format="value(name)" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  dev環境サービスが見つかりました: $DEV_SERVICE${NC}"
    
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        echo -e "${YELLOW}  [DRY-RUN] 削除コマンド: gcloud run services delete $DEV_SERVICE --region=$REGION --quiet${NC}"
    else
        echo -e "${RED}  削除中...${NC}"
        gcloud run services delete "$DEV_SERVICE" --region="$REGION" --quiet
        echo -e "${GREEN}  ✅ dev環境サービスを削除しました${NC}"
    fi
else
    echo -e "${GREEN}  ✅ dev環境サービスは既に削除されています${NC}"
fi

echo ""

# ────────────────────────────────────────────────────────────────────────────
# 2. 古いCloud Runリビジョンの削除（prod環境）
# ────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[2/4] 古いCloud Runリビジョンを確認中...${NC}"

# 最新3つを残して削除
REVISIONS_TO_DELETE=$(gcloud run revisions list \
    --service="$PRODUCTION_SERVICE" \
    --region="$REGION" \
    --format="value(name)" \
    --sort-by="~creationTimestamp" | tail -n +4)

if [[ -n "$REVISIONS_TO_DELETE" ]]; then
    REVISION_COUNT=$(echo "$REVISIONS_TO_DELETE" | wc -l | tr -d ' ')
    echo -e "${YELLOW}⚠️  削除対象のリビジョン: $REVISION_COUNT 個${NC}"
    
    while IFS= read -r revision; do
        if [[ -n "$revision" ]]; then
            if [[ "$DRY_RUN" == "--dry-run" ]]; then
                echo -e "${YELLOW}  [DRY-RUN] 削除予定: $revision${NC}"
            else
                echo -e "${RED}  削除中: $revision${NC}"
                gcloud run revisions delete "$revision" --region="$REGION" --quiet || true
            fi
        fi
    done <<< "$REVISIONS_TO_DELETE"
    
    if [[ "$DRY_RUN" != "--dry-run" ]]; then
        echo -e "${GREEN}  ✅ 古いリビジョンを削除しました${NC}"
    fi
else
    echo -e "${GREEN}  ✅ 削除すべき古いリビジョンはありません${NC}"
fi

echo ""

# ────────────────────────────────────────────────────────────────────────────
# 3. 古いDockerイメージの削除（Artifact Registry）
# ────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[3/4] 古いDockerイメージを確認中...${NC}"

# 最新10個を残して削除
IMAGES_TO_DELETE=$(gcloud artifacts docker images list \
    "asia-northeast1-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REGISTRY_REPO/crypto-bot" \
    --format="value(version)" \
    --sort-by="~createTime" 2>/dev/null | tail -n +11)

if [[ -n "$IMAGES_TO_DELETE" ]]; then
    IMAGE_COUNT=$(echo "$IMAGES_TO_DELETE" | wc -l | tr -d ' ')
    echo -e "${YELLOW}⚠️  削除対象のイメージ: $IMAGE_COUNT 個${NC}"
    
    while IFS= read -r version; do
        if [[ -n "$version" ]]; then
            IMAGE_PATH="asia-northeast1-docker.pkg.dev/$PROJECT_ID/$ARTIFACT_REGISTRY_REPO/crypto-bot:$version"
            if [[ "$DRY_RUN" == "--dry-run" ]]; then
                echo -e "${YELLOW}  [DRY-RUN] 削除予定: $version${NC}"
            else
                echo -e "${RED}  削除中: $version${NC}"
                gcloud artifacts docker images delete "$IMAGE_PATH" --quiet || true
            fi
        fi
    done <<< "$IMAGES_TO_DELETE"
    
    if [[ "$DRY_RUN" != "--dry-run" ]]; then
        echo -e "${GREEN}  ✅ 古いDockerイメージを削除しました${NC}"
    fi
else
    echo -e "${GREEN}  ✅ 削除すべき古いイメージはありません${NC}"
fi

echo ""

# ────────────────────────────────────────────────────────────────────────────
# 4. Terraform状態ファイルの確認（dev環境）
# ────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}[4/4] Terraform状態ファイルを確認中...${NC}"

# GCSバケット内のdev環境のTerraform状態ファイル
BUCKET_NAME="${PROJECT_ID}-terraform-state"
DEV_STATE_PATH="env/dev/terraform.tfstate"

if gsutil ls "gs://$BUCKET_NAME/$DEV_STATE_PATH" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  dev環境のTerraform状態ファイルが見つかりました${NC}"
    
    if [[ "$DRY_RUN" == "--dry-run" ]]; then
        echo -e "${YELLOW}  [DRY-RUN] 削除コマンド: gsutil rm gs://$BUCKET_NAME/$DEV_STATE_PATH${NC}"
    else
        echo -e "${RED}  削除中...${NC}"
        gsutil rm "gs://$BUCKET_NAME/$DEV_STATE_PATH"
        echo -e "${GREEN}  ✅ dev環境のTerraform状態ファイルを削除しました${NC}"
    fi
else
    echo -e "${GREEN}  ✅ dev環境のTerraform状態ファイルは既に削除されています${NC}"
fi

echo ""

# ────────────────────────────────────────────────────────────────────────────
# サマリー
# ────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}クリーンアップ完了${NC}"
echo -e "${BLUE}==============================================================================${NC}"

if [[ "$DRY_RUN" == "--dry-run" ]]; then
    echo -e "${YELLOW}📋 これはドライランでした。実際の削除は実行されていません。${NC}"
    echo -e "${YELLOW}実際に削除を実行する場合は: bash $0 --execute${NC}"
else
    echo -e "${GREEN}✅ すべてのクリーンアップ作業が完了しました！${NC}"
    echo ""
    echo -e "${GREEN}削除されたリソース:${NC}"
    echo "  - dev環境のCloud Runサービス"
    echo "  - 古いCloud Runリビジョン（最新3つ以外）"
    echo "  - 古いDockerイメージ（最新10個以外）"
    echo "  - dev環境のTerraform状態ファイル"
fi

echo ""
echo -e "${BLUE}現在の環境状態:${NC}"
echo "  - 本番環境のみの運用"
echo "  - 月額コスト: 2,000円（devなし）"
echo "  - CI/CD: mainブランチのみ自動デプロイ"