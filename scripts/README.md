# scripts/ - システム運用・管理スクリプト集

## 🎯 役割・責任

システム開発・運用・監視・デプロイメントの全工程を支援する統合ツール集を提供します。品質保証、機械学習モデル管理、本番環境デプロイ、システム分析まで、包括的な自動化ツールでシステムの効率的な開発・運用を支援します。

## 📂 ディレクトリ構成

```
scripts/
├── README.md               # このファイル
├── analytics/              # データ分析・監視スクリプト [詳細: analytics/README.md]
│   ├── base_analyzer.py           # 共通基盤クラス・ログ取得・システム監視
│   ├── data_collector.py          # データ収集・統計分析・CSV/JSON出力
│   ├── performance_analyzer.py    # システム性能分析・パフォーマンス監視
│   └── dashboard.py               # HTMLダッシュボード・可視化・レポート生成
├── backtest/               # バックテスト実行スクリプト [詳細: backtest/README.md]
│   └── run_backtest.py            # メインバックテスト実行スクリプト
├── deployment/             # デプロイメント・インフラ管理 [詳細: deployment/README.md]
│   ├── deploy_production.sh       # 本番環境デプロイメント・Cloud Run管理
│   ├── docker-entrypoint.sh       # Dockerコンテナエントリーポイント・起動制御
│   ├── setup_ci_prerequisites.sh  # CI/CD環境構築・GitHub Actions設定
│   ├── setup_gcp_secrets.sh       # GCP Secret Manager・認証管理
│   └── verify_gcp_setup.sh        # GCP環境検証・設定確認
├── ml/                     # 機械学習モデル学習・管理 [詳細: ml/README.md]
│   └── create_ml_models.py        # 機械学習モデル学習・構築メインスクリプト
└── testing/                # 品質保証・テストシステム [詳細: testing/README.md]
    ├── checks.sh                  # 品質チェック・テスト実行スクリプト
    └── dev_check.py               # 統合開発管理CLI・システム診断
```

## 📋 主要ディレクトリの役割

### **testing/ - 品質保証・テストシステム**
システム全体の品質保証とテスト実行を担当するディレクトリです。
- **checks.sh**: 全テスト実行・カバレッジ測定・コードスタイルチェック・品質ゲート
- **dev_check.py**: 統合開発管理CLI・システム診断・機械学習検証・本番環境監視
- 継続的品質保証・回帰防止・CI/CD統合・開発効率向上

### **ml/ - 機械学習モデル学習・管理**
機械学習モデルの学習・構築・品質保証を担当するディレクトリです。
- **create_ml_models.py**: LightGBM・XGBoost・RandomForest学習・ProductionEnsemble構築
- アンサンブル学習・ハイパーパラメータ最適化・バージョン管理・CI/CD統合
- 特徴量統合・品質検証・自動学習・週次再学習対応

### **deployment/ - デプロイメント・インフラ管理**
本番環境デプロイとインフラ管理を担当するディレクトリです。
- **deploy_production.sh**: GCP Cloud Run段階的デプロイ・品質ゲート・Discord通知
- **docker-entrypoint.sh**: コンテナ起動制御・デュアルプロセス・ヘルスチェック
- **GCP設定スクリプト**: CI/CD環境構築・Secret Manager・環境検証
- Docker統合・段階的リリース・監視・復旧・セキュリティ管理

### **analytics/ - データ分析・監視スクリプト**
システム運用データの分析・監視・可視化を担当するディレクトリです。
- **base_analyzer.py**: 共通基盤クラス・Cloud Runログ取得・システム監視
- **data_collector.py**: 取引データ収集・統計分析・品質メトリクス・Discord通知
- **performance_analyzer.py**: システム性能・機械学習モデル分析・改善提案
- **dashboard.py**: HTMLダッシュボード・Chart.js可視化・リアルタイムデータ

### **backtest/ - バックテスト実行スクリプト**
取引戦略の検証・性能評価を担当するディレクトリです。
- **run_backtest.py**: バックテストエンジン・戦略検証・パフォーマンス分析
- 過去データ使用・収益性分析・リスク管理・詳細レポート生成
- 本番前検証・戦略改善・統計分析・品質保証統合

## 📝 使用方法・例

### **日常開発ワークフロー**
```bash
# 1. 品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 2. 統合開発管理（推奨）
python3 scripts/testing/dev_check.py full-check

# 3. 機械学習モデル管理
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

### **分析・監視ワークフロー**
```bash
# 1. データ収集・分析
python3 scripts/analytics/data_collector.py --hours 24

# 2. システム性能分析
python3 scripts/analytics/performance_analyzer.py --period 7d

# 3. ダッシュボード生成
python3 scripts/analytics/dashboard.py --discord

# 4. バックテスト実行
python3 scripts/backtest/run_backtest.py --days 30 --verbose
```

### **機械学習ワークフロー**
```bash
# 1. モデル学習・構築
python3 scripts/ml/create_ml_models.py --verbose

# 2. 統合管理経由実行（推奨）
python3 scripts/testing/dev_check.py ml-models

# 3. 学習結果確認
python3 scripts/analytics/performance_analyzer.py --ml-metrics
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.8以上・全依存関係・プロジェクトルートから実行
- **GCP統合**: Cloud Run・Secret Manager・Artifact Registry設定済み
- **GitHub統合**: Actions・OIDC・Workload Identity設定完了
- **外部API**: Bitbank API・Discord Webhook設定・認証情報

### **品質保証制約**
- **テスト品質**: 全スクリプト実行前後でのテスト成功・カバレッジ維持必須
- **コード品質**: flake8・black・isort準拠・PEP8・型注釈・エラーハンドリング
- **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ遵守
- **監視統合**: Discord通知・ログ監視・アラート・自動復旧

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