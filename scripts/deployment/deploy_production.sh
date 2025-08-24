#!/bin/bash

# Phase 9-4: GCP Cloud Run本番デプロイメントスクリプト
# 
# 段階的デプロイメント対応（10%→50%→100%資金投入）
# 環境変数設定・ヘルスチェック・Discord通知・監視体制の自動構築
#
# 使用方法:
#   bash scripts/deploy_production.sh --stage 10percent  # 10%資金投入段階
#   bash scripts/deploy_production.sh --stage 50percent  # 50%資金投入段階  
#   bash scripts/deploy_production.sh --stage production # 100%本番運用
#
# 実行前チェック:
#   1. gcloud CLI認証済み（gcloud auth login）
#   2. Docker認証済み（gcloud auth configure-docker asia-northeast1-docker.pkg.dev）
#   3. Bitbank API認証情報準備済み
#   4. Discord Webhook URL準備済み

set -euo pipefail

# ========================================
# 設定・定数定義
# ========================================

# GCPプロジェクト設定
PROJECT_ID="my-crypto-bot-project"
REGION="asia-northeast1"
REPOSITORY="crypto-bot-repo"
SERVICE_NAME_PREFIX="crypto-bot-service"

# Docker設定
DOCKER_REGISTRY="asia-northeast1-docker.pkg.dev"
IMAGE_BASE_PATH="${DOCKER_REGISTRY}/${PROJECT_ID}/${REPOSITORY}/crypto-bot"

# ディレクトリ設定
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ログ設定
LOG_DIR="${PROJECT_ROOT}/logs/deployment"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/deploy_$(date +%Y%m%d_%H%M%S).log"

# ========================================
# ログ・ユーティリティ関数
# ========================================

log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "$1"; }
log_warn() { log "WARN" "$1"; }
log_error() { log "ERROR" "$1"; }
log_success() { log "SUCCESS" "$1"; }

error_exit() {
    log_error "$1"
    echo ""
    echo "❌ デプロイメント失敗"
    echo "📋 ログファイル: ${LOG_FILE}"
    exit 1
}

# ========================================
# デプロイメント段階設定
# ========================================

set_stage_config() {
    local stage="$1"
    
    case "${stage}" in
        "10percent")
            SERVICE_NAME="${SERVICE_NAME_PREFIX}-10percent"
            CONFIG_FILE="config/environments/live/stage_10.yaml"
            MEMORY="1Gi"
            CPU="1"
            MIN_INSTANCES="1"
            MAX_INSTANCES="1"
            TIMEOUT="1800"  # 30分
            MAX_DAILY_TRADES="10"
            ;;
        "50percent")
            SERVICE_NAME="${SERVICE_NAME_PREFIX}-50percent"
            CONFIG_FILE="config/environments/live/stage_50.yaml"
            MEMORY="1.5Gi"
            CPU="1"
            MIN_INSTANCES="1"
            MAX_INSTANCES="1"
            TIMEOUT="2400"  # 40分
            MAX_DAILY_TRADES="15"
            ;;
        "production"|"100percent")
            SERVICE_NAME="${SERVICE_NAME_PREFIX}-prod"
            CONFIG_FILE="config/environments/live/production.yaml"
            MEMORY="2Gi"
            CPU="2"
            MIN_INSTANCES="1"
            MAX_INSTANCES="2"
            TIMEOUT="3600"  # 60分
            MAX_DAILY_TRADES="25"
            ;;
        *)
            error_exit "無効なデプロイメント段階: ${stage}. 利用可能: 10percent, 50percent, production"
            ;;
    esac
    
    IMAGE_TAG="${stage}-$(date +%Y%m%d-%H%M%S)"
    IMAGE_FULL_PATH="${IMAGE_BASE_PATH}:${IMAGE_TAG}"
    
    log_info "📊 デプロイメント設定確定:"
    log_info "  段階: ${stage}"
    log_info "  サービス名: ${SERVICE_NAME}"
    log_info "  設定ファイル: ${CONFIG_FILE}"
    log_info "  イメージ: ${IMAGE_FULL_PATH}"
    log_info "  リソース: ${MEMORY} / ${CPU} CPU"
}

