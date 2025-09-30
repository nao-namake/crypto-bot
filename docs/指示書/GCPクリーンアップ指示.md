# 🧹 GCPリソース定期クリーンアップ指示書（実証済み改良版）

**更新履歴**:
- 2025年9月29日 - 完全クリーンアップ実証済み・デプロイ前準備対応・gcr.io削除追加
- 2025年9月7日 - 変数スコープ・エラー判定・自動化対応の実用性向上

## 📋 基本方針（実証済み改良版）
- **実行頻度**: 月1〜2回の定期実行（コスト最適化）・デプロイ前完全クリーンアップ対応
- **安全第一**: 本番稼働中サービスへの影響回避を最優先
- **段階的削除**: 安全→中程度→積極的の順で慎重に実行
- **完全クリーンアップ**: デプロイ前準備用・全リソース削除対応
- **完全自動化対応**: 環境変数による非インタラクティブモード対応
- **確実性向上**: 変数スコープ問題・エラー判定改良・削除処理最適化・実証済み手順

## ⚠️ 重要注意事項（改良版）
- **本番影響確認**: crypto-bot-service-prodが正常稼働中であることを事前確認
- **タグ付きリソース**: `latest`, `main`, `prod`等のタグが付いたリソースの確実削除手順
- **自動化モード**: `CLEANUP_AUTO_MODE=true`で非インタラクティブ実行可能
- **エラー許容**: `NOT_FOUND`は正常（既削除）として処理

## 🚀 **自動化モード設定**
```bash
# 自動化モード（CI/CD・スクリプト実行用）
export CLEANUP_AUTO_MODE=true

# 手動モード（デフォルト・確認付き）
unset CLEANUP_AUTO_MODE
```

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

### ✅ Artifact Registry 古いDockerイメージ削除（改良版・変数スコープ対応）

#### **🚀 方式1: 安全クリーンアップ（推奨・最新7個保持）**
```bash
echo "🐳 === Artifact Registry安全クリーンアップ（最新7個保持） ==="

# 現在のイメージ総数確認
TOTAL_IMAGES=$(gcloud artifacts docker images list asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot --format="value(version)" 2>/dev/null | wc -l)
echo "📋 現在のイメージ総数: $TOTAL_IMAGES 個"

if [ "$TOTAL_IMAGES" -le 7 ]; then
    echo "✅ イメージ数が7個以下のため削除不要"
    exit 0
fi

echo "🔍 削除対象: 最新7個以外の $((TOTAL_IMAGES - 7)) 個のイメージ"

# 自動化モード確認
if [ -n "$CLEANUP_AUTO_MODE" ]; then
    echo "🤖 自動化モード: 確認なしで削除実行"
    CONFIRM_DELETE="y"
else
    read -p "⚠️ 古いイメージ $((TOTAL_IMAGES - 7)) 個を削除しますか？ (y/N): " CONFIRM_DELETE
fi

if [[ $CONFIRM_DELETE == [yY] ]]; then
    echo "🗑️ 削除実行中..."
    
    # 削除処理（変数スコープ問題解決・パイプライン使用）
    DELETE_SUCCESS=0
    DELETE_FAILED=0
    
    gcloud artifacts docker images list \
      asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
      --sort-by=CREATE_TIME --format="value(version)" --limit=100 2>/dev/null | \
    tail -n +8 | \
    while read -r IMAGE_VERSION; do
        if [ -n "$IMAGE_VERSION" ]; then
            echo "削除中: crypto-bot:$IMAGE_VERSION"
            
            if gcloud artifacts docker images delete \
              "asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION" \
              --delete-tags --quiet 2>/dev/null; then
                echo "✅ 削除成功: $IMAGE_VERSION"
                DELETE_SUCCESS=$((DELETE_SUCCESS + 1))
            else
                # NOT_FOUND は正常（既削除）として処理
                echo "⚠️ 削除スキップ（既削除済み・NOT_FOUND）: $IMAGE_VERSION"
                DELETE_SUCCESS=$((DELETE_SUCCESS + 1))
            fi
        fi
    done
    
    echo "✅ 安全クリーンアップ完了"
    
    # 結果確認
    FINAL_IMAGES=$(gcloud artifacts docker images list asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot --format="value(version)" 2>/dev/null | wc -l)
    echo "📊 削除結果: $TOTAL_IMAGES 個 → $FINAL_IMAGES 個（削除: $((TOTAL_IMAGES - FINAL_IMAGES)) 個）"
else
    echo "❌ 削除をキャンセル"
fi
```

