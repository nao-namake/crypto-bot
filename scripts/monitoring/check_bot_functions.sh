#!/bin/bash
# =============================================================================
# Bot機能診断スクリプト
# Phase 53.9対応 (2025/12/14)
#
# 使用方法:
#   bash scripts/monitoring/check_bot_functions.sh
#
# 前提条:
#   check_infrastructure.sh が正常終了していること
#
# 終了コード:
#   0: 正常
#   1: 致命的問題（Silent Failure等）
#   2: 要注意
#   3: 監視継続
# =============================================================================

set -euo pipefail

echo "🤖 Bot機能診断開始: $(python3 -c "import datetime; print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S JST'))")"
echo "=============================================================="

# -----------------------------------------------------------------------------
# 共通関数定義
# -----------------------------------------------------------------------------
LATEST_CI_UTC=$(gh run list --limit=1 --workflow="CI/CD Pipeline" --status=success --json=createdAt --jq='.[0].createdAt' 2>/dev/null || echo "")
if [ -n "$LATEST_CI_UTC" ]; then
    DEPLOY_TIME="$LATEST_CI_UTC"
else
    DEPLOY_TIME=$(python3 -c "
import datetime
utc_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
print(utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
")
fi

count_logs() {
    local query="$1"
    local limit="${2:-50}"
    local result
    if [ -n "$DEPLOY_TIME" ]; then
        result=$(gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND ($query) AND timestamp>=\"$DEPLOY_TIME\"" --limit="$limit" --format="value(textPayload)" 2>/dev/null | grep -c . 2>/dev/null) || result=0
        echo "$result"
    else
        echo "0"
    fi
}

# スコア初期化
CRITICAL_ISSUES=0
WARNING_ISSUES=0
NORMAL_CHECKS=0

# -----------------------------------------------------------------------------
# A. 55特徴量システム確認
# -----------------------------------------------------------------------------
echo ""
echo "📊 55特徴量システム確認（Phase 51.7）"

FEATURE_55_COUNT=$(count_logs "textPayload:\"55特徴量\" OR textPayload:\"55個の特徴量\"" 15)
FEATURE_49_COUNT=$(count_logs "textPayload:\"49特徴量\" OR textPayload:\"基本特徴量のみ\"" 15)
DUMMY_MODEL_COUNT=$(count_logs "textPayload:\"DummyModel\"" 15)

echo "   55特徴量（完全セット）: $FEATURE_55_COUNT"
echo "   49特徴量（フォールバック）: $FEATURE_49_COUNT"
echo "   DummyModel: $DUMMY_MODEL_COUNT"

if [ "$FEATURE_55_COUNT" -gt 0 ] && [ "$DUMMY_MODEL_COUNT" -eq 0 ]; then
    echo "✅ 55特徴量システム: 正常稼働"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ "$FEATURE_49_COUNT" -gt 0 ] && [ "$DUMMY_MODEL_COUNT" -eq 0 ]; then
    echo "⚠️ 49特徴量フォールバック稼働中"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
elif [ "$DUMMY_MODEL_COUNT" -gt 0 ]; then
    echo "❌ DummyModelフォールバック（MLモデル停止）"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
else
    echo "⏸️ 特徴量システム: 待機中（取引サイクル未実行 - デプロイ直後は正常）"
fi

# -----------------------------------------------------------------------------
# B. Silent Failure 検出（最重要）
# -----------------------------------------------------------------------------
echo ""
echo "🔍 Silent Failure 検出"

SIGNAL_COUNT=$(count_logs "textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\"" 30)
ORDER_COUNT=$(count_logs "textPayload:\"注文実行\" OR textPayload:\"order_executed\" OR textPayload:\"create_order\"" 30)

echo "   シグナル生成: $SIGNAL_COUNT"
echo "   注文実行: $ORDER_COUNT"

if [ "$SIGNAL_COUNT" -eq 0 ]; then
    echo "⚠️ シグナル生成なし（Bot機能動作要確認）"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
elif [ "$SIGNAL_COUNT" -gt 0 ] && [ "$ORDER_COUNT" -eq 0 ]; then
    echo "❌ 完全Silent Failure検出（致命的）"
    echo "   → シグナル${SIGNAL_COUNT}生成されるも注文実行0"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 3))
else
    SUCCESS_RATE=$(python3 -c "print(int(($ORDER_COUNT / $SIGNAL_COUNT) * 100))" 2>/dev/null || echo "0")
    if [ "$SUCCESS_RATE" -ge 40 ]; then
        echo "✅ 取引実行: 正常（成功率${SUCCESS_RATE}%）"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    elif [ "$SUCCESS_RATE" -ge 20 ]; then
        echo "⚠️ 取引実行: 低成功率（${SUCCESS_RATE}%）"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    else
        echo "❌ 部分的Silent Failure（成功率${SUCCESS_RATE}%）"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
fi

# -----------------------------------------------------------------------------
# C. 6戦略動作確認
# -----------------------------------------------------------------------------
echo ""
echo "🎯 6戦略動作確認（Phase 51.7）"

STRATEGIES=("ATRBased" "BBReversal" "StochasticReversal" "DonchianChannel" "ADXTrendStrength" "MACDEMACrossover")
ACTIVE_STRATEGIES=0

for strategy in "${STRATEGIES[@]}"; do
    count=$(count_logs "textPayload:\"$strategy\"" 10)
    if [ "$count" -gt 0 ]; then
        echo "   $strategy: ✅ ($count)"
        ACTIVE_STRATEGIES=$((ACTIVE_STRATEGIES + 1))
    else
        echo "   $strategy: ℹ️ 未検出"
    fi