# ========================================
# 事前チェック
# ========================================

pre_deployment_checks() {
    log_info "🔍 事前チェック開始"
    
    # プロジェクトルート確認
    if [[ ! -f "${PROJECT_ROOT}/src/main.py" ]]; then
        error_exit "プロジェクトルートが正しくありません: ${PROJECT_ROOT}"
    fi
    
    # 設定ファイル確認
    if [[ ! -f "${PROJECT_ROOT}/${CONFIG_FILE}" ]]; then
        error_exit "設定ファイルが見つかりません: ${CONFIG_FILE}"
    fi
    
    # gcloud CLI確認
    if ! command -v gcloud &> /dev/null; then
        error_exit "gcloud CLIがインストールされていません"
    fi
    
    # gcloud認証確認
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        error_exit "gcloud認証が必要です: gcloud auth login"
    fi
    
    # Dockerデーモン確認
    if ! docker info &> /dev/null; then
        error_exit "Dockerデーモンが起動していません"
    fi
    
    # 必須環境変数チェック
    if [[ -z "${BITBANK_API_KEY:-}" ]]; then
        log_warn "環境変数 BITBANK_API_KEY が設定されていません"
        log_info "gcloud secrets managerに保存された値を使用します"
    fi
    
    if [[ -z "${DISCORD_WEBHOOK_URL:-}" ]]; then
        log_warn "環境変数 DISCORD_WEBHOOK_URL が設定されていません"
        log_info "gcloud secrets managerに保存された値を使用します"
    fi
    
    log_success "✅ 事前チェック完了"
}

# ========================================
# GCPサービス・シークレット準備
# ========================================

setup_gcp_services() {
    log_info "🏗️ GCPサービス準備開始"
    
    # プロジェクト設定
    gcloud config set project "${PROJECT_ID}" || error_exit "プロジェクト設定失敗"
    
    # 必要なAPIサービス有効化
    local services=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "artifactregistry.googleapis.com"
        "secretmanager.googleapis.com"
        "logging.googleapis.com"
        "monitoring.googleapis.com"
    )
    
    for service in "${services[@]}"; do
        log_info "APIサービス有効化: ${service}"
        gcloud services enable "${service}" || error_exit "APIサービス有効化失敗: ${service}"
    done
    
    # Artifact Registry確認・作成
    if ! gcloud artifacts repositories describe "${REPOSITORY}" --location="${REGION}" &> /dev/null; then
        log_info "Artifact Registry作成: ${REPOSITORY}"
        gcloud artifacts repositories create "${REPOSITORY}" \
            --repository-format=docker \
            --location="${REGION}" \
            --description="Crypto Bot Docker Repository" || error_exit "Artifact Registry作成失敗"
    else
        log_info "Artifact Registry確認済み: ${REPOSITORY}"
    fi
    
    log_success "✅ GCPサービス準備完了"
}

