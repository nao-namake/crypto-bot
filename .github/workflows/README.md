# GitHub Actions Workflows

**現在のシステム状況**: Phase 13完了・CI/CD自動化・GCPリソース最適化・本番稼働中

## 📂 ワークフロー構成

```
workflows/
├── ci.yml           # メインCI/CDパイプライン（自動品質チェック・段階的デプロイ）
├── cleanup.yml      # GCPリソース自動クリーンアップ（コスト最適化）
├── monitoring.yml   # 本番稼働監視（手動実行・ヘルスチェック）
└── README.md        # このファイル
```

## 🚀 ci.yml - メインCI/CDパイプライン

**本番稼働中の統合CI/CDシステム**

### 実行条件
- **自動実行**: `main`ブランチへのプッシュ
- **品質チェック**: プルリクエスト作成時
- **手動実行**: GitHub Actions画面から

### 実行フロー

#### 1️⃣ **品質保証 (quality-check)**
```bash
# 306テスト・コード品質・MLモデル整合性の統合チェック
bash scripts/testing/checks.sh
python -m pytest tests/ -v --tb=short
flake8 src/ && black --check src/ && isort --check-only src/
```

#### 2️⃣ **GCP環境確認 (gcp-environment-check)**
```bash
# 必須リソース存在確認
gcloud artifacts repositories describe crypto-bot-repo
gcloud secrets describe bitbank-api-key
gcloud secrets describe bitbank-api-secret
```

#### 3️⃣ **ビルド・デプロイ (build-deploy)**
```bash
# Dockerイメージビルド
docker build -t asia-northeast1-docker.pkg.dev/.../crypto-bot .

# 段階的Cloud Runデプロイ
gcloud run deploy crypto-bot-service-prod \
  --image="${IMAGE_TAG}" \
  --region=asia-northeast1 \
  --memory=1Gi --cpu=1 \
  --min-instances=1 --max-instances=2
```

#### 4️⃣ **ヘルスチェック (verify-deployment)**
```bash
# 5回リトライでサービス稼働確認
curl -f "${SERVICE_URL}/health"
curl -f "${SERVICE_URL}/"
```

### 段階的デプロイ対応

| モード | サフィックス | リソース | インスタンス | 用途 |
|--------|--------------|----------|-------------|------|
| paper | (なし) | 1Gi/1CPU | 0-1 | テスト環境 |
| stage-10 | -stage10 | 1Gi/1CPU | 1-1 | 10%投入 |
| stage-50 | -stage50 | 1.5Gi/1CPU | 1-1 | 50%投入 |
| live | -prod | 1Gi/1CPU | 1-2 | 本番環境 |

## 🧹 cleanup.yml - GCPリソースクリーンアップ

**コスト最適化・混乱防止のための自動クリーンアップ**

### 実行条件
- **手動実行**: 推奨（Actions画面から）
- **月次自動**: 第1日曜日 JST 2:00 AM

### クリーンアップレベル

#### Safe（推奨）
- 古いDockerイメージ削除（最新5個保持）
- 不要なCloud Runリビジョン削除

#### Moderate  
- Safe + Cloud Build履歴削除（30日以上古い）
- Cloud Run古いリビジョン削除（最新3個以外）

#### Aggressive（要注意）
- Moderate + 追加的な大量削除

### 使用方法
```bash
# 手動実行（推奨）
gh workflow run cleanup.yml -f cleanup_level=safe

# または GitHub Actions画面から
# Actions → GCP Resource Cleanup → Run workflow
```

## 🔍 monitoring.yml - 本番稼働監視

**手動実行専用の包括的監視システム**

### 監視項目

#### システムヘルス
- Cloud Runサービス稼働状況
- API応答時間測定
- エラーログ分析（過去15分）

#### パフォーマンス監視
- 複数回測定による平均応答時間
- 成功率・エラー率分析
- 閾値超過アラート

#### 取引システム監視
- 取引関連ログ確認
- シグナル生成状況
- システム正常性確認

### 使用方法
```bash
# 完全監視実行
gh workflow run monitoring.yml

# またはGitHub Actions画面から手動実行
```

## 🛠️ 使用方法・実行例

### 自動CI/CD（推奨）
```bash
git add .
git commit -m "fix: サービス名統一・品質改善"
git push origin main  # 自動的にCI/CD実行
```

### 手動実行
```bash
# メインCI/CD
gh workflow run ci.yml

# 監視実行  
gh workflow run monitoring.yml

# クリーンアップ実行
gh workflow run cleanup.yml -f cleanup_level=safe
```

### 実行状況確認
```bash
# 最新実行状況
gh run list --limit 5

# 詳細ログ確認
gh run view --log
```

## 📊 設定・環境変数

### 共通設定
```yaml
env:
  PROJECT_ID: my-crypto-bot-project
  REGION: asia-northeast1  
  REPOSITORY: crypto-bot-repo
  SERVICE_NAME: crypto-bot-service
```

### GitHub Secrets（必須）
```
# GCP認証
WORKLOAD_IDENTITY_PROVIDER: projects/.../providers/github-provider
SERVICE_ACCOUNT: github-deployer@project.iam.gserviceaccount.com

# デプロイ制御
DEPLOY_MODE: live  # paper/stage-10/stage-50/live
```

## 🎯 品質保証・効果

### 自動化達成効果
- **手動作業削減**: 80%削減・エラー防止
- **品質保証**: 306テスト自動実行・品質ゲート
- **コスト最適化**: 不要リソース自動削除
- **安定稼働**: 段階的デプロイ・ヘルスチェック

### 実行時間・効率
- **品質チェック**: 2-3分（306テスト）
- **ビルド・デプロイ**: 3-5分
- **監視**: 1-2分
- **クリーンアップ**: 2-3分

## 🚨 トラブルシューティング

### CI失敗時
```bash
# ローカルで事前確認
bash scripts/testing/checks.sh
python scripts/management/dev_check.py validate

# 失敗内容に応じて
python -m pytest tests/unit/ -v --tb=short
flake8 src/ --count --statistics
```

### デプロイ失敗時
```bash
# サービス状況確認
gcloud run services list --region=asia-northeast1
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### 監視アラート時
```bash
# 即座確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud logging read "severity>=ERROR" --limit=20

# 必要に応じてロールバック検討
```

---

**Phase 13達成**: 統合CI/CD・品質保証自動化・GCPリソース最適化により、安定した本番稼働とコスト効率を実現。個人開発に最適化された実用的なワークフローシステムを確立。