done

if [ "$ACTIVE_STRATEGIES" -eq 6 ]; then
    echo "✅ 6戦略: 全戦略稼働"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ "$ACTIVE_STRATEGIES" -ge 4 ]; then
    echo "⚠️ 6戦略: ${ACTIVE_STRATEGIES}/6戦略稼働"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "❌ 6戦略: ${ACTIVE_STRATEGIES}/6戦略のみ"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# D. ML予測確認
# -----------------------------------------------------------------------------
echo ""
echo "🤖 ML予測システム確認"

ML_PREDICTION_COUNT=$(count_logs "textPayload:\"ProductionEnsemble\" OR textPayload:\"ML予測\" OR textPayload:\"アンサンブル予測\"" 20)
echo "   ML予測実行: $ML_PREDICTION_COUNT"

if [ "$ML_PREDICTION_COUNT" -gt 0 ]; then
    echo "✅ ML予測: 正常実行中"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ ML予測: 未実行（ProductionEnsemble動作なし）"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# -----------------------------------------------------------------------------
# E. Phase 52.0/53.9 レジーム別TP/SL確認
# -----------------------------------------------------------------------------
echo ""
echo "📈 レジーム別TP/SL確認（Phase 52.0/53.9）"

REGIME_COUNT=$(count_logs "textPayload:\"市場状況:\" OR textPayload:\"RegimeType\" OR textPayload:\"レジーム\"" 10)
TIGHT_RANGE=$(count_logs "textPayload:\"TIGHT_RANGE\" OR textPayload:\"tight_range\"" 10)
NORMAL_RANGE=$(count_logs "textPayload:\"NORMAL_RANGE\" OR textPayload:\"normal_range\"" 10)
TRENDING=$(count_logs "textPayload:\"TRENDING\" OR textPayload:\"trending\"" 10)

echo "   市場状況分類: $REGIME_COUNT"
echo "   TIGHT_RANGE: $TIGHT_RANGE"
echo "   NORMAL_RANGE: $NORMAL_RANGE"
echo "   TRENDING: $TRENDING"

TOTAL_REGIME=$((TIGHT_RANGE + NORMAL_RANGE + TRENDING))
if [ "$TOTAL_REGIME" -gt 0 ]; then
    echo "✅ レジーム別TP/SL: 正常稼働"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⏸️ レジーム別TP/SL: 待機中（取引未実行 - 正常動作）"
fi

# -----------------------------------------------------------------------------
# F. Kelly基準確認
# -----------------------------------------------------------------------------
echo ""
echo "💱 Kelly基準確認"

KELLY_COUNT=$(count_logs "textPayload:\"Kelly基準\" OR textPayload:\"kelly_fraction\"" 15)
echo "   Kelly計算実行: $KELLY_COUNT"

if [ "$KELLY_COUNT" -gt 0 ]; then
    echo "✅ Kelly基準: 正常動作"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⏸️ Kelly基準: 待機中（5取引未満のため計算スキップ - 正常動作）"
fi

# -----------------------------------------------------------------------------
# G. Atomic Entry Pattern確認（Phase 51.6）
# -----------------------------------------------------------------------------
echo ""
echo "🎯 Atomic Entry Pattern確認（Phase 51.6）"

ATOMIC_SUCCESS=$(count_logs "textPayload:\"Atomic Entry完了\"" 10)
ATOMIC_ROLLBACK=$(count_logs "textPayload:\"ロールバック実行\" OR textPayload:\"Atomic Entry rollback\"" 10)

echo "   Atomic Entry成功: $ATOMIC_SUCCESS"
echo "   ロールバック: $ATOMIC_ROLLBACK"

if [ "$ATOMIC_SUCCESS" -gt 0 ] && [ "$ATOMIC_ROLLBACK" -le 2 ]; then
    echo "✅ Atomic Entry Pattern: 正常稼働"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ "$ATOMIC_ROLLBACK" -gt 5 ]; then
    echo "❌ Atomic Entry Pattern: 頻繁ロールバック"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
else
    echo "⏸️ Atomic Entry Pattern: 待機中（エントリー未実行 - 正常動作）"
fi

# -----------------------------------------------------------------------------
# 最終判定
# -----------------------------------------------------------------------------
echo ""
echo "=============================================================="
echo "📊 Bot機能診断結果"
echo "✅ 正常項目: $NORMAL_CHECKS"
echo "⚠️ 警告項目: $WARNING_ISSUES"
echo "❌ 致命的問題: $CRITICAL_ISSUES"

TOTAL_SCORE=$((NORMAL_CHECKS * 10 - WARNING_ISSUES * 3 - CRITICAL_ISSUES * 20))
echo "🏆 総合スコア: ${TOTAL_SCORE}点"

echo ""
echo "🎯 最終判定"

if [ "$SIGNAL_COUNT" -gt 0 ] && [ "$ORDER_COUNT" -eq 0 ]; then
    echo "💀 完全Silent Failure - 即座対応必須"
    echo "   → scripts/monitoring/emergency_fix.sh を実行"
    exit 1
elif [ "$CRITICAL_ISSUES" -ge 2 ]; then
    echo "🔴 Bot機能重大問題 - 緊急対応必要"
    exit 1
elif [ "$CRITICAL_ISSUES" -ge 1 ]; then
    echo "🟠 要注意 - Bot機能部分問題"
    exit 2
elif [ "$WARNING_ISSUES" -ge 3 ]; then
    echo "🟡 監視継続 - Bot機能品質低下"
    exit 3
else
    echo "🟢 Bot機能正常 - 全機能稼働中"
    exit 0
fi
