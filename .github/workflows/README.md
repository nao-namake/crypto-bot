# .github/workflows/ - GitHub Actions CI/CDパイプライン

## 📋 概要

**GitHub Actions CI/CD Pipeline Configuration**  
crypto-botプロジェクトの自動化パイプラインを管理します。コード品質チェック、テスト実行、Dockerビルド、GCPへの自動デプロイを実現します。

**🆕 2025年8月12日更新**:
- **ci.yml**: タイムスタンプタグ追加（BUILD_TIME）でリビジョン管理を改善
- **デプロイ検証**: 本番デプロイ後の自動ヘルスチェック強化
- **日本時間対応**: ログ分析時のタイムゾーン考慮

## 🎯 ワークフロー構成

```
.github/workflows/
├── README.md         # このファイル
├── ci.yml           # メインCI/CDパイプライン
└── code-review.yml  # PRコードレビュー（PR専用）
```

## 📁 各ワークフローの詳細

### **ci.yml - メインCI/CDパイプライン**

**トリガー**:
- mainブランチへのpush
- Pull Request
- 手動実行（workflow_dispatch）

**実行ジョブ**:

#### **1. test - 単体テスト**
```yaml
- Python 3.11環境でテスト実行
- flake8/isort/black品質チェック
- pytest + カバレッジ測定
- 事前計算キャッシュ生成
- 本番環境依存関係検証
```

#### **2. docker-build - Dockerビルド＆プッシュ**
```yaml
- AMD64プラットフォーム専用ビルド
- Artifact Registryへのプッシュ
- タグ付け:
  - latest
  - コミットSHA
  - タイムスタンプ（BUILD_TIME）🆕
- CI用モデル・キャッシュ準備
```

#### **3. terraform-deploy-dev - 開発環境デプロイ**
```yaml
- developブランチとPR時に実行
- paperモードで動作
- asia-northeast1リージョン
```

#### **4. terraform-deploy-prod - 本番環境デプロイ**
```yaml
- mainブランチpush時のみ実行
- liveモードで動作
- デプロイ後の自動検証:
  - ヘルスチェック
  - エラーログ確認
  - メインループ起動確認
```

### **code-review.yml - PRコードレビュー**

**トリガー**:
- Pull Request時のみ

**機能**:
- PR専用のコードレビュー
- エラーは正常動作（PRのみ実行のため）

## 🚀 使用方法

### **通常のデプロイフロー**
```bash
# 1. ローカルでコード変更
# 2. 品質チェック実行
bash scripts/ci_tools/checks.sh

# 3. mainブランチへプッシュ
git add -A
git commit -m "feat: 機能追加"
git push origin main

# 4. GitHub Actionsが自動実行
#    - テスト → Dockerビルド → 本番デプロイ
```

### **手動実行**
GitHubのActionsタブから手動トリガー可能：
1. Actionsタブを開く
2. "CI"ワークフローを選択
3. "Run workflow"ボタンをクリック

## ⚙️ 重要な設定

### **必要なGitHub Secrets**
```
GCP_PROJECT_ID         # GCPプロジェクトID
GCP_PROJECT_NUMBER     # GCPプロジェクト番号
GCP_WIF_PROVIDER      # Workload Identity Provider
GCP_DEPLOYER_SA       # デプロイ用サービスアカウント
BITBANK_API_KEY       # Bitbank APIキー（本番用）
BITBANK_API_SECRET    # Bitbank APIシークレット（本番用）
ALERT_EMAIL           # アラート通知先
CODECOV_TOKEN         # Codecovトークン（オプション）
```

### **タイムスタンプタグ（2025年8月12日追加）**
```yaml
- name: Set build timestamp
  id: timestamp
  run: echo "BUILD_TIME=$(date +%Y%m%d-%H%M%S)" >> $GITHUB_OUTPUT

tags: |
  .../crypto-bot:latest
  .../crypto-bot:${{ github.sha }}
  .../crypto-bot:${{ steps.timestamp.outputs.BUILD_TIME }}
```

これによりリビジョン管理が容易になり、最新CIパス版の特定が簡単になります。

## 📊 デプロイ後の検証

### **本番デプロイ後の自動チェック**
```bash
# 1. ヘルスチェック
curl https://crypto-bot-service-prod-*.run.app/health

# 2. エラーログ確認
gcloud logging read "severity>=ERROR" --limit=10

# 3. メインループ起動確認
gcloud logging read "textPayload:LOOP-ITER" --limit=1
```

### **日本時間でのログ確認**
デプロイ後30分経過時の確認：
```bash
# utilities/gcp_log_viewer.pyを使用
python scripts/utilities/gcp_log_viewer.py --hours 0.5

# 最新リビジョンのみを自動選択
# UTC→JST変換で時刻の混乱を防止
```

## ⚠️ トラブルシューティング

### **CI失敗時の対処**

**1. テストジョブ失敗**
```bash
# ローカルで同じチェックを実行
bash scripts/ci_tools/checks.sh
```

**2. Dockerビルド失敗**
```bash
# ローカルでビルドテスト
docker build -f docker/Dockerfile -t test .
```

**3. デプロイ失敗**
```bash
# Terraformの状態確認
cd infra/envs/prod
terraform plan
```

### **code-review.ymlのエラー**
- PR以外で実行されるとエラーになるのは正常動作
- mainブランチではci.ymlのみが実行される

## 📝 今後の改善予定

1. **並列実行の最適化**
   - テストとDockerビルドの並列化
   - 実行時間の短縮

2. **キャッシュ戦略の改善**
   - Docker layer cache
   - pip cache最適化

3. **通知機能の強化**
   - Slack通知統合
   - デプロイ成功/失敗の通知

4. **ロールバック自動化**
   - 失敗時の自動ロールバック
   - Blue/Greenデプロイメント

---

**最終更新**: 2025年8月12日  
**CI/CD実行時間**: 約5分（Phase 19+最適化済み）