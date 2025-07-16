#!/usr/bin/env bash
# =============================================================================
# GCP環境確認スクリプト - Terminal 1用
# Phase 2 ATR修正システムデプロイ前の環境チェック
# =============================================================================
set -euo pipefail

echo "=== [Terminal 1] GCP環境確認開始 ==="

# gcloudコマンド確認
echo ""
echo "=== gcloudコマンド確認 ==="
if command -v gcloud &> /dev/null; then
    echo "✅ gcloud コマンド利用可能"
    gcloud version
else
    echo "❌ gcloud コマンドが見つかりません"
    exit 1
fi

# 現在のプロジェクト設定確認
echo ""
echo "=== 現在のGCPプロジェクト設定確認 ==="
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "未設定")
echo "📋 現在のプロジェクト: $CURRENT_PROJECT"

# 認証状況確認
echo ""
echo "=== GCP認証状況確認 ==="
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1; then
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
    echo "✅ 認証済みアカウント: $ACTIVE_ACCOUNT"
else
    echo "❌ 認証されていません"
    echo "🔧 認証が必要です: gcloud auth login"
    exit 1
fi

# Docker設定確認
echo ""
echo "=== Docker設定確認 ==="
if command -v docker &> /dev/null; then
    echo "✅ Docker コマンド利用可能"
    docker version --format 'Docker version: {{.Client.Version}}'
else
    echo "❌ Docker コマンドが見つかりません"
    exit 1
fi

# Docker Buildx確認
echo ""
echo "=== Docker Buildx確認 ==="
if docker buildx version &> /dev/null; then
    echo "✅ Docker Buildx 利用可能"
    docker buildx version
else
    echo "❌ Docker Buildx が利用できません"
    exit 1
fi

# 既存のCloud Runサービス確認
echo ""
echo "=== 既存Cloud Runサービス確認 ==="
if [ "$CURRENT_PROJECT" != "未設定" ]; then
    echo "📋 $CURRENT_PROJECT の Cloud Runサービス一覧:"
    gcloud run services list --region=asia-northeast1 --format="table(metadata.name,status.url,status.conditions[0].status)" || echo "⚠️ サービス一覧取得に失敗（権限不足の可能性）"
else
    echo "⚠️ プロジェクトが設定されていないため、サービス確認をスキップ"
fi

echo ""
echo "=== [Terminal 1] GCP環境確認完了 ==="
echo "📋 現在の設定でPhase 2デプロイが実行可能です"