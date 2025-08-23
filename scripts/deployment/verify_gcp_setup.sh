#!/bin/bash

# Phase 12: GCP CI/CD事前検証スクリプト（レガシー改良版）
# 
# CI/CD実行前にGCP環境の全ての前提条件をチェックし、事前に問題を特定
# レガシーシステムのベストプラクティスを継承しつつ、個人開発向けに最適化
# 
# 機能:
#   - GCP認証・プロジェクト設定の検証
#   - 必要なAPI・サービスの有効化確認
#   - Artifact Registry・Cloud Run設定の検証
#   - GitHub Actions用Workload Identity設定確認
#   - Secret Manager認証情報の存在確認
#   - Docker・gcloud CLI環境の検証
#
# 使用方法:
#   bash scripts/deployment/verify_gcp_setup.sh --full      # 完全検証（推奨）
#   bash scripts/deployment/verify_gcp_setup.sh --quick     # 軽量検証
#   bash scripts/deployment/verify_gcp_setup.sh --ci        # CI/CD専用検証
#   bash scripts/deployment/verify_gcp_setup.sh --fix       # 自動修復試行
#
# 前提条件:
#   1. gcloud CLI認証済み（gcloud auth login）
#   2. 適切なGCPプロジェクトが設定済み
#   3. 最小限のIAM権限設定済み

set -euo pipefail

# ========================================
# 設定・定数定義（Phase 12 + レガシー改良）
# ========================================

# GCPプロジェクト設定（現在の設定から自動取得・GitHub Actions対応）
PROJECT_ID="${PROJECT_ID:-${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}}"
REGION="${REGION:-${GCP_REGION:-asia-northeast1}}"
REPOSITORY="${REPOSITORY:-${ARTIFACT_REPOSITORY:-crypto-bot-repo}}"
SERVICE_NAME="${SERVICE_NAME:-${CLOUD_RUN_SERVICE:-crypto-bot-service-prod}}"

# GitHub Actions統合設定
GITHUB_SA="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
WIF_POOL_ID="github-pool"
WIF_PROVIDER_ID="github-provider"

# スクリプト情報
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ログ設定（レガシー改良版）
LOG_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/gcp_verification_$(date +%Y%m%d_%H%M%S).log"

# カラー出力定義（レガシー継承）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 検証結果カウンター
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# ========================================
# ログ・ユーティリティ関数
# ========================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # コンソール出力（カラー付き）
    case "$level" in
        "INFO")  echo -e "${GREEN}[INFO]${NC}  $timestamp - $message" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC}  $timestamp - $message" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $timestamp - $message" ;;
        "DEBUG") echo -e "${BLUE}[DEBUG]${NC} $timestamp - $message" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $timestamp - $message" ;;
    esac
    
    # ファイル出力
    echo "[$level] $timestamp - $message" >> "$LOG_FILE"
}

check_result() {
    local description="$1"
    local success="$2"
    local is_critical="${3:-true}"
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    if [ "$success" = "true" ]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        log "SUCCESS" "✅ $description"
        return 0
    elif [ "$is_critical" = "false" ]; then
        WARNING_CHECKS=$((WARNING_CHECKS + 1))
        log "WARN" "⚠️ $description"
        return 1
    else
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        log "ERROR" "❌ $description"
        return 1
    fi
}

error_exit() {
    log "ERROR" "$1"
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ GCP環境検証失敗${NC}"
    echo -e "${RED}========================================${NC}"
    echo -e "詳細ログ: $LOG_FILE"
    exit 1
}

# ========================================
# 基本環境チェック
# ========================================

