# scripts/deployment/ - デプロイメント・インフラ管理スクリプト（Phase 49完了時点）

## 🎯 役割・責任

本番環境へのデプロイメント、GCP Cloud Run環境の管理、Docker コンテナベースの運用基盤を提供します。実運用に必要なスクリプトのみを管理し、初期セットアップ用スクリプトは archive/ に保管しています。

**Phase 49完了成果**: 1,117テスト100%成功・68.32%カバレッジ達成・バックテスト完全改修・確定申告対応・週間レポート実装

## 📂 ファイル構成（Phase 49完了版）

```
scripts/deployment/
├── README.md                    # このファイル（Phase 49完了版）
├── docker-entrypoint.sh         # Dockerコンテナエントリーポイント・起動制御（Phase 49完了）
└── archive/                     # 初期セットアップ用スクリプト（環境構築済みのため使用頻度低）
    ├── setup_gcp_environment.sh     # 統合GCP環境構築・認証管理（初期構築のみ）
    └── verify_gcp_setup.sh          # GCP環境検証・設定確認（診断時のみ）
```

**注**: deploy_production.shは削除（`.github/workflows/ci.yml`で`gcloud run deploy`を直接使用）

## 📋 主要ファイル・フォルダの役割

### **docker-entrypoint.sh**（Phase 49完了）
Docker コンテナの起動制御とプロセス管理を担当します。
- **デュアルプロセス**: ヘルスチェックサーバーと取引システムの並行実行
- **環境初期化**: Python パス設定・依存関係確認・設定ファイル検証
- **MLモデル検証**: 起動時55特徴量Strategy-Aware MLモデル動作確認
- **ヘルスチェックAPI**: /health エンドポイント・軽量JSON応答・Phase 49情報表示
- **プロセス監視**: メインプロセス監視・異常終了検知・自動復旧処理
- **エラーハンドリング**: 起動失敗時の詳細ログ・診断情報・適切な終了処理
- **Cloud Run最適化**: メモリ効率・起動時間短縮・スケーリング対応
- 約8.7KBの実装ファイル

### **archive/**（初期セットアップ専用）
GCP環境の初期構築・検証用スクリプトを保管するフォルダです。Phase 49時点でGCP環境構築済みのため、通常運用では使用しません。

**setup_gcp_environment.sh**（24KB・690行・Phase 29）:
- **用途**: GCP環境初期構築（API有効化・IAM設定・Secret Manager設定）
- **使用頻度**: 極めて低い（初期構築済み・環境再構築時のみ）
- **代替方法**: 日常運用は`gcloud`コマンドで直接実行

**verify_gcp_setup.sh**（26KB・714行・Phase 29）:
- **用途**: GCP環境検証・診断（Cloud Run・Secret Manager・GitHub Actions）
- **使用頻度**: 低い（環境診断時のみ・`.github/workflows/ci.yml`で権限付与のみ）
- **代替方法**: `gcloud run services describe crypto-bot-service-prod --region=asia-northeast1`等で直接確認

**保持理由**: 環境再構築・新規環境セットアップ時に有用（完全削除せず保管）

## 📝 使用方法・例

### **日常運用**（Phase 49完了版）
```bash
# 1. 品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 2. 本番環境稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# 3. システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# 4. ヘルスチェック確認
curl https://crypto-bot-service-prod-XXXXXXXX.asia-northeast1.run.app/health
```

**注**: デプロイは`.github/workflows/ci.yml`で自動実行（GitHub Actionsワークフロー）

### **環境再構築時のみ**（通常運用では不要）
```bash
# 1. 統合GCP環境構築（完全セットアップ）
bash scripts/deployment/archive/setup_gcp_environment.sh --full

# 2. 環境設定検証
bash scripts/deployment/archive/verify_gcp_setup.sh --full --final-check

# 3. デプロイはGitHub Actionsで自動実行
# （ci.ymlのgcloud run deployが実行される）
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

### **トラブルシューティング**（Phase 49完了版）
```bash
# Cloud Run ログ確認（Phase 49情報表示）
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# サービス状態確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# デプロイ履歴確認
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1

# ヘルスチェック確認（Phase 49情報取得）
curl https://crypto-bot-service-prod-XXXXXXXX.asia-northeast1.run.app/health | jq

# 環境再構築時の詳細診断（通常運用では不要）
bash scripts/deployment/archive/verify_gcp_setup.sh --debug --verbose
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **GCP プロジェクト**: 有効なGCPプロジェクト・課金設定・必要APIs有効化
- **権限設定**: Cloud Run・Artifact Registry・Secret Manager の管理者権限
- **GitHub統合**: GitHub Actions・OIDC・Workload Identity 設定完了
- **Docker環境**: Docker・gcloud CLI・kubectl インストール・認証設定

### **デプロイメント制約**（Phase 49完了版）
- **品質ゲート**: 1,117テスト100%成功・68.32%カバレッジ・コード品質確認必須
- **自動デプロイ**: GitHub Actions CI/CDワークフロー（.github/workflows/ci.yml）で自動実行
- **リソース制限**: GCP Cloud Run 1Gi・1CPU・月額700-900円コスト管理
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