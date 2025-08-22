#!/bin/bash

# Phase 12: CI/CD前提条件自動セットアップスクリプト（レガシー改良版）
# 
# verify_gcp_setup.shで検出された問題を自動的に解決し、CI/CD実行準備を完了
# レガシーシステムの自動化パターンを継承しつつ、より包括的な自動セットアップを提供
# 
# 機能:
#   - GCP API・サービスの自動有効化
#   - Artifact Registry・Cloud Run環境の自動構築
#   - GitHub Actions用Workload Identity自動設定
#   - Secret Manager認証情報の対話式設定
#   - CI/CD用IAM権限の自動付与
#   - プロジェクト設定の最適化
#
# 使用方法:
#   bash scripts/deployment/setup_ci_prerequisites.sh --interactive  # 完全対話式セットアップ
#   bash scripts/deployment/setup_ci_prerequisites.sh --automated   # 自動セットアップ（非対話）
#   bash scripts/deployment/setup_ci_prerequisites.sh --verify-only # 検証のみ（変更なし）
#   bash scripts/deployment/setup_ci_prerequisites.sh --repair      # 問題修復専用
#
# 前提条件:
#   1. gcloud CLI認証済み（gcloud auth login）
#   2. 適切なGCPプロジェクトが設定済み
#   3. プロジェクト管理者権限（owner又はeditor）

set -euo pipefail

# ========================================
# 設定・定数定義（Phase 12 + レガシー改良）
# ========================================

# GCPプロジェクト設定（環境変数優先、フォールバック・GitHub Actions対応）
PROJECT_ID="${PROJECT_ID:-${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}}"
REGION="${REGION:-${GCP_REGION:-asia-northeast1}}"
REPOSITORY="${REPOSITORY:-${ARTIFACT_REPOSITORY:-crypto-bot-repo}}"
SERVICE_NAME="${SERVICE_NAME:-${CLOUD_RUN_SERVICE:-crypto-bot-service-prod-prod}}"

# GitHub Actions統合設定
GITHUB_SA_NAME="github-deployer"
GITHUB_SA_EMAIL="${GITHUB_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
WIF_POOL_ID="github-pool"
WIF_PROVIDER_ID="github-provider"

# GitHub repository設定（実際のリポジトリ名に変更必要）
GITHUB_REPO="${GITHUB_REPOSITORY:-YOUR_USERNAME/crypto-bot}"

# スクリプト情報
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ログ設定（レガシー改良版）
LOG_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/ci_prerequisites_setup_$(date +%Y%m%d_%H%M%S).log"

# カラー出力定義（レガシー継承）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# セットアップ進捗カウンター
TOTAL_STEPS=0
COMPLETED_STEPS=0
FAILED_STEPS=0

# ========================================
# ログ・ユーティリティ関数
# ========================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # コンソール出力（カラー付き）
    case "$level" in
        "INFO")    echo -e "${GREEN}[INFO]${NC}    $timestamp - $message" ;;
        "WARN")    echo -e "${YELLOW}[WARN]${NC}    $timestamp - $message" ;;
        "ERROR")   echo -e "${RED}[ERROR]${NC}   $timestamp - $message" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $timestamp - $message" ;;
        "STEP")    echo -e "${BLUE}[STEP]${NC}    $timestamp - $message" ;;
        "PROMPT")  echo -e "${CYAN}[PROMPT]${NC}  $timestamp - $message" ;;
    esac
    
    # ファイル出力
    echo "[$level] $timestamp - $message" >> "$LOG_FILE"
}

step_result() {
    local description="$1"
    local success="$2"
    
    TOTAL_STEPS=$((TOTAL_STEPS + 1))
    
    if [ "$success" = "true" ]; then
        COMPLETED_STEPS=$((COMPLETED_STEPS + 1))
        log "SUCCESS" "✅ $description"
        return 0
    else
        FAILED_STEPS=$((FAILED_STEPS + 1))
        log "ERROR" "❌ $description"
        return 1
    fi
}