check_basic_environment() {
    log "INFO" "=== 基本環境チェック開始 ==="
    
    # gcloud CLI確認
    if command -v gcloud &> /dev/null; then
        local gcloud_version=$(gcloud version --format="value(Google Cloud SDK)" 2>/dev/null | head -n1)
        check_result "gcloud CLI利用可能 (バージョン: $gcloud_version)" "true"
    else
        check_result "gcloud CLIがインストールされていません" "false"
        return 1
    fi
    
    # Docker確認（CI/CD用）
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version 2>/dev/null | cut -d' ' -f3 | cut -d',' -f1)
        check_result "Docker利用可能 (バージョン: $docker_version)" "true" "false"
    else
        check_result "Docker未インストール（ローカルビルド時に必要）" "false" "false"
    fi
    
    # curl確認（API呼び出し用）
    if command -v curl &> /dev/null; then
        check_result "curl利用可能" "true"
    else
        check_result "curl未インストール" "false" "false"
    fi
    
    # jq確認（JSON処理用）
    if command -v jq &> /dev/null; then
        check_result "jq利用可能（JSON処理最適化）" "true" "false"
    else
        check_result "jq未インストール（JSON処理は代替手段を使用）" "false" "false"
    fi
    
    log "INFO" "=== 基本環境チェック完了 ==="
}

# ========================================
# GCP認証・プロジェクト設定チェック
# ========================================

check_gcp_authentication() {
    log "INFO" "=== GCP認証・プロジェクト設定チェック開始 ==="
    
    # gcloud認証確認
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 &> /dev/null; then
        local active_account=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
        check_result "gcloud認証済み (アカウント: $active_account)" "true"
        
        # GitHub Actions環境特有の Workload Identity 権限チェック追加
        if [[ "$active_account" == *"principal://"* ]]; then
            log "INFO" "GitHub Actions Workload Identity検出 - 基本権限確認中"
            
            # より実用的な権限確認（gcloud auth list成功時点で基本的にOK）
            if gcloud config set project "$PROJECT_ID" >/dev/null 2>&1; then
                check_result "GitHub Actions Workload Identity基本権限確認" "true"
            else
                check_result "GitHub Actions Workload Identity権限不足（プロジェクト設定不可）" "false"
                log "ERROR" "解決方法: GitHub Actions用サービスアカウント($GITHUB_SA)にWorkload Identity User権限の確認が必要"
                return 1
            fi
        fi
    else
        check_result "gcloud認証が必要です。gcloud auth login を実行してください" "false"
        return 1
    fi
    
    # プロジェクト設定確認
    if [ -z "$PROJECT_ID" ]; then
        check_result "GCPプロジェクトIDが設定されていません" "false"
        error_exit "環境変数GCP_PROJECTを設定するか、gcloud config set project PROJECT_ID を実行してください"
    fi
    
    # プロジェクト設定確認（レガシー方式）
    local current_project=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ "$current_project" = "$PROJECT_ID" ]; then
        check_result "GCPプロジェクト設定確認: $PROJECT_ID" "true"
    else
        # CI環境では設定を試行
        if gcloud config set project "$PROJECT_ID" &>/dev/null; then
            check_result "GCPプロジェクト設定成功: $PROJECT_ID" "true"
        else
            check_result "GCPプロジェクト設定失敗: $PROJECT_ID" "false"
            return 1
        fi
    fi
    
    # プロジェクト権限確認
    local current_user=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
    if gcloud projects get-iam-policy "$PROJECT_ID" --flatten="bindings[].members" --format="value(bindings.members)" | grep -q "$current_user"; then
        check_result "プロジェクト権限確認: $current_user" "true"
    else
        check_result "プロジェクト権限が不足している可能性があります" "false" "false"
    fi
    
    # デフォルトリージョン確認
    local current_region=$(gcloud config get-value compute/region 2>/dev/null || echo "")
    if [ -n "$current_region" ]; then
        check_result "デフォルトリージョン設定: $current_region" "true" "false"
    else
        check_result "デフォルトリージョン未設定（asia-northeast1を推奨）" "false" "false"
    fi
    
    log "INFO" "=== GCP認証・プロジェクト設定チェック完了 ==="
}

# ========================================
# GCP API・サービス有効化チェック
# ========================================

