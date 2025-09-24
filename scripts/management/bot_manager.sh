#!/bin/bash

# crypto-bot 統合管理スクリプト
#
# check_status.sh + force_stop.sh の統合版
# 実行状況確認・プロセス停止・誤認防止機能を一元化
#
# 機能:
# - 実際のプロセス状況確認（Claude Code誤認防止）
# - プロセス完全停止（Discord通知ループ解決）
# - ロックファイル・ポート・ログ確認
# - ドライラン・詳細表示モード
#
# 使用方法:
#   bash scripts/management/bot_manager.sh                    # 状況確認のみ
#   bash scripts/management/bot_manager.sh check              # 状況確認のみ
#   bash scripts/management/bot_manager.sh stop               # 完全停止実行
#   bash scripts/management/bot_manager.sh stop --dry-run     # 停止シミュレーション
#   bash scripts/management/bot_manager.sh stop --verbose     # 詳細ログ付き停止

set -euo pipefail

# ========================================
# 設定・定数定義
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ユーザー固有パス
USER_NAME="${USER:-$(whoami)}"
LOCK_FILE="/tmp/crypto_bot_${USER_NAME}.lock"
PID_FILE="/tmp/crypto_bot_${USER_NAME}.pid"

# OS判定
OS_TYPE="$(uname -s)"
IS_MACOS=false
if [[ "$OS_TYPE" == "Darwin" ]]; then
    IS_MACOS=true
fi

# オプション解析
COMMAND="${1:-check}"
DRY_RUN=false
VERBOSE=false

# 引数解析
for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        check|stop)
            COMMAND="$arg"
            shift
            ;;
    esac
done

# タイムアウト設定
SIGTERM_TIMEOUT=10
SIGKILL_TIMEOUT=5

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ========================================
# ユーティリティ関数
# ========================================