error_exit() {
    log "ERROR" "$1"
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ CI/CD前提条件セットアップ失敗${NC}"
    echo -e "${RED}========================================${NC}"
    echo -e "詳細ログ: $LOG_FILE"
    exit 1
}

confirm_action() {
    local message="$1"
    local default="${2:-N}"
    
    echo ""
    echo -e "${YELLOW}確認: $message${NC}"
    echo -n "続行しますか？ [y/N]: "
    
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        return 0
    else
        log "INFO" "ユーザーによりキャンセルされました"
        return 1
    fi
}

# ========================================
# 前提条件確認・初期化
# ========================================

check_prerequisites() {
    log "STEP" "=== 前提条件確認開始 ==="
    
    # プロジェクトID確認
    if [ -z "$PROJECT_ID" ]; then
        error_exit "GCPプロジェクトIDが設定されていません。環境変数GCP_PROJECTを設定するか、gcloud config set project PROJECT_ID を実行してください"
    fi
    
    # gcloud CLI確認
    if ! command -v gcloud &> /dev/null; then
        error_exit "gcloud CLIがインストールされていません"
    fi
    
    # 認証確認
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 &> /dev/null; then
        error_exit "gcloud認証が必要です。gcloud auth login を実行してください"
    fi
    
    # プロジェクト設定確認（レガシー軽量方式）
    local current_project=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ "$current_project" != "$PROJECT_ID" ]; then
        if ! gcloud config set project "$PROJECT_ID" &>/dev/null; then
            error_exit "GCPプロジェクト設定失敗: $PROJECT_ID"
        fi
    fi
    
    # 権限確認（概算）
    local current_user=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1)
    log "INFO" "実行ユーザー: $current_user"
    log "INFO" "対象プロジェクト: $PROJECT_ID"
    log "INFO" "対象リージョン: $REGION"
    
    step_result "前提条件確認完了" "true"
    log "STEP" "=== 前提条件確認完了 ==="
}

# ========================================
# GCP API有効化
# ========================================

enable_required_apis() {
    log "STEP" "=== 必要なGCP API有効化開始 ==="
    
    # 必要なAPI一覧（レガシーシステム分析結果）
    local required_apis=(
        "cloudbuild.googleapis.com"
        "run.googleapis.com"
        "artifactregistry.googleapis.com"
        "secretmanager.googleapis.com"
        "iamcredentials.googleapis.com"
        "sts.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
        "cloudresourcemanager.googleapis.com"
    )
    
    log "INFO" "必要なAPI数: ${#required_apis[@]}"
    
    for api in "${required_apis[@]}"; do
        log "INFO" "API有効化確認中: $api"
        
        if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            step_result "API既に有効化済み: $api" "true"
        else
            log "WARN" "API未有効化、有効化中: $api"
            
            if gcloud services enable "$api" --project="$PROJECT_ID"; then
                step_result "API有効化成功: $api" "true"
                
                # API有効化後の安定化待機
                if [[ "$api" == "artifactregistry.googleapis.com" ]] || [[ "$api" == "run.googleapis.com" ]]; then
                    log "INFO" "API安定化待機中: $api (15秒)"
                    sleep 15
                fi
            else
                step_result "API有効化失敗: $api" "false"
            fi
        fi
    done
    
    log "STEP" "=== 必要なGCP API有効化完了 ==="
}

# ========================================
# Artifact Registry設定
# ========================================

