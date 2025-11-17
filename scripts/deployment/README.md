# scripts/deployment/ - デプロイメント・インフラ管理スクリプト（Phase 52.4）

**最終更新**: 2025年11月15日 - Phase 52.4コード整理完了

## 🎯 役割・責任

本番環境へのデプロイメント、GCP Cloud Run環境の管理、Docker コンテナベースの運用基盤を提供します。実運用に必要なスクリプトのみを管理し、初期セットアップ用スクリプト（Phase 29）は archive/ に保管しています。

## 📂 ファイル構成（Phase 52.4）

```
scripts/deployment/
├── README.md                    # このファイル（Phase 52.4）
├── docker-entrypoint.sh         # Dockerコンテナエントリーポイント・起動制御（Phase 52.4）
└── archive/                     # 初期セットアップ用スクリプト（Phase 29・使用頻度極低）
    ├── setup_gcp_environment.sh     # GCP環境構築（Phase 29・初期構築のみ）
    └── verify_gcp_setup.sh          # GCP環境検証（Phase 29・診断時のみ）
```

**Phase 52.4整理内容**:
- docker-entrypoint.sh: Phase参照統一・ヘルスチェック情報更新
- README.md: Phase参照統一・統計情報削除・特徴量数正確化
- archive/: Phase 29歴史的スクリプト（Secret名バグ修正・Phase ラベル修正）

## 📋 主要ファイル・フォルダの役割

### **docker-entrypoint.sh**（Phase 52.4）
Docker コンテナの起動制御とプロセス管理を担当します。

**機能**:
- **デュアルプロセス**: ヘルスチェックサーバーと取引システムの並行実行
- **MLモデル検証**: 起動時55特徴量モデル動作確認
- **ヘルスチェックAPI**: `/health` エンドポイント・Phase 52.4情報応答
- **プロセス監視**: 異常終了検知・自動復旧処理
- **Cloud Run最適化**: メモリ効率・起動時間短縮

**Phase 52.4更新内容**:
- Phase参照更新: Phase 49/50.9 → Phase 52.4
- 統計情報更新: 1,153テスト・68.77%カバレッジ
- 特徴量情報: 55特徴量システム（49基本+6戦略）
- 戦略情報: 6戦略システム（ATRBased/Donchian/ADX/BBReversal/Stochastic/MACDCrossover）
- バージョン番号: 49.0.0 → 52.4.0

### **archive/**（Phase 29歴史的スクリプト）
GCP環境の初期構築（Phase 29）用スクリプトを保管。環境構築済みのため通常運用では使用しません。

**setup_gcp_environment.sh**（690行・Phase 29）:
- 用途: GCP環境初期構築（API有効化・IAM設定・Secret Manager設定）
- 使用頻度: 極めて低い（環境再構築時のみ）
- Phase 52.4修正: Phase ラベルバグ修正（phase=22 → phase=29）

**verify_gcp_setup.sh**（714行・Phase 29）:
- 用途: GCP環境検証・診断
- 使用頻度: 低い（環境診断時のみ）
- Phase 52.4修正: Secret名バグ修正（discord-webhook → discord-webhook-url）

**保持理由**: 環境再構築・新規環境セットアップ時に有用

## 📝 使用方法・例

### **日常運用**（Phase 52.4）
```bash
# 1. 品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 2. 本番環境稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# 3. システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# 4. ヘルスチェック確認（Phase 52.4情報）
curl https://[SERVICE_URL]/health | jq
```

**注**: デプロイは`.github/workflows/ci.yml`で自動実行

### **Docker コンテナ管理**
```bash
# ローカルコンテナテスト
docker build -t crypto-bot .
docker run --env-file .env crypto-bot

# ヘルスチェック確認
curl http://localhost:8080/health
```

### **トラブルシューティング**（Phase 52.4）
```bash
# Cloud Run ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=50

# サービス状態確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# デプロイ履歴確認
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1

# ヘルスチェック詳細（Phase 52.4情報含む）
curl https://[SERVICE_URL]/health | jq

# 環境診断（Phase 29スクリプト・通常運用では不要）
bash scripts/deployment/archive/verify_gcp_setup.sh --debug --verbose
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **GCP プロジェクト**: 有効なGCPプロジェクト・課金設定・必要APIs有効化
- **権限設定**: Cloud Run・Artifact Registry・Secret Manager の管理者権限
- **GitHub統合**: GitHub Actions・OIDC・Workload Identity 設定完了
- **Docker環境**: Docker・gcloud CLI インストール・認証設定

### **デプロイメント制約**（Phase 52.4）
- **品質ゲート**: テスト100%成功・カバレッジ基準達成・コード品質確認必須
- **自動デプロイ**: GitHub Actions CI/CDワークフロー（.github/workflows/ci.yml）
- **リソース制限**: GCP Cloud Run 1Gi・1CPU・月額700-900円
- **ネットワーク**: Discord通知・Bitbank API アクセス必須

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

### **外部システム連携**（Phase 52.4）
- **GitHub Actions**: CI/CD 自動化・テスト・デプロイ・週次ワークフロー
- **Discord API**: 通知システム・週間レポート配信
- **Bitbank API**: 取引システム・市場データ・注文実行

### **監視・ログシステム**
- `src/monitoring/`: Discord 通知・週間レポート
- `src/core/logger.py`: 構造化ログ・JST時刻・Cloud Run統合
- `src/backtest/logs/`: バックテストログ・JSONレポート

---

## 📋 Phase 52.4完了内容

**docker-entrypoint.sh更新**:
- Phase参照統一（Phase 49/50.9 → Phase 52.4）
- ヘルスチェックレスポンス更新（tests/coverage/features/models情報）
- バージョン番号更新（49.0.0 → 52.4.0）
- 統計情報は動的取得（随時変動のため固定記載削除）

**README.md更新**:
- Phase参照統一（Phase 49 → Phase 52.4）
- 統計情報削除（テスト数・カバレッジは随時変動）
- 特徴量数正確化（55特徴量・6戦略）
- ファイル構成・使用方法簡潔化

**archive/バグ修正**（Priority 3-4）:
- verify_gcp_setup.sh: Secret名修正（discord-webhook → discord-webhook-url）
- setup_gcp_environment.sh: Phaseラベル修正（phase=22 → phase=29）
- 歴史的スクリプトとしての位置づけ明確化

---

**最終更新**: 2025年11月15日 - Phase 52.4コード整理完了