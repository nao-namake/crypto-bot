#!/bin/bash
#
# ペーパートレード＋シグナル監視統合スクリプト
# Phase 2-1 + Phase 2-2 統合
#
# 使用方法:
#   ./paper_trade_with_monitoring.sh [--config CONFIG_FILE] [--duration HOURS]
#
# 機能:
# 1. ペーパートレードをバックグラウンドで開始
# 2. 定期的にシグナル監視を実行
# 3. 異常検出時にアラート
# 4. 終了時にサマリーレポート生成
#

set -e

# デフォルト設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="config/production/production.yml"
DURATION_HOURS=24
MONITOR_INTERVAL=3600  # 1時間（秒）
PID_FILE="/tmp/paper_trade.pid"
LOG_FILE="logs/paper_trade_session.log"

# 引数処理
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --duration)
            DURATION_HOURS="$2"
            shift 2
            ;;
        --interval)
            MONITOR_INTERVAL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--config CONFIG_FILE] [--duration HOURS] [--interval SECONDS]"
            exit 1
            ;;
    esac
done

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# クリーンアップ関数
cleanup() {
    log "🛑 Stopping paper trade session..."
    
    # ペーパートレードプロセス停止
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            log "Stopping paper trade process (PID: $PID)..."
            kill -SIGINT "$PID"
            sleep 5
        fi
        rm -f "$PID_FILE"
    fi
    
    # 最終監視レポート生成
    log "📊 Generating final monitoring report..."
    if python "$PROJECT_ROOT/scripts/utilities/signal_monitor.py" \
        --hours "$DURATION_HOURS" \
        --csv-path "$PROJECT_ROOT/logs/trading_signals.csv" \
        --report-dir "$PROJECT_ROOT/logs/monitoring_reports"; then
        log "✅ Final report generated"
    fi
    
    # ペーパートレード結果サマリー
    if [ -f "$PROJECT_ROOT/logs/paper_trades/paper_performance.json" ]; then
        log "💰 Paper Trade Performance Summary:"
        python -c "
import json
with open('$PROJECT_ROOT/logs/paper_trades/paper_performance.json') as f:
    data = json.load(f)
    print(f'  Total Trades: {data.get(\"total_trades\", 0)}')
    print(f'  Win Rate: {data.get(\"win_rate\", 0):.1%}')
    print(f'  Total PnL: {data.get(\"total_pnl\", 0):+.2f} JPY')
    print(f'  Max Drawdown: {data.get(\"max_drawdown\", 0):.1%}')
"
    fi
    
    log "✨ Session completed. Logs saved to: $LOG_FILE"
    exit 0
}

# シグナル終了時のクリーンアップ設定
trap cleanup SIGINT SIGTERM

# ディレクトリ作成
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/logs/paper_trades"
mkdir -p "$PROJECT_ROOT/logs/monitoring_reports"

# セッション開始
log "=========================================="
log "🚀 Paper Trade + Monitoring Session"
log "=========================================="
log "Config: $CONFIG_FILE"
log "Duration: $DURATION_HOURS hours"
log "Monitor Interval: $((MONITOR_INTERVAL/60)) minutes"
log "=========================================="

# 1. ペーパートレード開始（バックグラウンド）
log "📝 Starting paper trade in background..."
cd "$PROJECT_ROOT"

# ペーパートレードコマンド実行
nohup python -m crypto_bot.main live-bitbank \
    --config "$CONFIG_FILE" \
    --paper-trade \
    > logs/paper_trade_output.log 2>&1 &

PAPER_TRADE_PID=$!
echo $PAPER_TRADE_PID > "$PID_FILE"
log "✅ Paper trade started (PID: $PAPER_TRADE_PID)"

# プロセスが正常に起動したか確認
sleep 5
if ! kill -0 "$PAPER_TRADE_PID" 2>/dev/null; then
    log "❌ Failed to start paper trade"
    cat logs/paper_trade_output.log
    exit 1
fi

# 2. 初期データ生成を待つ
log "⏳ Waiting for initial signals to be generated..."
WAIT_COUNT=0
MAX_WAIT=60  # 最大60秒待機

while [ ! -f "$PROJECT_ROOT/logs/trading_signals.csv" ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ ! -f "$PROJECT_ROOT/logs/trading_signals.csv" ]; then
    log "⚠️ No signals generated after ${MAX_WAIT} seconds"
else
    log "✅ Signal generation confirmed"
fi

# 3. 監視ループ開始
log "🔍 Starting monitoring loop..."
START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION_HOURS * 3600))
MONITOR_COUNT=0

while [ $(date +%s) -lt $END_TIME ]; do
    # ペーパートレードプロセスの生存確認
    if ! kill -0 "$PAPER_TRADE_PID" 2>/dev/null; then
        log "⚠️ Paper trade process stopped unexpectedly"
        break
    fi
    
    # 定期監視実行
    if [ $MONITOR_COUNT -gt 0 ]; then  # 初回はスキップ
        log "📊 Running signal monitor (check #$MONITOR_COUNT)..."
        
        if python "$PROJECT_ROOT/scripts/utilities/signal_monitor.py" \
            --hours 1 \
            --csv-path "$PROJECT_ROOT/logs/trading_signals.csv" \
            --report-dir "$PROJECT_ROOT/logs/monitoring_reports" \
            --threshold-alert 50; then
            log "✅ Monitoring check passed"
        else
            log "⚠️ Monitoring detected issues"
            
            # 異常検出時の詳細表示
            LATEST_JSON=$(ls -t "$PROJECT_ROOT/logs/monitoring_reports"/signal_monitor_*.json 2>/dev/null | head -n1)
            if [ -f "$LATEST_JSON" ]; then
                python -c "
import json
with open('$LATEST_JSON') as f:
    data = json.load(f)
    print('Detected anomalies:')
    for anomaly in data.get('anomalies', []):
        print(f\"  - [{anomaly['severity']}] {anomaly['type']}: {anomaly['message']}\")
"
            fi
        fi
        
        # ペーパートレード途中経過表示
        if [ -f "$PROJECT_ROOT/logs/paper_trades/paper_performance.json" ]; then
            TRADES=$(python -c "
import json
with open('$PROJECT_ROOT/logs/paper_trades/paper_performance.json') as f:
    print(json.load(f).get('total_trades', 0))
")
            log "📈 Paper trades executed so far: $TRADES"
        fi
    fi
    
    MONITOR_COUNT=$((MONITOR_COUNT + 1))
    
    # 次の監視まで待機
    REMAINING=$((END_TIME - $(date +%s)))
    if [ $REMAINING -gt $MONITOR_INTERVAL ]; then
        log "💤 Waiting $(($MONITOR_INTERVAL/60)) minutes until next check..."
        sleep $MONITOR_INTERVAL
    else
        break
    fi
done

# 4. セッション終了
log "⏰ Session time limit reached"
cleanup