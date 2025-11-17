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
BACKGROUND_MODE=false  # デフォルト: フォアグラウンド実行

# OS判定
OS_TYPE="$(uname -s)"
IS_MACOS=false
if [[ "$OS_TYPE" == "Darwin" ]]; then
    IS_MACOS=true
fi

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
    echo "オプション:"
    echo "  --background バックグラウンド実行（非推奨：Claude Code誤認識の原因）"
    echo ""
    echo "特別コマンド:"
    echo "  status       実行状況確認"
    echo "  stop         強制停止"
    echo "  cleanup      ロックファイル削除"
    echo ""
    echo "例:"
    echo "  $0 local paper              # フォアグラウンド実行（推奨）"
    echo "  $0 local paper --background # バックグラウンド実行（非推奨）"
    echo "  $0 local live               # ローカルライブトレード"
    echo "  $0 gcp live                 # GCP環境ライブトレード"
    echo "  $0 status                   # 実行状況確認"
    echo "  $0 stop                     # 強制停止"
    echo ""
    echo "⚠️ 注意: Claude Codeで実行時は --background を使用しないでください"
    echo "   バックグラウンドプロセスが終了後も'running'として誤認識される問題があります"
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
            local start_time_int=${start_time%.*}  # 小数点以下を削除
            local elapsed=$((current_time - ${start_time_int:-$current_time}))
            local elapsed_min=$((elapsed / 60))

            log_info "✅ プロセス実行中: PID=$pid, 経過時間=${elapsed_min}分"

            # 子プロセス確認
            local children
            children=$(pgrep -P "$pid" 2>/dev/null || true)
            if [ -n "$children" ]; then
                log_info "   └─ 子プロセス: $children"
            fi

            # PIDファイル情報表示
            if [ -f "$PID_FILE" ]; then
                local mode=$(sed -n '3p' "$PID_FILE" 2>/dev/null || echo "")
                if [ -n "$mode" ]; then
                    log_info "   └─ 動作モード: $mode"
                fi
            fi

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

            # プロセスグループID取得
            local pgid
            pgid=$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ' || echo "")

            # プロセスグループ全体に対してSIGTERM送信（OS別処理）
            if [ -n "$pgid" ] && [ "$pgid" != "$pid" ]; then
                log_info "🔄 プロセスグループ停止: PGID=$pgid (OS: $OS_TYPE)"
                if [ "$IS_MACOS" = true ]; then
                    # macOS: プロセスグループ停止（互換性考慮）
                    kill -TERM -"$pgid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
                else
                    # Linux: 標準的なプロセスグループ停止
                    kill -TERM -"$pgid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
                fi
            else
                kill -TERM "$pid" 2>/dev/null
            fi

            if [ $? -eq 0 ]; then
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

                # プロセスグループ全体に対してSIGKILL送信（OS別処理）
                log_warn "⚠️ 強制終了実行 (OS: $OS_TYPE)"
                if [ -n "$pgid" ] && [ "$pgid" != "$pid" ]; then
                    if [ "$IS_MACOS" = true ]; then
                        # macOS: プロセスグループ強制終了（互換性考慮）
                        kill -KILL -"$pgid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
                    else
                        # Linux: 標準的なプロセスグループ強制終了
                        kill -KILL -"$pgid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null
                    fi
                else
                    kill -KILL "$pid" 2>/dev/null
                fi

                if [ $? -eq 0 ]; then
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

    log_info "🌍 実行環境設定: $environment (OS: $OS_TYPE)"

    # 共通環境変数（Python import問題対応）
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
    export PYTHONUNBUFFERED=1

    # 環境別設定
    case "$environment" in
        "local")
            export ENVIRONMENT="local"
            export RUNNING_ON_GCP="false"
            # .envファイルからの環境変数読み込み
            if [ -f "$PROJECT_ROOT/config/secrets/.env" ]; then
                log_info "📄 環境変数読み込み: $PROJECT_ROOT/config/secrets/.env"
                source "$PROJECT_ROOT/config/secrets/.env"
                export BITBANK_API_KEY BITBANK_API_SECRET DISCORD_WEBHOOK_URL
            else
                log_warn "⚠️ .envファイルが見つかりません: $PROJECT_ROOT/config/secrets/.env"
            fi
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

    # Phase 52.4: ペーパートレード時のシステム整合性検証
    if [ "$mode" == "paper" ] && [ -f "$PROJECT_ROOT/scripts/testing/validate_system.sh" ]; then
        log_info "🔍 Phase 52.4: システム整合性検証実行中..."
        if bash "$PROJECT_ROOT/scripts/testing/validate_system.sh" >/dev/null 2>&1; then
            log_info "✅ システム整合性検証完了"
        else
            log_error "❌ システム整合性検証失敗"
            log_error "   Dockerfile・特徴量・戦略の不整合が検出されました"
            log_error "   詳細: bash scripts/testing/validate_system.sh"
            return 1
        fi
    fi

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

    # ペーパーモード時のドローダウン自動リセット
    if [ "$mode" = "paper" ]; then
        # Phase 52.4: モード別パス対応
        DRAWDOWN_FILE="$PROJECT_ROOT/src/core/state/${mode}/drawdown_state.json"
        if [ -f "$DRAWDOWN_FILE" ]; then
            log_info "🔄 ドローダウン状態リセット（ペーパーモード）"
            rm -f "$DRAWDOWN_FILE"
        fi
    fi

    log_info "🚀 暗号資産取引Bot起動開始"
    log_info "   環境: $environment"
    log_info "   モード: $mode"
    log_info "   タイムアウト: ${timeout}秒"
    log_info "   実行方式: $([ "$BACKGROUND_MODE" = true ] && echo "バックグラウンド" || echo "フォアグラウンド")"
    log_info "   PID: $$"

    # バックグラウンドモード時の警告
    if [ "$BACKGROUND_MODE" = true ]; then
        log_warn "⚠️ バックグラウンド実行モード: Claude Code使用時は非推奨"
        log_warn "   プロセス終了後も'running'として誤認識される可能性があります"
    fi

    # PIDファイル作成（親プロセス情報記録）
    echo "$$" > "$PID_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S')" >> "$PID_FILE"
    echo "$mode" >> "$PID_FILE"

    # 実行結果変数
    local result=0

    # バックグラウンド vs フォアグラウンド実行
    if [ "$BACKGROUND_MODE" = true ]; then
        # バックグラウンド実行（従来の方式・非推奨）
        log_warn "🔄 バックグラウンド実行開始（非推奨モード）"

        # Python直接実行（バックグラウンド）
        python3 "$PROJECT_ROOT/main.py" --mode "$mode" &
        local bg_pid=$!
        log_info "✅ バックグラウンドプロセス起動: PID=$bg_pid"
        result=0
    else
        # フォアグラウンド実行（推奨・タイムアウト付き）
        log_info "🔄 フォアグラウンド実行開始（タイムアウト: ${timeout}秒）"

        # タイムアウト監視プロセス開始
        (
            sleep "$timeout"
            if kill -0 $$ 2>/dev/null; then
                log_error "[TIMEOUT] ❌ タイムアウト（${timeout}秒超過）- プロセス強制終了"
                kill -TERM $$ 2>/dev/null || true
            fi
        ) &
        local timeout_pid=$!

        # Python直接実行（フォアグラウンド）
        if python3 "$PROJECT_ROOT/main.py" --mode "$mode"; then
            log_info "✅ Bot正常終了"
            result=0
        else
            result=$?
            log_error "❌ Bot異常終了: 終了コード=$result"
        fi

        # タイムアウト監視プロセス終了
        if kill -0 "$timeout_pid" 2>/dev/null; then
            kill "$timeout_pid" 2>/dev/null || true
        fi
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
    # --backgroundオプション解析
    for arg in "$@"; do
        if [ "$arg" = "--background" ]; then
            BACKGROUND_MODE=true
        fi
    done

    # 引数から--backgroundを除外
    local args=()
    for arg in "$@"; do
        if [ "$arg" != "--background" ]; then
            args+=("$arg")
        fi
    done

    local command="${args[0]:-}"

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

            # bot_manager.shでの完全停止も提案
            echo ""
            echo -e "${BLUE}💡 より確実な停止には以下を実行:${NC}"
            echo "    bash scripts/management/bot_manager.sh stop"
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
            local environment="${args[0]:-$DEFAULT_ENVIRONMENT}"
            local mode="${args[1]:-$DEFAULT_MODE}"

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
    esac
}

# スクリプト実行
main "$@"