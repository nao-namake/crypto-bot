# config/infrastructure/ - GCPインフラストラクチャ設定

## 🎯 役割・責任

Google Cloud Platform（GCP）を基盤としたインフラストラクチャ設定を管理します。Cloud Run本番環境、Secret Manager、GitHub Actions CI/CD統合を定義し、24時間稼働する自動取引システムの運用基盤を提供します。

**Phase 52.4完了時点（2025年11月15日）**:
- ML統合システム・レジーム別最適化
- Cloud Run: crypto-bot-service-prod（asia-northeast1）
- 月額コスト: 700-900円
- 5分間隔実行・24時間稼働

---

## 📂 ファイル構成

```
infrastructure/
├── README.md                  # このファイル
├── gcp_config.yaml           # GCP統合設定（Cloud Run・Secret Manager等）
└── iam_policy_backup.json    # IAM権限バックアップ（2025年9月30日）
```

---

## 📋 各ファイルの役割

### **gcp_config.yaml** - GCP統合設定

GCPプロジェクト全体の設定を定義します。

**主要設定内容**:
- **プロジェクト情報**: ID `my-crypto-bot-project`、リージョン `asia-northeast1`
- **Cloud Run**: サービス `crypto-bot-service-prod`
  - メモリ: 1Gi、CPU: 1
  - Paper mode: min 0 / max 1 instances
  - Live mode: min 1 / max 2 instances
- **Secret Manager**:
  - `bitbank-api-key:3`
  - `bitbank-api-secret:3`
  - `discord-webhook-url:5`
- **Workload Identity**: GitHub Actions認証統合
  - Pool: `github-pool`
  - Provider: `github-provider`
  - Service Account: `github-deployer@my-crypto-bot-project.iam.gserviceaccount.com`
- **環境変数**: MODE=live、LOG_LEVEL=INFO、PYTHONPATH=/app

### **iam_policy_backup.json** - IAM権限バックアップ

実際のGCP環境のIAM権限設定バックアップです。権限トラブル時の復旧用参照ファイルとして使用します。

**記録内容**:
- Service Account権限一覧
- 本番環境の実際の権限構成
- 最終更新: 2025年9月30日

---

## 📝 使用方法・運用コマンド

### **自動デプロイ（GitHub Actions）**

```bash
# コードをプッシュすると自動実行
git add .
git commit -m "機能実装完了"
git push origin main
# → GitHub Actionsが全テスト実行 → Dockerビルド → Cloud Run自動デプロイ
```

### **サービス状況確認**

```bash
# Cloud Runサービス稼働状況
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# 詳細ステータス（URL・最新リビジョン）
gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format="value(status.conditions[0].status,status.url,status.latestReadyRevisionName)"

# 最新リビジョン確認（JST表示）
TZ='Asia/Tokyo' gcloud run revisions list \
  --service=crypto-bot-service-prod \
  --region=asia-northeast1 \
  --limit=5 \
  --format="table(metadata.name,metadata.creationTimestamp.date(tz='Asia/Tokyo'),status.conditions[0].status)"
```

### **ログ確認**

```bash
# 最新ログ確認
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod" \
  --limit=20

# エラーログのみ
gcloud logging read \
  "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit=10

# 取引ログ確認
gcloud logging read \
  'textPayload:"取引" OR textPayload:"BUY" OR textPayload:"SELL"' \
  --limit=10

# 残高確認
gcloud logging read \
  'textPayload:"残高" OR textPayload:"balance"' \
  --limit=5
```

### **Secret Manager管理**

```bash
# Secretバージョン一覧
gcloud secrets versions list bitbank-api-key
gcloud secrets versions list bitbank-api-secret
gcloud secrets versions list discord-webhook-url

# Secret値確認（注意：本番環境のみ）
gcloud secrets versions access 3 --secret="bitbank-api-key"

# 新バージョン作成（Secret更新時）
echo -n "新しいAPI Key" | gcloud secrets versions add bitbank-api-key --data-file=-
# ⚠️ 重要: ci.yml（L319）の--set-secrets設定も新バージョンに更新必要
```

### **GitHub Actions確認**

