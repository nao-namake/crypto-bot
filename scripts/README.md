# scripts/ - 暗号通貨自動取引システム実行スクリプト集

## 📋 概要

**Cryptocurrency Trading Bot Scripts Collection**  
crypto-bot プロジェクトの各種実行スクリプトを管理するディレクトリです。品質チェック、モデル学習、バックテスト、システム診断、デプロイメントなど、開発・運用に必要なツールを提供します。

**🎊 2025年8月13日重大更新**:
- **🚨 モデル互換性問題緊急対応**: monotonic_cst属性エラー・scikit-learnバージョン不整合の根本解決
- **model_tools/retrain_97_features_model.py**: FeatureOrderManager属性修正・完全再学習実装
- **model_tools/create_proper_ensemble_model.py**: バージョン整合モデル読み込みパス修正
- **operational_status_checker.py**: 🆕 完璧稼働状況確認システム（4段階チェック・隠れたエラー検出）
- **bot_manager.py**: デプロイ前包括チェック・data_check()機能追加
- **status_config.json**: 隠れたエラーパターンDB・過去12パターン登録済み

## 🎯 ディレクトリ構造（2025年8月11日 体系的整理実施）

```
scripts/
├── bot_manager.py          # 🌟 デプロイ前統合チェックCLI（品質・監視・修復）
├── operational_status_checker.py  # 🎊 完璧稼働状況確認システム（運用中監視）
├── status_config.json     # ⚙️ 隠れたエラーパターンDB・設定ファイル
├── ci_tools/               # 🚀 CI/CD前ツール（必須チェック）
│   ├── checks.sh          # 品質チェック統合実行
│   ├── validate_all.sh    # 3段階検証システム
│   ├── pre_deploy_validation.py
│   └── auto_push.sh       # 自動コミット＆プッシュ
├── model_tools/            # 🤖 モデル管理
│   ├── manage_models.py   # 統合モデル管理ツール
│   ├── create_*.py        # モデル作成スクリプト
│   └── retrain_*.py       # 再学習スクリプト
├── system_tools/           # 🔧 システム管理
│   ├── system_health_check.py
│   ├── diagnose_cloud_run_apis.py
│   └── gcp_revision_manager.py
├── data_tools/             # 📊 データ準備・分析
│   ├── prepare_initial_data.py
│   ├── analyze_training_data.py
│   └── create_backtest_data.py
├── monitoring/             # 📡 監視・検証・修復
│   ├── signal_monitor.py  # Phase 2-2
│   ├── future_leak_detector.py # Phase 2-3
│   ├── error_analyzer.py  # Phase 3
│   └── analyze_and_fix.py # Phase 3統合
├── core/                   # コア機能（既存維持）
├── utilities/              # 環境設定・補助ツール
├── archive/                # 過去の実装・参考用
└── deprecated/             # 整理済み古いスクリプト
```

## 🎯 推奨ワークフロー・使い分け

### **🚀 デプロイ前（CI実行前）**
```bash
# デプロイ前の包括チェック - bot_manager.py使用
python scripts/bot_manager.py full-check  # 品質・監視・修復の統合チェック
python scripts/bot_manager.py status      # システム状態確認
python scripts/bot_manager.py data-check  # データ取得ロジック事前検証
```

### **✅ CI通過後（運用中の稼働確認）**  
```bash
# 完璧稼働状況確認 - operational_status_checker.py使用
python scripts/operational_status_checker.py              # 全4段階チェック実行
python scripts/operational_status_checker.py --verbose    # 詳細ログ付き
python scripts/operational_status_checker.py --phase phase3  # 隠れた問題検出のみ
```

## 🌟 統合管理CLI（bot_manager.py）

**デプロイ前のすべての検証・監視・修復機能を1つのCLIで管理**

### **基本使用方法**
```bash
# ヘルプ表示
python scripts/bot_manager.py --help

# システム状態確認
python scripts/bot_manager.py status

# デプロイ前の完全チェック（推奨）
python scripts/bot_manager.py full-check
```