log_info() {
    echo -e "${GREEN}[INFO]${NC}  $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC}  $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_debug() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}

show_usage() {
    echo "crypto-bot 統合管理スクリプト"
    echo ""
    echo "使用方法:"
    echo "  $0                      # 状況確認のみ（デフォルト）"
    echo "  $0 check                # 状況確認のみ"
    echo "  $0 stop                 # 完全停止実行"
    echo "  $0 stop --dry-run       # 停止シミュレーション"
    echo "  $0 stop --verbose       # 詳細ログ付き停止"
    echo ""
    echo "機能:"
    echo "  check: 実際のプロセス状況確認（Claude Code誤認防止）"
    echo "  stop:  crypto-bot関連プロセス完全停止"
    echo ""
    echo "オプション:"
    echo "  --dry-run    実際の停止は行わず、対象のみ表示"
    echo "  --verbose    詳細なデバッグ情報を表示"
}

# ========================================
# ステータス確認機能
# ========================================

check_processes() {
    echo -e "${BLUE}🔍 1. 実際のプロセス確認${NC}"
    echo "---"

    local running_processes
    running_processes=$(ps aux | grep -E "(crypto|main\.py|python.*main)" | grep -v grep || true)

    if [ -z "$running_processes" ]; then
        echo -e "${GREEN}✅ 実行中のプロセスなし${NC}"
        return 1
    else
        echo -e "${YELLOW}⚠️ 実行中のプロセス発見:${NC}"
        echo "$running_processes"
        return 0
    fi
}

check_lock_files() {
    echo -e "${BLUE}🔒 2. ロックファイル確認${NC}"
    echo "---"

    local lock_files
    lock_files=$(ls -la /tmp/crypto_bot_* 2>/dev/null || true)

    if [ -z "$lock_files" ]; then
        echo -e "${GREEN}✅ ロックファイルなし${NC}"
        return 1
    else
        echo -e "${YELLOW}⚠️ ロックファイル存在:${NC}"
        echo "$lock_files"
        return 0
    fi
}

check_port_usage() {
    echo -e "${BLUE}🌐 3. ポート使用状況確認${NC}"
    echo "---"

    local port_usage
    port_usage=$(lsof -i :5000 2>/dev/null || true)

    if [ -z "$port_usage" ]; then
        echo -e "${GREEN}✅ ポート5000未使用${NC}"
    else
        echo -e "${YELLOW}⚠️ ポート5000使用中:${NC}"
        echo "$port_usage"
    fi
}

check_recent_logs() {
    echo -e "${BLUE}📝 4. 最近の実行ログ確認${NC}"
    echo "---"

    if [ -f "/tmp/crypto_bot_last_run.log" ]; then
        local last_log
        last_log=$(tail -3 /tmp/crypto_bot_last_run.log 2>/dev/null || true)
        if [ -n "$last_log" ]; then
            echo -e "${BLUE}最新ログ:${NC}"
            echo "$last_log"
        else
            echo -e "${GREEN}✅ ログファイル空${NC}"
        fi
    else
        echo -e "${GREEN}✅ ログファイルなし${NC}"
    fi
}

perform_status_check() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}📊 crypto-bot 実行状況確認${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo ""

    # 各種確認実行
    local has_processes=false
    local has_locks=false

    if check_processes; then
        has_processes=true
    fi
    echo ""

    if check_lock_files; then
        has_locks=true
    fi
    echo ""

    check_port_usage
    echo ""

    check_recent_logs
    echo ""

    # 総合判定
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}📋 総合判定${NC}"
    echo -e "${PURPLE}========================================${NC}"

    if [ "$has_processes" = false ] && [ "$has_locks" = false ]; then
        echo -e "${GREEN}✅ システム完全停止状態${NC}"
        echo -e "${GREEN}   → 新規実行可能${NC}"
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}🔍 Claude Code利用時の注意事項${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        echo -e "${YELLOW}⚠️ バックグラウンドプロセス誤認識問題:${NC}"
        echo -e "   Claude Codeが'running'と表示しても、実際にはプロセスが"
        echo -e "   終了している場合があります。これはClaude Codeの"
        echo -e "   内部トラッキングシステムの制限事項です。"
        echo ""
        echo -e "${GREEN}✅ 確実な確認方法:${NC}"
        echo -e "   上記の「1. 実際のプロセス確認」で「✅ 実行中のプロセスなし」"
        echo -e "   と表示されていれば、実際には停止しています。"
        echo ""
        echo -e "${BLUE}🔧 回避策:${NC}"
        echo -e "   バックグラウンド実行を避けるため、以下のコマンドを使用："
        echo ""
        echo -e "${BLUE}📈 推奨実行方法:${NC}"
        echo "   bash scripts/management/run_safe.sh local paper"
        echo "   → デフォルトでフォアグラウンド実行（誤認識なし）"
        echo ""
        echo "   bash scripts/management/run_safe.sh status"
        echo "   → 実行状況確認"
        echo ""
        echo -e "${YELLOW}⚠️ 非推奨:${NC}"
        echo "   bash scripts/management/run_safe.sh local paper --background"
        echo "   → バックグラウンド実行（Claude Code誤認識の原因）"
        echo ""
        return 0
    else
        echo -e "${RED}❌ プロセスまたはロックファイルが存在${NC}"
        echo -e "${RED}   → 停止処理推奨${NC}"
        echo ""
        echo -e "${BLUE}🛑 推奨コマンド:${NC}"
        echo "bash scripts/management/bot_manager.sh stop       # 完全停止"
        echo "bash scripts/management/bot_manager.sh stop --dry-run  # 停止対象確認"
        return 1
    fi
}

# ========================================
# プロセス停止機能
# ========================================

