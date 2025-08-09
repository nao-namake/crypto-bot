# scripts/ - 暗号通貨自動取引システム実行スクリプト集

## 📋 概要

**Cryptocurrency Trading Bot Scripts Collection**  
crypto-bot プロジェクトの各種実行スクリプトを管理するディレクトリです。品質チェック、モデル学習、バックテスト、システム診断、デプロイメントなど、開発・運用に必要なツールを提供します。

## 🎯 ディレクトリ構造

```
scripts/
├── core/                   # コア機能スクリプト
├── utilities/              # 汎用ユーティリティ・補助ツール  
├── archive/                # 過去の実装・参考用スクリプト
├── deprecated/             # 不要・古いスクリプト（整理済み）
└── [メインスクリプト]      # 日常的に使用するスクリプト
```

## 🚀 メインスクリプト（現在使用中）

### **品質管理・テスト**
- `checks.sh` - 品質チェック統合実行（flake8・isort・black・pytest）
- `run_all_local_tests.sh` - ローカル環境での包括的テスト
- `run_e2e.sh` - エンドツーエンドテスト
- `run_pipeline.sh` - パイプライン実行
- `run_production_tests.sh` - 本番環境テスト
- `quick_health_check.sh` - クイックヘルスチェック

### **モデル管理**
- `create_proper_ensemble_model.py` - 97特徴量アンサンブルモデル作成（現行版）
- `retrain_97_features_model.py` - 97特徴量モデル再学習
- `validate_97_features_optimization.py` - 97特徴量システム検証

### **統合システム（新規作成）**
- `unified_backtest_system.py` - 統合バックテストシステム
  - 標準・ハイブリッド・ウォークフォワード・軽量・閾値検証・JPY建て
- `unified_optimization_system.py` - 統合最適化システム
  - 特徴量選択・信頼度閾値・エントリー閾値・推奨事項生成
- `unified_ensemble_system.py` - 統合アンサンブルシステム
  - A/Bテスト・統計検証・統合計画・デモ実行

### **システム管理** (2025年8月10日更新)
- `system_health_check.py` - システム健全性チェック
- `diagnose_cloud_run_apis.py` - Cloud Run API診断
- `gcp_revision_manager.py` - GCPリビジョン管理
- `pre_compute_data.py` - 事前計算データ生成
- **`prepare_initial_data.py`** - 初期データ事前取得
  - 72時間分のOHLCVデータ取得（Bitbank API制限対応）
  - 97特徴量事前計算
  - `cache/initial_data.pkl` として保存
  - 本番デプロイ前に実行推奨
- **`create_minimal_cache.py`** - 最小限キャッシュ作成（CI/CD対応）
  - CI環境用の72時間ダミーデータ生成
  - リアリスティックなBTC/JPY価格データ
  - API認証不要のフォールバック
  - CI/CDパイプラインで使用
- **`create_ci_model.py`** - CI用モデルファイル作成（新規追加）
  - TradingEnsembleClassifier形式のダミーモデル
  - 97特徴量対応
  - CI/CDでのモデルファイル不在エラー解決

### **デプロイメント・環境管理** (2025年8月10日更新)
- `verify_github_secrets.sh` - GitHub Secrets設定確認・CI/CDトラブルシューティング
- `setup_gcp_secrets.sh` - GCP Secret Manager設定（オプション）
- `cleanup_cloud_run_revisions.sh` - Cloud Runリビジョン競合解決
- **`deploy_with_initial_data.sh`** - 初期データ付きデプロイ
  - 初期データキャッシュ準備
  - Dockerビルド・テスト
  - Git commit/push
  - CI/CD自動トリガー
  - 完全自動化デプロイスクリプト

### **開発ツール**
- `auto_push.sh` - 自動Git push（整形・テスト・プッシュ）
- `convert_absolute_to_relative_paths.py` - 絶対パス→相対パス変換
- `cleanup_feature_backups.sh` - 特徴量バックアップ整理

### **Phase関連**
- `phase42_adjusted_backtest.py` - Phase 4.2動的日付調整バックテスト
- `phase42_production_simulation.py` - Phase 4.2本番シミュレーション

