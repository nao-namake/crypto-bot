#!/bin/bash
# =============================================================================
# GCP インフラ基盤診断スクリプト
# Phase 53.9対応 (2025/12/14)
#
# 使用方法:
#   bash scripts/monitoring/check_infrastructure.sh
#
# 終了コード:
#   0: 正常
#   1: 致命的問題（即座対応必須）
#   2: 要注意（詳細診断推奨）
#   3: 監視継続（軽微な問題）
# =============================================================================

set -euo pipefail

echo "🚀 GCPインフラ基盤診断開始: $(python3 -c "import datetime; print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S JST'))")"
echo "=============================================================="

# -----------------------------------------------------------------------------
# 共通関数定義
# -----------------------------------------------------------------------------
LATEST_CI_UTC=$(gh run list --limit=1 --workflow="CI/CD Pipeline" --status=success --json=createdAt --jq='.[0].createdAt' 2>/dev/null || echo "")
if [ -n "$LATEST_CI_UTC" ]; then
    LATEST_CI_JST=$(python3 -c "
import datetime
utc_time = datetime.datetime.fromisoformat('$LATEST_CI_UTC'.replace('Z', '+00:00'))
jst_time = utc_time.astimezone(datetime.timezone(datetime.timedelta(hours=9)))
print(jst_time.strftime('%Y-%m-%d %H:%M:%S JST'))
")
    echo "✅ 最新CI時刻: $LATEST_CI_JST"
    DEPLOY_TIME="$LATEST_CI_UTC"
else
    DEPLOY_TIME=$(python3 -c "
import datetime
utc_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
print(utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
")
    echo "⚠️ CI時刻取得失敗、過去24時間のログを確認"
fi

count_logs() {
    local query="$1"
    local limit="${2:-50}"
    if [ -n "$DEPLOY_TIME" ]; then
        gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND ($query) AND timestamp>=\"$DEPLOY_TIME\"" --limit="$limit" --format="value(textPayload)" 2>/dev/null | grep -c . || echo "0"
    else
        echo "0"
    fi
}

show_logs() {
    local query="$1"
    local limit="${2:-5}"
    if [ -n "$DEPLOY_TIME" ]; then
        gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND ($query) AND timestamp>=\"$DEPLOY_TIME\"" --limit="$limit" --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)" 2>/dev/null
    fi
}

# スコア初期化
CRITICAL_ISSUES=0
WARNING_ISSUES=0
NORMAL_CHECKS=0

# -----------------------------------------------------------------------------
# A. Cloud Run サービス稼働確認
# -----------------------------------------------------------------------------
echo ""
echo "🔧 Cloud Run サービス稼働確認"

SERVICE_STATUS=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.conditions[0].status)" 2>/dev/null || echo "Unknown")
if [ "$SERVICE_STATUS" = "True" ]; then
    echo "✅ Cloud Run: 正常稼働中"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ Cloud Run: 異常 (status=$SERVICE_STATUS)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
fi

# 最新リビジョン確認
echo ""
echo "📋 最新リビジョン:"
TZ='Asia/Tokyo' gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=3 --format="table(metadata.name,metadata.creationTimestamp.date(tz='Asia/Tokyo'),status.conditions[0].status)" 2>/dev/null || echo "  ❌ リビジョン取得失敗"

# -----------------------------------------------------------------------------
# B. Secret Manager 権限確認
# -----------------------------------------------------------------------------
echo ""
echo "🔐 Secret Manager 権限確認"

SERVICE_ACCOUNT=$(gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(spec.template.spec.serviceAccountName)" 2>/dev/null || echo "")
if [ -n "$SERVICE_ACCOUNT" ]; then
    echo "   サービスアカウント: $SERVICE_ACCOUNT"

    BITBANK_KEY_OK=$(gcloud secrets get-iam-policy bitbank-api-key --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")
    BITBANK_SECRET_OK=$(gcloud secrets get-iam-policy bitbank-api-secret --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")
    DISCORD_OK=$(gcloud secrets get-iam-policy discord-webhook-url --format="value(bindings[].members)" 2>/dev/null | grep -q "$SERVICE_ACCOUNT" && echo "OK" || echo "NG")

    echo "   bitbank-api-key: $BITBANK_KEY_OK"
    echo "   bitbank-api-secret: $BITBANK_SECRET_OK"
    echo "   discord-webhook-url: $DISCORD_OK"

    if [ "$BITBANK_KEY_OK" = "OK" ] && [ "$BITBANK_SECRET_OK" = "OK" ] && [ "$DISCORD_OK" = "OK" ]; then
        echo "✅ Secret Manager権限: 全て正常"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    else
        echo "❌ Secret Manager権限: 一部欠如"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
    fi
else
    echo "❌ サービスアカウント取得失敗"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
fi

# -----------------------------------------------------------------------------
# C. Container 安定性確認
# -----------------------------------------------------------------------------
echo ""
echo "🔥 Container 安定性確認"

CONTAINER_EXIT_COUNT=$(count_logs "textPayload:\"Container called exit(1)\"" 20)
RUNTIME_WARNING_COUNT=$(count_logs "textPayload:\"RuntimeWarning\" AND textPayload:\"never awaited\"" 20)

echo "   Container exit(1): $CONTAINER_EXIT_COUNT回"
echo "   RuntimeWarning: $RUNTIME_WARNING_COUNT回"

if [ "$CONTAINER_EXIT_COUNT" -lt 5 ] && [ "$RUNTIME_WARNING_COUNT" -eq 0 ]; then
    echo "✅ Container安定性: 正常"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ "$CONTAINER_EXIT_COUNT" -lt 10 ] && [ "$RUNTIME_WARNING_COUNT" -lt 5 ]; then
    echo "⚠️ Container: 軽微問題（要監視）"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "❌ Container: 深刻問題（頻繁クラッシュ）"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# D. Discord 通知確認
# -----------------------------------------------------------------------------
echo ""
echo "📨 Discord 通知確認"

DISCORD_ERROR_COUNT=$(count_logs "textPayload:\"code: 50027\" OR textPayload:\"Invalid Webhook Token\"" 5)
if [ "$DISCORD_ERROR_COUNT" -eq 0 ]; then
    echo "✅ Discord: 正常（Webhook有効）"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ Discord: エラー検出（${DISCORD_ERROR_COUNT}回）"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# E. API 残高取得確認
# -----------------------------------------------------------------------------
echo ""
echo "💰 API 残高取得確認"

API_BALANCE_COUNT=$(count_logs "textPayload:\"残高\"" 15)
FALLBACK_COUNT=$(count_logs "textPayload:\"フォールバック\"" 15)

echo "   残高取得ログ: $API_BALANCE_COUNT回"
echo "   フォールバック使用: $FALLBACK_COUNT回"

if [ "$API_BALANCE_COUNT" -gt 0 ] && [ "$FALLBACK_COUNT" -lt 3 ]; then
    echo "✅ API残高取得: 正常"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ "$FALLBACK_COUNT" -gt 5 ]; then
    echo "⚠️ フォールバック多用中（API認証問題の可能性）"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "⚠️ 残高取得: 要確認"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# F. Phase 53.6 ポジション復元確認
# -----------------------------------------------------------------------------
echo ""
echo "📊 Phase 53.6 ポジション復元確認"

POSITION_RESTORE_COUNT=$(count_logs "textPayload:\"Phase 53.6\"" 10)
echo "   ポジション復元ログ: $POSITION_RESTORE_COUNT回"

if [ "$POSITION_RESTORE_COUNT" -gt 0 ]; then
    echo "✅ ポジション復元: 正常動作"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "ℹ️ ポジション復元: 未確認（ライブモードでのみ動作）"
fi

# -----------------------------------------------------------------------------
# G. 取引阻害エラー検出
# -----------------------------------------------------------------------------
echo ""
echo "🛡️ 取引阻害エラー検出"

NONETYPE_ERROR_COUNT=$(count_logs "textPayload:\"NoneType\"" 20)
API_ERROR_COUNT=$(count_logs "textPayload:\"bitbank API エラー\" OR textPayload:\"API.*エラー.*20\"" 20)

echo "   NoneTypeエラー: $NONETYPE_ERROR_COUNT回"
echo "   API異常: $API_ERROR_COUNT回"

if [ "$NONETYPE_ERROR_COUNT" -eq 0 ] && [ "$API_ERROR_COUNT" -lt 3 ]; then
    echo "✅ 取引阻害エラー: なし"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ "$NONETYPE_ERROR_COUNT" -lt 5 ] && [ "$API_ERROR_COUNT" -lt 10 ]; then
    echo "⚠️ 取引阻害エラー: 軽微（要監視）"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "❌ 取引阻害エラー: 多発"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# 最終判定
# -----------------------------------------------------------------------------
echo ""
echo "=============================================================="
echo "📊 インフラ基盤診断結果"
echo "✅ 正常項目: $NORMAL_CHECKS"
echo "⚠️ 警告項目: $WARNING_ISSUES"
echo "❌ 致命的問題: $CRITICAL_ISSUES"

TOTAL_SCORE=$((NORMAL_CHECKS * 10 - WARNING_ISSUES * 3 - CRITICAL_ISSUES * 20))
echo "🏆 総合スコア: $TOTAL_SCORE点"

echo ""
echo "🎯 最終判定"

if [ "$CRITICAL_ISSUES" -ge 2 ]; then
    echo "💀 致命的問題検出 - 即座対応必須"
    echo "   → scripts/monitoring/emergency_fix.sh を実行"
    exit 1
elif [ "$CRITICAL_ISSUES" -ge 1 ]; then
    echo "🟠 要注意 - 詳細診断推奨"
    exit 2
elif [ "$WARNING_ISSUES" -ge 3 ]; then
    echo "🟡 監視継続 - 軽微な問題"
    exit 3
else
    echo "🟢 インフラ基盤正常"
    echo "   → 次は scripts/monitoring/check_bot_functions.sh を実行"
    exit 0
fi