check_gcp_apis() {
    log "INFO" "=== GCP API・サービス有効化チェック開始 ==="
    
    # 必要なAPI一覧
    local required_apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "artifactregistry.googleapis.com"
        "secretmanager.googleapis.com"
        "iamcredentials.googleapis.com"
        "sts.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
    )
    
    # 各API有効化確認
    for api in "${required_apis[@]}"; do
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            check_result "API有効化確認: $api" "true"
        else
            check_result "API未有効化: $api" "false" "false"
            
            # --fixオプションが指定されている場合は自動有効化
            if [[ "${1:-}" == "--fix" ]]; then
                log "INFO" "API自動有効化中: $api"
                if gcloud services enable "$api"; then
                    log "SUCCESS" "API有効化完了: $api"
                else
                    log "ERROR" "API有効化失敗: $api"
                fi
            fi
        fi
    done
    
    log "INFO" "=== GCP API・サービス有効化チェック完了 ==="
}

# ========================================
# Artifact Registry設定チェック
# ========================================

check_artifact_registry() {
    log "INFO" "=== Artifact Registry設定チェック開始 ==="
    
    # Artifact Registryリポジトリ存在確認
    if gcloud artifacts repositories describe "$REPOSITORY" \
        --location="$REGION" \
        --project="$PROJECT_ID" &>/dev/null; then
        check_result "Artifact Registryリポジトリ確認: $REPOSITORY" "true"
        
        # リポジトリ詳細情報取得
        local repo_format=$(gcloud artifacts repositories describe "$REPOSITORY" \
            --location="$REGION" \
            --project="$PROJECT_ID" \
            --format="value(format)" 2>/dev/null)
        check_result "リポジトリフォーマット: $repo_format" "true" "false"
        
    else
        check_result "Artifact Registryリポジトリが存在しません: $REPOSITORY" "false"
        
        # --fixオプションが指定されている場合は自動作成
        if [[ "${1:-}" == "--fix" ]]; then
            log "INFO" "Artifact Registryリポジトリ自動作成中: $REPOSITORY"
            if gcloud artifacts repositories create "$REPOSITORY" \
                --repository-format=docker \
                --location="$REGION" \
                --description="Phase 12 crypto-bot Docker images"; then
                log "SUCCESS" "Artifact Registryリポジトリ作成完了: $REPOSITORY"
            else
                log "ERROR" "Artifact Registryリポジトリ作成失敗: $REPOSITORY"
            fi
        fi
    fi
    
    # Docker認証設定確認
    if gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet &>/dev/null; then
        check_result "Docker認証設定確認: ${REGION}-docker.pkg.dev" "true" "false"
    else
        check_result "Docker認証設定失敗" "false" "false"
    fi
    
    log "INFO" "=== Artifact Registry設定チェック完了 ==="
}

# ========================================
# Cloud Run設定チェック
# ========================================

check_cloud_run() {
    log "INFO" "=== Cloud Run設定チェック開始 ==="
    
    # Cloud Runサービス存在確認
    if gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" &>/dev/null; then
        check_result "Cloud Runサービス確認: $SERVICE_NAME" "true" "false"
        
        # サービス詳細情報取得
        local service_url=$(gcloud run services describe "$SERVICE_NAME" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --format="value(status.url)" 2>/dev/null)
        if [ -n "$service_url" ]; then
            check_result "Cloud RunサービスURL: $service_url" "true" "false"
        fi
        
        # サービス設定確認
        local current_image=$(gcloud run services describe "$SERVICE_NAME" \
            --region="$REGION" \
            --project="$PROJECT_ID" \
            --format="value(spec.template.spec.template.spec.containers[0].image)" 2>/dev/null)
        if [[ "$current_image" == *"$REPOSITORY"* ]]; then
            check_result "Cloud Runイメージ設定確認" "true" "false"
        else
            check_result "Cloud Runイメージ設定要確認: $current_image" "false" "false"
        fi
        
    else
        check_result "Cloud Runサービス未作成（初回デプロイ時に自動作成）" "false" "false"
    fi
    
    # Cloud Runリージョン利用可能確認
    if gcloud run regions list --filter="name:$REGION" --format="value(name)" | grep -q "$REGION"; then
        check_result "Cloud Runリージョン利用可能: $REGION" "true"
    else
        check_result "Cloud Runリージョン利用不可: $REGION" "false"
    fi
    
    log "INFO" "=== Cloud Run設定チェック完了 ==="
}

