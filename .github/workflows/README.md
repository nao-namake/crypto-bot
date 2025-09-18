# GitHub Actions Workflows - 統一設定管理体系

## 🎯 役割・責任

このディレクトリには、統一設定管理体系の下で実行される3つのワークフローファイルが含まれています。CI/CD統一化・設定不整合完全解消により、システムの品質保証、機械学習モデルの管理、リソース最適化を実現します。

## 📂 ファイル構成

```
workflows/
├── ci.yml               # メインCI/CDパイプライン（統一設定管理体系対応）
├── model-training.yml   # ML モデル学習・デプロイメント（15特徴量統一）
├── cleanup.yml          # GCPリソースクリーンアップ（625テスト品質保証）
└── README.md            # このファイル
```

## 🔧 ワークフローの役割・ルール

### **ci.yml - CI/CDパイプライン（統一設定管理体系）**

**役割**: メインのCI/CDパイプライン・設定不整合完全解消・GitHub Actions統一

**実行条件**:
- `main` ブランチへのプッシュ（自動デプロイ・MODE=live）
- プルリクエスト作成時（品質チェック）
- 手動実行
- **repository_dispatch**: ML学習完了時の自動デプロイ（`model-updated`イベント）

**実行フロー**:
1. **品質チェック**: 625テスト実行・64.74%カバレッジ・コード品質確認
2. **GCP環境確認**: Secret Manager（:3,:5）・Workload Identity・必要リソース確認
3. **Dockerビルド**: イメージ構築とArtifact Registryプッシュ
4. **本番デプロイ**: Cloud Runサービスデプロイ（MODE=live統一設定）
5. **ヘルスチェック**: デプロイ成功確認

### **model-training.yml - MLモデル学習・デプロイメント（15特徴量統一）**

**役割**: MLモデルの学習とデプロイメント・15特徴量統一システム

**実行条件**:
- 毎週日曜日 18:00 JST（スケジュール実行）
- 手動実行（パラメータ設定可能）

**パラメータ**:
- `training_days`: 学習データ期間（90/180/365日）
- `dry_run`: テスト実行フラグ

**実行フロー**:
1. **環境セットアップ**: Python3.13・依存関係インストール・モデルディレクトリ作成
2. **モデル学習**: ProductionEnsemble・3モデルアンサンブル学習・指定期間データ
3. **品質検証**: 15特徴量・モデルファイル・メタデータ整合性検証
4. **バージョン管理**: 自動コミット・プッシュ・Git情報追跡
5. **デプロイトリガー**: repository_dispatch → `model-updated`イベント送信

### **cleanup.yml - GCPリソースクリーンアップ（625テスト品質保証）**

**役割**: GCPリソースの自動削除とコスト最適化・625テスト品質保証環境

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

### **完全自動化フロー（統一設定管理体系）**

```
🗓️  毎週日曜18:00 JST
    ↓
🤖 model-training.yml 自動実行
    ├── Python3.13環境・MLライブラリ依存関係
    ├── ProductionEnsemble学習（LightGBM・XGBoost・RandomForest）
    ├── 15特徴量品質検証・モデル整合性確認
    └── Git自動コミット・repository_dispatch送信
    ↓
🚀 ci.yml 自動トリガー（model-updatedイベント）
    ├── 625テスト・品質チェック・64.74%カバレッジ確認
    ├── Docker Build・Artifact Registry プッシュ
    └── Cloud Run本番デプロイ・新MLモデル適用（MODE=live）
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

### **統一設定管理体系制約**
- **同時実行制限**: mainブランチでは順次実行（競合回避）
- **実行時間制限**: CI/CD 30分・ML学習 60分・クリーンアップ 20分
- **Python版**: 3.13（全ワークフロー統一・MLライブラリ互換性最適化）
- **MODE設定**: CI/CDは自動的にMODE=live（統一設定管理体系）

### **権限・セキュリティ（統一設定管理体系対応）**
- **Workload Identity**: `projects/11445303925/locations/global/workloadIdentityPools/github-pool/providers/github-provider`
- **Service Account**: `github-deployer@my-crypto-bot-project.iam.gserviceaccount.com`
- **Secret Manager**: 具体的バージョン（bitbank-api-key:3, bitbank-api-secret:3, discord-webhook-url:5）
- **実行制限**: mainブランチでの実行に制限（安全性確保）

### **依存関係**
- GCPプロジェクト設定とリソースの事前準備が必要
- 各ワークフローは他のプロジェクトファイル（scripts/, src/, models/ など）に依存
- 統一設定管理体系：全設定ファイルとの整合性が必要

## 🔧 重要な修正履歴

### **2025-09-18: 統一設定管理体系確立完了**

**実現内容**: CI/CD・GCP・設定ファイルの完全統一・設定不整合完全解消

**主要改善**:
- **cloudbuild.yaml削除**: GitHub Actions統一・Cloud Build廃止・設定不整合解消
- **Secret Manager最適化**: :latest廃止→具体的バージョン（:3,:5）・セキュリティ向上
- **MODE設定統一**: CI/CD時自動的にMODE=live・環境変数で統一制御
- **Kelly基準最適化**: min_trades 20→5・初期position_size 0.0002 BTC・実用性大幅向上
- **Python版統一**: 全ワークフローで3.13統一
- **テスト・品質統一**: 625テスト・64.74%カバレッジ・15特徴量で統一

**技術的詳細**:
- 3層優先順位：CLI引数 > 環境変数 > YAML設定
- CI/CD環境変数：MODE=live・LOG_LEVEL=INFO・PYTHONPATH=/app
- Secret Manager具体的バージョン使用でCloud Run環境での動的参照問題解決

**影響**:
- ✅ 設定不整合完全解消・100%統一達成
- ✅ CI/CDでデプロイ時確実にライブモード動作
- ✅ Kelly基準問題解決・取引開始促進
- ✅ 全システムで統一設定管理体系確立

### **2025-09-15: Secret Manager参照修正（根本原因解決）**

**解決方法**: 具体的バージョン番号に変更（ci.yml:319）
```yaml
# 修正後の設定
--set-secrets="BITBANK_API_KEY=bitbank-api-key:3,BITBANK_API_SECRET=bitbank-api-secret:3,DISCORD_WEBHOOK_URL=discord-webhook-url:5"
```

**教訓**: Cloud Run環境では `key: latest` ではなく具体的バージョン番号を使用

---

**統一設定管理体系により、AI自動取引botのCI/CD・GCP環境・設定ファイルが100%統一され、設定不整合問題が完全に解消されました。**