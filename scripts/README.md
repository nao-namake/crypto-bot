# scripts/ - システム運用・管理スクリプト集（Phase 49完了版）

## 🎯 役割・責任

システム開発・運用・監視・デプロイメント・バックテストの全工程を支援する統合ツール集を提供します。品質保証、機械学習モデル管理、本番環境デプロイ、バックテスト実行まで、包括的な自動化ツールでシステムの効率的な開発・運用を支援します。

**Phase 49完了成果**：1,117テスト100%成功・68.32%カバレッジ達成・バックテスト完全改修・確定申告対応・週間レポート実装

## 📂 ディレクトリ構成

```
scripts/
├── README.md               # このファイル（Phase 49完了版）
├── deployment/             # デプロイメント・インフラ管理 [詳細: deployment/README.md]
│   ├── README.md                  # デプロイメントガイド（Phase 49完了版）
│   ├── docker-entrypoint.sh       # Dockerコンテナエントリーポイント・起動制御（Phase 49対応済み）
│   └── archive/                   # 初期セットアップ用スクリプト（環境構築済みのため使用頻度低）
│       ├── setup_gcp_environment.sh   # 統合GCP環境構築・認証管理・GitHub Actions設定
│       └── verify_gcp_setup.sh        # GCP環境検証・設定確認
├── management/             # Bot管理スクリプト [詳細: management/README.md]
│   ├── README.md                  # Bot管理ガイド（Phase 49完了版）
│   ├── run_safe.sh                # 統合実行スクリプト（Phase 49.14対応済み・タイムアウト・Claude Code対応）
│   └── bot_manager.sh             # 統合管理スクリプト（状況確認・プロセス停止）
├── backtest/               # バックテスト実行システム [詳細: backtest/README.md] 【Phase 49新設】
│   ├── README.md                  # バックテスト実行ガイド（Phase 49完了版）
│   └── run_backtest.sh            # バックテスト実行スクリプト（Phase 34実装・Phase 49移動）
├── ml/                     # 機械学習モデル学習・管理 [詳細: ml/README.md]
│   ├── README.md                  # ML管理ガイド（Phase 49完了版）
│   ├── create_ml_models.py        # 機械学習モデル学習・構築メインスクリプト（55特徴量Strategy-Aware ML）
│   └── archive/                   # 過去の実験的スクリプト（Phase 49整理）
│       └── train_meta_learning_model.py   # Meta-Learning実験実装（Phase 45.3・未使用）
└── testing/                # 品質保証・テストシステム [詳細: testing/README.md]
    ├── README.md                  # テストシステムガイド（Phase 49完了版）
    ├── checks.sh                  # 品質チェック・テスト実行スクリプト（1,117テスト・68.32%カバレッジ）
    └── validate_system.sh         # システム整合性検証スクリプト（Phase 49.14実装）
```

## 📋 主要ディレクトリの役割

### **testing/ - 品質保証・テストシステム（Phase 49完了）**
システム全体の品質保証とテスト実行を担当するディレクトリです。
- **checks.sh**: 1,117テスト100%成功・68.32%カバレッジ・コードスタイルチェック・隠れた致命的障害検出
- **validate_system.sh**: Phase 49.14実装・Dockerfile/特徴量/戦略/モジュール整合性検証・Phase 49.13問題防止
- 継続的品質保証・回帰防止・CI/CD統合・開発効率向上・Phase 49品質基準完全達成

### **ml/ - 機械学習モデル学習・管理（Phase 49対応）**
機械学習モデルの学習・構築・品質保証を担当するディレクトリです。
- **create_ml_models.py**: 55特徴量Strategy-Aware ML・LightGBM・XGBoost・RandomForest学習・ProductionEnsemble構築
- アンサンブル学習・ハイパーパラメータ最適化・バージョン管理・CI/CD統合
- 特徴量統合（50基本+5戦略信号）・品質検証・自動学習・週次再学習対応・1,117テスト品質ゲート統合