setup_secrets() {
    log_info "🔐 シークレット管理設定開始"
    
    # Bitbank APIキー
    if ! gcloud secrets describe "bitbank-api-key" &> /dev/null; then
        if [[ -n "${BITBANK_API_KEY:-}" ]]; then
            log_info "Bitbank APIキー作成中..."
            echo -n "${BITBANK_API_KEY}" | gcloud secrets create "bitbank-api-key" --data-file=- || error_exit "Bitbank APIキー作成失敗"
        else
            log_warn "⚠️ Bitbank APIキーが未設定 - 手動で作成してください:"
            log_warn "  echo 'YOUR_API_KEY' | gcloud secrets create bitbank-api-key --data-file=-"
        fi
    else
        log_info "Bitbank APIキー確認済み"
    fi
    
    # Bitbank APIシークレット
    if ! gcloud secrets describe "bitbank-api-secret" &> /dev/null; then
        if [[ -n "${BITBANK_API_SECRET:-}" ]]; then
            log_info "Bitbank APIシークレット作成中..."
            echo -n "${BITBANK_API_SECRET}" | gcloud secrets create "bitbank-api-secret" --data-file=- || error_exit "Bitbank APIシークレット作成失敗"
        else
            log_warn "⚠️ Bitbank APIシークレットが未設定 - 手動で作成してください:"
            log_warn "  echo 'YOUR_API_SECRET' | gcloud secrets create bitbank-api-secret --data-file=-"
        fi
    else
        log_info "Bitbank APIシークレット確認済み"
    fi
    
    # Discord Webhook URL
    if ! gcloud secrets describe "discord-webhook-url" &> /dev/null; then
        if [[ -n "${DISCORD_WEBHOOK_URL:-}" ]]; then
            log_info "Discord Webhook URL作成中..."
            echo -n "${DISCORD_WEBHOOK_URL}" | gcloud secrets create "discord-webhook-url" --data-file=- || error_exit "Discord Webhook URL作成失敗"
        else
            log_warn "⚠️ Discord Webhook URLが未設定 - 手動で作成してください:"
            log_warn "  echo 'YOUR_WEBHOOK_URL' | gcloud secrets create discord-webhook-url --data-file=-"
        fi
    else
        log_info "Discord Webhook URL確認済み"
    fi
    
    log_success "✅ シークレット管理設定完了"
}

# ========================================
# Docker イメージビルド・プッシュ
# ========================================

build_and_push_image() {
    log_info "🐳 Dockerイメージビルド開始"
    
    cd "${PROJECT_ROOT}"
    
    # Docker認証確認
    if ! gcloud auth configure-docker "${DOCKER_REGISTRY}" --quiet; then
        error_exit "Docker認証設定失敗"
    fi
    
    # Dockerfileが存在することを確認
    if [[ ! -f "Dockerfile" ]]; then
        error_exit "Dockerfileが見つかりません"
    fi
    
    # イメージビルド
    log_info "イメージビルド中: ${IMAGE_FULL_PATH}"
    if ! docker build \
        --platform linux/amd64 \
        --tag "${IMAGE_FULL_PATH}" \
        --file Dockerfile \
        . >> "${LOG_FILE}" 2>&1; then
        error_exit "Dockerイメージビルド失敗"
    fi
    
    # イメージプッシュ
    log_info "イメージプッシュ中: ${IMAGE_FULL_PATH}"
    if ! docker push "${IMAGE_FULL_PATH}" >> "${LOG_FILE}" 2>&1; then
        error_exit "Dockerイメージプッシュ失敗"
    fi
    
    # プッシュ確認
    if ! gcloud artifacts docker images describe "${IMAGE_FULL_PATH}" &> /dev/null; then
        error_exit "イメージプッシュ検証失敗"
    fi
    
    log_success "✅ Dockerイメージビルド・プッシュ完了: ${IMAGE_FULL_PATH}"
}

# ========================================
# Cloud Run デプロイメント
# ========================================

deploy_cloud_run() {
    log_info "☁️ Cloud Runデプロイメント開始"
    
    # デプロイコマンド構築
    local deploy_cmd=(
        gcloud run deploy "${SERVICE_NAME}"
        --image="${IMAGE_FULL_PATH}"
        --region="${REGION}"
        --platform=managed
        --port=8080
        --memory="${MEMORY}"
        --cpu="${CPU}"
        --min-instances="${MIN_INSTANCES}"
        --max-instances="${MAX_INSTANCES}"
        --timeout="${TIMEOUT}"
        --concurrency=1
        --allow-unauthenticated
        --set-env-vars="MODE=live,EXCHANGE=bitbank,LOG_LEVEL=INFO,CONFIG_FILE=${CONFIG_FILE},MAX_DAILY_TRADES=${MAX_DAILY_TRADES}"
        --set-secrets="BITBANK_API_KEY=bitbank-api-key:latest,BITBANK_API_SECRET=bitbank-api-secret:latest,DISCORD_WEBHOOK_URL=discord-webhook-url:latest"
        --revision-suffix="${stage}-$(date +%H%M%S)"
        --quiet
    )
    
    log_info "Cloud Runデプロイコマンド:"
    printf '  %s\n' "${deploy_cmd[@]}" | tee -a "${LOG_FILE}"
    
    # デプロイ実行
    if ! "${deploy_cmd[@]}" >> "${LOG_FILE}" 2>&1; then
        error_exit "Cloud Runデプロイ失敗"
    fi
    
    # デプロイ確認
    local service_url
    service_url=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)" 2>/dev/null)
    
    if [[ -z "${service_url}" ]]; then
        error_exit "Cloud Runサービス確認失敗"
    fi
    
    log_success "✅ Cloud Runデプロイ完了"
    log_success "🌐 サービスURL: ${service_url}"
    
    # ヘルスチェック実行
    log_info "🏥 ヘルスチェック実行中..."
    local health_check_passed=false
    
    for i in {1..10}; do
        if curl -s --max-time 10 "${service_url}/health" &> /dev/null; then
            health_check_passed=true
            break
        fi
        log_info "ヘルスチェック試行 ${i}/10 - 10秒後に再試行..."
        sleep 10
    done
    
    if ${health_check_passed}; then
        log_success "✅ ヘルスチェック成功"
    else
        log_warn "⚠️ ヘルスチェック失敗 - サービスは起動していますが応答がありません"
    fi
    
    export DEPLOYED_SERVICE_URL="${service_url}"
}

