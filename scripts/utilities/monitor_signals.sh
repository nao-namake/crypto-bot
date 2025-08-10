#!/bin/bash
#
# シグナル監視実行スクリプト
# Phase 2-2: ChatGPT提案採用
#
# 使用方法:
# 1. ローカルcron定期実行: */60 * * * * /path/to/monitor_signals.sh
# 2. 手動実行: ./monitor_signals.sh
# 3. CI/CD組み込み: bash scripts/utilities/monitor_signals.sh --ci
#

set -e

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# デフォルト設定
CSV_PATH="$PROJECT_ROOT/logs/trading_signals.csv"
REPORT_DIR="$PROJECT_ROOT/logs/monitoring_reports"
HOURS=24
THRESHOLD=60
CI_MODE=false

# 引数処理
while [[ $# -gt 0 ]]; do
    case $1 in
        --ci)
            CI_MODE=true
            shift
            ;;
        --hours)
            HOURS="$2"
            shift 2
            ;;
        --threshold)
            THRESHOLD="$2"
            shift 2
            ;;
        --csv-path)
            CSV_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ログ出力
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "=========================================="
log "📊 Signal Monitoring Started"
log "=========================================="
log "CSV Path: $CSV_PATH"
log "Report Dir: $REPORT_DIR"
log "Analysis Period: $HOURS hours"
log "Alert Threshold: $THRESHOLD"
log "CI Mode: $CI_MODE"

# Python仮想環境のアクティベート（存在する場合）
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    log "Activating virtual environment..."
    source "$PROJECT_ROOT/.venv/bin/activate"
fi

# CSVファイルの存在確認
if [ ! -f "$CSV_PATH" ]; then
    if [ "$CI_MODE" = true ]; then
        log "⚠️ Warning: No signal CSV found (OK for CI if no live trading yet)"
        # CI環境では警告のみ（エラーにしない）
        exit 0
    else
        log "❌ Error: Signal CSV not found at $CSV_PATH"
        log "Please ensure trading system has been running to generate signals"
        exit 1
    fi
fi

# レポートディレクトリ作成
mkdir -p "$REPORT_DIR"

# Pythonスクリプト実行
log "Running signal monitor..."
cd "$PROJECT_ROOT"

if python "$SCRIPT_DIR/signal_monitor.py" \
    --csv-path "$CSV_PATH" \
    --report-dir "$REPORT_DIR" \
    --hours "$HOURS" \
    --threshold-alert "$THRESHOLD"; then
    
    log "✅ Monitoring completed successfully"
    
    # 最新のHTMLレポートを探す
    LATEST_REPORT=$(ls -t "$REPORT_DIR"/signal_monitor_*.html 2>/dev/null | head -n1)
    
    if [ -n "$LATEST_REPORT" ]; then
        log "📁 Latest report: $LATEST_REPORT"
        
        # ローカル実行時はブラウザで開く（オプション）
        if [ "$CI_MODE" = false ] && [ "$(uname)" = "Darwin" ]; then
            # macOSの場合
            if command -v open &> /dev/null; then
                log "Opening report in browser..."
                open "$LATEST_REPORT"
            fi
        fi
    fi
    
else
    EXIT_CODE=$?
    log "⚠️ Monitoring detected issues (exit code: $EXIT_CODE)"
    
    if [ "$CI_MODE" = true ]; then
        log "❌ CI check failed - signal health below threshold"
        exit $EXIT_CODE
    else
        log "Please check the report for details"
        
        # 最新レポートを表示
        LATEST_REPORT=$(ls -t "$REPORT_DIR"/signal_monitor_*.html 2>/dev/null | head -n1)
        if [ -n "$LATEST_REPORT" ]; then
            log "📁 Report with issues: $LATEST_REPORT"
            
            # JSONレポートから異常を抽出（オプション）
            LATEST_JSON="${LATEST_REPORT%.html}.json"
            if [ -f "$LATEST_JSON" ]; then
                log "Anomalies detected:"
                python -c "
import json
with open('$LATEST_JSON') as f:
    data = json.load(f)
    for anomaly in data.get('anomalies', []):
        print(f\"  - [{anomaly['severity']}] {anomaly['type']}: {anomaly['message']}\")
"
            fi
        fi
        
        # ローカルでは継続実行（cronのため）
        exit 0
    fi
fi

log "=========================================="
log "📊 Signal Monitoring Completed"
log "=========================================="