### **データ分析**
- `analyze_training_data.py` - 学習データ分析
- `market_data_analysis.py` - 市場データ分析
- `create_backtest_data.py` - バックテストデータ作成
- `clean_historical_data.py` - 履歴データクリーニング

### **テスト・検証**
- `test_multi_timeframe.py` - マルチタイムフレームテスト
- `test_quality_monitor.py` - 品質監視テスト

## 📁 core/ - コア機能

```
core/
└── protect_feature_order.py    # feature_order.json保護システム
```

## 🔧 utilities/ - ユーティリティ

### **環境・インフラ**
- `check_gcp_env.sh` - GCP環境確認
- `setup_secrets.sh` - シークレット設定
- `monitor_deployment.sh` - デプロイメント監視
- `verify_wif_hardening.sh` - WIF強化検証
- `test_terraform_local.sh` - Terraformローカルテスト

### **データ・テスト**
- `generate_btc_csv_data.py` - BTCデータCSV生成
- `test_bitbank_auth.py` - Bitbank API認証テスト
- `emergency_shutdown.py` - 緊急停止ツール

### **診断・トラブルシューティング**
- `troubleshoot_deployment.sh` - デプロイメント問題診断
- `bigquery_log_queries.sql` - BigQueryログクエリ集

## 📦 archive/ - アーカイブ

過去の実装や参考用スクリプトを保管。将来の機能拡張時の参考資料として活用。

## 🗑️ deprecated/ - 不要スクリプト

整理により不要と判定されたスクリプト（63ファイル）を保管。古い特徴量システム（127/125/124）、デバッグ・修正系、統合前の個別スクリプトなど。

## 🚀 使用方法

### **日常的な開発作業**
```bash
# 品質チェック実行
bash scripts/checks.sh

# 自動プッシュ（整形・テスト・プッシュ）
bash scripts/auto_push.sh "feat: add new feature"

# 包括的ローカルテスト
bash scripts/run_all_local_tests.sh
```

### **モデル管理**
```bash
# 97特徴量アンサンブルモデル作成
python scripts/create_proper_ensemble_model.py

# モデル再学習
python scripts/retrain_97_features_model.py
```

### **統合システム活用**
```bash
# バックテスト実行
python scripts/unified_backtest_system.py --mode standard --config production.yml
python scripts/unified_backtest_system.py --mode walkforward --months 6

# 最適化実行
python scripts/unified_optimization_system.py --mode confidence --min 0.2 --max 0.5
python scripts/unified_optimization_system.py --mode recommendations

# アンサンブル検証
python scripts/unified_ensemble_system.py --mode verify
```

### **システム診断**
```bash
# システムヘルスチェック
python scripts/system_health_check.py

# Cloud Run診断
python scripts/diagnose_cloud_run_apis.py

# GCP環境確認
bash scripts/utilities/check_gcp_env.sh
```

## ⚠️ 重要事項

### **ファイル管理原則**
- **メインスクリプト**: 日常使用・最新版のみ維持
- **統合システム**: 複数機能を1つに統合・保守性向上
- **deprecated/**: 削除せず保管（履歴参照用）
- **archive/**: 将来の参考資料として保持

### **整理による効果**
- **ファイル数削減**: 63ファイルをdeprecatedへ移動
- **統合効率化**: バックテスト・最適化・アンサンブルを各1ファイルに
- **明確な構造**: 用途別に整理・探しやすさ向上
- **保守性向上**: 重複削除・責任明確化

### **今後の追加ガイドライン**
1. 新規スクリプトは適切なカテゴリに配置
2. 類似機能は統合システムへ追加
3. 一時的なデバッグスクリプトは作成後削除
4. README.mdの更新を忘れずに

### **CI/CD関連スクリプト使用例**
```bash
# CI用モデル作成（ローカルテスト）
python scripts/create_ci_model.py

# CI用キャッシュ作成（ローカルテスト）
python scripts/create_minimal_cache.py

# 本番用初期データ準備
export BITBANK_API_KEY="your-api-key"
export BITBANK_API_SECRET="your-api-secret"
python scripts/prepare_initial_data.py
```

---

*Scripts構造は2025年8月7日に大規模整理・最適化されました*
*2025年8月10日：CI/CD対応スクリプト追加*