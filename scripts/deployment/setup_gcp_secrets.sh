#!/bin/bash

# Phase 12: GCP Secret Manager自動設定スクリプト（レガシー改良版）
# 
# CI/CDパイプライン稼働のためのSecret Manager認証情報設定
# レガシーシステムの良い部分を継承しつつ、Phase 12対応で大幅改良
# bitbank API・Discord Webhook・GitHub Actions統合を完全自動化
#
# 使用方法:
#   bash scripts/deployment/setup_gcp_secrets.sh --interactive  # 対話式設定
#   bash scripts/deployment/setup_gcp_secrets.sh --check       # 設定確認のみ
#   bash scripts/deployment/setup_gcp_secrets.sh --setup-ci    # CI/CD専用設定
#
# 前提条件:
#   1. gcloud CLI認証済み（gcloud auth login）
#   2. Secret Manager API有効化済み
#   3. 適切なIAM権限設定済み（roles/secretmanager.admin）

set -euo pipefail

# ========================================
# 設定・定数定義（Phase 12 + レガシー改良）
# ========================================

# GCPプロジェクト設定
PROJECT_ID="my-crypto-bot-project"
REGION="asia-northeast1"
GITHUB_SA="github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Workload Identity設定
WIF_POOL_ID="github-pool"
WIF_PROVIDER_ID="github-provider"
GITHUB_REPO="YOUR_GITHUB_USERNAME/crypto-bot"  # 実際のリポジトリに変更必要

# スクリプト情報
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ログ設定（レガシー改良版）
LOG_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/secrets_setup_$(date +%Y%m%d_%H%M%S).log"

# カラー出力定義（レガシー継承）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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
    esac
    
    # ファイル出力
    echo "[$level] $timestamp - $message" >> "$LOG_FILE"
}

error_exit() {
    log "ERROR" "$1"
    exit 1
}

# ========================================
# 前提条件チェック
# ========================================

check_prerequisites() {
    log "INFO" "前提条件チェック開始"
    
    # gcloud CLI確認
    if ! command -v gcloud &> /dev/null; then
        error_exit "gcloud CLIがインストールされていません"
    fi
    
    # 認証確認
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 &> /dev/null; then
        error_exit "gcloud認証が必要です。 gcloud auth login を実行してください"
    fi
    
    # プロジェクト設定確認
    local current_project=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -z "$current_project" ]; then
        error_exit "GCPプロジェクトが設定されていません。 gcloud config set project PROJECT_ID を実行してください"
    fi
    
    log "INFO" "現在のプロジェクト: $current_project"
    
    # Secret Manager API有効化確認
    if ! gcloud services list --enabled --filter="name:secretmanager.googleapis.com" --format="value(name)" | grep -q "secretmanager.googleapis.com"; then
        log "WARN" "Secret Manager APIが有効化されていません。有効化中..."
        gcloud services enable secretmanager.googleapis.com
        sleep 10
    fi
    
    log "INFO" "前提条件チェック完了"
}

# ========================================
# シークレット作成・更新関数
# ========================================

create_or_update_secret() {
    local secret_id="$1"
    local description="$2"
    local prompt_message="$3"
    
    log "INFO" "シークレット処理開始: $secret_id"
    
    # 既存シークレット確認
    if gcloud secrets describe "$secret_id" &>/dev/null; then
        log "WARN" "シークレット '$secret_id' は既に存在します"
        echo -n "更新しますか？ [y/N]: "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log "INFO" "スキップ: $secret_id"
            return 0
        fi
    else
        log "INFO" "新規シークレット作成: $secret_id"
        gcloud secrets create "$secret_id" \
            --replication-policy="automatic" \
            --labels="environment=production,managed-by=crypto-bot" || {
            error_exit "シークレット作成失敗: $secret_id"
        }
    fi
    
    # シークレット値入力
    echo ""
    echo -e "${BLUE}$prompt_message${NC}"
    echo -n "値を入力してください（入力は非表示）: "
    read -s secret_value
    echo ""
    
    if [ -z "$secret_value" ]; then
        error_exit "空の値は設定できません: $secret_id"
    fi
    
    # シークレット値設定
    echo "$secret_value" | gcloud secrets versions add "$secret_id" --data-file=- || {
        error_exit "シークレット値設定失敗: $secret_id"
    }
    
    log "INFO" "シークレット設定完了: $secret_id"
}

# ========================================
# IAMサービスアカウント設定
# ========================================

setup_service_account() {
    log "INFO" "IAMサービスアカウント設定開始"
    
    local sa_name="crypto-bot-runner"
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # サービスアカウント作成（既存確認）
    if ! gcloud iam service-accounts describe "$sa_email" &>/dev/null; then
        log "INFO" "サービスアカウント作成中: $sa_name"
        gcloud iam service-accounts create "$sa_name" \
            --display-name="Crypto Bot Service Account" \
            --description="Phase 12本番運用用サービスアカウント"
    else
        log "INFO" "サービスアカウント確認済み: $sa_email"
    fi
    
    # 必要な権限付与
    local required_roles=(
        "roles/secretmanager.secretAccessor"
        "roles/run.invoker"
        "roles/logging.logWriter"
        "roles/monitoring.editor"
        "roles/cloudtrace.agent"
    )
    
    for role in "${required_roles[@]}"; do
        log "INFO" "IAMロール付与中: $role"
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:$sa_email" \
            --role="$role" \
            --quiet || {
            log "WARN" "IAMロール付与失敗（既に設定済みの可能性）: $role"
        }
    done
    
    log "INFO" "IAMサービスアカウント設定完了"
}

