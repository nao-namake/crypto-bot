# Deployment Scripts

デプロイ・Docker・本番環境系スクリプト集（Phase 12 CI/CD統合・24時間監視・実データ収集対応）

## 📂 スクリプト一覧

### setup_gcp_secrets.sh
**GCP Secret Manager自動設定スクリプト（Phase 12対応・レガシー改良版）**

Bitbank API認証情報・Discord Webhook等のシークレット管理をGCP Secret Managerで自動化。GitHub Actions CI/CDパイプライン・Workload Identity統合・セキュリティ最適化を実現。

#### 主要機能
- **対話式設定**: API Key・Secret・Webhook URL等の安全な入力・保存
- **設定確認**: 既存シークレット一覧・アクセス権限・整合性チェック
- **CI/CD統合**: GitHub Actions Workload Identity・自動認証設定
- **セキュリティ強化**: 暗号化保存・アクセスログ・権限最小化

#### 使用例
```bash
# 対話式設定（推奨）
bash scripts/deployment/setup_gcp_secrets.sh --interactive

# 設定確認
bash scripts/deployment/setup_gcp_secrets.sh --check

# CI/CD用セットアップ
bash scripts/deployment/setup_gcp_secrets.sh --setup-ci

# ヘルプ表示
bash scripts/deployment/setup_gcp_secrets.sh --help
```

#### Phase 12改良点
- **レガシー知見活用**: 過去のエラーパターン・解決策を統合
- **GitHub Actions統合**: Workload Identity自動設定・シームレス認証
- **セキュリティ向上**: 最小権限・監査ログ・自動ローテーション対応
- **運用効率化**: 一括設定・エラーハンドリング・トラブルシューティング

### docker-entrypoint.sh
**Docker統合エントリポイント（Phase 12対応・CI/CD統合・監視統合）**

新システム用の軽量Dockerエントリポイント。本番環境でのコンテナ起動・プロセス管理・ヘルスチェック・CI/CD統合・24時間監視を担当。

#### 主要機能
- **統合エントリポイント**: main.py統合システムの起動制御・GitHub Actions対応
- **環境変数管理**: MODE・EXCHANGE・LOG_LEVEL等の設定・段階的デプロイ対応
- **プロセス監視**: PID管理・グレースフルシャットダウン・CI/CD統合
- **ヘルスチェック**: 基本的な動作確認・API接続テスト・24時間監視統合
- **データ収集**: 取引統計・パフォーマンス指標・実データ保存（Phase 12追加）

#### 使用例
```bash
# Docker内で自動実行（通常は手動実行不要）
./scripts/deployment/docker-entrypoint.sh

# 手動実行（デバッグ用）
chmod +x scripts/deployment/docker-entrypoint.sh
./scripts/deployment/docker-entrypoint.sh
```

#### Docker統合
```dockerfile
# Dockerfile内での使用
COPY scripts/deployment/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
```

### deploy_production.sh
**本番デプロイスクリプト（Phase 12対応・CI/CD統合・実データ収集統合）**

GCP Cloud Runへの本番環境デプロイを自動化。品質チェック・Docker Build・デプロイ・動作確認・CI/CD統合・段階的リリース・実データ収集システム統合を実行。

#### 主要機能
- **事前品質チェック**: checks.sh実行・286テスト確認・CI/CD品質ゲート
- **Docker Build**: 最適化イメージ作成・レジストリプッシュ・セキュリティスキャン
- **段階的デプロイ**: 10%→50%→100%トラフィック分割・カナリアリリース
- **Cloud Run デプロイ**: サービス更新・環境変数設定・Workload Identity統合・MIN_INSTANCES=1（安定性重視）
- **デプロイ後確認**: ヘルスチェック・基本動作確認・24時間監視開始・実データ収集開始

