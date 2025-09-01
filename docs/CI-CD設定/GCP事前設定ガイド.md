# GCP事前設定ガイド

**CI/CD統合簡素化完了**: 654テスト100%成功・59.24%カバレッジ・checks.sh統一品質ゲート・70%削減効率化のGCP環境完全セットアップガイド

## 📋 概要

このガイドでは、GitHub Actions CI/CDパイプライン（簡素化版）を成功させるために必要なGCP環境の事前設定を詳しく説明します。CI/CD統合簡素化完了により、checks.sh統一品質ゲート・Local=CI環境統一・企業級品質保証と個人開発効率性を両立した設定手順を提供します。

## 🎯 対象者

- CI/CD統合簡素化完了システム（checks.sh統一品質ゲート）を初めてセットアップする開発者
- CI/CD実行時にGCP関連エラーが発生した開発者  
- GCP環境の設定を確認・修正したい開発者
- 654テスト100%・59.24%カバレッジの統一品質保証システムで運用を開始する開発者

## ⚡ クイックスタート

```bash
# 1. 自動セットアップ実行（推奨）
bash scripts/deployment/setup_ci_prerequisites.sh --interactive

# 2. 環境検証
bash scripts/deployment/verify_gcp_setup.sh --full

# 3. GitHub Secretsに設定値を追加（手順は後述）

# 4. CI/CD実行
git push origin main
```

## 📚 詳細設定手順

### 1. 前提条件確認

#### 1.1 gcloud CLI設定

```bash
# gcloud CLIインストール確認
gcloud version

# 認証（ブラウザが開きます）
gcloud auth login

# プロジェクト設定
gcloud config set project my-crypto-bot-project

# 現在の設定確認
gcloud config list
```

#### 1.2 権限確認

必要な権限:
- `Project Editor` または `Project Owner`
- 最小限権限の場合は以下のロール:
  - `Artifact Registry Admin`
  - `Cloud Run Admin`
  - `Secret Manager Admin`
  - `Service Account Admin`
  - `Workload Identity Pool Admin`

```bash
# 現在のユーザー権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
```

### 2. 自動セットアップ実行

#### 2.1 対話式セットアップ（推奨）

```bash
# 包括的な自動セットアップ
bash scripts/deployment/setup_ci_prerequisites.sh --interactive
```

このスクリプトは以下を自動実行します:
- 必要なGCP APIの有効化
- Artifact Registryリポジトリ作成
- GitHub Actions用サービスアカウント作成
- Workload Identity設定
- Secret Manager認証情報設定

#### 2.2 自動セットアップ（非対話）

```bash
# CI/CD環境での自動実行
bash scripts/deployment/setup_ci_prerequisites.sh --automated
```

#### 2.3 問題修復専用

```bash
# 既存設定の問題修復
bash scripts/deployment/setup_ci_prerequisites.sh --repair
```

### 3. 手動設定（自動セットアップが失敗した場合）

#### 3.1 GCP API有効化

```bash
# 必要なAPIを個別に有効化
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable iamcredentials.googleapis.com
gcloud services enable sts.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
```

#### 3.2 Artifact Registry設定

```bash
# Dockerリポジトリ作成
gcloud artifacts repositories create crypto-bot-repo \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Phase 16-A: crypto-bot Docker images"

# Docker認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

#### 3.3 サービスアカウント作成

```bash
# GitHub Actions用サービスアカウント作成
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account" \
  --description="Phase 16-A: CI/CD automation service account"

# 必要な権限付与
SA_EMAIL="github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/monitoring.editor"
```

#### 3.4 Workload Identity設定

```bash
# Workload Identity Pool作成
gcloud iam workload-identity-pools create github-pool \
  --location="global" \
  --display-name="GitHub Actions Pool" \
  --description="Phase 16-A: GitHub Actions用Workload Identity Pool"

# OIDC Provider作成（リポジトリ名を実際の値に変更）
GITHUB_REPO="YOUR_USERNAME/crypto-bot"  # 実際のリポジトリ名に変更

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool="github-pool" \
  --location="global" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'"

