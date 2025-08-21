# Crypto-Bot - 🚀 AI自動取引システム

**個人向けAI自動取引システム（Phase 12完了・CI/CD全8回修正完了・Secret Manager統合・稼働確実性達成）**

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org) [![Phase](https://img.shields.io/badge/phase-12%20完了-brightgreen)](CLAUDE.md) [![Tests](https://img.shields.io/badge/tests-316%20passed-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-68.13%25-success)](tests/) [![Quality](https://img.shields.io/badge/flake8%20改善-54%25%20削減-success)](scripts/quality/) [![READMEs](https://img.shields.io/badge/READMEs-25+%20files-blue)](src/) [![CI/CD](https://img.shields.io/badge/CI%2FCD-全8回修正完了-brightgreen)](scripts/deployment/) [![GCP](https://img.shields.io/badge/GCP-Secret%20Manager統合-brightgreen)](config/ci/)

## 🎯 システム概要

個人向けAI自動取引システムです。レガシーシステム（56,355行）から新システムへの全面リファクタリングにより、保守性・安定性・効率性を大幅に向上させました。

### 🏆 Phase 12完了成果（2025年8月21日）

**CI/CD全8回修正完了・Secret Manager統合・稼働確実性達成・本番運用準備完了**:
- **316テスト・68.13%カバレッジ**: 品質保証体制確立・CI/CD統合検証追加
- **CI/CD全8回修正完了**: 全根本原因解決・Workload Identity・Secret Manager名前統合・構文修正完了
- **Secret Manager完全統合**: bitbank-api-key・bitbank-api-secret・discord-webhook-url正常動作
- **自動診断システム**: verify_gcp_setup.sh・setup_ci_prerequisites.sh・ワンクリック環境構築
- **包括的ドキュメント**: GCP事前設定ガイド・CI/CDエラーハンドリング強化・統合ワークフロー
- **25+個README完備**: src/18個・scripts/7個・包括的ガイド・config統合設定
- **完全修正履歴**: 環境変数・認証・ファイルパス・Secret Manager・構文・全根本原因解決（2025年8月21日）

### 📊 システム完成状況

```
✅ Phase 1-12: 全フェーズ完了・CI/CD全8回修正完了システム統合
🎯 316テスト・68.13%カバレッジ・GitHub Actions環境検証ジョブ追加
📊 CI/CD全修正完了: 全8回根本原因解決・Secret Manager統合・構文修正・本番運用準備
🔧 品質最適化継続中（flake8エラー54%削減）・自動診断システム稼働
🚀 CI/CD稼働確実性: 全根本原因解決・Secret Manager名前統合・Workload Identity確実化
```

## 🔧 開発原則

### **🚨 重要：README.md優先原則**
**各フォルダ作業前に必ずREADME.mdを読む**
- **25+個README完備**: src/18個・scripts/7個・包括的ガイド・config統合設定
- **目的・設計原則・実装方針**: 各ディレクトリの責任範囲を理解

## 🚀 クイックスタート

### GCP CI/CD改善システム（⭐ Phase 12新機能）

```bash
# 📋 GCP環境検証・準備（初回セットアップ）
bash scripts/deployment/verify_gcp_setup.sh --full              # 包括的環境検証
bash scripts/deployment/setup_ci_prerequisites.sh --interactive # 自動セットアップ

# 🔧 問題修復・メンテナンス（エラー発生時）
bash scripts/deployment/verify_gcp_setup.sh --ci                # CI実行前検証
bash scripts/deployment/setup_ci_prerequisites.sh --repair     # 自動修復

# 期待結果: ✅ GCP環境準備完了・CI/CD失敗率90%削減・デプロイ成功
```

### 統合管理CLI（推奨）

```bash
# 注意: 環境によってはpython3コマンドが必要
# CI前チェック（開発時）
python3 scripts/management/dev_check.py full-check     # 6段階統合チェック
python3 scripts/management/dev_check.py validate       # 軽量品質チェック
python3 scripts/management/dev_check.py ml-models      # MLモデル作成・検証

# CI後チェック（デプロイ後）
python3 scripts/management/ops_monitor.py              # 運用診断・4フェーズ確認

# 期待結果: ✅ すべてのチェックに合格・レポート自動保存（logs/配下）
```

### システム実行

```bash
# メインシステム（環境によってはpython3を使用）
python3 main.py --mode paper     # ペーパートレード（推奨・安全確認）
python3 main.py --mode backtest  # バックテスト（過去データ検証）
python3 main.py --mode live      # ライブトレード（本番取引）

# 統合分析（Phase 12新機能）
python3 scripts/data_collection/trading_data_collector.py --hours 24  # 実データ収集
python3 scripts/ab_testing/simple_ab_test.py --hours 24               # A/Bテスト
python3 scripts/dashboard/trading_dashboard.py --discord              # ダッシュボード
```

### 品質チェック

```bash
# 品質チェック（推奨）
bash scripts/quality/checks.sh                        # 316テスト・flake8・isort・black

# 手動テスト
python3 tests/manual/test_phase2_components.py         # データ層基盤確認
```

## 🏗️ システム構成

```
src/                    # 新システム（18個README完備）
├── core/              # 基盤システム（設定管理・ログ・例外処理・統合制御）
├── data/              # データ層（Bitbank API・パイプライン・キャッシュ）
├── features/          # 特徴量（テクニカル指標12個・異常検知）
├── strategies/        # 戦略システム（4戦略・113テスト）
├── ml/                # 機械学習（アンサンブル・89テスト・本番モデル）
├── backtest/          # バックテスト（エンジン・評価・84テスト）
├── trading/           # 取引実行（リスク管理・Kelly基準・113テスト）
└── monitoring/        # 監視（Discord通知・3階層）

scripts/                # 運用スクリプト（22個README完備）
├── management/        # 統合管理CLI（dev_check.py・6機能統合）
├── quality/           # 品質チェック（316テスト・flake8・isort・black）
├── analytics/         # 統合分析基盤（base_analyzer.py・重複500行削除）
├── data_collection/   # 実データ収集（統計分析・TradingStatisticsManager）
├── ab_testing/        # A/Bテスト（統計的検定・p値計算）
├── dashboard/         # ダッシュボード（HTML可視化・Chart.js）
├── ml/               # MLモデル作成（12特徴量・アンサンブル）
├── deployment/       # デプロイ（GCP Cloud Run・Docker）
└── testing/          # ライブトレードテスト

logs/                   # ログ・レポート（9個README完備・Phase 12レポート機能）
├── dev_check_reports/     # CI前チェック結果
├── ops_monitor_reports/   # CI後チェック結果
├── backtest_reports/      # バックテストレポート
├── paper_trading_reports/ # ペーパートレードセッション
├── operational_reports/   # JSON形式運用診断
├── operational_status/    # キャッシュ・デバッグデータ
├── state/                # 状態管理（ドローダウン・ヘルス・監視・セキュリティ）
└── trading/              # 取引ログ（316テスト実績）
```

## 📊 技術仕様

### データフロー
```
📊 data → 🔢 features → 🎯 strategies → 🤖 ml → 💼 trading → 📡 monitoring
                                       ↓
📊 backtest → 📈 analytics → 📊 data_collection → 🎨 dashboard
```

### 主要設定

**特徴量**: 12個厳選（97個→12個、87.6%削減）  
**ML**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）  
**リスク管理**: Kelly基準・ドローダウン20%制限・ATR損切り

## 🚨 トラブルシューティング

### よくある問題

**1. インポートエラー**
```bash
# プロジェクトルートから実行（python3使用）
cd /Users/nao/Desktop/bot
python3 -m pytest tests/unit/ -v
```

**2. テスト失敗**
```bash
# 個別テスト実行で問題特定
python3 -m pytest tests/unit/strategies/test_atr_based.py -v -s
```

**3. バックテストエラー**
```bash
# バックテストシステム確認
python3 -c "from src.backtest.engine import BacktestEngine; print('✅ OK')"
```

**4. 品質チェックエラー**
```bash
# 軽量品質チェック（推奨）
bash scripts/quality/checks_light.sh

# 完全品質チェック
bash scripts/quality/checks.sh
```

## 📋 重要ファイル

- **src/**: 新システム実装（18個README完備）
- **scripts/**: 運用スクリプト（22個README・base_analyzer.py基盤）
- **tests/**: 316テスト・68.13%品質保証環境
- **logs/**: レポート・状態管理（9個README・Phase 12レポート機能）
- **config/**: 設定管理（production.yaml含む）
- **CLAUDE.md**: 開発ガイダンス（詳細な開発方針・使用方法）
- **開発履歴.md**: Phase 1-12詳細開発経緯（技術詳細・実装背景）

## 💰 運用効率

### 技術実績
- **316テスト・68.13%カバレッジ**: 包括的品質保証体制
- **統合分析基盤**: base_analyzer.py・重複コード500行削除・4種レポート自動生成
- **31個README完備**: 完全ドキュメント化・保守性向上

### 運用コスト
- **月額¥2,000以内**（GCP Cloud Run）
- **個人開発最適化**・理解しやすい実装
- **エラーハンドリング完備**・品質保証確立

---

**🎯 Phase 12完了**: 統合分析基盤・重複コード500行削除・レポート生成機能・CI/CD統合・手動実行監視により、保守性と運用効率を大幅向上させた個人向けAI自動取引システムを完成