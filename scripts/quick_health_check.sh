#!/bin/bash
# =============================================================================
# クイックヘルスチェックスクリプト
# 土曜日早朝問題を含む主要問題を1分で検出
# =============================================================================

set -e

BASE_URL="https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "🚀 クイックヘルスチェック開始 ($TIMESTAMP)"
echo "=" $(printf '=%.0s' {1..50})

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# チェック結果カウンター
CHECKS_TOTAL=0
CHECKS_PASSED=0
CRITICAL_ISSUES=0
WARNING_ISSUES=0

# チェック関数
check_result() {
    local status="$1"
    local message="$2"
    local details="$3"
    
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✅ SUCCESS${NC}: $message"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️ WARNING${NC}: $message"
            WARNING_ISSUES=$((WARNING_ISSUES + 1))
            ;;
        "CRITICAL")
            echo -e "${RED}🚨 CRITICAL${NC}: $message"
            CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️ INFO${NC}: $message"
            CHECKS_PASSED=$((CHECKS_PASSED + 1))
            ;;
    esac
    
    if [[ -n "$details" ]]; then
        echo "    $details"
    fi
}

# 1. 基本接続チェック
echo -e "\n${BLUE}🔍 基本接続チェック${NC}"
if curl -s --max-time 10 "$BASE_URL/health" > /dev/null; then
    check_result "SUCCESS" "システム基本稼働" "API応答正常"
else
    check_result "CRITICAL" "システム接続失敗" "APIサーバー応答なし"
    exit 1
fi

