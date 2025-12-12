# GCP運用ガイド

**最終更新**: 2025年12月11日

## このドキュメントの役割

| 項目 | 内容 |
|------|------|
| **目的** | GCP関連の運用作業をまとめたガイド |
| **対象読者** | GCP運用者・開発者 |
| **記載内容** | IAM権限管理、リソースクリーンアップ、コスト最適化 |
| **使用頻度** | 月1-2回（定期クリーンアップ）、権限問題発生時 |

---

## 目次

1. [IAM権限管理](#1-iam権限管理)
2. [リソース管理・クリーンアップ](#2-リソース管理クリーンアップ)

---

# 1. IAM権限管理

## 1.1 サービスアカウント権限一覧

### 本番システム実行用
**`crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com`**

| 権限 | 用途 |
|------|------|
| `roles/secretmanager.secretAccessor` | API Key・Webhook URL取得 |
| `roles/logging.logWriter` | Cloud Run実行ログ出力 |

**使用場所**: Cloud Run本番環境

---

### CI/CD デプロイ用
**`github-deployer@my-crypto-bot-project.iam.gserviceaccount.com`**

| 権限 | 用途 |
|------|------|
| `roles/artifactregistry.writer` | コンテナイメージpush |
| `roles/iam.serviceAccountUser` | crypto-bot-runner実行権限 |
| `roles/run.developer` | Cloud Runサービス更新 |
| `roles/viewer` | デプロイ状況確認 |

**使用場所**: GitHub Actions CI/CD

---

### 通知用
**`webhook-notifier@my-crypto-bot-project.iam.gserviceaccount.com`**

| 権限 | 用途 |
|------|------|
| `roles/pubsub.publisher` | 通知メッセージ送信 |
| `roles/secretmanager.secretAccessor` | Discord Webhook URL取得 |

**使用場所**: Discord通知システム

---

## 1.2 権限確認コマンド

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

## 1.3 権限追加ルール

### 追加前の確認事項
1. **必要性検証**: 本当に必要か？より限定的な権限で代替できないか？
2. **最小権限**: `admin`ではなく`writer`や`accessor`を使用
3. **期限設定**: 一時的な権限は期限付きで付与

### 追加コマンド例
```bash
gcloud projects add-iam-policy-binding my-crypto-bot-project \
  --member="serviceAccount:crypto-bot-runner@my-crypto-bot-project.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 追加後の必須作業
1. このファイルに権限を記録
2. 実際の設定と照合確認

---

## 1.4 禁止権限

以下の権限は**絶対に付与しない**:

| 権限 | 理由 |
|------|------|
| `roles/owner` | 全権限（セキュリティリスク極大） |
| `roles/editor` | 編集権限（SAには過剰） |
| `roles/iam.serviceAccountAdmin` | SA管理権限（セキュリティリスク） |
| `roles/resourcemanager.projectIamAdmin` | IAM管理権限（セキュリティリスク） |
| `roles/secretmanager.admin` | Secret管理権限（読み取りのみで十分） |

---

## 1.5 権限マトリックス

| サービスアカウント | Secret Manager | Logging | Cloud Run | Artifact Registry | Pub/Sub | IAM | Viewer |
|-------------------|----------------|---------|-----------|-------------------|---------|-----|--------|
| crypto-bot-runner | accessor | writer | - | - | - | - | - |
| github-deployer | - | - | developer | writer | - | user | viewer |
| webhook-notifier | accessor | - | - | - | publisher | - | - |

---

# 2. リソース管理・クリーンアップ

## 2.1 基本方針

| 項目 | 内容 |
|------|------|
| **実行頻度** | 月1〜2回の定期実行 |
| **安全第一** | 本番稼働中サービスへの影響回避を最優先 |
| **段階的削除** | 安全→完全→デプロイ前の順で用途別実行 |
| **自動化対応** | `CLEANUP_AUTO_MODE=true`で非インタラクティブ実行可能 |

---

## 2.2 事前確認

### 本番サービス稼働確認
```bash
# Cloud Runサービス稼働状況確認
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod \
  --region=asia-northeast1 \
  --format="value(status.conditions[0].status,status.url)"

# 最新リビジョン確認
TZ='Asia/Tokyo' gcloud run revisions list \
  --service=crypto-bot-service-prod \
  --region=asia-northeast1 --limit=3
```

### リソース使用量確認
```bash
# Artifact Registry使用量
echo "=== Artifact Registry ==="
gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
  --include-tags --format="table(version,tags,createTime.date())" --limit=10

# Cloud Run リビジョン数
echo "=== Cloud Run Revisions ==="
gcloud run revisions list \
  --service=crypto-bot-service-prod \
  --region=asia-northeast1 --limit=10

# Cloud Build 履歴
echo "=== Cloud Build ==="
gcloud builds list --limit=10 --format="table(id,createTime.date(),status)"
```

### 事前確認チェックリスト
- [ ] crypto-bot-service-prodが正常稼働中
- [ ] 直近1時間でERRORログがない
- [ ] 現在のリソース使用量を把握済み

---

## 2.3 安全クリーンアップ（推奨・最新7個保持）

```bash
echo "=== Artifact Registry安全クリーンアップ（最新7個保持） ==="

# 現在のイメージ総数確認
TOTAL_IMAGES=$(gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
  --format="value(version)" 2>/dev/null | wc -l)
echo "現在のイメージ総数: $TOTAL_IMAGES 個"

if [ "$TOTAL_IMAGES" -le 7 ]; then
    echo "イメージ数が7個以下のため削除不要"
    exit 0
fi

echo "削除対象: 最新7個以外の $((TOTAL_IMAGES - 7)) 個"

# 削除実行
gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
  --sort-by=CREATE_TIME --format="value(version)" --limit=100 2>/dev/null | \
tail -n +8 | \
while read -r IMAGE_VERSION; do
    if [ -n "$IMAGE_VERSION" ]; then
        echo "削除中: crypto-bot:$IMAGE_VERSION"
        gcloud artifacts docker images delete \
          "asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION" \
          --delete-tags --quiet 2>/dev/null || \
        echo "スキップ（既削除済み）: $IMAGE_VERSION"
    fi
done

echo "安全クリーンアップ完了"
```

---

## 2.4 完全クリーンアップ（全削除・デバッグ用）

```bash
echo "=== 完全クリーンアップ（全削除） ==="
echo "【警告】全てのイメージを削除します"

# 全イメージ削除
gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
  --format="value(version)" 2>/dev/null | \
while read -r IMAGE_VERSION; do
    if [ -n "$IMAGE_VERSION" ]; then
        echo "削除中: crypto-bot:$IMAGE_VERSION"
        gcloud artifacts docker images delete \
          "asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION" \
          --delete-tags --quiet 2>/dev/null || \
        echo "スキップ: $IMAGE_VERSION"
    fi
done

echo "完全クリーンアップ完了"
```

---

## 2.5 デプロイ前完全クリーンアップ

```bash
echo "=== デプロイ前完全クリーンアップ ==="

# ステップ1: Cloud Runサービス削除
echo "Cloud Runサービス削除中..."
if gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 >/dev/null 2>&1; then
    gcloud run services delete crypto-bot-service-prod --region=asia-northeast1 --quiet
    echo "Cloud Runサービス削除完了"
else
    echo "Cloud Runサービスが見つかりません"
fi

# ステップ2: Artifact Registry全イメージ削除
echo "Artifact Registry全イメージ削除..."
gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
  --format="value(version)" 2>/dev/null | while read -r IMAGE_VERSION; do
    if [ -n "$IMAGE_VERSION" ]; then
        gcloud artifacts docker images delete \
          "asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION" \
          --delete-tags --quiet 2>/dev/null
    fi
done

# ステップ3: Cloud Build履歴削除
echo "Cloud Build履歴削除..."
gcloud builds list --format="value(id)" --limit=100 2>/dev/null | while read -r BUILD_ID; do
    if [ -n "$BUILD_ID" ]; then
        gcloud builds delete "$BUILD_ID" --quiet 2>/dev/null
    fi
done

echo "デプロイ前完全クリーンアップ完了"
```

---

## 2.6 タグ付きリソース削除

### Artifact Registry タグ付きイメージ削除
```bash
# --delete-tags オプションで強制削除
gcloud artifacts docker images delete \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:IMAGE_VERSION \
  --delete-tags --quiet

# 特定タグのみ削除（イメージは保持）
gcloud artifacts docker tags delete \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:latest \
  --quiet
```

### Cloud Run トラフィック受信中リビジョン削除
```bash
# 1. トラフィックを最新リビジョンに移行
gcloud run services update-traffic crypto-bot-service-prod \
  --to-latest=100 --region=asia-northeast1

# 2. 古いリビジョン削除
gcloud run revisions delete OLD_REVISION_NAME \
  --region=asia-northeast1 --quiet
```

---

## 2.7 エラー対策

| エラーメッセージ | 原因 | 対策 |
|---|---|---|
| `Image is referenced by tags` | タグが残っている | `--delete-tags`で削除 |
| `Revision is receiving traffic` | トラフィック受信中 | トラフィック移行後削除 |
| `NOT_FOUND` | 既に削除済み | 無視（正常） |
| `PERMISSION_DENIED` | 権限不足 | [1.2 権限確認](#12-権限確認コマンド)参照 |

---

## 関連リンク

- 自動クリーンアップCI: `.github/workflows/cleanup.yml`