### **deployment/ - デプロイメント・インフラ管理（Phase 49完了）**
本番環境デプロイとインフラ管理を担当するディレクトリです。
- **docker-entrypoint.sh**: コンテナ起動制御（Phase 49対応済み）・デュアルプロセス・ヘルスチェック
- **archive/**: 初期セットアップ用スクリプト（環境構築済みのため使用頻度低）
  - **setup_gcp_environment.sh**: GCP環境初期構築（初期構築のみ）
  - **verify_gcp_setup.sh**: GCP環境検証・設定確認（診断時のみ）
- Docker統合・段階的リリース・監視・復旧・セキュリティ管理・Phase 49完了成果反映

### **management/ - Bot管理スクリプト（Phase 49完了・Claude Code完全対応）**
Botの安全で効率的な実行・管理を支援するディレクトリです。
- **run_safe.sh**: 統合実行スクリプト（Phase 49.14対応済み）・タイムアウト管理・Claude Code完全対応・環境別実行制御
- **bot_manager.sh**: 統合管理スクリプト・Discord通知ループ解決・バックグラウンド誤認識防止
- プロセス重複防止・強制停止機能・詳細プロセス監視・運用効率向上・Phase 49.14システム検証統合

### **backtest/ - バックテスト実行システム（Phase 49新設）** 【Phase 49整理】
バックテストシステムの実行・管理を支援するディレクトリです。
- **run_backtest.sh**: バックテスト実行スクリプト（Phase 34実装・Phase 49移動）・3モード実行（quick/standard/full）
- **Phase 49完全改修**: 戦略シグナル事前計算・TP/SL決済ロジック・TradeTracker実装・matplotlib可視化
- バックテスト信頼性100%達成・ライブモード完全一致・SELL判定正常化・45分実行（10倍高速化）
- **Phase 49整理**: scripts/management/から分離・バックテスト専用ツールとして独立

## 📝 使用方法・例

### **日常開発ワークフロー（Phase 49完了版）**
```bash
# 1. 品質チェック（開発時必須・1,117テスト・68.32%カバレッジ）
bash scripts/testing/checks.sh

# 2. システム整合性検証（Phase 49.14・推奨）
bash scripts/testing/validate_system.sh

# 3. 機械学習モデル管理（55特徴量Strategy-Aware ML）
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50
```

### **本番デプロイワークフロー**
```bash
# 1. 品質チェック（必須）
bash scripts/testing/checks.sh

# 2. システム整合性検証（推奨）
bash scripts/testing/validate_system.sh

# 3. 環境検証（必要時のみ）
bash scripts/deployment/verify_gcp_setup.sh --full

# 4. デプロイ実行（GitHub Actions自動実行）
# .github/workflows/ci.yml が自動実行（main ブランチpush時）

# 5. デプロイ後確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
curl https://crypto-bot-service-prod-XXXXXXXX.asia-northeast1.run.app/health
```

### **Bot実行・管理ワークフロー（Phase 49完了版）**
```bash
# 1. 実行状況確認（誤認防止・推奨）
bash scripts/management/bot_manager.sh check

# 2. 通常実行（Phase 49.14システム検証自動実行）
bash scripts/management/run_safe.sh local paper

# 3. 完全停止（Discord通知ループ解決）
bash scripts/management/bot_manager.sh stop

# 4. 本番環境監視（GCP Cloud Run）
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

### **機械学習ワークフロー**（Phase 49完了版）
```bash
# 1. モデル学習・構築（55特徴量Strategy-Aware ML・基本実行）
python3 scripts/ml/create_ml_models.py --verbose

# 2. Optunaハイパーパラメータ最適化（推奨）
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50 --verbose

# 3. 週次自動再学習（GitHub Actions）
# .github/workflows/model-training.yml - 毎週日曜18:00 JST自動実行

# 4. モデル検証
python3 -c "import json; print(json.load(open('models/production/production_model_metadata.json', 'r')))"
```

### **バックテストワークフロー（Phase 49完了版）** 【Phase 49新設】
```bash
# 1. 品質チェック（必須）
bash scripts/testing/checks.sh

# 2. クイックバックテスト（7日間・動作確認用）
bash scripts/backtest/run_backtest.sh quick

# 3. 標準バックテスト（30日間・通常検証用）
bash scripts/backtest/run_backtest.sh standard

# 4. フルバックテスト（180日間・推奨・完全検証）
bash scripts/backtest/run_backtest.sh full

# 5. レポート確認
open logs/backtest_report_*.html
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.8以上・全依存関係・プロジェクトルートから実行
- **GCP統合**: Cloud Run・Secret Manager・Artifact Registry設定済み
- **GitHub統合**: Actions・OIDC・Workload Identity設定完了
- **外部API**: Bitbank API・Discord Webhook設定・認証情報

### **品質保証制約（Phase 49基準）**
- **テスト品質**: 1,117テスト100%成功・68.32%カバレッジ維持必須・隠れた致命的障害検出
- **コード品質**: flake8・black・isort準拠・PEP8・型注釈・エラーハンドリング
- **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ遵守・統一設定管理体系
- **監視統合**: Discord通知・ログ監視・アラート・自動復旧・Claude Code誤認識防止
- **バックテスト検証**: Phase 49完全改修・信頼性100%達成・ライブモード完全一致必須

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
- **GitHub Actions**: CI/CD・自動化・品質ゲート・週次学習ワークフロー・週間レポート自動送信
- **Discord API**: 通知・アラート・監視・レポート配信・運用連携・週間レポート（Phase 48実装）
- **Bitbank API**: 市場データ・取引システム・認証・レート制限対応・バックテスト履歴データ取得

### **監視・分析システム**
- `src/monitoring/`: Discord通知・アラート・システム監視・ヘルスチェック
- Cloud Run監視・ログ分析・パフォーマンス・エラー検知・自動復旧
- HTMLダッシュボード・可視化・レポート・統計分析・トレンド監視
- `src/backtest/`: バックテストエンジン（Phase 49完全改修）・TradeTracker・matplotlib可視化
- `src/core/reporting/`: 週間レポート生成（Phase 48実装）・損益曲線グラフ・通知99%削減