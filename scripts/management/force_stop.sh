#!/bin/bash

# crypto-bot 完全停止スクリプト
#
# Discord通知の無限ループやasyncioタスクが停止しない問題を解決する
# 強力なプロセス停止機能を提供します。
#
# 機能:
# - 全crypto-bot関連プロセスの検出と停止
# - プロセスグループ全体の終了
# - ロックファイル・PIDファイルの完全削除
# - ポート使用状況の確認
# - 段階的停止（SIGTERM → SIGKILL）
#
# 使用方法:
#   bash scripts/management/force_stop.sh
#   bash scripts/management/force_stop.sh --verbose
#   bash scripts/management/force_stop.sh --dry-run

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

# タイムアウト設定
SIGTERM_TIMEOUT=10
SIGKILL_TIMEOUT=5

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# フラグ
VERBOSE=false
DRY_RUN=false

# ========================================
# ユーティリティ関数
# ========================================

log_info() {
    printf "${GREEN}[INFO]${NC}  %s - %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_warn() {
    printf "${YELLOW}[WARN]${NC}  %s - %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_error() {
    printf "${RED}[ERROR]${NC} %s - %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

log_debug() {
    if [ "$VERBOSE" = true ]; then
        printf "${BLUE}[DEBUG]${NC} %s - %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
    fi
}

show_usage() {
    echo "crypto-bot 完全停止スクリプト"
    echo ""
    echo "使用方法: $0 [options]"
    echo ""
    echo "オプション:"
    echo "  --verbose     詳細ログを表示"
    echo "  --dry-run     実際の停止は行わず、検出のみ実行"
    echo "  --help        このヘルプを表示"
    echo ""
    echo "機能:"
    echo "  - 全crypto-bot関連プロセスの強制停止"
    echo "  - Discord通知の無限ループ解決"
    echo "  - asyncioタスクの完全終了"
    echo "  - ロックファイル・PIDファイルの削除"
    echo ""
}

# ========================================
# プロセス検出関数
# ========================================

find_crypto_processes() {
    log_debug "crypto-bot関連プロセスを検索中..."

    local found_processes=()

    # 1. pgrep による検索（プロジェクト特化）
    local pgrep_pids
    pgrep_pids=$(pgrep -f "/Users/nao/Desktop/bot.*main\.py|run_safe\.sh.*paper|crypto.*bot" 2>/dev/null || true)
    if [ -n "$pgrep_pids" ]; then
        while IFS= read -r pid; do
            found_processes+=("$pid")
        done <<< "$pgrep_pids"
    fi

    # 2. ps による詳細検索（プロジェクト特化）
    local ps_pids
    ps_pids=$(ps aux | grep -E "(/Users/nao/Desktop/bot.*main\.py|run_safe\.sh.*paper|crypto.*bot)" | grep -v grep | awk '{print $2}' || true)
    if [ -n "$ps_pids" ]; then
        while IFS= read -r pid; do
            if [ -n "$pid" ]; then
                local found=false
                if [ ${#found_processes[@]} -gt 0 ]; then
                    for existing in "${found_processes[@]}"; do
                        if [ "$existing" = "$pid" ]; then
                            found=true
                            break
                        fi
                    done
                fi
                if [ "$found" = false ]; then
                    found_processes+=("$pid")
                fi
            fi
        done <<< "$ps_pids"
    fi

    # 3. ロックファイルから取得
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(head -n 1 "$LOCK_FILE" 2>/dev/null || true)
        if [ -n "$lock_pid" ]; then
            local found=false
            if [ ${#found_processes[@]} -gt 0 ]; then
                for existing in "${found_processes[@]}"; do
                    if [ "$existing" = "$lock_pid" ]; then
                        found=true
                        break
                    fi
                done
            fi
            if [ "$found" = false ]; then
                found_processes+=("$lock_pid")
            fi
        fi
    fi

    # 4. PIDファイルから取得
    if [ -f "$PID_FILE" ]; then
        local pid_file_pid
        pid_file_pid=$(head -n 1 "$PID_FILE" 2>/dev/null || true)
        if [ -n "$pid_file_pid" ]; then
            local found=false
            if [ ${#found_processes[@]} -gt 0 ]; then
                for existing in "${found_processes[@]}"; do
                    if [ "$existing" = "$pid_file_pid" ]; then
                        found=true
                        break
                    fi
                done
            fi
            if [ "$found" = false ]; then
                found_processes+=("$pid_file_pid")
            fi
        fi
    fi

    # 5. プロセス存在確認
    local valid_processes=()
    if [ ${#found_processes[@]} -gt 0 ]; then
        for pid in "${found_processes[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                valid_processes+=("$pid")
            fi
        done
    fi

    if [ ${#valid_processes[@]} -gt 0 ]; then
        printf '%s\n' "${valid_processes[@]}"
    fi
}

show_process_details() {
    local pids=("$@")

    if [ ${#pids[@]} -eq 0 ]; then
        log_info "検出されたプロセスはありません"
        return
    fi

    printf "${PURPLE}========================================${NC}\n"
    printf "${PURPLE}🔍 検出されたプロセス詳細${NC}\n"
    printf "${PURPLE}========================================${NC}\n"

    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            local process_info
            process_info=$(ps -p "$pid" -o pid,ppid,user,time,command 2>/dev/null || echo "PID $pid: 情報取得失敗")
            echo "$process_info"

            # 子プロセス確認
            local children
            children=$(pgrep -P "$pid" 2>/dev/null || true)
            if [ -n "$children" ]; then
                echo "  └─ 子プロセス: $children"
            fi

            echo ""
        fi
    done

    printf "${PURPLE}========================================${NC}\n"
}

# ========================================
# プロセス停止関数
# ========================================

stop_process_gracefully() {
    local pid="$1"
    local process_name="${2:-PID $pid}"

    if ! kill -0 "$pid" 2>/dev/null; then
        log_debug "$process_name: 既に停止済み"
        return 0
    fi

    log_info "$process_name: 正常終了を試行中... (PID: $pid)"

    # SIGTERM送信
    if [ "$DRY_RUN" = false ]; then
        kill -TERM "$pid" 2>/dev/null || {
            log_warn "$process_name: SIGTERM送信失敗"
            return 1
        }
    else
        log_debug "[DRY-RUN] kill -TERM $pid"
    fi

    # 正常終了を待機
    for ((i=1; i<=SIGTERM_TIMEOUT; i++)); do
        if ! kill -0 "$pid" 2>/dev/null; then
            log_info "$process_name: 正常終了完了"
            return 0
        fi
        sleep 1
    done

    log_warn "$process_name: 正常終了タイムアウト - 強制終了中..."

    # SIGKILL送信
    if [ "$DRY_RUN" = false ]; then
        kill -KILL "$pid" 2>/dev/null || {
            log_error "$process_name: SIGKILL送信失敗"
            return 1
        }
    else
        log_debug "[DRY-RUN] kill -KILL $pid"
    fi

    # 強制終了を待機
    for ((i=1; i<=SIGKILL_TIMEOUT; i++)); do
        if ! kill -0 "$pid" 2>/dev/null; then
            log_info "$process_name: 強制終了完了"
            return 0
        fi
        sleep 1
    done

    log_error "$process_name: 停止失敗 (PID: $pid)"
    return 1
}

stop_process_group() {
    local pgid="$1"
    local process_name="${2:-PGID $pgid}"

    log_info "$process_name: プロセスグループ全体を停止中... (PGID: $pgid)"

    if [ "$DRY_RUN" = false ]; then
        # プロセスグループ全体にSIGTERM
        kill -TERM -"$pgid" 2>/dev/null || {
            log_warn "$process_name: プロセスグループSIGTERM送信失敗"
            return 1
        }

        sleep "$SIGTERM_TIMEOUT"

        # まだ残っているプロセスがあればSIGKILL
        if pgrep -g "$pgid" >/dev/null 2>&1; then
            log_warn "$process_name: プロセスグループ強制終了中..."
            kill -KILL -"$pgid" 2>/dev/null || true
            sleep "$SIGKILL_TIMEOUT"
        fi
    else
        log_debug "[DRY-RUN] kill -TERM -$pgid"
        log_debug "[DRY-RUN] kill -KILL -$pgid"
    fi

    # 確認
    if pgrep -g "$pgid" >/dev/null 2>&1; then
        log_error "$process_name: プロセスグループ停止失敗"
        return 1
    else
        log_info "$process_name: プロセスグループ停止完了"
        return 0
    fi
}

# ========================================
# クリーンアップ関数
# ========================================

cleanup_files() {
    log_info "ファイルクリーンアップ開始"

    local files_to_remove=(
        "$LOCK_FILE"
        "$PID_FILE"
        "/tmp/crypto_bot_*.lock"
        "/tmp/crypto_bot_*.pid"
    )

    for file_pattern in "${files_to_remove[@]}"; do
        if [[ "$file_pattern" == *"*"* ]]; then
            # ワイルドカード展開（安全な処理）
            shopt -s nullglob  # マッチしない場合は空にする
            expanded_files=($file_pattern)
            shopt -u nullglob  # 元に戻す

            # 配列が空でない場合のみ処理
            if [ ${#expanded_files[@]} -gt 0 ]; then
                for file in "${expanded_files[@]}"; do
                    if [ -f "$file" ]; then
                        if [ "$DRY_RUN" = false ]; then
                            rm -f "$file"
                            log_info "削除完了: $file"
                        else
                            log_debug "[DRY-RUN] rm -f $file"
                        fi
                    fi
                done
            fi
        else
            # 単一ファイル
            if [ -f "$file_pattern" ]; then
                if [ "$DRY_RUN" = false ]; then
                    rm -f "$file_pattern"
                    log_info "削除完了: $file_pattern"
                else
                    log_debug "[DRY-RUN] rm -f $file_pattern"
                fi
            fi
        fi
    done
}

check_port_usage() {
    log_debug "ポート使用状況確認"

    # よく使用されるポートをチェック
    local common_ports=(8080 8000 3000 5000)

    for port in "${common_ports[@]}"; do
        local port_usage
        port_usage=$(lsof -ti :$port 2>/dev/null || true)
        if [ -n "$port_usage" ]; then
            log_warn "ポート $port が使用中: PID $port_usage"

            # crypto-bot関連かチェック
            local process_cmd
            process_cmd=$(ps -p "$port_usage" -o command= 2>/dev/null || true)
            if echo "$process_cmd" | grep -E "(crypto|main\.py)" >/dev/null; then
                log_warn "  → crypto-bot関連プロセスがポートを使用中"
            fi
        fi
    done
}

# ========================================
# 検証関数
# ========================================

verify_cleanup() {
    log_info "停止確認開始"

    local remaining_processes
    remaining_processes=$(find_crypto_processes)

    if [ -n "$remaining_processes" ]; then
        log_error "停止に失敗したプロセスが残っています:"
        show_process_details $remaining_processes
        return 1
    else
        log_info "✅ 全てのプロセスが正常に停止されました"
    fi

    # ファイル存在確認
    local remaining_files=()
    for file in "$LOCK_FILE" "$PID_FILE"; do
        if [ -f "$file" ]; then
            remaining_files+=("$file")
        fi
    done

    if [ ${#remaining_files[@]} -gt 0 ]; then
        log_error "削除に失敗したファイルが残っています:"
        printf '  %s\n' "${remaining_files[@]}"
        return 1
    else
        log_info "✅ 全てのファイルが正常に削除されました"
    fi

    return 0
}

# ========================================
# メイン処理
# ========================================

main() {
    # 引数解析
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --dry-run|-n)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "不明なオプション: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    echo ""
    printf "${PURPLE}========================================${NC}\n"
    printf "${PURPLE}🛑 crypto-bot 完全停止スクリプト${NC}\n"
    printf "${PURPLE}========================================${NC}\n"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warn "🧪 DRY-RUN モード: 実際の停止は行いません"
        echo ""
    fi

    # 1. プロセス検出
    log_info "🔍 crypto-bot関連プロセスを検索中..."
    local processes=()
    while IFS= read -r pid; do
        [ -n "$pid" ] && processes+=("$pid")
    done < <(find_crypto_processes)

    if [ ${#processes[@]} -eq 0 ]; then
        log_info "停止対象のプロセスは見つかりませんでした"
        echo ""

        # ファイルクリーンアップのみ実行
        cleanup_files
        check_port_usage

        echo ""
        log_info "✅ 完了: 停止対象なし"
        exit 0
    fi

    # 2. プロセス詳細表示
    show_process_details "${processes[@]}"

    # 3. プロセス停止
    log_info "🛑 プロセス停止開始 (対象: ${#processes[@]}個)"
    echo ""

    local failed_processes=()

    for pid in "${processes[@]}"; do
        # プロセスグループID取得
        local pgid
        pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || echo "")

        local process_name
        process_name=$(ps -p "$pid" -o command= 2>/dev/null | cut -c1-50 || echo "PID $pid")

        if [ -n "$pgid" ] && [ "$pgid" != "$pid" ]; then
            # プロセスグループとして停止
            if ! stop_process_group "$pgid" "$process_name"; then
                failed_processes+=("$pid")
            fi
        else
            # 個別プロセスとして停止
            if ! stop_process_gracefully "$pid" "$process_name"; then
                failed_processes+=("$pid")
            fi
        fi
    done

    echo ""

    # 4. ファイルクリーンアップ
    cleanup_files

    # 5. ポートチェック
    check_port_usage

    # 6. 結果確認
    echo ""
    if verify_cleanup; then
        echo ""
        log_info "🎉 完全停止完了"

        if [ ${#failed_processes[@]} -gt 0 ]; then
            log_warn "一部のプロセス停止に失敗しましたが、システムはクリーンアップされました"
        fi

        echo ""
        exit 0
    else
        echo ""
        log_error "❌ 停止処理に問題が発生しました"
        echo ""
        exit 1
    fi
}

# スクリプト実行
main "$@"