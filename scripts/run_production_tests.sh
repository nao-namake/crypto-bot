#!/bin/bash
# =============================================================================
# scripts/run_production_tests.sh
# 本番環境向け統合テストを安全に実行するスクリプト
# - API互換性チェック
# - 最小額での注文テスト
# - 実際の残高・取引機能の検証
# =============================================================================

set -euo pipefail

# スクリプトディレクトリの取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# 色付きログ出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 使用方法の表示
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [EXCHANGE]

実際の取引所APIを使った本番環境統合テストを実行します。

OPTIONS:
    -h, --help          このヘルプを表示
    -a, --all           全ての取引所をテスト
    -s, --slow          実際の注文テスト（@pytest.mark.slow）も実行
    -c, --compatibility  API互換性チェックのみ実行
    -v, --verbose       詳細ログを出力

EXCHANGE:
    bybit      Bybit Testnet でのテスト
    bitbank    Bitbank 本番環境でのテスト（要APIキー）
    bitflyer   BitFlyer 本番環境でのテスト（要APIキー）
    okcoinjp   OKCoinJP 本番環境でのテスト（要APIキー）

Environment Variables（必要なもの）:
    BYBIT_TESTNET_API_KEY      Bybit Testnet APIキー
    BYBIT_TESTNET_API_SECRET   Bybit Testnet シークレット
    BITBANK_API_KEY           Bitbank APIキー
    BITBANK_API_SECRET        Bitbank シークレット
    BITFLYER_API_KEY          BitFlyer APIキー
    BITFLYER_API_SECRET       BitFlyer シークレット
    OKCOINJP_API_KEY          OKCoinJP APIキー
    OKCOINJP_API_SECRET       OKCoinJP シークレット
    OKCOINJP_PASSPHRASE       OKCoinJP パスフレーズ

Examples:
    $0 bybit                   # Bybit Testnet のテスト
    $0 -s bitbank             # Bitbank で実注文テストも実行
    $0 -a -c                  # 全取引所のAPI互換性チェック
    $0 -v bitflyer            # BitFlyer の詳細テスト

注意事項:
- 本番環境のテストでは実際の資産が必要です
- --slow オプション使用時は最小額での注文が発生する可能性があります
- テストネット以外では十分な残高があることを確認してください
EOF
}

# 引数の解析
EXCHANGE=""
RUN_SLOW_TESTS=false
COMPATIBILITY_ONLY=false
VERBOSE=false
TEST_ALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -a|--all)
            TEST_ALL=true
            shift
            ;;
        -s|--slow)
            RUN_SLOW_TESTS=true
            shift
            ;;
        -c|--compatibility)
            COMPATIBILITY_ONLY=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        bybit|bitbank|bitflyer|okcoinjp)
            EXCHANGE="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# プロジェクトルートに移動
cd "${PROJECT_ROOT}"

# 仮想環境の確認
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    log_warn "仮想環境が有効化されていません。.venv を有効化します..."
    if [[ -f ".venv/bin/activate" ]]; then
        source .venv/bin/activate
    else
        log_error "仮想環境が見つかりません。'python -m venv .venv' で作成してください。"
        exit 1
    fi
fi

# 必要なパッケージの確認
log_info "必要なパッケージを確認しています..."
pip install -q -e .
pip install -q -r requirements/dev.txt

# pytest オプションの設定
PYTEST_ARGS="-v"
if [[ "$VERBOSE" == "true" ]]; then
    PYTEST_ARGS="$PYTEST_ARGS -s"
fi

if [[ "$RUN_SLOW_TESTS" == "true" ]]; then
    PYTEST_ARGS="$PYTEST_ARGS --runslow"
else
    PYTEST_ARGS="$PYTEST_ARGS -m 'not slow'"
fi

# 互換性チェック関数
run_compatibility_check() {
    local exchange="$1"
    log_info "API互換性チェックを実行中: $exchange"
    
    python -c "
from crypto_bot.execution.api_version_manager import ApiVersionManager
import json

manager = ApiVersionManager()
report = manager.validate_api_compatibility('$exchange')
print(json.dumps(report, indent=2, ensure_ascii=False))

if report['overall_status'] != 'PASS':
    exit(1)
"
}

