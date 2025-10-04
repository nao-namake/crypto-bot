#!/bin/bash

# バックテスト実行スクリプト - Phase 34実装
#
# 機能:
# - 過去データCSV収集（オプション）
# - バックテスト実行
# - 結果レポート表示
#
# 使用方法:
#   bash scripts/backtest/run_backtest.sh               # デフォルト: 180日間バックテスト
#   bash scripts/backtest/run_backtest.sh --days 30     # 30日間バックテスト
#   bash scripts/backtest/run_backtest.sh --collect     # データ収集のみ
#   bash scripts/backtest/run_backtest.sh --help        # ヘルプ表示

set -euo pipefail

# ========================================
# 設定・定数定義
# ========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# デフォルト値
DEFAULT_DAYS=180
COLLECT_ONLY=false
DAYS=$DEFAULT_DAYS

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
    echo "使用方法: $0 [options]"
    echo ""
    echo "オプション:"
    echo "  --days N        バックテスト期間（日数） [default: 180]"
    echo "  --collect       データ収集のみ実行"
    echo "  --skip-collect  データ収集をスキップ"
    echo "  --help          ヘルプ表示"
    echo ""
    echo "例:"
    echo "  $0                      # 180日間バックテスト実行"
    echo "  $0 --days 30            # 30日間バックテスト実行"
    echo "  $0 --collect --days 90  # 90日間データ収集のみ"
    echo "  $0 --skip-collect       # データ収集スキップしてバックテスト実行"
}

# ========================================
# データ収集関数
# ========================================

collect_csv_data() {
    local days=$1

    log_info "📊 過去データCSV収集開始: ${days}日間"

    # Python環境設定
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
    export PYTHONUNBUFFERED=1

    # CSV収集実行
    python3 "$PROJECT_ROOT/src/backtest/scripts/collect_historical_csv.py" --days "$days"

    if [ $? -eq 0 ]; then
        log_info "✅ CSVデータ収集完了"
        return 0
    else
        log_error "❌ CSVデータ収集失敗"
        return 1
    fi
}

# ========================================
# バックテスト実行関数
# ========================================

run_backtest() {
    log_info "🚀 バックテスト実行開始"

    # 環境変数設定
    export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
    export PYTHONUNBUFFERED=1
    export ENVIRONMENT="local"
    export RUNNING_ON_GCP="false"

    # .envファイル読み込み
    if [ -f "$PROJECT_ROOT/config/secrets/.env" ]; then
        log_info "📄 環境変数読み込み: $PROJECT_ROOT/config/secrets/.env"
        source "$PROJECT_ROOT/config/secrets/.env"
        export BITBANK_API_KEY BITBANK_API_SECRET DISCORD_WEBHOOK_URL
    else
        log_warn "⚠️ .envファイルが見つかりません"
    fi

    # プロジェクトディレクトリに移動
    cd "$PROJECT_ROOT"

    # ドローダウン状態リセット（バックテストモード）
    DRAWDOWN_FILE="$PROJECT_ROOT/src/core/state/backtest/drawdown_state.json"
    if [ -f "$DRAWDOWN_FILE" ]; then
        log_info "🔄 ドローダウン状態リセット（バックテストモード）"
        rm -f "$DRAWDOWN_FILE"
    fi

    # バックテスト実行
    log_info "🔄 バックテスト実行中..."
    python3 "$PROJECT_ROOT/main.py" --mode backtest

    local result=$?

    if [ $result -eq 0 ]; then
        log_info "✅ バックテスト実行完了"
        return 0
    else
        log_error "❌ バックテスト実行失敗: 終了コード=$result"
        return 1
    fi
}

# ========================================
# レポート表示関数
# ========================================

show_backtest_report() {
    log_info "📈 バックテスト結果レポート"

    # バックテストログディレクトリ
    LOG_DIR="$PROJECT_ROOT/src/backtest/logs"

    if [ ! -d "$LOG_DIR" ]; then
        log_warn "⚠️ バックテストログディレクトリが見つかりません: $LOG_DIR"
        return
    fi

    # 最新のレポートファイルを探す
    latest_report=$(find "$LOG_DIR" -name "backtest_report_*.txt" -type f -print0 | xargs -0 ls -t 2>/dev/null | head -1)

    if [ -n "$latest_report" ] && [ -f "$latest_report" ]; then
        log_info "📄 最新レポート: $latest_report"
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}📊 バックテスト結果サマリー${NC}"
        echo -e "${BLUE}========================================${NC}"
        cat "$latest_report" | head -50
        echo ""
        log_info "📁 詳細レポート: $latest_report"
    else
        log_warn "⚠️ バックテストレポートファイルが見つかりません"
    fi
}

# ========================================
# メイン処理
# ========================================

main() {
    # 引数解析
    SKIP_COLLECT=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --days)
                DAYS="$2"
                shift 2
                ;;
            --collect)
                COLLECT_ONLY=true
                shift
                ;;
            --skip-collect)
                SKIP_COLLECT=true
                shift
                ;;
            --help|-h)
                show_usage
                exit 0
                ;;
            *)
                log_error "❌ 不正な引数: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🚀 バックテスト実行システム - Phase 34${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    # データ収集
    if [ "$SKIP_COLLECT" = false ]; then
        if ! collect_csv_data "$DAYS"; then
            log_error "❌ データ収集失敗"
            exit 1
        fi
        echo ""
    else
        log_info "⏭️ データ収集をスキップ"
        echo ""
    fi

    # 収集のみモード
    if [ "$COLLECT_ONLY" = true ]; then
        log_info "✅ データ収集完了（収集のみモード）"
        exit 0
    fi

    # バックテスト実行
    if run_backtest; then
        echo ""
        show_backtest_report
        echo ""
        echo -e "${GREEN}🎉 バックテスト完了${NC}"
        echo ""
        exit 0
    else
        echo ""
        echo -e "${RED}❌ バックテスト失敗${NC}"
        echo ""
        exit 1
    fi
}

# スクリプト実行
main "$@"
