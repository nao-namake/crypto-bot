#!/bin/bash
#########################################
# デプロイメントトラブルシューティングスクリプト
# GitHub Actions・Cloud Run・Terraform エラーの自動診断・解析
#########################################

set -euo pipefail

echo "🔧 デプロイメントトラブルシューティング"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="my-crypto-bot-project"
SERVICE_NAME="crypto-bot-dev"
REGION="asia-northeast1"
REPO_OWNER="nao-namake"
REPO_NAME="crypto-bot"

# Function: Check GitHub CLI authentication
check_gh_auth() {
    echo "🔍 GitHub CLI認証確認..."
    if gh auth status &>/dev/null; then
        echo -e "${GREEN}✅ GitHub CLI認証済み${NC}"
        return 0
    else
        echo -e "${RED}❌ GitHub CLI未認証${NC}"
        echo "以下のコマンドで認証してください: gh auth login"
        return 1
    fi
}

# Function: Get latest GitHub Actions run status
check_github_actions() {
    echo "🔍 GitHub Actions実行状況確認..."
    
    if ! check_gh_auth; then
        echo -e "${YELLOW}⚠️  GitHub CLI未認証のため、GitHub Actionsチェックをスキップ${NC}"
        return 1
    fi
    
    echo "最新のワークフロー実行:"
    gh run list --repo="$REPO_OWNER/$REPO_NAME" --limit=5 --json status,conclusion,workflowName,createdAt,url \
        --template '{{range .}}{{.workflowName}} | {{.status}} | {{.conclusion}} | {{.createdAt}} | {{.url}}
{{end}}' || echo "GitHub Actionsの情報取得に失敗しました"
    
    echo
    echo "最新の失敗したワークフロー:"
    FAILED_RUN_ID=$(gh run list --repo="$REPO_OWNER/$REPO_NAME" --status=failure --limit=1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || echo "")
    
    if [[ -n "$FAILED_RUN_ID" ]]; then
        echo "失敗したワークフロー詳細 (Run ID: $FAILED_RUN_ID):"
        gh run view "$FAILED_RUN_ID" --repo="$REPO_OWNER/$REPO_NAME" || echo "詳細の取得に失敗しました"
        
        echo
        echo "失敗したジョブのログ:"
        gh run view "$FAILED_RUN_ID" --repo="$REPO_OWNER/$REPO_NAME" --log || echo "ログの取得に失敗しました"
    else
        echo -e "${GREEN}✅ 最近の失敗したワークフローはありません${NC}"
    fi
}

# Function: Check Cloud Run service status
check_cloud_run_status() {
    echo "🔍 Cloud Runサービス状況確認..."
    
    # Check if service exists
    if gcloud run services describe "$SERVICE_NAME" --region="$REGION" &>/dev/null; then
        echo -e "${GREEN}✅ サービス存在確認: $SERVICE_NAME${NC}"
        
        # Get detailed service information
        echo "サービス詳細:"
        gcloud run services describe "$SERVICE_NAME" --region="$REGION" \
            --format="table(
                status.conditions[0].type:label='Condition',
                status.conditions[0].status:label='Status',
                status.conditions[0].reason:label='Reason',
                status.latestReadyRevisionName:label='Latest Revision'
            )" 2>/dev/null || echo "詳細情報の取得に失敗しました"
        
        # Check revisions
        echo
        echo "最新のリビジョン状況:"
        gcloud run revisions list --service="$SERVICE_NAME" --region="$REGION" --limit=3 \
            --format="table(
                metadata.name:label='Revision',
                status.conditions[0].status:label='Ready',
                spec.containerConcurrency:label='Concurrency',
                status.observedGeneration:label='Generation'
            )" 2>/dev/null || echo "リビジョン情報の取得に失敗しました"
    else
        echo -e "${RED}❌ サービスが存在しません: $SERVICE_NAME${NC}"
        echo "デプロイが完了していない可能性があります"
        return 1
    fi
}