find_target_processes() {
    log_debug "プロセス検索開始"

    # 検索パターン配列
    local patterns=(
        "crypto.*bot"
        "main\.py"
        "python.*main\.py"
        "run_safe\.sh"
        "python.*paper"
        "python.*live"
    )

    local all_pids=()

    # 各パターンで検索
    for pattern in "${patterns[@]}"; do
        log_debug "検索パターン: $pattern"

        # pgrep使用（より確実）
        local pids
        pids=$(pgrep -f "$pattern" 2>/dev/null || true)

        if [ -n "$pids" ]; then
            log_debug "発見PID: $pids"
            # 配列に追加
            while IFS= read -r pid; do
                if [[ " ${all_pids[*]} " != *" $pid "* ]]; then
                    all_pids+=("$pid")
                fi
            done <<< "$pids"
        fi
    done

    # ロックファイルからもPID取得
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(head -n 1 "$LOCK_FILE" 2>/dev/null || true)
        if [ -n "$lock_pid" ] && kill -0 "$lock_pid" 2>/dev/null; then
            if [[ " ${all_pids[*]} " != *" $lock_pid "* ]]; then
                all_pids+=("$lock_pid")
                log_debug "ロックファイルからPID追加: $lock_pid"
            fi
        fi
    fi

    # 重複除去とソート
    if [ ${#all_pids[@]} -gt 0 ]; then
        printf '%s\n' "${all_pids[@]}" | sort -u
    fi
}

show_process_details() {
    local pids=("$@")

    if [ ${#pids[@]} -eq 0 ]; then
        log_info "停止対象のプロセスは見つかりませんでした"
        return
    fi

    echo ""
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}🔍 検出されたプロセス詳細${NC}"
    echo -e "${PURPLE}========================================${NC}"

    # ヘッダー表示
    printf "%-8s %-8s %-10s %-10s %s\n" "PID" "PPID" "USER" "TIME" "COMMAND"
    echo "----------------------------------------"

    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            # プロセス詳細取得（macOS対応）
            if [ "$IS_MACOS" = true ]; then
                ps -p "$pid" -o pid,ppid,user,time,command | tail -n +2
            else
                ps -p "$pid" -o pid,ppid,user,time,command --no-headers
            fi

            # 子プロセス確認
            local children
            children=$(pgrep -P "$pid" 2>/dev/null || true)
            if [ -n "$children" ]; then
                echo "  └─ 子プロセス: $children"
            fi
        fi
    done
    echo ""
}

stop_processes() {
    local pids=("$@")

    if [ ${#pids[@]} -eq 0 ]; then
        log_info "停止対象のプロセスは見つかりませんでした"
        return 0
    fi

    log_info "🛑 プロセス停止開始 (対象: ${#pids[@]}個)"

    # Step 1: SIGTERM送信
    log_info "🔄 SIGTERM送信中..."
    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            if [ "$DRY_RUN" = true ]; then
                log_info "[DRY-RUN] SIGTERM送信予定: PID=$pid"
            else
                # プロセスグループ取得
                local pgid
                pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || echo "")

                if [ -n "$pgid" ] && [ "$pgid" != "$pid" ]; then
                    log_debug "プロセスグループ停止: PGID=$pgid"
                    if [ "$IS_MACOS" = true ]; then
                        kill -TERM -"$pgid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
                    else
                        kill -TERM -"$pgid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
                    fi
                else
                    kill -TERM "$pid" 2>/dev/null || true
                fi
            fi
        fi
    done

    if [ "$DRY_RUN" = true ]; then
        return 0
    fi

    # Step 2: SIGTERM待機
    log_info "⏳ 正常終了を待機中 (${SIGTERM_TIMEOUT}秒)..."
    local remaining_pids=()

    for i in $(seq 1 $SIGTERM_TIMEOUT); do
        remaining_pids=()
        for pid in "${pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                remaining_pids+=("$pid")
            fi
        done

        if [ ${#remaining_pids[@]} -eq 0 ]; then
            log_info "✅ プロセス正常終了"
            return 0
        fi

        sleep 1
    done

    # Step 3: SIGKILL送信
    if [ ${#remaining_pids[@]} -gt 0 ]; then
        log_warn "⚠️ 強制終了実行 (対象: ${#remaining_pids[@]}個)"

        for pid in "${remaining_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                local pgid
                pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || echo "")

                if [ -n "$pgid" ] && [ "$pgid" != "$pid" ]; then
                    if [ "$IS_MACOS" = true ]; then
                        kill -KILL -"$pgid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
                    else
                        kill -KILL -"$pgid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
                    fi
                else
                    kill -KILL "$pid" 2>/dev/null || true
                fi
            fi
        done

        # SIGKILL待機
        sleep $SIGKILL_TIMEOUT

        # 最終確認
        local final_remaining=()
        for pid in "${remaining_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                final_remaining+=("$pid")
            fi
        done

        if [ ${#final_remaining[@]} -eq 0 ]; then
            log_info "✅ プロセス強制終了"
        else
            log_error "❌ プロセス終了失敗: ${final_remaining[*]}"
            return 1
        fi
    fi
}

cleanup_files() {
    log_info "🧹 ファイルクリーンアップ開始"

    local files_to_clean=(
        "$LOCK_FILE"
        "$PID_FILE"
        "/tmp/crypto_bot_*.lock"
        "/tmp/crypto_bot_*.pid"
    )

    for file_pattern in "${files_to_clean[@]}"; do
        if [[ "$file_pattern" == *"*"* ]]; then
            # ワイルドカード展開（安全に処理）
            shopt -s nullglob
            local expanded_files=($file_pattern)
            shopt -u nullglob

            if [ ${#expanded_files[@]} -gt 0 ]; then
                for file in "${expanded_files[@]}"; do
                if [ -f "$file" ]; then
                    if [ "$DRY_RUN" = true ]; then
                        log_info "[DRY-RUN] 削除予定: $file"
                    else
                        rm -f "$file"
                        log_info "削除完了: $file"
                    fi
                fi
                done
            fi
        else
            if [ -f "$file_pattern" ]; then
                if [ "$DRY_RUN" = true ]; then
                    log_info "[DRY-RUN] 削除予定: $file_pattern"
                else
                    rm -f "$file_pattern"
                    log_info "削除完了: $file_pattern"
                fi
            fi
        fi
    done
}

check_port_conflicts() {
    local port_usage
    port_usage=$(lsof -i :5000 2>/dev/null || true)

    if [ -n "$port_usage" ]; then
        local pid
        pid=$(echo "$port_usage" | awk 'NR==2 {print $2}')
        log_warn "ポート 5000 が使用中: PID $pid"
    fi
}

perform_stop() {
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}🛑 crypto-bot 完全停止スクリプト${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_info "🔍 ドライランモード: 実際の停止は行いません"
        echo ""
    fi

    log_info "🔍 crypto-bot関連プロセスを検索中..."

    # プロセス検索
    local target_pids=()
    local found_processes
    found_processes=$(find_target_processes)

    if [ -n "$found_processes" ]; then
        # プロセスが見つかった場合のみ配列に格納
        while IFS= read -r pid; do
            target_pids+=("$pid")
        done <<< "$found_processes"
    fi

    # プロセス詳細表示
    if [ ${#target_pids[@]} -gt 0 ]; then
        show_process_details "${target_pids[@]}"
        # プロセス停止
        stop_processes "${target_pids[@]}"
    else
        show_process_details
    fi

    # ファイルクリーンアップ
    cleanup_files

    # ポート競合確認
    check_port_conflicts

    echo ""
    if [ "$DRY_RUN" = true ]; then
        log_info "✅ ドライラン完了"
    else
        log_info "✅ 完全停止完了"
    fi
}

# ========================================
# メイン処理
# ========================================

main() {
    case "$COMMAND" in
        "check")
            perform_status_check
            ;;
        "stop")
            perform_stop
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            log_error "不明なコマンド: $COMMAND"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"