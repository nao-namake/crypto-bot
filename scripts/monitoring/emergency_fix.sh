#!/bin/bash
# =============================================================================
# 緊急対応スクリプト
# Phase 53.9対応 (2025/12/14)
#
# 使用方法:
#   bash scripts/monitoring/emergency_fix.sh [問題タイプ]
#
# 問題タイプ:
#   secret    : Secret Manager権限修正
#   silent    : Silent Failure修正
#   container : Container問題修正
#   discord   : Discord Webhook修復
#   ml        : ML予測システム再起動
#   full      : システム完全再起動（最終手段）
#   (引数なし): インタラクティブメニュー表示
# =============================================================================

set -euo pipefail

echo "🚨 緊急対応スクリプト"
echo "=============================================================="

# -----------------------------------------------------------------------------
# ヘルパー関数
# -----------------------------------------------------------------------------
timestamp() {
    python3 -c 'import time; print(int(time.time()))'
}

jst_time() {
    python3 -c "import datetime; print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S JST'))"
}

# -----------------------------------------------------------------------------
# Secret Manager 権限修正
# -----------------------------------------------------------------------------
fix_secret_manager() {
    echo ""
    echo "🔐 Secret Manager権限修正"

    SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null || echo "")
    if [ -z "$SERVICE_ACCOUNT" ]; then
        echo "❌ サービスアカウント取得失敗"
        return 1
    fi

    echo "   対象: $SERVICE_ACCOUNT"

    for secret in bitbank-api-key bitbank-api-secret discord-webhook-url; do
        echo "   $secret に権限付与中..."
        gcloud secrets add-iam-policy-binding "$secret" \
          --member="serviceAccount:$SERVICE_ACCOUNT" \
          --role="roles/secretmanager.secretAccessor" 2>/dev/null || echo "     (既に付与済み)"
    done

    FIX_TIMESTAMP=$(timestamp)
    echo "   新リビジョンデプロイ（権限適用）..."
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --set-env-vars="PERMISSION_FIX_TIMESTAMP=$FIX_TIMESTAMP"

    echo "✅ Secret Manager権限修正完了"
    echo "   10分後に check_infrastructure.sh で効果確認"
}

# -----------------------------------------------------------------------------
# Silent Failure 修正
# -----------------------------------------------------------------------------
fix_silent_failure() {
    echo ""
    echo "🔍 Silent Failure修正"

    # async/await問題確認
    ASYNC_WARNINGS=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND textPayload:\"RuntimeWarning\" AND textPayload:\"never awaited\"" --limit=10 --format="value(textPayload)" 2>/dev/null | grep -c . || echo "0")

    if [ "$ASYNC_WARNINGS" -gt 0 ]; then
        echo "   async/await問題検出 - システム再起動"
        ASYNC_FIX=$(timestamp)
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --set-env-vars="ASYNC_FIX_RESTART_TIMESTAMP=$ASYNC_FIX"
    fi

    # Secret Manager権限再確認
    echo "   Secret Manager権限再確認..."
    SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null || echo "")
    if [ -n "$SERVICE_ACCOUNT" ]; then
        for secret in bitbank-api-key bitbank-api-secret discord-webhook-url; do
            gcloud secrets add-iam-policy-binding "$secret" \
              --member="serviceAccount:$SERVICE_ACCOUNT" \
              --role="roles/secretmanager.secretAccessor" 2>/dev/null || true
        done
    fi

    echo "✅ Silent Failure修正完了"
    echo "   30分後に check_bot_functions.sh で効果確認"
}

# -----------------------------------------------------------------------------
# Container 問題修正
# -----------------------------------------------------------------------------
fix_container() {
    echo ""
    echo "🔥 Container問題修正"

    # メモリ・CPU増加
    echo "   メモリ増加: 2Gi"
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --memory=2Gi

    echo "   CPU増加: 2"
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --cpu=2

    # 強制再起動
    RESTART=$(timestamp)
    echo "   強制再起動..."
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --set-env-vars="EMERGENCY_RESTART_TIMESTAMP=$RESTART"

    echo "✅ Container問題修正完了"
    echo "   20分後に check_infrastructure.sh で効果確認"
}