# Function: Check recent Cloud Run logs
check_cloud_run_logs() {
    echo "🔍 Cloud Runログ確認..."
    
    echo "最新のエラーログ (直近30分):"
    gcloud logging read "
        resource.type=\"cloud_run_revision\" 
        AND resource.labels.service_name=\"$SERVICE_NAME\"
        AND severity>=ERROR 
        AND timestamp>=\"$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\"
    " --limit=10 --format="table(timestamp,severity,textPayload)" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  エラーログの取得に失敗しました${NC}"
    }
    
    echo
    echo "最新の一般ログ (直近10分):"
    gcloud logging read "
        resource.type=\"cloud_run_revision\" 
        AND resource.labels.service_name=\"$SERVICE_NAME\"
        AND timestamp>=\"$(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\"
    " --limit=20 --format="table(timestamp,severity,textPayload)" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  一般ログの取得に失敗しました${NC}"
    }
}

# Function: Check Terraform state
check_terraform_state() {
    echo "🔍 Terraform状態確認..."
    
    TF_DIR="/Users/nao/Desktop/bot/infra/envs/dev"
    if [[ -f "$TF_DIR/terraform.tfstate" ]]; then
        echo -e "${GREEN}✅ Terraform stateファイル存在確認${NC}"
        
        # Check last applied resources
        echo "最後にapplyされたリソース:"
        cd "$TF_DIR"
        terraform show -json 2>/dev/null | jq -r '.values.root_module.resources[].address' 2>/dev/null | head -10 || {
            echo -e "${YELLOW}⚠️  Terraform show実行に失敗しました${NC}"
        }
        
        # Check for any drift
        echo
        echo "設定ドリフト確認 (terraform plan):"
        terraform plan -no-color 2>&1 | head -20 || {
            echo -e "${YELLOW}⚠️  Terraform plan実行に失敗しました${NC}"
        }
        cd - > /dev/null
    else
        echo -e "${RED}❌ Terraform stateファイルが見つかりません${NC}"
        echo "Terraform initが必要な可能性があります"
    fi
}

# Function: Check network connectivity
check_connectivity() {
    echo "🔍 ネットワーク接続確認..."
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [[ -n "$SERVICE_URL" ]]; then
        echo "サービスURL: $SERVICE_URL"
        
        # Test health endpoint
        echo "ヘルスチェック実行:"
        if curl -sf "$SERVICE_URL/healthz" -w "Response time: %{time_total}s\n" 2>/dev/null; then
            echo -e "${GREEN}✅ ヘルスチェック成功${NC}"
        else
            echo -e "${RED}❌ ヘルスチェック失敗${NC}"
            
            # Try basic connectivity
            echo "基本接続テスト:"
            curl -I "$SERVICE_URL" 2>&1 | head -5 || echo "基本接続も失敗"
        fi
    else
        echo -e "${RED}❌ サービスURLが取得できません${NC}"
    fi
}

# Function: Comprehensive diagnostic
run_comprehensive_diagnostic() {
    echo "🔧 包括的診断実行中..."
    echo "===================="
    
    local errors=0
    
    echo
    if ! check_github_actions; then
        ((errors++))
    fi
    
    echo
    if ! check_cloud_run_status; then
        ((errors++))
    fi
    
    echo
    check_cloud_run_logs
    
    echo
    check_terraform_state
    
    echo
    check_connectivity
    
    echo
    echo "===================="
    if [[ $errors -eq 0 ]]; then
        echo -e "${GREEN}✅ 診断完了 - 重大な問題は検出されませんでした${NC}"
    else
        echo -e "${RED}❌ 診断完了 - $errors 個の問題が検出されました${NC}"
        echo
        echo "🔧 推奨アクション:"
        echo "1. GitHub Actionsのワークフローログを確認"
        echo "2. Cloud Runサービスの設定を確認"
        echo "3. Terraformの設定とstateを確認"
        echo "4. 必要に応じて再デプロイを実行"
    fi
}

# Function: Show help
show_help() {
    echo "使用方法:"
    echo "  $0                    # 包括的診断実行"
    echo "  $0 --github          # GitHub Actions確認のみ"
    echo "  $0 --cloudrun        # Cloud Run確認のみ"
    echo "  $0 --logs            # ログ確認のみ"
    echo "  $0 --terraform       # Terraform確認のみ"
    echo "  $0 --connectivity    # 接続確認のみ"
}

# Main execution
case "${1:-all}" in
    "--github")
        check_github_actions
        ;;
    "--cloudrun")
        check_cloud_run_status
        ;;
    "--logs")
        check_cloud_run_logs
        ;;
    "--terraform")
        check_terraform_state
        ;;
    "--connectivity")
        check_connectivity
        ;;
    "--help"|"-h")
        show_help
        ;;
    "all"|*)
        run_comprehensive_diagnostic
        ;;
esac