# ========================================
# Workload Identity設定
# ========================================

setup_workload_identity() {
    log "INFO" "Workload Identity設定開始"
    
    local pool_id="github-pool"
    local provider_id="github-provider"
    local sa_email="crypto-bot-runner@${PROJECT_ID}.iam.gserviceaccount.com"
    local github_repo="YOUR_GITHUB_USERNAME/crypto-bot"  # 実際のリポジトリに変更必要
    
    # Workload Identity Pool作成
    if ! gcloud iam workload-identity-pools describe "$pool_id" --location="global" &>/dev/null; then
        log "INFO" "Workload Identity Pool作成中: $pool_id"
        gcloud iam workload-identity-pools create "$pool_id" \
            --location="global" \
            --display-name="GitHub Actions Pool" \
            --description="Phase 12 GitHub Actions用Workload Identity Pool"
    else
        log "INFO" "Workload Identity Pool確認済み: $pool_id"
    fi
    
    # OIDC Provider作成
    local provider_name="projects/${PROJECT_ID}/locations/global/workloadIdentityPools/${pool_id}/providers/${provider_id}"
    if ! gcloud iam workload-identity-pools providers describe "$provider_id" \
        --workload-identity-pool="$pool_id" \
        --location="global" &>/dev/null; then
        
        log "INFO" "OIDC Provider作成中: $provider_id"
        gcloud iam workload-identity-pools providers create-oidc "$provider_id" \
            --workload-identity-pool="$pool_id" \
            --location="global" \
            --issuer-uri="https://token.actions.githubusercontent.com" \
            --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
            --attribute-condition="assertion.repository=='${github_repo}'"
    else
        log "INFO" "OIDC Provider確認済み: $provider_id"
    fi
    
    # IAMポリシーバインディング
    log "INFO" "Workload Identity IAMバインディング設定中"
    gcloud iam service-accounts add-iam-policy-binding "$sa_email" \
        --role="roles/iam.workloadIdentityUser" \
        --member="principalSet://iam.googleapis.com/${provider_name}/attribute.repository/${github_repo}" \
        --quiet || {
        log "WARN" "IAMバインディング設定失敗（既に設定済みの可能性）"
    }
    
    # GitHub Secrets設定値出力
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}GitHub Secrets設定値${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo "以下の値をGitHubリポジトリのSecretsに設定してください:"
    echo ""
    echo "GCP_WIF_PROVIDER: projects/${PROJECT_ID}/locations/global/workloadIdentityPools/${pool_id}/providers/${provider_id}"
    echo "GCP_SERVICE_ACCOUNT: $sa_email"
    echo "GCP_PROJECT: $PROJECT_ID"
    echo ""
    
    log "INFO" "Workload Identity設定完了"
}

# ========================================
# メイン処理
# ========================================

main() {
    log "INFO" "Phase 12 GCP Secret Manager設定開始"
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Phase 12: GCP認証設定セットアップ${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
    
    # 前提条件チェック
    check_prerequisites
    
    # IAMサービスアカウント設定
    setup_service_account
    
    # Workload Identity設定
    setup_workload_identity
    
    echo ""
    echo -e "${YELLOW}シークレット情報の設定を開始します${NC}"
    echo "機密情報を安全に入力してください"
    echo ""
    
    # 各シークレットの作成・更新
    create_or_update_secret \
        "bitbank-api-key" \
        "Bitbank API Key" \
        "BitbankのAPIキーを入力してください"
    
    create_or_update_secret \
        "bitbank-api-secret" \
        "Bitbank API Secret" \
        "BitbankのAPIシークレットを入力してください"
    
    create_or_update_secret \
        "discord-webhook" \
        "Discord Webhook URL" \
        "Discord WebhookのURLを入力してください"
    
    # オプション：デプロイモード設定
    echo ""
    echo "デプロイモードを選択してください:"
    echo "1) paper - ペーパートレード（安全、推奨）"
    echo "2) live  - 実取引（注意：実際の資金を使用）"
    echo -n "選択 [1]: "
    read -r mode_choice
    
    local deploy_mode="paper"
    if [[ "$mode_choice" == "2" ]]; then
        deploy_mode="live"
        echo ""
        echo -e "${RED}⚠️  実取引モードが選択されました${NC}"
        echo -e "${RED}⚠️  実際の資金が使用されます${NC}"
        echo -n "本当によろしいですか？ [y/N]: "
        read -r confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            deploy_mode="paper"
            log "INFO" "ペーパートレードモードに変更されました"
        fi
    fi
    
    # デプロイモードをシークレットに設定
    echo "$deploy_mode" | gcloud secrets versions add "deploy-mode" --data-file=- 2>/dev/null || {
        gcloud secrets create "deploy-mode" --replication-policy="automatic"
        echo "$deploy_mode" | gcloud secrets versions add "deploy-mode" --data-file=-
    }
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ セットアップ完了${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    log "INFO" "設定されたシークレット:"
    gcloud secrets list --filter="labels.managed-by:crypto-bot" --format="table(name,createTime)"
    echo ""
    log "INFO" "デプロイモード: $deploy_mode"
    echo ""
    echo -e "${BLUE}次のステップ:${NC}"
    echo "1. GitHub SecretsにWorkload Identity情報を設定"
    echo "2. GitHub ActionsでCI/CDパイプラインを実行"
    echo "3. Cloud Runサービスの動作確認"
    echo ""
    log "INFO" "Phase 12 GCP Secret Manager設定完了"
}

# スクリプト実行
main "$@"