setup_artifact_registry() {
    log "STEP" "=== Artifact Registry設定開始 ==="
    
    # リポジトリ存在確認
    if gcloud artifacts repositories describe "$REPOSITORY" \
        --location="$REGION" \
        --project="$PROJECT_ID" &>/dev/null; then
        step_result "Artifact Registryリポジトリ既存確認: $REPOSITORY" "true"
    else
        log "INFO" "Artifact Registryリポジトリ作成中: $REPOSITORY"
        
        if gcloud artifacts repositories create "$REPOSITORY" \
            --repository-format=docker \
            --location="$REGION" \
            --project="$PROJECT_ID" \
            --description="Phase 12: crypto-bot Docker images repository"; then
            step_result "Artifact Registryリポジトリ作成成功: $REPOSITORY" "true"
            
            # リポジトリ作成後の安定化待機
            log "INFO" "リポジトリ安定化待機中 (10秒)"
            sleep 10
        else
            step_result "Artifact Registryリポジトリ作成失敗: $REPOSITORY" "false"
        fi
    fi
    
    # Docker認証設定
    log "INFO" "Docker認証設定中: ${REGION}-docker.pkg.dev"
    if gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet; then
        step_result "Docker認証設定成功" "true"
    else
        step_result "Docker認証設定失敗" "false"
    fi
    
    log "STEP" "=== Artifact Registry設定完了 ==="
}

# ========================================
# IAMサービスアカウント設定
# ========================================

setup_github_service_account() {
    log "STEP" "=== GitHub Actions用サービスアカウント設定開始 ==="
    
    # サービスアカウント存在確認・作成
    if gcloud iam service-accounts describe "$GITHUB_SA_EMAIL" \
        --project="$PROJECT_ID" &>/dev/null; then
        step_result "サービスアカウント既存確認: $GITHUB_SA_NAME" "true"
    else
        log "INFO" "サービスアカウント作成中: $GITHUB_SA_NAME"
        
        if gcloud iam service-accounts create "$GITHUB_SA_NAME" \
            --display-name="GitHub Actions Service Account" \
            --description="Phase 12: CI/CD automation service account" \
            --project="$PROJECT_ID"; then
            step_result "サービスアカウント作成成功: $GITHUB_SA_NAME" "true"
        else
            step_result "サービスアカウント作成失敗: $GITHUB_SA_NAME" "false"
            return 1
        fi
    fi
    
    # 必要な権限付与（レガシーシステム分析 + CI/CD最適化）
    local required_roles=(
        "roles/artifactregistry.writer"
        "roles/run.developer"
        "roles/secretmanager.secretAccessor"
        "roles/logging.logWriter"
        "roles/monitoring.editor"
        "roles/cloudtrace.agent"
        "roles/storage.objectViewer"
    )
    
    log "INFO" "IAM権限付与開始（${#required_roles[@]}個の権限）"
    
    for role in "${required_roles[@]}"; do
        log "INFO" "IAM権限付与中: $role"
        
        if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$GITHUB_SA_EMAIL" \
            --role="$role" \
            --quiet; then
            step_result "IAM権限付与成功: $role" "true"
        else
            log "WARN" "IAM権限付与失敗（既に設定済みの可能性）: $role"
        fi
    done
    
    log "STEP" "=== GitHub Actions用サービスアカウント設定完了 ==="
}

# ========================================
# Workload Identity設定
# ========================================