### **主要コマンド**

| コマンド | 説明 | 使用例 |
|---------|------|--------|
| `validate` | 3段階検証実行 | `bot_manager.py validate --mode quick` |
| `monitor` | シグナル監視 | `bot_manager.py monitor --hours 24` |
| `fix-errors` | エラー分析・修復 | `bot_manager.py fix-errors --auto-fix` |
| `paper-trade` | ペーパートレード | `bot_manager.py paper-trade --hours 2` |
| `leak-detect` | リーク検出 | `bot_manager.py leak-detect` |
| `data-check` 🆕 | データ取得検証 | `bot_manager.py data-check` |
| `full-check` | 完全チェック | `bot_manager.py full-check` |
| `status` | 状態確認 | `bot_manager.py status` |

## 🎊 完璧稼働状況確認システム（operational_status_checker.py）🆕

**CI通過後の運用中システムを完璧に監視・隠れたエラーを確実に検出**

### **特徴**
- **4段階固定チェック**: インフラ・アプリ・隠れた問題・総合判定
- **過去10パターンの隠れたエラー検出**: 48/300停滞・表面稼働実際停止等
- **既存tool統合**: 4つの監視スクリプト統合・重複排除
- **JST時刻統一**: UTC/JST混在問題を根本解決
- **美しいHTMLレポート**: 問題分析・具体的アクション提案付き

### **基本使用方法**
```bash
# 完璧稼働状況確認（全4段階）
python scripts/operational_status_checker.py

# 詳細ログ付き実行
python scripts/operational_status_checker.py --verbose

# 特定段階のみ実行
python scripts/operational_status_checker.py --phase phase1  # インフラのみ
python scripts/operational_status_checker.py --phase phase3  # 隠れた問題のみ

# HTMLレポート生成確認
python scripts/operational_status_checker.py --save-report
```

### **4段階チェック内容**

| Phase | 内容 | 重み | 検出項目 |
|-------|------|------|---------|
| **Phase 1** | インフラ・基盤確認 | 25% | GCP Cloud Run・API接続・システムヘルス・リソース |
| **Phase 2** | アプリケーション動作確認 | 30% | ログ分析・データ取得・シグナル生成・メインループ |
| **Phase 3** | 隠れた問題検出 | 30% | **過去10パターン**・パフォーマンス異常・未来リーク・設定整合性 |
| **Phase 4** | 総合判定・レポート生成 | 15% | スコアリング・リスク評価・アクション提案・HTML生成 |

### **隠れたエラーパターン（Phase 3で検出）**
1. **データ取得停滞**: 48/300で停止・Empty batch連続
2. **表面稼働・実際停止**: ヘルス200だが数時間前からログなし  
3. **メインループ未到達**: INIT段階で停止・メインループ到達せず
4. **リビジョン切替失敗**: 新リビジョン作成されるが古いバージョンがACTIVE
5. **無限リトライループ**: Attempt 15/20等の異常リトライ
6. **モデル予測異常**: confidence固定値・連続HOLD過多
7. **インポート・メソッド不在**: テスト実行時発覚の隠れたエラー
8. **CI/CD長時間スタック**: GitHub Actions数時間停止
9. **メモリリーク**: 緩やかなメモリ使用量増加・パフォーマンス劣化
10. **UTC/JST混在**: 時刻表示混乱による状況誤認

### **推奨ワークフロー（デプロイ前）**
```bash
# 1. 開発前の状態確認
python scripts/bot_manager.py status

# 2. コード変更後の高速チェック
python scripts/bot_manager.py validate --mode quick

# 3. コミット前の完全チェック
python scripts/bot_manager.py full-check

# 4. エラーがある場合は修復
python scripts/bot_manager.py fix-errors --auto-fix

# 5. 再度検証
python scripts/bot_manager.py validate
```

## 📁 各フォルダの役割