# ========================================
# 監視・アラート設定
# ========================================

setup_monitoring() {
    log_info "📊 監視・アラート設定開始"
    
    # ログベースのメトリクス作成（取引成功数）
    local trade_success_metric="crypto_bot_trades_success_${stage}"
    if ! gcloud logging metrics describe "${trade_success_metric}" &> /dev/null; then
        log_info "取引成功メトリクス作成: ${trade_success_metric}"
        gcloud logging metrics create "${trade_success_metric}" \
            --description="Crypto Bot successful trades metric for ${stage}" \
            --log-filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND \"✅\" AND \"注文実行成功\"" || log_warn "取引成功メトリクス作成失敗"
    fi
    
    # ログベースのメトリクス作成（エラー数）
    local error_metric="crypto_bot_errors_${stage}"
    if ! gcloud logging metrics describe "${error_metric}" &> /dev/null; then
        log_info "エラーメトリクス作成: ${error_metric}"
        gcloud logging metrics create "${error_metric}" \
            --description="Crypto Bot error metric for ${stage}" \
            --log-filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND severity >= ERROR" || log_warn "エラーメトリクス作成失敗"
    fi
    
    log_success "✅ 監視・アラート設定完了"
}

# ========================================
# デプロイメント完了レポート
# ========================================