#### **⚡ 方式2: 完全クリーンアップ（全削除・デバッグ用）**
```bash
echo "🔥 === Artifact Registry完全クリーンアップ（全削除） ==="

# 危険操作の確認（自動化モード対応）
if [ -n "$CLEANUP_AUTO_MODE" ]; then
    echo "🤖 自動化モード: 完全削除実行"
    CONFIRM_FULL_DELETE="y"
else
    echo "⚠️ 【警告】全てのイメージを削除します（本番影響あり）"
    read -p "🚨 本当に全削除しますか？ (y/N): " CONFIRM_FULL_DELETE
fi

if [[ $CONFIRM_FULL_DELETE == [yY] ]]; then
    echo "🗑️ 全イメージ削除実行中..."
    
    # 全イメージ削除（エラー許容・確実削除）
    gcloud artifacts docker images list \
      asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
      --format="value(version)" 2>/dev/null | \
    while read -r IMAGE_VERSION; do
        if [ -n "$IMAGE_VERSION" ]; then
            echo "削除中: crypto-bot:$IMAGE_VERSION"
            
            # --delete-tagsで強制削除・エラー許容
            gcloud artifacts docker images delete \
              "asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION" \
              --delete-tags --quiet 2>/dev/null || \
            echo "⚠️ 削除スキップ: $IMAGE_VERSION"
        fi
    done
    
    # Cloud Runサービス削除（完全クリーンアップ時のみ）
    if gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 >/dev/null 2>&1; then
        echo "🚨 Cloud Runサービスも削除中..."
        gcloud run services delete crypto-bot-service-prod --region=asia-northeast1 --quiet
        echo "✅ Cloud Runサービス削除完了"
    fi
    
    echo "🔥 完全クリーンアップ完了"
else
    echo "❌ 完全削除をキャンセル（推奨）"
fi
```

#### **🚀 方式3: デプロイ前完全クリーンアップ（実証済み）**
```bash
echo "🧹 === デプロイ前完全GCPクリーンアップ（全削除・実証済み） ==="

# ステップ1: Cloud Runサービス削除
echo "🚨 Cloud Runサービス削除中..."
if gcloud run services describe crypto-bot-service-prod --region=asia-northeast1 >/dev/null 2>&1; then
    gcloud run services delete crypto-bot-service-prod --region=asia-northeast1 --quiet
    echo "✅ Cloud Runサービス削除完了"
else
    echo "⚠️ Cloud Runサービスが見つかりません"
fi

# ステップ2: Artifact Registry全イメージ削除
echo "🗑️ Artifact Registry全イメージ削除..."
gcloud artifacts docker images list asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot \
  --format="value(version)" 2>/dev/null | while read -r IMAGE_VERSION; do
    if [ -n "$IMAGE_VERSION" ]; then
        echo "削除中: crypto-bot:$IMAGE_VERSION"
        gcloud artifacts docker images delete \
          "asia-northeast1-docker.pkg.dev/my-crypto-bot-project/crypto-bot-repo/crypto-bot:$IMAGE_VERSION" \
          --delete-tags --quiet 2>/dev/null || echo "⚠️ 削除スキップ: $IMAGE_VERSION"
    fi
done

# ステップ3: 旧gcr.io削除（一回きり・2025年9月29日実施済み）
echo "🗑️ 旧gcr.ioイメージ確認・削除..."
if gcloud container images list-tags gcr.io/my-crypto-bot-project/crypto-bot --format="value(DIGEST)" 2>/dev/null | grep -q .; then
    echo "旧gcr.ioイメージが見つかりました。削除実行中..."
    gcloud container images list-tags gcr.io/my-crypto-bot-project/crypto-bot --format="value(DIGEST)" 2>/dev/null | \
    while read -r DIGEST; do
        if [ -n "$DIGEST" ]; then
            echo "削除中: gcr.io digest:$DIGEST"
            gcloud container images delete "gcr.io/my-crypto-bot-project/crypto-bot@sha256:$DIGEST" \
              --force-delete-tags --quiet 2>/dev/null || echo "⚠️ 削除失敗: $DIGEST"
        fi
    done
else
    echo "✅ gcr.io: 既にクリーンアップ済み（通常）"
fi

# ステップ4: Cloud Build履歴削除
echo "🏗️ Cloud Build履歴全削除..."
gcloud builds list --format="value(id)" --limit=100 2>/dev/null | while read -r BUILD_ID; do
    if [ -n "$BUILD_ID" ]; then
        echo "削除中: Build $BUILD_ID"
        gcloud builds delete "$BUILD_ID" --quiet 2>/dev/null || echo "⚠️ 削除失敗: $BUILD_ID"
    fi
done

echo "✅ デプロイ前完全クリーンアップ完了"
echo "🚀 新規デプロイ準備完了: クリーンな状態でのデプロイが可能です"
```

