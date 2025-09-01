# config/infrastructure/ - インフラストラクチャ設定

**Phase 16-B完了**: 設定一元化・保守性向上完成により、160個ハードコード値統合・8個ヘルパー関数・620テスト100%成功・50%+カバレッジで、個人開発最適化されたGCP統合インフラストラクチャシステムが完成

## 🎯 役割・責任

Google Cloud Platform（GCP）を基盤とした CI/CD パイプライン、段階的デプロイ（paper→live）、セキュリティ統合の設定管理を担当します。GitHub Actions と GCP の完全統合により、bitbank信用取引専用の高品質で安全な自動デプロイメントシステムを提供します。

## 📂 ファイル構成

```
infrastructure/
├── README.md               # このファイル（Phase 16-B完成版）
├── gcp_config.yaml        # GCP統合設定（Phase 16-B対応・設定一元化最適化）
└── cloudbuild.yaml        # Cloud Build実行定義（620テスト対応）
```

## 🔧 主要機能・実装

### **GCP統合アーキテクチャ（Phase 16-B完成版）**

**基盤サービス統合**:
```yaml
# GCP基本構成（Phase 16-B対応）
project:
  id: "my-crypto-bot-project"
  region: "asia-northeast1"
  services:
    - Cloud Run: crypto-bot-service-prod（本番統一サービス）
    - Artifact Registry: Dockerイメージ管理・セキュリティスキャン
    - Secret Manager: bitbank API認証・Discord Webhook管理
    - Cloud Logging: 構造化ログ・監視統合
    - Cloud Monitoring: メトリクス・アラート・ヘルスチェック
```

### **CI/CD完全自動化システム（620テスト対応）**

**GitHub Actions統合**:
- **品質ゲート**: 620テスト・50%+カバレッジ・160個設定値検証・型安全性チェック
- **自動デプロイ**: mainブランチプッシュで即座デプロイ
- **ヘルスチェック**: デプロイ後自動稼働確認・設定一元化監視
- **ロールバック対応**: 障害時の迅速復旧機能

**デプロイフロー（Phase 16-B完成）**:
```yaml
1. 品質保証フェーズ: 620テスト・50%+カバレッジ・設定一元化検証・型安全性チェック
2. ビルド・プッシュ: Docker イメージ・Artifact Registry
3. 本番デプロイ: Cloud Run・環境変数・Secret統合
4. ヘルスチェック: 自動稼働確認・設定一元化監視開始
5. 通知・監視: Discord・Cloud Monitoring・アラート設定
```

### **段階的デプロイシステム（2段階・シンプル化）**

**paper → live 段階移行**:
```yaml
# Stage廃止・2段階デプロイ統合
deployment_modes:
  paper:
    memory: "1Gi"
    min_instances: 0
    description: "ペーパートレード（デフォルト・安全テスト）"
    
  live:
    memory: "1Gi" 
    min_instances: 1
    description: "実資金取引（十分な検証後に移行）"
```

### **セキュリティ強化システム（bitbank専用）**

**Workload Identity統合**:
```yaml
# 自動認証・最小権限設計
iam:
  github_service_account: "github-actions-sa"
  workload_identity_pool: "github-pool"  
  automatic_token_refresh: true
  minimal_permissions: true  # bitbank取引専用権限
```

**機密情報管理**:
- **Secret Manager**: `bitbank-api-key`, `bitbank-api-secret`, `discord-webhook-url`
- **環境変数分離**: 設定ファイルから機密情報完全除外
- **アクセス制御**: 最小権限・監査ログ・main ブランチ制限
- **セキュリティ監視**: 不正アクセス検出・即座アラート

## 📝 使用方法・例

### **自動デプロイ（推奨フロー）**
```bash
# Phase 16-B標準デプロイフロー
git add .
git commit -m "feat: Phase 16-B設定一元化完成・620テスト成功"
git push origin main
# → 自動実行: 620テスト→設定検証→ビルド→デプロイ→設定一元化監視開始

# 実行状況確認
gh run list --limit 5
gh run watch
```

### **手動インフラ管理**
```bash
# GCP基盤確認
gcloud projects describe my-crypto-bot-project
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# Secret Manager確認（bitbank専用）
gcloud secrets list
gcloud secrets versions access latest --secret=bitbank-api-key
gcloud secrets versions access latest --secret=discord-webhook-url

# Workload Identity確認
gcloud iam workload-identity-pools list --location=global
```