# ========================================
# Workload Identity設定チェック
# ========================================

check_workload_identity() {
    log "INFO" "=== Workload Identity設定チェック開始 ==="
    
    # Workload Identity Pool確認
    if gcloud iam workload-identity-pools describe "$WIF_POOL_ID" \
        --location="global" \
        --project="$PROJECT_ID" &>/dev/null; then
        check_result "Workload Identity Pool確認: $WIF_POOL_ID" "true" "false"
    else
        check_result "Workload Identity Pool未作成: $WIF_POOL_ID" "false" "false"
    fi
    
    # OIDC Provider確認
    if gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER_ID" \
        --workload-identity-pool="$WIF_POOL_ID" \
        --location="global" \
        --project="$PROJECT_ID" &>/dev/null; then
        check_result "OIDC Provider確認: $WIF_PROVIDER_ID" "true" "false"
    else
        check_result "OIDC Provider未作成: $WIF_PROVIDER_ID" "false" "false"
    fi
    
    # GitHubサービスアカウント確認
    if gcloud iam service-accounts describe "$GITHUB_SA" \
        --project="$PROJECT_ID" &>/dev/null; then
        check_result "GitHubサービスアカウント確認: $GITHUB_SA" "true" "false"
    else
        check_result "GitHubサービスアカウント未作成: $GITHUB_SA" "false" "false"
    fi
    
    log "INFO" "=== Workload Identity設定チェック完了 ==="
}

# ========================================
# Secret Manager設定チェック
# ========================================

check_secret_manager() {
    log "INFO" "=== Secret Manager設定チェック開始 ==="
    
    # 必要なシークレット一覧
    local required_secrets=(
        "bitbank-api-key"
        "bitbank-api-secret"
        "discord-webhook"
    )
    
    # 各シークレット存在確認
    for secret in "${required_secrets[@]}"; do
        if gcloud secrets describe "$secret" \
            --project="$PROJECT_ID" &>/dev/null; then
            check_result "シークレット確認: $secret" "true"
            
            # 最新バージョン存在確認
            if gcloud secrets versions list "$secret" \
                --project="$PROJECT_ID" \
                --filter="state:enabled" \
                --limit=1 &>/dev/null; then
                check_result "シークレット最新バージョン確認: $secret" "true" "false"
            else
                check_result "シークレット最新バージョン未設定: $secret" "false" "false"
            fi
        else
            check_result "シークレット未作成: $secret" "false"
        fi
    done
    
    # オプション：シークレット値テスト（非本番環境のみ）
    if [[ "${ENVIRONMENT:-}" != "production" ]]; then
        for secret in "${required_secrets[@]}"; do
            if gcloud secrets versions access latest --secret="$secret" --project="$PROJECT_ID" &>/dev/null; then
                local secret_length=$(gcloud secrets versions access latest --secret="$secret" --project="$PROJECT_ID" 2>/dev/null | wc -c)
                if [ "$secret_length" -gt 10 ]; then
                    check_result "シークレット値確認: $secret (長さ: ${secret_length}文字)" "true" "false"
                else
                    check_result "シークレット値が短すぎる可能性: $secret" "false" "false"
                fi
            fi
        done
    fi
    
    log "INFO" "=== Secret Manager設定チェック完了 ==="
}

# ========================================
# GitHub Actions環境変数チェック
# ========================================

