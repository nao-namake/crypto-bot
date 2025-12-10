# GCP IAM権限管理

**Phase 52.4**

## 📋 このファイルの目的

**使用場面**:
- 新規権限追加時の参照
- セキュリティ監査時の権限確認
- 権限トラブル発生時の調査

**ルール**:
- 実際のGCP設定と完全一致を維持
- 新規権限追加時は必ず記録
- 過去の削除履歴は記載しない（開発履歴ドキュメント参照）
- 最小権限の原則を厳守

---

## 🔐 サービスアカウント権限一覧

### 1. 本番システム実行用
**`crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com`**

| 権限 | 用途 |
|------|------|
| `roles/secretmanager.secretAccessor` | API Key・Webhook URL取得 |
| `roles/logging.logWriter` | Cloud Run実行ログ出力 |

**使用場所**: Cloud Run本番環境

---

### 2. CI/CD デプロイ用
**`github-deployer@my-crypto-bot-project.iam.gserviceaccount.com`**

| 権限 | 用途 |
|------|------|
| `roles/artifactregistry.writer` | コンテナイメージpush |
| `roles/iam.serviceAccountUser` | crypto-bot-runner実行権限 |
| `roles/run.developer` | Cloud Runサービス更新 |
| `roles/viewer` | デプロイ状況確認 |

**使用場所**: GitHub Actions CI/CD

---

### 3. 通知用
**`webhook-notifier@my-crypto-bot-project.iam.gserviceaccount.com`**

| 権限 | 用途 |
|------|------|
| `roles/pubsub.publisher` | 通知メッセージ送信 |
| `roles/secretmanager.secretAccessor` | Discord Webhook URL取得 |

**使用場所**: Discord通知システム

---

## 🔧 権限確認コマンド

### 全体確認
```bash
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --format="table(bindings.role,bindings.members)" | \
  grep -E "crypto-bot-runner|github-deployer|webhook-notifier"
```

### 特定SA確認
```bash
gcloud projects get-iam-policy my-crypto-bot-project \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com"
```

---

## 🚨 権限追加ルール

### 追加前の確認事項
1. **必要性検証**: 本当に必要か？より限定的な権限で代替できないか？
2. **最小権限**: `admin`ではなく`writer`や`accessor`を使用
3. **期限設定**: 一時的な権限は期限付きで付与

### 追加コマンド例
```bash
# Secret Manager読み取り権限追加
gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 追加後の必須作業
1. このファイルに権限を記録
2. 実際の設定と照合確認

---

## ⚠️ 禁止権限

以下の権限は**絶対に付与しない**:

| 権限 | 理由 |
|------|------|
| `roles/owner` | 全権限（セキュリティリスク極大） |
| `roles/editor` | 編集権限（SAには過剰） |
| `roles/iam.serviceAccountAdmin` | SA管理権限（セキュリティリスク） |
| `roles/resourcemanager.projectIamAdmin` | IAM管理権限（セキュリティリスク） |
| `roles/secretmanager.admin` | Secret管理権限（読み取りのみで十分） |

---

## 📊 権限マトリックス（実際の設定）

| サービスアカウント | Secret Manager | Logging | Cloud Run | Artifact Registry | Pub/Sub | IAM | Viewer |
|-------------------|----------------|---------|-----------|-------------------|---------|-----|--------|
| crypto-bot-runner | accessor ✅ | writer ✅ | - | - | - | - | - |
| github-deployer | - | - | developer ✅ | writer ✅ | - | user ✅ | ✅ |
| webhook-notifier | accessor ✅ | - | - | - | publisher ✅ | - | - |

**最終確認日**: 2025年11月15日