### **監視・デバッグ**
```bash
# リアルタイム監視
gcloud logging tail "resource.type=cloud_run_revision"

# パフォーマンス分析（Phase 16-B対応）
python3 scripts/analytics/dashboard.py --gcp
python3 scripts/management/dev_check.py validate

# デプロイ履歴確認
gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1
```

## ⚠️ 注意事項・制約

### **bitbank信用取引制約**
- **通貨ペア**: BTC/JPY専用（信用取引対応）
- **レバレッジ**: 最大2倍（bitbank仕様準拠・安全性重視で1倍）
- **資金管理**: 1万円→成功時50万円段階拡大
- **取引時間**: 24時間・自動取引継続性確保

### **Phase 16-B対応事項**
- **620テスト**: 設定一元化全テスト100%合格維持・品質保証継続
- **50%+カバレッジ**: 目標を上回る企業級品質保証達成・継続監視
- **型安全性**: MyPy統合・段階的型エラー解消継続
- **2段階デプロイ**: stage廃止・paper→live統合完了

### **インフラ変更時の注意**
- **影響範囲**: GCPプロジェクト全体への影響考慮
- **ダウンタイム**: 本番サービス稼働時間への配慮
- **コスト影響**: 個人開発予算（月額2000円程度）監視
- **セキュリティ**: bitbank API・Discord Webhook保護

### **CI/CD運用制約**
- **GitHub Actions制限**: 月間2000分無料枠・同時実行制限
- **Cloud Run制約**: 1Gi メモリ・1 CPU・同時リクエスト数制限
- **Artifact Registry**: イメージサイズ・保存容量制限
- **ネットワーク**: asia-northeast1 リージョン最適化

## 🔗 関連ファイル・依存関係

### **重要な外部依存**
- **`.github/workflows/ci.yml`**: Phase 16-B対応CI/CDパイプライン
- **`Dockerfile`**: コンテナイメージ定義・12特徴量対応
- **`requirements.txt`**: Python依存関係・型安全性ライブラリ
- **`scripts/deployment/`**: デプロイ支援スクリプト

### **GCPサービス統合**
- **Cloud Run**: `crypto-bot-service-prod`本番サービス
- **Artifact Registry**: `crypto-bot-repo`イメージリポジトリ  
- **Secret Manager**: bitbank・Discord機密情報安全管理
- **Cloud Logging**: 構造化ログ・検索・監視統合
- **Cloud Monitoring**: メトリクス・アラート・ダッシュボード

### **設定システム連携**
- **`config/core/base.yaml`**: 基本設定・段階的デプロイ統合
- **`config/core/feature_order.json`**: 12個厳選特徴量定義
- **`config/production/production.yaml`**: 本番特化設定
- **`src/core/config.py`**: モード設定一元化システム

### **監視・分析システム**
- **Discord Webhook**: リアルタイム通知・障害アラート
- **GitHub Actions**: デプロイ監視・品質ゲート
- **Cloud Monitoring**: パフォーマンス監視・SLA管理
- **pytest**: インフラ設定検証・620テスト統合

## 📊 Phase 16-B最適化成果

### **設定最適化結果**
- **gcp_config.yaml**: 380行→180行（53%削減）
- **stage廃止**: stage-10/50削除・2段階デプロイ統合
- **設定統合**: 重複排除・現実準拠・bitbank制約準拠
- **品質向上**: 620テスト・50%+カバレッジ・設定一元化完成

### **個人開発最適化**
- **コスト効率**: 月額約2000円・1Gi メモリ・1 CPU
- **段階拡大**: 1万円→10万円→50万円（成功時）
- **安全性重視**: paper デフォルト・live 慎重移行
- **取引制約**: bitbank信用取引・2倍レバレッジ上限・BTC/JPY専用

---

**重要**: Phase 16-B完了により、bitbank信用取引専用・160個ハードコード値統合・8個ヘルパー関数による動的設定管理・620テスト品質保証・設定一元化システムが完成しました。このディレクトリはインフラストラクチャの中核であり、thresholds.yaml設定変更時は本番サービス・個人開発予算への影響を慎重に確認し、適切な監視体制での運用を実施してください。