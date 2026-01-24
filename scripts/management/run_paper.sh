#!/bin/bash
#
# ペーパートレード実行スクリプト（Phase 61）
#
# 使用方法:
#   bash scripts/management/run_paper.sh         # ペーパートレード開始
#   bash scripts/management/run_paper.sh stop    # 停止
#   bash scripts/management/run_paper.sh status  # 状況確認
#

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

# カラー出力
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_usage() {
    echo "ペーパートレード実行スクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0           ペーパートレード開始"
    echo "  $0 stop      停止"
    echo "  $0 status    状況確認"
}

check_status() {
    echo -e "${GREEN}[状況確認]${NC}"
    local procs
    procs=$(ps aux | grep -E "main\.py.*paper" | grep -v grep || true)

    if [ -z "$procs" ]; then
        echo -e "${GREEN}✅ 実行中のプロセスなし${NC}"
    else
        echo -e "${YELLOW}⚠️ 実行中:${NC}"
        echo "$procs"
    fi
}

stop_bot() {
    echo -e "${YELLOW}[停止処理]${NC}"

    # main.pyプロセスを検索して停止
    local pids
    pids=$(pgrep -f "main\.py" 2>/dev/null || true)

    if [ -z "$pids" ]; then
        echo -e "${GREEN}✅ 停止対象なし${NC}"
        return 0
    fi

    echo "停止中: $pids"
    pkill -f "main\.py" 2>/dev/null || true
    sleep 2

    # 強制終了（残っていれば）
    pids=$(pgrep -f "main\.py" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}強制終了中...${NC}"
        pkill -9 -f "main\.py" 2>/dev/null || true
    fi

    echo -e "${GREEN}✅ 停止完了${NC}"
}

run_paper() {
    # 既存プロセス確認
    local existing
    existing=$(pgrep -f "main\.py" 2>/dev/null || true)
    if [ -n "$existing" ]; then
        echo -e "${RED}❌ 既にプロセスが実行中です (PID: $existing)${NC}"
        echo "停止するには: $0 stop"
        exit 1
    fi

    # 環境変数読み込み
    if [ -f "$PROJECT_ROOT/config/secrets/.env" ]; then
        source "$PROJECT_ROOT/config/secrets/.env"
        export BITBANK_API_KEY BITBANK_API_SECRET DISCORD_WEBHOOK_URL
    fi

    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"

    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ペーパートレード開始${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "停止: Ctrl+C または $0 stop"
    echo ""

    # ペーパートレード実行
    python3 "$PROJECT_ROOT/main.py" --mode paper
}

# メイン処理
case "${1:-}" in
    "stop")
        stop_bot
        ;;
    "status")
        check_status
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    "")
        run_paper
        ;;
    *)
        echo -e "${RED}❌ 不明なコマンド: $1${NC}"
        show_usage
        exit 1
        ;;
esac
