# scripts/deployment/ - デプロイメント・インフラ管理スクリプト

## 🎯 役割・責任

本番環境へのデプロイメント、GCP Cloud Run環境の構築・管理、CI/CD環境の設定、認証システムの管理を担当するインフラ管理スクリプト群を管理します。Docker コンテナベースの本番デプロイから GCP サービスの設定、GitHub Actions との統合まで、システムの運用基盤を構築・保守する包括的なデプロイメントツールを提供します。

## 📂 ファイル構成

```
scripts/deployment/
├── README.md                    # このファイル
├── deploy_production.sh         # 本番環境デプロイメント・Cloud Run管理
├── docker-entrypoint.sh         # Dockerコンテナエントリーポイント・起動制御
├── setup_ci_prerequisites.sh    # CI/CD環境構築・GitHub Actions設定
├── setup_gcp_secrets.sh         # GCP Secret Manager・認証管理
└── verify_gcp_setup.sh          # GCP環境検証・設定確認
```

## 📋 主要ファイル・フォルダの役割

### **deploy_production.sh**
GCP Cloud Run への本番デプロイメントを管理するメインスクリプトです。
- **段階的デプロイ**: paper→stage-10→stage-50→live の段階的リリース
- **Docker統合**: Dockerfile ビルド・Artifact Registry 管理・イメージ推送
- **サービス管理**: Cloud Run サービス作成・更新・環境変数設定
- **品質ゲート**: デプロイ前後のテスト実行・品質確認・ロールバック機能
- **Discord通知**: デプロイ状況の通知・成功/失敗レポート送信
- **ヘルスチェック**: サービス起動確認・応答性テスト・安定性検証
- 約19.5KBの実装ファイル

### **docker-entrypoint.sh**
Docker コンテナの起動制御とプロセス管理を担当します。
- **デュアルプロセス**: ヘルスチェックサーバーと取引システムの並行実行
- **環境初期化**: Python パス設定・依存関係確認・設定ファイル検証
- **ヘルスチェックAPI**: /health エンドポイント・軽量JSON応答・監視連携
- **プロセス監視**: メインプロセス監視・異常終了検知・自動復旧処理
- **エラーハンドリング**: 起動失敗時の詳細ログ・診断情報・適切な終了処理
- **Cloud Run最適化**: メモリ効率・起動時間短縮・スケーリング対応
- 約8.7KBの実装ファイル

### **setup_ci_prerequisites.sh**
CI/CD 環境の構築と GitHub Actions との統合を管理します。
- **GCP環境構築**: Cloud Run・Artifact Registry・Secret Manager サービス設定
- **GitHub Actions統合**: OIDC 設定・Workload Identity 構築・権限管理
- **サービスアカウント**: CI/CD 用サービスアカウント・IAM ロール設定
- **対話式設定**: ユーザー入力による設定確認・自動修復機能
- **環境検証**: 設定完了後の動作確認・接続テスト・権限確認
- **レポート生成**: 設定結果レポート・問題診断・修復手順提示
- 約25.4KBの実装ファイル

### **setup_gcp_secrets.sh**
GCP Secret Manager を使用した認証情報の管理を担当します。
- **API認証**: Bitbank API キー・シークレットの安全な保存
- **Discord統合**: Webhook URL の設定・通知システム認証
- **セキュリティ設定**: アクセス制御・権限管理・暗号化設定
- **対話式入力**: 認証情報の安全な入力・確認・検証
- **権限管理**: サービスアカウント権限・最小権限原則・監査ログ
- **統合テスト**: 設定後の接続確認・認証テスト・動作検証
- 約13.1KBの実装ファイル

### **verify_gcp_setup.sh**
GCP 環境の設定状況を包括的に検証・診断します。
- **環境診断**: GCP サービス設定・権限・接続状況の全体確認
- **Cloud Run検証**: サービス状態・設定・ヘルスチェック・スケーリング
- **Secret Manager確認**: 認証情報存在・アクセス権限・設定整合性
- **GitHub Actions確認**: OIDC 設定・Workload Identity・CI/CD 権限
- **ネットワーク検証**: API 接続・外部サービス通信・レスポンス確認
- **問題診断**: 設定不備検出・修復提案・詳細レポート生成
- 約26.6KBの実装ファイル

## 📝 使用方法・例

### **基本的なデプロイワークフロー**
```bash
# 1. 品質チェック（デプロイ前必須）
bash scripts/testing/checks.sh

# 2. GCP環境検証
bash scripts/deployment/verify_gcp_setup.sh --full

# 3. 本番環境デプロイ
bash scripts/deployment/deploy_production.sh --staged

# 4. デプロイ後確認
bash scripts/deployment/verify_gcp_setup.sh --cloud-run-check
```