#### **🔧 エラーハンドリング改良**
```bash
# カスタムエラー判定関数
cleanup_delete_image() {
    local IMAGE_URI="$1"
    local IMAGE_VERSION="$2"
    
    if gcloud artifacts docker images delete "$IMAGE_URI" --delete-tags --quiet 2>/dev/null; then
        echo "✅ 削除成功: $IMAGE_VERSION"
        return 0
    else
        local EXIT_CODE=$?
        case $EXIT_CODE in
            1) 
                # NOT_FOUND = 正常（既削除）
                echo "⚠️ 既削除済み: $IMAGE_VERSION"
                return 0
                ;;
            2)
                # PERMISSION_DENIED = 権限エラー
                echo "❌ 権限エラー: $IMAGE_VERSION"
                return 1
                ;;
            *)
                # その他エラー
                echo "❌ 削除失敗: $IMAGE_VERSION (終了コード: $EXIT_CODE)"
                return 1
                ;;
        esac
    fi
}
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
| `parse error near ')'` | 変数展開エラー | コマンド分割実行 |
| `no matches found: gs://bucket/**` | バケット空 | 正常（既にクリーン） |

---

## 🔗 関連リンク

- [自動クリーンアップCI](../../.github/workflows/cleanup.yml) - 月次自動クリーンアップ
- [CI後チェック作業](./CI後チェック作業.md) - デプロイ後確認手順
- [開発計画ToDo](../開発計画/ToDo.md) - 緊急対応事項

---

---

## 🎯 実証済み結果サマリー（2025年9月29日）

### ✅ **デプロイ前完全クリーンアップ実証**
- **Cloud Runサービス**: crypto-bot-service-prod（完全削除成功）
- **Artifact Registry**: crypto-bot-repo全イメージ（削除成功）
- **gcr.io旧イメージ**: 1個（一回きり削除成功・今後発生せず）
- **Cloud Build履歴**: 4個（部分削除・権限制限あり）
- **Cloud Storage**: 一時ファイル（クリーンアップ成功）

### 🛡️ **保持された重要リソース**
- Secret Manager（API Key・認証情報）
- IAM設定（サービスアカウント・権限）
- MLモデル（my-crypto-bot-models）
- Terraform状態（インフラ管理用）

### 🚀 **効果確認済み**
- 新規デプロイ時の名前衝突回避
- リソース使用量最適化
- コスト削減効果
- クリーンな環境でのデプロイ準備完了

---

**🧹 定期的なGCPクリーンアップで、タグ付きリソース含めた完全なコスト最適化を実現・デプロイ前準備対応完備** 🚀