### **ci_tools/ - CI/CD前ツール**
コミット前・デプロイ前の必須チェックツール
- **主要ツール:** checks.sh, validate_all.sh
- **用途:** 品質保証、検証、自動化
- **詳細:** [ci_tools/README.md](ci_tools/README.md)

### **model_tools/ - モデル管理**
機械学習モデルの作成・再学習・管理
- **主要ツール:** manage_models.py（統合管理）
- **用途:** モデル作成、再学習、CI用モデル
- **詳細:** [model_tools/README.md](model_tools/README.md)

### **system_tools/ - システム管理**
GCP Cloud Run、システムヘルスチェック
- **主要ツール:** system_health_check.py
- **用途:** 診断、監視、トラブルシューティング
- **詳細:** [system_tools/README.md](system_tools/README.md)

### **data_tools/ - データ準備**
データの取得、分析、クリーニング
- **主要ツール:** prepare_initial_data.py
- **用途:** データ準備、バックテスト、分析
- **詳細:** [data_tools/README.md](data_tools/README.md)

### **monitoring/ - 監視・修復**
Phase 2-3/Phase 3の高度な監視機能
- **主要ツール:** signal_monitor.py, analyze_and_fix.py
- **用途:** リアルタイム監視、エラー修復
- **詳細:** [monitoring/README.md](monitoring/README.md)



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

### **デプロイメント・環境管理** (2025年8月12日更新)
- `verify_github_secrets.sh` - GitHub Secrets設定確認・CI/CDトラブルシューティング
- `setup_gcp_secrets.sh` - GCP Secret Manager設定（オプション）
- `cleanup_cloud_run_revisions.sh` - Cloud Runリビジョン競合解決
- **`deploy_with_initial_data.sh`** - 初期データ付きデプロイ
  - 初期データキャッシュ準備
  - Dockerビルド・テスト
  - Git commit/push
  - CI/CD自動トリガー
  - 完全自動化デプロイスクリプト
- **`cleanup_gcp_resources.sh`** - GCPリソースクリーンアップ（新規追加）
  - dev環境Cloud Runサービス削除
  - 古いリビジョン削除（最新3つ以外）
  - 古いDockerイメージ削除（最新10個以外）
  - dev環境Terraform状態ファイル削除
  - ドライランモード対応

### **監視・統合ツール** (2025年8月11日追加 - Phase 2-2/2-3)
- **`paper_trade_with_monitoring.sh`** - ペーパートレード＋シグナル監視統合
  - Phase 2-1 + Phase 2-2の統合実行
  - バックグラウンドでペーパートレード実行
  - 1時間毎にシグナル監視
  - 異常検出時のアラート
  - 終了時の統合レポート生成

### **検証・品質保証** (2025年8月11日追加 - Phase 2-3)
- **`validate_all.sh`** - 包括的3段階検証スクリプト
  - Level 1: 静的解析（checks.sh）
  - Level 2: 未来データリーク検出
  - Level 3: 動的検証（ペーパートレード・監視）
  - `--quick`: 高速モード（Level 1のみ）
  - `--ci`: CI/CDモード（Level 1+2）
- **`pre_deploy_validation.py`** - 本番デプロイ前統合検証
  - 未来データリーク検出
  - ペーパートレード実行
  - シグナルモニタリング
  - ユニットテスト実行
  - HTMLレポート生成

### **エラー分析・修復** (2025年8月11日追加 - Phase 3)
- **`analyze_and_fix.py`** - エラー分析・修復統合スクリプト
  - エラーログ収集・分析
  - 修復提案生成
  - インタラクティブ修復モード
  - 自動修復（CRITICALエラー）
  - 修復スクリプト生成

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

### **監視・品質管理** (2025年8月11日追加 - Phase 2-2/2-3/3)
- **`signal_monitor.py`** - シグナル生成監視システム（Phase 2-2）
  - 1時間以上シグナルなし検出
  - 連続パターン異常検出（30回連続HOLD等）
  - Confidence値異常検出
  - HTML/JSONレポート生成
- **`monitor_signals.sh`** - シグナル監視実行ラッパー
  - cronで定期実行対応
  - CI/CDパイプライン組み込み可能
