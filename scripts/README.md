# scripts/ - システム運用・管理スクリプト集（Phase 28完了・Phase 29最適化版）

## 🎯 役割・責任

システム開発・運用・監視・デプロイメントの全工程を支援する統合ツール集を提供します。品質保証、機械学習モデル管理、本番環境デプロイ、システム分析まで、包括的な自動化ツールでシステムの効率的な開発・運用を支援します。

**Phase 29最適化成果**：625テスト100%成功・64.74%カバレッジ達成・統一設定管理体系完成

## 📂 ディレクトリ構成

```
scripts/
├── README.md               # このファイル（Phase 35更新版）
├── analysis/               # システム分析基盤 [詳細: analysis/README_analytics.md]
│   ├── README_analytics.md        # 分析基盤ガイド
│   ├── base_analyzer.py           # 共通基盤クラス・Cloud Runログ取得・システム監視
│   └── ml_confidence_analysis.sh  # ML信頼度分析スクリプト
├── deployment/             # デプロイメント・インフラ管理 [詳細: deployment/README.md]
│   ├── README.md                  # デプロイメントガイド
│   ├── deploy_production.sh       # 本番環境デプロイメント・Cloud Run管理
│   ├── docker-entrypoint.sh       # Dockerコンテナエントリーポイント・起動制御
│   ├── setup_gcp_environment.sh   # 統合GCP環境構築・認証管理・GitHub Actions設定
│   └── verify_gcp_setup.sh        # GCP環境検証・設定確認
├── management/             # Bot管理スクリプト [詳細: management/README.md]
│   ├── README.md                  # Bot管理ガイド
│   ├── run_safe.sh                # 統合実行スクリプト（タイムアウト・Claude Code対応）
│   └── bot_manager.sh             # 統合管理スクリプト（状況確認・プロセス停止）
├── ml/                     # 機械学習モデル学習・管理 [詳細: ml/README.md]
│   ├── README.md                  # ML管理ガイド
│   └── create_ml_models.py        # 機械学習モデル学習・構築メインスクリプト
└── testing/                # 品質保証・テストシステム [詳細: testing/README.md]
    ├── README.md                  # テストシステムガイド
    ├── checks.sh                  # 品質チェック・テスト実行スクリプト（625テスト・64.74%カバレッジ）
    └── dev_check.py               # 統合開発管理CLI・システム診断
```

## 📋 主要ディレクトリの役割

### **testing/ - 品質保証・テストシステム（Phase 29最適化完了）**
システム全体の品質保証とテスト実行を担当するディレクトリです。
- **checks.sh**: 625テスト100%成功・64.74%カバレッジ・コードスタイルチェック・隠れた致命的障害検出
- **dev_check.py**: 統合開発管理CLI・システム診断・機械学習検証・本番環境監視
- 継続的品質保証・回帰防止・CI/CD統合・開発効率向上・Phase 29品質基準完全達成

### **ml/ - 機械学習モデル学習・管理（Phase 29対応）**
機械学習モデルの学習・構築・品質保証を担当するディレクトリです。
- **create_ml_models.py**: 15特徴量統一・LightGBM・XGBoost・RandomForest学習・ProductionEnsemble構築
- アンサンブル学習・ハイパーパラメータ最適化・バージョン管理・CI/CD統合
- 特徴量統合・品質検証・自動学習・週次再学習対応・625テスト品質ゲート統合

### **deployment/ - デプロイメント・インフラ管理**
本番環境デプロイとインフラ管理を担当するディレクトリです。
- **deploy_production.sh**: GCP Cloud Run段階的デプロイ・品質ゲート・Discord通知
- **docker-entrypoint.sh**: コンテナ起動制御・デュアルプロセス・ヘルスチェック
- **GCP設定スクリプト**: CI/CD環境構築・Secret Manager・環境検証
- Docker統合・段階的リリース・監視・復旧・セキュリティ管理

### **analysis/ - システム分析基盤（Phase 35統合完了）**
システム運用データの分析・監視機能の共通基盤を提供するディレクトリです。
- **base_analyzer.py**: 共通基盤クラス・Cloud Runログ取得・システム監視・dev_check.py統合利用
- **ml_confidence_analysis.sh**: ML信頼度分析・GCPログ解析・統計計算・推奨事項自動出力
- Phase 35で analysis/ と analytics/ を統合・ディレクトリ簡素化完了

### **management/ - Bot管理スクリプト（Claude Code対応・プロセス管理統合）**
Botの安全で効率的な実行・管理を支援するディレクトリです。
- **run_safe.sh**: 統合実行スクリプト・タイムアウト管理・Claude Code完全対応・環境別実行制御
- **bot_manager.sh**: 統合管理スクリプト・Discord通知ループ解決・バックグラウンド誤認識防止
- プロセス重複防止・強制停止機能・詳細プロセス監視・運用効率向上

