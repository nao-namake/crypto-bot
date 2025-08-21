# Crypto-Bot - 🚀 AI自動取引システム

**個人向けAI自動取引システム（Phase 12完了・GCP古いリソース337個削除・運用最適化達成）**

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org) [![Phase](https://img.shields.io/badge/phase-12%20完了-brightgreen)](CLAUDE.md) [![Tests](https://img.shields.io/badge/tests-400+%20passed-success)](tests/) [![Quality](https://img.shields.io/badge/flake8%20改善-54%25%20削減-success)](scripts/quality/) [![READMEs](https://img.shields.io/badge/READMEs-22+%20完備-blue)](src/) [![GCP](https://img.shields.io/badge/GCP-337%20リソース削除-brightgreen)](docs/gcp/) [![CI/CD](https://img.shields.io/badge/CI%2FCD-最終修正完了-brightgreen)](.github/workflows/)

## 🎯 システム概要

個人向けAI自動取引システムです。レガシーシステム（56,355行）から保守性の高い新システム（Phase 12完了）への全面リファクタリングにより、安定性・効率性・運用品質を大幅に向上させました。

### 🏆 Phase 12完了成果（2025年8月21日）

**統合分析基盤・GCP古いリソース337個完全削除・本番運用最適化完了**:
- **400+テスト99.7%合格**: 統合品質チェック自動化・GitHub Actions統合・統合分析基盤対応
- **GCP古いリソース337個完全削除**: 7月レガシーシステム・8月20日以前古いリソース・コスト最適化達成
- **統合分析基盤完成**: base_analyzer.py基盤・重複コード520行削除・4種レポート自動生成統合
- **CI/CD最終修正完了**: Secret Manager統合・Workload Identity・構文修正・本番運用体制確立
- **22個README完備**: src/18個・scripts/4新設ディレクトリ・完全ドキュメント化
- **月次GCPリソースクリーンアップ**: 定期削除手順確立・コスト効率化・セキュリティ強化

### 📊 システム完成状況

```
✅ Phase 1-12: 全フェーズ完了・統合分析基盤・GCP古いリソース337個削除・本番運用最適化
🎯 400+テスト・99.7%品質保証達成・base_analyzer.py基盤・重複コード520行削除
📊 統合分析基盤確立: 実データ収集・A/Bテスト・ダッシュボード・パフォーマンス分析統合
🔧 品質最適化継続中（flake8エラー54%削減: 1,184→538）・月次クリーンアップ手順確立
🚀 本番運用体制完成: 24時間監視・段階的デプロイ・品質ゲート・GCP運用効率化
```

## 🔧 開発原則

### **🚨 重要：README.md優先原則**
**各フォルダ作業前に必ずREADME.mdを読む**
- **22個README完備**: src/18個・scripts/4新設ディレクトリ・包括的ガイド・完全ドキュメント化
- **目的・設計原則・実装方針**: 各ディレクトリの責任範囲を理解

## 🚀 クイックスタート

### 統合管理CLI（推奨 - Phase 12統合分析基盤対応）

```bash
# 注意: 環境によってはpython3コマンドが必要
# CI前チェック（開発時）
python3 scripts/management/dev_check.py full-check     # 6段階統合チェック（推奨）
python3 scripts/management/dev_check.py validate       # 軽量品質チェック
python3 scripts/management/dev_check.py ml-models      # MLモデル作成・検証

# 期待結果: 🎉 品質チェック完了！全項目合格・400+テスト99.7%成功
```

### 統合分析基盤（⭐ Phase 12新機能）

```bash
# 📊 実データ収集・分析・ダッシュボード（base_analyzer.py基盤活用）
python3 scripts/data_collection/trading_data_collector.py --hours 24    # 実データ収集
python3 scripts/ab_testing/simple_ab_test.py --hours 24                 # A/Bテスト実行
python3 scripts/dashboard/trading_dashboard.py --discord                # ダッシュボード生成

# 期待結果: ✅ 統合分析基盤によるレポート自動生成・Discord通知・HTML可視化
```

### システム実行

```bash
# メインシステム（環境によってはpython3を使用）
python3 main.py --mode paper     # ペーパートレード（推奨・安全確認）
python3 main.py --mode backtest  # バックテスト（過去データ検証）
python3 main.py --mode live      # ライブトレード（本番取引）

# 期待結果: 🚀 新システム v12.0 起動・400+テスト品質保証済み
```

### 品質チェック

```bash
# 品質チェック（推奨）
bash scripts/quality/checks.sh                        # 400+テスト・flake8・isort・black
bash scripts/quality/checks_light.sh                   # 軽量品質チェック（99.7%成功実績）

# 期待結果: ✅ 軽量品質チェック完了・flake8エラー54%削減達成
```

## 🏗️ システム構成

### **Phase 12統合分析基盤・重複コード520行削除・base_analyzer.py基盤**

```
src/                    # 新システム（18個README完備）
├── core/              # 基盤システム（設定管理・ログ・例外処理・統合制御）
├── data/              # データ層（Bitbank API・パイプライン・キャッシュ）
├── features/          # 特徴量（テクニカル指標12個厳選・異常検知）
├── strategies/        # 戦略システム（4戦略・113テスト100%）
├── ml/                # 機械学習（アンサンブル・89テスト100%・本番モデル）
├── backtest/          # バックテスト（エンジン・評価・84テスト100%）
├── trading/           # 取引実行（リスク管理・Kelly基準・113テスト100%）
└── monitoring/        # 監視（Discord通知・3階層）

scripts/                # 運用スクリプト（Phase 12機能別整理完了）
├── management/        # 管理・統合系（dev_check.py統合管理CLI）
├── quality/           # 品質保証・チェック系（完全品質・軽量チェック）
├── analytics/         # 📊 統合分析基盤（Phase 12新設）
│   └── base_analyzer.py            # 共通Cloud Runログ取得・抽象基盤・重複500行削除
├── data_collection/   # 📊 実データ収集システム（Phase 12新設）
│   └── trading_data_collector.py   # TradingStatisticsManager改良・統計分析
├── ab_testing/        # 🧪 A/Bテスト基盤（Phase 12新設）
│   └── simple_ab_test.py           # 統計的検定・p値計算・実用性重視
├── dashboard/         # 🎨 ダッシュボード（Phase 12新設）
│   └── trading_dashboard.py        # HTML可視化・Chart.js・Discord通知
├── ml/                # 機械学習・モデル系（12特徴量・アンサンブル）
├── deployment/        # デプロイ・Docker系（GCP Cloud Run）
└── testing/           # テスト・検証系（ライブトレードテスト）

models/                 # MLモデル管理（Phase 11完了・CI/CD統合）
├── production/         # 本番用統合モデル（ProductionEnsemble）
└── training/           # 学習用個別モデル（LightGBM・XGBoost・RandomForest）
```

## 📊 技術仕様

### **統合分析基盤データフロー（Phase 12完成）**
```
📊 src/data/ → Bitbank API・マルチタイムフレーム・キャッシュ
    ↓
🔢 src/features/ → テクニカル指標12個厳選・異常検知
    ↓  
🎯 src/strategies/ → 4戦略統合・シグナル生成（113テスト100%）
    ↓
🤖 src/ml/ → アンサンブル予測・投票システム（89テスト100%）
    ↓
📊 src/backtest/ → 性能評価・統計分析（84テスト100%）
    ↓
💼 src/trading/ → リスク管理・注文実行（113テスト100%）
    ↓
📡 src/monitoring/ → Discord通知・システム監視
    ↓
📈 scripts/analytics/ → base_analyzer.py基盤・Cloud Runログ統合・重複500行削除
    ↓
📊 scripts/data_collection/ → 実データ収集・TradingStatisticsManager改良・統計分析
📧 scripts/ab_testing/ → A/Bテスト・統計的検定・実用性重視
🎨 scripts/dashboard/ → HTML可視化・Chart.js・Discord通知連携
```

### 主要設定

**特徴量**: 12個厳選（97個→12個、87.6%削減）  
**ML**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）  
**リスク管理**: Kelly基準・ドローダウン制御・ATR損切り  
**統合分析**: base_analyzer.py基盤・4種レポート自動生成・重複コード520行削除

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

**3. 統合管理CLI実行**
```bash
# 統合品質チェック（400+テスト・flake8・isort・black）
python3 scripts/management/dev_check.py full-check

# 期待結果: 🎉 品質チェック完了！全項目合格
```

**4. 統合分析基盤実行**
```bash
# base_analyzer.py基盤による実データ収集
python3 scripts/data_collection/trading_data_collector.py --hours 24

# 期待結果: ✅ Phase 12-2実データ収集成功！
```

## 📋 重要ファイル

- **src/**: 新システム実装（18個README完備）・400+テスト99.7%品質保証
- **scripts/**: 運用スクリプト（22個README・base_analyzer.py基盤・統合分析基盤）
- **tests/**: 400+テスト・99.7%品質保証環境・包括的カバレッジ
- **CLAUDE.md**: 開発ガイダンス（Phase 12完了状況・統合分析基盤・GCP古いリソース337個削除）
- **docs/**: 包括的ドキュメント（運用手順・ローカル検証・GCPリソース管理）

## 💰 運用効率・コスト最適化

### **Phase 12技術実績**
- **400+テスト99.7%合格**: 統合品質保証体制・GitHub Actions統合・base_analyzer.py基盤対応
- **統合分析基盤完成**: base_analyzer.py・重複コード520行削除・4種レポート自動生成統合
- **GCP古いリソース337個削除**: 7月レガシー・8月20日以前リソース・月次クリーンアップ手順確立

### **運用コスト最適化達成**
- **月額¥2,000以内運用**: GCP古いリソース337個削除・コスト効率化達成
- **個人開発最適化**: 理解しやすい実装・保守性重視・統合分析基盤活用
- **品質保証確立**: 400+テスト・エラーハンドリング完備・月次リソースクリーンアップ

### **月次GCPリソース管理（Phase 12新機能）**
- **定期クリーンアップ手順**: 古いDockerイメージ・Cloud Runリビジョン・BigQueryテーブル削除
- **コスト効率化**: 不要リソース削除・ストレージ最適化・監視システム効率化
- **セキュリティ強化**: 古い設定削除・アクセス権限整理・セキュアな運用体制確立

---

**🎉 Phase 12完了成果**: *統合分析基盤・GCP古いリソース337個完全削除・重複コード520行削除・base_analyzer.py基盤・実データ収集・A/Bテスト・ダッシュボード・月次クリーンアップ手順により、保守性と運用効率を大幅向上させた個人向けAI自動取引システムを完成* 🚀

*統合分析基盤・コスト最適化・品質保証継続・月次GCPリソース管理・レガシー知見活用・実用性重視を重視した個人開発最適化アーキテクチャ*