# IAMポリシーバインディング
PROVIDER_NAME="projects/my-crypto-bot-project/locations/global/workloadIdentityPools/github-pool/providers/github-provider"

gcloud iam service-accounts add-iam-policy-binding \
  "github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${PROVIDER_NAME}/attribute.repository/${GITHUB_REPO}"
```

#### 3.5 Secret Manager設定

```bash
# 必要なシークレット作成
gcloud secrets create bitbank-api-key --replication-policy="automatic"
gcloud secrets create bitbank-api-secret --replication-policy="automatic"
gcloud secrets create discord-webhook --replication-policy="automatic"

# シークレット値設定（対話式）
echo -n "YOUR_BITBANK_API_KEY" | gcloud secrets versions add bitbank-api-key --data-file=-
echo -n "YOUR_BITBANK_API_SECRET" | gcloud secrets versions add bitbank-api-secret --data-file=-
echo -n "YOUR_DISCORD_WEBHOOK_URL" | gcloud secrets versions add discord-webhook --data-file=-
```

### 4. GitHub Secrets設定

#### 4.1 必要なSecrets

GitHubリポジトリの `Settings > Secrets and variables > Actions` で以下を設定:

**Repository Secrets:**
```
GCP_PROJECT_ID: my-crypto-bot-project
GCP_WIF_PROVIDER: projects/my-crypto-bot-project/locations/global/workloadIdentityPools/github-pool/providers/github-provider
GCP_SERVICE_ACCOUNT: github-actions-sa@my-crypto-bot-project.iam.gserviceaccount.com
```

**Repository Variables:**
```
GCP_REGION: asia-northeast1
ARTIFACT_REPOSITORY: crypto-bot-repo
CLOUD_RUN_SERVICE: crypto-bot-service
```

#### 4.2 設定値取得コマンド

```bash
# 現在の設定値を表示
echo "GCP_PROJECT_ID: $(gcloud config get-value project)"
echo "GCP_WIF_PROVIDER: projects/$(gcloud config get-value project)/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "GCP_SERVICE_ACCOUNT: github-actions-sa@$(gcloud config get-value project).iam.gserviceaccount.com"
```

### 5. 設定検証

#### 5.1 完全検証

```bash
# 包括的な環境検証
bash scripts/deployment/verify_gcp_setup.sh --full
```

#### 5.2 CI/CD専用検証

```bash
# CI/CD実行前の軽量検証
bash scripts/deployment/verify_gcp_setup.sh --ci
```

#### 5.3 軽量検証

```bash
# 日常的な確認用
bash scripts/deployment/verify_gcp_setup.sh --quick
```

### 6. CI/CD実行

#### 6.1 初回実行

```bash
# ローカル品質チェック（CI環境と同一）
bash scripts/testing/checks.sh

# 設定確認
git status
git add .
git commit -m "feat: CI/CD簡素化完了 GCP環境設定完了・checks.sh統一品質ゲート・統合簡素化"

# CI/CDトリガー
git push origin main
```

#### 6.2 デプロイモード設定

GitHub Secretsで `DEPLOY_MODE` を設定:

- `paper` - ペーパートレード（安全、推奨）
- `stage-10` - 10%資金投入モード
- `stage-50` - 50%資金投入モード  
- `live` - 100%本番モード

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. 権限不足エラー

```
Error: Permission denied
```

**解決方法:**
```bash
# 現在のユーザー権限確認
gcloud projects get-iam-policy my-crypto-bot-project

# プロジェクトオーナーに権限付与を依頼
# または、個別のIAMロールを確認
```

#### 2. API未有効化エラー

```
Error: API not enabled
```

**解決方法:**
```bash
# 必要なAPIを自動有効化
bash scripts/deployment/setup_ci_prerequisites.sh --repair

# または手動で有効化
gcloud services enable [API_NAME]
```

#### 3. Workload Identity設定エラー

```
Error: Workload Identity Pool not found
```

**解決方法:**
```bash
# Workload Identity設定を再実行
gcloud iam workload-identity-pools create github-pool \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

#### 4. Secret Manager接続エラー

```
Error: Secret not found
```