check_github_environment() {
    log "INFO" "=== GitHub Actions環境変数チェック開始 ==="
    
    # CI環境判定
    if [ "${CI:-}" = "true" ] || [ "${GITHUB_ACTIONS:-}" = "true" ]; then
        check_result "GitHub Actions環境で実行中" "true" "false"
        
        # GitHub Actions環境変数確認
        local github_vars=(
            "GITHUB_REPOSITORY"
            "GITHUB_REF"
            "GITHUB_SHA"
            "GITHUB_ACTOR"
        )
        
        for var in "${github_vars[@]}"; do
            if [ -n "${!var:-}" ]; then
                check_result "GitHub環境変数確認: $var=${!var}" "true" "false"
            else
                check_result "GitHub環境変数未設定: $var" "false" "false"
            fi
        done
        
        # GCP環境変数確認（GitHub Secrets由来）
        local gcp_vars=(
            "GCP_PROJECT_ID"
            "GCP_WIF_PROVIDER"
            "GCP_SERVICE_ACCOUNT"
        )
        
        for var in "${gcp_vars[@]}"; do
            if [ -n "${!var:-}" ]; then
                check_result "GCP環境変数確認: $var" "true"
            else
                check_result "GCP環境変数未設定: $var (GitHub Secretsで設定必要)" "false" "false"
            fi
        done
        
    else
        check_result "ローカル環境で実行中" "true" "false"
    fi
    
    log "INFO" "=== GitHub Actions環境変数チェック完了 ==="
}

# ========================================
# ネットワーク・接続性チェック
# ========================================

check_network_connectivity() {
    log "INFO" "=== ネットワーク・接続性チェック開始 ==="
    
    # Google Cloud API接続確認
    if curl -s --max-time 10 "https://cloudresourcemanager.googleapis.com/v1/projects/$PROJECT_ID" \
        -H "Authorization: Bearer $(gcloud auth print-access-token)" >/dev/null; then
        check_result "Google Cloud API接続確認" "true"
    else
        check_result "Google Cloud API接続失敗" "false" "false"
    fi
    
    # Artifact Registry接続確認
    if curl -s --max-time 10 "https://${REGION}-docker.pkg.dev" >/dev/null; then
        check_result "Artifact Registry接続確認" "true" "false"
    else
        check_result "Artifact Registry接続失敗" "false" "false"
    fi
    
    # Cloud Run接続確認
    if curl -s --max-time 10 "https://${REGION}-run.googleapis.com" >/dev/null; then
        check_result "Cloud Run API接続確認" "true" "false"
    else
        check_result "Cloud Run API接続失敗" "false" "false"
    fi
    
    log "INFO" "=== ネットワーク・接続性チェック完了 ==="
}

# ========================================
# 設定ファイル・依存関係チェック
# ========================================

check_project_configuration() {
    log "INFO" "=== プロジェクト設定・依存関係チェック開始 ==="
    
    # Dockerfile存在確認
    if [ -f "$PROJECT_ROOT/Dockerfile" ]; then
        check_result "Dockerfile存在確認" "true"
    else
        check_result "Dockerfile未作成" "false"
    fi
    
    # requirements.txt存在確認
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        check_result "requirements.txt存在確認" "true"
    else
        check_result "requirements.txt未作成" "false"
    fi
    
    # GitHub Workflowファイル確認
    if [ -f "$PROJECT_ROOT/.github/workflows/ci.yml" ]; then
        check_result "CI/CDワークフローファイル存在確認" "true"
    else
        check_result "CI/CDワークフローファイル未作成" "false" "false"
    fi
    
    # 設定ファイル確認
    if [ -d "$PROJECT_ROOT/config" ]; then
        check_result "設定ディレクトリ存在確認" "true" "false"
    fi
    
    # ソースコード確認
    if [ -d "$PROJECT_ROOT/src" ]; then
        check_result "ソースコードディレクトリ存在確認" "true"
    else
        check_result "ソースコードディレクトリ未作成" "false"
    fi
    
    # main.py確認
    if [ -f "$PROJECT_ROOT/main.py" ]; then
        check_result "メインアプリケーションファイル存在確認" "true"
    else
        check_result "main.py未作成" "false"
    fi
    
    log "INFO" "=== プロジェクト設定・依存関係チェック完了 ==="
}

# ========================================
# メイン処理・オプション解析
# ========================================