- **`future_leak_detector.py`** - 未来データリーク検出器（Phase 2-3）
  - MLパイプラインの時系列整合性検証
  - 危険なパターン検出（shift(-1)、center=True等）
  - バックテストデータ分割チェック
  - HTML/JSONレポート生成
  - CI/CD統合対応（終了コードで判定）
- **`error_analyzer.py`** - エラーログ分析器（Phase 3）
  - GCP/ローカルログからエラーパターン抽出
  - 既知パターンとのマッチング
  - 修復提案の自動生成
  - 成功率学習システム
  - HTMLレポート生成

## 📦 archive/ - アーカイブ

過去の実装や参考用スクリプトを保管。将来の機能拡張時の参考資料として活用。

## 🗑️ deprecated/ - 不要スクリプト

整理により不要と判定されたスクリプト（63ファイル）を保管。古い特徴量システム（127/125/124）、デバッグ・修正系、統合前の個別スクリプトなど。

## 🚀 使用方法

### **📋 完全ワークフロー（推奨）**
```bash
# === デプロイ前チェック（CI実行前） ===
python scripts/bot_manager.py full-check        # 包括チェック（品質・監視・修復）
python scripts/bot_manager.py data-check        # データ取得ロジック事前検証

# Git push → CI実行 → デプロイ完了

# === CI通過後の稼働確認（運用開始後） ===  
python scripts/operational_status_checker.py   # 完璧稼働状況確認（4段階・隠れたエラー検出）

# 問題検出時の詳細確認
python scripts/operational_status_checker.py --verbose --phase phase3
```

### **日常的な開発作業**
```bash
# 品質チェック実行（コミット前必須）
bash scripts/checks.sh

# 包括的検証（本番デプロイ前必須）
bash scripts/validate_all.sh              # フル検証（〜10分）
bash scripts/validate_all.sh --quick      # 高速版（〜1分）
bash scripts/validate_all.sh --ci         # CI用（〜3分）

# 未来データリーク検出のみ
python scripts/utilities/future_leak_detector.py --project-root . --html

# 自動プッシュ（整形・テスト・プッシュ）
bash scripts/auto_push.sh "feat: add new feature"

# ペーパートレード＋監視統合実行（Phase 2-1 + 2-2）
bash scripts/paper_trade_with_monitoring.sh --duration 24

# シグナル監視のみ実行
python scripts/utilities/signal_monitor.py --hours 24
```

### **稼働確認専用ツール**
```bash
# 完璧稼働状況確認システム（運用中必須）
python scripts/operational_status_checker.py              # 全チェック実行
python scripts/operational_status_checker.py --phase phase3  # 隠れた問題のみ
python scripts/operational_status_checker.py --verbose    # 詳細ログ付き

# JST統一時刻でGCPログ確認
python scripts/utilities/unified_status_checker.py --hours 2
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

## 🎊 重要な変更・更新履歴

### **2025年8月12日：完璧稼働状況確認システム完成**
- **operational_status_checker.py**: 4段階チェックシステム（2,100行）
- **status_config.json**: 過去10パターンの隠れたエラーDB 
- **使い分け明確化**: デプロイ前=`bot_manager.py` / CI通過後=`operational_status_checker.py`
- **表面稼働・実際停止問題**: 完全解決（ヘルス200+ログ古い→検出）
- **UTC/JST混在問題**: JST統一・時刻混乱解消
- **既存tool統合**: 重複排除・4つの監視スクリプト統合完了

### **2025年8月11日：Phase 2-3検証システム**
- 未来データリーク検出・統合検証システム追加

### **2025年8月10日：CI/CD対応スクリプト**
- CI/CDパイプライン完全対応・エラー解決済み

### **2025年8月7日：大規模整理・最適化**
- Scripts構造体系化・63ファイル整理・統合システム構築

---

**🎯 現在のシステム状態**: 完璧稼働状況確認システム完成・隠れたエラー問題根本解決済み