setup_workload_identity() {
    log "STEP" "=== Workload Identity設定開始 ==="
    
    # GitHub リポジトリ情報確認
    if [[ "$GITHUB_REPO" == "YOUR_USERNAME/crypto-bot" ]]; then
        log "WARN" "GitHubリポジトリ名が未設定です"
        echo ""
        echo -e "${YELLOW}GitHubリポジトリの情報を入力してください${NC}"
        echo -n "リポジトリ名 (例: username/crypto-bot): "
        read -r repo_input
        
        if [ -n "$repo_input" ]; then
            GITHUB_REPO="$repo_input"
            log "INFO" "GitHubリポジトリ設定: $GITHUB_REPO"
        else
            log "WARN" "GitHubリポジトリ名が未設定のため、手動設定が必要です"
        fi
    fi
    
    # Workload Identity Pool作成
    if gcloud iam workload-identity-pools describe "$WIF_POOL_ID" \
        --location="global" \
        --project="$PROJECT_ID" &>/dev/null; then
        step_result "Workload Identity Pool既存確認: $WIF_POOL_ID" "true"
    else
        log "INFO" "Workload Identity Pool作成中: $WIF_POOL_ID"
        
        if gcloud iam workload-identity-pools create "$WIF_POOL_ID" \
            --location="global" \
            --display-name="GitHub Actions Pool" \
            --description="Phase 12: GitHub Actions用Workload Identity Pool" \
            --project="$PROJECT_ID"; then
            step_result "Workload Identity Pool作成成功: $WIF_POOL_ID" "true"
        else
            step_result "Workload Identity Pool作成失敗: $WIF_POOL_ID" "false"
            return 1
        fi
    fi
    
    # OIDC Provider作成
    if gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER_ID" \
        --workload-identity-pool="$WIF_POOL_ID" \
        --location="global" \
        --project="$PROJECT_ID" &>/dev/null; then
        step_result "OIDC Provider既存確認: $WIF_PROVIDER_ID" "true"
    else
        log "INFO" "OIDC Provider作成中: $WIF_PROVIDER_ID"
        
        if gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER_ID" \
            --workload-identity-pool="$WIF_POOL_ID" \
            --location="global" \
            --issuer-uri="https://token.actions.githubusercontent.com" \
            --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
            --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
            --project="$PROJECT_ID"; then
            step_result "OIDC Provider作成成功: $WIF_PROVIDER_ID" "true"
        else
            step_result "OIDC Provider作成失敗: $WIF_PROVIDER_ID" "false"
            return 1
        fi
    fi
    
    # IAMポリシーバインディング
    local provider_name="projects/${PROJECT_ID}/locations/global/workloadIdentityPools/${WIF_POOL_ID}/providers/${WIF_PROVIDER_ID}"
    
    log "INFO" "Workload Identity IAMバインディング設定中"
    if gcloud iam service-accounts add-iam-policy-binding "$GITHUB_SA_EMAIL" \
        --role="roles/iam.workloadIdentityUser" \
        --member="principalSet://iam.googleapis.com/${provider_name}/attribute.repository/${GITHUB_REPO}" \
        --project="$PROJECT_ID" \
        --quiet; then
        step_result "Workload Identity IAMバインディング成功" "true"
    else
        log "WARN" "Workload Identity IAMバインディング失敗（既に設定済みの可能性）"
    fi
    
    log "STEP" "=== Workload Identity設定完了 ==="
}

# ========================================
# Secret Manager設定
# ========================================

setup_secret_manager() {
    log "STEP" "=== Secret Manager認証情報設定開始 ==="
    
    # 必要なシークレット一覧
    local required_secrets=(
        "bitbank-api-key:Bitbank APIキー"
        "bitbank-api-secret:Bitbank APIシークレット"
        "discord-webhook:Discord WebhookURL"
    )
    
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}🔐 認証情報設定${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}以下の認証情報を設定します:${NC}"
    for secret_info in "${required_secrets[@]}"; do
        local secret_name=$(echo "$secret_info" | cut -d: -f1)
        local secret_desc=$(echo "$secret_info" | cut -d: -f2)
        echo "  - $secret_desc ($secret_name)"
    done
    echo ""
    
    if ! confirm_action "認証情報の設定を開始"; then
        log "INFO" "Secret Manager設定をスキップしました"
        return 0
    fi
    
    for secret_info in "${required_secrets[@]}"; do
        local secret_name=$(echo "$secret_info" | cut -d: -f1)
        local secret_desc=$(echo "$secret_info" | cut -d: -f2)
        
        log "INFO" "シークレット設定中: $secret_name"
        
        # 既存シークレット確認
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
            log "INFO" "シークレット既存確認: $secret_name"
            echo -n "シークレット '$secret_name' を更新しますか？ [y/N]: "
            read -r update_response
            
            if [[ ! "$update_response" =~ ^[Yy]$ ]]; then
                step_result "シークレット設定スキップ: $secret_name" "true"
                continue
            fi
        else
            # 新規シークレット作成
            if gcloud secrets create "$secret_name" \
                --replication-policy="automatic" \
                --labels="managed-by=crypto-bot,environment=production" \
                --project="$PROJECT_ID"; then
                log "SUCCESS" "シークレット作成成功: $secret_name"
            else
                step_result "シークレット作成失敗: $secret_name" "false"
                continue
            fi
        fi
        
        # シークレット値入力
        echo ""
        echo -e "${BLUE}$secret_desc の値を入力してください:${NC}"
        echo -n "値（入力は非表示）: "
        read -s secret_value
        echo ""
        
        if [ -z "$secret_value" ]; then
            log "WARN" "空の値が入力されました。スキップします: $secret_name"
            continue
        fi
        
        # シークレット値設定
        if echo "$secret_value" | gcloud secrets versions add "$secret_name" \
            --data-file=- \
            --project="$PROJECT_ID"; then
            step_result "シークレット値設定成功: $secret_name" "true"
        else
            step_result "シークレット値設定失敗: $secret_name" "false"
        fi
    done
    
    log "STEP" "=== Secret Manager認証情報設定完了 ==="
}

