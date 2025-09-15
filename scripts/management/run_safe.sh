#!/bin/bash

# 安全な暗号資産取引Bot実行スクリプト
#
# 機能:
# - ローカル/GCP環境の自動判定
# - プロセス重複防止（ロックファイル使用）
# - 環境変数による動作制御
# - タイムアウト管理
# - エラー時の自動クリーンアップ
#
# 使用方法:
#   bash scripts/management/run_safe.sh local paper    # ローカルペーパートレード
#   bash scripts/management/run_safe.sh local live     # ローカルライブトレード
#   bash scripts/management/run_safe.sh gcp live       # GCP環境ライブトレード
#   bash scripts/management/run_safe.sh status         # 実行状況確認
#   bash scripts/management/run_safe.sh stop           # 強制停止

set -euo pipefail

# ========================================
# 設定・定数定義
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOCK_FILE="/tmp/crypto_bot_${USER}.lock"
PID_FILE="/tmp/crypto_bot_${USER}.pid"

# デフォルト値
DEFAULT_ENVIRONMENT="local"
DEFAULT_MODE="paper"
DEFAULT_TIMEOUT=14400  # 4時間

# カラー出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

show_usage() {
    echo "使用方法: $0 [environment] [mode] [options]"
    echo ""
    echo "引数:"
    echo "  environment  実行環境 (local|gcp) [default: local]"
    echo "  mode         動作モード (paper|live|backtest) [default: paper]"
    echo ""
    echo "特別コマンド:"
    echo "  status       実行状況確認"
    echo "  stop         強制停止"
    echo "  cleanup      ロックファイル削除"
    echo ""
    echo "例:"
    echo "  $0 local paper       # ローカルペーパートレード"
    echo "  $0 local live        # ローカルライブトレード"
    echo "  $0 gcp live          # GCP環境ライブトレード"
    echo "  $0 status            # 実行状況確認"
    echo "  $0 stop              # 強制停止"
}

# ========================================
# プロセス管理関数
# ========================================

check_process_status() {
    if [ -f "$LOCK_FILE" ]; then
        local pid=$(head -n 1 "$LOCK_FILE" 2>/dev/null || echo "")
        local start_time=$(sed -n '2p' "$LOCK_FILE" 2>/dev/null || echo "")

        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            local current_time=$(date +%s)
            local elapsed=$((current_time - ${start_time:-$current_time}))
            local elapsed_min=$((elapsed / 60))

            log_info "✅ プロセス実行中: PID=$pid, 経過時間=${elapsed_min}分"
            return 0
        else
            log_warn "⚠️ ロックファイルが存在しますが、プロセスは実行されていません"
            return 1
        fi
    else
        log_info "📋 プロセス停止中"
        return 1
    fi
}

acquire_lock() {
    if check_process_status; then
        log_error "❌ 既にプロセスが実行中です"
        return 1
    fi

    # 古いロックファイルをクリーンアップ
    if [ -f "$LOCK_FILE" ]; then
        log_warn "🧹 古いロックファイルを削除"
        rm -f "$LOCK_FILE"
    fi

    # 新しいロック作成
    echo "$$" > "$LOCK_FILE"
    echo "$(date +%s)" >> "$LOCK_FILE"

    log_info "🔒 プロセスロック取得: PID=$$"
    return 0
}

release_lock() {
    if [ -f "$LOCK_FILE" ]; then
        rm -f "$LOCK_FILE"
        log_info "🔓 プロセスロック解除"
    fi

    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
    fi
}

stop_process() {
    if check_process_status; then
        local pid=$(head -n 1 "$LOCK_FILE" 2>/dev/null || echo "")

        if [ -n "$pid" ]; then
            log_info "🛑 プロセス停止中: PID=$pid"

            # SIGTERM送信
            if kill -TERM "$pid" 2>/dev/null; then
                log_info "⏳ 正常終了を待機中..."

                # 30秒待機
                for i in {1..30}; do
                    if ! kill -0 "$pid" 2>/dev/null; then
                        log_info "✅ プロセス正常終了"
                        release_lock
                        return 0
                    fi
                    sleep 1
                done

                # SIGKILL送信
                log_warn "⚠️ 強制終了実行"
                if kill -KILL "$pid" 2>/dev/null; then
                    log_info "✅ プロセス強制終了"
                else
                    log_error "❌ プロセス終了失敗"
                fi
            else
                log_error "❌ プロセス停止失敗: PID=$pid"
            fi
        fi

        release_lock
    else
        log_info "📋 停止対象のプロセスはありません"
    fi
}

cleanup_files() {
    log_info "🧹 ロックファイルクリーンアップ"
    rm -f "$LOCK_FILE" "$PID_FILE"
    log_info "✅ クリーンアップ完了"
}

# ========================================
# 環境設定関数
# ========================================