```bash
# CI/CD実行履歴
gh run list --limit=10

# 最新実行の詳細
gh run view

# 失敗したワークフロー確認
gh run list --status=failure --limit=5
```

---

## 🛠️ トラブルシューティング

### **CI/CDデプロイ失敗時**

```bash
# 1. GitHub Actionsログ確認
gh run view --log-failed

# 2. Service Account確認
gcloud iam service-accounts describe github-deployer@my-crypto-bot-project.iam.gserviceaccount.com

# 3. Workload Identity Pool確認
gcloud iam workload-identity-pools list --location=global

# 4. Cloud Buildログ確認
gcloud builds list --limit=5 --format="table(id,createTime.date(),status,logUrl)"
```

### **Secret Manager権限エラー**

```bash
# デフォルトCompute Engine SAに権限付与
SERVICE_ACCOUNT="11445303925-compute@developer.gserviceaccount.com"

for SECRET in bitbank-api-key bitbank-api-secret discord-webhook-url; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"
done
```

### **Cloud Runサービスエラー**

```bash
# サービス詳細確認
gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format=yaml

# 直近のエラーログ
gcloud logging read \
  "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit=20 \
  --format="table(timestamp,severity,textPayload)"

# リビジョン一覧（トラフィック配分確認）
gcloud run revisions list \
  --service=crypto-bot-service-prod \
  --region=asia-northeast1
```

### **IAM権限確認**

```bash
# github-deployer権限確認（CI/CD用SA）
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members~github-deployer@my-crypto-bot-project.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

# デフォルトCompute Engine SA権限確認（Cloud Run実行用）
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --filter="bindings.members~11445303925-compute@developer.gserviceaccount.com" \
  --format="table(bindings.role)"

# 全Service Account一覧
gcloud iam service-accounts list \
  --format="table(email,displayName)"
```

---

## ⚠️ 重要な注意事項

### **GCPリソース制約**
- **リージョン**: `asia-northeast1`（東京）固定
- **Cloud Run**: 1Gi メモリ、1 CPU制限
- **コスト管理**: 月額700-900円の個人開発予算内
- **Artifact Registry**: 定期的なクリーンアップ推奨

### **セキュリティ要件**
- **Secret Manager**: 具体的バージョン使用（`:latest`禁止）
- **Workload Identity**: GitHub Actions認証のみ許可
- **最小権限原則**: 必要最小限のIAM権限付与

### **デプロイ制約**
- **mainブランチ**: 自動デプロイ対象
- **テスト要件**: 1,117テスト100%成功必須
- **Python**: 3.13統一

---

## 🔗 関連ファイル・依存関係

### **CI/CD関連**
- `.github/workflows/ci.yml`: GitHub Actions CI/CDワークフロー
- `Dockerfile`: Python 3.13・Cloud Run対応
- `requirements.txt`: Python依存関係

### **設定ファイル**
- `config/core/unified.yaml`: 統一設定ファイル
- `config/core/thresholds.yaml`: 動的閾値設定

### **GCPサービス**
- **Cloud Run**: `crypto-bot-service-prod`
- **Artifact Registry**: `crypto-bot-repo`
- **Secret Manager**: 3シークレット管理
- **Cloud Logging**: ログ管理（JST対応）
- **Cloud Monitoring**: メトリクス監視（Discord統合）

---

## 📊 Phase 52.4完了時点のシステム状態

### インフラ構成
- **Cloud Run**: asia-northeast1（東京）
- **実行モード**: MODE=live（5分間隔）
- **月額コスト**: 700-900円（Phase 48: 35%削減達成）

### デプロイ実績
- **GitHub Actions**: 自動CI/CD統合
- **Secret Manager**: 具体的バージョン管理（:3, :5）
- **Workload Identity**: GitHub認証完了

### システム構成
- **ML統合**: アンサンブルモデル・レジーム別最適化
- **設定管理**: feature_order.json・strategies.yaml・thresholds.yaml
- **品質保証**: 全テスト自動実行・CI/CD品質ゲート

---

**最終更新**: Phase 52.4完了（2025年11月15日）