# ========================================
# GitHub Secrets設定情報出力
# ========================================

output_github_secrets_config() {
    log "STEP" "=== GitHub Secrets設定情報出力 ==="
    
    local provider_name="projects/${PROJECT_ID}/locations/global/workloadIdentityPools/${WIF_POOL_ID}/providers/${WIF_PROVIDER_ID}"
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}📋 GitHub Secrets設定情報${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BOLD}以下の値をGitHubリポジトリのSecretsに設定してください:${NC}"
    echo ""
    
    cat << EOF
🔹 Repository Secrets:
   GCP_PROJECT_ID: $PROJECT_ID
   GCP_WIF_PROVIDER: $provider_name
   GCP_SERVICE_ACCOUNT: $GITHUB_SA_EMAIL

🔹 Repository Variables:
   GCP_REGION: $REGION
   ARTIFACT_REPOSITORY: $REPOSITORY
   CLOUD_RUN_SERVICE: $SERVICE_NAME

🔹 設定手順:
   1. GitHubリポジトリの Settings > Secrets and variables > Actions へ移動
   2. 上記の値を Repository secrets / Repository variables に追加
   3. .github/workflows/ci.yml でこれらの値を参照
EOF
    
    echo ""
    echo -e "${CYAN}📝 設定が完了したら、GitHub ActionsでCI/CDパイプラインを実行できます${NC}"
    echo ""
    
    log "STEP" "=== GitHub Secrets設定情報出力完了 ==="
}

# ========================================
# 環境検証・最終確認
# ========================================

verify_setup() {
    log "STEP" "=== セットアップ検証開始 ==="
    
    echo ""
    echo -e "${BLUE}🔍 設定完了状況を検証中...${NC}"
    echo ""
    
    # 事前検証スクリプト実行
    local verify_script="$SCRIPT_DIR/verify_gcp_setup.sh"
    if [ -f "$verify_script" ]; then
        log "INFO" "GCP環境検証スクリプト実行中"
        
        if bash "$verify_script" --ci; then
            step_result "GCP環境検証成功" "true"
        else
            step_result "GCP環境検証で問題検出" "false"
            log "WARN" "詳細は検証スクリプトのログを確認してください"
        fi
    else
        log "WARN" "GCP環境検証スクリプトが見つかりません: $verify_script"
    fi
    
    log "STEP" "=== セットアップ検証完了 ==="
}

# ========================================
# 結果サマリー・レポート
# ========================================