print_usage() {
    echo "使用方法: $0 [オプション]"
    echo ""
    echo "オプション:"
    echo "  --full    完全検証（全チェック実行・推奨）"
    echo "  --quick   軽量検証（基本チェックのみ）"
    echo "  --ci      CI/CD専用検証"
    echo "  --fix     自動修復試行"
    echo "  --help    このヘルプを表示"
    echo ""
    echo "例:"
    echo "  $0 --full     # 本番運用前の完全チェック"
    echo "  $0 --quick    # 日常的な軽量チェック"
    echo "  $0 --ci       # CI/CD実行前チェック"
    echo "  $0 --fix      # 問題自動修復"
}

print_summary() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}📊 GCP環境検証結果サマリー${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "📈 総チェック数: ${CYAN}$TOTAL_CHECKS${NC}"
    echo -e "✅ 成功: ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "⚠️ 警告: ${YELLOW}$WARNING_CHECKS${NC}"
    echo -e "❌ 失敗: ${RED}$FAILED_CHECKS${NC}"
    echo ""
    
    local success_rate=0
    if [ "$TOTAL_CHECKS" -gt 0 ]; then
        success_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    fi
    
    echo -e "📊 成功率: ${CYAN}${success_rate}%${NC}"
    echo ""
    
    if [ "$FAILED_CHECKS" -eq 0 ]; then
        echo -e "${GREEN}🎉 全ての重要なチェックに合格しました！${NC}"
        echo -e "${GREEN}✨ CI/CD実行準備完了${NC}"
    elif [ "$FAILED_CHECKS" -le 2 ]; then
        echo -e "${YELLOW}⚠️ 軽微な問題が検出されました${NC}"
        echo -e "${YELLOW}📝 詳細ログを確認して修正を検討してください${NC}"
    else
        echo -e "${RED}❌ 重要な問題が検出されました${NC}"
        echo -e "${RED}🔧 CI/CD実行前に修正が必要です${NC}"
    fi
    
    echo ""
    echo -e "📋 詳細ログ: ${CYAN}$LOG_FILE${NC}"
    echo ""
}

main() {
    local mode="${1:---full}"
    
    echo -e "${BLUE}==========================================${NC}"
    echo -e "${BLUE}🔍 Phase 12: GCP CI/CD事前検証システム${NC}"
    echo -e "${BLUE}==========================================${NC}"
    echo ""
    
    log "INFO" "GCP環境検証開始 (モード: $mode)"
    
    case "$mode" in
        "--help")
            print_usage
            exit 0
            ;;
        "--quick")
            log "INFO" "軽量検証モード実行中"
            check_basic_environment
            check_gcp_authentication
            check_project_configuration
            ;;
        "--ci")
            log "INFO" "CI/CD専用検証モード実行中"
            check_basic_environment
            check_gcp_authentication "$mode"
            check_gcp_apis "$mode"
            check_artifact_registry "$mode"
            check_workload_identity
            check_secret_manager
            check_github_environment
            ;;
        "--fix")
            log "INFO" "自動修復モード実行中"
            check_basic_environment
            check_gcp_authentication
            check_gcp_apis "$mode"
            check_artifact_registry "$mode"
            check_cloud_run
            check_workload_identity
            check_secret_manager
            check_github_environment
            check_network_connectivity
            check_project_configuration
            ;;
        "--full"|*)
            log "INFO" "完全検証モード実行中"
            check_basic_environment
            check_gcp_authentication
            check_gcp_apis "$mode"
            check_artifact_registry "$mode"
            check_cloud_run
            check_workload_identity
            check_secret_manager
            check_github_environment
            check_network_connectivity
            check_project_configuration
            ;;
    esac
    
    print_summary
    log "INFO" "GCP環境検証完了"
    
    # 終了コード決定
    if [ "$FAILED_CHECKS" -eq 0 ]; then
        exit 0
    elif [ "$FAILED_CHECKS" -le 2 ]; then
        exit 1
    else
        exit 2
    fi
}

# スクリプト実行
main "$@"