setup_environment() {
    local environment="$1"
    local mode="$2"

    log_info "🌍 実行環境設定: $environment"

    # 共通環境変数
    export PYTHONPATH="$PROJECT_ROOT"
    export PYTHONUNBUFFERED=1

    # 環境別設定
    case "$environment" in
        "local")
            export ENVIRONMENT="local"
            export RUNNING_ON_GCP="false"
            log_info "💻 ローカル環境設定完了"
            ;;
        "gcp")
            export ENVIRONMENT="gcp"
            export RUNNING_ON_GCP="true"
            export LOG_LEVEL="INFO"
            log_info "☁️ GCP環境設定完了"
            ;;
        *)
            log_error "❌ 不正な環境: $environment"
            return 1
            ;;
    esac

    log_info "🎯 動作モード: $mode"

    return 0
}

# ========================================
# 実行管理関数
# ========================================

run_bot() {
    local environment="$1"
    local mode="$2"
    local timeout="${3:-$DEFAULT_TIMEOUT}"

    # ロック取得
    if ! acquire_lock; then
        return 1
    fi

    # クリーンアップのトラップ設定
    trap 'release_lock; exit 1' INT TERM EXIT

    # 環境設定
    if ! setup_environment "$environment" "$mode"; then
        release_lock
        return 1
    fi

    # プロジェクトディレクトリに移動
    cd "$PROJECT_ROOT"

    log_info "🚀 暗号資産取引Bot起動開始"
    log_info "   環境: $environment"
    log_info "   モード: $mode"
    log_info "   タイムアウト: ${timeout}秒"
    log_info "   PID: $$"

    # PIDファイル作成
    echo "$$" > "$PID_FILE"

    # タイムアウト設定（GCP環境のみ）
    if [ "$environment" = "gcp" ]; then
        (
            sleep "$timeout"
            log_warn "⏰ タイムアウト（${timeout}秒）により終了"
            kill -TERM $$ 2>/dev/null || true
        ) &
        timeout_pid=$!
    fi

    # Bot実行
    if python3 main.py --mode "$mode"; then
        log_info "✅ Bot正常終了"
        result=0
    else
        log_error "❌ Bot異常終了"
        result=1
    fi

    # タイムアウトプロセス終了
    if [ "$environment" = "gcp" ] && [ -n "${timeout_pid:-}" ]; then
        kill "$timeout_pid" 2>/dev/null || true
    fi

    # トラップ解除とクリーンアップ
    trap - INT TERM EXIT
    release_lock

    return $result
}

run_with_monitoring() {
    local environment="$1"
    local mode="$2"

    log_info "📊 監視付き実行開始"

    # リソース使用量記録
    local start_time=$(date +%s)

    # Bot実行
    if run_bot "$environment" "$mode"; then
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        local elapsed_min=$((elapsed / 60))

        log_info "✅ 実行完了: 経過時間=${elapsed_min}分"
        return 0
    else
        log_error "❌ 実行失敗"
        return 1
    fi
}

# ========================================
# メイン処理
# ========================================

main() {
    local command="${1:-}"

    case "$command" in
        "status")
            echo ""
            echo -e "${BLUE}========================================${NC}"
            echo -e "${BLUE}📊 暗号資産取引Bot実行状況${NC}"
            echo -e "${BLUE}========================================${NC}"
            echo ""
            check_process_status
            echo ""
            ;;

        "stop")
            echo ""
            echo -e "${YELLOW}🛑 プロセス停止実行${NC}"
            echo ""
            stop_process
            echo ""
            ;;

        "cleanup")
            echo ""
            echo -e "${YELLOW}🧹 クリーンアップ実行${NC}"
            echo ""
            cleanup_files
            echo ""
            ;;

        "help"|"--help"|"-h")
            show_usage
            ;;

        "")
            log_error "❌ 引数が指定されていません"
            echo ""
            show_usage
            exit 1
            ;;

        *)
            # 通常実行
            local environment="${1:-$DEFAULT_ENVIRONMENT}"
            local mode="${2:-$DEFAULT_MODE}"

            # 引数検証
            if [[ ! "$environment" =~ ^(local|gcp)$ ]]; then
                log_error "❌ 不正な環境: $environment"
                echo ""
                show_usage
                exit 1
            fi

            if [[ ! "$mode" =~ ^(paper|live|backtest)$ ]]; then
                log_error "❌ 不正なモード: $mode"
                echo ""
                show_usage
                exit 1
            fi

            echo ""
            echo -e "${BLUE}========================================${NC}"
            echo -e "${BLUE}🚀 暗号資産取引Bot安全実行${NC}"
            echo -e "${BLUE}========================================${NC}"
            echo ""

            if run_with_monitoring "$environment" "$mode"; then
                echo ""
                echo -e "${GREEN}🎉 実行完了${NC}"
                echo ""
                exit 0
            else
                echo ""
                echo -e "${RED}❌ 実行失敗${NC}"
                echo ""
                exit 1
            fi
            ;;
    esac
}

# スクリプト実行
main "$@"