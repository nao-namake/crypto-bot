# GCP IAM権限管理ガイド

**更新日**: 2025年9月29日
**バージョン**: Phase 29完了版
**適正化実施**: 2025年9月29日完了（過剰権限最終解決済み）

## 📋 権限管理概要

### 🎯 **最終適正化結果**
- **GitHub Actions権限**: 14個 → 4個（71%削減）
- **過剰権限完全解決**: admin権限 → 必要最小限権限に変更
- **Editor権限保持者**: 3個 → 1個（67%削除）
- **ユーザー権限**: secretmanager.admin削除済み
- **セキュリティレベル**: ✅ 企業級最小権限体制完全確立

## 🔐 サービスアカウント一覧

### **1. 本番システム実行用**
**`crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com`**
- **用途**: Cloud Run暗号資産取引Bot実行専用
- **権限**:
  - `roles/secretmanager.secretAccessor` - API Key取得
  - `roles/logging.logWriter` - ログ出力
- **セキュリティ**: ✅ 最小権限設計

### **2. CI/CD デプロイ用**
**`github-deployer@my-crypto-bot-project.iam.gserviceaccount.com`**
- **用途**: GitHub Actions自動デプロイ
- **権限**:
  - `roles/artifactregistry.writer` - コンテナイメージ書き込み（admin→writer適正化済み）
  - `roles/iam.serviceAccountUser` - サービスアカウント実行
  - `roles/run.developer` - Cloud Run開発者権限（admin→developer適正化済み）
  - `roles/viewer` - プロジェクト状況確認
- **セキュリティ**: ✅ 最小権限デプロイ専用（過剰権限解決済み）

### **3. 通知用**
**`webhook-notifier@my-crypto-bot-project.iam.gserviceaccount.com`**
- **用途**: Discord通知機能
- **権限**:
  - `roles/pubsub.publisher` - 通知メッセージ送信
  - `roles/secretmanager.secretAccessor` - Webhook URL取得
- **セキュリティ**: ✅ 通知専用限定権限

### **4. GCPシステム用（自動管理）**
**`11445303925@cloudservices.gserviceaccount.com`**
- **用途**: GCP内部サービス連携
- **権限**: `roles/editor`
- **管理**: Google自動管理（変更不可）

## 🚨 削除済み危険権限

### **GitHub Actions から削除**
```yaml
削除された過剰権限:
- roles/bigquery.admin          # BigQuery全権限（不要）
- roles/cloudfunctions.admin    # Cloud Functions全権限（不要）
- roles/iam.serviceAccountAdmin # IAM管理権限（危険）
- roles/iam.workloadIdentityPoolAdmin # WIF管理権限（危険）
- roles/logging.admin           # ログ管理権限（過剰）
- roles/monitoring.admin        # 監視管理権限（過剰）
- roles/pubsub.admin           # Pub/Sub管理権限（過剰）
- roles/resourcemanager.projectIamAdmin # プロジェクトIAM権限（危険）
- roles/secretmanager.admin     # Secret管理権限（危険）
- roles/storage.admin          # Storage管理権限（不要）

適正化された権限（admin→最小権限）:
- roles/artifactregistry.admin → roles/artifactregistry.writer
- roles/run.admin → roles/run.developer
```

### **ユーザーアカウントから削除**
```yaml
削除された過剰権限:
- roles/secretmanager.admin     # Secret管理権限（ユーザーに不要）
```

### **Editor権限から削除**
```yaml
削除されたEditor権限:
- 11445303925-compute@developer.gserviceaccount.com  # Compute Engine default
- my-crypto-bot-project@appspot.gserviceaccount.com  # App Engine default
```

## 🎯 権限設計原則

### **1. 最小権限の原則**
- 各サービスアカウントは必要最小限の権限のみ
- 管理者権限の完全排除
- 用途別の権限分離

### **2. 用途別分離**
- **実行用**: Secret読み取り + ログ出力のみ
- **デプロイ用**: Cloud Run + Container Registry のみ
- **通知用**: Pub/Sub + Webhook Secret のみ

### **3. セキュリティ監査**
- 定期的な権限レビュー（月1回推奨）
- 不要権限の即座削除
- 新規権限追加時の必要性検証

## 🔧 権限管理コマンド

### **権限確認**
```bash
# 現在のIAMポリシー確認
gcloud projects get-iam-policy my-crypto-bot-project

# 特定SAの権限確認
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com"
```

### **権限追加（緊急時のみ）**
```bash
# Secret Manager読み取り権限追加例
gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### **権限削除**
```bash
# 不要権限削除例
gcloud projects remove-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:example@my-crypto-bot-project.iam.gserviceaccount.com" \
  --role="roles/editor"
```

## 📊 現在の権限マトリックス

| サービスアカウント | Secret Manager | Logging | Cloud Run | Container Registry | Pub/Sub |
|-------------------|----------------|---------|-----------|-------------------|---------|
| crypto-bot-runner | 読み取り ✅ | 書き込み ✅ | - | - | - |
| github-deployer | - | - | 管理 ✅ | 管理 ✅ | - |
| webhook-notifier | 読み取り ✅ | - | - | - | 送信 ✅ |

## ⚠️ セキュリティ注意事項

### **絶対に付与してはいけない権限**
- `roles/owner` - オーナー権限
- `roles/editor` - エディター権限（ユーザー以外）
- `roles/iam.serviceAccountAdmin` - SA管理権限
- `roles/resourcemanager.projectIamAdmin` - プロジェクトIAM権限

### **緊急時対応**
1. **権限問題発生時**:
   - 最小限の権限のみ一時的に付与
   - 問題解決後、即座に削除
   - 作業ログを必ず記録

2. **新機能追加時**:
   - 必要な権限を事前に設計
   - 最小権限での実装
   - テスト環境での検証

## 🔄 定期メンテナンス

### **月次チェック項目**
- [ ] 不要なサービスアカウント削除
- [ ] 過剰権限の有無確認
- [ ] 新規権限の必要性検証
- [ ] セキュリティログ確認

### **権限レビュー手順**
1. 現在のIAMポリシー取得
2. 各権限の利用状況確認
3. 不要権限の特定と削除
4. 変更内容の文書化

---

**この権限体系により、セキュリティと機能性のバランスを保ちながら、暗号資産取引Botの安全な運用を実現しています。**

**🔐 企業級セキュリティ基準達成**
