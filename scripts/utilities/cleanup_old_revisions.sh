#!/bin/bash

# ======================================================================
# GCP Cloud Run 古いリビジョン削除スクリプト
#
# 最新3つのリビジョンを残して、古いリビジョンを削除します
# これにより、ログの混乱を避け、最新のものだけを確実に参照できます
#
# Usage:
#   bash scripts/utils/cleanup_old_revisions.sh [--dry-run]
#
# Options:
#   --dry-run: 削除対象を表示するのみ（実際には削除しない）
# ======================================================================

set -euo pipefail

# 設定
SERVICE_NAME="crypto-bot-service-prod"
REGION="asia-northeast1"
KEEP_COUNT=3  # 保持するリビジョン数

# ドライランモードのチェック
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 ドライランモード: 削除対象を表示のみ"
fi

echo "========================================"
echo "📋 GCP Cloud Run リビジョンクリーンアップ"
echo "========================================"
echo "サービス: $SERVICE_NAME"
echo "リージョン: $REGION"
echo "保持数: 最新 $KEEP_COUNT 個"
echo ""

# 現在のリビジョン一覧を取得
echo "📊 現在のリビジョン一覧を取得中..."
ALL_REVISIONS=$(gcloud run revisions list \
    --service="$SERVICE_NAME" \
    --region="$REGION" \
    --format="value(metadata.name)" \
    --sort-by="~metadata.creationTimestamp")

TOTAL_COUNT=$(echo "$ALL_REVISIONS" | wc -l | tr -d ' ')
echo "✅ 合計 $TOTAL_COUNT 個のリビジョンが見つかりました"

# 削除対象のリビジョンを特定
if [ "$TOTAL_COUNT" -le "$KEEP_COUNT" ]; then
    echo "ℹ️ リビジョン数が $KEEP_COUNT 個以下のため、削除不要です"
    exit 0
fi

# 保持するリビジョン
KEEP_REVISIONS=$(echo "$ALL_REVISIONS" | head -n "$KEEP_COUNT")
echo ""
echo "✅ 以下のリビジョンを保持:"
echo "$KEEP_REVISIONS" | while read -r rev; do
    echo "  - $rev"
done

# 削除するリビジョン
DELETE_REVISIONS=$(echo "$ALL_REVISIONS" | tail -n +$((KEEP_COUNT + 1)))
DELETE_COUNT=$(echo "$DELETE_REVISIONS" | wc -l | tr -d ' ')

echo ""
echo "🗑️ 以下の $DELETE_COUNT 個のリビジョンを削除:"
echo "$DELETE_REVISIONS" | while read -r rev; do
    echo "  - $rev"
done

# 削除の実行または確認
if [ "$DRY_RUN" = true ]; then
    echo ""
    echo "📝 ドライランモード: 実際には削除されませんでした"
    echo "実際に削除するには、--dry-run オプションなしで実行してください"
else
    echo ""
    read -p "⚠️ 本当に削除しますか？ (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 削除を開始します..."
        
        # 各リビジョンを削除
        echo "$DELETE_REVISIONS" | while read -r revision; do
            if [ -n "$revision" ]; then
                echo "  削除中: $revision"
                gcloud run revisions delete "$revision" \
                    --region="$REGION" \
                    --quiet || {
                    echo "  ⚠️ 警告: $revision の削除に失敗しました"
                }
            fi
        done
        
        echo ""
        echo "✅ クリーンアップ完了！"
        
        # 最終確認
        echo ""
        echo "📊 最終的なリビジョン一覧:"
        gcloud run revisions list \
            --service="$SERVICE_NAME" \
            --region="$REGION" \
            --format="table(metadata.name,status.conditions[0].status,metadata.creationTimestamp)" \
            --limit=5
    else
        echo "❌ キャンセルされました"
        exit 0
    fi
fi

echo ""
echo "========================================"
echo "✨ スクリプト完了"
echo "========================================"