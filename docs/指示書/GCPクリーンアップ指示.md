# 🧹 GCPリソース定期クリーンアップ指示書

## 📋 基本方針
- **実行頻度**: 月1〜2回の定期実行（コスト最適化）
- **安全第一**: 本番稼働中サービスへの影響回避を最優先
- **段階的削除**: 安全→中程度→積極的の順で慎重に実行
- **タグ対応**: タグ付きリソースの特別削除手順を含む
- **確認必須**: 削除前後でリソース状況を必ず確認・記録

## ⚠️ 重要注意事項
- **本番影響確認**: crypto-bot-service-prodが正常稼働中であることを事前確認
- **タグ付きリソース**: `latest`, `main`, `prod`等のタグが付いたリソースは特別な削除手順が必要
- **段階的実行**: 一度にすべて実行せず、段階的に様子を見ながら実行

---

## 🔍 1. 事前確認・現在のリソース状況把握

### ✅ 現在の本番サービス稼働確認
```bash
# Cloud Runサービス稼働状況確認（JST表示）
TZ='Asia/Tokyo' gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="value(status.conditions[0].status,status.url)"

# 最新リビジョンが正常稼働中であることを確認
TZ='Asia/Tokyo' gcloud run revisions list --service=crypto-bot-service-prod --region=asia-northeast1 --limit=3

# 直近1時間のエラーログ確認（問題ないことを確認）
TZ='Asia/Tokyo' gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="crypto-bot-service-prod" AND severity>=ERROR AND timestamp>=date("%Y-%m-%d %H:%M:%S", "-1h")' --limit=10
```

### ✅ 現在のリソース使用量確認
```bash
# Artifact Registry使用量確認（タグ付きも表示）
echo "🐳 Artifact Registry 現在の使用状況:"
gcloud artifacts docker images list asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot --include-tags --format="table(version,tags,createTime.date(),sizeBytes)" --limit=20

# Cloud Run リビジョン数確認（トラフィック配分も表示）
echo ""
echo "☁️ Cloud Run リビジョン数とトラフィック配分:"
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 --format="table(spec.traffic[].revisionName,spec.traffic[].percent,spec.traffic[].tag)"

# Cloud Build ジョブ数確認
echo ""
echo "🏗️ Cloud Build 履歴数:"
gcloud builds list --limit=10 --format="table(id,createTime.date(),status,tags)"

# Cloud Storage バケット使用量確認
echo ""
echo "📦 Cloud Storage 使用量:"
gsutil ls -L gs://my-crypto-bot-project_cloudbuild | grep "Storage class\|Total size" || echo "⚠️ バケット確認失敗"
```

### 🎯 事前確認ポイント
- [ ] crypto-bot-service-prodが正常稼働中
- [ ] 直近1時間でERRORログがない（または想定内エラーのみ）
- [ ] タグ付きリソースの存在確認済み
- [ ] 現在のリソース使用量を記録・把握済み

---

## 🧹 2. 安全レベル クリーンアップ（本番影響なし）