## 📝 使用方法・例

### **日常開発ワークフロー（Phase 29最適化版）**
```bash
# 1. 品質チェック（開発時必須・625テスト・64.74%カバレッジ）
bash scripts/testing/checks.sh

# 2. 統合開発管理（推奨）
python3 scripts/testing/dev_check.py check

# 3. 機械学習モデル管理（15特徴量統一システム）
python3 scripts/testing/dev_check.py ml-models

# 4. システム状態確認
python3 scripts/testing/dev_check.py status
```

### **本番デプロイワークフロー**
```bash
# 1. 環境検証
bash scripts/deployment/verify_gcp_setup.sh --full

# 2. 品質チェック
bash scripts/testing/checks.sh

# 3. 段階的デプロイ
bash scripts/deployment/deploy_production.sh --staged

# 4. デプロイ後確認
python3 scripts/testing/dev_check.py health-check
```

### **Bot実行・管理ワークフロー（Phase 29最適化版）**
```bash
# 1. 実行状況確認（誤認防止・推奨）
bash scripts/management/bot_manager.sh check

# 2. 通常実行（Claude Code完全対応）
bash scripts/management/run_safe.sh local paper

# 3. 完全停止（Discord通知ループ解決）
bash scripts/management/bot_manager.sh stop

# 4. システム監視
python3 scripts/testing/dev_check.py monitor
```

### **機械学習ワークフロー**
```bash
# 1. モデル学習・構築
python3 scripts/ml/create_ml_models.py --verbose

# 2. 統合管理経由実行（推奨）
python3 scripts/testing/dev_check.py ml-models

# 3. ML信頼度分析
bash scripts/analysis/ml_confidence_analysis.sh
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.8以上・全依存関係・プロジェクトルートから実行
- **GCP統合**: Cloud Run・Secret Manager・Artifact Registry設定済み
- **GitHub統合**: Actions・OIDC・Workload Identity設定完了
- **外部API**: Bitbank API・Discord Webhook設定・認証情報

### **品質保証制約（Phase 29基準）**
- **テスト品質**: 625テスト100%成功・64.74%カバレッジ維持必須・隠れた致命的障害検出
- **コード品質**: flake8・black・isort準拠・PEP8・型注釈・エラーハンドリング
- **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ遵守・統一設定管理体系
- **監視統合**: Discord通知・ログ監視・アラート・自動復旧・Claude Code誤認識防止

### **セキュリティ要件**
- **認証管理**: APIキー・シークレット・Webhook URLの適切な保護
- **アクセス制御**: 最小権限原則・サービスアカウント・権限管理
- **機密情報**: 環境変数・設定ファイル・ログマスキング・暗号化
- **監査**: 実行履歴・アクセスログ・変更記録・セキュリティ監視

### **運用制約**
- **リソース管理**: メモリ使用量・計算時間・ストレージ容量・コスト管理
- **実行順序**: 依存関係・前提条件・実行タイミング・競合回避
- **エラー対応**: 例外処理・ロールバック・復旧手順・問題エスカレーション
- **更新管理**: 定期保守・依存関係更新・セキュリティパッチ・互換性確認

## 🔗 関連ファイル・依存関係

### **システム統合**
- `src/`: メインシステム・特徴量生成・機械学習・取引システム・監視
- `config/`: 設定管理・パラメータ・環境変数・認証情報
- `models/`: 機械学習モデル・バージョン管理・メタデータ・アーカイブ
- `logs/`: システムログ・レポート・分析結果・監視データ

### **CI/CD・デプロイ**
- `.github/workflows/`: CI/CDパイプライン・自動テスト・週次学習・デプロイ
- `Dockerfile`: コンテナ化・エントリポイント・依存関係・実行環境
- `docker-compose.yml`: 開発環境・テスト環境・ローカル実行・統合テスト

### **品質保証・テスト**
- `tests/`: 単体テスト・統合テスト・機械学習テスト・品質保証
- `coverage-reports/`: カバレッジレポート・品質メトリクス・分析データ
- `.flake8`・`pyproject.toml`: コード品質・プロジェクト設定・ツール設定

### **外部システム統合**
- **GCP Services**: Cloud Run・Secret Manager・Artifact Registry・IAM
- **GitHub Actions**: CI/CD・自動化・品質ゲート・週次学習ワークフロー
- **Discord API**: 通知・アラート・監視・レポート配信・運用連携
- **Bitbank API**: 市場データ・取引システム・認証・レート制限対応

### **監視・分析システム**
- `src/monitoring/`: Discord通知・アラート・システム監視・ヘルスチェック
- Cloud Run監視・ログ分析・パフォーマンス・エラー検知・自動復旧
- HTMLダッシュボード・可視化・レポート・統計分析・トレンド監視