# 2. データ新鮮度チェック（最重要）
echo -e "\n${BLUE}🔍 データ新鮮度チェック${NC}"
if command -v gcloud >/dev/null 2>&1; then
    LATEST_DATA=$(gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"latest:"' --limit=1 --format="value(textPayload)" 2>/dev/null | head -1)
    
    if [[ -n "$LATEST_DATA" && "$LATEST_DATA" == *"ago"* ]]; then
        if [[ "$LATEST_DATA" == *"20."*"h ago"* ]] || [[ "$LATEST_DATA" == *"hours ago"* ]]; then
            # 時間を抽出（20.8h ago -> 20.8）
            HOURS=$(echo "$LATEST_DATA" | grep -o '[0-9]*\.[0-9]*h ago' | grep -o '[0-9]*\.[0-9]*')
            if [[ -n "$HOURS" ]] && (( $(echo "$HOURS > 2" | bc -l) )); then
                check_result "CRITICAL" "データが古すぎます" "${HOURS}時間前のデータ"
            else
                check_result "SUCCESS" "データ新鮮度良好" "${HOURS}時間前"
            fi
        else
            check_result "SUCCESS" "データ新鮮度良好" "1時間以内"
        fi
    else
        check_result "WARNING" "データ新鮮度不明" "ログ情報不足"
    fi
else
    check_result "WARNING" "gcloud未利用" "ローカル環境のためスキップ"
fi

# 3. API認証チェック
echo -e "\n${BLUE}🔍 API認証チェック${NC}"
DETAILED_HEALTH=$(curl -s --max-time 15 "$BASE_URL/health/detailed" 2>/dev/null)
if [[ -n "$DETAILED_HEALTH" ]]; then
    if echo "$DETAILED_HEALTH" | grep -q '"status":"healthy"'; then
        MARGIN_MODE=$(echo "$DETAILED_HEALTH" | grep -o '"margin_mode":[^,}]*' | cut -d':' -f2)
        if [[ "$MARGIN_MODE" == "true" ]]; then
            check_result "SUCCESS" "API認証正常・信用取引有効" "margin_mode=true"
        else
            check_result "WARNING" "API認証正常・現物取引のみ" "margin_mode=false"
        fi
    else
        check_result "WARNING" "API認証状態不明" "詳細ヘルス応答異常"
    fi
else
    check_result "WARNING" "詳細ヘルス取得失敗" "タイムアウトまたは接続問題"
fi

# 4. エラーパターンチェック
echo -e "\n${BLUE}🔍 重要エラーチェック${NC}"
if command -v gcloud >/dev/null 2>&1; then
    # API Error 10000チェック
    if gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"10000"' --limit=1 --format="value(textPayload)" 2>/dev/null | grep -q "10000"; then
        check_result "CRITICAL" "API Error 10000検出" "4時間足取得問題"
    else
        check_result "SUCCESS" "API Error 10000なし" "正常"
    fi
    
    # 認証エラーチェック
    if gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"401"' --limit=1 --format="value(textPayload)" 2>/dev/null | grep -q "401"; then
        check_result "CRITICAL" "認証エラー検出" "APIキー問題"
    else
        check_result "SUCCESS" "認証エラーなし" "正常"
    fi
else
    check_result "INFO" "ログチェックスキップ" "gcloud未利用"
fi

# 5. データ取得件数チェック
echo -e "\n${BLUE}🔍 データ取得件数チェック${NC}"
if command -v gcloud >/dev/null 2>&1; then
    RECORD_LOG=$(gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"records"' --limit=2 --format="value(textPayload)" 2>/dev/null | head -1)
    if [[ -n "$RECORD_LOG" && "$RECORD_LOG" == *"records"* ]]; then
        # "99 records"のような形式から数値を抽出
        RECORD_COUNT=$(echo "$RECORD_LOG" | grep -o '[0-9]*\s*records' | grep -o '[0-9]*' | head -1)
        if [[ -n "$RECORD_COUNT" ]]; then
            if [[ $RECORD_COUNT -ge 100 ]]; then
                check_result "SUCCESS" "データ取得件数良好" "${RECORD_COUNT}件 (十分な学習データ)"
            elif [[ $RECORD_COUNT -ge 50 ]]; then
                check_result "WARNING" "データ取得件数やや少ない" "${RECORD_COUNT}件 (ML精度に影響の可能性)"
            elif [[ $RECORD_COUNT -ge 10 ]]; then
                check_result "WARNING" "データ取得件数不足" "${RECORD_COUNT}件 (取引判定に支障)"
            else
                check_result "CRITICAL" "データ取得件数深刻不足" "${RECORD_COUNT}件 (システム機能不全)"
            fi
        else
            check_result "WARNING" "データ取得件数解析失敗" "数値抽出不可"
        fi
    else
        check_result "WARNING" "データ取得件数不明" "ログ情報なし"
    fi
else
    check_result "INFO" "データ取得チェックスキップ" "gcloud未利用"
fi

# 6. マルチタイムフレーム処理チェック
echo -e "\n${BLUE}🔍 マルチタイムフレーム処理チェック${NC}"
if command -v gcloud >/dev/null 2>&1; then
    ENSEMBLE_LOG=$(gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"ensemble processor created"' --limit=3 --format="value(textPayload)" 2>/dev/null)
    if [[ -n "$ENSEMBLE_LOG" ]]; then
        TF_15M=$(echo "$ENSEMBLE_LOG" | grep -c "15m" || echo "0")
        TF_1H=$(echo "$ENSEMBLE_LOG" | grep -c "1h" || echo "0")
        TF_4H=$(echo "$ENSEMBLE_LOG" | grep -c "4h" || echo "0")
        TOTAL_TF=$((TF_15M + TF_1H + TF_4H))
        
        if [[ $TOTAL_TF -ge 3 ]]; then
            check_result "SUCCESS" "マルチタイムフレーム完全準備" "15m/1h/4h統合可能"
        elif [[ $TOTAL_TF -ge 2 ]]; then
            check_result "WARNING" "マルチタイムフレーム部分準備" "${TOTAL_TF}/3タイムフレーム"
        else
            check_result "CRITICAL" "マルチタイムフレーム準備不足" "統合分析不可"
        fi
    else
        # base_timeframe設定確認
        BASE_TF_LOG=$(gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"base_timeframe"' --limit=1 --format="value(textPayload)" 2>/dev/null)
        if [[ -n "$BASE_TF_LOG" && "$BASE_TF_LOG" == *"1h"* ]]; then
            check_result "SUCCESS" "ベースタイムフレーム設定正常" "1h基準設定"
        else
            check_result "WARNING" "マルチタイムフレーム状態不明" "設定確認推奨"
        fi
    fi
else
    check_result "INFO" "マルチタイムフレームチェックスキップ" "gcloud未利用"
fi

# 7. 特徴量使用状況チェック
echo -e "\n${BLUE}🔍 特徴量使用状況チェック${NC}"
if command -v gcloud >/dev/null 2>&1; then
    FEATURE_LOG=$(gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"features.*generated"' --limit=1 --format="value(textPayload)" 2>/dev/null)
    if [[ -n "$FEATURE_LOG" && "$FEATURE_LOG" == *"features"* ]]; then
        # "151 features generated"のような形式から数値を抽出
        FEATURE_COUNT=$(echo "$FEATURE_LOG" | grep -o '[0-9]*\s*features' | grep -o '[0-9]*' | head -1)
        if [[ -n "$FEATURE_COUNT" ]]; then
            if [[ $FEATURE_COUNT -ge 140 ]]; then
                check_result "SUCCESS" "特徴量生成完全" "${FEATURE_COUNT}特徴量 (151特徴量システム正常)"
            elif [[ $FEATURE_COUNT -ge 100 ]]; then
                check_result "WARNING" "特徴量やや不足" "${FEATURE_COUNT}特徴量 (外部データ一部未取得)"
            elif [[ $FEATURE_COUNT -ge 50 ]]; then
                check_result "WARNING" "特徴量大幅不足" "${FEATURE_COUNT}特徴量 (外部データ系統問題)"
            else
                check_result "CRITICAL" "特徴量深刻不足" "${FEATURE_COUNT}特徴量 (基本特徴量のみ)"
            fi
        else
            check_result "WARNING" "特徴量数解析失敗" "数値抽出不可"
        fi
    else
        # 特徴量警告チェック
        FEATURE_WARNING=$(gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"WARNING.*feature"' --limit=2 --format="value(textPayload)" 2>/dev/null)
        if [[ -n "$FEATURE_WARNING" ]]; then
            WARNING_COUNT=$(echo "$FEATURE_WARNING" | wc -l)
            check_result "WARNING" "特徴量警告検出" "${WARNING_COUNT}件 (未実装特徴量の可能性)"
        else
            check_result "INFO" "特徴量状態ログなし" "初期化中の可能性"
        fi
    fi
else
    check_result "INFO" "特徴量チェックスキップ" "gcloud未利用"
fi

# 8. 初期化状態チェック
echo -e "\n${BLUE}🔍 初期化状態チェック${NC}"
if command -v gcloud >/dev/null 2>&1; then
    INIT_SUCCESS=$(gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"INIT.*success"' --limit=3 --format="value(textPayload)" 2>/dev/null)
    if [[ -n "$INIT_SUCCESS" ]]; then
        INIT_COUNT=$(echo "$INIT_SUCCESS" | wc -l)
        check_result "SUCCESS" "初期化プロセス確認" "${INIT_COUNT}段階の成功ログ"
    else
        check_result "WARNING" "初期化状態不明" "成功ログなし"
    fi
else
    check_result "INFO" "初期化チェックスキップ" "gcloud未利用"
fi

# 9. 土日取引スケジュールチェック
echo -e "\n${BLUE}🔍 取引スケジュールチェック${NC}"
WEEKDAY=$(date +%u)  # 1=月曜日, 7=日曜日
if [[ $WEEKDAY -ge 6 ]]; then
    check_result "INFO" "土日期間中" "監視モード（取引停止期間）"
else
    check_result "SUCCESS" "平日期間" "通常取引スケジュール"
fi

# サマリーレポート
echo -e "\n$( printf '=%.0s' {1..50})"
echo -e "${BLUE}📊 クイックヘルスチェック結果サマリー${NC}"
echo "=" $(printf '=%.0s' {1..50})

SUCCESS_RATE=$(( CHECKS_PASSED * 100 / CHECKS_TOTAL ))
echo -e "✅ 成功: ${GREEN}${CHECKS_PASSED}/${CHECKS_TOTAL}${NC} (${SUCCESS_RATE}%)"
echo -e "🚨 CRITICAL: ${RED}${CRITICAL_ISSUES}件${NC}"
echo -e "⚠️ WARNING: ${YELLOW}${WARNING_ISSUES}件${NC}"

# 修正提案
if [[ $CRITICAL_ISSUES -gt 0 ]] || [[ $WARNING_ISSUES -gt 0 ]]; then
    echo -e "\n${BLUE}🚀 推奨アクション${NC}"
    
    if [[ $CRITICAL_ISSUES -gt 0 ]]; then
        echo "1. CRITICAL問題の即座修正が必要"
        echo "   python scripts/system_health_check.py --detailed"
    fi
    
    if gcloud logging read 'resource.type=cloud_run_revision AND textPayload:"latest:"' --limit=1 --format="value(textPayload)" 2>/dev/null | grep -q "20.*h ago"; then
        echo "2. Phase H.8: 最新データ強制取得システム実装"
        echo "   古いデータ問題の根本解決"
    fi
    
    if [[ $WARNING_ISSUES -gt 2 ]]; then
        echo "3. 詳細ヘルスチェックの実行推奨"
        echo "   python scripts/system_health_check.py --save health_report.json"
    fi
fi

echo -e "\n${BLUE}完了時刻${NC}: $(date '+%Y-%m-%d %H:%M:%S')"

# 終了コード設定
if [[ $CRITICAL_ISSUES -gt 0 ]]; then
    exit 1
else
    exit 0
fi