### ✅ Artifact Registry 古いDockerイメージ削除（タグ対応）
```bash
echo "🐳 === Artifact Registry古いイメージクリーンアップ開始（タグ対応） ==="

# 現在のイメージ一覧取得（タグも表示）
IMAGES_WITH_TAGS=$(gcloud artifacts docker images list \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
  --include-tags --sort-by=~CREATE_TIME \
  --format="csv[no-heading](version,tags)" \
  --limit=50)

echo "📋 現在のイメージ総数: $(echo "$IMAGES_WITH_TAGS" | wc -l)"
echo "最新10個のイメージ（タグ付きも表示）:"
echo "$IMAGES_WITH_TAGS" | head -10

# 削除対象イメージを特定（最新7個以外、かつタグなし）
echo ""
echo "🔍 削除対象の決定（最新7個以外 かつ タグなしイメージ）:"

DELETE_COUNT=0
DELETE_CANDIDATES=""
TAGGED_IMAGES=""

while IFS=',' read -r version tags; do
    DELETE_COUNT=$((DELETE_COUNT + 1))
    if [ $DELETE_COUNT -le 7 ]; then
        echo "⏭️ 保持: $version (最新7個以内)"
        continue
    fi
    
    # タグの確認（空またはsha256のみなら削除対象）
    if [[ -z "$tags" || "$tags" == "" ]]; then
        echo "✅ 削除対象: $version (タグなし)"
        DELETE_CANDIDATES+=" $version"
    else
        echo "⚠️ タグ付きのため要確認: $version (タグ: $tags)"
        TAGGED_IMAGES+=" $version:$tags"
    fi
done <<< "$IMAGES_WITH_TAGS"

# タグなし画像の削除実行
if [ -n "$DELETE_CANDIDATES" ]; then
    echo ""
    echo "🗑️ タグなし削除対象イメージ:"
    echo "$DELETE_CANDIDATES"
    
    read -p "⚠️ タグなしの古いイメージを削除しますか？ (y/N): " confirm
    if [[ $confirm == [yY] ]]; then
        for IMAGE_VERSION in $DELETE_CANDIDATES; do
            echo "削除中: crypto-bot:$IMAGE_VERSION"
            gcloud artifacts docker images delete \
              asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION \
              --quiet || echo "⚠️ 削除失敗（既に削除済み）: $IMAGE_VERSION"
        done
        echo "✅ タグなし古いイメージ削除完了"
    else
        echo "❌ タグなしイメージ削除をキャンセル"
    fi
else
    echo "📋 削除対象のタグなしイメージなし"
fi

# タグ付きイメージの処理
if [ -n "$TAGGED_IMAGES" ]; then
    echo ""
    echo "🏷️ === タグ付きイメージの削除手順 ==="
    echo "以下のイメージにはタグが付いています："
    echo "$TAGGED_IMAGES"
    echo ""
    echo "💡 タグ付きイメージの削除方法："
    echo "1. タグを削除してからイメージを削除"
    echo "2. または --delete-tags オプションを使用"
    echo ""
    
    read -p "⚠️ タグ付きイメージも削除しますか？（危険度高）(y/N): " dangerous_confirm
    if [[ $dangerous_confirm == [yY] ]]; then
        for TAGGED_IMAGE in $TAGGED_IMAGES; do
            IMAGE_VERSION=$(echo "$TAGGED_IMAGE" | cut -d':' -f1)
            IMAGE_TAGS=$(echo "$TAGGED_IMAGE" | cut -d':' -f2-)
            
            echo "🏷️ タグ付きイメージ削除: $IMAGE_VERSION (タグ: $IMAGE_TAGS)"
            
            # --delete-tagsオプションで強制削除
            gcloud artifacts docker images delete \
              asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION \
              --delete-tags --quiet || echo "⚠️ タグ付きイメージ削除失敗: $IMAGE_VERSION"
        done
        echo "✅ タグ付きイメージ削除完了"
    else
        echo "❌ タグ付きイメージ削除をキャンセル（推奨）"
        echo ""
        echo "💡 手動でタグ別削除する場合："
        for TAGGED_IMAGE in $TAGGED_IMAGES; do
            IMAGE_VERSION=$(echo "$TAGGED_IMAGE" | cut -d':' -f1)
            echo "gcloud artifacts docker images delete asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION --delete-tags"
        done
    fi
fi
```

### 💡 タグ付きリソース削除の詳細手順

#### 🏷️ Artifact Registry タグ付きイメージ削除
```bash
# 方法1: --delete-tags オプションで強制削除
gcloud artifacts docker images delete \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:IMAGE_VERSION \
  --delete-tags --quiet

# 方法2: タグを個別削除してからイメージ削除  
gcloud artifacts docker tags delete TAG_NAME --quiet
gcloud artifacts docker images delete IMAGE_URI --quiet

# 方法3: 特定タグのみ削除（イメージは保持）
gcloud artifacts docker tags delete \
  asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:latest \
  --quiet
```

#### 🚦 Cloud Run トラフィック受信中リビジョン削除
```bash
# 1. トラフィックを最新リビジョンに移行
gcloud run services update-traffic crypto-bot-service-prod \
  --to-latest=100 --region=asia-northeast1

# 2. 特定リビジョンにトラフィック配分
gcloud run services update-traffic crypto-bot-service-prod \
  --to-revisions=REVISION_NAME=100 --region=asia-northeast1

# 3. 古いリビジョン削除
gcloud run revisions delete OLD_REVISION_NAME \
  --region=asia-northeast1 --quiet
```

---

## 📊 削除失敗時の原因と対策

| エラーメッセージ | 原因 | 対策 |
|---|---|---|
| `FAILED_PRECONDITION: Image is referenced by tags` | タグが残っている | `--delete-tags`で削除 |
| `INVALID_ARGUMENT: Revision is receiving traffic` | トラフィック受信中 | トラフィック移行後削除 |
| `NOT_FOUND` | 既に削除済み | 無視（正常） |
| `PERMISSION_DENIED` | 権限不足 | 認証・権限確認 |

---

## 🔗 関連リンク

- [自動クリーンアップCI](../../.github/workflows/cleanup.yml) - 月次自動クリーンアップ
- [CI後チェック作業](./CI後チェック作業.md) - デプロイ後確認手順
- [開発計画ToDo](../開発計画/ToDo.md) - 緊急対応事項

---

**🧹 定期的なGCPクリーンアップで、タグ付きリソース含めた完全なコスト最適化を実現** 🚀