#### 使用例
```bash
# 本番デプロイ実行（段階的デプロイ・CI/CD統合）
bash scripts/deployment/deploy_production.sh

# ドライラン（デプロイなし・チェックのみ・CI/CD事前チェック）
bash scripts/deployment/deploy_production.sh --dry-run

# 段階的デプロイ（10%→50%→100%）
bash scripts/deployment/deploy_production.sh --canary

# GitHub Actions経由デプロイ（推奨・Phase 12対応）
git push origin main  # 自動CI/CDパイプライン実行

# 統合管理CLI経由確認（推奨）
python scripts/management/bot_manager.py health-check

# パフォーマンス分析（Phase 12追加）
python scripts/analytics/performance_analyzer.py --period 24h --format markdown
```

## 🎯 設計原則

### デプロイ哲学
- **品質ファースト**: デプロイ前の完全品質チェック必須・CI/CD品質ゲート
- **ゼロダウンタイム**: ローリングアップデート・グレースフルシャットダウン・段階的デプロイ
- **回復性**: ロールバック機能・障害時復旧手順・自動ロールバック
- **監視統合**: デプロイ後の自動ヘルスチェック・24時間監視・パフォーマンス追跡

### セキュリティ（Phase 11強化）
- **シークレット管理**: GCP Secret Manager統合・Workload Identity・自動ローテーション
- **最小権限**: 必要最小限のIAM権限設定・監査ログ・アクセス制御
- **ネットワーク**: VPC・ファイアウォール設定・トラフィック暗号化
- **ログ監視**: Cloud Logging・異常検知・セキュリティ監査・コンプライアンス

## 🏗️ GCP Cloud Run 設定

### 環境設定
```bash
# 必要な環境変数
export PROJECT_ID="my-crypto-bot-project"
export REGION="asia-northeast1"
export SERVICE_NAME="crypto-bot-service-prod"
export DOCKER_REPO="asia-northeast1-docker.pkg.dev/${PROJECT_ID}/crypto-bot-repo"
```

### Cloud Run仕様
```yaml
# 本番環境設定
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "5"
    spec:
      containerConcurrency: 80
      timeoutSeconds: 3600
      containers:
      - image: asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:latest
        resources:
          limits:
            cpu: "1"
            memory: "1Gi"
        env:
        - name: MODE
          value: "live"
        - name: EXCHANGE  
          value: "bitbank"
        - name: LOG_LEVEL
          value: "INFO"
```

### 秘密情報管理
```bash
# GCP Secret Manager設定
gcloud secrets create bitbank-api-key --data-file=-
gcloud secrets create bitbank-api-secret --data-file=-

# Cloud Run環境変数設定
--set-secrets="BITBANK_API_KEY=bitbank-api-key:latest,BITBANK_API_SECRET=bitbank-api-secret:latest"
```

## 🔧 トラブルシューティング

### よくあるエラー

**1. 品質チェック失敗**
```bash
❌ 品質チェック失敗。デプロイを中止します。
```
**対処**: 品質問題修正後再実行
```bash
# 品質チェック単体実行
bash scripts/quality/checks.sh

# 問題修正後デプロイ
bash scripts/deployment/deploy_production.sh
```

**2. Docker Build 失敗**
```bash
❌ Docker Build失敗: permission denied
```
**対処**: Docker権限・認証確認
```bash
# Docker権限確認
docker ps

# GCP認証確認
gcloud auth list
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
```

**3. Cloud Run デプロイ失敗**
```bash
❌ Cloud Run deployment failed
```
**対処**: GCP権限・リソース確認
```bash
# Cloud Run権限確認
gcloud run services list --region=asia-northeast1

# リソース使用量確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
```

**4. ヘルスチェック失敗**
```bash
❌ デプロイ後ヘルスチェック失敗
```
**対処**: サービス状態・ログ確認
```bash
# サービス状態確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# ログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

## 📊 運用管理

### デプロイフロー（Phase 11 CI/CD統合）
```bash
# 推奨デプロイフロー（CI/CD統合・段階的デプロイ）
1. python scripts/management/bot_manager.py full-check  # 事前品質確認
2. git add . && git commit -m "deploy: Phase 11 update"
3. git push origin main                                  # GitHub Actions自動実行
4. python scripts/management/bot_manager.py health-check # 本番環境確認
5. python scripts/management/bot_manager.py monitor --hours 24 # 24時間監視開始

