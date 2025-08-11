# Crypto-Bot - 🚀 次世代AI自動取引システム

**BitbankでのBTC/JPY自動取引を行う高度なML取引システム**

[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/nao-namake/crypto-bot/ci.yml)](https://github.com/nao-namake/crypto-bot/actions) [![Coverage](https://img.shields.io/badge/coverage-32.30%25-yellow)](https://github.com/nao-namake/crypto-bot) [![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org) [![GCP](https://img.shields.io/badge/platform-GCP%20Cloud%20Run-green)](https://cloud.google.com)

**🆕 2025年8月12日更新**:
- **データ取得効率化**: ATR初期化データのメインループ再利用でAPI制限回避
- **日本時間ログビューアー**: GCPログをJSTで表示する新ツール追加
- **リビジョン管理強化**: CI/CDタイムスタンプタグ・古いリビジョン自動削除

## 🎯 システム概要

crypto-botは、機械学習を活用したBitbank BTC/JPY自動取引システムです。97の高度な特徴量を使用し、3つのMLモデル（LightGBM、XGBoost、RandomForest）のアンサンブル学習で予測を行い、信用取引で自動売買を実行します。

### 🚀 主要機能

- **🧠 97特徴量システム**: テクニカル指標・市場状態・時間特徴量の最適化セット
- **🤖 アンサンブル学習**: LightGBM + XGBoost + RandomForest統合モデル
- **📊 リアルタイム予測**: 1時間足データでの高精度エントリーシグナル生成
- **🛡️ リスク管理**: Kelly基準・動的ポジションサイジング・ATR損切り
- **⚡ 高速インフラ**: GCP Cloud Run・5分以内CI/CD・月額2,200円

### 📊 現在の運用状況

**✅ 正常稼働中** (2025年8月11日更新・Phase 2-3/Phase 3完全実装済み)
- **取引モード**: live（BTC/JPY自動取引）
- **予測システム**: 97特徴量アンサンブル学習
- **実行環境**: GCP Cloud Run・自動スケーリング
- **最新実装**: ✅ ChatGPT提案システム完全実装（Paper Trading・Signal Monitoring・Leak Detection・Error Auto-Fix）
- **品質保証**: ✅ 605/605テスト成功・32.32%カバレッジ・flake8/black完全準拠
- **エントリー条件**: confidence > 0.35（全戦略で統一済み）
- **リスク管理**: 1取引あたり1%・最大3%

## 🚨 開発作業の重要原則

### 📋 各フォルダのREADME.mdを必ず最初に読むこと

このプロジェクトでは、各フォルダにREADME.mdが配置されており、その**目的・設計原則・使用方法**が記載されています。作業前に必ず対象フォルダのREADME.mdを読んでください。

**主要README.md**：`crypto_bot/*/README.md`, `scripts/README.md`, `tests/README.md`, `config/README.md`, `models/README.md`, `infra/README.md`

## ✨ 最新機能（Phase 2-3実装 - 2025年8月11日）

### **🌟 統合CLIで全機能を簡単管理**

```bash
# 統合CLIのヘルプを表示
python scripts/bot_manager.py --help

# すべての機能を1つのコマンドでチェック
python scripts/bot_manager.py full-check
```

### **Phase 2-1: ペーパートレード機能**
リアルデータでの仮想取引を実行し、リスクフリーで戦略を検証：
```bash
# 統合CLI経由（推奨）
python scripts/bot_manager.py paper-trade --hours 2

# 従来の方法
python -m crypto_bot.main live-bitbank --paper-trade
```

### **Phase 2-2: シグナル監視システム**
取引シグナルの異常パターンを自動検出：
```bash
# 統合CLI経由（推奨）
python scripts/bot_manager.py monitor --hours 24

# ペーパートレードと同時監視
python scripts/bot_manager.py monitor --hours 24 --with-paper-trade

# 従来の方法
python scripts/utilities/signal_monitor.py --hours 24
```

### **Phase 2-3: 未来データリーク検出**
MLパイプラインの時系列整合性を検証：
```bash
# 統合CLI経由（推奨）
python scripts/bot_manager.py leak-detect

# 従来の方法
python scripts/utilities/future_leak_detector.py --project-root . --html
```

### **Phase 3: エラー分析・自動修復**
エラーパターンを学習し、自動修復提案を生成：
```bash
# 統合CLI経由（推奨）
python scripts/bot_manager.py fix-errors --auto-fix
python scripts/bot_manager.py fix-errors --source gcp

# 従来の方法
python scripts/analyze_and_fix.py --source both --hours 24
python scripts/analyze_and_fix.py --interactive
python scripts/analyze_and_fix.py --auto-fix
```

### **📋 統合検証フロー**
本番デプロイ前の包括的な3段階検証：
```bash
# フル検証（〜10分）
bash scripts/validate_all.sh

# 高速版（Level 1のみ、〜1分）  
bash scripts/validate_all.sh --quick

# CI用（Level 1+2、〜3分）
bash scripts/validate_all.sh --ci
```

## 🛠️ クイックスタート

### 🌟 統合CLIによる簡単管理（推奨）

```bash
# リポジトリクローン
git clone https://github.com/your-username/crypto-bot.git
cd crypto-bot

# 依存関係インストール
pip install -r requirements/dev.txt

# 統合CLIでシステム状態確認
python scripts/bot_manager.py status

# 開発ワークフロー（統合CLI使用）
python scripts/bot_manager.py validate --mode quick  # 高速チェック
python scripts/bot_manager.py full-check            # 完全検証
python scripts/bot_manager.py fix-errors            # エラー修復
```

### 従来の開発環境（個別スクリプト）

```bash
# 依存関係チェック
python requirements/validate.py
make validate-deps

# 品質チェック実行（コミット前必須）
bash scripts/checks.sh

# 本番デプロイ前検証（デプロイ前必須）
bash scripts/validate_all.sh
```

### バックテスト実行

```bash
# 97特徴量システムでバックテスト
python -m crypto_bot.main backtest --config config/validation/unified_97_features_backtest.yml

# アンサンブル学習バックテスト
python -m crypto_bot.main backtest --config config/validation/ensemble_trading.yml
```

### ライブトレード（本番）

```bash
# 本番設定でライブトレード実行
python -m crypto_bot.main live-bitbank --config config/production/production.yml
```

## 🏗️ システム構成

```
crypto_bot/                    # メインアプリケーション
├── cli/                       # CLIコマンド（backtest・live・train等）
├── data/                      # データ管理
│   ├── fetcher.py            # 統合データ取得API
│   └── fetching/             # 分割システム（Phase 16）
├── ml/                        # 機械学習パイプライン  
│   ├── feature_master_implementation.py  # 97特徴量エンジン
│   └── preprocessor.py       # データ前処理
├── strategy/                  # 戦略・リスク管理
├── execution/                 # Bitbank取引実行
├── utils/                     # 共通ユーティリティ
└── main.py                   # エントリーポイント（130行・95%削減達成）

config/production/production.yml  # 本番設定（固定ファイル）
models/production/model.pkl       # 本番モデル（固定ファイル）
infra/envs/prod/                   # 本番インフラ（Terraform）
```

## ⚙️ 重要設定

### 97特徴量システム

**構成**: OHLCV基本データ(5) + 高度ML特徴量(92) = 97特徴量

**主要カテゴリ**:
- **基本ラグ・リターン**: close_lag_1/3, returns_1/2/3/5/10
- **移動平均・トレンド**: ema_5/10/20/50/100/200, price_position_20/50
- **テクニカル指標**: RSI, MACD, Bollinger Bands, ATR, Stochastic
- **出来高分析**: VWAP, OBV, CMF, MFI, volume系指標
- **高度パターン**: サポレジ、ブレイクアウト、ローソク足パターン
- **市場状態**: volatility_regime, momentum_quality, market_phase
- **時間特徴**: hour, day_of_week, session分析

### アンサンブル学習設定

```yaml
ensemble:
  enabled: true
  models: ["lgbm", "xgb", "rf"]  # LightGBM + XGBoost + RandomForest
  confidence_threshold: 0.35     # エントリー判定閾値
  method: trading_stacking       # 統合方式
  model_weights: [0.5, 0.3, 0.2] # モデル重み
```

### リスク管理設定

```yaml
risk:
  risk_per_trade: 0.01          # 1取引あたり1%リスク
  kelly_criterion:
    enabled: true
    max_fraction: 0.03          # Kelly基準最大3%
  stop_atr_mult: 1.2           # 1.2×ATR損切り
```

## 🔧 開発・運用コマンド

### システム監視

```bash
# 本番システムヘルスチェック
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

# GCPログ監視
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TRADE\"" --limit=10

# システム性能分析
python scripts/analyze_live_performance.py
```

### インフラ操作

```bash
# Terraformローカル検証（5分以内処理）
cd infra/envs/prod/ 
terraform validate && terraform plan

# 高速CI/CDデプロイ（本番環境）
git push origin main  # GitHub Actions自動実行・5分以内完了
```

### モデル管理

```bash
# モデル再学習
python scripts/retrain_97_features_model.py
python scripts/create_proper_ensemble_model.py

# バックアップ・昇格ワークフロー
cp models/production/model.pkl models/production/model_backup_$(date +%Y%m%d).pkl
cp models/validation/best_model.pkl models/production/model.pkl
```

## 💰 運用コスト・効率

### 月額運用コスト

| 環境 | CPU | Memory | 月額コスト |
|------|-----|--------|-----------|
| dev  | 500m | 1Gi   | ¥200     |
| prod | 1000m | 2Gi   | ¥2,000   |
| **合計** | - | - | **¥2,200** |

### 技術効率

- **コード最適化**: 10,644行削除による保守性向上
- **処理効率**: 97特徴量最適化で24%計算効率向上
- **CI/CD高速化**: Terraform 5分以内処理達成
- **予測精度**: アンサンブル学習による安定性向上

## 🚀 デプロイ前の推奨チェックリスト

### **必須確認項目**

```bash
# 1. 統合CLIで完全チェック実行
python scripts/bot_manager.py full-check

# すべてPASSしたら次へ進む
```

### **環境確認**

- [ ] **GCP認証**: `gcloud auth list` で認証済みか確認
- [ ] **プロジェクト設定**: `gcloud config get-value project` で正しいプロジェクトか確認
- [ ] **Bitbank API**: 環境変数 `BITBANK_API_KEY` と `BITBANK_API_SECRET` が設定済みか
- [ ] **本番設定**: `config/production/production.yml` の内容を最終確認
- [ ] **モデルファイル**: `models/production/model.pkl` が存在するか確認

### **最終デプロイコマンド**

```bash
# すべての確認が完了したら
git add -A
git commit -m "feat: your detailed commit message"
git push origin main

# CI/CDの進行状況を確認
# GitHub Actions: https://github.com/your-repo/actions
```

### **デプロイ後の確認**

```bash
# ヘルスチェック
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

# 🆕 日本時間でログ確認（最新リビジョンのみ自動選択）
python scripts/utilities/gcp_log_viewer.py --hours 0.5  # 過去30分
python scripts/utilities/gcp_log_viewer.py --search "TRADE" --hours 1

# 🆕 古いリビジョンの削除（ログの混乱防止）
bash scripts/utilities/cleanup_old_revisions.sh --dry-run

# 従来のログ確認方法（UTC表示）
gcloud logging read "resource.type=cloud_run_revision" --limit=10
gcloud logging read "textPayload:TRADE" --limit=5
```

## 🚨 トラブルシューティング

### よくある問題

```bash
# データ取得エラー
# 対処: config/production/production.yml の since_hours・limit 値調整

# モデル予測エラー
# 対処: python scripts/create_proper_ensemble_model.py 実行

# CI/CD・Terraformエラー  
# 対処: Phase 19+最適化済み（5分以内処理・環境変数3個に最適化）
```

### システム診断

```bash
# Step 1: 基本ヘルスチェック
curl https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health

# Step 2: ログ分析
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"TRADE\"" --limit=5

# Step 3: CI/CD状態確認
gcloud logging read "resource.type=cloud_run_revision AND textPayload:\"INIT\"" --limit=5

# Step 4: 緊急時対応
python scripts/utilities/emergency_shutdown.py  # 取引停止
```

## 🎊 開発成果・特徴

### 解決された主要課題（2025年8月10日最新）
- **エントリーシグナル生成エラー修正**: pandas import重複・strategy型チェック・confidence_threshold統一（0.35）
- **8つの隠れたエラー修正**: API認証・モデル不在・タイムスタンプ・INIT処理等の完全解決
- **CI/CD完全修正**: YAML構文エラー・flake8違反・black整形問題の根本解決
- **取引実行基盤**: 97特徴量システム・アンサンブル学習・リスク管理統合
- **システム安定性**: データ取得最適化・エラー処理強化・品質保証体制
- **開発効率**: モジュラー設計（10,644行削除）・文書体系整備・CI/CD高速化
- **運用最適化**: インフラ安定化・コスト効率化・監視体制確立

### 現在のシステム特徴
- ✅ **高精度予測**: 97特徴量×アンサンブル学習（LGBM+XGBoost+RF）
- ✅ **安全なリスク管理**: Kelly基準・信用取引・動的ポジションサイジング
- ✅ **効率的運用**: 月額2,200円・自動スケーリング・CI/CD 5分以内
- ✅ **品質保証**: 579テスト成功・カバレッジ32.30%・flake8/black/isort完全準拠
- ✅ **保守性**: モジュラー設計・完全文書化・README.md体系整備

---

## 📝 ライセンス・貢献

このプロジェクトは個人開発プロジェクトです。詳細な開発履歴や技術的な背景については `CLAUDE.md` を参照してください。

**🚀 継続的改善により進化し続ける次世代AI自動取引システム** （2025年8月10日現在）