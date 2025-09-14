# config/infrastructure/ - インフラストラクチャ設定（v22.0.0 Phase 22設定最適化完了版）

**最終更新**: 2025年9月14日 - Phase 22設定最適化完了・26キー重複問題解決・真のシステム性能発揮

## 🚀 Phase 22 最適化成果（2025年9月14日完了）

**🎯 目標**: インフラ設定ファイル最新化・設定最適化成果反映

**✅ 実現成果**:
- **設定統合**: 26キー重複問題完全解決・デフォルト値強制問題解決
- **ファイル最適化**: unified.yaml 72.7%削減・thresholds.yaml 60.9%削減
- **テスト品質**: 625テスト100%成功・58.64%カバレッジ達成
- **システム性能**: 真のシステム性能発揮・最適化設定活用
- **インフラ同期**: cloudbuild.yaml・gcp_config.yaml・Dockerfile全て最新化

## 🚨 **重要: 実環境整合性修正について**

**2025年9月7日に発見・修正された重要な設定不整合問題**:
- **問題**: 存在しないサービスアカウント指定によりCI/CDが2ヶ月間停止
- **修正**: 実際のGCP環境に合わせた設定ファイル最適化
- **結果**: CI/CDパイプライン復旧・自動デプロイ機能復活

## 🎯 役割・責任

Google Cloud Platform（GCP）を基盤としたインフラストラクチャ設定を管理します。CI/CDパイプライン、クラウドリソース設定、セキュリティ設定を定義し、**実際のGCP環境との完全な整合性を保証**した自動デプロイメント、監視、コスト管理などの運用基盤を提供します。

## 📂 ファイル構成

```
infrastructure/
├── README.md               # このファイル（v16.2.0対応・実環境情報）
├── gcp_config.yaml        # GCP統合設定（v16.2.0・実環境整合版）
└── cloudbuild.yaml        # Cloud Build実行定義（修正版・Python 3.12対応）
```

## 📋 各ファイルの役割（v16.2.0対応）

### **gcp_config.yaml（v16.2.0・実環境整合版）**
GCPプロジェクト全体の設定を**実際の環境構成に合わせて**定義します。

**🔧 重要な修正内容**:
- **サービスアカウント**: `github-actions-sa` → `github-deployer`（実在SA）
- **実権限反映**: admin権限多数の実際の権限構成を正確記録
- **変数具体化**: テンプレート変数 → 実値（例: `asia-northeast1`）

**主要設定内容**:
- プロジェクト基本情報（ID: `my-crypto-bot-project`、リージョン: `asia-northeast1`）
- Cloud Runサービス設定（`crypto-bot-service-prod`）
- Secret Manager設定（3シークレット・IAM権限確認済み）
- **実際のWorkload Identity設定**: `github-pool`/`github-provider`
- 監視・ログ設定
- **実環境セキュリティポリシー**

### **cloudbuild.yaml（修正版・Python 3.12対応）**
Cloud Buildでのビルド・デプロイ処理を定義します。

**🔧 重要な修正内容**:
- **テスト実行コマンド**: `python scripts/testing/checks.sh` → `bash scripts/testing/checks.sh`
- **Python version**: 3.11 → 3.12（MLライブラリ互換性最適化・DockerfileおよびGitHub Actionsとの統一）
- **サービスアカウント**: 存在しない`crypto-bot-workload-identity@...`を削除

**主要機能**:
- **625テスト実行（完全品質保証・Phase 22対応）**
- Dockerイメージビルド（Python 3.13）
- Artifact Registryへのプッシュ
- **実際のデフォルトCompute Engine SA使用**でのCloud Runデプロイ
- 環境変数・シークレット設定（実証済み権限構成）

## 📝 使用方法・例（実環境対応）

### **自動デプロイ（GitHub Actions・復旧版）**
```bash
# コードをプッシュすると自動実行（2ヶ月停止から復旧）
git add .
git commit -m "インフラ設定更新"
git push origin main
# → GitHub Actionsが自動でCloud Build実行（復旧済み）
```

