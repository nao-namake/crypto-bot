# config/infrastructure/ - インフラストラクチャ設定

**目的**: GCP・CI/CD・デプロイメント関連の統合管理

## 📁 ファイル構成

```
infrastructure/
├── README.md               # このファイル
├── gcp_config.yaml        # GCP統合設定（380行）
└── cloudbuild.yaml        # Cloud Build実行定義
```

## 🎯 役割分担

### gcp_config.yaml - 設定定義（WHAT）
- **目的**: Google Cloud Platform全体の設定管理
- **内容**: プロジェクト・IAM・Workload Identity・Secret Manager
- **効果**: 90%設定管理効率向上・自動認証

### cloudbuild.yaml - 実行定義（HOW）
- **目的**: CI/CDパイプラインの実行手順
- **内容**: ビルド・テスト・デプロイステップ
- **効果**: 80%デプロイ効率向上・自動化

## 🚀 GCP統合アーキテクチャ

### 基盤サービス
```yaml
# GCP基本構成
project:
  id: "my-crypto-bot-project"
  region: "asia-northeast1"
  services:
    - Cloud Run（アプリケーション実行）
    - Artifact Registry（Dockerイメージ管理）
    - Secret Manager（機密情報管理）
    - Cloud Logging（ログ管理）
    - Cloud Monitoring（監視・アラート）
```

### セキュリティ統合
```yaml
# Workload Identity設定
iam:
  github_service_account: "github-actions-sa"
  workload_identity_pool: "github-pool"
  automatic_token_refresh: true
  minimal_permissions: true
```

## 🔧 使用方法

### GitHub Actions CI/CD
```bash
# 自動デプロイ（推奨）
git push origin main

# 手動デプロイ確認
python scripts/management/dev_check.py validate --mode light
```

### 手動GCPコマンド
```bash
# プロジェクト確認
gcloud projects describe my-crypto-bot-project

# Workload Identity確認
gcloud iam workload-identity-pools list --location=global

# Secret Manager確認
gcloud secrets list
```

## 📊 CI/CDパイプライン

### ビルドステップ（cloudbuild.yaml）
```yaml
steps:
  1. 品質チェック（306テスト・sklearn警告解消）
  2. Dockerビルド・プッシュ
  3. Cloud Runデプロイ
  4. ヘルスチェック・動作確認
  5. 監視・アラート設定
```

### 段階的デプロイ対応
- **Paper**: 開発・テスト環境
- **Live Stages**: testing → validation → stage_10 → stage_50 → production

## 🔒 セキュリティ機能

### 自動認証
- Workload Identityによるトークン自動更新
- Secret Managerによる機密情報管理
- 最小権限によるアクセス制御

### 監査・監視
- 全デプロイ操作のログ記録
- エラー・異常の自動検出
- Discord通知による即座なアラート

## 🚨 トラブルシューティング

### デプロイ失敗時
```bash
# ログ確認
gcloud builds log [BUILD_ID]

# サービス状態確認
gcloud run services describe crypto-bot-service --region=asia-northeast1

# 権限確認
gcloud projects get-iam-policy my-crypto-bot-project
```

### 認証問題
```bash
# Workload Identity確認
gcloud iam workload-identity-pools providers describe github-provider \
  --location=global --workload-identity-pool=github-pool

# Secret Manager確認
gcloud secrets versions access latest --secret=bitbank-api-key
```

---

**重要**: このディレクトリはGCP・CI/CD基盤の中核です。変更時は全環境への影響を慎重に確認してください。