# 取引所テスト実行関数
run_exchange_test() {
    local exchange="$1"
    log_info "取引所テストを実行中: $exchange"
    
    # 互換性チェック
    if ! run_compatibility_check "$exchange"; then
        log_error "$exchange のAPI互換性チェックに失敗しました"
        return 1
    fi
    
    if [[ "$COMPATIBILITY_ONLY" == "true" ]]; then
        log_success "$exchange の互換性チェックが完了しました"
        return 0
    fi
    
    # 統合テストの実行
    local test_path=""
    case "$exchange" in
        bybit)
            test_path="tests/integration/bybit/test_bybit_e2e.py"
            ;;
        bitbank)
            test_path="tests/integration/bitbank/test_bitbank_e2e.py"
            ;;
        bitflyer)
            test_path="tests/integration/bitflyer/test_bitflyer_e2e_real.py"
            ;;
        okcoinjp)
            test_path="tests/integration/okcoinjp/test_okcoinjp_e2e_real.py"
            ;;
    esac
    
    if [[ -f "$test_path" ]]; then
        log_info "$exchange の統合テストを実行中..."
        if pytest $PYTEST_ARGS "$test_path"; then
            log_success "$exchange のテストが成功しました"
        else
            log_error "$exchange のテストに失敗しました"
            return 1
        fi
    else
        log_warn "$exchange のテストファイルが見つかりません: $test_path"
    fi
}

# 環境変数チェック関数
check_env_vars() {
    local exchange="$1"
    local missing_vars=()
    
    case "$exchange" in
        bybit)
            [[ -z "${BYBIT_TESTNET_API_KEY:-}" ]] && missing_vars+=("BYBIT_TESTNET_API_KEY")
            [[ -z "${BYBIT_TESTNET_API_SECRET:-}" ]] && missing_vars+=("BYBIT_TESTNET_API_SECRET")
            ;;
        bitbank)
            [[ -z "${BITBANK_API_KEY:-}" ]] && missing_vars+=("BITBANK_API_KEY")
            [[ -z "${BITBANK_API_SECRET:-}" ]] && missing_vars+=("BITBANK_API_SECRET")
            ;;
        bitflyer)
            [[ -z "${BITFLYER_API_KEY:-}" ]] && missing_vars+=("BITFLYER_API_KEY")
            [[ -z "${BITFLYER_API_SECRET:-}" ]] && missing_vars+=("BITFLYER_API_SECRET")
            ;;
        okcoinjp)
            [[ -z "${OKCOINJP_API_KEY:-}" ]] && missing_vars+=("OKCOINJP_API_KEY")
            [[ -z "${OKCOINJP_API_SECRET:-}" ]] && missing_vars+=("OKCOINJP_API_SECRET")
            [[ -z "${OKCOINJP_PASSPHRASE:-}" ]] && missing_vars+=("OKCOINJP_PASSPHRASE")
            ;;
    esac
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_warn "$exchange のテストに必要な環境変数が設定されていません: ${missing_vars[*]}"
        if [[ "$COMPATIBILITY_ONLY" != "true" ]]; then
            log_warn "API互換性チェックのみ実行します"
        fi
        return 1
    fi
    
    return 0
}

# メイン実行
main() {
    log_info "本番環境統合テストを開始します"
    
    if [[ "$RUN_SLOW_TESTS" == "true" ]]; then
        log_warn "実際の注文テスト（@pytest.mark.slow）が有効です。実際の取引が発生する可能性があります。"
        echo -n "続行しますか？ [y/N]: "
        read -r answer
        if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
            log_info "テストを中止しました"
            exit 0
        fi
    fi
    
    local exchanges_to_test=()
    local failed_exchanges=()
    
    if [[ "$TEST_ALL" == "true" ]]; then
        exchanges_to_test=("bybit" "bitbank" "bitflyer" "okcoinjp")
    elif [[ -n "$EXCHANGE" ]]; then
        exchanges_to_test=("$EXCHANGE")
    else
        log_error "テストする取引所を指定してください。-h でヘルプを表示します。"
        exit 1
    fi
    
    for exchange in "${exchanges_to_test[@]}"; do
        log_info "=== $exchange のテストを開始 ==="
        
        # 環境変数チェック
        if ! check_env_vars "$exchange"; then
            if [[ "$COMPATIBILITY_ONLY" != "true" ]]; then
                COMPATIBILITY_ONLY=true
                log_info "環境変数が不足しているため、互換性チェックのみ実行します"
            fi
        fi
        
        # テスト実行
        if run_exchange_test "$exchange"; then
            log_success "$exchange のテストが完了しました"
        else
            failed_exchanges+=("$exchange")
            log_error "$exchange のテストに失敗しました"
        fi
        
        echo ""
    done
    
    # 結果サマリ
    log_info "=== テスト結果サマリ ==="
    local total_tested=${#exchanges_to_test[@]}
    local failed_count=${#failed_exchanges[@]}
    local success_count=$((total_tested - failed_count))
    
    log_info "総テスト数: $total_tested"
    log_success "成功: $success_count"
    
    if [[ $failed_count -gt 0 ]]; then
        log_error "失敗: $failed_count (${failed_exchanges[*]})"
        exit 1
    else
        log_success "全てのテストが成功しました！"
    fi
}

# 実行
main "$@"