### **手動デプロイ確認（実際のサービス名）**
```bash
# サービス状況確認（実際のサービス名使用）
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# ビルド履歴確認（最新のCI/CD実行状況）
gcloud builds list --limit=5

# ログ確認（実際のサービス）
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=crypto-bot-service-prod" --limit=10
```

### **実環境Secret Manager管理**
```bash
# シークレット一覧確認（実際の3シークレット）
gcloud secrets list

# IAM権限確認（重要: 実際のサービスアカウント権限）
SERVICE_ACCOUNT="11445303925-compute@developer.gserviceaccount.com"
for SECRET in bitbank-api-key bitbank-api-secret discord-webhook-url; do
  gcloud secrets get-iam-policy $SECRET --format="value(bindings[].members)" | grep -q "$SERVICE_ACCOUNT" && echo "✅ $SECRET: 権限あり" || echo "❌ $SECRET: 権限なし"
done

# シークレット更新
gcloud secrets versions add bitbank-api-key --data-file=api_key.txt
```

### **実際のサービスアカウント確認**
```bash
# 実際に使用されているサービスアカウント一覧
gcloud iam service-accounts list --format="table(email,displayName)"

# github-deployerの権限確認（CI/CD用SA）
gcloud projects get-iam-policy my-crypto-bot-project --flatten="bindings[].members" --filter="bindings.members~github-deployer@my-crypto-bot-project.iam.gserviceaccount.com" --format="table(bindings.role)"

# デフォルトCompute Engine SA権限確認（Cloud Run実行用）
gcloud projects get-iam-policy my-crypto-bot-project --flatten="bindings[].members" --filter="bindings.members~11445303925-compute@developer.gserviceaccount.com" --format="table(bindings.role)"
```

## ⚠️ 注意事項・制約（実環境基準）

### **実証済みGCPリソース制約**
- **リージョン**: `asia-northeast1`（東京）固定・確認済み
- **Cloud Run**: 1Gi メモリ、1 CPU制限・稼働実績あり
- **コスト管理**: 月額約2000円の個人開発予算内・実績ベース
- **Artifact Registry**: 4.7GB使用中・クリーンアップ対応済み

### **実環境セキュリティ要件**  
- **Secret Manager**: 3シークレット・IAM権限設定済み・確認済み
- **Workload Identity**: `github-pool`設定済み・GitHub Actions認証対応
- **最小権限**: デフォルトCompute Engine SAが適切な権限保有確認済み
- **実際の権限**: github-deployerにadmin権限多数付与・実運用対応

### **実証済みデプロイ制約**
- **mainブランチ**: 自動デプロイ対象・CI/CD復旧済み
- **テスト要件**: **625テスト100%成功必須**・品質保証確認済み・Phase 22対応
- **Cloud Build**: 10分タイムアウト・Python 3.13対応
- **復旧状況**: 2ヶ月停止状態から正常動作復旧・設定最適化完了

## 🔗 関連ファイル・依存関係（実環境整合版）

### **CI/CD関連（整合性確認済み・Phase 22対応）**
- `.github/workflows/ci.yml`: **github-deployer**使用・Python 3.13・整合済み
- `Dockerfile`: Python 3.13・Cloud Run対応・**Phase 22設定最適化対応**・動作確認済み
- `requirements.txt`: Python依存関係・**625テスト対応**
- `scripts/deployment/verify_gcp_setup.sh`: **github-deployer**対応・整合済み

### **設定ファイル連携（実環境対応）**
- `config/core/unified.yaml`: 統一設定ファイル（全環境対応）
- `src/core/config.py`: 設定管理システム・統合対応

### **実際のGCPサービス（確認済み）**
- **Cloud Run**: `crypto-bot-service-prod`・稼働確認済み
- **Artifact Registry**: `crypto-bot-repo`・4.7GB使用・クリーンアップ対応
- **Secret Manager**: 3シークレット・権限設定済み・認証確認済み
- **Cloud Logging**: ログ管理・JST対応・監視統合
- **Cloud Monitoring**: メトリクス監視・Discord統合

## 🛠️ トラブルシューティング（実環境経験ベース）

