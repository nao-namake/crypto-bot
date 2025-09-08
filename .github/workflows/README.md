# GitHub Actions Workflows

## 🎯 役割・責任

このディレクトリには、GitHub Actionsで実行される3つのワークフローファイルが含まれています。それぞれ異なる自動化タスクを担当し、システムの品質保証、機械学習モデルの管理、リソース最適化を実現します。

## 📂 ファイル構成

```
workflows/
├── ci.yml               # メインCI/CDパイプライン
├── model-training.yml   # ML モデル学習・デプロイメント
├── cleanup.yml          # GCPリソースクリーンアップ
└── README.md            # このファイル
```

## 🔧 ワークフローの役割・ルール

### **ci.yml - CI/CDパイプライン**

**役割**: メインのCI/CDパイプライン

**実行条件**:
- `main` ブランチへのプッシュ（自動デプロイ）
- プルリクエスト作成時（品質チェック）
- 手動実行

**実行フロー**:
1. **品質チェック**: テスト実行、コード品質確認、カバレッジ測定
2. **GCP環境確認**: 必要なリソース存在確認
3. **Dockerビルド**: イメージ構築とArtifact Registryプッシュ
4. **本番デプロイ**: Cloud Runサービスデプロイ
5. **ヘルスチェック**: デプロイ成功確認

### **model-training.yml - MLモデル学習・デプロイメント**

**役割**: MLモデルの学習とデプロイメント

**実行条件**:
- 毎週日曜日 18:00 JST（スケジュール実行）
- 手動実行（パラメータ設定可能）

**パラメータ**:
- `training_days`: 学習データ期間（90/180/365日）
- `dry_run`: テスト実行フラグ

**実行フロー**:
1. **環境セットアップ**: モデルディレクトリ作成、Git設定
2. **モデル学習**: 指定期間のデータで学習実行
3. **品質検証**: 学習済みモデルの検証
4. **バージョン管理**: 自動コミット・プッシュ

### **cleanup.yml - GCPリソースクリーンアップ**

**役割**: GCPリソースの自動削除とコスト最適化

**実行条件**:
- 手動実行（推奨）
- 毎月第1日曜日 JST 2:00 AM（スケジュール実行）

**パラメータ**:
- `cleanup_level`: クリーンアップレベル（safe/moderate/aggressive）

**クリーンアップレベル**:
- **Safe**: 古いDockerイメージ・Cloud Runリビジョンのみ削除
- **Moderate**: Safe + Cloud Build履歴・古いリビジョン削除
- **Aggressive**: より積極的な大量削除

## 📝 使用方法

### **基本的な実行方法**

```bash
# GitHub CLI使用
gh workflow run ci.yml                                    # CI/CDパイプライン
gh workflow run model-training.yml                       # MLモデル学習
gh workflow run cleanup.yml -f cleanup_level=safe        # リソースクリーンアップ

# パラメータ付き実行
gh workflow run model-training.yml -f training_days=365  # 365日学習
gh workflow run model-training.yml -f dry_run=true       # テスト実行
gh workflow run cleanup.yml -f cleanup_level=moderate    # 中程度クリーンアップ
```

### **実行状況確認**

```bash
# 実行履歴確認
gh run list --workflow=ci.yml --limit 5
gh run list --workflow=model-training.yml --limit 5

# 詳細ログ確認
gh run view [RUN_ID] --log
```

## ⚠️ 注意事項

### **実行制約**
- **同時実行制限**: mainブランチでは順次実行（競合回避）
- **実行時間制限**: 各ワークフロー最大45分でタイムアウト
- **リソース制限**: GitHub Actions無料枠を考慮した使用

### **権限・セキュリティ**
- 必要なSecretsの設定: `WORKLOAD_IDENTITY_PROVIDER`, `SERVICE_ACCOUNT`
- GCP権限: Cloud Run, Artifact Registry, Secret Manager へのアクセス
- mainブランチでの実行に制限（安全性確保）

### **依存関係**
- GCPプロジェクト設定とリソースの事前準備が必要
- 各ワークフローは他のプロジェクトファイル（scripts/, src/, models/ など）に依存