# -----------------------------------------------------------------------------
# Discord Webhook 修復
# -----------------------------------------------------------------------------
fix_discord() {
    echo ""
    echo "📨 Discord Webhook修復"

    echo "新しいDiscord Webhook URLを入力してください:"
    echo "(Discordサーバー設定 → 連携サービス → ウェブフック から取得)"
    read -r NEW_WEBHOOK_URL

    if [ -n "$NEW_WEBHOOK_URL" ]; then
        echo "   Secret Manager更新中..."
        echo "$NEW_WEBHOOK_URL" | gcloud secrets versions add discord-webhook-url --data-file=-

        WEBHOOK_FIX=$(timestamp)
        echo "   新リビジョンデプロイ..."
        gcloud run services update crypto-bot-service-prod \
          --region=asia-northeast1 \
          --set-env-vars="WEBHOOK_FIX_TIMESTAMP=$WEBHOOK_FIX"

        echo "✅ Discord Webhook修復完了"
    else
        echo "❌ URL未入力 - 修復中断"
    fi
}

# -----------------------------------------------------------------------------
# ML予測システム再起動
# -----------------------------------------------------------------------------
fix_ml() {
    echo ""
    echo "🤖 ML予測システム再起動"

    # メモリ確保
    echo "   メモリ確保: 2Gi（MLモデル用）"
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --memory=2Gi

    # 再起動
    ML_RESTART=$(timestamp)
    echo "   ML再起動..."
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --set-env-vars="ML_RESTART_TIMESTAMP=$ML_RESTART"

    echo "✅ ML予測システム再起動完了"
    echo "   25分後に check_bot_functions.sh で効果確認"
}

# -----------------------------------------------------------------------------
# システム完全再起動（最終手段）
# -----------------------------------------------------------------------------
fix_full() {
    echo ""
    echo "⚡ システム完全再起動（最終手段）"
    echo ""
    echo "⚠️ 警告: 全システムを再起動します。"
    echo "   続行しますか？ (y/N): "
    read -r confirm

    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "中断しました"
        return 0
    fi

    CURRENT_REVISION=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.latestReadyRevisionName)" 2>/dev/null || echo "unknown")
    echo "   現在のリビジョン: $CURRENT_REVISION"

    FULL_RESTART=$(timestamp)
    gcloud run services update crypto-bot-service-prod \
      --region=asia-northeast1 \
      --memory=2Gi \
      --cpu=2 \
      --set-env-vars="FULL_SYSTEM_RESTART_TIMESTAMP=$FULL_RESTART"

    echo ""
    echo "✅ システム完全再起動完了"
    echo ""
    echo "📋 再起動後確認手順:"
    echo "   1. 5分待機"
    echo "   2. bash scripts/monitoring/check_infrastructure.sh"
    echo "   3. bash scripts/monitoring/check_bot_functions.sh"
}

# -----------------------------------------------------------------------------
# メニュー表示
# -----------------------------------------------------------------------------
show_menu() {
    echo ""
    echo "対応する問題を選択してください:"
    echo ""
    echo "  1) Secret Manager権限修正"
    echo "  2) Silent Failure修正"
    echo "  3) Container問題修正"
    echo "  4) Discord Webhook修復"
    echo "  5) ML予測システム再起動"
    echo "  6) システム完全再起動（最終手段）"
    echo "  q) 終了"
    echo ""
    echo -n "選択 [1-6/q]: "
    read -r choice

    case $choice in
        1) fix_secret_manager ;;
        2) fix_silent_failure ;;
        3) fix_container ;;
        4) fix_discord ;;
        5) fix_ml ;;
        6) fix_full ;;
        q|Q) echo "終了します"; exit 0 ;;
        *) echo "❌ 無効な選択"; exit 1 ;;
    esac
}

# -----------------------------------------------------------------------------
# メイン処理
# -----------------------------------------------------------------------------
echo "現在時刻: $(jst_time)"

case "${1:-}" in
    secret) fix_secret_manager ;;
    silent) fix_silent_failure ;;
    container) fix_container ;;
    discord) fix_discord ;;
    ml) fix_ml ;;
    full) fix_full ;;
    "") show_menu ;;
    *)
        echo "❌ 不明なオプション: $1"
        echo ""
        echo "使用方法: $0 [secret|silent|container|discord|ml|full]"
        exit 1
        ;;
esac