### **🚨 CI/CD失敗時の確認手順**
```bash
# 1. サービスアカウント存在確認
gcloud iam service-accounts describe github-deployer@my-crypto-bot-project.iam.gserviceaccount.com

# 2. Workload Identity Pool確認
gcloud iam workload-identity-pools list --location=global

# 3. 最新Cloud Buildログ確認
gcloud builds list --limit=3 --format="table(id,createTime.date(),status,logUrl)"

# 4. 権限エラー確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10
```

### **🔧 権限エラー解決**
```bash
# Secret Manager権限再設定（必要に応じて）
SERVICE_ACCOUNT="11445303925-compute@developer.gserviceaccount.com"
for SECRET in bitbank-api-key bitbank-api-secret discord-webhook-url; do
  gcloud secrets add-iam-policy-binding $SECRET --member="serviceAccount:$SERVICE_ACCOUNT" --role="roles/secretmanager.secretAccessor"
done
```

### **📊 デプロイ状況確認**
```bash
# Cloud Runサービス稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.conditions[0].status,status.url)"

# 最新リビジョン確認（JST表示）
TZ='Asia/Tokyo' gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=3 --format="table(metadata.name,metadata.creationTimestamp.date(tz='Asia/Tokyo'),status.conditions[0].status)"
```

## 📈 バージョン履歴・修正記録

### **v22.0.0（2025-09-14）- Phase 22設定最適化完了版** 🚀
- 🎯 **Phase 22完了**: 26キー重複問題完全解決・設定最適化完了
- 📁 **ファイル最適化**: unified.yaml 72.7%削減・thresholds.yaml 60.9%削減  
- 🧪 **テスト統一**: 620/654テスト → 625テスト・58.64%カバレッジ統一
- ⚡ **性能向上**: デフォルト値強制問題解決・真のシステム性能発揮
- 🔧 **インフラ統一**: cloudbuild.yaml・gcp_config.yaml・Dockerfile全て最新化
- 🏗️ **Python統一**: 3.12 → 3.13統一・15特徴量統一システム対応

### **v16.2.0（2025-09-07）- 実環境整合性修正版**
- 🚨 **CI/CD復旧**: 存在しないサービスアカウント問題解決
- 🔧 **設定統一**: github-actions-sa → github-deployer（実際のSA）
- ✅ **権限反映**: admin権限多数の実際の構成を設定に反映
- 📊 **整合性確保**: 全関連ファイル（ci.yml、verify_gcp_setup.sh等）との統一
- 🎯 **問題解決**: 2ヶ月間のCI/CDパイプライン停止状態解消

### **v16.1.0（2025-08-29）- Phase 16-B完了**
- Phase 16-B完了対応: 620テスト・50%+カバレッジ → **Phase 22で625テスト・58.64%カバレッジに進化**
- stage-10/50廃止: 2段階デプロイ（paper→live）に統合
- 設定大幅削減: 380行→180行（53%削減）
- bitbank信用取引専用設定
- 個人開発最適化: 1万円→50万円段階拡大

---

## 🎯 **重要事項まとめ**

### **✅ Phase 22完了事項**
- **設定最適化完了**: 26キー重複問題完全解決・デフォルト値強制問題解決
- **ファイル軽量化**: unified.yaml 72.7%削減・thresholds.yaml 60.9%削減
- **テスト統一**: 625テスト100%成功・58.64%カバレッジ達成
- **インフラ統一**: cloudbuild.yaml・gcp_config.yaml・Dockerfile全て最新化
- **システム性能**: 真のシステム性能発揮・最適化設定活用

### **✅ v16.2.0修正完了事項**
- CI/CDパイプライン復旧（2ヶ月停止 → 正常動作）
- 実環境との完全整合性確保
- 設定ファイル間の統一性確保
- Python 3.13統一・MLライブラリ互換性最適化・テストコマンド修正

### **🔍 実環境確認済み事項**
- Secret Manager IAM権限設定済み
- Workload Identity Pool稼働中
- デフォルトCompute Engine SA適切権限保有
- GitHub Actions認証設定済み

**Phase 22設定最適化により、AI自動取引botの最高性能発揮・安定稼働・自動デプロイ・24時間監視が実現されています。**