### **初回環境構築**
```bash
# 1. GCP サービス・CI/CD環境構築
bash scripts/deployment/setup_ci_prerequisites.sh --interactive

# 2. 認証情報設定
bash scripts/deployment/setup_gcp_secrets.sh --interactive

# 3. 環境設定検証
bash scripts/deployment/verify_gcp_setup.sh --full --final-check

# 4. 初回デプロイ実行
bash scripts/deployment/deploy_production.sh --first-deploy
```

### **Docker コンテナ管理**
```bash
# ローカルでのコンテナテスト
docker build -t crypto-bot .
docker run --env-file .env crypto-bot

# エントリーポイント直接実行
bash scripts/deployment/docker-entrypoint.sh

# ヘルスチェック確認
curl http://localhost:8080/health
```

### **トラブルシューティング**
```bash
# 詳細診断実行
bash scripts/deployment/verify_gcp_setup.sh --debug --verbose

# Cloud Run ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# サービス状態確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# デプロイ履歴確認
gcloud run revisions list --service=crypto-bot-service-prod
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **GCP プロジェクト**: 有効なGCPプロジェクト・課金設定・必要APIs有効化
- **権限設定**: Cloud Run・Artifact Registry・Secret Manager の管理者権限
- **GitHub統合**: GitHub Actions・OIDC・Workload Identity 設定完了
- **Docker環境**: Docker・gcloud CLI・kubectl インストール・認証設定

### **デプロイメント制約**
- **品質ゲート**: テスト成功・コード品質・依存関係確認必須
- **段階的デプロイ**: paper→stage→live 順次実行・各段階での確認必須
- **リソース制限**: GCP 無料枠・Cloud Run メモリ/CPU制限・コスト管理
- **ネットワーク**: 外部API接続・Discord通知・Bitbank API アクセス必須

### **セキュリティ要件**
- **認証管理**: API キー・シークレット・Webhook URL の適切な保護
- **アクセス制御**: 最小権限原則・サービスアカウント権限管理
- **監査**: 設定変更・デプロイ履歴・アクセスログ記録
- **暗号化**: 通信暗号化・データ保護・Secret Manager 活用

### **運用制約**
- **監視**: Cloud Run ヘルスチェック・Discord 通知・ログ監視必須
- **バックアップ**: 設定ファイル・モデル・履歴のバックアップ管理
- **復旧**: ロールバック手順・障害復旧・データ復元計画
- **更新**: 定期的なセキュリティ更新・依存関係管理・環境保守

## 🔗 関連ファイル・依存関係

### **コンテナ・デプロイシステム**
- `Dockerfile`: コンテナイメージ定義・依存関係・実行環境設定
- `docker-compose.yml`: 開発環境・テスト環境・ローカル実行設定
- `main.py`: アプリケーションエントリーポイント・取引システム起動

### **設定・環境管理**
- `config/production/`: 本番環境設定・パラメータ・環境変数定義
- `config/secrets/`: ローカル認証情報・Discord Webhook・開発用設定
- `.env`: 環境変数テンプレート・ローカル開発設定・Docker設定

### **品質保証・テスト**
- `scripts/testing/checks.sh`: デプロイ前品質チェック・テスト実行
- `tests/`: 単体テスト・統合テスト・デプロイメントテスト
- `.github/workflows/`: CI/CD パイプライン・自動テスト・デプロイワークフロー

### **GCP統合サービス**
- **Cloud Run**: 本番実行環境・スケーラブル・サーバーレス実行基盤
- **Artifact Registry**: Docker イメージ管理・バージョン管理・セキュリティ
- **Secret Manager**: 認証情報管理・API キー・セキュア設定保存
- **IAM & Workload Identity**: サービスアカウント・権限管理・GitHub統合

### **外部システム連携**
- **GitHub Actions**: CI/CD 自動化・テスト・デプロイ・週次学習ワークフロー
- **Discord API**: 通知システム・アラート・運用監視・レポート配信
- **Bitbank API**: 取引システム・市場データ・注文実行・認証連携

### **監視・ログシステム**
- `src/monitoring/`: Discord 通知・アラート・監視システム
- `src/core/logger.py`: 構造化ログ・JST時刻・Cloud Run ログ統合
- `logs/`: 実行ログ・エラーログ・デプロイ履歴・運用記録