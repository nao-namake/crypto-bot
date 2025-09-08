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
- **repository_dispatch**: ML学習完了時の自動デプロイ（`model-updated`イベント）

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
1. **環境セットアップ**: Python3.12・依存関係インストール・モデルディレクトリ作成
2. **モデル学習**: ProductionEnsemble・3モデルアンサンブル学習・指定期間データ
3. **品質検証**: 12特徴量・モデルファイル・メタデータ整合性検証
4. **バージョン管理**: 自動コミット・プッシュ・Git情報追跡
5. **デプロイトリガー**: repository_dispatch → `model-updated`イベント送信

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

### **完全自動化フロー**

```
🗓️  毎週日曜18:00 JST
    ↓
🤖 model-training.yml 自動実行
    ├── Python3.12環境・MLライブラリ依存関係
    ├── ProductionEnsemble学習（LightGBM・XGBoost・RandomForest）
    ├── 12特徴量品質検証・モデル整合性確認
    └── Git自動コミット・repository_dispatch送信
    ↓
🚀 ci.yml 自動トリガー（model-updatedイベント）
    ├── 625テスト・品質チェック・カバレッジ確認
    ├── Docker Build・Artifact Registry プッシュ
    └── Cloud Run本番デプロイ・新MLモデル適用
    ↓
✅ 週次完全自動モデル更新完了
```

### **手動実行方法**

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
- **実行時間制限**: CI/CD 45分・ML学習 60分・クリーンアップ 45分
- **リソース制限**: GitHub Actions無料枠を考慮した使用
- **Python版**: 3.12（MLライブラリ互換性最適化・GitHub Actions安定化）

### **権限・セキュリティ**
- 必要なSecretsの設定: `WORKLOAD_IDENTITY_PROVIDER`, `SERVICE_ACCOUNT`
- GCP権限: Cloud Run, Artifact Registry, Secret Manager へのアクセス
- mainブランチでの実行に制限（安全性確保）

### **依存関係**
- GCPプロジェクト設定とリソースの事前準備が必要
- 各ワークフローは他のプロジェクトファイル（scripts/, src/, models/ など）に依存