print_setup_summary() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}📊 CI/CD前提条件セットアップ結果${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    echo -e "📈 総ステップ数: ${CYAN}$TOTAL_STEPS${NC}"
    echo -e "✅ 完了: ${GREEN}$COMPLETED_STEPS${NC}"
    echo -e "❌ 失敗: ${RED}$FAILED_STEPS${NC}"
    echo ""
    
    local success_rate=0
    if [ "$TOTAL_STEPS" -gt 0 ]; then
        success_rate=$((COMPLETED_STEPS * 100 / TOTAL_STEPS))
    fi
    
    echo -e "📊 成功率: ${CYAN}${success_rate}%${NC}"
    echo ""
    
    if [ "$FAILED_STEPS" -eq 0 ]; then
        echo -e "${GREEN}🎉 CI/CD前提条件セットアップが完了しました！${NC}"
        echo -e "${GREEN}✨ GitHub Actions CI/CDパイプライン実行準備完了${NC}"
        echo ""
        echo -e "${CYAN}次のステップ:${NC}"
        echo "  1. GitHubリポジトリにSecretsを設定"
        echo "  2. コードをpushしてCI/CDパイプラインを実行"
        echo "  3. Cloud Runサービスのデプロイ確認"
    else
        echo -e "${YELLOW}⚠️ 一部のセットアップでエラーが発生しました${NC}"
        echo -e "${YELLOW}📝 詳細ログを確認して手動で修正してください${NC}"
        echo ""
        echo -e "${CYAN}トラブルシューティング:${NC}"
        echo "  1. 詳細ログの確認: $LOG_FILE"
        echo "  2. GCP権限の確認（owner/editor必要）"
        echo "  3. verify_gcp_setup.sh での問題特定"
    fi
    
    echo ""
    echo -e "📋 詳細ログ: ${CYAN}$LOG_FILE${NC}"
    echo ""
}

# ========================================
# メイン処理・オプション解析
# ========================================

print_usage() {
    echo "使用方法: $0 [オプション]"
    echo ""
    echo "オプション:"
    echo "  --interactive  完全対話式セットアップ（推奨）"
    echo "  --automated    自動セットアップ（非対話）"
    echo "  --verify-only  検証のみ（変更なし）"
    echo "  --repair       問題修復専用"
    echo "  --help         このヘルプを表示"
    echo ""
    echo "例:"
    echo "  $0 --interactive  # 初回セットアップ（推奨）"
    echo "  $0 --automated    # CI/CD環境での自動実行"
    echo "  $0 --verify-only  # 設定確認のみ"
    echo "  $0 --repair       # 問題修復"
}

main() {
    local mode="${1:---interactive}"
    
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}🚀 Phase 12: CI/CD前提条件自動セットアップ${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
    
    log "INFO" "CI/CD前提条件セットアップ開始 (モード: $mode)"
    
    case "$mode" in
        "--help")
            print_usage
            exit 0
            ;;
        "--verify-only")
            log "INFO" "検証専用モード実行中"
            check_prerequisites
            verify_setup
            ;;
        "--repair")
            log "INFO" "問題修復モード実行中"
            check_prerequisites
            enable_required_apis
            setup_artifact_registry
            setup_github_service_account
            setup_workload_identity
            verify_setup
            ;;
        "--automated")
            log "INFO" "自動セットアップモード実行中"
            check_prerequisites
            enable_required_apis
            setup_artifact_registry
            setup_github_service_account
            setup_workload_identity
            output_github_secrets_config
            verify_setup
            ;;
        "--interactive"|*)
            log "INFO" "対話式セットアップモード実行中"
            check_prerequisites
            enable_required_apis
            setup_artifact_registry
            setup_github_service_account
            setup_workload_identity
            setup_secret_manager
            output_github_secrets_config
            verify_setup
            ;;
    esac
    
    print_setup_summary
    log "INFO" "CI/CD前提条件セットアップ完了"
    
    # 終了コード決定
    if [ "$FAILED_STEPS" -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# スクリプト実行
main "$@"