# 手動デプロイフロー（緊急時）
1. python scripts/management/bot_manager.py full-check  # 事前品質確認
2. bash scripts/deployment/deploy_production.sh --canary # 段階的デプロイ
3. python scripts/management/bot_manager.py status     # デプロイ後確認
```

### ロールバック手順
```bash
# 前回リビジョンにロールバック
gcloud run services update-traffic crypto-bot-service-prod \
  --to-revisions=PREVIOUS=100 \
  --region=asia-northeast1
```

### 監視・アラート
```bash
# サービス稼働状況確認
gcloud run services list --region=asia-northeast1

# ログ監視
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10

# メトリクス確認
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision"
```

## 📈 Performance Optimization

### Docker最適化
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
# ... build dependencies

FROM python:3.11-slim as runtime
# ... runtime only
COPY --from=builder /app /app
```

### Cloud Run最適化（Phase 12コスト効率版）
- **CPU割り当て**: 本番1CPU（コスト最適化・軽量設計活用）
- **メモリ使用量**: 本番1Gi（効率的メモリ使用・97→12特徴量削減効果）  
- **同時実行数**: 80（接続プール考慮）
- **タイムアウト**: 3600秒（長時間バックテスト対応）
- **最小インスタンス**: 1（取引継続性・SIGTERM問題回避）

### コスト最適化（レガシー知見活用）
- **MIN_INSTANCES=1**: SIGTERM頻発問題完全解決・約1,800円/月実績
- **CPU統一**: 1CPU統一設計・50%コスト削減
- **メモリ効率**: 1Gi最適化・軽量システム設計活用
- **Region**: asia-northeast1（東京・レイテンシー最小）

## 🎯 Phase 12実装済み機能

**CI/CD統合**:
- ✅ **GitHub Actions CI/CD**: 自動品質チェック・段階的デプロイ・24時間監視
- ✅ **段階的デプロイ**: paper → stage-10 → stage-50 → live（10%→50%→100%）
- ✅ **品質ゲート**: 398テスト・flake8・コード整形・包括的チェック

**24時間監視**:
- ✅ **自動監視**: 15分間隔ヘルスチェック・エラー分析・パフォーマンス追跡
- ✅ **アラート**: Discord通知・クリティカル状況即座対応
- ✅ **レポート生成**: パフォーマンス分析・統計サマリー・改善提案

**コスト最適化**:
- ✅ **MIN_INSTANCES=1**: レガシー知見活用・SIGTERM問題解決・約1,800円/月
- ✅ **リソース効率**: 1CPU/1Gi統一・50%コスト削減・軽量設計活用

## 🔮 Future Enhancements

Phase 13以降の拡張予定:
- **実データ収集**: Phase 12-2実装中・取引統計・A/Bテスト基盤
- **Blue-Green Deploy**: 無停止デプロイメント・ゼロダウンタイム・トラフィック切り替え
- **Auto Scaling**: トラフィック連動スケーリング・負荷予測・動的リソース調整
- **Multi-Region**: 複数リージョン冗長化・災害復旧・グローバル展開
- **Advanced CI/CD**: GitHub Actions完全自動化・パイプライン最適化・並列実行
- **Enhanced Canary**: より高度な段階的リリース・A/Bテスト・メトリクス連動
- **Infrastructure as Code**: Terraform統合・Pulumi・クラウドネイティブ管理
- **Security Enhancement**: SAST/DAST統合・脆弱性スキャン・コンプライアンス自動化

## 💡 Best Practices

### セキュリティ
- **定期的な基盤更新**: ベースイメージ・依存関係の更新
- **シークレットローテーション**: API キー定期変更
- **アクセス制限**: 必要最小限のネットワークアクセス
- **監査ログ**: 全デプロイ操作のログ記録

### 信頼性
- **健全性チェック**: デプロイ前後の包括的チェック
- **段階的展開**: 開発→ステージング→本番の順次展開
- **自動復旧**: 障害時の自動ロールバック・通知
- **容量計画**: トラフィック予測に基づくリソース設計