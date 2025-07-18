# Scripts ディレクトリ構造ガイド

このディレクトリは用途別に整理されたスクリプトファイルを管理します。

## 📁 ディレクトリ構造

```
scripts/
├── archive/           # 特定作業用・将来参考価値あり
├── utilities/         # 汎用ユーティリティ・補助ツール
├── README.md         # このファイル
└── [メインスクリプト] # 日常的に使用するスクリプト
```

## 🚀 メインスクリプト（日常使用）

**現在使用中・重要なスクリプト**

### `start_live_with_api_fixed.py`
- **用途**: 本番ライブトレード起動スクリプト
- **状況**: ✅ **現在稼働中** - Phase 2.2対応・API-onlyモード回避版
- **機能**: ライブトレード + APIサーバー統合・Cloud Run対応
- **実行**: Docker環境で自動実行

### `auto_push.sh`
- **用途**: 自動化されたGitプッシュワークフロー
- **機能**: 依存インストール → コード整形 → Lint/Test → Git push
- **使用法**: `bash scripts/auto_push.sh "feat: new feature"`
- **オプション**: `--install` で依存関係再インストール

### `checks.sh`
- **用途**: 品質チェック（CI/CDで使用中）
- **機能**: flake8・isort・black・pytest + カバレッジ
- **実行**: `bash scripts/checks.sh`
- **重要**: CI/CDパイプラインの中核

### `build_docker.sh`
- **用途**: 基本Dockerイメージビルド
- **機能**: crypto-bot:latest イメージ作成
- **実行**: `bash scripts/build_docker.sh`

### テスト実行スクリプト群
- `run_docker.sh` - Docker内でのコマンド実行
- `run_all_local_tests.sh` - ローカル環境での包括的テスト
- `run_e2e.sh` - E2Eテスト実行
- `run_pipeline.sh` - パイプライン実行
- `run_production_tests.sh` - 本番環境テスト

## 📦 Archive フォルダ (`archive/`)

**特定作業用・将来参考価値のあるスクリプト**

### デプロイメント関連
- `build_phase2_amd64.sh` - Phase 2専用AMD64ビルド・デプロイ
- `build_complete_amd64.sh` - 完成版AMD64ビルド
- `phase3_deploy.sh` - Phase 3デプロイメント
- `phase3_deployment.py` - Phase 3デプロイメント（Python版）

### アンサンブル学習・分析システム
- `ensemble_backtest_system.py` - アンサンブルバックテストシステム
- `performance_comparison_system.py` - パフォーマンス比較システム
- `production_integration_system.py` - 本番統合システム
- `monitoring_alert_system.py` - 監視・アラートシステム

### 使用場面
- 将来の機能拡張時の参考
- 類似システム開発時のベースライン
- 過去の実装手法の確認

## 🔧 Utilities フォルダ (`utilities/`)

**汎用ユーティリティ・補助ツール**

### データ生成・テスト
- `generate_btc_csv_data.py` - BTCデータCSV生成
- `test_bitbank_auth.py` - Bitbank API認証テスト
- `emergency_shutdown.py` - 緊急停止ツール

### インフラ・セットアップ
- `check_gcp_env.sh` - GCP環境確認
- `setup_secrets.sh` - シークレット設定
- `monitor_deployment.sh` - デプロイメント監視
- `bigquery_log_queries.sql` - BigQueryログクエリ集

### トラブルシューティング
- `troubleshoot_deployment.sh` - デプロイメント問題診断
- `verify_wif_hardening.sh` - WIF強化検証
- `test_docker_local.sh` - ローカルDocker環境テスト
- `test_terraform_local.sh` - ローカルTerraform環境テスト

### 使用場面
- 問題発生時の診断・修復
- 新規環境セットアップ
- データ生成・テスト用途

## 🔄 使用方法

### 日常的な開発作業
```bash
# 品質チェック実行
bash scripts/checks.sh

# 自動プッシュ（整形・テスト・プッシュ）
bash scripts/auto_push.sh "feat: add new feature"

# Dockerビルド
bash scripts/build_docker.sh

# 包括的ローカルテスト
bash scripts/run_all_local_tests.sh
```

### 本番デプロイメント
```bash
# 本番ライブトレード起動（Docker環境で自動実行）
python scripts/start_live_with_api_fixed.py
```

### ユーティリティ活用
```bash
# GCP環境確認
bash scripts/utilities/check_gcp_env.sh

# Bitbank API認証テスト
python scripts/utilities/test_bitbank_auth.py

# CSV データ生成
python scripts/utilities/generate_btc_csv_data.py
```

### アーカイブ活用
```bash
# アンサンブルバックテスト実行
python scripts/archive/ensemble_backtest_system.py

# パフォーマンス比較分析
python scripts/archive/performance_comparison_system.py
```

## ⚠️ 重要事項

### ファイル管理原則
- **メインスクリプト**: 日常使用するもののみ・変更時は慎重に
- **Archive**: 保存目的・直接変更は避ける
- **Utilities**: 補助ツール・必要に応じて拡張可能

### セキュリティ注意事項
- シークレット情報はファイルに直接記載しない
- 本番環境での実行前は必ずテスト環境で検証
- 緊急停止ツールの場所と使用方法を把握

### 追加・削除時のガイドライン
- **新規追加**: 適切なフォルダに配置・README更新
- **削除**: 他のスクリプトからの依存関係確認
- **移動**: 既存の呼び出し元の更新忘れに注意

---

*Scripts構造は2025年7月17日に整理・最適化されました*