**解決方法:**
```bash
# シークレット存在確認
gcloud secrets list

# 不足しているシークレットを作成
gcloud secrets create [SECRET_NAME] --replication-policy="automatic"
```

#### 5. CI/CD実行失敗

**確認手順:**
1. GitHub Actions ログの確認
2. GCP環境検証スクリプト実行
3. GitHub Secrets設定の確認
4. レガシーシステムとの差分確認

### エラー診断フローチャート

```
CI/CD失敗
    ↓
GCP環境検証実行
    ↓
├─ API未有効化 → API有効化実行
├─ 権限不足 → IAM権限確認・付与
├─ リソース未作成 → 自動セットアップ実行
├─ Secret未設定 → Secret Manager設定
└─ その他 → 詳細ログ確認・手動修正
```

## 📊 設定完了チェックリスト

### 基本設定
- [ ] gcloud CLI認証済み
- [ ] プロジェクト設定済み
- [ ] 必要な権限確認済み

### GCP環境
- [ ] 必要なAPI有効化済み
- [ ] Artifact Registryリポジトリ作成済み
- [ ] Cloud Run設定準備済み

### 認証・権限
- [ ] GitHub Actions用サービスアカウント作成済み
- [ ] Workload Identity Pool設定済み
- [ ] OIDC Provider設定済み

### Secret Manager
- [ ] bitbank-api-key設定済み
- [ ] bitbank-api-secret設定済み  
- [ ] discord-webhook設定済み

### GitHub設定
- [ ] Repository Secrets設定済み
- [ ] Repository Variables設定済み
- [ ] デプロイモード設定済み

### 検証
- [ ] 完全検証（--full）成功
- [ ] CI/CD検証（--ci）成功
- [ ] 初回CI/CD実行成功

## 🔗 関連リソース

### スクリプト（Phase 13完了構造対応）
- [verify_gcp_setup.sh](../../scripts/deployment/verify_gcp_setup.sh) - GCP環境検証
- [setup_ci_prerequisites.sh](../../scripts/deployment/setup_ci_prerequisites.sh) - 自動セットアップ
- [setup_gcp_secrets.sh](../../scripts/deployment/setup_gcp_secrets.sh) - Secret Manager設定
- [checks.sh](../../scripts/testing/checks.sh) - 統合品質チェック（quality→testing統合）

### ドキュメント（Phase 13統合構造対応）
- [CI-CD設定・デプロイメントガイド.md](./CI-CD設定・デプロイメントガイド.md) - 基本的なCI/CD設定
- [../../scripts/deployment/README.md](../../scripts/deployment/README.md) - デプロイスクリプト詳細
- [../../scripts/testing/README.md](../../scripts/testing/README.md) - 統合品質チェック詳細
- [../../scripts/analytics/README.md](../../scripts/analytics/README.md) - 統合分析基盤詳細

### 設定ファイル
- [.github/workflows/ci.yml](../../.github/workflows/ci.yml) - CI/CDワークフロー
- [config/gcp/gcp_config.yaml](../../config/gcp/gcp_config.yaml) - GCP設定統合

## 💡 ベストプラクティス

### セキュリティ
- Secret Manager使用でAPIキー・認証情報を安全に管理
- Workload Identityでキーファイル不要の認証
- 最小権限の原則でIAMロール設定

### 運用効率（CI/CD簡素化対応）
- CI/CD統合簡素化（675→200行・70%削減）で運用効率向上
- checks.sh統一品質ゲートで手動作業最小化
- Local=CI環境統一で開発体験向上
- 段階的デプロイでリスク最小化
- 単一スクリプト実行で複雑性排除

### 保守性（統一環境対応）
- checks.sh統一品質ゲートで管理一元化
- Local=CI環境統一で設定差異排除
- pathlib修正でCI安定性向上
- 企業級品質保証と個人開発効率性両立
- CI/CD簡素化で保守性大幅向上

---

**CI/CD統合簡素化完了: GCP事前設定ガイド完了**
*654テスト100%成功・59.24%カバレッジ・checks.sh統一品質ゲート・CI/CD 70%削減の包括的なGCP環境セットアップで、企業級品質保証と個人開発効率性を両立した安全・確実なデプロイを実現*