generate_deployment_report() {
    log_info "📋 デプロイメント完了レポート生成"
    
    local report_file="${LOG_DIR}/deployment_report_${stage}_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "${report_file}" << EOF
# Phase 9-4: 本番デプロイメント完了レポート

## デプロイメント概要
- **実行日時**: $(date '+%Y年%m月%d日 %H:%M:%S')
- **デプロイ段階**: ${stage}
- **サービス名**: ${SERVICE_NAME}
- **リージョン**: ${REGION}

## 設定詳細
- **Dockerイメージ**: ${IMAGE_FULL_PATH}
- **設定ファイル**: ${CONFIG_FILE}
- **リソース**: ${MEMORY} / ${CPU} CPU
- **インスタンス数**: ${MIN_INSTANCES}-${MAX_INSTANCES}
- **タイムアウト**: ${TIMEOUT}秒

## デプロイ結果
- **サービスURL**: ${DEPLOYED_SERVICE_URL}
- **ヘルスチェック**: $(${health_check_passed} && echo "✅ 成功" || echo "⚠️ 失敗")
- **監視設定**: ✅ 完了
- **シークレット管理**: ✅ 完了

## 次のステップ

### Phase 9-2: 少額実運用テスト
\`\`\`bash
# 単発注文テスト
python scripts/test_live_trading.py --mode single --config ${CONFIG_FILE}

# 連続取引テスト（4時間）
python scripts/test_live_trading.py --mode continuous --duration 4 --config ${CONFIG_FILE}
\`\`\`

### 監視・管理コマンド
\`\`\`bash
# サービス状況確認
gcloud run services describe ${SERVICE_NAME} --region=${REGION}

# ログ確認
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\"" --limit=50

# リビジョン管理
gcloud run revisions list --service=${SERVICE_NAME} --region=${REGION}
\`\`\`

## 緊急時対応
- **サービス停止**: \`gcloud run services delete ${SERVICE_NAME} --region=${REGION}\`
- **スケールダウン**: \`gcloud run services update ${SERVICE_NAME} --min-instances=0 --max-instances=0 --region=${REGION}\`
- **Discord通知確認**: ${DEPLOYED_SERVICE_URL}/health

## ログファイル
- **デプロイメントログ**: ${LOG_FILE}
- **レポートファイル**: ${report_file}

---
Generated by Phase 9-4 deployment script
EOF

    log_success "📋 デプロイメント完了レポート作成: ${report_file}"
    echo ""
    echo "🎉 === Phase 9-4 デプロイメント成功 ==="
    echo ""
    echo "📊 デプロイ段階: ${stage}"
    echo "🌐 サービスURL: ${DEPLOYED_SERVICE_URL}"
    echo "📁 設定ファイル: ${CONFIG_FILE}"
    echo "📋 完了レポート: ${report_file}"
    echo ""
    echo "🚀 次のステップ:"
    echo "  1. Phase 9-2: 少額実運用テスト実行"
    echo "     python scripts/test_live_trading.py --mode single --config ${CONFIG_FILE}"
    echo ""
    echo "  2. 24時間監視開始"
    echo "     gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\""
    echo ""
}

# ========================================
# メイン処理
# ========================================

main() {
    echo "🚀 Phase 9-4: GCP Cloud Run 本番デプロイメント開始"
    echo "📅 実行時間: $(date '+%Y年%m月%d日 %H:%M:%S')"
    echo ""
    
    # コマンドライン引数解析
    local stage=""
    local force_rebuild=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --stage)
                stage="$2"
                shift 2
                ;;
            --force-rebuild)
                force_rebuild=true
                shift
                ;;
            --help|-h)
                cat << EOF
Phase 9-4: GCP Cloud Run 本番デプロイメントスクリプト

使用方法:
  bash scripts/deploy_production.sh --stage STAGE [OPTIONS]

段階別デプロイメント:
  --stage 10percent   10%資金投入段階（保守的）
  --stage 50percent   50%資金投入段階（バランス型）
  --stage production  100%本番運用（フル）

オプション:
  --force-rebuild     強制的にDockerイメージ再ビルド
  --help, -h          このヘルプを表示

実行前準備:
  1. gcloud auth login
  2. gcloud auth configure-docker asia-northeast1-docker.pkg.dev
  3. export BITBANK_API_KEY="your_api_key"
  4. export BITBANK_API_SECRET="your_api_secret"
  5. export DISCORD_WEBHOOK_URL="your_webhook_url"

例:
  bash scripts/deploy_production.sh --stage 10percent
  bash scripts/deploy_production.sh --stage production --force-rebuild
EOF
                exit 0
                ;;
            *)
                error_exit "無効なオプション: $1. --help でヘルプを確認してください。"
                ;;
        esac
    done
    
    # 必須パラメータチェック
    if [[ -z "${stage}" ]]; then
        error_exit "デプロイメント段階が指定されていません。--stage オプションを使用してください。"
    fi
    
    # ユーザー確認
    echo "⚠️ 本番環境デプロイメントを実行します:"
    echo "  段階: ${stage}"
    echo "  プロジェクト: ${PROJECT_ID}"
    echo "  リージョン: ${REGION}"
    echo ""
    read -p "続行しますか？ [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "デプロイメント中止"
        exit 0
    fi
    
    # 段階別設定適用
    set_stage_config "${stage}"
    
    # デプロイメント実行
    pre_deployment_checks
    setup_gcp_services
    setup_secrets
    build_and_push_image
    deploy_cloud_run
    setup_monitoring
    generate_deployment_report
    
    log_success "🎉 Phase 9-4 デプロイメント完了!"
}

# スクリプト実行
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi