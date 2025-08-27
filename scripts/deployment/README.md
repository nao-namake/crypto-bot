# scripts/deployment/ - デプロイメント・インフラ管理

**Phase 13対応**: GCP Cloud Run本番デプロイ・Docker・インフラ自動化（2025年8月26日現在）

## 📂 ファイル構成

```
deployment/
├── deploy_production.sh         # GCP Cloud Run本番デプロイ
├── docker-entrypoint.sh         # Dockerエントリポイント
├── setup_ci_prerequisites.sh    # CI/CD前提条件セットアップ
├── setup_gcp_secrets.sh         # GCP Secret Manager設定
├── verify_gcp_setup.sh          # GCP環境検証
└── README.md                    # このファイル
```

## 🎯 役割・責任

デプロイメント・インフラ管理として以下を提供：
- **本番デプロイ**: GCP Cloud Run自動デプロイ・段階的リリース
- **環境構築**: CI/CD前提条件・GCP環境・認証設定自動化
- **品質保証**: デプロイ前チェック・環境検証・問題事前検出
- **Docker統合**: コンテナ化・エントリポイント・プロセス管理

## 🚀 主要機能・実装

### **deploy_production.sh**: 本番デプロイ自動化
- 品質チェック・Docker Build・段階的デプロイ
- Cloud Run サービス更新・環境変数設定・ヘルスチェック
- カナリアリリース・トラフィック分割・自動監視

### **docker-entrypoint.sh**: Docker統合エントリポイント
- main.py統合システム起動制御・環境変数管理
- プロセス監視・グレースフルシャットダウン・ヘルスチェック
- CI/CD統合・手動実行監視統合

### **verify_gcp_setup.sh**: GCP環境検証
- 包括的環境検証・CI/CD失敗防止・自動診断
- GCP認証・API状態・リソース・権限・ネットワーク確認
- 問題事前検出・修復提案・レポート生成

### **setup_ci_prerequisites.sh**: CI/CD環境自動構築
- GCP環境・IAM・Workload Identity・Secret Manager一括設定
- 対話式設定・自動修復・GitHub統合
- 初回セットアップ・問題修復・検証機能

### **setup_gcp_secrets.sh**: シークレット管理
- GCP Secret Manager自動設定・認証情報管理
- Bitbank API・Discord Webhook設定・権限管理
- CI/CD統合・セキュリティ強化・アクセス制御

## 🔧 使用方法・例

### **デプロイフロー（推奨）**
```bash
# 1. 事前品質チェック
bash scripts/testing/checks.sh

# 2. GCP環境検証
bash scripts/deployment/verify_gcp_setup.sh --full

# 3. 本番デプロイ実行
bash scripts/deployment/deploy_production.sh

# 4. 段階的デプロイ（カナリアリリース）
bash scripts/deployment/deploy_production.sh --canary
```

### **初回環境構築**
```bash
# 1. 包括的環境検証
bash scripts/deployment/verify_gcp_setup.sh --full

# 2. 自動環境セットアップ
bash scripts/deployment/setup_ci_prerequisites.sh --interactive

# 3. シークレット設定
bash scripts/deployment/setup_gcp_secrets.sh --interactive

# 4. 再検証・確認
bash scripts/deployment/verify_gcp_setup.sh --ci
```

### **トラブルシューティング**
```bash
# 問題検出・診断
bash scripts/deployment/verify_gcp_setup.sh --full

# 自動修復
bash scripts/deployment/setup_ci_prerequisites.sh --repair

# ログ確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR"
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **GCP認証必須**: gcloud auth設定済み環境
2. **Docker環境**: Docker Desktop・権限設定済み
3. **ネットワーク**: GCP API・Artifact Registry・Cloud Run アクセス必要
4. **権限要件**: GCP Project Editor・IAM Admin・Service Account Admin

### **デプロイ制約**
- **品質チェック必須**: scripts/testing/checks.sh合格後のみデプロイ可能
- **環境検証必須**: verify_gcp_setup.sh合格確認
- **段階的デプロイ推奨**: paper → stage → live 順次実行
- **ロールバック準備**: 前回リビジョン保持・即座復旧可能

## 🔗 関連ファイル・依存関係

### **システム統合**
- **scripts/testing/**: checks.sh品質チェック・テスト実行
- **scripts/management/**: dev_check.pyデプロイ確認・監視統合
- **scripts/analytics/**: デプロイ後パフォーマンス分析・監視

### **設定・環境**
- **config/gcp/**: GCP設定ファイル・環境別設定・統合管理
- **config/deployment/**: デプロイ設定・Cloud Run仕様・環境変数
- **.github/workflows/**: GitHub Actions・CI/CD・自動デプロイ

### **外部依存**
- **GCP Cloud Run**: 本番実行環境・スケーリング・監視
- **GCP Artifact Registry**: Dockerイメージ管理・セキュリティ
- **GCP Secret Manager**: 認証情報・API Key・セキュア管理
- **GitHub Actions**: CI/CD・自動デプロイ・品質ゲート

---

**🎯 Phase 13対応完了**: GCP Cloud Run本番デプロイ・Docker統合・環境自動構築・品質保証により安定した本番運用環境を実現。