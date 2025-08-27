# config/infrastructure/ - インフラストラクチャ設定

**Phase 13完了**: GCP統合・CI/CD完全自動化・セキュリティ強化により、エンタープライズレベルのインフラストラクチャ管理システムが確立

## 🎯 役割・責任

Google Cloud Platform（GCP）を基盤とした CI/CD パイプライン、デプロイメント自動化、セキュリティ統合の設定管理を担当します。GitHub Actions と GCP の完全統合により、高品質で安全な自動デプロイメントシステムを提供します。

## 📂 ファイル構成

```
infrastructure/
├── README.md               # このファイル（Phase 13完了版）
├── gcp_config.yaml        # GCP統合設定（更新推奨：Phase 12→13）
└── cloudbuild.yaml        # Cloud Build実行定義（CI/CD自動化）
```

**🔄 更新推奨**: `gcp_config.yaml`はPhase 12版のため、Phase 13の最新機能を反映した更新が推奨されます。

## 🔧 主要機能・実装

### **GCP統合アーキテクチャ（Phase 13完成版）**

**基盤サービス統合**:
```yaml
# GCP基本構成（Phase 13対応）
project:
  id: "my-crypto-bot-project"
  region: "asia-northeast1"
  services:
    - Cloud Run: crypto-bot-service-prod（本番統一サービス）
    - Artifact Registry: Dockerイメージ管理・セキュリティスキャン
    - Secret Manager: API認証情報・機密データ管理
    - Cloud Logging: 構造化ログ・監視統合
    - Cloud Monitoring: メトリクス・アラート・ヘルスチェック
```

### **CI/CD完全自動化システム**

**GitHub Actions統合**:
- **品質ゲート**: 306テスト・58.88%カバレッジ・コード品質チェック
- **自動デプロイ**: mainブランチプッシュで即座デプロイ
- **ヘルスチェック**: デプロイ後自動稼働確認
- **ロールバック対応**: 障害時の迅速復旧機能

**デプロイフロー（Phase 13完成）**:
```yaml
1. 品質保証フェーズ: 306テスト・カバレッジ・コード品質
2. ビルド・プッシュ: Docker イメージ・Artifact Registry
3. 本番デプロイ: Cloud Run・環境変数・Secret統合
4. ヘルスチェック: 自動稼働確認・監視開始
5. 通知・監視: Discord・Cloud Monitoring・アラート設定
```

### **セキュリティ強化システム（Phase 13完了）**

**Workload Identity統合**:
```yaml
# 自動認証・最小権限設計
iam:
  github_service_account: "github-actions-sa"
  workload_identity_pool: "github-pool"  
  automatic_token_refresh: true
  minimal_permissions: true
  api_key_protection: "gcp_secret_manager"
```

**機密情報管理**:
- **Secret Manager**: `bitbank-api-key`, `bitbank-api-secret`
- **環境変数分離**: 設定ファイルから機密情報完全除外
- **アクセス制御**: 最小権限・監査ログ・自動ローテーション
- **セキュリティ監視**: 不正アクセス検出・即座アラート

## 📝 使用方法・例

### **自動デプロイ（推奨フロー）**
```bash
# Phase 13標準デプロイフロー
git add .
git commit -m "feat: Phase 13機能追加"
git push origin main
# → 自動実行: 品質チェック→ビルド→デプロイ→監視開始

# 実行状況確認
gh run list --limit 5
gh run watch
```

### **手動インフラ管理**
```bash
# GCP基盤確認
gcloud projects describe my-crypto-bot-project
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# Secret Manager確認
gcloud secrets list
gcloud secrets versions access latest --secret=bitbank-api-key

# Workload Identity確認
gcloud iam workload-identity-pools list --location=global
```

### **監視・デバッグ**
```bash
# リアルタイム監視
gcloud logging tail "resource.type=cloud_run_revision"

# パフォーマンス分析
python3 scripts/analytics/dashboard.py --gcp
python3 scripts/management/dev_check.py operational

# デプロイ履歴確認
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1
```

## ⚠️ 注意事項・制約

### **インフラ変更時の注意**
- **影響範囲**: GCPプロジェクト全体への影響考慮
- **ダウンタイム**: 本番サービス稼働時間への配慮
- **コスト影響**: リソース変更による料金変動監視
- **セキュリティ**: IAM・Secret Manager設定変更の慎重実施

### **CI/CD運用制約**
- **GitHub Actions制限**: 月間2000分無料枠・同時実行制限
- **Cloud Run制約**: メモリ・CPU・同時リクエスト数制限
- **Artifact Registry**: イメージサイズ・保存容量制限
- **ネットワーク**: レスポンス時間・地域間遅延考慮

### **セキュリティ制約**
- **機密情報**: 設定ファイルへのAPIキー記載禁止
- **アクセス権限**: 最小権限原則・定期的権限見直し
- **監査要件**: 全変更操作のログ記録・追跡可能性
- **障害対応**: インシデント対応手順・エスカレーション体制

### **Phase 13対応事項**
- **段階的デプロイ廃止**: production統一・シンプル化完了
- **モード一元化**: 環境変数制御・設定ファイル統合
- **品質保証統合**: 306テスト・カバレッジ・自動品質ゲート

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`.github/workflows/ci.yml`**: メインCI/CDパイプライン・自動デプロイ
- **`Dockerfile`**: コンテナイメージ定義・ビルド設定
- **`requirements.txt`**: Python依存関係・環境再現
- **`scripts/deployment/`**: デプロイ支援スクリプト

### **GCPサービス統合**
- **Cloud Run**: `crypto-bot-service-prod`本番サービス
- **Artifact Registry**: `crypto-bot-repo`イメージリポジトリ  
- **Secret Manager**: 機密情報安全管理・自動取得
- **Cloud Logging**: 構造化ログ・検索・監視統合
- **Cloud Monitoring**: メトリクス・アラート・ダッシュボード

### **設定システム連携**
- **`config/core/base.yaml`**: 基本設定・環境変数統合
- **`config/production/production.yaml`**: 本番特化設定
- **`src/core/config.py`**: モード設定一元化システム
- **`scripts/management/dev_check.py`**: 品質チェック・運用診断

### **監視・分析システム**
- **Discord Webhook**: リアルタイム通知・障害アラート
- **GitHub Actions**: デプロイ監視・品質ゲート
- **Cloud Monitoring**: パフォーマンス監視・SLA管理
- **pytest**: インフラ設定検証・自動テスト統合

---

**重要**: Phase 13完了により、GCP統合・CI/CD完全自動化・セキュリティ強化が完成しました。このディレクトリはインフラストラクチャの中核であり、変更時は全環境・本番サービスへの影響を慎重に確認し、適切な監視体制での運用を実施してください。